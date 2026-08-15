# 6D2 MPU spell capture — how the dump→emulator pipeline works

Goal: produce `qemu-eos/hw/eos/mpu_spells/6D2.h` (which does not exist upstream —
no DIGIC 7 body has one) so qemu-eos stops using generic MPU spells for the 6D2.

## The pipeline (all pieces verified working 2026-08-15)

1. **Build the startup-log ML variant** (adds the DebugMsg + MPU ring-buffer
   logger from `ml/src/log-d678.c`, wired in via the new `CONFIG_STARTUP_LOG`
   flag):

       nix-shell --run 'cd ml/platform/6D2.111 && \
         make disk_image CONFIG_STARTUP_LOG=y \
           ARM_BINPATH="$(dirname $(which arm-none-eabi-gcc))" \
           ML_MODULES="raw_video/mlv_lite file_man bench dual_iso"'

   Produces `build/autoexec.bin` (the file that goes on the card) and
   `build/sd.qcow2` (same thing, for QEMU).

2. **Get a boot log.** ML hooks Canon's DebugMsg from `boot_post_init_task`,
   captures every MPU send/recv during startup, and writes `DEBUGMSG.LOG` to the
   card ~20s after boot (see `src/init.c` startup_log_dump_task).
   - In QEMU: `scratchpad/boot_ml_test.py` boots headless, then pull the file:
     `guestfish --ro -a build/sd.qcow2 -m /dev/sda1 -- download /DEBUGMSG.LOG out.log`
   - On real body: power on, wait ~25s, battery out, pull card, copy DEBUGMSG.LOG.

3. **Convert log → spell header:**

       cp DEBUGMSG.LOG 6D2-startup.log   # extractor derives model from filename
       ML_PLATFORM_DIR=/home/chris/ml6d2/magiclantern_simplified/platform/ \
         python3 qemu-eos/hw/eos/mpu_spells/extract_init_spells.py 6D2-startup.log > 6D2.h

   (`ML_PLATFORM_DIR` env override added to `outils.py`; upstream hardcoded the
   old `magic-lantern/platform/` repo path. Worth upstreaming that fix.)

## Status / open issues

- **Emulator boot is truncated.** Stock + our ML both halt at the Canon RscMgr
  assert (EstimatedSize.c:1521) before the GUI, so a QEMU-only log yields ~28 MPU
  messages — enough to prove the pipeline and generate a valid partial 6D2.h, but
  the *full* spell set needs a real-body boot that runs to completion.
- **Capture completeness gap (must fix before the body run).** In QEMU the MPU
  send/recv lines appear in the live console (QEMU `-d debugmsg` plugin) but NOT
  in the card-side DEBUGMSG.LOG — ML's own `my_DebugMsg` buffer stopped appending
  after ~0.15s of timer / 403 lines while the console kept going to 5000+. On real
  hardware only the card file exists, so this must be root-caused first. Prime
  suspects: the `cli_spin_lock` in log-d678.c's `my_DebugMsg` under interrupt
  context, or the 2 MB `_AllocateMemory` buffer vs the hardcoded-address approach
  log-d678.h recommends ("addresses to be found experimentally"). The console
  proves the messages are generated; the buffering path is what drops them.

## What goes on the SD card (only when steps above are green)

Just `build/autoexec.bin` from the CONFIG_STARTUP_LOG build, copied to the card
root. Nothing else — bootflag already set, ML already installed. Do NOT format
the card in-camera (wipes boot-sector flags). This is still an untested-on-body
build (`platform/6D2.111/README.txt`), so: short run, battery-pull, one file out.
