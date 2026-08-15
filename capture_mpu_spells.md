# 6D2 MPU spell capture — dump→emulator pipeline

Goal: produce `qemu-eos/hw/eos/mpu_spells/6D2.h`, which does not exist upstream —
**no DIGIC 7 camera has one**, so the 6D2 would be the first.

Status 2026-08-15: pipeline built and proven end to end in QEMU. The logger is
verified correct and a complete log was captured. It then **regressed** when
another session enabled four features; see "Current blocker".

## The pipeline

1. **Build the startup-log ML** (`CONFIG_STARTUP_LOG` adds `src/log-d678.o` plus
   the `log_start()` / dump-task hooks in `src/init.c`):

       nix-shell --run 'cd ml/platform/6D2.111 && \
         make disk_image CONFIG_STARTUP_LOG=y \
           ARM_BINPATH="$(dirname $(which arm-none-eabi-gcc))" \
           ML_MODULES="raw_video/mlv_lite file_man bench dual_iso"'

   Yields `build/autoexec.bin` (goes on the card) and `build/sd.qcow2` (for QEMU).
   The explicit `ML_MODULES` list omits `lua`, which does not build under gcc 15.

2. **Get a boot log.** ML hooks Canon's DebugMsg from `boot_post_init_task`,
   records every MPU send/recv, and a task writes `DEBUGMSG.LOG` to the card 20 s
   after boot.
   - In QEMU: `python3 tools/grab_log.py` reads the buffer straight out of guest
     RAM via the monitor's `pmemsave`. Works even when the guest wedges, so it is
     the more reliable option — but the card path works too (see below).
   - On the body: power on, wait ~25 s, pull the battery, copy `DEBUGMSG.LOG`.

3. **Convert log → spell header:**

       cp <log> 6D2-startup.log      # extractor derives the model from the filename
       ML_PLATFORM_DIR=/home/chris/ml6d2/magiclantern_simplified/platform/ \
         python3 qemu-eos/hw/eos/mpu_spells/extract_init_spells.py 6D2-startup.log > 6D2.h

   The `ML_PLATFORM_DIR` override was added to `outils.py`; upstream hardcodes the
   old `magic-lantern/platform/` repo path. Worth upstreaming.

Captured artifacts are in `tools/`: `6D2-startup-qemu.log` (105 KB, 1343 lines)
and `6D2_spells_qemu.h` (23 spells, 16 with decoded property names such as
PROP_CARD2_EXISTS, PROP_AVAIL_SHOT, PROP_BURST_COUNT, PROP_TFT_STATUS). The
RAM-extraction and card-file paths were cross-checked and agree.

## Verified working (measured, not assumed)

Read from the host over the qemu monitor (ML's own counters in BSS, plus
`pmemsave`), and from the card after a clean shutdown:

- The logger sees essentially every DebugMsg the firmware emits (1306 calls) and
  **appends all of them**: `drop_nobuf=0`, `drop_full=0`, `entered == appended`,
  spin lock balanced (`lock_enter == lock_exit`).
- The DebugMsg patch stays installed all run (`0xdf006e6c` reads
  `c004f8df / bf004760 / <my_DebugMsg>`).
- `_AllocateMemory(2 MB)` succeeded, from a 9 MB pool (free dropped 2097168).
- **Card file: 102744 bytes, zero NUL bytes, 1310 lines, 23 mpu_send + 3
  mpu_recv, `Logging finished.` and the DIAG trailer both present.**

### Measurement trap — do not read sd.qcow2 while QEMU is running

An earlier run appeared to truncate at exactly 32768 bytes with NUL padding, and
this was written up here as a qemu-eos SD DMA bug. **That was wrong.** The image
was being read before QEMU had flushed it; 32768 is exactly two 16 KiB FAT
clusters, i.e. flush granularity. Stop the emulator first, then read. There is no
SD emulation bug — Canon's `dump_file` (ROM stub `0xe00809a2`) writes the whole
100 KB correctly, and it is the same stub that wrote this body's 32 MiB ROM0.BIN
in 2025.

## Current blocker (new, 2026-08-15 ~14:00)

Another session enabled `FEATURE_SHOW_TASKS`, `FEATURE_SHOW_CPU_USAGE`,
`FEATURE_SHOW_GUI_EVENTS` and `FEATURE_OVERRIDE_MOVIE_30_MIN_LIMIT` in
`platform/6D2.111/features.h` (plus consts.h/stubs.S edits). With those enabled,
the startup logger no longer captures anything. Reproducible, measured:

- At `log_start()` time `GetMemoryInformation()` now reports **0 total / 0 free**,
  every `_AllocateMemory` fails (2 MB down to 128 KB, with retries), so `buf`
  stays NULL, DebugMsg is never patched, and no `DEBUGMSG.LOG` is written.
- Previously, at the same point, the pool reported 9 MB total / 5.9 MB free.

Two things to resolve before a body run:

1. **Allocation.** Either move `log_start()` later (after Canon's allocator is
   up) or use a hardcoded unused-RAM buffer, which is what `src/log-d678.h:9-15`
   says upstream does for 80D/5D4/200D and explicitly warns must be found per
   camera. Do not reuse another model's address.
2. **ISR hook conflict.** `FEATURE_SHOW_TASKS` pulls in `src/tskmon.c`, which
   sets `pre_isr_hook` / `post_isr_hook` (tskmon.c:505-506) — the same two hooks
   `log_start()` installs for MPU capture. Whichever runs last wins. The MPU
   send/recv capture is the whole point of this exercise, so build the capture
   image with those debug features off, or make the hooks chain.

## Safety change kept

`src/log-d678.c` upstream does `while (!buf);` if the allocation fails — an
infinite spin inside `boot_post_init_task`. On a body that is a camera that looks
bricked, and the blocker above shows the allocation really can fail. It now sets
`buf_size = 0` and returns: no log beats a dead camera.

The neighbouring interrupt check `if (!(read_cpsr() & 80))` is dead code —
80 is decimal (0x50) and overlaps CPSR M[4], which is set in every AArch32 mode,
so it can never fire. Left as-is deliberately (correcting it to 0x80 makes the
check live and starts dropping messages); only its `while(1)` was made a return.

## What goes on the SD card

Only `build/autoexec.bin` from the `CONFIG_STARTUP_LOG` build, copied to the card
root. Nothing else — the bootflag is set and ML is already installed. Do NOT
format the card in-camera (it wipes the boot-sector flags).

Still an untested-on-body build (`platform/6D2.111/README.txt`): keep the run
short — power on, wait ~25 s, battery out, one file off the card. Read the DIAG
trailer first; `drop_full` non-zero means raise `buf_size` and repeat.

## What QEMU cannot tell you

- **The MPU traffic here is synthetic** — qemu-eos replays its own generic model
  (`[MPU] FIXME: using generic MPU spells for 6D2`). The 23 spells are the
  emulator talking to itself. Only a body run yields a real 6D2 spell set.
- **The emulator wedges early** at `ASSERT : Resource/./EstimatedSize.c, Task =
  RscMgr, Line 1521` (spike 001) and then stops entirely — console output and
  every ML counter freeze together and stay frozen (verified over 200 s). The
  phases that generate most MPU traffic are never reached.
- **Memory pressure is not representative**, which is exactly what the blocker
  above is about.
