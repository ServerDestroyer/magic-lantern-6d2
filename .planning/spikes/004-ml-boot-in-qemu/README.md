---
spike: 004
name: ml-boot-in-qemu
type: standard
validates: "Given our built autoexec.bin, when loaded in qemu-eos alongside the 6D2 ROMs, then ML's own init runs and its stage of failure is identified"
verdict: VALIDATED
related: [001, 002]
tags: [qemu, ml-build, boot]
---

# Spike 004: Boot Our Own ML Build in QEMU

## What This Validates

**Given** the `autoexec.bin` we built from `platform/6D2.111`,
**when** it is loaded in qemu-eos alongside the real 6D2 ROMs,
**then** ML's own init code runs and we identify exactly how far it gets and
where it fails.

This is Phase A step 5 — the debug rig. It was previously assumed blocked on
"build ML first," but the build already exists:
`ml/platform/6D2.111/build/autoexec.bin` (243 KB, 1296 symbols in
`6D2_111.sym`), built 2026-08-15.

## Research

Depends on spike 001. Stock firmware currently halts at the `RscMgr` assert
before the GUI, so ML's boot may not be reachable until that clears. Two
possible outcomes, both useful:

- If ML loads before the assert point, we get ML-specific failure data now.
- If not, this spike is gated on 001 and says so explicitly rather than guessing.

Run this **after** 001 in the same session — both need exclusive use of the
emulator and the SD card image, so they must not run concurrently.

## How to Run

    nix-shell "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/shell.nix"
    cd /home/chris/ml6d2/qemu-eos/magiclantern
    python3 run_qemu.py 6D2 -q /home/chris/ml6d2/qemu-eos-build

with our `autoexec.bin` placed on the emulated card. For source-level debugging,
qemu's `-s -S` plus `arm-none-eabi-gdb` against `build/autoexec` (the unstripped
ELF) and `6D2_111.sym`.

## What to Expect

ML boot messages distinguishable from Canon's, or a clear statement that the
Canon assert fires first and gates this.

## Investigation Trail

Run after spike 001, same session, never concurrently.

### 1. Is this gated on spike 001? No — answer it up front

It is not. 001 established that the `RscMgr` / `EstimatedSize.c:1521` assert is
a *soft* failure (Canon's `ErrorSend (101, ABORT)` path, not a hang) and that it
is caused by qemu-eos having no 6D2 MPU spells, not by anything on the card.
More importantly, in the ML run below **the assert never fires at all**, because
ML stops the boot earlier than the point where Canon reaches the estimator.

So the dependency is the reverse of what was assumed: 004 does not wait on 001.

### 2. Getting `autoexec.bin` onto the emulated card

`make disk_image` (`platform/Makefile:169` → `create_disk_image_from_zip.py`)
requires `guestmount` from libguestfs, which is **not** in `shell.nix` or on this
system. Rather than add it, built the card with `mtools`, which needs no root
and no kernel mount:

- Base image is `ml/platform/sd.qcow2.xz` — the same one
  `create_disk_image_from_zip.py` uses. Unlike `qemu-eos/magiclantern/disk_images/sd.qcow2`,
  it already carries the card-side boot flags: FAT16 partition at LBA 99, with
  `EOS_DEVELOP` (volume label) and `BOOTDISK` (boot code, at offset 0x40 of the
  boot sector) both present. Verified before use; the boot sector was never
  touched afterwards.
- `mcopy -i <raw>@@50688` to install the contents of
  `platform/6D2.111/build/magiclantern.zip` (`autoexec.bin`, `ML/`,
  `ML-SETUP.FIR`), replacing the stale 25664-byte `autoexec.bin` the base image
  ships with.
- `qemu-img convert -O qcow2` back to a qcow2 for SD and CF.

Artefact under test (snapshotted into the spike's scratch dir first, because the
`ml/` tree was being rebuilt concurrently):

    autoexec.bin  244288 bytes  md5 6f6534f8dd9c30023675fa5df9020a33

Note the build was made with `CONFIG_STARTUP_LOG=y` — `Logging started.` in the
trace below comes from `src/log-d678.c:359`, which only compiles under that flag.

Camera-side bootflag comes from qemu, not the card: `-M 6D2,firmware=boot=1`
makes `eos.c:2136` write `0xFFFFFFFF` to `bootflags_addr + 4`. 6D2 has no
explicit `bootflags_addr` in `model_list.c` and inherits the DIGIC 7 default
`0xE1FF8000` (`model_list.c:578`) — which turns out to be correct, as the
bootloader trace proves.

### 3. Does the card boot? Yes, and it is demonstrably *our* binary

Serial output with `boot=1`:

    <<<<< Musa(PU0) Boot Ver 0.19 >>>>>
    BootLoad
    SLOT_A LOAD OK.
    Open file for read : AUTOEXEC.BIN
    File size : 0x3BA40
    Now jump to AUTOEXEC.BIN(0x00800000)!!
     K406 READY
    [STARTUP]
    K406 ICU Firmware Version 1.1.1 ( 6.4.9 )

`0x3BA40` = 244288 = the exact byte count of our `autoexec.bin`, so this is not
the stale one from the base image. `0x00800000` matches `AUTOEXEC_BASE` in
`platform/6D2.111/Makefile`. Canon's firmware banner appearing *after* the jump
means ML's D678 boot code relocated itself, patched the copied
`firmware_entry`/`cstart`, and handed control back — i.e. `boot-d678.c` works on
this body.

### 4. Does ML's own init run? Yes — it prints its own banner

Filtering the `-d debugmsg` stream for messages whose caller address is outside
ROM (ROM is `0xE0…`/`0xF0…`; ML relocates to `RESTARTSTART = 0xE0F90` and is
0x3BA40 long, so ML occupies roughly `0x000E0F90`–`0x0011C9D0`):

    init  0x0010179d  replacing task_dispatch_hook
    init  0x001017df  Logging started.
    init  0x0010180f  Magic Lantern 2026-08-15.6D2.111 (3f24042a4 dev)
    init  0x0010181d  Built on 2026-08-15 19:35:28 UTC by chris@legion

Resolved against `build/6D2_111.sym`:

    0x10179d -> boot_pre_init_task + 0x24     (src/init.c:636)
    0x1017df -> boot_post_init_task + 0x06    (src/log-d678.c:359)
    0x10180f -> boot_post_init_task + 0x36
    0x10181d -> boot_post_init_task + 0x44

That is unambiguous: ML installs its task-dispatch hook in `boot_pre_init_task`,
reaches `boot_post_init_task`, and prints its own version and build stamp. The
banner names our build (`chris@legion`, today's date), not a nightly.

### 5. Where it stops — and the control that proves it is a hang

Boot then stops progressing. Message counts over the same wall-clock window:

| run | debugmsgs | last Canon progress |
|---|---|---|
| stock card, `boot=0` | 1283 | full startup → DCF → `EstimatedSize` assert → `startupCompleteCallback` |
| ML card, `boot=0` (control) | 1283 | identical to stock — the ML files on the card change nothing when the bootflag is off |
| ML card, `boot=1` | **195** | `Startup: startupEntry` → `[PWM] PWM_Initialize` → `[ADC] InitializePollingADC` → `PowerMgr: GlobalVectorInit`, then nothing |

Everything the stock run does after `GlobalVectorInit` — ADC calibration,
`PROP_RegisterMultiConvert`, `ChangeAEMode`, the whole PropMgr/DCF sequence — is
never reached.

The trace tail shows both cores in a tight loop: repeated
`MRC p15,0,Rd,cr0,cr0,5: MPIDR_EL1_S` reads plus a continuous SGI 0xa
ping-pong between CPU0 and CPU1. Counting MPIDR reads across the whole run is
the control that turns "looks stuck" into evidence:

| run | MPIDR reads | PCs |
|---|---|---|
| stock `boot=0` | 9 | `0xE0007648`, `0xE0004900`, `0xE00076DA`, `0xE004000A` — all ROM, all boot-time core identification |
| ML card `boot=0` | 9 | same ROM addresses |
| ML card `boot=1` | **208** | `0x001037A8` ×181, `0x0010390C` ×12 — both inside ML's relocated image |

Nine reads in ROM is normal startup. 208 reads at two RAM addresses is a spin
loop, and it is at addresses that only exist when ML is loaded.

Dead ends and things deliberately not done: `make disk_image` (needs
libguestfs); rebuilding ML (the tree was being rebuilt by another task, so the
binary under test was snapshotted by md5 instead); and no source changes to
`ml/` or `qemu-eos/`.

## Results

**Verdict: VALIDATED.** Our `autoexec.bin` loads from the emulated card, ML's
own init runs, and the stage of failure is identified.

**What works**

1. Card build path without libguestfs — `mtools` + `qemu-img` against
   `ml/platform/sd.qcow2.xz`, which already carries `EOS_DEVELOP` + `BOOTDISK`.
2. qemu's `-M 6D2,firmware=boot=1` correctly sets the camera bootflag; the 6D2's
   inherited DIGIC 7 `bootflags_addr = 0xE1FF8000` is right.
3. The Canon bootloader finds and loads our binary — `File size : 0x3BA40`
   (244288) matches byte for byte, jumping to `0x00800000`.
4. `boot-d678.c` relocation and firmware-entry patching succeed on 6D2: Canon's
   firmware starts *after* ML has taken and returned control.
5. ML reaches `boot_post_init_task` and prints its own banner.

**Where it fails.** Immediately after the banner. Canon's startup sequence stops
at `PowerMgr: GlobalVectorInit` (195 debugmsgs vs 1283 for the same window
without ML) and both Cortex-A9 cores enter a spin at `0x001037A8` /
`0x0010390C`, repeatedly reading `MPIDR_EL1` and exchanging SGI 0xa. Both
addresses lie inside ML's relocated image; neither is executed at all in the
stock runs.

**Surprises**

1. **004 was never gated on 001.** The Canon `RscMgr` assert does not appear in
   the ML run — ML hangs well before Canon reaches the estimator. Spike 001's
   assert and this hang are independent failures on different code paths.
2. The ML card with `boot=0` produces a byte-for-byte equivalent boot to the
   stock card (1283 debugmsgs, same assert). ML files sitting on the card are
   inert without the camera bootflag, which is a useful clean control.
3. `platform/6D2.111/README.txt`'s "boots in qemu, but qemu doesn't get far for
   6D2" understates it in one direction and overstates it in another: ML's own
   code runs fine and self-identifies; it is the *handover back to Canon's
   multi-core startup* that fails.

**Caveat on attribution.** `0x001037A8` could not be tied to a specific ML
function with confidence. `build/6D2_111.sym` has only 1298 symbols and its
nearest preceding entry is `edmac_copy_rectangle_cbr_start + 0x1AF`, which over
that distance is not trustworthy. The unstripped `build/autoexec` ELF carries
only 57 symbols (link-time addresses based at `0x800000`, not the relocated
`0xE0F90` base), so it does not resolve it either. Resolving this properly needs
`build/autoexec.map`, or a gdb session breaking on the spin address.

Two readings remain open and this spike cannot separate them:

- an ML bug — `boot-d678.c` copies `firmware_entry`/`cstart` into its `_reloc`
  buffer, and the second core ends up executing that copy and never leaving it
  (the `MPIDR_EL1` reads are exactly what core-identity code in `cstart` does);
- or a qemu-eos gap in secondary-core startup that only ML's relocated copy
  exercises, since stock firmware runs the original code in ROM instead.

**Next step for this thread.** Break at `*0x001037A8` under
`arm-none-eabi-gdb` (qemu already supports it — `--gdb`, port 1234, used
successfully in spike 001), read the call stack and compare against the
`FIRMWARE_ENTRY_LEN` / `CSTART_LEN` region `boot-d678.c` copies. If the spin PC
falls inside `_reloc`, the copied-region length constants in
`platform/6D2.111` are the first thing to check.

**Reproduce**

    # build the card (mtools, no root)
    #   base: ml/platform/sd.qcow2.xz  (FAT16 @ LBA 99, EOS_DEVELOP + BOOTDISK set)
    #   install: platform/6D2.111/build/magiclantern.zip
    # then run with the camera bootflag on:
    nix-shell "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/shell.nix"
    cd /home/chris/ml6d2/qemu-eos/magiclantern
    python3 run_qemu.py 6D2 -q /home/chris/ml6d2/qemu-eos-build --boot

`run_qemu.py --boot` looks for `platform/6D2.111/build/sd.qcow2` and `cf.qcow2`,
so put the built image there under those names. Capture with `-d debugmsg` —
the serial log alone stops at the Canon banner and hides every ML message.

---

## 2026-08-15 (evening) — Track B follow-up: the "spin" was a misattribution; no ML boot bug

The planned gdb session was run, against **the exact binary from the table
above** (md5 `6f6534f8dd9c30023675fa5df9020a33`, recovered together with its
card images from the original session's scratch dir) and against a fresh plain
build. All work was done in a scratch tree, `/home/chris/ml6d2/scratch-ml-spike004`
(full copy of `ml/`), with a private qemu instance (own monitor socket, own
card images, `-gdb tcp::1244`) — the shared tree and shared monitor socket were
not touched.

### 1. The two "spin PCs" are log-d678.c's logger functions, not `_reloc`

Resolved by disassembling guest RAM over gdb and matching instruction-for-
instruction against source (this build has `CONFIG_STARTUP_LOG=y`, so
`src/log-d678.c` is compiled in — its **static** functions are invisible to
`6D2_111.sym`, which is why symbol resolution failed above; they live in the
sym-file gap between `edmac_copy_rectangle_cbr_start` 0x1035F9 and `log_start`
0x103A01):

| PC | actually is | proof |
|---|---|---|
| `0x001037A8` | `my_DebugMsg` (log-d678.c) — TB starting right after `blx cli_spin_lock` | contains the verbatim `mrs r3, CPSR; tst r3, #80; b.n <self>` dead-interrupt check, then `mrc p15,0,r3,c0,c0,5; and r3,#3` = the inlined `get_cpu_id()` for the `"[%d] "` prefix (log-d678.c:98) |
| `0x0010390C` | `pre_isr_log` (log-d678.c:233) | opens with `get_cpu_id()`, then the exact isr filter `bic r3,r0,#0x100; cmp #0x2A; movw r3,#0x147; cmp; cmp r0,#0x1B`, then the `mpu_send_ring_buffer` drain loop |
| `0x001039A0` | `post_isr_log` (log-d678.c:264) | `movw r3,#0x147; cmp r0,r3`, then `get_cpu_id()`, then the `mpu_recv_ring_buffer` drain |

The real `_reloc` buffer in this binary is at **0x15504C–0x15534C** (gdb
`find` over 0xE0F90–0x400000 for the words at ROM 0xE0040010 hits 0x15505C,
i.e. `_reloc+0x10`; `FIRMWARE_ENTRY_LEN` = 0x300). Nowhere near the "spin" PCs.

So the MPIDR reads were **per-event logger overhead** — one read per logged
DebugMsg (my_DebugMsg) plus one per interrupt (the pre/post ISR hooks, which
Canon calls on both cores; the source comment on `post_isr_log` even says
"this runs on both CPU cores"). They are a signature of a *working*
`CONFIG_STARTUP_LOG` boot, not of a hang: healthy full boots measured today
show 1700–3800 RAM-address MPIDR reads. The 208 in the original run was low.

### 2. The GlobalVectorInit stall did not reproduce — it is nondeterministic

Same `autoexec.bin`, same card qcow2 files, same `qemu-system-arm` (built
11:44, before the original 12:46 run — the qemu binary was never rebuilt):

| run | outcome |
|---|---|
| exact old binary, 4 runs | **4/4 full boots** — past GlobalVectorInit, through PropMgr to the known spike-001 soft assert (`ErrorSend (101, ABORT)`), ML `log_dump` task writes `DEBUGMSG.LOG` at t≈15 s |
| fresh plain build (no STARTUP_LOG, features.h as-is), 2 runs | 2/2 full boots, ML banner prints, no recurring RAM MPIDR reads at all |

Healthy boots carry only **7–12 `SGI 0xa` events total**. The original run's
"continuous SGI 0xa ping-pong" is therefore genuinely anomalous — but it was a
*lost-wakeup storm*, not a spin in ML code.

### 3. Verdict on the two open readings: both wrong as stated

- **ML `_reloc`/`cstart` bug — refuted.** The relocation demonstrably works:
  on every boot CPU0's early MPIDR trace hits `_reloc+0xA` and `_reloc+0xFC`
  (the copied `firmware_entry`/`cstart` identity checks), while **CPU1 executes
  the ROM originals** (`0xE004000A`, `0xE00400FC`): ROM `firmware_entry` reads
  MPIDR at 0xE0040014, a non-zero core branches at 0xE0040034 straight to ROM
  `cstart` 0xE00400FC, whose core≠0 path is `blx 0xE043A6D0` into ROM. CPU1
  never touches ML's copy, so `boot-d678.c`'s "our code only runs on CPU0"
  assumption holds on the 6D2.
- **"qemu-eos secondary-core gap that only ML's copy exercises" — refuted as
  stated.** CPU1 runs, and runs ROM code; ML's copy is not involved.

What remains is a **nondeterministic cross-core interrupt-delivery race in
qemu-eos** (reading (b) in spirit, but ML-independent — plausibly the same
defect class behind the Core-1 `EngInit` wall in `PU1_INVESTIGATION.md`):

- `hw/eos/eos.c:2825` — `static int iar = 0x20;` — a **single global IAR slot**
  shared by both CPUs' GIC CPU interfaces (`eos_handle_intengine_gic`, mapped
  for DIGIC 7 at 0xC1000000, `model_list` mmio entry at eos.c:557).
- `ICDSGIR` write (eos.c:2961 `case 0xf00`) sets the shared `iar` and raises
  `CPU_INTERRUPT_HARD` on the *other* CPU; a `GICC_IAR` read (eos.c:2854) by
  **either** CPU returns and consumes it — cross-consumption is possible.
- The Canon intengine model (eos.c:~2742, reads of 0xD4011000/0xD5011000) does
  `cpu_reset_interrupt(CURRENT_CPU, CPU_INTERRUPT_HARD)` unconditionally —
  the **same flag** the SGI path asserts, so acking a device interrupt can
  silently cancel a pending SGI.

A lost SGI 0xa during the CPU0↔CPU1 DryOS bring-up handshake — right where
CPU1 starts doing real task work (`GlobalVectorInit` is logged from CPU1) —
leaves one core waiting while its peer retries the kick: continuous SGI 0xa
ping-pong with zero forward progress. That is exactly the recorded stall
signature, and it is timing-dependent, hence unreproducible on demand.

### 4. Proposed qemu-side change (NOT applied — shared tree)

In `qemu-eos/hw/eos/eos.c`, `eos_handle_intengine_gic`:

1. Line 2825: `static int iar = 0x20;` → `static int iar[2] = {0x20, 0x20};`
2. `GICC_IAR` case (lines 2854–2891): read/clear `iar[current_cpu->cpu_index]`
   only.
3. `GICC_EOIR` case (line 2894): reset `iar[current_cpu->cpu_index] = 0x20;`.
4. `ICDSGIR` case (lines 2961–2984): write `iar[target]` where `target` is the
   CPU being interrupted (current code always interrupts the other core; keep
   that, but store the SGI number in that CPU's slot, not globally).
5. Harder, later: stop the Canon-intengine read path (eos.c:2742) from
   clearing `CPU_INTERRUPT_HARD` while that CPU still has a pending GIC SGI —
   needs a per-CPU pending flag; or adopt QEMU's `intc/arm_gic.c` outright, as
   the FIXME at eos.c:2813 already suggests.

This is a proposal only; validating it requires making the stall reproducible
first (e.g. stress-boot in a loop, or force adversarial vCPU scheduling with
`-accel tcg,thread=single` vs default MTTCG).

Scratch artifacts: the probe logs are preserved permanently in `evidence/`
(renamed `.log` → `.txt` because `.gitignore` ignores `*.log`):
`qemu-run-oldbin.txt`, `qemu-run-newbuild-control.txt`, `rep1..3.txt`,
`probe_oldbin.txt`. The full scratch tree
`/home/chris/ml6d2/scratch-ml-spike004/` (ml copy + builds + card images +
`old-bin/` with the exact spike-004 binary) is scheduled for deletion in the
2026-08-15 evening housekeeping pass — the analysis above and `evidence/`
are the durable record.

---

## 2026-08-15 (night) — re-run with real MPU spells: ML fully exonerated, the wedge is qemu-eos's global interrupt latch

Re-ran the boot now that `qemu-eos/hw/eos/mpu_spells/6D2.h` exists (27 856 bytes,
2026-08-15 18:48) and `qemu-system-arm` was rebuilt against it (same timestamp).
Binary under test: `platform/6D2.111/build/autoexec.bin`, 244 256 bytes,
md5 `8cf3bfa93848ba37b82c0ff16677f43f` (the rev-4 diagnostic build, 19:39).
Card rebuilt with the same mtools recipe as above; the bootloader confirms it:
`File size : 0x3BA20` = 244 256, `Now jump to AUTOEXEC.BIN(0x00800000)!!`.
Nothing in `ml/` or `qemu-eos/` was modified; all scratch lives outside both trees.

### 1. The stall is identical with and without ML — 5/5 runs, deterministic

Sampling both cores' registers over the qemu monitor every 5 s for 60 s:

| run | bootflag | log lines | task debugmsgs | CPU0 PC/PSR | CPU1 PC/PSR | last debugmsg |
|---|---|---|---|---|---|---|
| stock1 | boot=0 | 468 | 292 | `E02C6100`/`600000F3` | `E00D97E0`/`40000073` | `DbgMgr:e05eae1b [PM] Enable (ID = 10, cnt = 0/1)` |
| stock2 | boot=0 | 462 | 291 | same | same | same |
| ml1 | boot=1 | 495 | 295 | same | same | same |
| ml2 | boot=1 | 508 | 294 | same | same | same |
| ml3 | boot=1 | 497 | 295 | same | same | same |

Byte-identical stall state in every run. A `difflib` alignment of the stock1 and
ml1 debugmsg streams shows the only ML-attributable differences are ML's own
three messages (`replacing task_dispatch_hook` at `0x00101A31`, the version and
build-stamp lines at `0x00101A8D`/`0x00101A9B`), ML's relocation MMU/cache work
at `0x0083B3xx`/`0x000E7Axx`, and PM-counter interleaving noise. **ML gets three
messages further than stock, not less.** The `GlobalVectorInit` "stall point"
from the original session is reached in both cases and passed in both cases —
the boot now runs on through PropMgr, `ChangeAEMode`, the battery-report spells
and `nfcmgrstate_Initialize:ce_init` before wedging.

So the question this spike could not previously separate is settled by the
control: with `boot=0` there is no ML in the machine at all, and the machine
wedges in exactly the same place. **ML is not the cause.**

### 2. Where both cores actually are — symbolized

Both PCs are ROM, and both are one instruction past a `WFI`:

| core | PC | actually is |
|---|---|---|
| CPU0 | `0xE02C6100` | insn after the `WFI` at `0xE02C60FE`, inside the PowerMgr idle loop `0xE02C608E–0xE02C6106`. Identified by the two `DebugMsg` string literals it references: `0xE02C61D0` = `"[PM] pmSelfRefresh : In"`, `0xE02C61E8` = `"[PM] pmSelfRefresh : Out"`, and the task-name literal `"PowerMgr"` at `0xE02C6208`. PSR `600000F3` = svc, Thumb, I=1 F=1. |
| CPU1 | `0xE00D97E0` | `b.n 0xE00D97DE`, and `0xE00D97DE` is `WFI` (`bf30`) — a two-instruction `wfi; b .-2` park loop in the DryOS multicore support block that also contains `dcache_clean_multicore` (`0xE00D9CCC`, named in `platform/6D2.111/stubs.S:37`). PSR `40000073` = svc, Thumb, I=0 F=1. |

Both cores are halted waiting for an interrupt. Nothing in ML is executing; the
"spin PCs" of the original session (`0x001037A8` / `0x0010390C`, already refuted
as logger overhead) do not appear at all.

### 3. What they are waiting for — an interrupt that qemu-eos will never deliver again

Re-ran stock with `-d debugmsg,int,verbose`
(`evidence/2026-08-15-night-stockint.txt`). The interrupt timeline splits cleanly
in two at log line 438:

| window | interrupts delivered | interrupts refused |
|---|---|---|
| lines 0–437 | `0x1B` ×11, `0x11E` ×6, `0x12E` ×1, `0x16D` ×1 | 7 |
| lines 438–499 (60 s wall clock) | **0** | `0x28` ×60 |

`0x28` is `hptimer_interrupt` (`model_list.c:594` for the 6D2's DIGIC 7 entry).
After line 438 **not one interrupt of any id is ever delivered again** — the
machine's entire interrupt system is dead, which is exactly why both cores sit in
`WFI` forever.

The last three events before the death, in order, are the cross-core handshake:

    line 422  0xe00d9c61: cpu 0 sending SGI 0xa      <- inside the dcache_clean_multicore block
    line 427  0xe026aaa5: cpu 0 ack SGI 0x0, iar: 0xa
    line 428  0xe0004d37: cpu 1 ack SGI 0x0, iar: 0xa

Both cores read `GICC_IAR` and **both were handed the same `iar` value 0xa** —
the single global latch — and the code path each read takes clears
`CPU_INTERRUPT_HARD`.

### 4. Root cause (qemu-eos, `hw/eos/eos.c`) — confirmed, high confidence

Three single-CPU assumptions in a two-CPU machine compound:

1. `eos_state->irq_id` is one global latch. `eos_trigger_int` (line 2436) refuses
   to deliver *anything* while it is non-zero:
   `if(!delay && irq_enabled[id] && !eos_state->irq_id)`.
2. `irq_id` is cleared only when the guest reads the interrupt-reason register
   (`0xD4011000`, line 2741) — and that same read does
   `cpu_reset_interrupt(CPU(CURRENT_CPU), CPU_INTERRUPT_HARD)` (line 2742).
3. The GIC SGI path shares that very flag and also has a single global `iar`
   (`static int iar = 0x20;`, line 2825). A `GICC_IAR` read clears
   `CPU_INTERRUPT_HARD` on the reading core (lines 2878–2882).

Delivery targets `CPU(CURRENT_CPU)` (lines 2443 and 1004) — whichever vCPU
happened to be executing when the device fired, not the core that owns the
interrupt (`CURRENT_CPU` is `eos_state->cpus[current_cpu ? current_cpu->cpu_index : 0]`,
`eos.h:60`).

Failure sequence, matching the measured trace line for line: a device interrupt
is latched into the global `irq_id` and `CPU_INTERRUPT_HARD` is raised on some
core; before that core takes it, the `dcache_clean_multicore` SGI 0xa handshake
runs and that core reads `GICC_IAR`, whose handler clears `CPU_INTERRUPT_HARD`.
The device interrupt is now invisible to the core, so the reason register is
never read, so `irq_id` is never cleared — and condition (1) refuses every
subsequent interrupt for the rest of the run. Both cores idle into `WFI` and the
emulated camera is dead. This is the same defect class the evening session
predicted from code reading; the `-d int` trace is the direct measurement.

### 5. Sketched fix (NOT applied — `qemu-eos/` is shared)

Smallest change that should clear this wedge, in `eos_handle_intengine_gic`,
`GICC_IAR` read case (eos.c:2873–2883): after clearing `CPU_INTERRUPT_HARD` for
the SGI ack, re-assert it on that same core when a device interrupt is still
latched —

    if (eos_state->irq_id) {
        cpu_interrupt(CPU(current_cpu->cpu_index ? eos_state->cpu1
                                                 : eos_state->cpu0),
                      CPU_INTERRUPT_HARD);
    }

That restores the dropped wake without touching the interrupt model's structure.
The structural fixes behind it, in increasing cost: make `iar` per-CPU
(`static int iar[2]`, indexed by `current_cpu->cpu_index`, cleared per-CPU in
`GICC_EOIR`); make `irq_id` per-CPU and deliver to the owning core instead of
`CURRENT_CPU`; or replace the hand-rolled GIC with QEMU's `intc/arm_gic.c`, as
the FIXME at eos.c:2813 already says.

Verification is now cheap: the wedge is 5/5 deterministic, so a fixed build
either passes `nfcmgrstate_Initialize:ce_init` or it does not.

### 6. Side observation on the boot ceiling

The archived pre-spells qemu log `tools/6D2-startup-qemu.txt` has 1 339 messages
and reaches `startupCompleteCallback` and the `EstimatedSize` assert. Today's
runs stop at ~292 messages. This is **not** a like-for-like regression: with real
spells the guest receives real property values and takes a different code path
(`ChangeAEMode`, `propst_ChangeAEMode`, `ReqChangeCBR`, the NFC/CE bring-up)
that the pre-spells run never entered. What is fair to say is that the current
tree's 6D2 boot ceiling is `nfcmgrstate_Initialize:ce_init`, and that ceiling is
set by the interrupt bug above, not by missing spells and not by ML.

**Reproduce**

    # card: mtools recipe from section 2 above, using the current magiclantern.zip
    # harness: QemuRunner, model 6D2, d_args=["debugmsg"] (add "int","verbose" for
    #   the interrupt timeline), boot=True/False, monitor "info registers -a"
    #   sampled every 5 s.  Note: the monitor socket path must be < 108 bytes.

Evidence added this session: `evidence/2026-08-15-night-stockint.txt` (the
`-d int` run), `evidence/2026-08-15-night-runs.txt` (the 5-run summary table and
register samples).
