# PR Q2 — qemu-eos: 6D2 (DIGIC 7) MPU init spells, and a wrong `assert_log` address

- **Target repo:** `reticulatedpines/qemu-eos`
- **Target branch:** `qemu-eos-v4.2.1` (based on `4b667a1d3c`, the local clone's HEAD)
- **Source branch:** none yet, by design — no branch was created inside the shared
  `qemu-eos/` clone, which holds live uncommitted work from several sessions.
  Commands below build the branch from the patch file.
- **Files:** `hw/eos/mpu_spells/6D2.h` (new, 272 lines), `hw/eos/mpu.c` (+2),
  `magiclantern/cam_config/6D2/debugmsg.gdb` (1 line changed, +7 comment)
- **Patch file:** `.planning/prs/PR-Q2-qemu-6D2-mpu-spells.patch`
  (verified to apply cleanly to a `git archive HEAD` extraction)
- **Commits:** 2

## Titles

```
mpu_spells: add 6D2 (DIGIC 7) init spells captured from the body
```
```
6D2: fix the assert_log breakpoint address in debugmsg.gdb
```

## PR body (ready to paste)

```markdown
This adds the first MPU init spell set for a DIGIC 7 body, captured from a real
EOS 6D Mark II (firmware 1.1.1), and fixes a wrong breakpoint address in the
6D2's `debugmsg.gdb`.

## 1. The spells

### The failure they fix

`hw/eos/mpu_spells/` currently stops at 700D-era bodies, so `mpu.c` prints

    [MPU] FIXME: using generic MPU spells for 6D2.

and replays the generic set. On the 6D2 that is not a cosmetic FIXME — it kills
the boot:

    [FSU] AllocateMemoryStrictly For Speed Class!!!
    RscMgr  ASSERT : Resource/./EstimatedSize.c, Task = RscMgr, Line 1521 / FALSE
    PropMgr startupErrorRequestChangeCBR : ErrorSend (101, ABORT)
    FileMgr [STARTUP]startupCompleteCallback 0x400000

`GetEstimatedSize()` at ROM `0xE0202312` loads a frame rate in hundredths of fps
(`ldr r0,[r6,#8]` at `0xE0202372`) and switches on it against exactly eight legal
values — 2000, 2398, 2400, 2500, 2997, 5000, 5994, 11988 — falling through to
`ASSERT(FALSE)` at `0xE0202480` (`movw r2, #1521`). Under the generic spells that
field holds **81** (`0x51`), because no spell ever populates the movie-format
record; verified in gdb (`r6 = 0x221228`, and the neighbouring words are
`0x8000003B` / `0x8000003F`, i.e. DIGIC 6/7 property ids — so the estimator is
dereferencing a record that was never filled). 200D's `patches.gdb` records the
identical value: *"strange values passed in, 0x51"*.

The same defect shows up non-fatally elsewhere: `PROP_AVAIL_SHOT` arrives with an
all-zero payload, which is where `[TA10] ERROR Irregular TotalSheets 0 !!` comes
from.

Everything else was ruled out first. The assert was reproduced across eight SD
configurations — 248 MiB / 512 MiB / 2 GiB / 8 GiB / 32 GiB containers, freshly
built FAT16 248 MiB and FAT32 2 GiB / 8 GiB filesystems, an unformatted card —
and byte-identically **with no SD drive on the command line at all**. An assert
that fires when there is no card in the machine is not a card problem. The four
`[SDIO] Error` lines were also ruled out (they are CMD0 / CMD52 / CMD5 no-response
probes classified as errors by `sdio_send_command`; card init succeeds).

### How the spells were captured

Not from the emulator — that would be circular, since the emulator is replaying
the generic set. From the body:

1. An ML build for `platform/6D2.111` with `CONFIG_STARTUP_LOG=y`, which hooks
   `DryosDebugMsg` and the MPU send/receive rings via `src/log-d678.c` and writes
   `DEBUGMSG.LOG` to the card.
2. One boot on the body. Result: 522 KB, 6530 messages, **0 dropped**
   (`drop_nobuf=0`, `drop_full=0`), 71 `mpu_send` + 104 `mpu_recv`.
3. `hw/eos/mpu_spells/extract_init_spells.py` — this repository's own extractor,
   unmodified except for the `ML_PLATFORM_DIR` fix submitted separately.

The result is **69 request spells carrying 117 replies** (272 lines), with
decoded property names on most of them.

### One hand edit, and why

The extractor drops replies whose spell has `num > 1`. That rule discarded the
Mode-group reply `94 93 02 0e …` (property `0x80000001`) from spell #5. The guest
needs it: without it the ICU never emits the `02 0e` acknowledgement that gates
spells #6 onward, and the boot ceilings out ~1100 messages early. It is
uncommented by hand in `6D2.h` with a comment saying so. This is a bug in
`extract_init_spells.py`'s heuristic, not in the capture; it is left as an
explicit hand edit rather than silently changing the extractor.

A second, strictly additive merge appends 13 movie-mode replies (from a second
body capture in movie mode) to existing photo-mode entries, matched by request
spell. No new request entries were added, no environmental or noise replies
(temperature, battery, GPS, shot counter), and the mode selectors
(`PROP_FIXED_MOVIE`, `PROP_LIVE_VIEW_MOVIE_SELECT`) keep their photo values, so
QEMU still boots as photo mode.

### Measured result

Stock 6D2 firmware, headless, 120 s, `-d debugmsg`, **no gdb script attached**:

| | generic spells (before) | 6D2 spells (this PR) |
|---|---|---|
| `ASSERT` / `Irregular TotalSheets` / `ErrorSend` | present | **0** |
| startup completion flag | `startupCompleteCallback 0x400000` (Canon's `ErrorSend (101, ABORT)` error path) | **`startupCompleteCallback 0x10`** → `[SEQ] NotifyComplete (Startup, Flag = 0x10)` |
| stderr lines | boot ends in the error path | **1582** |
| unique message texts | — | 1019 |
| last progress | — | `NFCMgr nfcmgrstate_Initialize ce_init`, then RTCMgr I2C / DbgMgr PM housekeeping |

The startup flag changing from `0x400000` to `0x10` is the substantive result:
the firmware now completes startup normally instead of aborting.

Five `[MPU] warning: non-empty spell #N has duplicate(s)` lines appear. They are
benign — `mpu_interpret_command()` resumes matching from the previous spell, so
duplicate pairs are consumed in order.

## 2. The `assert_log` address

`magiclantern/cam_config/6D2/debugmsg.gdb` ships

    b *0xE06170EC
    assert_log

`0xE06170EC` is **mid-instruction inside AES S-box lookup code**:
`0xE06170E0`–`0xE06170FE` disassembles as `ubfx` / `ldrb rN,[r2,rN]` / `lsls` /
`orr`, a byte-table shuffle. Nothing has ever been assert-logged for this camera.

The real handler is `0xE0617620`: standard prologue, loads the handler pointer
stored at `0x4000`, tail-calls it (`bx r3`). Signature
`assert(r0 = expr string, r1 = file string, r2 = line number)`, confirmed against
the call site at `0xE020248C`, which sets `r2 = 1521` and ADRs both strings.
Verified by disassembling both addresses.

## What is NOT claimed

- **Magic Lantern itself does not boot under emulation.** With our `autoexec.bin`
  on the card and `boot=1`, ML's own init runs and prints its banner from
  `boot_post_init_task`, then both cores spin at `0x001037A8` / `0x0010390C`
  inside ML's relocated image (208 `MPIDR_EL1` reads versus 9 for a stock boot).
  This PR does not change that, and does not claim to.
- **The GUI is not reached.** Boot now stalls at `NFCMgr
  nfcmgrstate_Initialize ce_init` → `ERROR [I2C] I2C_Read[CH3] : 0xa8,…`. The
  remaining candidates are the unmodelled DIGIC 7 I2C block and the SD/CSMgr
  event chain; neither is investigated here.
- **The movie-mode replies are coverage, not verified behaviour.** The ICU never
  issues those requests before the current stall, so they are not exercised.
- **One body, one firmware version.** Captured from a single EOS 6D Mark II on
  1.1.1. The spell set has not been checked against another 6D2.
- The two trailing-whitespace warnings `git apply` reports on commented-out
  lines in `6D2.h` are `extract_init_spells.py` output format, identical to
  what `5D3.h` already carries.

## Provenance and content of `6D2.h`

The file contains MPU↔ICU bus traffic recorded from a camera, converted by this
repository's own extractor — the same category of data as the 14 spell files
already in `hw/eos/mpu_spells/`. It contains no ROM bytes and no firmware code.

Like several existing files it embeds a `PROP_LENS_NAME` string for whatever lens
was mounted (`TAMRON SP 24-70mm F/2.8 Di VC USD G2 A032`; compare
`$EF-S18-55mm f/3.5-5.6 IS STM` in `100D.h`/`EOSM2.h`, `$EF-S24mm f/2.8 STM` in
`5D3.h`) and an `LP-E6` battery record with a pack identifier (compare the same
record in `5D3.h`, `60D.h`, `6D.h`). The GPS records are all-zero apart from the
`WGS-84` datum constant — no coordinates. No body serial number is present; the
MPU bus does not carry it.
```

## Suggested commit messages

```
mpu_spells: add 6D2 (DIGIC 7) init spells captured from the body

hw/eos/mpu_spells/ stops at 700D-era bodies, so the 6D2 falls back to
mpu_init_spells_generic. That is not cosmetic: the generic set never
populates the movie-format record, GetEstimatedSize() (ROM 0xE0202312)
reads 81 instead of one of {2000,2398,2400,2500,2997,5000,5994,11988}
and the boot dies at ASSERT(FALSE) "Resource/./EstimatedSize.c" line
1521, task RscMgr, taking Canon's ErrorSend (101, ABORT) path.

Ruled out first: eight SD card configurations (248MiB..32GiB containers,
fresh FAT16/FAT32 filesystems, unformatted, and no SD drive at all) all
produce the identical assert.

Captured from a real 6D2 on firmware 1.1.1 with an ML CONFIG_STARTUP_LOG
build (src/log-d678.c) -- 6530 messages, 0 drops, 71 mpu_send +
104 mpu_recv -- and converted with this repo's own
extract_init_spells.py -- 69 request spells carrying 117 replies.

One hand edit: extract_init_spells.py drops replies from spells with
num > 1, which discarded the Mode group reply 94 93 02 0e (prop
0x80000001). The guest needs it to emit the 02 0e ack that gates spell
#6 onward; it is uncommented with a comment saying so.

Measured, stock firmware, 120s, -d debugmsg, no gdb attached: zero
ASSERT / Irregular TotalSheets / ErrorSend, 1582 stderr lines, and
startup now completes normally -- startupCompleteCallback 0x10 and
[SEQ] NotifyComplete (Startup, Flag = 0x10), where the generic spells
gave 0x400000 via the error path.

Not claimed: ML itself still does not boot under emulation, and the
stock boot now stalls later, at NFCMgr nfcmgrstate_Initialize ce_init /
I2C_Read[CH3], which is a separate unmodelled DIGIC 7 I2C block.
```

```
6D2: fix the assert_log breakpoint address in debugmsg.gdb

cam_config/6D2/debugmsg.gdb breaks at 0xE06170EC, which is
mid-instruction inside AES S-box lookup code (0xE06170E0-0xE06170FE is
ubfx / ldrb rN,[r2,rN] / lsls / orr). Nothing was ever assert-logged for
this camera.

The real handler is 0xE0617620: standard prologue, loads the handler
pointer at 0x4000, tail-calls it (bx r3), signature
assert(r0 = expr str, r1 = file str, r2 = line). Confirmed against the
call site at 0xE020248C, which sets r2 = 1521 and ADRs both strings.

Verified by disassembling both addresses.
```

## Deliberately excluded (do not add when posting)

The **EstimatedSize breakpoint workaround** from local patch `0004b`
(`b *0xE0202374` forcing `r0 = 0x7D0`) is not in this PR and must not be added
to it. It was scaffolding for the period when the illegal frame rate had no
known cause. The spells in this PR remove the cause: measured today, a 120 s
stock boot with these spells and no gdb script produces zero `EstimatedSize`
hits in 1582 lines. Shipping the workaround now would silently force a legal
frame rate for anyone who regenerates or edits `6D2.h`, turning a loud `ASSERT`
into a quiet wrong value.

Also excluded: the 522 KB source capture `tools/6D2-DEBUGMSG-body.txt`, the
archived header `tools/6D2_spells_body.h`, and the three untracked files another
workstream left in the clone (`magiclantern/cam_config/named_functions.idc`,
`magiclantern/cam_config/state_objects.py`, `magiclantern/test_00.png`).

## Exact commands for Chris (branch + push)

```sh
cd "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/qemu-eos"

# Do NOT branch inside this clone while another session is mid-task.
# Work in a throwaway clone instead -- nothing here touches the shared tree:
git clone --no-hardlinks . /tmp/qemu-eos-pr-q2
cd /tmp/qemu-eos-pr-q2
git checkout -b 6d2-mpu-spells 4b667a1d3c

git apply "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/prs/PR-Q2-qemu-6D2-mpu-spells.patch"

# commit 1 -- the spells
git add hw/eos/mpu_spells/6D2.h hw/eos/mpu.c
git commit -F - <<'EOF'
<paste the first commit message above>
EOF

# commit 2 -- the assert_log fix
git add magiclantern/cam_config/6D2/debugmsg.gdb
git commit -F - <<'EOF'
<paste the second commit message above>
EOF

git remote add fork git@github.com:<YOUR_GITHUB_USER>/qemu-eos.git
git push fork 6d2-mpu-spells

gh pr create --repo reticulatedpines/qemu-eos \
  --base qemu-eos-v4.2.1 --head <YOUR_GITHUB_USER>:6d2-mpu-spells \
  --title "6D2: add DIGIC 7 MPU init spells captured from the body" \
  --body-file <(sed -n '/^```markdown$/,/^```$/p' \
      "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/prs/PR-Q2-qemu-6D2-mpu-spells.md" \
      | sed '1d;$d')
```
