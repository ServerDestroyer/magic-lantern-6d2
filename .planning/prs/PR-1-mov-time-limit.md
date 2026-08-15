# PR 1 — 6D2: override the 29:59 MOV/MP4 recording limit

- **Target repo:** `reticulatedpines/magiclantern_simplified`
- **Target branch:** `dev` (based on `dev` @ `3f24042a4`, current local `origin/dev`)
- **Source branch:** `6d2-mov-time-limit` (1 commit: `e6cad78b6`)
- **Files:** `platform/6D2.111/consts.h` (+10), `platform/6D2.111/features.h` (+4)
- **Local branch location:** the `magiclantern_simplified` clone in this project (note: `magiclantern_simplified` is a symlink to `ml/`)
- **Patch file (durability copy):** `.planning/prs/0001-6D2-override-the-29-59-MOV-MP4-recording-lim.branch1.patch`

## Title

```
6D2: override the 29:59 MOV/MP4 recording limit
```

## PR body (ready to paste)

```markdown
This enables `FEATURE_OVERRIDE_MOVIE_30_MIN_LIMIT` on the 6D2 by adding the two
constants the existing `movtweaks.c` implementation needs:

| Constant | Value | Meaning |
|---|---|---|
| `MVR_TIME_LIMIT_NORMAL_FPS` | `0xe042ff74` | 1799000 ms (29:59) |
| `MVR_TIME_LIMIT_HIGH_FPS`   | `0xe042ff78` | 449000 ms (7:29) |

No new code — just the port-side constants plus the feature flag.

### How the addresses were established

Searching ROM0 (6D2 firmware 1.1.1, maps at 0xE0000000) for the exact
`.old_value` fields `movtweaks.c` asserts against — 1799000 (`0x1b7358`) and
449000 (`0x6d9e8`) — finds each byte pattern **exactly once in the whole 32 MiB
image**, adjacent and in that order, so there is no competing candidate.

Both are read by a two-armed getter at `0xe042fee8`: the `beq` at `0xe042fef0`
selects normal vs high FPS, and each arm is an `ldr r0, [pc, #128]` whose
literal target — `align4(PC+4) + 0x80` — resolves to `0xe042ff74` and
`0xe042ff78` respectively. Confirmed by decoding the instructions, not by
pattern-matching bytes.

### Test evidence

**Confirmed on hardware (2026-08-15, 6D2 body, firmware 1.1.1).** With the menu
limit set to 1 min, two recordings each stopped on their own at ~60 s,
producing ~448 MB MP4s that agree within 0.2%. That settled the one thing
static analysis could not: the getter at `0xe042fee8` is the function Canon
actually consults to stop recording.

`apply_patches()` validated `.old_value` on the body without tripping
`E_PATCH_OLD_VALUE_MISMATCH`, which independently confirms both constants
against this body's ROM (a mismatch rolls both patches back atomically).

Also verified statically before flashing: `movtweaks.o` exports
`change_mov_time_limit` / `mov_time_limit` / `print_mov_time_limit`, and
`autoexec.bin` contains the `MOV/MP4 time limit` menu string.

Build-tested on `dev` + this commit with gcc-arm-embedded 15.2.1
(`ML_MODULES="raw_video/mlv_lite file_man bench dual_iso"` — lua does not build
under gcc 15, which is pre-existing and unrelated).

### Risk analysis

- The patch mechanism is fail-safe: `apply_patches()` compares `.old_value`
  before writing and rolls back atomically on mismatch, so a wrong address
  fails loudly instead of patching anything. The realistic bad outcome is
  "menu applies but recording still stops at 29:59" — and the hardware test
  shows it does not.
- Feature is off by default in the menu; with the limit set to "Disabled"
  nothing is patched.
- No change to any shared source file; the diff is 6D2-platform-only.
```

## Deliberately excluded (do not add when posting)

`FEATURE_SHOW_TASKS`, `FEATURE_SHOW_CPU_USAGE`, `FEATURE_SHOW_GUI_EVENTS` from
local patch 0001 are **not** in this branch. They are implicated (not yet
proven — the A/B is spike 005 task 5) in a memory-pool regression where
`GetMemoryInformation()` reports 0/0 at `log_start()` time. Upstreaming them
before that A/B lands would ship a suspect. The MOV limit does not need them —
verified: the branch builds and the `Show tasks` / `Show CPU usage` /
`Show GUI events` menu strings are absent from the built `autoexec.bin`, while
`MOV/MP4 time limit` is present. The `internals.h` version-comment fix and the
`stubs.S` duplicate-stub removal from patch 0001 are also excluded — cosmetic,
not needed by this feature (the build proves it).

## Exact push commands for Chris

```sh
cd "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml"   # = magiclantern_simplified (symlink)

# one-time: add your fork as a remote (create the fork on GitHub first)
git remote add fork git@github.com:<YOUR_GITHUB_USER>/magiclantern_simplified.git

git push fork 6d2-mov-time-limit

# then open the PR (or use the GitHub web UI):
gh pr create --repo reticulatedpines/magiclantern_simplified \
  --base dev --head <YOUR_GITHUB_USER>:6d2-mov-time-limit \
  --title "6D2: override the 29:59 MOV/MP4 recording limit" \
  --body-file <(sed -n '/^```markdown$/,/^```$/p' \
      "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/prs/PR-1-mov-time-limit.md" \
      | sed '1d;$d')
```
