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
