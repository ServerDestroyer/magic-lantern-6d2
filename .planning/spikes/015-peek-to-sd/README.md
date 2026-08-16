---
spike: 015
name: peek-to-sd
type: build
validates: "Given a running 6D2 with an ML capture build, when the operator sets an [address, length] in the 'Peek to SD' debug submenu and fires 'Dump now', then that memory range is written read-only to ML/LOGS/PEEK0.BIN with a PEEK0.TXT sidecar (addr/len/timestamp/build), recoverable by battery pull if the address faults"
verdict: BUILT — compiles clean for 6D2.111 under -Werror with the feature enabled; not yet run on hardware
related: [005, 011, 013]
tags: [hitl, debug, read-only, on-camera, digic7]
---

# Spike 015: Peek-to-SD (HITL ladder rung 2)

## Verdict, up front

**Code is written and compiles clean for 6D2.111 (`-Werror`, arm-none-eabi-gcc
15.2.1). Not yet run on hardware.** This is the fastest safe way to read real
silicon: a read-only, battery-pull-recoverable on-camera dump of an arbitrary
`[address, length]` range to the SD card. Off by default via a build flag, so
normal builds are untouched; Chris flips it on for a capture build.

The whole feature is a reuse of two things that already exist in ML:

- `save_mem_to_file(void *start, uint32_t size, char *filename)` — the dump
  primitive, `ml/src/fio-ml.c:816-826`. Read-only by construction: it opens the
  file, `FIO_WriteFile(f, start, size)`, closes it. It only *reads* from
  `start` and *writes* the file. Nothing is written to camera memory.
- `run_in_separate_task(void* routine, int argument)` — `ml/src/menu.h:309`,
  the same menu-action mechanism the existing "Dump ROM and RAM" and "Dump
  image buffers" entries use (`ml/src/debug.c`). This is the smaller wiring than
  the `request_core_dump` / `core_dump_requested` / `crash_log_step` trigger
  pair (`ml/src/debug.c:532-540, 609-615`) — that path needs a polling consumer
  in `crash_log_step()` and is gated on `CONFIG_CRASH_LOG`; a `.select =
  run_in_separate_task` menu action needs neither and matches the two existing
  dump-to-SD entries exactly.

## Design

One build flag, one task function, one debug submenu. No new subsystem.

### The build flag

`FEATURE_PEEK_TO_SD`, defined **commented-out** in
`ml/platform/6D2.111/features.h` (just below the three `FEATURE_SHOW_*` flags).
All feature code is under `#ifdef FEATURE_PEEK_TO_SD`, so a default build emits
zero peek bytes and behaves exactly as before. Chris uncomments the line for a
HITL capture build.

**Deliberately independent of the `FEATURE_SHOW_*` path.** The features.h
comment block (lines ~43-53) records that `FEATURE_SHOW_TASKS` /
`FEATURE_SHOW_CPU_USAGE` / `FEATURE_SHOW_GUI_EVENTS` make
`GetMemoryInformation()` report 0/0 and every `_AllocateMemory` fail, breaking
`CONFIG_STARTUP_LOG`. Peek-to-SD touches neither the startup log nor
`_AllocateMemory` — it only reads memory and calls FIO. So it can ride in the
same capture build as `CONFIG_STARTUP_LOG` without disturbing it.

### The trigger

Debug menu → **Peek to SD** submenu, with three children:

1. **Address** — `UNIT_HEX`, `.min = 0, .max = 0xFFFFFFFF`. Full 32-bit hex
   editing (proven pattern, copied from `modules/selftest/selftest.c:2688-2694`
   "Hex 0..FFFFFFFF"). Press Q, then scroll to edit each hex digit. This reaches
   ROM/MMIO at `0xE0000000+` — the hexdump browser's `.max = 0x20000000` cannot.
2. **Length** — `UNIT_HEX`, `.min = 1, .max = 0x2000000` (32 MB).
3. **Dump now** — `.select = run_in_separate_task, .priv = peek_dump_task`.

`peek_dump_task` reads `peek_addr`/`peek_len`, clamps length to
`[0x100, PEEK_MAX_LEN]`, `NotifyBox`es a "reading..." message, calls
`save_mem_to_file((void*)(uintptr_t)addr, len, "ML/LOGS/PEEK0.BIN")`, then
writes the `ML/LOGS/PEEK0.TXT` sidecar (addr, len, RTC timestamp via
`LoadCalendarFromRTC`, ML `build_version`/`build_id`).

## Files changed

- `ml/platform/6D2.111/features.h` — added the commented `FEATURE_PEEK_TO_SD`
  flag plus an explanatory comment (after the `FEATURE_SHOW_*` block, before
  `#undef CONFIG_ADDITIONAL_VERSION`).
- `ml/src/debug.c` — two additions, both `#ifdef FEATURE_PEEK_TO_SD`:
  - `peek_addr` / `peek_len` statics, `PEEK_MAX_LEN`, and `peek_dump_task()`,
    inserted immediately before `static struct menu_entry debug_menus[]`.
  - The "Peek to SD" submenu entry, inserted in `debug_menus[]` right after the
    "Dump image buffers" entry.

No other files touched. No existing behavior changed (all new code is behind the
`#ifdef`, which is off by default).

## How Chris builds, triggers, and reads the result

**Build (capture build):**
1. In `ml/platform/6D2.111/features.h`, uncomment `#define FEATURE_PEEK_TO_SD`.
2. From `ml/platform/6D2.111/`:
   `nix-shell "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/shell.nix" --run 'make ARM_BINPATH=$(dirname $(which arm-none-eabi-gcc))'`
   (The `ARM_BINPATH` override is needed on this NixOS box — see "Build-env
   note" below.) Produces `build/autoexec.bin` + `build/magiclantern.zip`.
3. Install on the card as usual (one boot).

**Trigger on-camera:**
1. Open ML menu → Debug → **Peek to SD**.
2. Set **Address** (Q to select digit, scroll to change) and **Length**.
3. Select **Dump now**. A NotifyBox shows progress, then "Peek done".

**Read the result:** pull the card. `ML/LOGS/PEEK0.BIN` is the raw bytes;
`ML/LOGS/PEEK0.TXT` records what/when/which-build. Re-firing overwrites both
(single-slot, `PEEK0`).

## Read-only safety argument

- **No writes to camera memory, by construction.** The only memory operation is
  `FIO_WriteFile(f, start, size)` inside `save_mem_to_file` — `start` is a
  source that is *read*; the *destination* is the SD file. There is no store to
  any camera address anywhere in the added code. The address the operator types
  is used solely as a read source and as text in the sidecar.
- **Worst case is a data abort → battery pull.** A bad/unmapped address faults
  on read; that is recoverable by removing the battery, matching the accepted
  HITL safety model for rung 2. Nothing is flashed, no bootflag is touched.
- **Cheap fat-finger guard.** Length is clamped to `[0x100, 0x2000000]` (32 MB)
  in both the menu bounds and the task, so a typo cannot try to stream gigabytes
  to the card. Address is intentionally unrestricted — reading any address is
  the whole point, and read-only + battery-pull is the safety net rather than an
  address whitelist (which would be over-engineering for a spike and would block
  the ROM/MMIO peeks this exists to do).

## VERIFIED vs ASSUMED

**VERIFIED:**
- `save_mem_to_file` exists at `ml/src/fio-ml.c:816-826` with signature
  `(void *start, uint32_t size, char *filename)` and is read-only as described
  (confirmed via code graph + source).
- The `request_core_dump`/`core_dump_requested`/`crash_log_step` trigger pair
  exists at `ml/src/debug.c:532-540` and `598-630` (confirmed) — evaluated and
  deliberately not used in favor of the smaller `run_in_separate_task` action.
- `CONFIG_CRASH_LOG` is defined for 6D2.111 and the three `FEATURE_SHOW_*` flags
  are off (`ml/platform/6D2.111/features.h:32, 51-53`).
- Full-32-bit `UNIT_HEX` menu editing with `.max = 0xFFFFFFFF` is a working
  pattern in this tree (`modules/selftest/selftest.c:2688-2694`); the menu
  clamp/wrap logic (`menu_numeric_toggle_hex`, `ml/src/menu.c:745-762`) treats
  `.max` as `uint32_t`.
- **It compiles.** `make` for 6D2.111 with `FEATURE_PEEK_TO_SD` enabled builds
  to `autoexec.bin` + `magiclantern.zip`; a forced clean rebuild of `debug.o`
  passes under `-Werror` with no warnings on `debug.c`.

**ASSUMED (not yet verified on hardware):**
- The menu entry renders and "Dump now" fires on a real 6D2 (compiled, never
  booted here — this session does not touch the camera or run QEMU).
- `ML/LOGS/` exists at dump time. Assumed because the existing ROM dump writes
  `ML/LOGS/ROM0.BIN` there; if a fresh card lacks it, `FIO_CreateFile` may fail
  silently and no file appears (no crash). Low risk; confirm on first run.
- `LoadCalendarFromRTC` returns a sane time on 6D2 (declared for
  `CONFIG_DIGIC_78X` in `ml/src/dryos.h:175-177`; used widely in
  `ml/src/flexinfo.c`). Only the sidecar timestamp depends on it; the .BIN dump
  does not.
- Reading a given address does not have hardware read side-effects. True for
  RAM/ROM; some MMIO registers can have read-side-effects — inherent to peeking
  hardware, not something this tool can know. Read-only + battery-pull is the
  guard.

## Build-env note

On this NixOS box the ML Makefile hardcodes `ARM_BINPATH ?= /usr/bin`
(`ml/Makefile.globals:17`) but the cross toolchain lives at a `/nix/store/...`
path from `shell.nix`. Passing `ARM_BINPATH=$(dirname $(which
arm-none-eabi-gcc))` on the `make` line resolves it. This is a pre-existing
environment quirk unrelated to the peek code; noting it here so the capture
build does not trip on the same thing.

## What remains for Chris

1. Uncomment `FEATURE_PEEK_TO_SD` in `ml/platform/6D2.111/features.h`.
2. Build (with the `ARM_BINPATH` override above) and install — one boot.
3. On-camera: Debug → Peek to SD → set Address/Length → Dump now.
4. Pull card, read `ML/LOGS/PEEK0.BIN` + `PEEK0.TXT`. First run also confirms
   the three ASSUMED items above (menu renders, `ML/LOGS/` present, RTC sane).
