---
spike: 003
name: cheap-wins-scoping
type: standard
validates: "Given the MOV time limit and focus-box/clean-HDMI asks, when the responsible code paths are traced in ML and the 6D2 ROM, then each has a concrete implementation route and effort estimate"
verdict: VALIDATED
related: [002]
tags: [features, scoping, upstream]
---

# Spike 003: Scoping the Two Cheap Wins

## What This Validates

**Given** the two targets the upstream maintainer already flagged as cheap and
high-value for DIGIC 7 bodies,
**when** the responsible code paths are traced through `ml/` and the 6D2 ROM,
**then** each target has a concrete implementation route, the specific Canon
function or property involved, and an honest effort estimate.

The two targets (Phase C step 9):

1. **MOV recording time limit extension** — reticulatedpines called this
   "fairly easy to add" on D7 cams.
2. **Focus-box hide → clean HDMI / clear overlays** — upstream issue #221, the
   community's top ask for the new cams, driven by WalterSchulz.

This is scoping, not implementation. The deliverable is knowing what the work
actually is before committing to it.

## Research

Both features exist and work on mature bodies, so the reference implementations
are in-tree — the question is what differs on DIGIC 7. Compare against a mature
platform such as `5D3.113`, and check which `CONFIG_*` gates gate each feature.

## How to Run

Static source analysis plus ROM string/symbol search. No emulator required, no
camera required.

## What to Expect

For each of the two features: the mature-body implementation, the 6D2 gap, the
specific blocker (missing stub / unported subsystem / different hardware path /
just never enabled), and an effort estimate.

## Investigation Trail

Static analysis only. No emulator, no camera. `ml/` and `qemu-eos/` untouched;
`roms/` opened read-only for constant/string search.

### Correcting the comparison body first

The brief suggested comparing against `5D3.113`. That turned out to be the wrong
reference for both features. New ports (`6D2`, `200D`, `77D`, `750D`, `7D2`,
`5D4`, D8/DX bodies) do **not** `#include "all_features.h"` — only DIGIC 4/5
platforms do (verified: `grep -rn 'all_features.h' platform/*/features.h` returns
`100D 1100D 500D 50D 550D 5D2 5D3.113 5D3.123 600D 60D 650D 6D 700D 70D 7D EOSM`
and nothing newer). Each new cam has a short hand-written `features.h` instead.
So "5D3 has it, 6D2 doesn't" is true of almost everything and carries no signal.

The body that actually matters is the **200D** — same DIGIC 7, same
`FEATURE_VRAM_RGBA` display stack, same MMU patching, and it is the only body in
the tree with the MOV time limit working. All comparisons below use 200D.101.

### Feature 1 — searches run

1. Grepped for time/limit vocabulary across `src/ modules/ platform/`. One line
   carried the whole feature: `platform/200D.101/features.h:62` —
   `// We are able to override the MOV / MP4 29:59 limit`.
2. Traced `FEATURE_OVERRIDE_MOVIE_30_MIN_LIMIT` → `src/movtweaks.c:869-962`.
   Read the patch struct. This settled the **4 GB vs 29:59 question**: the code
   patches `.old_value = 0x1b7358` (1799000) and `0x6d9e8` (449000), which are
   milliseconds — 29m59s and 7m29s. It is the **29:59 duration timer**, not the
   FAT32 4 GB file-size limit. The 4 GB limit appears only in the bitrate
   *indicator* code (`src/bitrate.c:437`) and in `mlv_lite` chunking, and is
   untouched by this feature.
3. `grep -rn MVR_TIME_LIMIT` across the whole tree → defined **only** in
   `platform/200D.101/consts.h:163-164`. No other body has it. Confirmed absent
   from 6D2 by diffing the `#define` name sets of the two `consts.h` files.
4. Searched the 6D2 ROM for those two values. **Dead end on the first attempt**:
   zero hits in `ROM1.BIN`. I had assumed ROM1 = main firmware at `0xE0000000`.
5. Corrected the base from `platform/200D.101/consts.h:190-193`, which states for
   DIGIC 7: `ROM0_ADDR 0xe0000000 / ROM0_SIZE 0x2000000` and
   `ROM1_ADDR 0xf0000000 / ROM1_SIZE 0x1000000`. Our dumps match those sizes
   exactly (ROM0 = 32 MB, ROM1 = 16 MB), i.e. **ROM0.BIN is the main firmware and
   maps to 0xE0000000** — the inverse of the naming intuition.
   Cross-checked empirically before trusting it: at ROM0 offset `0x836ef4`
   (= `GMT_FUNCTABLE` from `platform/6D2.111/consts.h:36`) sit exactly seven
   odd-valued (Thumb) `0xe00dc???` pointers, matching `GMT_NFUNCS 0x7`; and ROM0
   offset `0x617620` (= `DRYOS_ASSERT_HANDLER`'s `debug_assert`, consts.h:11)
   begins `70 b5 14 46` — a valid Thumb prologue. Both are `0xff` padding in ROM1.
6. Re-scanned with the corrected base. Both constants found, and a
   proximity heuristic (adjacent word pair, both multiples of 1000, both plausible
   durations) reproduced the 200D's exact layout.
7. Confirmed the constants are live code, not coincidence, by decoding Thumb
   PC-relative literal loads in the surrounding ±8 KB.

### Feature 2 — searches run, including two wrong turns

1. Grepped `focus.?box|afframe|clearscreen|canon_gui_disable|front_buffer`.
   Found the two legacy mechanisms (`clear_lv_afframe`,
   `canon_gui_disable_front_buffer`) and their feature gates.
2. **Wrong turn #1**: I initially read the ask as "suppress ML's own overlays"
   (`FEATURE_CLEAR_OVERLAYS` / `clearscreen`, `src/tweaks.c:3523-3544`). Fetching
   the actual issue corrected this — see below.
3. **Wrong turn #2**: kitor's `LV_OVERLAYS_MODE` looked like the modern answer.
   Reading `src/zebra.c:409-424` shows it is **read-only detection** —
   `lv_disp_mode = LV_OVERLAYS_MODE != 3;` — telling ML whether the user has
   already pressed INFO. It does not let ML turn Canon overlays off. Useful
   context, not the route.
4. Read issue #221 directly. Opened by **evgeniimv** on 2025-08-31 (not
   WalterSchulz — he made the "clean HDMI is the top wish" comment in issue #155
   that motivated it). The decisive sentence:
   > "Canon 6D Mark II already has an option to hide most of the overlays from the
   > LiveView screen EXCEPT `Focus Box`. So, essentially to achieve
   > `Clean HDMI/Clear Overlays` feature we may only need to implement
   > `Focus Box` hiding."

   That narrows the target sharply: Canon's own INFO cycle already does the rest.
   The single remaining artifact is Canon's AF frame rectangle.
5. Checked whether the legacy mechanisms could carry that on 6D2. They cannot —
   four independent reasons, documented in Results.
6. Searched the 6D2 ROM for AF-frame reversing anchors (106 unique matching
   strings) to give the implementation a concrete starting point.

### Sources checked and found empty

- No 6D2-specific `MVR_TIME_LIMIT` work exists on any branch (`git log --all`).
- `FEATURE_CLEAR_OVERLAYS` is defined in `src/all_features.h:205` and referenced
  in `tweaks.c`/`zebra.c`, but **no** `platform/*/features.h` defines it
  explicitly — so no new cam has it.
- `PROP_AFFRAME_ENABLE_SETTING` (`src/property.h:392`) exists but is referenced
  nowhere in any `.c` file. It is a dormant guess from the original 6D, sitting
  inside `#ifdef CONFIG_6D`.

---

## Results

### Feature 1 — MOV/MP4 recording time limit

**Verdict: cheap and real. reticulatedpines' "fairly easy" is accurate.**

#### Which limit this is

The 29:59 duration timer, held in ROM as **milliseconds**. Not the 4 GB FAT32
file-size limit, which is a separate concern and is not addressed by this feature
on any body.

#### Mature-body implementation (200D.101, DIGIC 7)

| What | Where |
|---|---|
| Feature gate | `ml/platform/200D.101/features.h:63` — `#define FEATURE_OVERRIDE_MOVIE_30_MIN_LIMIT` |
| ROM addresses | `ml/platform/200D.101/consts.h:163-164` — `MVR_TIME_LIMIT_NORMAL_FPS 0xe0402bfc`, `MVR_TIME_LIMIT_HIGH_FPS 0xe0402c00` |
| Config var | `ml/src/movtweaks.c:870` — `CONFIG_INT("movie.time_limit", mov_time_limit, 30*60)` |
| Patch logic | `ml/src/movtweaks.c:885-961` — `change_mov_time_limit()` |
| Settings restore on boot | `ml/src/movtweaks.c:977-980` — in `movtweak_task_init()` |
| Menu entry | `ml/src/movtweaks.c:1042-1050` — "MOV/MP4 time limit", min 1, max 180 |

The mechanism is an MMU ROM patch of two literal-pool words
(`ml/src/movtweaks.c:936-951`):

    .addr = MVR_TIME_LIMIT_NORMAL_FPS, .old_value = 0x1b7358, // 1799000 ms = 29m59s
    .addr = MVR_TIME_LIMIT_HIGH_FPS,   .old_value = 0x6d9e8,  //  449000 ms =  7m29s
    .new_value = mov_time_limit * 1000, .size = 4

Setting exactly 30 min unpatches and reverts to stock (`movtweaks.c:952-957`).

#### The 6D2 gap

Exactly two missing constants and one missing `#define`. Confirmed by diffing the
`#define` name sets — `MVR_TIME_LIMIT_HIGH_FPS` and `MVR_TIME_LIMIT_NORMAL_FPS`
are among only nine symbols the 200D has that the 6D2 lacks.

Everything else is already in place on the 6D2:

- `CONFIG_MMU_REMAP` and `CONFIG_SGI_HANDLERS` — `ml/platform/6D2.111/features.h:21-22`
- MMU patching proven on this body — commit `2115e55fb` "6d2: enable MMU patching"
- `movtweaks.o` already builds for 6D2 (present in `platform/6D2.111/build/`)

#### Addresses located in the 6D2 ROM

Searching `roms/6D2/ROM0.BIN` (which maps to `0xE0000000` — see Investigation
Trail step 5):

| Symbol | 6D2 address | Value | 200D analogue |
|---|---|---|---|
| `MVR_TIME_LIMIT_NORMAL_FPS` | `0xE042FF74` | 1799000 (29m59s) | `0xE0402BFC` |
| `MVR_TIME_LIMIT_HIGH_FPS` | `0xE042FF78` | 449000 (7m29s) | `0xE0402C00` |

Five independent facts say these are the right words:

1. Both values are **unique in the entire 32 MB ROM** — exactly one occurrence each.
2. They are **adjacent words**, reproducing the 200D layout precisely.
3. Each is loaded by **exactly one** Thumb PC-relative literal load, and those two
   loads are **consecutive instructions** — `LDR r0,[pc,#128]` at `0xE042FEF2`
   and `0xE042FEF6`, both into `r0`. That is the shape of a small
   FPS-conditional getter returning the applicable limit.
4. Same firmware module as the LiveView AF-frame code (`CalcLvAfFrame` strings at
   `0xE042E98C`–`0xE042E9F8`), and the same `0xE04xxxxx` neighbourhood as the
   200D's constants.
5. Both sit in the **same 64 KB MMU page** (`0xE042xxxx`), so a single remapped
   page covers both — well inside `MAX_PATCHES` (`ml/src/patch.h:119-122`) and
   satisfying the no-page-spanning rule at `ml/src/patch_mmu.c:115-116`.

#### Blocker classification

**Just never enabled / never looked up.** The lowest-cost category, and it was
correctly suspected as such. Not a missing stub, not an unported subsystem, not a
hardware difference.

#### Implementation route

1. Add to `ml/platform/6D2.111/consts.h`:
   `#define MVR_TIME_LIMIT_NORMAL_FPS 0xe042ff74` and
   `#define MVR_TIME_LIMIT_HIGH_FPS 0xe042ff78`.
2. Add `#define FEATURE_OVERRIDE_MOVIE_30_MIN_LIMIT` to
   `ml/platform/6D2.111/features.h`, with the same explanatory comment style the
   200D uses.
3. Build; menu entry and the shared `movtweaks.c` code appear with no edits to
   `src/`.
4. Verify. `apply_patches()` checks `old_value` and returns
   `E_PATCH_OLD_VALUE_MISMATCH` (`ml/src/patch.h:34`) if the address is wrong, so
   a mis-located constant fails loudly rather than corrupting ROM shadow.

#### Effort

**~1 hour to write; the cost is entirely in verification.** A three-line diff
across two files, no `src/` changes. Realistically half a day to a day including
a QEMU run and a careful body test, since this is a live ROM patch on a body that
has never run our build (`ml/platform/6D2.111/README.txt`).

#### Honest uncertainty

- I could not confirm the enclosing function at `0xE042FEF2` is the recording
  limit getter rather than an unrelated duration pair. The five convergent
  signals make it very likely; only running it proves it.
- The 6D2's actual high-FPS ceiling is assumed to be 7m29s because the constant
  matches the 200D's. Unverified against the camera's spec sheet.
- Upstream notes the true maximum is unknown (`ml/src/movtweaks.c:888` — "max 90m,
  it is not determined what true max is"), so a long-recording test may hit a
  different Canon limit (thermal, file system, buffer) before the patched value.

#### Who has touched it upstream

**stephen-e**, exclusively:

- `8ddd6f173` 2024-10-13 — "200d: allow config of mov/mp4 30m time limit"
- `9f63a791c` 2024-10-31 — "mov time limit work"
- `53ee17360` 2025-04-01 — "movtweaks: hide menu if cam has no Tweak features"

Not reticulatedpines, despite his being the one who called it easy. Also relevant:
`d4c7baf08` 2025-07-13 "6D2: disable 30 min LV timer" — a *different* 30-minute
limit (LiveView powersave) that stephen-e already solved on the 6D2. Worth not
confusing the two when writing the PR description.

---

### Feature 2 — Focus box hide → clean HDMI (issue #221)

**Verdict: well-bounded but not cheap. The "just implement focus box hiding"
framing understates it by roughly an order of magnitude.**

#### What is actually being asked

From issue #221 (evgeniimv, 2025-08-31), motivated by WalterSchulz's "clean HDMI"
comment in issue #155: the 6D2's own INFO cycle already clears every LiveView
overlay **except the AF/focus box**. So the deliverable is narrow — suppress
Canon's AF frame rectangle in LiveView. This is *not* about ML's own overlays and
*not* about HDMI plumbing.

#### Mature-body implementation

Two separate legacy mechanisms, both DIGIC 4/5 era:

| Mechanism | Where | What it does |
|---|---|---|
| `clear_lv_afframe()` | `ml/src/tweaks.c:313-360` | Erases the focus box by **overwriting BMP VRAM pixels** — reads `bmp_vram()` / `get_bvram_mirror()`, scrubs white pixels in a 200×150 box around `get_afframe_pos()` |
| dirty-tracking driver | `ml/src/tweaks.c:286-311` | `af_frame_autohide` config, 20-tick countdown, `clear_lv_afframe_if_dirty()` |
| call site | `ml/src/tweaks.c:1136-1138` | inside the tweaks task loop |
| menu | `ml/src/tweaks.c:2033-2042` | "Display: Show / Auto-Hide" under "Focus box settings" |
| gate | `ml/src/all_features.h:261` | `FEATURE_LV_FOCUS_BOX_AUTOHIDE` |
| Canon GUI suppression | `ml/src/dialog_test.c:44-69` | `canon_gui_disable_front_buffer()` sets `WINSYS_BMP_DIRTY_BIT_NEG` |
| real dirty bit (5D3) | `ml/platform/5D3.113/consts.h:209` | `MEM(0x323b0+0x2c)` — a genuine Canon WINSYS struct field |
| LV widget suppression | `ml/src/gui-common.c:97-130` | `CONFIG_LVAPP_HACK` family, e.g. `ml/platform/5D3.113/internals.h:156` |

#### The 6D2 gap — four stacked blockers

1. **Gate absent, and not reachable.** `FEATURE_LV_FOCUS_BOX_AUTOHIDE` lives in
   `all_features.h`, which 6D2 does not include. Adding the `#define` alone would
   compile but not work, for reasons 2-4.

2. **`WINSYS_BMP_DIRTY_BIT_NEG` is a fake on 6D2.**
   `ml/platform/6D2.111/consts.h:91` defines it as `MEM(&winsys_bmp_dirty_bit_neg)`,
   and `ml/platform/6D2.111/function_overrides.c:59-60` is
   `// fake WINSYS_BMP_DIRTY_BIT_NEG` / `int winsys_bmp_dirty_bit_neg = 0;`.
   So `canon_gui_disable_front_buffer()` toggles an ML-local integer and does
   nothing to Canon. The same fake is present on 200D, 750D, 77D, 5D4 and 7D2 —
   this is a new-cam-wide gap, not a 6D2 oversight.

3. **The pixel-scrub cannot run.** `clear_lv_afframe()` needs the legacy 8bpp BMP
   VRAM. The 6D2 uses the RGBA/XIMR compositor path (`FEATURE_VRAM_RGBA`,
   `ml/platform/6D2.111/features.h:1`; `XIMR_CONTEXT 0x9b01c`, consts.h:170), and
   the buffers the function depends on are stubbed to zero —
   `YUV422_LV_BUFFER_DISPLAY_ADDR 0x0` and `YUV422_HD_BUFFER_DMA_ADDR 0x0`
   (consts.h:93-94), with `LV_BOTTOM_BAR_DISPLAYED 0x0 // wrong, fake bool`
   (consts.h:99). Even if it ran, ML draws into the shared Canon layer
   (`CANON_GUI_LAYER_ID 0`, `ml/src/compositor.h:60-61`) because
   `CONFIG_COMPOSITOR_DEDICATED_LAYER` is **not** set for 6D2 — only 850D, M6II,
   R and R6 have it. Scrubbing pixels there would fight Canon's own redraw.

4. **`CONFIG_LVAPP_HACK` is DIGIC 4/5 only.** Present on 5D3, 6D, 100D, 550D,
   600D, 60D, 650D, 700D, 1100D, EOSM. Absent from every DIGIC 6/7/8 body.

For completeness: `LV_OVERLAYS_MODE` — kitor's modern replacement
(`ml/src/zebra.c:413-423`, `ml/src/propvalues.c:311-331`) — is defined for 5D2,
EOSM, M50, M6II, R, R5, RP, SX70 and SX740 but **not** for 6D2/200D/77D/750D/7D2/5D4.
It only *detects* Canon's overlay state, so it does not solve #221 by itself, but
without it `lv_disp_mode` falls back to `PROP_LV_OUTPUT_TYPE` (0x80030030), and
kitor documented that DIGIC 8 has no such property
(`ml/platform/RP.160/consts.h`, comment above line 161). Whether DIGIC 7 still
fires it is **unverified and worth measuring** — if it does not, `lv_disp_mode`
is permanently 0 and ML believes Canon's display is always clean.

#### Blocker classification

**Subsystem unported** — primarily, with a secondary **hardware/firmware
genuinely differs** component (the RGBA/XIMR display stack replaced the BMP VRAM
the old hack depended on). Explicitly **not** "just never enabled": flipping the
existing feature flag produces dead code.

#### Implementation route

Do not port the legacy hack. Use the technique already proven on this body by
Feature 1 — MMU-patch or hook the Canon function that draws the AF frame.

ROM reversing anchors, located in `roms/6D2/ROM0.BIN` (base `0xE0000000`),
ordered by promise:

| Address | String | Why it matters |
|---|---|---|
| `0xE06E6DA8` | `ChangeVisibleAfFrameTouchWidget AFArea(%#x) AFMode(%#x)` | Names AF-frame **visibility** directly — start here |
| `0xE06E6DFC` | `ShowFrameWidget AFArea(%d)` | The show path |
| `0xE06E6E2C` | `GetDisplayStatusAfPoint AfArea(0x%d), AFMode(0x%d)` | State query — likely the flag to force |
| `0xE039AEB8` | `SetDisplayAFPointsToWinSystem(%d)` | Bridge from AF logic to the drawing layer |
| `0xE03990E8` | `SetDisplayAFPointsToStorage(%d)` | Persisted counterpart |
| `0xE06C0D50` | `UpdateAfFrameIcon(%d)` | Redraw trigger |
| `0xE042E9B0` | `CalcLvAfFrame %d,%d(%dx%d)` | Geometry; same module as the Feature 1 constants |
| `0xE03D0710` | `SetLiveAFFrame:%d, %d` | LV-specific setter |

Suggested order of work:

1. Disassemble around `ChangeVisibleAfFrameTouchWidget` and
   `SetDisplayAFPointsToWinSystem`; find the boolean or branch that decides
   whether the frame is drawn.
2. Prefer a single-word constant or branch patch via `apply_patches()` — same
   MMU machinery, same verification safety net, and it keeps the change reversible
   from the menu.
3. Only if no clean patch point exists, consider the property route:
   `PROP_AFFRAME_ENABLE_SETTING 0x8003004F` (`ml/src/property.h:392`) is a
   dormant, never-referenced guess from the original 6D. Treat as speculative.
   **Note the safety gate**: writing properties on D678 requires adding the ID to
   `prop_write_allow[]` in `ml/platform/6D2.111/property_whitelist.h:35-41`, and
   the file's own header warns "Writing to props can brick cams if mistakes are
   made" (line 17). Currently only four properties are whitelisted.
4. Expose it as a menu entry mirroring the 200D/6D2 house style, gated behind a
   new per-cam `FEATURE_*` in `platform/6D2.111/features.h`.

#### Effort

**2-5 days**, dominated by ROM reversing and body iteration, not coding. The
final diff is likely small — a constant plus a feature flag plus a menu entry —
but finding the patch point is the work. Emulator help is limited: QEMU does not
currently reach the 6D2 GUI (spike 001), so LiveView behaviour must be validated
on the camera.

This is a genuinely good target despite not being cheap: it is narrow, it has a
clear success criterion visible on an HDMI monitor, the patching machinery is
already proven on this body, and it is the community's most-requested item.

#### Honest uncertainty

- I identified reversing anchors, not the patch point. Which of those functions
  owns the draw decision is unknown without disassembly.
- Whether Canon's AF frame on 6D2 is drawn through the WINSYS widget path (likely,
  given `ChangeVisibleAfFrameTouchWidget`) or composited separately in the XIMR
  layer is undetermined. If the latter, effort rises toward the top of the range.
- Whether `PROP_LV_OUTPUT_TYPE` fires on DIGIC 7 is unverified and materially
  affects how ML behaves once the box is hidden.

#### Who has touched it upstream

- **stephen-e** owns the 6D2 port outright — 471 of ~500 commits repo-wide in the
  last three years, and every `platform/6D2.111/` commit except one. Directly
  relevant: `462fb40ef` 2025-07-13 "6D2: enable global draw".
- **kitor** owns the display stack this must integrate with — `94c0e0325`
  "FEATURE_VRAM_RGBA: Draw full buffer while displaying LV overlays",
  `91b67092d` "200D: Global draw in LV, with overlays", `338dd8efe` /
  `958c07fdd` (LV_OVERLAYS_MODE and D8 overlay prop IDs), `103f33d2d`
  "COMPOSITOR_DEDICATED_LAYER: Clear overlays on mode switch". His RP/R consts
  comments are the closest thing to a written method for this class of problem.
- **WalterSchulz** — 2 commits in three years. He is the requester and tester
  behind the "clean HDMI" wish, not an implementer. Route design questions go to
  stephen-e (6D2) or kitor (compositor); WalterSchulz is the right person to
  confirm the observed behaviour matches what users want.
- **reticulatedpines** — 7 commits in three years; maintainer and release owner
  rather than active author on these paths.

---

### Summary

| | Feature 1 — MOV time limit | Feature 2 — Focus box hide |
|---|---|---|
| Blocker class | Just never enabled | Subsystem unported (+ hardware differs) |
| Missing pieces | 2 consts + 1 `#define` | AF-frame draw suppression, from scratch |
| Addresses | **Found** — `0xE042FF74` / `0xE042FF78` | Anchors found; patch point not yet |
| Files to touch | `platform/6D2.111/consts.h`, `features.h` | Same two, plus reversing work |
| Effort | ~1 h to write, ≤1 day with verification | 2-5 days |
| Upstream owner | stephen-e | stephen-e (port) + kitor (compositor) |
| Confidence | High | Medium — route is sound, target unconfirmed |

Recommended order: ship Feature 1 first. It is a near-trivial diff that exercises
the whole contribution pipeline (build → QEMU → body → PR) on a change whose
correctness is machine-checkable via `E_PATCH_OLD_VALUE_MISMATCH`, and it earns
standing before proposing the larger Feature 2 work.

**Verdict rationale (PARTIAL):** the spike's hypothesis was that *both* targets
have a concrete route and effort estimate. Feature 1 exceeded that — the exact
ROM addresses are in hand. Feature 2 has a concrete route and a defensible
estimate, but its premise as a *cheap* win is wrong, and the specific patch point
is still unidentified. Half validated, half corrected.

---

## Independent verification of the Feature 1 addresses (2026-08-15)

The two addresses were found by heuristic, so before they get written into
`consts.h` they were put through a four-lens adversarial check — raw bytes,
whole-ROM uniqueness, Thumb-2 instruction decoding, and cross-body structure —
each lens instructed to *refute* rather than confirm, plus a judge that
re-derived the load-bearing facts itself.

**Verdict: CONFIRMED.** No lens refuted it, and the judge independently
reproduced the decisive evidence:

- `ROM0.BIN` is 33,554,432 bytes. Word at file offset `0x42FF74` = `0x001B7358`
  (1,799,000 ms = 29m59s); word at `0x42FF78` = `0x0006D9E8` (449,000 ms =
  7m29s). Adjacent, in the claimed order.
- Each byte pattern occurs **exactly once** in the entire 32 MiB image, and the
  adjacent pair occurs exactly once. There are zero competing candidate sites,
  which eliminates the usual "picked one of several" failure mode.
- Halfwords at `0x42FEF2` and `0x42FEF6` are both `0x4820` = `LDR r0,[pc,#128]`.
  Computing the T1 literal target by hand — `align4(PC+4) + 0x80` — resolves to
  `0xE042FF74` and `0xE042FF78` exactly.
- The surrounding shape is a textbook getter: `push {r4,lr}` / `bl` /
  `cmp r0,#1` / `beq` / ldr-literal / `pop` / ldr-literal / `pop`, with the two
  words in the trailing literal pool.

**One correction to this spike's own wording.** It described `0xE042FEF2` and
`0xE042FEF6` as "two consecutive instructions". They are not sequentially
executed — they are the two *arms* of the `beq` at `0xE042FEF0`, separated by a
`pop` at `0xE042FEF4`. This strengthens the finding rather than weakening it: a
two-arm mode selector is exactly the shape a normal-FPS/high-FPS limit getter
should have.

**Residual risk is semantic, not addressing.** Nothing static proves this getter
is the function Canon consults to *stop recording* — uniqueness and structure are
strong circumstantial support, but no lens traced the return value to a
recording-stop path. Also unverified: whether Canon caches the limit into RAM at
boot (which would make a post-boot ROM patch inert), and whether 64 KB MMU remap
of page `0xE0420000` actually works on this body.

**This cannot brick anything.** `apply_patches()` validates `.old_value` before
writing and rolls back all patches atomically, so a wrong address fails loudly
with `E_PATCH_OLD_VALUE_MISMATCH`. The realistic bad outcome is "menu applies,
recording still stops at 29m59s" — not damage.

**Cheapest next check:** ship the two defines plus
`FEATURE_OVERRIDE_MOVIE_30_MIN_LIMIT`, set the limit to an unmistakable 60 s,
record, and see whether it stops at 60 s. That one test collapses all three
residual risks at once — cheaper and more conclusive than any further static
analysis.

*(Outcome: done. Confirmed on hardware 2026-08-15 — recording stopped at ~60 s.
See patches/README.md, patch 0001.)*

---

## 2026-08-15 — Feature 2 re-scoped against upstream PR #223 (scoping now complete)

Fetched live from GitHub this session (`gh api .../issues/221`, `/issues/221/comments`,
`/pulls/223`, PR diff and comments). This corrects part of the analysis above and
replaces the Feature 2 implementation route. Verdict flipped PARTIAL → VALIDATED:
both features now have a concrete, evidence-backed route.

### Upstream state this spike had not seen

Issue #221's author **evgeniimv** did not stop at the issue. He opened
**PR #223** (2025-08-31, still open, `mergeable_state: clean`) — a 2-line diff
adding `#define FEATURE_LV_FOCUS_BOX_AUTOHIDE` to `platform/6D2.111/features.h` —
built it, ran it **on a real 6D Mark II**, and posted photos plus a video:

- **On the rear LCD it works.** The focus box disappears from LiveView.
  Combined with Canon's own INFO cycle, the LCD is clean.
- **On HDMI output it does not.** His follow-up comment (2025-08-31 19:36):
  "actually Focus Box remains on the screen, when used with HDMI output. This
  feature only clears Focus Box from the Canon display. Basically means we need
  full fledged Clear HDMI feature."
- **reticulatedpines replied** (2025-09-01): "the newer cams draw in a different
  way, and it means our old code doesn't work. If you trace what
  FEATURE_LV_FOCUS_BOX_AUTOHIDE enables, the work is done in clear_lv_afframe(),
  tweaks.c" — and invited him to Discord for the graphics-layer discussion.
  No further activity since 2025-09-01.
- Side observation in the PR: a flaky `EFLensComTask: stack warning: free=232
  used=792` on his build. reticulatedpines points at `ml/src/tskmon.c:195`,
  which already has 6D2/200D exceptions for near-limit stock tasks
  (`RTCMgr`, `idle`) but not this one. Watch for it in any body test.

### Two corrections to this spike's own Feature 2 analysis

1. **"Flipping the existing feature flag produces dead code" is wrong for the
   LCD.** PR #223 proves the 2-line enable hides the box on the camera display.
   The four-blocker analysis above correctly describes why the *legacy D4/5
   mechanisms* cannot run, but missed the mechanism that does the work on a
   `FEATURE_VRAM_RGBA` body (next section).
2. **The effort framing inverts.** The "2-5 days of ROM reversing" route above
   is not the smallest viable implementation — it is the fallback. The LCD half
   of #221 is a hardware-proven 2-line diff; the open engineering problem is
   specifically **HDMI**.

### The actual LCD mechanism on a VRAM_RGBA body (verified in source)

- `bmp_vram()` on RGBA bodies returns ML's own malloc'd 8bpp indexed buffer,
  not Canon VRAM: `ml/src/bmp.c:123-138` (`bmp_vram_indexed + BMP_HDMI_OFFSET`,
  allocated in `bmp_init()`, `ml/src/bmp.c:1479-1487`).
- At boot, ML latches Canon's GUI-layer MARV **once**: `rgb_vram_preinit()`
  (`ml/src/bmp.h:63-76`) copies `_rgb_vram_info` → `rgb_vram_info`, spun on at
  `ml/src/init.c:712`. On 6D2, `_rgb_vram_info` is `DATA_PTR 0x100b8`
  (`ml/platform/6D2.111/stubs.S:256`), and the stub's own comment says it is
  **"written to in InitializeScreen"** — i.e. Canon rewrites it when the display
  stack re-initializes.
- A 20 fps task (`redraw_task`, `ml/src/bmp.c:113-114`) converts the indexed
  buffer into that MARV's RGBA `bitmap_data` and kicks the compositor with
  `XimrExe((void*)XIMR_CONTEXT)` (`ml/src/bmp.c:263-266`;
  `XIMR_CONTEXT 0x9b01c`, `ml/platform/6D2.111/consts.h:180`).
- The copy has two modes (`ml/src/bmp.c:211-256`): when `zebra_should_run()`
  (`ml/src/zebra.c:3618` — LV idle + global draw on) it writes **every** pixel
  including fully-transparent ones; otherwise it skips transparent pixels.
  Only the write-everything mode can *remove* Canon's pixels from the shared
  layer (6D2 has no `CONFIG_COMPOSITOR_DEDICATED_LAYER`, so ML writes into
  Canon's own layer 0). That full-buffer overwrite is what erases Canon's AF
  frame; the white-pixel scrub in `clear_lv_afframe()` (`ml/src/tweaks.c:313`)
  only touches ML's own buffer on these bodies. The feature flag's real
  contribution is the dirty-tracking driver (`ml/src/tweaks.c:286-311`) plus
  the task-loop call site (`ml/src/tweaks.c:1136-1138`) that forces the erase
  cycle after the AF frame moves (`afframe_set_dirty()` callers:
  `ml/src/shoot.c:652`, `ml/src/lens.c:238`, `ml/src/vram.c:147`,
  `ml/src/zebra.c:3973`).

### Why HDMI still shows the box — ranked, measurable hypotheses

1. **Stale surface.** `rgb_vram_info` is latched once at boot from
   `_rgb_vram_info` (0x100b8), which Canon rewrites in `InitializeScreen`.
   HDMI hot-plug re-initializes the display stack; ML keeps writing the old
   panel-sized surface. Predicts: ML overlays are entirely absent from HDMI —
   which matches evgeniimv's report.
2. **Stale Ximr context.** `XIMR_CONTEXT 0x9b01c` is a fixed panel context;
   the HDMI output path may composite through a different context, so
   `XimrExe(XIMR_CONTEXT)` refreshes the wrong output. Same prediction.
3. **Separate layer for HDMI OSD.** Canon may build the external-monitor OSD
   from a different input layer that ML's overwrite never touches. Predicts:
   even a correctly re-latched surface would not clear the box → fall back to
   the ROM-patch route above.

Sibling ports document exactly this structure: `ml/platform/RP.160/consts.h:70-118`
(per-device VRAM pointers `DV_VRAM_PANEL` / `DV_VRAM_LINE` / `DV_VRAM_EVF`,
"HDMI is referenced as 'Line' in Canon functions", `DispDev` type field) and
`ml/platform/200D.101/consts.h:108-113` (`DISP_VRAM_STRUCT_PTR` via the
`"CurrentImgAddr : %#08x"` string; "the constant should be dependent on what
display is in use"). The 6D2 has none of these reversed yet.

ROM anchors for the HDMI path (string offsets in `roms/6D2/ROM0.BIN`,
base `0xE0000000`, found this session, read-only):

| Address | String | Use |
|---|---|---|
| `0xE00AB0B0` | `CurrentImgAddr` | Recover `DISP_VRAM_STRUCT_PTR` per the 200D method |
| `0xE019319D` | `VramState` | Per-device buffer listing evproc (RP method) |
| `0xE04C61DC` | `InitializeScreen` | The writer of `_rgb_vram_info`; same module as `RefreshVrmsSurface` (`0xE04C77D0`, stubs.S:250) |
| `0xE00B3AFC` | `DispDev` | Display-device type structure |

### What the 6D2 already has vs needs

Already in `ml/platform/6D2.111/stubs.S`: `RefreshVrmsSurface` (0xe04c77d0),
`XimrExe` (0xe022d5d0), `winsys_sem` (0x100b4), `display_refresh_needed`
(0x100cc), `_rgb_vram_info` (0x100b8), plus `XIMR_CONTEXT` in consts.h.
**Nothing further is needed for the LCD phase.** The HDMI phase needs the
active-surface / context discovery above; no new stubs can be named until the
phase 2 measurement below says which hypothesis holds.

### Implementation sketch (file-by-file; next session can code this without re-research)

**Phase 1 — LCD focus-box autohide (S; mirror of upstream PR #223).**
Draft diff — **UNBUILT / UNTESTED in this tree** (hardware-proven upstream by
the PR author on a real 6D2):

    --- a/platform/6D2.111/features.h
    +++ b/platform/6D2.111/features.h
    @@ (after the FEATURE_POWERSAVE_LIVEVIEW block, mirroring PR #223's placement)
    +// Upstream PR #223 (evgeniimv, tested on a real 6D2): hides Canon's AF frame
    +// on the rear LCD ~1-2 s after it moves. With Canon's INFO cycle this gives a
    +// clean rear display. Known limitation: NO effect on HDMI output (issue #221
    +// stays open for that half).
    +#define FEATURE_LV_FOCUS_BOX_AUTOHIDE

Notes: no prop writes anywhere in the enabled path (`clear_lv_afframe()` only
reads), so `property_whitelist.h` is untouched — `all_features.h:251-267` groups
this flag under `CONFIG_PROP_REQUEST_CHANGE`, but that gate is about its
*neighbours* (snap/zoom features write `PROP_LV_AFFRAME`); 6D2 defines the
CONFIG anyway. Menu appears under Prefs → Focus box settings
(`ml/src/tweaks.c:1995`). **Contention:** `platform/6D2.111/features.h` is
currently carrying spike 005's A/B experiment (four features commented out) —
do not apply anything to that file until Track A finishes.

**Phase 2 — one measurement build (S; decides the HDMI route).**
Add a temporary debug print (Debug menu or console) showing, before and after
HDMI hot-plug: `MEM(0x100b8)` vs the cached `rgb_vram_info`, plus
`rgb_vram_info->width/height`, plus `hdmi_code`. One body session with an HDMI
monitor then discriminates the hypotheses:

- `_rgb_vram_info` changed and ML overlays absent on HDMI → hypothesis 1 →
  phase 3a.
- Unchanged, overlays still absent → hypothesis 2 → phase 3b.
- Re-latching in a debugger changes nothing → hypothesis 3 → phase 4.

Also record whether Canon's INFO cycle affects the HDMI picture at all on this
body (issue #221 assumes it does; nobody has stated it for HDMI specifically).

**Phase 3a — re-latch the surface on display change (M; likely ~30-60 lines).**

- `ml/src/bmp.h`: declare `void rgb_vram_reinit(void);`
- `ml/src/bmp.c`: implement — re-read `_rgb_vram_info` (non-XCM path of
  `rgb_vram_preinit()`), swap `rgb_vram_info` if changed, log the new MARV's
  `width/height`. NULL-guard: keep the old pointer if Canon's is transiently
  NULL mid-reinit.
- `ml/src/vram.c:716-724`: in `PROP_HANDLER(PROP_HDMI_CHANGE)` and
  `PROP_HANDLER(PROP_HDMI_CHANGE_CODE)`, call `rgb_vram_reinit()` under
  `#ifdef FEATURE_VRAM_RGBA`.
- `ml/src/bmp.c:243-256`: derive the copy extent from
  `rgb_vram_info->width/height` instead of the assumed 960×540
  (`BMP_VRAM_SIZE`); the DIGIC X loop at `ml/src/bmp.c:220-241` is the
  row-stride template. Without this, a 1920×1080 HDMI surface gets a
  quarter-height garbled overlay — visual only, but useless.

**Phase 3b — find the HDMI Ximr context (M).** Disassemble
`RefreshVrmsSurface` (0xe04c77d0) and `InitializeScreen` (0xE04C61DC) for the
context-selection path; a second XimrContext or a rewritten field inside
0x9b01c will show up there. Then pass the live context to `XimrExe()` instead
of the fixed constant.

**Phase 4 — suppress Canon's AF-frame draw in ROM (L; the original route
above).** Unchanged: anchors `ChangeVisibleAfFrameTouchWidget` (0xE06E6DA8),
`SetDisplayAFPointsToWinSystem` (0xE039AEB8) etc.; MMU patch via
`apply_patches()`. Kills the box on *every* output at the source, independent
of ML's refresh loop. Now strictly a fallback: only if phase 3 dead-ends, or if
upstream wants Canon-level suppression.

### Risk

- Phase 1: minimal. No prop writes, no ROM patches, RAM-only drawing; already
  run on real 6D2 hardware upstream. Watch for the `EFLensComTask` stack
  warning noted in the PR.
- Phase 3: RAM-only writes into Canon's GUI surface; worst case is visual
  garbage on the external monitor, recovered by reboot. No brick vector.
- Phase 4: MMU ROM patch; same machinery as the (now hardware-proven) MOV
  limit, fails loudly via `E_PATCH_OLD_VALUE_MISMATCH`.

### Body test (Chris, ~15 min, after Track A frees the build tree)

1. Build with phase 1 (+ phase 2 print), sync `build/zip/ML/` + `autoexec.bin`.
2. LiveView, move the focus box (touch) → box shows, then vanishes within ~2 s
   on the LCD. INFO-cycle to the cleanest state → LCD fully clean.
3. Connect the HDMI monitor. Record: (a) is the box visible on HDMI (expected
   yes, per PR #223); (b) do ML overlays/menu appear on HDMI at all (the single
   most informative observation); (c) phase 2 debug values before/after plug.
4. No card format in-camera; normal shutdown.

### Status

Feature 1: **shipped and hardware-confirmed** (patch 0001, 2026-08-15).
Feature 2: scoping **complete** — LCD half is a proven 2-line enable waiting on
the build tree; HDMI half has a phased, measurable route with named files,
addresses, and a decision procedure. Remaining unknowns are exactly the two
measurements phase 2 exists to take.
