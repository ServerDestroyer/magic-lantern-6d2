# 6D2 MPU spell capture — dump→emulator pipeline

Goal: produce `qemu-eos/hw/eos/mpu_spells/6D2.h`, which does not exist upstream —
**no DIGIC 7 camera has one**, so the 6D2 would be the first.

Status 2026-08-15: pipeline built and proven end to end in QEMU. The logger is
verified correct. The only remaining limit is how far the *emulator* boots.

## The pipeline

1. **Build the startup-log ML** (new `CONFIG_STARTUP_LOG` flag adds
   `src/log-d678.o` and the `log_start()` / dump-task hooks in `src/init.c`):

       nix-shell --run 'cd ml/platform/6D2.111 && \
         make disk_image CONFIG_STARTUP_LOG=y \
           ARM_BINPATH="$(dirname $(which arm-none-eabi-gcc))" \
           ML_MODULES="raw_video/mlv_lite file_man bench dual_iso"'

   Yields `build/autoexec.bin` (goes on the card) and `build/sd.qcow2` (for QEMU).
   The explicit `ML_MODULES` list omits `lua`, which does not compile under gcc 15.

2. **Get a boot log.** ML hooks Canon's DebugMsg from `boot_post_init_task`,
   records every MPU send/recv, and a task writes `DEBUGMSG.LOG` to the card 20 s
   after boot.
   - **In QEMU, do NOT use the card copy** — read the buffer out of guest RAM:

         nix-shell --run 'python3 tools/grab_log.py'      # writes 6D2-startup.log

     (Why: see "The 32 KB truncation" below.)
   - **On the real body**: power on, wait ~25 s, pull the battery, read
     `DEBUGMSG.LOG` off the card. There the card copy is the correct source.

3. **Convert log → spell header:**

       cp <log> 6D2-startup.log      # extractor derives the model from the filename
       ML_PLATFORM_DIR=/home/chris/ml6d2/magiclantern_simplified/platform/ \
         python3 qemu-eos/hw/eos/mpu_spells/extract_init_spells.py 6D2-startup.log > 6D2.h

   The `ML_PLATFORM_DIR` override was added to `outils.py`; upstream hardcodes the
   old `magic-lantern/platform/` repo path. Worth upstreaming.

Current QEMU output is in `tools/` — `6D2-startup-qemu.log` (105 KB, 1343 lines)
and `6D2_spells_qemu.h` (23 spells, 16 with decoded property names such as
PROP_CARD2_EXISTS, PROP_AVAIL_SHOT, PROP_BURST_COUNT, PROP_TFT_STATUS).

## The 32 KB truncation — an emulator bug, not an ML bug

The card-side `DEBUGMSG.LOG` holds exactly 32768 bytes of text followed by NUL
padding out to the recorded file size. This was originally misdiagnosed as ML
dropping messages. It is not. Measured, from the host, via the qemu monitor:

- The logger is called for essentially every DebugMsg the firmware emits
  (1339 calls) and **appends all of them** — `drop_nobuf=0`, `drop_full=0`,
  `entered == appended`, spin lock balanced (`enter == exit`).
- The DebugMsg patch stays installed for the whole run (the words at
  `0xdf006e6c` remain `c004f8df / bf004760 / <my_DebugMsg>`).
- `_AllocateMemory(2 MB)` genuinely succeeds: the pool is 9 MB and free drops by
  2097168 bytes across the call.
- **The buffer in guest RAM is complete** right up to `len` (105389 bytes) —
  confirmed by reading it at several offsets and by `pmemsave`.
- Canon's driver issues the whole write: `FIO_WriteFile(3,0x7ba4c4,102213)` →
  `[N]Write buf=7ba4c4 start=15c0 count=199` (199 sectors), reporting success
  with no SDIO error. Yet a raw scan of the card image finds exactly **64
  sectors = 32768 bytes** of log text at that offset and nothing after.

Root cause: `qemu-eos/hw/eos/eos.c`, `sdio_write_data()` performs a single DMA
burst per SD command, so only the first 32 KB of a chunked multi-burst write is
committed. Everything above that is silently dropped.

This does **not** affect the real camera: Canon's `dump_file` (ROM stub
`0xe00809a2`) is the same function ML used to write the 32 MiB `ROM0.BIN` and
16 MiB `ROM1.BIN` from this very body in 2025 — large-file writes demonstrably
work on real hardware.

## What actually limits the QEMU capture

Not the logger and not the SD bug (which `tools/grab_log.py` bypasses), but the
known 6D2 boot wedge: the firmware halts at
`ASSERT : Resource/./EstimatedSize.c, Task = RscMgr, Line 1521` and shortly after
stops making progress entirely — console output and every ML counter freeze
together and stay frozen for as long as you wait (verified over 200 s). That caps
the emulator at ~23 MPU spells. Tracked as spike 001.

A real-body boot runs to completion and would produce the full spell set.

## What goes on the SD card

Only `build/autoexec.bin` from the `CONFIG_STARTUP_LOG` build, copied to the card
root. Nothing else — the camera bootflag is already set and ML is already
installed. Do NOT format the card in-camera (that wipes the boot-sector flags).

This is still an untested-on-body build (`platform/6D2.111/README.txt`), so keep
the run short: power on, wait ~25 s, battery out, one file off the card.
