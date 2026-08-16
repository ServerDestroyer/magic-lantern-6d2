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

## GIC fix applied + partial result (2026-08-15 night, main session)

Applied the minimal re-assert from the agent's sketch (`patches/0008-qemu-eos-
gic-pending-irq-fix.patch`, in GICC_IAR read: re-raise CPU_INTERRUPT_HARD when
`irq_id` still latched). Measured effect: the permanent interrupt refusal is
GONE — `-d int` now shows `trigger int 0x28` (hptimer) flowing continuously
after the SGI handshake, where the pre-fix trace had 60 consecutive refusals
and zero deliveries. Boot still stalls at the same `DbgMgr [PM] Enable` point
(473 stderr lines) — but with live interrupts, the remaining stall is most
plausibly the missing GUI-stage MPU dialogue (no 6D2 button codes, one unknown
reply `08 06 01 a7 00 01`), not the GIC. Next lever: capture a LONGER body
startup log (bigger CONFIG_STARTUP_LOG buffer or later dump) to harvest the
GUI-stage spells, and/or make_button_codes for the 6D2. The agent's structural
follow-ups (per-CPU iar/irq_id or adopting intc/arm_gic.c) remain open.

## BREAKTHROUGH 2026-08-15 night: stock 6D2 firmware now COMPLETES STARTUP in QEMU

Boot progress went from **473 → 1581** stderr lines (3.3x) after two changes:

1. **The gating spell defect (spike 005 gui-stage-gap-analysis, verified):** the
   extractor's `num > 1` rule had commented out the Mode group reply
   (`94 93 02 0e ...`, property 0x80000001) in `mpu_spells/6D2.h` spell #5.
   Without it the guest never emits the `08 06 00 00 02 0e 00 00` ack that gates
   spell #6 onward. Un-commented by hand with a provenance note.
2. **6D2 button codes** (spike 009) — statically decoded from ROM0, no Unicorn
   and no body run needed. Landed into `button_codes.h` + `MPU_BUTTON_CODES(6D2)`.
   NOTE: mpu.c's key_map check `exit(1)`s on any gui_code missing from the table;
   the 6D2 has no physical zoom-out button, so the internal switch 0x0A codes
   (same numbering as the 200D, confirmed present in our ROM decode) are supplied.
   Landing the table without them made qemu exit at startup — a real trap.

Boot now reaches: `GISS_Initialize : End`, `GIS_Initialize : End`,
`[STARTUP]startupCompleteCallback 0x10`, `[SEQ] NotifyComplete (Startup, Flag =
0x10)`, then RTCMgr/I2C traffic. Zero ASSERT / Irregular TotalSheets / ErrorSend.

Also landed this wave: the **per-core interrupt fix** (patch 0008) — the 6D2 has
a two-level architecture (one GIC carrying 4 INTIDs plus TWO per-core Canon
controllers at 0xD4011000/0xD5011000, the core-1 bank never decoded by qemu-eos).
Core 1 now receives its own interrupts for the first time (0 → 6520 IRQ
exceptions in 60 s), verified independently. That fix alone did NOT move the boot
ceiling — the spell defect was the real gate — but the interrupt system is now
measurably healthy on both cores, which retires it as a suspect.

---

## ML boot retest (post-breakthrough) — 2026-08-15 night, second pass

Re-ran the whole thing now that stock firmware completes startup. Binary under
test: `platform/6D2.111/build/zip/autoexec.bin`, **244 256 bytes**, md5
`8cf3bfa93848ba37b82c0ff16677f43f` (rev-4 diagnostic build, 19:39; note this is
0x3BA20, not the 0x3B8A0 quoted in the task brief). Card built with the mtools
recipe from section 2 (base `ml/platform/sd.qcow2.xz`, boot sector verified to
carry `EOS_DEVELOP` @0x2B and `BOOTDISK` @0x40 before and after insertion).
Nothing in `ml/` or `qemu-eos/` was modified or rebuilt; all scratch outside both
trees.

### 1. ML loads, relocates, and runs — confirmed byte-exact

Serial with `boot=1`:

    <<<<< Musa(PU0) Boot Ver 0.19 >>>>>
    BootLoad
    SLOT_A LOAD OK.
    Open file for read : AUTOEXEC.BIN
    File size : 0x3BA20              <- 244 256, exact match
    Now jump to AUTOEXEC.BIN(0x00800000)!!
     K406 READY
    [STARTUP]
    K406 ICU Firmware Version 1.1.1 ( 6.4.9 )

Canon's banner printing *after* the jump proves `boot-d678.c` relocation and
firmware-entry patching still work. ML's own three messages appear in the
debugmsg stream (callers outside ROM, resolved against `build/magiclantern`,
which is linked at RESTARTSTART `0xE0F90` — so sym/ELF addresses are already
runtime addresses, **bias = 0**):

    00101a31  replacing task_dispatch_hook   -> boot_pre_init_task+0x24  (init.c:636)
    00101a8d  Magic Lantern 2026-08-15.6D2.111 (3f24042a4 dev)  -> boot_post_init_task+0x20 (init.c:672)
    00101a9b  Built on 2026-08-16 02:39:10 UTC by chris@legion  -> boot_post_init_task+0x2e (init.c:677)

### 2. Control vs ML, same session, same 150 s, `-d debugmsg`

| run | bootflag | stderr lines | Canon startup markers | last messages |
|---|---|---|---|---|
| stock (control) | boot=0 | **1558** | `startupCompleteCallback 0x10`, `[SEQ] NotifyComplete (Startup, Flag = 0x10)` | RTCMgr/I2C + PM Enable/Disable churn |
| ML card | boot=1 | **1608** | identical, same line positions +46 | identical tail, byte for byte |

ML is **+50 lines ahead**, not behind: its own 3 messages plus MPU/PM
interleaving. Canon's startup still reaches `[SEQ] NotifyComplete (Startup,
Flag = 0x10)` with ML present. (The 1558 vs the earlier session's 1581 is card
content + run jitter, not a regression — the tail is identical.)

### 3. Exactly where ML stops — measured with gdb, not inferred

`boot_post_init_task` (0x101a6c) after the banner is one merged poll loop:

    101ab6  ldr r3,[0x000100b8]   ; _rgb_vram_info  (Canon global, stubs.S:256)
    101abc  ldr r3,[0x0015682c]   ; rgb_vram_info   (ML global)
    101aee  msleep(100) ; b 101ab6
    101ad8  task_create("ml_init", 0x1e, 0x4000, my_big_init_task, 0)   <- init.c:729

Attached gdb (qemu started without `-S`, `-gdb tcp::1244`, attached after the
boot settled) with four breakpoints; ran 8 continues:

| breakpoint | source | hits |
|---|---|---|
| `*0x101ab6` | `rgb_vram_preinit`, bmp.h:70 | **4** |
| `*0x101aee` | `msleep(100)`, init.c:713 | **4** |
| `*0x101ad8` | `task_create("ml_init")`, init.c:729 | **0** |
| `*0x1017c6` | `my_big_init_task`, init.c:413 | **0** |

At every hit: `_rgb_vram_info` @0x100b8 = `0x00000000`, ML's `rgb_vram_info`
@0x15682c = `0x00000000`.

**ML's stopping point is `while (!rgb_vram_preinit()) msleep(100);`,
src/init.c:712–713.** ML is alive and looping at 10 Hz, waiting for Canon to
publish the RGBA GUI surface (`struct MARV *`). `my_big_init_task` never starts,
so there is no `_mem_init`, no `_find_ml_card`, no file I/O, **no GUI, no menu**.

Corroborating: after qemu exited, the card image contains no `ML/LOGS` at all
(`mdir -i card.img@@50688 ::/ML/LOGS` → "File not found"), so `RAWDIAG.LOG`
captured nothing — expected, since `diag_log` lives in `src/exmem.c:211` /
`mlv_lite.c:391`, both far downstream of `my_big_init_task`. This build also has
`CONFIG_STARTUP_LOG` **off** (no `Logging started.` message), so there is no
startup log either.

### 4. Why `_rgb_vram_info` is never written — Canon's startup sequencer stalls

`[SEQ] CreateSequencer (Startup, Num = 6)`. Stage progression in the plain
(TB-chained) run, identical stock and ML:

    stage 0: 0x10000 (init) 0x2000000 (RomRead) 0x8000 (SFRead)   -> seqEventDispatch 0
    stage 1: 0x2 (PowerMgr)                                       -> seqEventDispatch 1
    stage 2: 0x20000000 (Startup) 0x20000 (RscMgr) 0x10 (FileMgr) -> 0x400000 STILL OUTSTANDING

`seqEventDispatch (Startup, 2)` never fires, so stages 3–5 never run — and the
GUI/WINSYS bring-up that writes `_rgb_vram_info` (stubs.S:256: "written to in
InitializeScreen"; ROM literal-pool refs to 0x000100B8 at 0xE0885ADC, 0xE088656C,
0xE0886FFC, 0xE08B9D4C, 0xE08BA7DC) is behind it.

Flag 0x400000 identified statically. `startupCompleteCallback` = **0xE0042CCC**
(prologue `push {r4,lr}`; the logged `e0042cd9` is its DebugMsg return address;
tail-calls NotifyComplete at 0xE00491E8). ROM0 has exactly one direct `BL` to it
(0xE0041CC2, hardcoded 0x20000000) and four literal-pool copies of `0xE0042CCD`;
the one at 0xE00423E8 is consumed at:

    e0042024  ldr r0,=0xE0042CCD          ; startupCompleteCallback
    e0042026  mov.w r1,#0x400000
    e004202a  bl 0xE0658104               ; FM_Prepare  (error string 'FM_Prepare (%#x)' @0xE00423EC,
                                          ;  asserts against './FileMgr/FileMgr.c')

So **0x400000 = FileMgr's `FM_Prepare` completion**. FileMgr's last forward
progress in the chained run:

    fmPrepare -> @FileMgr FIO_Init(25,28,...) -> CSMGR_Initialize
      -> InitializeLogicalStorage: LStorageList = NULL -> SocketServiceInstall: SUCCESS
      -> FIO_GetSupportedDriveInfo -> InitializeSDDriver     <- last message, then nothing

`-d sdcf,verbose` over a full run: **zero** SDIO/CF controller lines. The SD
driver writes an undecoded MMIO block at 0xD2090600–0xD209064C / 0xD209F218–
0xD209F224 / 0xD209B140 (qemu-eos prints these as `[DIGIC6] ??? `; the modelled
SDIO handlers are at 0xC0C0xxxx / 0xC805xxxx / 0xD074xxxx / 0xD2B1xxxx, none of
which the 6D2 touches).

### 5. The FileMgr stall is a *timing race*, not a missing device — `-d nochain` clears it

Discovered by accident while capturing an `-d io` trace (`io` implies
`CPU_LOG_TB_NOCHAIN`, util/log.c:280). Isolated with `nochain` alone:

| run | flags | debugmsgs | how far |
|---|---|---|---|
| stock 150 s | `debugmsg` | 1558 | stage 2, 0x400000 outstanding |
| ML 150 s | `debugmsg` | 1608 | same |
| stock 40 s | `debugmsg,io` | 2721 | **stage 3**, gyro wait |
| stock 150 s | `debugmsg,nochain` | 4770 | **stage 3**, gyro wait |
| ML 150 s | `debugmsg,io` | 4758 | **stage 3**, gyro wait |
| ML 150 s | `debugmsg,nochain` (+gdb) | 4708 | **stage 3**, gyro wait |

With TB chaining disabled the guest runs slower and FileMgr completes:
`startupCompleteCallback 0x400000` → `NotifyComplete (Cur = 2, 0x400000, Flag =
0x400000)` → `seqEventDispatch (Startup, 2)` → `startupPrepareCapture`,
`WaitPU1 TimeOut`, `[MNAV] MEMNAVI_Initialize`, EventMgr multicast registration,
`ShootCapture scsInit`, `InitializeHeadControl`, `startupCompleteCallback
0x80000` (`SBS_Initialize`), `NotifyComplete (Cur = 3, 0xc0000, ...)`.

### 6. New ceiling at the deeper boot — a Core-1 lock assert, same with and without ML

Immediately after stage 3 opens, in both stock and ML runs:

    [CPU1] Startup:e0040efd  ASSERT : SystemIF::KerRLock.c, Task = ShtCap
    [CPU1]                   ASSERT : Core 1
    [CPU1]                   ASSERT : Line 205
    [CPU0] PropMgr:e0041481  startupErrorRequestChangeCBR (0x1d)
    [CPU0] PropMgr:e00414b3  startupErrorRequestChangeCBR : ErrorSend (101, ABORT)
    ... then, ~80 gyro ticks later ...
    [CPU0] ShootCapture:e0040efd ASSERT : ./Shoot/ShtPath/ShtCapturePath/ShtCapturePath.c, Task = ShootCapture
    [CPU0]                       ASSERT : Core 0, Line 154

`SCS_Initialize` (registered at 0xE0042104 with flag **0x40000**, error string
`'SCS_Initialize (%#x)'` @0xE0042460) therefore never completes, stage 3 hangs
with 0x40000 outstanding, and the run degenerates into the `Panning: WAIT AUTO
GYRO OFFSET` / `PowerMgr: GyroOffsetTimerCBR(n)` pair repeating forever (854 of
each in the last 1700 messages of a 60 s run) — the only remaining activity.

ML is present for none of this: with `boot=0` there is no ML in the machine and
the assert, the flag, and the gyro loop are identical.

### 7. Verdict

- **ML boots further than ever measured and is not the limiter.** Loads
  (0x3BA20 exact), relocates, hooks task dispatch, prints its banner, and parks
  in a legitimate wait for Canon's GUI surface. Zero ML-attributable failures.
- **ML does NOT reach GUI/menu**, and cannot until Canon's startup sequencer
  gets past stage 2 (chained) / stage 3 (nochain), because
  `_rgb_vram_info` is written by the WINSYS/`InitializeScreen` stage that lives
  behind those gates.
- Every prior attribution to ML in this spike is now retired: the original
  "spin PCs" (logger overhead), the `_reloc`/`cstart` theory (refuted), and the
  "GlobalVectorInit stall" (long since passed).

### 8. Next levers, in order

1. **`SystemIF::KerRLock.c:205` assert on Core 1 (`ShtCap`).** This is the hard
   gate on 0x40000/`SCS_Initialize` and therefore on everything visual. It is a
   kernel *resource-lock* assert raised on the second core — the same defect
   class as the per-core interrupt work already landed. Disassemble around
   0xE0040EFC (`ASSERT` printer) callers and find the KerRLock entry that fails;
   check whether qemu-eos's second-core model satisfies whatever lock-owner /
   `current_task` per-core state it reads (6D2 `current_task_addr = 0x28`,
   `model_list.c:619`, is a single global — suspicious on a 2-core machine).
2. **The FileMgr/SD timing race.** A chained-TB run stalls at
   `InitializeSDDriver` 100 % of the time here (2 runs this session, plus the
   1581-line run last session); `nochain` passes it every time (3/3). Either
   model the 0xD2090600 SD block or find why the chained run drops the driver's
   completion. Until then, **run 6D2 boots with `-d nochain`** — it is worth
   ~3x more boot progress and costs only speed.
3. The gyro/`Panning` loop is downstream of (1) and probably needs an ADC/gyro
   value that settles; do not chase it before the KerRLock assert.

**Reproduce**

    # card
    xz -dc ml/platform/sd.qcow2.xz > base.qcow2
    qemu-img convert -O raw base.qcow2 card.img
    MTOOLS_SKIP_CHECK=1 mcopy -i card.img@@50688 -s -o -Q \
        ml/platform/6D2.111/build/zip/* ::/
    mdir -i card.img@@50688 ::/            # verify
    qemu-img convert -O qcow2 card.img sd.qcow2 ; cp sd.qcow2 cf.qcow2
    # run: QemuRunner, model 6D2, boot=True, d_args=["debugmsg"] (add "nochain"
    #   for the deep boot), monitor socket path < 108 bytes.
    # gdb: append ["-gdb","tcp::1244"] to q.qemu_command (do NOT use gdb_port=,
    #   that adds -S and the breakpoints would be written before ML is in RAM);
    #   attach after boot settles, symbols from build/magiclantern (bias 0).
    # ALWAYS let qemu exit before reading the card image back.

Evidence added: `evidence/2026-08-15-night2-ml-serial.txt` (bootloader loading
our binary), `evidence/2026-08-15-night2-ml-gdb-rgbvram-wait.txt` (the gdb
breakpoint session), `evidence/2026-08-15-night2-nochain-shtcap-assert.txt`
(the KerRLock / ShtCapturePath asserts at the deeper ceiling).


---

## ADVERSARIAL VERIFICATION — headline SURVIVES, three supporting numbers corrected

An independent agent re-derived these claims from primary sources (HOLDS: False).
Act on the corrected version below, not on the text above where they conflict.

Three sub-claims need rewriting.

1. "ML gets 50 lines FURTHER than the stock control" — WRONG FRAMING. My matched pair gives 1579 (stock) vs 1614 (ML), +35. I diffed the two logs: the delta is NOT boot progress. It is (i) extra repetitions of the idle "[PM] Enable/Disable" and RTCMgr I2C churn that both runs loop in at the end, (ii) CPU1 cache-maintenance MRC/MCR lines produced by ML's own mmu_init/RPC (e.g. "[CPU1] E0004BC4: MCR ... CACHEMAINT x898"), (iii) qemu's own "Setting BOOTDISK flag at E1FF8004" line that only appears with firmware=boot=1, and (iv) ML's 3 real messages. The two logs' tails are line-for-line identical and BOTH stop at the identical sequencer point "[SEQ] NotifyComplete (Cur = 2, 0x400010, Flag = 0x10)" with startupCompleteCallback seen for 0x2/0x10/0x20000/0x20000000 in each. Correct statement: "ML causes no regression — stock and ML reach exactly the same Canon startup stage; the small line-count difference is idle-loop churn plus ML's own output, not extra progress." (The only genuine ML footprint on Canon is a heap/stack pointer shift: FIO_GetSupportedDriveInfo(0x21ef9c) stock vs (0x2201ac) with ML.)

2. "`-d sdcf,verbose` over a whole run: zero SDIO/CF lines" — FALSE AS WRITTEN. My boot=1 run with -d debugmsg,sdcf,verbose logged 170 "[SDIO] Command …/Response received" lines. All 170 fall in stderr lines 130–299 — the Musa bootloader reading AUTOEXEC.BIN off the card, long before Canon's main firmware. "InitializeSDDriver" appears at line 1689 and produces zero further SD command traffic. The other agent's zero came from probing a boot=0 run, where the bootloader never touches the card, so the probe could not have shown anything either way. The corrected statement is stronger, not weaker: the modelled SDIO controller demonstrably WORKS (it served a 244256-byte file read), therefore the DryOS SD driver's failure to issue a single command is not "qemu has no SD". Also, "the SD block it touches is unmodelled" is only half right: in my -d io run FileMgr touches BOTH modelled and unmodelled space — 53 accesses in the [SDIO] region at 0xC80500xx/0xC8050090/0xC80500D8/0xC80500DC (that is qemu-eos's SDIO85 handler, eos.c "SDIO85" 0xC8050000–0xC8050FFF), 6 in [SDDMA], 55 in [TIMER], and 41 logged as "[DIGIC6] … : ???" at the unmodelled 0xD2090600/0608/060C/0610/0614/0618/0634/063C, 0xD209F200/F204/F208/F218/F224, 0xD209B080/B140. Correct statement: "FileMgr's SD driver drives a mix of modelled SDIO85/SDDMA registers and a wholly unmodelled 0xD209xxxx block, and completes no SD command; the only real SD traffic in any run is the bootloader's."

3. "ML cannot reach its GUI until Canon's WINSYS/InitializeScreen stage runs — ROM0 literal-pool refs to 0x000100B8 only at 0xE0885ADC, 0xE088656C, 0xE0886FFC, 0xE08B9D4C, 0xE08BA7DC (WINSYS region)" — THE ADDRESS LIST REPRODUCES, THE INTERPRETATION IS WRONG. My own scan of ROM0 finds exactly those five word-aligned occurrences of the constant 0x000100B8 and no others. But they are not literal pools in code. Disassembling 0xE0885A80 gives a long run of the repeating word 0x00400040 (a numeric table), and the ±0x600 neighbourhoods of all five hits contain float/data tables, no strings and no code. The "InitializeScreen %#x %#x" format strings live at 0xE04C61DC and 0xE04C61F8 — nowhere near any of the five. The method is also wrong in principle: _rgb_vram_info at 0x100b8 sits in Canon's low RAM alongside 0x100bc (bmp_vram_info) and 0x100cc (display_refresh_needed), i.e. fields of one small struct, which ARM code will reach as base+offset from a base register — invisible to a scan for the exact 32-bit constant. Correct statement: "the five hits are coincidental data words; the ROM site that writes _rgb_vram_info was not located. What is measured is that _rgb_vram_info stays 0 in every run, chained and nochain, stock and ML."

Two smaller fixes: (i) "roughly triples boot progress (1558 → 4770 messages)" — my nochain runs give 7307/7325 vs 1579/1614 (4.6x), but ~3180 of the nochain lines (44%) are the post-assert "WAIT AUTO GYRO OFFSET"/"GyroOffsetTimerCBR" idle loop whose count scales with wall-clock, not with progress. The real gain is precise and should be stated as such: one extra sequencer stage (stage 2 dispatches; Cur reaches 3, 0xc0000) plus the stage-3 init that follows, up to the KerRLock assert. Message counts are not a progress metric here. (ii) "timing race, not a missing device" is an over-read of one knob: -d nochain also implies -singlestep, which changes interrupt-delivery granularity and TB boundaries, not just timing; and the 0xD2090600 block really is undecoded. The deliverable's own unresolved list says this correctly — the "established" bullet should be softened to match it. Determinism is now better supported than the deliverable claims: 5/5 chained stall (mine) + 3 theirs = 8/8, and 3/3 nochain pass (mine) + theirs.

Evidence lives in /tmp/claude-1000/-home-chris-Vibe-Coding-6D-Mark-II-Magic-Lantern-6D2/d1809f97-1ab5-4672-8a2b-1ab8dcfa3d5e/scratchpad/advver/ — runs/{ctl,ml,ctlnc,mlnc,sdcf,r1,r2,io}/{stderr.log,serial.log}, runs/gdb/gdb.log, guest_text.bin, ml.img, run.py, gdbprobe.sh. No project file was created or edited.
