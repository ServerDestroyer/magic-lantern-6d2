# FEATURE_MATRIX.md — Magic Lantern on the Canon EOS 6D Mark II

**Date:** 2026-08-15 (classification completed same day — 0 unknown rows remain)
**Tree analysed:** ml/ = `reticulatedpines/magiclantern_simplified`, HEAD `3f24042a4` (2026-08-02)
**Platform:** ml/platform/6D2.111 (firmware 1.1.1, DIGIC 7, Cortex-A9, dual core)
**Method:** static source analysis only. No camera, no QEMU run. Nothing in ml/ or qemu-eos/ was modified.
The 2026-08-15 completion pass additionally used upstream GitHub state (issue #221, PR #223) and the
hardware results recorded in patches/README.md; rows marked "Done locally" reflect this repo's
patches, not upstream HEAD.

---

## Method

Every claim below comes from a file in the tree, not from forum posts or recollection.

1. **Effective macro sets were computed with the real C preprocessor**, not by eyeballing headers.
   `cpp -dM -I platform/<CAM> -I src` over ml/src/config-defines.h, which includes the platform's
   internals.h, then ml/src/internals-common.h, then the platform's features.h. This resolves the
   derived macros (`CONFIG_DIGIC_678X`, `CONFIG_TSKMON`, `CONFIG_CORTEX_A9` …) that no single file states.
   Result: **6D2 = 34 macros** (8 `FEATURE_`, 26 `CONFIG_`) vs **5D3.113 = 144** (96 / 48).

2. **Two reference points, not one.** 5D3.113 is the mature D5 baseline the plan asked for. But the
   decisive comparison is against the *DIGIC 6/7/8/X siblings* in the same tree — 200D.101, 77D.110,
   M50.110, 850D.100, R.180, RP.160, R5.152, R6.150, SX70.111, SX740.102, M6II.111, 5D4.133,
   80D.103, 750D.110. If a sibling on the same silicon has a feature on and the 6D2 does not, that is
   "never enabled". If *no* D6+ port has it, it is a family-wide subsystem gap, not a 6D2 regression.

3. **Link-blocker test.** For each disabled feature, its `#ifdef FEATURE_X … #endif` regions were
   extracted from every compiled source file, and the identifiers inside were checked against the
   symbols the 6D2 actually provides (ml/platform/6D2.111/consts.h `#define`s +
   ml/platform/6D2.111/stubs.S `THUMB_FN`/`DATA_PTR`/`NSTUB` entries). A feature that references a
   symbol the 6D2 lacks is **Blocked**; one that does not is a **candidate for a one-line enable**.

4. **Upstream attribution** from `git -C ml log`. Note for the record: the commit author name is
   **`stephen-e`**, and `git log --format='%an <%ae>'` shows `stephen-e` and `reticulatedpines` share
   the GitHub noreply address `33672591+reticulatedpines@users.noreply.github.com` — same person.
   34 of the 37 commits ever touching ml/platform/6D2.111 are his; `kitor` has 1, `olicooper` 2.
   **WalterSchulz** has touched nothing 6D2-specific; his only work in the last 3 years is DXO
   dynamic-range data in ml/src/raw.c for the R5 and 80D (`ea2d2a2aa`, `436ae766f`, 2026-06-15).

---

## Two structural findings that frame everything below

**A. The 6D2 port is opt-in, not opt-out.** ml/platform/5D3.113/features.h begins
`#include "all_features.h"` and then `#undef`s a dozen things. ml/platform/6D2.111/features.h does
**not** include it — it names 8 features explicitly. Every DIGIC 6/7/8/X port in this tree does the
same, and all of them land in the 18–45 macro range. So "missing on 6D2" usually means "not yet
turned on anywhere on modern DIGIC", not "removed from the 6D2".

**B. The code is already compiled in.** ml/platform/6D2.111/build/ contains `zebra.o`,
`histogram.o`, `falsecolor.o`, `vectorscope.o`, `focus.o`, `shoot.o`, `tweaks.o`, `hdr.o`,
`flexinfo.o`, `movtweaks.o`, `fps-engio.o`, `lv-img-engio.o`, `beep.o`, `bitrate.o`, `picstyle.o`.
These files build today with their `FEATURE_` macros undefined, so the feature bodies are
preprocessed away. For anything marked "never enabled/tested" below, the change is a `#define` in
ml/platform/6D2.111/features.h — the object file is already in the binary.

**C. Property writes are whitelisted per-property.** `CONFIG_PROP_REQUEST_CHANGE` *is* defined for
the 6D2, but ml/platform/6D2.111/property_whitelist.h allows `prop_request_change()` for exactly four
properties: `PROP_ICU_AUTO_POWEROFF`, `PROP_BUTTON_ASSIGNMENT`, `PROP_REMOTE_SW1`, `PROP_REMOTE_SW2`.
`PROP_MVR_REC_START` is denied even for reads ("probably related to MVR stubs being all wrong").
A large family of features is gated on `CONFIG_PROP_REQUEST_CHANGE` in ml/src/all_features.h and will
therefore **compile but silently do nothing** until the property it writes is added to
`prop_write_allow[]`. That is a per-feature reversing + verification task, not a free `#define`.

---

## Status vocabulary

| Status | Meaning |
|---|---|
| **On** | Macro defined for 6D2; feature is in the build. |
| **Partial** | Enabled, but upstream's own comment or commit message says it is incomplete or unverified. |
| **Off** | Source file is compiled into the 6D2 binary, macro undefined, and no missing symbol was found. A `#define` is the whole code change. |
| **Off (prop)** | As Off, but the feature writes a Canon property that is not in `prop_write_allow[]`. Compiles, does nothing, until whitelisted. |
| **Blocked** | Enabling the macro references a const or stub the 6D2 does not have. Will not link / will not work. |
| **Unported** | The `CONFIG_` this depends on is defined by no DIGIC 6/7/8/X port in the tree. Family-wide gap. |

## Reason categories (exactly one per row)

`never enabled` · `stub missing` · `hw/fw differs` · `subsystem unported`

## Effort scale

`S` one-line define + rebuild + verify · `M` a few addresses to reverse, or one property to
whitelist and prove safe · `L` significant reversing or new code for this body · `XL` port a
subsystem across the whole D678X family

---

## Matrix

### 1. Already working (the current baseline)

| Feature | Status | Reason | Effort | Upstream | Evidence |
|---|---|---|---|---|---|
| Global draw (bitmap overlay) | On | — | — | stephen-e `462fb40ef` "6D2: enable global draw" | ml/platform/6D2.111/features.h |
| RGBA VRAM draw path (D7 compositor) | On | — | — | stephen-e | ml/platform/6D2.111/features.h `FEATURE_VRAM_RGBA`; ml/platform/6D2.111/consts.h `XIMR_CONTEXT`, `WINSYS_BMP_DIRTY_BIT_NEG` |
| MMU ROM→RAM remapping | On | — | — | stephen-e `2115e55fb` "6d2: enable MMU patching" | ml/platform/6D2.111/features.h `CONFIG_MMU_REMAP`, `CONFIG_SGI_HANDLERS` |
| Intervalometer | On | — | — | stephen-e `ec3bc02bc` "6D2: enable intervalometer" | ml/platform/6D2.111/features.h |
| Powersave / 30-min LiveView timer off | On | — | — | stephen-e `d4c7baf08` "6D2: disable 30 min LV timer" | ml/platform/6D2.111/features.h `FEATURE_POWERSAVE_LIVEVIEW` |
| Picture style | On | — | — | kitor `18a5953ee` "Picture style consolidation and update for Digic 6+" | ml/platform/6D2.111/features.h; ml/src/picstyle.c |
| ROM auto-backup to card | On | — | — | stephen-e `644565f8f`, `13bf5592f` | ml/platform/6D2.111/features.h `CONFIG_AUTOBACKUP_ROM` |
| Don't Click Me (dev hook) | On | — | — | stephen-e `32f1f3ba3` | ml/platform/6D2.111/features.h |
| Screenshot | Partial | never enabled | S | stephen-e `d4cb9e8b3` | ml/platform/6D2.111/features.h; 200D's note (ml/platform/200D.101/features.h) says "wrong colorspace and not dumping all the images that old cams support" |
| Crash log | Partial | hw/fw differs | M | stephen-e `d4cb9e8b3` | ml/platform/200D.101/features.h: "no stack unwinding, since existing code assumes ARM, not Thumb" |
| Shutter count | Partial | stub missing | M | stephen-e `339a6d5f1` | ml/platform/6D2.111/features.h: "Half works? shutter_count_plus_lv_actuations seems to go up correctly, but shutter_count doesn't seem to change" |
| Raw LiveView | On | — | — | stephen-e | ml/platform/6D2.111/features.h `CONFIG_RAW_LIVEVIEW`; ml/platform/6D2.111/consts.h `RAW_LV_EDMAC_CHANNEL_ADDR` |
| mlv_lite (raw video) | Partial | — | L to finish | stephen-e `e77bd879a` "6D2: mostly working raw video" (2025-09-27), `fd11ca504`, `9f213efc2`, `aa2c66d06` | ml/platform/6D2.111/modules.included; ml/platform/6D2.111/function_overrides.c:356 "these are only here because mlv_lite module has them as deps" |
| dual_iso | Partial | — | M | stephen-e `87f24974d` "6d2: enable dual ISO" | Shipped but hidden: in both ml/platform/6D2.111/modules.included and modules.hidden. ml/modules/dual_iso/dual_iso.c:1298 `is_camera("6D2","1.1.1")`; :376 "logic used doesn't work for the 6D2 data structure" |
| bench, file_man | On | — | — | stephen-e `41ec65338` | ml/platform/6D2.111/modules.included |
| FPS registers | Partial | stub missing | M | stephen-e `53791dafe` "6D2: fps reg a and reg b found, probably" | ml/platform/6D2.111/fps-engio_per_cam.c |
| Prop writes (4 properties) | Partial | — | M each | stephen-e `288f6bde2` | ml/platform/6D2.111/property_whitelist.h |

### 2. Never enabled / tested — code compiles, no missing symbol (cheapest category)

| Feature | Status | Reason | Effort | Upstream | Evidence |
|---|---|---|---|---|---|
| Show tasks | **Done locally (2026-08-15)** | never enabled | — | stephen-e — on for 12 of 14 D6/7/8/X siblings | Enabled and flashed with patches/0001 (commit 93b53bb "debug displays"). Upstream evidence: ml/src/debug.c:1050, ml/src/tasks.c:30,92,137; `CONFIG_TSKMON` unconditional at ml/src/config-defines.h:31. Temporarily commented out in the working tree for spike 005's A/B — that is an experiment, not a revert. |
| Show CPU usage | **Done locally (2026-08-15)** | never enabled | — | stephen-e — on for 12 siblings | Same patch 0001 / same A/B note. ml/src/debug.c:1070, ml/src/tasks.c:27,38 |
| Show GUI events | **Done locally (2026-08-15)** | never enabled | — | stephen-e — on for 12 siblings | Same patch 0001 / same A/B note. ml/src/debug.c:1081 |
| Show free memory | Off | never enabled | S | stephen-e — on for 10 siblings | ml/src/mem.c:1104–1715, ml/src/debug.c:1843. The one EDMAC reference (ml/src/mem.c:1390) sits inside `#ifndef CONFIG_DIGIC_678X`, so it is excluded on 6D2 — not a blocker |
| Show image buffers info | Off | never enabled | S | none on 6D2 | ml/src/debug.c |
| Unmount SD card | Off | never enabled | S | none on 6D2 | ml/src/debug.c |
| Sticky half-shutter | Off | never enabled | S | stephen-e — on for 77D | ml/src/tweaks.c; ml/platform/77D.110/features.h. 200D has it commented: "Works but likely not required" |
| Disk log (fast logging) | Off | never enabled | S | stephen-e — on for 200D, M6II | ml/platform/200D.101/features.h `FEATURE_DISK_LOG` |
| Console→UART duplication | Off | never enabled | S | stephen-e — on for 200D only | ml/platform/200D.101/features.h `CONFIG_COPY_CONSOLE_TO_UART` |
| SD autotune | Off | never enabled | S | stephen-e `d21e9b946` — on for 200D | **Deliberately off.** ml/platform/6D2.111/features.h: "exists, but doesn't seem to improve over stock speeds" |
| Additional version string | Off | never enabled | S | stephen-e | Explicitly `#undef CONFIG_ADDITIONAL_VERSION` in ml/platform/6D2.111/features.h; on for M50, R, SX740, 80D, 750D |
| Show EDMAC info | Off | never enabled | S (no-op) | — | Macro exists in ml/src/all_features.h but a full-tree grep finds **no consumer**. Enabling it does nothing. |
| Zebras, fast zebras | Off | never enabled | M | nobody — on no D6+ port | ml/src/zebra.c. LV YUV buffers exist: ml/platform/6D2.111/consts.h `YUV422_LV_BUFFER_1/2/3`, `YUV422_LV_BUFFER_DISPLAY_ADDR`, `YUV422_LV_PITCH` |
| Histogram | Off | never enabled | M | nobody — on no D6+ port | ml/src/histogram.c, ml/src/zebra.c; `histogram.o` in ml/platform/6D2.111/build/ |
| Raw histogram, raw spotmeter | Off | never enabled | M | nobody | ml/src/histogram.c, ml/src/zebra.c. Gate in ml/src/all_features.h is `CONFIG_RAW_PHOTO \|\| CONFIG_RAW_LIVEVIEW`; 6D2 has the latter |
| Waveform | Off | never enabled | M | nobody | ml/src/zebra.c |
| Vectorscope | Off | never enabled | M | nobody | ml/src/vectorscope.c; `vectorscope.o` in build/ |
| False colour | Off | never enabled | M | nobody | ml/src/falsecolor.c; `falsecolor.o` in build/ |
| Spotmeter | Off | never enabled | M | nobody | ml/src/shoot.c, ml/src/zebra.c |
| Clear overlays | Off | never enabled | M | nobody | ml/src/tweaks.c, ml/src/zebra.c |
| Overlays in playback mode | Off | never enabled | M | nobody | ml/src/gui-common.c, ml/src/zebra.c |
| Ghost image | Off | never enabled | M | nobody | ml/src/cropmarks.c, ml/src/zebra.c |
| Rec indicator / rec notify | Off | never enabled | M | nobody | ml/src/bitrate.c, ml/src/movtweaks.c |
| Movie logging, movie restart | Off | never enabled | M | nobody | ml/src/movtweaks.c, ml/src/lens.c |
| Motion detect | Off | never enabled | M | nobody | ml/src/shoot.c |
| Snap sim | Off | never enabled | S | nobody | ml/src/shoot.c |
| Screen layout | Off | never enabled | M | nobody | ml/src/movtweaks.c, ml/src/tweaks.c |
| Colour scheme | Off | never enabled | S | nobody | ml/src/menu.c, ml/src/tweaks.c |
| Upside down | Off | never enabled | S | nobody | ml/src/gui-common.c, ml/src/tweaks.c |
| Warnings for bad settings | Off | never enabled | S | nobody | ml/src/tweaks.c |
| Play timelapse | Off | never enabled | M | nobody | ml/src/tweaks.c |
| DIGIC focus peaking | Off | never enabled | M | nobody | ml/src/tweaks.c |
| LV brightness/contrast, saturation, crazy colours, display gain | Off | never enabled | M | nobody | ml/src/tweaks.c, ml/src/lv-img-engio.c |
| LV display presets | Off | never enabled | M | nobody | ml/src/tweaks.c, ml/src/gui-common.c |
| FPS ramping | Off | never enabled | M | depends on FPS override below | ml/src/fps-engio.c |
| Vignetting correction | Off | never enabled | M | nobody | ml/src/lv-img-engio.c |
| Force HDMI VGA | Off | never enabled | M | nobody | ml/src/movtweaks.c, ml/src/tweaks.c. *Related to the clean-HDMI deep dive owned by another agent — listed here for completeness only.* |
| Magic Zoom full screen | Off | never enabled | M | nobody | ml/src/zebra.c. Gated on `CONFIG_CAN_REDIRECT_DISPLAY_BUFFER_EASILY` in ml/src/all_features.h, which no D6+ port defines |

### 3. Off (prop) — compiles, but needs a property added to `prop_write_allow[]`

All gated on `CONFIG_PROP_REQUEST_CHANGE` in ml/src/all_features.h. 6D2 defines that macro, so they
build; the runtime write is refused by ml/platform/6D2.111/property_whitelist.h. Reason for all:
`never enabled`. Upstream: stephen-e wrote the whitelist mechanism; none of these properties has been
enabled for the 6D2. Effort `M` each — the file's own instruction is "enable properties one at a time
after checking correctness via reversing, tests, etc.", and it warns "Writing to props can brick cams".

| Feature | Evidence |
|---|---|
| White balance | ml/src/shoot.c, ml/src/tweaks.c |
| Expo: ISO / shutter / aperture / preset | ml/src/shoot.c, ml/src/tweaks.c |
| Expo ISO via DIGIC | ml/src/lv-img-engio.c, ml/src/shoot.c |
| Rec picture style | ml/src/picstyle.c, ml/src/shoot.c |
| HDR bracketing | ml/src/shoot.c, ml/src/flexinfo.c |
| Follow focus / rack focus / focus stacking | ml/src/focus.c, ml/src/shoot.c |
| LV zoom settings, LV zoom sharp contrast | ml/src/shoot.c, ml/src/lens.c |
| LV focus box snap, snap-to-x5-raw | ml/src/shoot.c, ml/src/tweaks.c — these write `PROP_LV_AFFRAME`. **Autohide moved out of this bucket**: it sits in the same `CONFIG_PROP_REQUEST_CHANGE` block of all_features.h:251-267 but its enabled path makes no prop write (ml/src/tweaks.c:313-368 only reads), and upstream PR #223 ran it on a real 6D2 with the stock 4-property whitelist. Reclassified as plain `never enabled` — see its row in section 4. |
| Sticky DOF | ml/src/tweaks.c |

### 4. Blocked — stub or const missing (solvable by reversing this ROM)

*(Also holds, for continuity, the three rows resolved or reclassified on 2026-08-15: the MOV limit
— formerly counted here as `stub missing`, now Done locally — and the two rows the former
"Focus box hide / clean HDMI — unknown" entry split into.)*

| Feature | Status | Reason | Effort | Upstream | Evidence |
|---|---|---|---|---|---|
| Cropmarks | Blocked | stub missing | M | stephen-e — **on for 200D, 77D, M50, R, SX740, M6II, 80D, 750D** | ml/platform/6D2.111/features.h: `//#define FEATURE_CROPMARKS // wants IMGPLAY_ZOOM_LEVEL_ADDR`. Needed at ml/src/zebra.c:4277. 200D has the const (ml/platform/200D.101/consts.h), 6D2 does not |
| Raw zebras | Blocked | stub missing | M | nobody | Needs `IMGPLAY_ZOOM_LEVEL_ADDR` (ml/src/zebra.c:617) **and** `CONFIG_RAW_PHOTO`, which no D6+ port defines |
| SET+main dial shortcuts | Blocked | stub missing | M | nobody | Needs `IMGPLAY_ZOOM_LEVEL_ADDR`, ml/src/tweaks.c:460 |
| LV focus box fast | Blocked | stub missing | M | nobody | Needs `IMGPLAY_ZOOM_LEVEL_ADDR`, ml/src/tweaks.c:1097 |
| Arrow shortcuts | Blocked | stub missing | S–M | nobody | Needs `ARROW_MODE_TOGGLE_KEY`, ml/src/tweaks.c:1302, ml/src/menuindex.c:122 |
| Trap focus | Blocked | stub missing | M | nobody | Needs `DISPLAY_TRAP_FOCUS_MSG`, `_MSG_BLANK`, `_POS_X/_Y` — ml/src/shoot.c:5045,5087. All four present in ml/platform/5D3.113/consts.h, absent from 6D2's |
| Show CMOS temperature | Blocked | stub missing | S–M | nobody | Needs `EFIC_CELSIUS`, ml/src/debug.c:747,1145 |
| Beep | Blocked | stub missing | L | nobody | Needs `ASIF_MAX_VOL` (ml/src/beep.c:1004) and `CONFIG_BEEP`, defined by no D6+ port |
| Force LiveView | Blocked | stub missing | M | nobody | Needs `GUIMODE_MOVIE_ENSURE_A_LENS_IS_ATTACHED`, `GUIMODE_MOVIE_PRESS_LV_TO_RESUME` — ml/src/movtweaks.c:399,966 |
| FlexInfo (custom info display) | Blocked | stub missing | L | nobody | Needs `CARD_A_MAKER`, `CARD_A_MODEL`, `DISPLAY_BATTERY_POS_X/Y`, `DISPLAY_CLOCK_POS_X/Y` and more — ml/src/flexinfo.c:15. `flexinfo.o` already builds |
| FPS override | Blocked | stub missing | L | stephen-e `53791dafe` (regs "found, probably"), `ffef459f0` | Needs `FRAME_SHUTTER_BLANKING_WRITE`, ml/src/fps-engio.c:1534. Partial groundwork in ml/platform/6D2.111/fps-engio_per_cam.c |
| MOV/MP4 29:59 recording limit override | **Done locally (2026-08-15)** | never enabled | — | stephen-e — on for 200D; addresses for 6D2 found by spike 003 | Was misclassified "stub missing": the two consts were simply never looked up. Found (`0xE042FF74`/`0xE042FF78`), enabled, **confirmed on the real camera** — recording stopped at ~60 s with a 1-min limit. patches/0001, patches/README.md. Not yet upstreamed (Track C). |
| Focus box autohide (rear LCD) | Off | never enabled | S | evgeniimv, upstream **PR #223** (open, hardware-tested on a real 6D2) | 2-line enable of `FEATURE_LV_FOCUS_BOX_AUTOHIDE` (ml/src/all_features.h:261; driver ml/src/tweaks.c:286-313, call site ml/src/tweaks.c:1136). Works via the full-buffer RGBA overwrite (ml/src/bmp.c:211-217), not the legacy pixel scrub. See spike 003, 2026-08-15 section. |
| Clean HDMI (focus box on external monitor) | Blocked | subsystem unported | M–L | nobody — PR #223 confirmed it does NOT extend to HDMI | ML latches Canon's panel surface once at boot (ml/src/init.c:712, ml/src/bmp.h:63-76; `_rgb_vram_info` stubs.S:256) and refreshes a fixed panel Ximr context (ml/src/bmp.c:263-266, consts.h:180); no D7 port follows the display to HDMI. Phased route in spike 003, 2026-08-15 section. |

### 5. Unported — no DIGIC 6/7/8/X port in this tree defines the required CONFIG

Verified by taking the union of effective macros across all 14 D6/7/8/X platforms and confirming
none of these appears. These are family-wide gaps, not 6D2 regressions. Upstream owner for all:
stephen-e (nobody has attempted them on modern DIGIC).

| Feature | Missing CONFIG | Reason | Effort | Evidence |
|---|---|---|---|---|
| Magic Zoom | needs `REG_EDMAC_WRITE_HD_ADDR`, `REG_EDMAC_WRITE_LV_ADDR` | hw/fw differs | XL | ml/src/zebra.c:3189. ml/src/mem.c:1388 states it outright: "These addresses are not yet known for modern Digic. They may not even exist as the drawing routines are changed significantly by Ximr." |
| Focus peaking | needs `YUV422_HD_BUFFER_2` | hw/fw differs | L | ml/src/zebra.c:1413. 6D2 has only `YUV422_HD_BUFFER_DMA_ADDR` (ml/platform/6D2.111/consts.h); the numbered HD buffers are D5-era |
| Defishing preview | `CONFIG_DISPLAY_FILTERS` + `YUV422_HD_BUFFER_2` | hw/fw differs | L | ml/src/tweaks.c:2966 |
| Anamorphic preview | `CONFIG_DISPLAY_FILTERS` | hw/fw differs | L | ml/src/tweaks.c, ml/src/zebra.c |
| Play: compare images / exposure fusion | needs `YUV422_HD_BUFFER_1/2` | hw/fw differs | L | ml/src/shoot.c:1299,1340 |
| Play: exposure adjust | `CONFIG_DISPLAY_FILTERS` family | hw/fw differs | L | ml/src/shoot.c, ml/src/tweaks.c |
| HDR video | `CONFIG_FRAME_ISO_OVERRIDE`, consts `FRAME_ISO`, `FRAME_BV` | hw/fw differs | XL | ml/src/hdr.c, ml/src/state-object.c |
| Gradual exposure | `CONFIG_FRAME_ISO_OVERRIDE` | hw/fw differs | XL | ml/src/movtweaks.c:711 |
| Shutter fine tuning | `CONFIG_FRAME_SHUTTER_OVERRIDE`, const `FRAME_SHUTTER_TIMER` | hw/fw differs | XL | ml/src/lv-img-engio.c:699 |
| Audio meters + all audio controls | `CONFIG_AUDIO_CONTROLS` | subsystem unported | XL | ml/src/audio-common.c, ml/src/audio-ak.c; 8 features gated on it in ml/src/all_features.h |
| Mirror lockup | `CONFIG_MLU` | subsystem unported | L | ml/src/shoot.c |
| Bulb timer (+ show previous pic) | `CONFIG_BULB`, `CONFIG_SEPARATE_BULB_MODE` | subsystem unported | L | ml/src/shoot.c |
| Electronic level indicator | `CONFIG_ELECTRONIC_LEVEL` | subsystem unported | L | ml/src/zebra.c; `electronic_level.o` builds but the CONFIG is off |
| ExpSim | `CONFIG_EXPSIM` | subsystem unported | L | ml/src/shoot.c, ml/src/tweaks.c |
| Expo lock / expo override | `ISO_ADJUSTMENT_ACTIVE` const + prop writes | subsystem unported | L | ml/src/shoot.c:3052, ml/src/lens.c:1545 |
| Raw photo (silent pics, raw zebras) | `CONFIG_RAW_PHOTO` | subsystem unported | XL | 6D2 has `CONFIG_RAW_LIVEVIEW` only (ml/platform/6D2.111/features.h) |
| AFMA microadjustment | `CONFIG_AFMA` | subsystem unported | L | 5D3 has it via ml/platform/5D3.113/afma.h; no equivalent file for 6D2 |
| Battery info | `CONFIG_BATTERY_INFO` | subsystem unported | M | ml/src/battery.c |
| Zoom trick / half-shutter zoom | `CONFIG_ZOOM_HALFSHUTTER_UILOCK` | hw/fw differs | L | ml/src/tweaks.c, ml/src/shoot.c |
| Dual slot handling | `CONFIG_DUAL_SLOT` | hw/fw differs | S | 6D2 is single-SD; correctly absent. Not a gap. |

### 6. Modules — what the 6D2 zip actually ships

ml/platform/6D2.111/modules.included lists **4**: `bench`, `dual_iso`, `file_man`, `mlv_lite`.
ml/platform/5D3.113/modules.included lists **20**. ml/platform/6D2.111/modules.hidden hides 16 from
the GUI, of which only `dual_iso` is also shipped — so `dual_iso` is present but hidden. Every module
still *builds* (all 20 `.mo` files exist under ml/modules/build/); the per-camera filter is
`modules.included` alone. Mechanism added by stephen-e `41ec65338` "modules: limit modules in zip,
allow hidden modules".

| Module | 6D2 | 5D3 | Reason | Effort | Evidence |
|---|---|---|---|---|---|
| bench, file_man | shipped | shipped | — | — | ml/platform/6D2.111/modules.included |
| mlv_lite | shipped | shipped | — | — | Promoted from hidden→included by `e77bd879a` |
| dual_iso | shipped, hidden | shipped | never enabled | S to unhide, M to fix | In both modules.included and modules.hidden; ml/modules/dual_iso/dual_iso.c:376 |
| mlv_play, mlv_snd | not shipped | shipped | never enabled | M | ml/modules/raw_video/mlv_play, /mlv_snd — zero 6D2 references in either |
| crop_rec | not shipped | shipped | subsystem unported | XL | ml/modules/crop_rec — 1 file mentions 6D2 |
| silent | not shipped | shipped | subsystem unported | XL | Depends on `CONFIG_RAW_PHOTO`; ml/modules/silent |
| ettr | not shipped | shipped | never enabled | M | ml/modules/ettr/ettr.c — depends on `FEATURE_RAW_ZEBRAS` (blocked) |
| lua | not shipped | shipped | never enabled | M | ml/modules/lua — 49 files mention 6D2, so scripting bindings largely exist |
| sd_uhs | not shipped | shipped | never enabled | M | ml/modules/sd_uhs; related note in ml/platform/200D.101/features.h |
| adv_int, arkanoid, autoexpo, deflick, dot_tune, edmac, img_name, pic_view, selftest | not shipped | shipped | never enabled | S each | Present in ml/platform/5D3.113/modules.included, absent from ml/platform/6D2.111/modules.included |

---

## Counts

Counted directly from the tables above (108 feature/module rows in sections 1–6; the former
"unknown" focus-box row split into two classified rows on 2026-08-15).

| Reason | Count |
|---|---|
| never enabled / tested | 56 |
| stub missing | 13 |
| hardware/firmware differs | 12 |
| subsystem unported | 12 |
| **Total classified** | **93** |
| Working today, no reason needed (status On / Partial-with-no-blocker) | 15 |
| Honestly unknown | 0 |

**Classification is complete: every 6D2-missing row now carries exactly one reason class.**
The 56 in the first row includes the 9 rows of section 3, whose shared reason is stated in the prose
above that table rather than in a cell, plus 4 rows now marked Done locally (MOV limit and the three
debug displays — their historical reason class was `never enabled`, and it is kept for the count).
2026-08-15 reclassifications: MOV limit `stub missing` → `never enabled` (the "missing stubs" were
two consts nobody had looked up — found, enabled, hardware-confirmed); focus-box autohide (LCD)
`unknown` → `never enabled` (upstream PR #223 hardware test); clean HDMI `unknown` →
`subsystem unported` (ML's RGBA refresh path does not follow the display to HDMI on any D7 port).

For scale: of the 144 effective macros on 5D3.113, **89 `FEATURE_` and 36 `CONFIG_` are absent on the
6D2**. The tables above also cover features that exist only on the modern-DIGIC side and have no 5D3
equivalent (`FEATURE_VRAM_RGBA`, `FEATURE_DISK_LOG`, `FEATURE_SD_AUTOTUNE`,
`FEATURE_OVERRIDE_MOVIE_30_MIN_LIMIT`, `CONFIG_COPY_CONSOLE_TO_UART`, `CONFIG_MMU_REMAP`,
`CONFIG_SGI_HANDLERS`), plus per-module state, so the row count exceeds the raw macro delta.

---

## Next cheap wins, in priority order (2026-08-15) — this drives the rest of Phase C

Ranked by (confidence it works) × (smallness of diff). **Excluded because already done:** the MOV
time limit and the three debug displays (`FEATURE_SHOW_TASKS`, `FEATURE_SHOW_CPU_USAGE`,
`FEATURE_SHOW_GUI_EVENTS`) shipped in patches/0001 and the MOV limit is confirmed on the real
camera; their upstreaming is Track C, not a new win.

**Tier 1 — proven on this exact body, one-line diff.**

1. **`FEATURE_LV_FOCUS_BOX_AUTOHIDE`** — upstream PR #223 (evgeniimv) enabled exactly this line on
   a real 6D2 and posted photos + video: focus box hides on the rear LCD. With Canon's INFO cycle
   that makes the rear display clean. Known limit: no effect on HDMI out. Draft diff and mechanism
   analysis in .planning/spikes/003-cheap-wins-scoping/README.md (2026-08-15 section). The only
   candidate with same-body hardware evidence.

**Tier 2 — strong sibling precedent, one small caveat each.**

2. **`FEATURE_SHOW_FREE_MEMORY`** — on for 10 siblings. The only reference to a symbol the 6D2 lacks
   (ml/src/mem.c:1390) is inside `#ifndef CONFIG_DIGIC_678X`, so it is excluded on this body.
   Upstream's caveat is honest and already written down: "working but slightly hackish, don't yet
   have a good way to determine free stack size."
3. **`FEATURE_DISK_LOG`** — on for 200D and M6II. Pure logging; useful infrastructure for every
   later investigation, including the spike 005 allocation blocker.
4. **`CONFIG_COPY_CONSOLE_TO_UART`** — on for 200D. Debug-rig value: gets console output out of the
   camera without the display path, which matters while QEMU still halts before the GUI.
5. **`FEATURE_STICKY_HALFSHUTTER`** — on for 77D. 200D's comment ("Works but likely not required")
   is the reason it is low here, not any technical doubt.
6. **`FEATURE_SHOW_IMAGE_BUFFERS_INFO`, `FEATURE_UNMOUNT_SD_CARD`** — no missing symbols, no
   sibling precedent. Cheap but unproven.

**Tier 3 — one address away.**

7. **`FEATURE_CROPMARKS`** — blocked on exactly one const, `IMGPLAY_ZOOM_LEVEL_ADDR`. Upstream
   already wrote the reason into ml/platform/6D2.111/features.h. The 200D has the address in
   ml/platform/200D.101/consts.h and eight ports enable the feature. Finding one address unlocks
   cropmarks **and** unblocks `FEATURE_SET_MAINDIAL`, `FEATURE_LV_FOCUS_BOX_FAST`, and half of
   `FEATURE_RAW_ZEBRAS` — the best value-per-address in the whole matrix.

**Tier 4 — module list additions, untested but zero code.**

8. **Ship low-risk modules** already built for every camera (`adv_int`, `autoexpo`, `img_name`,
   `pic_view`, `selftest`) — one line each in ml/platform/6D2.111/modules.included. `selftest`
   first: it exists to validate a port. No 6D2-specific code in any of them, which is precisely why
   they are untested claims until run.

**Explicitly not wins:** `FEATURE_SD_AUTOTUNE` was tried and rejected on this body
("doesn't seem to improve over stock speeds" — ml/platform/6D2.111/features.h); do not re-litigate.
`FEATURE_SHOW_EDMAC_INFO` has no consumer in the tree — enabling it does nothing.

**Sequencing note:** ml/platform/6D2.111/features.h currently carries spike 005's A/B experiment
(four features commented out) — land nothing in that file until Track A completes.

---

## Honest gaps

- Whether any tier-1/2 feature *renders correctly* cannot be settled statically. The link-blocker
  test proves the build will succeed; it does not prove the D7 compositor draws the result. **Unknown
  — needs QEMU** past the current Canon assert, or a camera.
- The LiveView overlay family (zebras, histogram, waveform, vectorscope, false colour, spotmeter) is
  classified `never enabled` because the macros are off, the objects are compiled, and no symbol is
  missing. But **no DIGIC 6/7/8/X port has ever enabled any of them**, so the runtime risk is real
  and unquantified. Treat the `M` effort estimates there as a floor, not a forecast.
- "Focus box hide / clean HDMI" is now mapped and split (section 4): the LCD half is
  `FEATURE_LV_FOCUS_BOX_AUTOHIDE` (hardware-proven on a 6D2 by upstream PR #223); the HDMI half is a
  real subsystem gap with a phased route in spike 003's 2026-08-15 section. The remaining unknowns
  there are two measurements (does `_rgb_vram_info` change on HDMI hot-plug; do ML overlays appear
  on HDMI at all), not classification.
- Effort estimates are relative sizing from code shape and address counts, not measured.
