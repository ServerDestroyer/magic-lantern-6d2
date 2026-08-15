# Patches against `magiclantern_simplified`

`ml/` is a clone of someone else's repo and is gitignored here, so any work in it
would be invisible to this repo and lost on a `git checkout`. Patches live here
instead.

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

Built and inspected, **not yet run on the camera**:

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

**On-camera test:** set the limit to 60 s, record, and check it stops at 60 s.
That single test settles the only remaining doubt — whether this getter is the
one Canon consults to stop recording.

## Not included, and why

`FEATURE_RAW_HISTOGRAM` / `FEATURE_RAW_SPOTMETER` were attempted and dropped.
Their gate (`CONFIG_RAW_PHOTO || CONFIG_RAW_LIVEVIEW`) does pass on the 6D2, but
the macro only switches the *raw variant* of code inside `histogram.c`, and the
6D2 defines none of `FEATURE_HISTOGRAM`, `FEATURE_ZEBRA`, or `FEATURE_OVERLAYS`.
Enabling it alone compiles fine and displays nothing — the exact
"compiles and silently does nothing" trap that the property whitelist also sets.
It needs the histogram display infrastructure first, which is real work requiring
on-camera verification.
