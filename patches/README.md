# Patches against `magiclantern_simplified` and `qemu-eos`

`ml/` and `qemu-eos/` are clones of other people's repos and are gitignored here,
so any work in them would be invisible to this repo and lost on a `git checkout`.
Patches live here instead.

| # | Target | Subject | State |
|---|---|---|---|
| 0001 | `ml/` | MOV time limit, debug flags, two source fixes | **Tested on the real camera** — but SPLIT before upstreaming: Track A's A/B measured the three `FEATURE_SHOW_*` flags causing a 0/0 memory pool at `log_start()` in `CONFIG_STARTUP_LOG` builds (MOV limit exonerated; normal boots unaffected). Ship the MOV-limit + source-fix half alone; hold the SHOW flags until the pool interaction is understood. |
| 0002 | `ml/` | `CONFIG_STARTUP_LOG` MPU-spell capture build | Working in QEMU when combined with 0005; body package ready |
| 0003 | `qemu-eos/` | `outils.py`: honour `ML_PLATFORM_DIR` | Works; upstreamable one-liner |
| 0004b | `qemu-eos/` | 6D2 `debugmsg.gdb`: EstimatedSize workaround + fix wrong `assert_log` address (renamed from 0004 to resolve the numbering collision; 0006 is reserved by spike 006's diagnostic build) | **Verified live in QEMU**; both parts upstreamable |
| 0004 | `ml/` | `prop_request_change_wait`: skip timeout on denied writes — **hardware-confirmed 2026-08-15 16:12** (raw-video livelock cured, 25-frame MLV recorded) | Applied in tree; PR-2 ready to post |
| 0005 | `ml/` | Capture build: disable the three `FEATURE_SHOW_*` flags (they zero the allocator pool — spike 005 A/B) | **Measured in QEMU**, both legs |

## Applying

```sh
cd ml
git apply ../patches/0001-6D2-mov-time-limit-debug-flags-fixes.patch
```

Check first with `git apply --check`. To undo: `git apply -R`.

## 0001 — MOV time limit, debug flags, two source fixes

Against `magiclantern_simplified` @ `3f24042a4` (branch `dev`).
**Builds clean.** Verified by symbol inspection, not just a zero exit code.

| Change | File | Why |
|---|---|---|
| `MVR_TIME_LIMIT_NORMAL_FPS 0xe042ff74`, `MVR_TIME_LIMIT_HIGH_FPS 0xe042ff78` | `consts.h` | The 29:59 and 7:29 recording limits, in ms, in a ROM0 literal pool |
| `FEATURE_OVERRIDE_MOVIE_30_MIN_LIMIT` | `features.h` | Turns on the existing `movtweaks.c` implementation |
| `FEATURE_SHOW_TASKS`, `FEATURE_SHOW_CPU_USAGE`, `FEATURE_SHOW_GUI_EVENTS` | `features.h` | On for both D7 siblings (200D, 77D) and 10 other modern ports |
| `6D2 1.0.5` → `6D2 1.1.1` | `internals.h` | Wrong version in the header comment; platform dir and verified ROM are both 1.1.1 |
| Remove duplicated `CreateResLockEntry` / `LockEngineResources` | `stubs.S` | Each was defined twice with identical addresses |

### How the addresses were established

Searching `ROM0.BIN` for 1799000 (`0x1b7358`, 29m59s) and 449000 (`0x6d9e8`,
7m29s) — the exact `.old_value` fields `movtweaks.c` asserts against — finds each
byte pattern **exactly once in the whole 32 MiB image**, adjacent and in that
order. No competing candidate exists.

Both are reached by a two-armed getter at `0xe042fee8`: the `beq` at `0xe042fef0`
selects normal vs high FPS, and each arm is an `ldr r0, [pc, #128]` whose T1
literal target — `align4(PC+4) + 0x80` — resolves to `0xe042ff74` and
`0xe042ff78` respectively. Confirmed by decoding the instructions, not by
pattern-matching bytes.

Note `ROM0.BIN` is the main firmware and maps to `0xE0000000` — the inverse of
what the filenames suggest, and the reason a first scan of ROM1 found nothing.

### Verification status

**CONFIRMED ON HARDWARE (2026-08-15).** Built, flashed to the card, and tested on
the real 6D2: with the limit set to 1 min, recording stopped on its own at ~60 s.
That was the one thing static analysis could not settle — whether the getter at
`0xe042fee8` is the function Canon actually consults to stop recording. It is.

Both addresses are therefore real, and `apply_patches()` did not trip
`E_PATCH_OLD_VALUE_MISMATCH`, which independently confirms the `.old_value`
constants (`0x1b7358` / `0x6d9e8`) match what is in this body's ROM.

Also verified statically before flashing:

- `movtweaks.o` exports `change_mov_time_limit`, `mov_time_limit`,
  `print_mov_time_limit`
- `tasks.o` exports `tasks_print`, `show_cpu_usage_flag`
- `autoexec.bin` contains the menu strings `MOV/MP4 time limit`, `Show tasks`,
  `Show CPU usage`, `Show GUI events`

**The MOV limit cannot brick anything.** `apply_patches()` validates
`.old_value` before writing and rolls back both patches atomically, so a wrong
address fails loudly with `E_PATCH_OLD_VALUE_MISMATCH` rather than corrupting
anything. The realistic bad outcome is "the menu applies but recording still
stops at 29:59".

**On-camera test: PASSED.** Limit set to 1 min, recording stopped by itself at
~60 s. Ready to offer upstream.

## Not included, and why

`FEATURE_RAW_HISTOGRAM` / `FEATURE_RAW_SPOTMETER` were attempted and dropped.
Their gate (`CONFIG_RAW_PHOTO || CONFIG_RAW_LIVEVIEW`) does pass on the 6D2, but
the macro only switches the *raw variant* of code inside `histogram.c`, and the
6D2 defines none of `FEATURE_HISTOGRAM`, `FEATURE_ZEBRA`, or `FEATURE_OVERLAYS`.
Enabling it alone compiles fine and displays nothing — the exact
"compiles and silently does nothing" trap that the property whitelist also sets.
It needs the histogram display infrastructure first, which is real work requiring
on-camera verification.

## 0002 — `CONFIG_STARTUP_LOG` MPU-spell capture build

Against `magiclantern_simplified` @ `3f24042a4` (branch `dev`). Builds clean.
Opt-in: `make CONFIG_STARTUP_LOG=y`, otherwise a no-op.

| Change | File | Why |
|---|---|---|
| `CONFIG_STARTUP_LOG=y` flag adds `log-d678.o` | `platform/6D2.111/Makefile` | Nothing in the tree wired the DIGIC 6/7/8 logger into a build |
| `log_start()` + a `log_dump` task (sleeps 20 s, then `log_finish()`) | `src/init.c` | Capture Canon's startup DebugMsg and MPU ring buffers, then write `DEBUGMSG.LOG` |
| `task_name_padded[11]` → `[12]` | `src/log-d678.c` | gcc 15 `-Werror=unterminated-string-initialization` |
| `GetFreeMemForAllocateMemory` duplicate guard | `src/log-d678.c` | `src/mem.c` already defines it in a full ML build |
| DIAG counters + trailer written into the log | `src/log-d678.c` | Self-verification; on the body the card file is the only evidence |
| **`while (!buf);` → clean bail-out** | `src/log-d678.c` | Upstream spins forever inside `boot_post_init_task` if the allocation fails — an apparently-bricked camera. Spike 005 proves that allocation really can fail. |

Deliberately not changed: `if (!(read_cpsr() & 80))` is dead (80 is decimal
0x50, overlapping CPSR M[4], set in every AArch32 mode). Making it live starts
dropping messages; only its `while(1)` became a return.

**Unblocked 2026-08-15** — the 0/0-pool allocation failure was the three
`FEATURE_SHOW_*` flags (see 0005). With 0001 + 0002 + the ml 0004 + 0005
applied, capture is verified working in QEMU; body-run package in
`card_packages/capture/`. See `.planning/spikes/005-mpu-spell-capture/`.

## 0003 — `qemu-eos` `outils.py`: honour `ML_PLATFORM_DIR`

`extract_init_spells.py` dies looking for the pre-2020 `magic-lantern/platform/`
path. One-line env override, upstreamable as-is.

```sh
cd qemu-eos && git apply ../patches/0003-qemu-eos-outils-ML_PLATFORM_DIR.patch
```

## 0004b — 6D2 `debugmsg.gdb`: EstimatedSize workaround + wrong `assert_log` address

Against `qemu-eos` @ `4b667a1d3c` (branch `qemu-eos-v4.2.1`).
**Verified live in QEMU**, not by inspection.

Two independent changes to `magiclantern/cam_config/6D2/debugmsg.gdb`:

**1. EstimatedSize workaround (new).** `GetEstimatedSize()` at `0xE0202312` loads a
frame-rate field (fps x100) at `0xE0202372` (`ldr r0,[r6,#8]`) and switches on it
against exactly eight legal values — `2000 2398 2400 2500 2997 5000 5994 11988` —
falling through to `ASSERT(FALSE)` at `0xE0202480` = `EstimatedSize.c:1521`, task
`RscMgr`. Under generic MPU spells the field holds **81** (`0x51`); 200D's
`patches.gdb` records the identical value ("strange values passed in, 0x51").
Breakpoint goes AFTER the load — an entry patch is clobbered by it. Same register
form 77D/750D already ship.

Observed: `ESTSIZE_HIT rate=81` x14, boot **223 -> 2882** log lines. The 1521 assert
is gone; only a non-fatal `[RSC] ERROR GetEstimatedSizeOfMovie NOT Exist` remains.

**2. `assert_log` address was wrong (bug fix).** The file shipped `b *0xE06170EC`.
That address is *mid-instruction inside AES S-box lookup code* —
`0xE06170E0-0xE06170FE` is `ubfx` / `ldrb rN,[r2,rN]` / `lsls` / `orr`, a byte-table
shuffle. Nothing was ever assert-logged for this camera. The real handler is
`0xE0617620`: standard prologue, loads the handler pointer at `0x4000`, tail-calls
it (`bx r3`). Signature `assert(r0 = expr str, r1 = file str, r2 = line)`, confirmed
against the call site at `0xE020248C` which sets `r2=1521` and ADRs both strings.
Verified by disassembling both addresses.

### Not included, deliberately

The `EngInit` stub for the *next* wall (`set *(unsigned short*)0xE0091D04 = 0x4770`,
clearing `SystemIF::KerRLock.c:205` / `WaitPU1 TimeOut`) is **not** in this patch. It
removes a symptom without booting the camera — `startupInitializeComplete` was absent
in all 8 test runs — and all three hypotheses around it were refuted on adversarial
review. It is documented and commented-out in `tools/qemu-6d2-boot.gdb` instead.
See `PU1_INVESTIGATION.md`.

## 0005 — Capture build: disable the three `FEATURE_SHOW_*` flags

Apply on top of 0001. Spike 005 task 5 A/B (measured over the qemu monitor,
addresses re-resolved per build): with `FEATURE_SHOW_TASKS`,
`FEATURE_SHOW_CPU_USAGE`, `FEATURE_SHOW_GUI_EVENTS` enabled,
`GetMemoryInformation()` reports 0 total / 0 free at `log_start()` and every
`_AllocateMemory` fails, so `CONFIG_STARTUP_LOG` captures nothing. With them
off the pool reads 9437184/5970756, the 2 MB buffer allocates (free drops by
exactly 2097168), and the capture is complete (DIAG trailer, 23 `mpu_send` +
3 `mpu_recv`). `FEATURE_OVERRIDE_MOVIE_30_MIN_LIMIT` is exonerated — leg 2 and
the packaged ship build carry it and are healthy — as are `consts.h`,
`internals.h`, `stubs.S` (leg 1 carried all three and was healthy). Which of
the three flags does it, and why, is not narrowed; unverified hypothesis is
image/BSS growth colliding with the pool. The body-run card package built from
this configuration is in `card_packages/capture/`.

## 0007 — qemu-eos: real 6D2 MPU spells from the body (closes spike 001)

Adds `hw/eos/mpu_spells/6D2.h` (generated by `extract_init_spells.py` from the
2026-08-15 body capture, ~175 spells with decoded property names) and wires it
into `mpu.c` (`#include` + `MPU_SPELL_SET(6D2)`). First DIGIC 7 spell set in
qemu-eos. Verified: stock 6D2 firmware no longer hits the
`Resource/./EstimatedSize.c` RscMgr assert (nor `Irregular TotalSheets` /
`ErrorSend`) and continues through NFC/LiveView property init. Source log:
`tools/6D2-DEBUGMSG-body.txt` (522 KB, 6530 msgs, 0 drops, 71 mpu_send +
104 mpu_recv); header also archived as `tools/6D2_spells_body.h`. Note: the
body log contains raw non-UTF-8 bytes — strip NULs and invalid sequences
before feeding `extract_init_spells.py`. Candidate for upstreaming to
qemu-eos together with 0003.

### rev 2 — movie-capture replies merged (2026-08-15)

Strict addition per `.planning/spikes/005-mpu-spell-capture/movie-spells-analysis.md`
§5.2: 13 movie-only *active* replies appended to the existing photo-mode entries
(matched by request spell) — spell #2 `PROP_CARD2_EXISTS`; #20 `PROP_PICTURE_STYLE`;
spell #21 `PROP_ISO`, `PROP_HIGHISO_NOISE_REDUCTION`,
`PROP_HTP`, `PROP_CARD1/2_IMAGE_QUALITY`; #30 `PROP_AFFRAME_ENABLE_SETTING`, `PROP 80030075`,
`PROP_AFPOINT`, `PROP_AF_SELECT_FOCUS_AREA`; #36 `PROP 8004005F`, `PROP 80040060`.
No new request entries, no environmental/noise replies (temperature, battery, GPS,
shot counter, the all-zero movie Lens group), and the mode selectors
(`PROP_FIXED_MOVIE`, `PROP_LIVE_VIEW_MOVIE_SELECT`) stay at their photo values —
QEMU still boots as photo mode. Regression test (120 s, `-d debugmsg`): 472 stderr
lines vs 469 baseline, zero `ASSERT` / `Irregular TotalSheets` / `ErrorSend`, same
stopping point (NFCMgr/DbgMgr init). Two new benign
`non-empty spell #N has duplicate(s)` warnings for the now-non-empty #20/#36 —
`mpu_interpret_command()` resumes matching from the previous spell, so the
duplicate pairs are consumed in order. The new replies are not exercised within
the current boot window (the ICU never issues those requests before the stall);
they are coverage for when it does.

## 0006 — raw-video diagnostics for spike 006 (Session 4/5 card builds)

### rev 1 (session 4, superseded)

Four edits from `spikes/006-rawvideo-memory/README.md` §NEXT TEST: (1)
mlv_lite.c un-shadow `fps` — real upstream bug, outer `fps` stuck at 1
feeding `overflow_time`; (2) `raw inactive: lv=%d movie=%d gui=%d` printf in
the free branch; (3) `[probe] N MB: ok|TIMEOUT (T ms)` timing around each
`shoot_malloc_autodetect` probe in exmem.c; (4) the suites-NULL re-arm fix,
**`#if 0`'d** until step 1 confirms the dead state. Built 2026-08-15 evening,
autoexec `c6fc4936…`, mlv_lite.mo `33a57525…`.

Session 4 evidence (`evidence/photo-session-2-18h25.md`) showed edits (2) and
(3) produced no usable data: 34 `[probe]` lines self-flushed the 21-line
console (`CONSOLE_H`, src/console.c:19), and `No memory suites.` spam buried
everything else. Hence rev 2.

### rev 2 (session 5, superseded)

Keeps rev 1's edits (1), (2) and the `#if 0`'d (4) unchanged; replaces (3)
and adds the real fix for spike-006 bug 3.

- **exmem.c:217-259** — `shoot_malloc_autodetect()` now tracks slowest step and
  its size across the probe loop and prints **one** summary line afterwards:
  `[probe] max %dMB steps %d slowest %dms@%dMB last %s` (last = `ok`/`TIMEOUT`
  for the step that ended the loop). Per-step `get_ms_clock()` measurement is
  unchanged; only the printing moved out of the loop.
- **mlv_lite.c:1575-1591** — the `No memory suites.` dead-state message now
  carries the state needed to diagnose why no realloc happens, and is
  rate-limited to once per second so it no longer floods the console:
  `No memory suites. lv=%d movie=%d gui=%d rawact=%d rec=%d suites=%d/%d`
  (`rawact` = `raw_video_enabled && lv && is_movie_mode()`, `rec` =
  `raw_recording_state`).
- **mlv_lite.c:381-386, 2944-2951, 3242-3259, 3436-3437** — measured-fps stamp
  in the MLVI header. The vsync hook records the first/last VIDF timestamp and
  a frame counter (reset at record start); `finish_chunk()` recomputes
  `sourceFpsNom = (frames-1) * 1e9 / (last_us - first_us)`, `sourceFpsDenom =
  1000`, guarded on `frames >= 2 && last > first` and a `< 1000 fps` sanity
  bound, with `int64_t` intermediates. This overrides the value
  `init_mlv_chunk_headers()` wrote from `fps_get_current_x1000()`, which on the
  6D2 derives from an unmeasured `TG_FREQ_BASE`/timer A (reg A cannot be read
  back at all — see `platform/6D2.111/fps-engio_per_cam.c`) and returned
  215.430 fps for a 59.94p take and 21.545 for a 23.976p take. The formula was
  checked against the three analysed recordings in
  `evidence/mlv-analysis-2.md` and reproduces their mean-Δts fps exactly
  (23976, 59954, 59945). Upstream-quality — not gated behind spike flags.

Built 2026-08-15 18:50 local, `ML_MODULES="raw_video/mlv_lite file_man bench
dual_iso"`, `-Werror` clean. Strings verified in the **staged** `build/zip`
artifacts. md5: `zip/autoexec.bin` `54eb1339b8812bebcd9d2a2472309d7c`,
`zip/ML/modules/mlv_lite.mo` `ca38b52a268c37d94e3a899d88f6f554`.

### rev 3 (session 5, current) — the camera logs its own diagnostics

Keeps every rev-2 edit; only the three diagnostic call sites change, so the
owner no longer has to photograph the console before it self-flushes.

- **src/exmem.c:211-235** and **mlv_lite.c:391-415** — a `static void
  diag_log(const char *fmt, ...)` helper, duplicated verbatim in both files.
  It `vsnprintf`s into a 128-byte stack buffer, `printf("%s", buf)`s it (so
  console behaviour is byte-identical to rev 2), then appends a `[%d.%03d]`
  seconds.millis stamp (trailing space) plus the line to
  `ML/LOGS/RAWDIAG.LOG` via `FIO_CreateFileOrAppend` /
  `FIO_WriteFile` / `FIO_CloseFile`, opening and closing per call so a crash
  never loses earlier lines. Duplication is deliberate: exporting one helper
  from the core to modules would need `.sym` plumbing for 12 lines.
  `vsnprintf`, `snprintf`, `strlen`, `printf`, `get_ms_clock`,
  `FIO_CreateFileOrAppend`, `FIO_WriteFile` and `FIO_CloseFile` are all
  already in `build/magiclantern.sym`, so the module link needs nothing new.
- **exmem.c:283**, **mlv_lite.c:1610**, **mlv_lite.c:2107** — the `[probe] max
  …`, `No memory suites. lv=…` and `raw inactive: lv=…` lines now call
  `diag_log` instead of `printf`.
- Context safety: all three sites run in task context (shoot task via
  `shoot_malloc_autodetect`, `raw_rec_polling_cbr` for the other two), never in
  an ISR, so FIO is legal there — noted in the helper comment in both files.
  Volume is low by construction: one line per autodetect, at most one per
  second in the dead state, one per mode exit.

**No `features.h` change.** `FEATURE_SCREENSHOT` is already defined upstream at
`platform/6D2.111/features.h:5` and `screenshot.o` is in `platform/Makefile:373`
— the screenshot feature was never off on this body. The build confirms it:
`Screenshot - 10s` and `Screenshot after 10 seconds => VRAMx.BMP.` are both in
the staged `autoexec.bin`. `features.h` is therefore *not* part of this patch;
its only local edits belong to 0001 and 0005.

Built 2026-08-15 19:17 local, same `ML_MODULES` set, `-Werror` clean. Strings
verified in the **staged** `build/zip` artifacts: `autoexec.bin` carries
`[probe] max %dMB steps %d slowest %dms@%dMB last %s` and `ML/LOGS/RAWDIAG.LOG`;
`mlv_lite.mo` carries `ML/LOGS/RAWDIAG.LOG`, `raw inactive: lv=%d movie=%d
gui=%d` and `No memory suites. lv=%d movie=%d gui=%d rawact=%d rec=%d
suites=%d/%d`. md5: `zip/autoexec.bin` `8dd0cd24f24ca93a2616dddf6fe471bb`,
`zip/ML/modules/mlv_lite.mo` `737bec86ca1ff088c305a06836a0eb5e`.

**Build-system trap (worse than previously recorded).** `make clean` in
`platform/6D2.111` does NOT rebuild modules, and clearing only
`modules/build/` is *not enough either*: each module has its own
`modules/<path>/build/module_complete` marker, and while that exists the
module is relinked from a stale `.o` and copied onward with a fresh mtime —
identical size, identical content, new timestamp. A rev-2 build done that way
silently shipped the rev-1 `mlv_lite.mo`. Force a real module rebuild with:

```sh
rm -f modules/<path>/build/<mod>.* modules/<path>/build/module_complete \
      modules/build/<mod>.* modules/build/default_modules_complete \
      platform/6D2.111/build/modules/<mod>.mo \
      platform/6D2.111/build/zip/ML/modules/<mod>.mo
```

and always verify with `strings` on `build/zip/…`, never on the source tree.
