# 6D2 MPU spell capture — dump→emulator pipeline

Goal: produce `qemu-eos/hw/eos/mpu_spells/6D2.h`, which does not exist upstream —
**no DIGIC 7 camera has one**, so the 6D2 would be the first.

Status 2026-08-15: pipeline built and proven end to end in QEMU. The logger is
verified correct and a complete log was captured. It then **regressed** after
another session's `platform/6D2.111` changes; see "Current blocker".

This document was adversarially verified after being written, and several of its
earlier claims were wrong — retractions are marked inline rather than deleted.

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

Captured artifacts are in `tools/`: `6D2-startup-qemu.txt` (105 KB, 1343 lines), `6D2-DEBUGMSG-card.txt` (the card copy)
and `6D2_spells_qemu.h` (23 spells; 16 carry a description, of which 8 are
symbolic names such as PROP_AVAIL_SHOT, PROP_BURST_COUNT, PROP_TFT_STATUS, 6 are
raw property IDs and 2 are protocol markers). The RAM-extraction and card-file
paths were cross-checked and agree.

Both files were renamed off `.log` on purpose: `.gitignore:14` ignores `*.log`,
so the originals were invisible to git.

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

1. **Allocation.** Cause not yet established — the controlling A/B (build with
   those features off) is untried, and that session also changed `consts.h`,
   `internals.h` and `stubs.S` in the same window. Fixes to consider once the
   cause is known: move `log_start()` later, or use a hardcoded unused-RAM
   buffer as done for the 80D (`src/log-d678.c:366`), 5D4 (`:371`) and 200D
   (`:376`). `src/log-d678.h:6-23` carries only the general warning that such an
   address must be found per body and never copied — note that path is tied to
   `LOG_EARLY_STARTUP`, which the 6D2 does not enable, so it is a larger change
   than it sounds.
2. ~~ISR hook conflict~~ — **retracted, do not reinstate.** An earlier draft
   claimed `tskmon.c` steals `pre_isr_hook`/`post_isr_hook`. False:
   `src/tskmon.c:501` guards those assignments behind `#ifdef CONFIG_ISR_HOOKS`,
   which is defined nowhere in the tree, so they never compile; `tskmon.o` is
   unconditional (`platform/Makefile:364`), not gated by `FEATURE_SHOW_TASKS`;
   and the captured trailer reads `pre_isr_hook=103935 post_isr_hook=1039c9`
   — log-d678's own hooks, intact.

## Safety change kept

`src/log-d678.c` upstream does `while (!buf);` if the allocation fails — an
infinite spin inside `boot_post_init_task`. On a body that is a camera that looks
bricked, and the blocker above shows the allocation really can fail. It now sets
`buf_size = 0` and returns: no log beats a dead camera.

The neighbouring interrupt check `if (!(read_cpsr() & 80))` is dead code —
80 is decimal (0x50) and overlaps CPSR M[4], which is set in every AArch32 mode,
so it can never fire. Left as-is deliberately; only its `while(1)` was made a
return. Whether correcting it to `0x80` would actually drop messages was never
isolated, and is doubtful — `cli_spin_lock` (arm-mcr.h:571-573) masks interrupts
immediately before it, so a live check should pass. `diag_irq_enabled` settles it.

## What goes on the SD card

Sync the whole `build/zip/ML/` tree (modules and `6D2_111.sym`) **plus**
`build/autoexec.bin`, all from the same `CONFIG_STARTUP_LOG` build. A stale `ML/`
tree or a mismatched `6D2_111.sym` is a known card-sync failure mode, and the
reduced `ML_MODULES` list means the on-card module set differs from any earlier
build. Do NOT format the card in-camera (it wipes the boot-sector flags).

`platform/6D2.111/README.txt` says this code was never tested on a real cam;
that line is out of date — an ML build from this tree has already been flashed
and confirmed on this body (see `patches/README.md`, MOV time limit). Keep the
run short anyway: power on, wait ~25 s, battery out, one file off the card. Read
the DIAG trailer first; `drop_full` non-zero means raise `buf_size` and repeat.
Note a NULL `buf` produces no file and no trailer — absence is the failure.

## What QEMU cannot tell you

- **The MPU traffic here is synthetic** — qemu-eos replays its own generic model
  (`[MPU] FIXME: using generic MPU spells for 6D2`). The 23 spells are the
  emulator talking to itself. Only a body run yields a real 6D2 spell set.
- **The emulator stops progressing early.** The assert at t≈0.32 s
  (`Resource/./EstimatedSize.c:1521`) is a *soft* failure — per spike 001 Canon
  completes startup via `ErrorSend (101, ABORT)` rather than halting — but the
  phases that generate most MPU traffic are never reached: 22 of 23 spells land
  before it. ML itself stays alive; its `log_dump` task runs at t=19.5 s and
  writes the card file.
- **Memory pressure is not representative**, which is exactly what the blocker
  above is about.
