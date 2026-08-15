---
spike: 001
name: qemu-rscmgr-assert
type: standard
validates: "Given stock 6D2 firmware in qemu-eos, when the emulated SD card geometry is varied, then the RscMgr/EstimatedSize.c:1521 assert clears and boot proceeds toward the GUI"
verdict: INVALIDATED
related: [004]
tags: [qemu, boot, sd-card]
---

# Spike 001: QEMU RscMgr Assert

## What This Validates

**Given** stock 6D2 firmware booting in qemu-eos,
**when** the emulated SD card geometry / image size is varied (and the earlier
`[SDIO] Error` and `[TA10] Irregular TotalSheets` warnings are ruled in or out),
**then** the `ASSERT : Resource/./EstimatedSize.c, Task = RscMgr, Line 1521`
clears and boot proceeds further toward the Canon GUI.

This is the gate blocking Phase A step 4. Until firmware reaches the GUI, there
is no debug rig for any ML feature work.

## Research

Prior run (2026-08-15) established the exact failure point. Boot reaches:

    [EOS] loading ROM0.BIN to 0xE0000000-0xE1FFFFFF
    [EOS] loading ROM1.BIN to 0xF0000000-0xF0FFFFFF
    <<<<< Musa(PU0) Boot Ver 0.19 >>>>>
    K406 READY
    K406 ICU Firmware Version 1.1.1 ( 6.4.9 )
    [SD] Name: QEMU! Size: 247(7bc00)
    [FSU] efat_map_filesys / Attach SC 1 0 80 20 248

then halts at:

    [FSU] AllocateMemoryStrictly For Speed Class!!!
    ASSERT : Resource/./EstimatedSize.c, Task = RscMgr, Line 1521

The assert fires in the resource manager's size estimation immediately after
the filesystem unit performs a **speed-class** allocation for the emulated card.
247 MB is small and QEMU-synthesised — prime suspect.

## How to Run

    nix-shell "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/shell.nix"
    cd /home/chris/ml6d2/qemu-eos/magiclantern
    python3 run_qemu.py 6D2 -q /home/chris/ml6d2/qemu-eos-build

`-q` is required — `get_default_dirs` resolves via `realpath`, which follows the
symlink farm back to the space-containing project path and finds no build dir.

## What to Expect

Baseline reproduces the assert above. A successful variation shows the assert
either disappearing or moving to a different line/task — both are signal.

## Investigation Trail

All runs headless (`display=None`), captured to
`/tmp/claude-1000/-home-chris-Vibe-Coding-6D-Mark-II-Magic-Lantern-6D2/7fd303d5-2f0f-4650-82c5-e334e473a37f/scratchpad/`
via a small wrapper around `ml_qemu.run.QemuRunner` (`runq.py`) so each run
writes its own `<tag>.serial` (UART) and `<tag>.err` (`-d debugmsg`) log.
Runs were compared by diffing those files, never by eyeballing one run.

### 1. Baseline — reproduce, and find the prior reading was wrong

Baseline reproduces exactly (`base248`, and again as `rpt248` for determinism).
But the `-d debugmsg` stream shows something the serial log alone hid:

**the firmware does not halt at the assert.** It continues for ~30 more
messages and finishes startup in an error state:

    RscMgr    ASSERT : Resource/./EstimatedSize.c, Line 1521 / FALSE
    PropMgr   startupErrorRequestChangeCBR (0x1d)
    PropMgr   startupErrorRequestChangeCBR : ErrorSend (101, ABORT)
    FileMgr   [STARTUP]startupCompleteCallback 0x400000
    FileMgr   [SEQ] NotifyComplete (Startup, Flag = 0x400000)
    FileMgr   PROP_CARD2_CLUSTER_SIZE = 16384 / FOLDER_NUMBER = 100 / FILE_NUMBER = 46

So this is a *soft* failure (Canon's ABORT-with-error-101 startup path), not a
hang. PLAN_OF_ACTION §2a's "Stops here" is an artefact of reading only the
serial log. That matters: it means later boot stages are reachable in principle.

The 12 messages immediately before the assert are all `RscMgr` DCF work —
`srmNotifyDcfNo 0x2 100 0 0 1`, `Diff Dcf List`, `####### [1]DCF No 46`,
`ExcludeAllocedMem3 0`. So the assert is in *remaining-shots estimation* after
the card's DCF directory is enumerated, not in card initialisation.

### 2. Card size sweep — the stated hypothesis

`qemu-img resize` on a copy of the stock image, so only the *card* size changes
(the MBR/FAT16 partition stays at 247.5 MiB starting at LBA 99):

| card | `[SD] Name: QEMU! Size:` | `[FSU] Attach SC` | assert |
|---|---|---|---|
| 248 MiB (stock) | `247(7bc00)` | `1 0 80 20 248` | **fires** |
| 512 MiB | `512(100000)` | `1 0 80 20 248` | **fires** |
| 2 GiB | `2048(400000)` | `1 0 80 20 248` | **fires** |
| 8 GiB | `8192(1000000)` | `1 0 80 20 248` | **fires** |
| 32 GiB | `32768(4000000)` | `1 0 80 20 248` | **fires** |

The size is reported faithfully, so the emulation is doing its job — and the
assert is byte-identical at every size. Note the `Attach SC` trailer stays
`248`: that number is the *partition*, not the card.

### 3. Real filesystems, not just a resized container

Built fresh cards with `sfdisk` + `mkfs.vfat` (no root needed), partition
starting at LBA 99 to match stock:

| card | `Attach SC` | assert |
|---|---|---|
| FAT16, 248 MiB | `1 0 200 80 248` | **fires** |
| FAT32, 2 GiB | `1 0 200 80 2044` | **fires** |
| FAT32, 8 GiB | `1 0 200 80 8176` | **fires** |

This is the important negative: the FSU speed-class parameters **do** respond to
the filesystem (`80 20` → `200 80`, and the trailing size tracks the partition),
proving the knob is really being turned — and the assert still does not move.

### 4. Controls — take the card away entirely

- **Blank card** (248 MiB of zeros, no MBR, no FS): `[FSU] ERROR fsuGetPart :
  not supported format`. The `EstimatedSize` assert **does not appear** — a
  different one does, `SystemIF::KerRLock.c, Task = ShtCap, Line 205` on Core 1.
  Initially this looked like progress; it is not. With no mountable filesystem
  the DCF path is simply never entered, so the estimator is never called.
- **No SD drive at all** (`-drive if=sd` removed from the command line):
  `SddomCARDInitialize(0) media type unknown ERR`, `SD_DeviceCreate ERROR` —
  and `ASSERT : Resource/./EstimatedSize.c, Line 1521` **still fires,
  identically**.

That is decisive. An assert that fires when there is no card in the machine
cannot be caused by the card's geometry.

### 5. Ruling in/out the earlier warnings (lead 2)

**`[SDIO] Error` ×4 — benign, ruled out.** Re-ran with `-d debugmsg,sdcf` to
log every command. All four are `sdio_send_command` classifying a *no-response*
command as an error (`rlen == 0` falls into the error branch in
`hw/eos/eos.c:5013`):

    Command 0  00000000   -> CMD0  GO_IDLE_STATE (x3, no response by design)
    Command 52 80000c08   -> CMD52 IO_RW_DIRECT     (SDIO-only)
    Command 5  00000000   -> CMD5  IO_SEND_OP_COND  (SDIO-only)

CMD0 never returns a response; CMD52/CMD5 are SDIO-I/O probes that a plain
memory card correctly ignores. Card init then succeeds. This is a logging
artefact, not a fault. (With no card, the count rises to 17 — also expected.)

**`[TA10] ERROR Irregular TotalSheets 0 !!` — ruled out as card-related, but it
is the same root cause.** It appears in *every* configuration, including
no-card and blank-card, and always *before* SD init, so nothing on the card can
influence it. Its origin is visible in the MPU trace:

    [MPU] Received: 0a 08 03 06 00 00 00 00 00 00  (unknown - PROP_AVAIL_SHOT)

An all-zero `PROP_AVAIL_SHOT` payload is exactly "TotalSheets 0".

### 6. Root cause — read it out of the ROM, then confirm in gdb

Located the assert in `roms/6D2/ROM0.BIN` (read-only; nothing copied or
modified). The string `Resource/./EstimatedSize.c` is at `0xE02023F0` with no
32-bit literal-pool reference anywhere — because the caller reaches it with a
PC-relative `subw`, which means the calling code must sit within ~4 KB of it.
Searching that window for `movw rX, #1521` found the call site at `0xE0202480`.

Assert handler (`0xE0040E9A`, args `r0=cond, r1=file, r2=line`), call site:

    e0202372:  ldr    r0, [r6, #8]        <- the value under test
    e020237a:  cmp.w  r0, #2000
    e0202380:  cmp.w  r0, #2400
    e0202386:  sub.w  r1, r0, #2304 ; subs r1, #94    -> 2398
    e020238e:  subs   r1, #102                        -> 2500
    e0202392:  sub.w  r1, r0, #2816 ; subs r1, #181   -> 2997
    e020239a:  sub.w  r1, r0, #4864 ; subs r1, #136   -> 5000
    e02023a2:  sub.w  r1, r0, #5888 ; subs r1, #106   -> 5994
    e0202478:  sub.w  r1, r0, #11776; subs r1, #212   -> 11988
    e0202480:  movw   r2, #1521                       <- line number
    e0202484:  subw   r1, pc, #152        -> "Resource/./EstimatedSize.c"
    e0202488:  subw   r0, pc, #40         -> "FALSE"
    e020248c:  bl     0xe0617620          -> assert

The accepted set is `{2000, 2398, 2400, 2500, 2997, 5000, 5994, 11988}` —
frame rates in hundredths of fps: 20, 23.98, 24, 25, 29.97, 50, 59.94, 119.88.
The strings adjacent to the filename in ROM agree: `GetEstimatedSizeOfBaselineJpeg
%ld`, `NO IMAGEFORMAT %s %d`, `pdwSize != NULL`, **`pdwFrameRate != NULL`**,
`pdwGopStruct != NULL`, `FALSE`.

Confirmed live with gdb (`--gdb`, `arm-none-eabi-gdb`, breakpoint at
`*0xe0202480`):

    r0 = 0x51 (81)        <- not in the accepted set
    r6 = 0x221228
    0x221228: 00000000 00000001 00000051 8000003b
    0x221238: 00000058 00000001 00000055 8000003f

`0x8000003B` / `0x8000003F` are DIGIC 6/7 property IDs, so the record the
estimator dereferences is not a movie-format descriptor at all — the field that
should hold a frame rate holds 81.

### 7. Where the bad data comes from

`hw/eos/mpu_spells/` contains spells for 450D…700D, 100D, EOSM, 5D2, 5D3, 6D,
60D, 70D — and nothing newer. `mpu.c:1245` therefore falls back to
`mpu_init_spells_generic` and prints the FIXME we already knew about. The
consequence is visible throughout the trace: most received spells decode as
`unknown - unnamed`, several are mapped to the wrong property name, and no
image-quality / video-format property ever arrives. `PROP_AVAIL_SHOT` arriving
as all zeros (→ `TotalSheets 0`) is the same failure in a case where the
firmware only warns instead of asserting.

Dead ends worth recording: `qemu-img resize` alone (the FS never changes, so it
only tests the card container); reading the serial log instead of the debugmsg
stream (hides everything after the assert); and treating the blank-card result
as progress (it skips the code path rather than fixing it).

## Results

**Verdict: INVALIDATED.** Varying the emulated SD card's size or geometry does
not clear the `RscMgr` / `EstimatedSize.c:1521` assert. Eight distinct card
configurations were tested — 248 MiB / 512 MiB / 2 GiB / 8 GiB / 32 GiB
containers, freshly built FAT16 248 MiB and FAT32 2 GiB / 8 GiB filesystems, an
unformatted card, and no card at all — and the assert is unchanged in all of
them except the unformatted card, which merely skips the code path and trips a
different assert instead.

**What the assert actually is.** `EstimatedSize.c:1521` is a
`switch`-with-no-default over a frame rate expressed in hundredths of fps.
Accepted: `{2000, 2398, 2400, 2500, 2997, 5000, 5994, 11988}`. Observed under
emulation: `81`. The firmware is estimating image sizes to compute remaining
shots, is handed a movie-format record that was never populated, and asserts on
the unrecognised value.

**Root cause.** qemu-eos has no MPU spells for the 6D2 and falls back to the
generic set (`hw/eos/mpu.c:1245`, `hw/eos/mpu_spells/` stops at 700D-era
bodies). The properties that would populate the video-format record never
arrive, so the record contains unrelated data. The `[TA10] Irregular TotalSheets
0` warning is the same defect in a non-fatal spot — `PROP_AVAIL_SHOT` arrives
with an all-zero payload.

This promotes the `[MPU] FIXME: using generic MPU spells for 6D2` line from
"note but do not chase" (PLAN_OF_ACTION §2a lead 3) to **the** blocker. It is
not just a future GUI-navigation problem; it is what is failing now.

**Surprises**

1. The firmware never halted. It completes startup via Canon's error path
   (`ErrorSend (101, ABORT)`, `startupCompleteCallback 0x400000`). The "halts
   here" in PLAN_OF_ACTION §2a comes from reading only the serial log; the
   `-d debugmsg` stream continues well past it.
2. The FSU speed-class parameters *do* track the filesystem
   (`1 0 80 20 248` → `1 0 200 80 2044`), which made the card look causal right
   up until the no-card control fired the identical assert.
3. The assert is *absent* only when the card has no filesystem — the one
   configuration that looks like an improvement is the one that proves least.
4. Both `[SDIO] Error` and `[TA10] Irregular TotalSheets` are fully explained
   and neither is on the path to this assert.

**What would unblock it.** Real 6D2 MPU init spells, captured from the body
(`hw/eos/mpu_spells/make_spells.sh` + `extract_init_spells.py` consume a
DEBUGMSG log from the camera; `platform/6D2.111/Makefile` already has a
`CONFIG_STARTUP_LOG=y` build that hooks `DryosDebugMsg` and the MPU send/recv
rings for exactly this purpose, via `src/log-d678.c`). That is a
capture-on-hardware task, not an emulator-tuning task.

Two cheaper things worth trying first, both of which were **not** attempted here
because they require editing the upstream `qemu-eos` tree (out of scope per the
spike constraints) — described rather than applied:

- Add a `6D2` entry to `mpu_spells/` reusing the closest existing DIGIC 6/7-era
  spell set instead of `generic`, and see whether the video-format property
  starts arriving.
- Or, purely as a diagnostic, patch the emulated property response so `[r6+8]`
  lands on `2997`, and confirm the assert clears and boot proceeds. This would
  prove the causal chain end-to-end without needing a real capture.

Neither is a fix to ship; both are evidence-gathering steps that stay inside the
emulator.

**Reproduce**

    nix-shell "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/shell.nix"
    cd /home/chris/ml6d2/qemu-eos/magiclantern
    python3 run_qemu.py 6D2 -q /home/chris/ml6d2/qemu-eos-build

The no-card control is the fastest one-line confirmation: drop
`-drive if=sd,file=...` from the generated qemu command line and the assert
still fires.
