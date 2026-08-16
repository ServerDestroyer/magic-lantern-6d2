# Direction 3 — The Feature Roadmap Queue

**Status:** recorded (not yet decided or planned)
**Recorded:** 2026-08-16
**Judged against:** [INTENT.md](INTENT.md) in this folder, with particular weight on Layer 4 §4.3 (a direction that produces no visible camera capability cannot demonstrate the method) and §4.4 (body-session time is the scarcest resource).

---

## One-sentence goal

Ship the camera features that were paused by the 2026-08-16 JTAG scope decision, cheapest-first, in the smallest number of body sessions — movie-mode dual-ISO, the playback-zoom-blocked overlays, focus-box autohide, the one-line enables, and the big one, lossless LJ92 raw compression for sustained 1080p recording.

## What makes this direction structurally different from the other four

Every other candidate in this folder delivers *capability to build things*. This one delivers **things**. Under INTENT Layer 4 §4.3 that is not a small distinction: a direction that terminates in a working camera feature is the only kind that can make the method's success legible to Chris, to the maintainers, or to anyone he later shows it to. Direction 3 is the only entry in the folder whose deliverables *are* camera capabilities by construction.

It is also the direction that spends the scarcest resource. Under §4.4, body-session time is what the project cannot buy more of, and two sessions have already been lost to our own instrumentation defects. Every item in this queue terminates in a body session. So the whole value of this direction turns on one question: **how few sessions can the queue be compressed into, and how much of each session is protected from our own bugs?** That question is answered in "The body-session budget" below, and the answer materially depends on whether direction 1's QEMU work happens first.

---

## The queue at a glance

Ordered by (confidence it works) × (smallness of diff) ÷ (body-session cost), cheapest first.

| # | Item | Desk work | Body sessions | Brick risk | Upstreamable now? | What it unblocks |
|---|------|-----------|---------------|------------|-------------------|------------------|
| 0 | `m_VSize` / `m_ShutterSpeed` assert probe | ~10 lines (rider on any build) | 0 (rides along) | none | as a **bug report**, yes — that is the requested mode | stops an assert interrupting items 1 and 5 |
| 1 | Focus-box autohide (upstream PR #223) | 1 line | shares a session | none | **best fit in the queue** — confirming someone else's tested patch | a stale contributor PR; a clean rear LCD |
| 2 | `IMGPLAY_ZOOM_LEVEL_ADDR` group — **claim does not survive review** | 2 lines (not an address hunt) | shares a session | none | yes, with the sibling-precedent argument | cropmarks today; SET+maindial / LV-focus-box-fast as *untested*, not unblocked |
| 3 | Cheap-win enables (free memory, disk log, sticky half-shutter, modules) | ~6 lines + module list | shares a session | none | one at a time, with evidence | diagnostics this project itself needs |
| 4 | Movie-mode dual-ISO | ~6 lines of constants | 2–3 | none structural; ERR70/80 → battery pull | **measurement yes, patch not yet** | the only extended-DR video route on this body |
| 5 | Lossless LJ92 raw compression | 4–8 agent sessions of RE + integration | 2–4 | none structural | not until a byte-verifiable file exists | sustained 1080p24/25/29.97 raw |

Items 0–3 are **one shared body session**. Items 4 and 5 are the ones that cost real human time.

---

## Item 0 — the assert that will interrupt everything else (rider, not a work item)

Not in the original brief, but it belongs at the top of the queue because it is free and it protects items 4 and 5.

`ASSERT: m_VSize @ ImgSeqCoopStore.c:194` fired during session 5 and will fire again on the same button presses that reach raw movie LiveView — which is the exact path item 4 requires. It is ours, not Canon's: ROM `0xE04471DE` is `ImgSeqCoopStore::GetVSize()`, stubbed in our own tree as `_get_fps_register_b` at [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/platform/6D2.111/stubs.S](ml/platform/6D2.111/stubs.S) line 279, and it asserts because we read `m_VSize` while the timing generator has it at zero. The sibling `_get_fps_register_a` → `ImgSeqCoopStore::GetShutterSpeed()` at `0xE044726A` has the identical shape and will assert at line 232 under the same race. Byte-verified disassembly in [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/007-dual-iso-scoping/crash-analysis.md](.planning/spikes/007-dual-iso-scoping/crash-analysis.md) §1.1.

**Do not apply that spike's proposed one-line fix.** Its own adversarial verification refuted the call-site attribution (`raw.c:1234` is unreachable on the observed path; `raw_lv_enable()` → `wait_lv_frames(2)` runs first and unconditionally at raw.c:2453-2456), and the fix was justified by that attribution. Backtrace is compiled out on D678 (init.c:576-580), so the only way to localise it is a `diag_log` probe **inside** `fps_get_current_x1000()` recording `get_current_task_name()` and the return address.

- **Needs:** desk work only, ~10 lines, reusing the already-proven `diag_log` → `ML/LOGS/RAWDIAG.LOG` helper from patch 0006 rev 3. It rides along on whatever build goes to the next body session and costs zero extra human time.
- **Brick risk:** none. It is a log line.
- **Upstreamable:** yes, and in the form the maintainer explicitly asked for — a bug report with reasoning, naming the two ROM functions, the struct offsets (`+0x1C` / `+0x2C` of the singleton at `0x1C928`), and the fact that ML's `if (!lv)` guard is the wrong guard because `lv` stays 1 across a LiveView reconfiguration. That is a finding about *upstream's own stub table*, not a speculative patch.
- **Verdict:** free, protects two expensive items, and is exactly the contribution mode Layer 3 says is welcome. Take it.

---

## Item 1 — focus-box autohide (upstream PR #223)

**One line in [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/platform/6D2.111/features.h](ml/platform/6D2.111/features.h): `#define FEATURE_LV_FOCUS_BOX_AUTOHIDE`.**

This is somebody else's patch. evgeniimv opened PR #223 on 2025-08-31, built it, ran it **on a real 6D Mark II**, and posted photos and a video: the focus box disappears from LiveView on the rear LCD, and with Canon's own INFO cycle the LCD is clean. reticulatedpines replied once on 2025-09-01 pointing at `clear_lv_afframe()` in tweaks.c; nothing since. `mergeable_state: clean`.

**The mechanism is verified in source**, which matters because the naive reading is wrong. On a `FEATURE_VRAM_RGBA` body the erase does not come from the legacy white-pixel scrub in `clear_lv_afframe()` (tweaks.c:313-368 only touches ML's own indexed buffer on these bodies). It comes from the write-everything mode of the RGBA copy at [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/src/bmp.c](ml/src/bmp.c) lines 211-256, which runs when `zebra_should_run()` and overwrites *every* pixel including transparent ones — and because the 6D2 has no `CONFIG_COMPOSITOR_DEDICATED_LAYER`, ML writes into Canon's own layer 0, so that full-buffer write is what erases Canon's AF frame. The feature flag's real contribution is the dirty-tracking driver at tweaks.c:286-311 plus the call site at tweaks.c:1136-1138 that forces the erase cycle after the frame moves. Full trace in [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/003-cheap-wins-scoping/README.md](.planning/spikes/003-cheap-wins-scoping/README.md), 2026-08-15 section.

`FEATURE_MATRIX.md` already reclassified this out of the "Off (prop)" bucket for the right reason: the enabled path makes no property write, and #223 ran it with the stock 4-property whitelist.

- **Needs:** 1 line of desk work; ~2 minutes of a body session, eyes on the rear LCD. No PC work beyond the build.
- **Unblocks:** a stale contributor PR, and the LCD half of upstream issue #221.
- **Does not unblock:** HDMI. The PR author's own follow-up (2025-08-31 19:36) says the box remains on HDMI output. `FEATURE_MATRIX.md` classifies clean HDMI as `subsystem unported`, M–L. **Do not claim clean HDMI on the strength of this.** Overclaiming is the specific failure Layer 3 item 4 records.
- **Watch item, and it is free evidence:** the PR author saw a flaky `EFLensComTask: stack warning: free=232 used=792`. reticulatedpines pointed at [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/src/tskmon.c](ml/src/tskmon.c) line 195, which already carries 6D2/200D exceptions for `RTCMgr` and `idle` but not this task. Whether a second body reproduces it is a one-bit answer that costs nothing to collect and is directly useful to the maintainer.
- **Brick risk:** none. Draw path only.
- **Upstreamable:** **this is the single best-fitting item in the whole queue against the maintainer's stated preferences.** It adds evidence to an existing hardware-tested patch rather than adding a diff; it costs him nothing to re-review; it unsticks a contributor who has waited since 2025-08-31. Layer 3 item 2 asks for evidence over speculative fixes — this is nothing but evidence.
- **The gate, and it is a real one:** the drafted comment at [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/prs/DRAFT-comment-on-upstream-PR-223.md](.planning/prs/DRAFT-comment-on-upstream-PR-223.md) promises Chris's time on a public thread. It was blocked by the harness classifier and deliberately not worked around. Under INTENT §4.2 that block was doing work Chris cannot do for himself. **Post it only when the body session is actually scheduled** — an unfunded public promise damages the relationship more than silence does.

---

## Item 2 — `IMGPLAY_ZOOM_LEVEL_ADDR`: the claim was checked and it does not survive

The brief asked me to verify the standing claim that this is "one ROM address that unblocks cropmarks + SET-maindial + fast LV focus box + half of raw-zebras — the best value-per-address item in the matrix" (`FEATURE_MATRIX.md` Tier 3, and the four Blocked rows in its section 4). **It does not hold, in three separate ways, and the net effect is that the item is *cheaper* than advertised, not more expensive.**

**(i) It is not a ROM address.** Every consumer reads it as `MEM(IMGPLAY_ZOOM_LEVEL_ADDR)` — it is a DryOS RAM variable. The recovery method is written into every D5-era `consts.h`: *"dec GuiImageZoomDown and look for a negative counter"*. That is a live-code reversing task, not a literal-pool lookup like the MOV time limit was.

**(ii) Seven sibling ports enable the headline feature with a constant they document as wrong.** Grepped across all platforms:

| Port | Value | Comment | `FEATURE_CROPMARKS`? |
|---|---|---|---|
| 200D.101 | `0x2CBC` | `//wrong, will be needed when overlays are enabled in play mode` | **enabled** |
| 77D.110, M50.110, R.180, SX740.102 | `0x2CBC` | `//wrong` | **enabled** |
| 80D.103, 750D.110 | `0x2CBC` | `//wrong, code looks different` | **enabled** |
| M6II.111 | `0x1000C` | (no comment — the only modern port with a value that looks real) | **enabled** |
| 5D4.133, 7D2.112, R5.152, SX70.111, XF605.101 | `0x2CBC` | `//wrong` | not enabled |
| **6D2.111** | **absent** | features.h line 25: `//#define FEATURE_CROPMARKS // wants IMGPLAY_ZOOM_LEVEL_ADDR` | blocked |

So the 6D2 is not blocked on knowledge nobody has. It is blocked on a two-line edit that seven other ports on the same silicon generation already made. **Cropmarks is a Tier-1-cost item today**, not a Tier-3 one, and it is the only overlay feature in `FEATURE_MATRIX.md` section 2 with eight-port precedent — every other overlay (zebras, histogram, waveform, vectorscope, false colour, spotmeter) has *zero* modern-DIGIC precedent and the matrix's own "honest gaps" section says so.

**(iii) A wrong value cannot corrupt anything, because all four consumers only read it.** Checked every reference:

- `FEATURE_CROPMARKS` — zebra.c:4287-4293, read-only, and inside a branch gated on `crop_enabled && cropmarks_play && PLAY_MODE`. LiveView cropmarks — the half people actually want — never touch the address at all.
- `FEATURE_RAW_ZEBRAS` — zebra.c:634, 690, read-only (a polling loop that breaks when playback zoom changes; a garbage constant means the break never fires — degraded, not dangerous).
- `FEATURE_SET_MAINDIAL` — tweaks.c:547, read-only.
- `FEATURE_LV_FOCUS_BOX_FAST` — tweaks.c:1117, read-only.

The *write* sites (tweaks.c:910, 1014, 1033-1043, 1057-1086) all sit under `FEATURE_QUICK_ZOOM` / `FEATURE_REMEMBER_LAST_ZOOM_POS_5D3` **and** an inner `#ifdef IMGPLAY_ZOOM_POS_X`, which the 6D2 does not define — it has no `IMGPLAY_*` constants at all. So none of the four target features can write to a bogus address.

**(iv) The "unblocks four features" arithmetic is true at the linker and false in practice.** No DIGIC 6/7/8 port anywhere in the tree enables `FEATURE_SET_MAINDIAL`, `FEATURE_LV_FOCUS_BOX_FAST` or `FEATURE_RAW_ZEBRAS` — verified against all eight D6+ ports' features.h. "Unblocked" for those three means *will link*, not *will work*. And raw zebras additionally needs `CONFIG_RAW_PHOTO`, which no D6+ port defines and which `FEATURE_MATRIX.md` section 5 rates XL / subsystem unported — so "half of raw zebras" is literally accurate and the remaining half is the expensive half.

**Restated honestly:**

- **Enable cropmarks now**, with the sibling placeholder, as a two-line change. This is the item's real value and it is nearly free.
- Enable SET+maindial and LV-focus-box-fast in the same batch if you like — same two lines cover them — but record them as **untested on any modern body**, not as delivered.
- **Finding the real address is a separate, lower-value task.** It buys correct playback-zoom behaviour and nothing else, and no modern-DIGIC port has managed it (every one that tried wrote "wrong" or "code looks different").
- **One unverified assumption remains:** nobody has checked what lives at `0x2CBC` on the 6D2. It is low DryOS RAM — the same region ML already reads at `0x46C8` and `0x5738` per spike 008 — so a fault is very unlikely, but the read is unproven on this body. Cheapest de-risk is to watch for a `CRASH00.LOG` entry on the first boot; the address is only touched in playback branches.

- **Needs:** 2 lines desk; ~3 minutes of the shared body session (cropmarks visible in LV, then one playback frame).
- **Brick risk:** none.
- **Upstreamable:** yes, and the argument writes itself — "the 6D2 is the only D7 body without cropmarks, and the reason recorded in features.h is a constant that seven sibling ports supply as a documented placeholder." That is a small, honest, precedent-backed PR. It also fixes a misclassification in this project's own `FEATURE_MATRIX.md`, which should be corrected whether or not the PR is filed.

---

## Item 3 — cheap-win enables, and which are genuinely dependency-free

`FEATURE_MATRIX.md` Tier 2 lists six. Checked each against the tree; three are genuinely free, one is free-but-useless-today, and the whole category carries a caveat the matrix understates.

**Genuinely dependency-free:**

1. **`FEATURE_SHOW_FREE_MEMORY`** — on for 10 siblings. The single reference to a symbol the 6D2 lacks (mem.c:1390) sits inside `#ifndef CONFIG_DIGIC_678X`, so it is excluded on this body. Upstream's own caveat is honest and already written down ("working but slightly hackish, don't yet have a good way to determine free stack size"). **This is not just a feature — it is diagnostic infrastructure this project needs**: spike 006's bug 3 was an entire investigation into the shoot pool, and spike 005's blocker was an allocation failure.
2. **`FEATURE_DISK_LOG`** — on for 200D and M6II. Pure logging.
3. **`FEATURE_STICKY_HALFSHUTTER`** — on for 77D. 200D's comment ("Works but likely not required") is why it ranks low, not any technical doubt.

**Free but with no benefit today:**

4. **`CONFIG_COPY_CONSOLE_TO_UART`** — on for 200D only. On the body, the 6D2's UART is not reachable without opening the camera (that is spike 014, deferred, ~$5 adapter). So on hardware this enable buys nothing until that spike runs. **In QEMU it is genuinely valuable** — it puts ML's console into the emulator's output stream, which is precisely what direction 1's trace harness wants — but only once ML boots under QEMU. Rank it as *QEMU infrastructure*, not a camera win.

**Cheap but unproven:**

5. `FEATURE_SHOW_IMAGE_BUFFERS_INFO`, `FEATURE_UNMOUNT_SD_CARD` — no missing symbols, no sibling precedent.

**Explicitly not wins** (do not re-litigate): `FEATURE_SD_AUTOTUNE` was tried and rejected on this exact body ("doesn't seem to improve over stock speeds", features.h). `FEATURE_SHOW_EDMAC_INFO` has no consumer anywhere in the tree — enabling it does nothing.

**Modules.** Five build for every camera and cost one line each in `modules.included`: `adv_int`, `autoexpo`, `img_name`, `pic_view`, `selftest`. Note a mechanism detail the matrix omits: all five are *also* in [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/platform/6D2.111/modules.hidden](ml/platform/6D2.111/modules.hidden), so shipping them visible needs a deletion from that file too — the same shape as the `dual_iso` unhide, which is the only body listed in both files and reads as "shipped but not signed off". `selftest` is both the highest-information (it exists to validate a port) and the highest risk of a hang on an immature port; run it last in a session, not first.

**The caveat the matrix understates, and it is the important part of this item.** "One-line define, zero risk" is not true on this port. Spike 005's A/B, measured in QEMU and recorded in patch 0005 and in features.h itself: with `FEATURE_SHOW_TASKS` / `FEATURE_SHOW_CPU_USAGE` / `FEATURE_SHOW_GUI_EVENTS` enabled, `GetMemoryInformation()` reports **0 total / 0 free** at `log_start()` and every `_AllocateMemory` fails, so a `CONFIG_STARTUP_LOG` build captures nothing. With them off, the pool is 9437184 / 5970756 and capture works. That is a demonstrated, still-unexplained case of display-only features breaking an unrelated subsystem on this body. Consequences:

- Every new enable must be A/B'd against a capture build before it is trusted.
- `FEATURE_SHOW_FREE_MEMORY` lives in the same file (mem.c) and is the most likely next instance. Test it in a capture build first.
- This is a perfect job for direction 1's headless QEMU loop and a poor use of a body session.

- **Needs:** ~6 lines desk + module-list edits; ~5 minutes of the shared body session.
- **Brick risk:** none, with the pool-interaction caveat above.
- **Upstreamable:** one at a time, each with the sibling-precedent list and the A/B result. Batching them into one PR is exactly the "spend less of my time, spend more of the reviewer's" pattern Layer 3 item 2 names as painful.

**Merge hazard, and it applies to items 1, 2 and 3 together.** All three edit the same 47-line `features.h`, which *currently* carries spike 005's A/B (three features commented out). `FEATURE_MATRIX.md`'s own sequencing note says to land nothing in that file until that track completes. **Batch them into one change or they will collide.**

---

## Item 4 — movie-mode dual-ISO

**The diff is ~6 lines of constants; the address it points at is an open four-way choice.**

### What is settled

Stills dual-ISO works on this body and is measured: +1.705 to +1.709 EV, repeatable to ±0.005 EV over three frames, with `cr2hdr` merging end-to-end and correctly rejecting the controls ([/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/007-dual-iso-scoping/development-results.md](.planning/spikes/007-dual-iso-scoping/development-results.md)). Measured merged dynamic range 12.42 EV vs 11.08 EV at the same white point — +1.34 EV real, against cr2hdr's printed "12.74 EV (cooked)" which is optimistic by ~0.3 EV.

The ROM structure is decoded. The FixData blob at ROM `0xE1980000` (Canon names it itself — `FixData.bin` in the factory dump table at `0xE0066B58`) is DMA'd whole to heap; the stills ISO table is blob `+0xB30`; the LiveView array is blob `+0xEF4`, 104 records of 7 words, **four blocks of 26**, each block a 1/3-stop ladder with full stops every third record.

**ROM patching does not work on the 6D2** — upstream's own comment at [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/modules/dual_iso/dual_iso.c](ml/modules/dual_iso/dual_iso.c) lines 1148-1156: *"Patching the rom copy doesn't work, presumably this happens too late."* The shipping stills patch targets the DMA'd RAM copy via `get_photo_cmos_iso_start_6d2()`, which scans `0x780000–0x880000` for the DMA descriptor whose source is `0xE1980000` and returns `probe[6] + 0xb30`. **Any movie constant must be written RAM-relative**, i.e. `PHOTO_CMOS_ISO_START - 0xb30 + 0xef4`, never as a bare ROM address. A reader who takes only the headline of the spike and writes `0xE1980EF4` gets a silent no-op.

The existing `patch_cmos_iso_values_6d2()` needs **no rework** — it already indexes by `item_size * i` and preserves the bytes between patched words, so an arbitrary stride works and the earlier prediction of "a modest rework" was wrong.

### What was refuted

The spike's identification of block 0 as the movie table was **not supported** on independent re-derivation. All three supporting points failed:

1. The "200D's video table is +0x3BC from its stills base, ours is +0x3C4, eight bytes apart" argument is arithmetically wrong. The 200D's video table is **+0xC0** from its stills base; +0x3BC was measured from a rounded-down address with no counterpart to the 6D2's real DMA source base. The comparison was between two incompatible quantities.
2. The amplifier-break argument inverts. The `0x38`-column gain-stage break sits at gain code 1→2 only in the *stills* table and block 0; in blocks 1, 2, 3 and in a previously unnoticed 26×3 variant array at `0xE1981B8C` it sits at record 8, mid-run of gain code 3. The break is anchored to record index, not gain code — which makes block 0 the outlier that matches **stills**, and on this sensor the movie readout is the line-skipped one that should *not* match stills. That points as easily to photo-LiveView or x5/x10 zoom as to movie.
3. There is **no ROM reference to any block in any addressing form**. All 32 MiB searched at 4- and 2-byte alignment for every candidate address: zero hits. Canon walks the DMA'd copy by parsing `ffffffff <id>` section markers; the block is selected at runtime from sensor-mode state.

Blocks 0 and 1 are byte-identical for records 0–4, so the discriminating measurement must cross the code 1→2 boundary.

### The one measurement that closes it

One `adtglog2` capture in movie LiveView, raw video on, dual-ISO **off**, stepping ISO 200 → 400. It discriminates all four blocks at once:

- `buf_addr` names the base record. The corrected candidate list is **six** `0x304` base records at blob `+0xD44, +0xD8C, +0xDD4, +0xE1C, +0xE64, +0xEAC` (the spike listed five and omitted `+0xD44`), plus section `0x305`'s own base record at `+0x1CC4` which the plan did not anticipate.
- The `reg 0x10` word names the block: `10717220` → block 0 or 1, `1871723e` → block 2, `10717a20` → block 3. **`10717620` or `10717e20` means none of the four** — those belong to the 26×3 variant array at `0xE1981A54`.
- The gain code written at ISO 400 separates block 0 from block 1: `0d03a220` = block 0, `0d03a330` = block 1.

`adtglog2` is already 6D2-ported but appears in no body's `modules.included` — it is build-from-source only, from `ml/modules/dev_tools/adtglog2/`, and the `.mo` is copied to the card by hand. It writes `adtg.log` to the card, unlimited size, so it self-records and needs no console photography.

### Two behaviours to state before anyone ships this

- **`SIZE = 0x54` silently disables dual-ISO at every 1/3-stop movie ISO** — 125, 160, 250, 320, 500, 640, 1000 and so on — because the stride patches only records 0, 3, 6 … 21. Stills cannot hit this because the 6D2 stills table has only 8 full-stop entries. This is not a defect in the diff and it matches the 200D's known behaviour, but it is user-visible and must be documented, not discovered.
- **Block 2 is un-patchable by the current code.** All 26 of its records carry the `0x0d01` prefix and `patch_cmos_iso_values_6d2()` gates on `(val & 0xffff0000) == 0x0d030000`, so every item is skipped *silently* — dual-ISO reports enabled and produces nothing. Relaxing the gate to `0x0d000000` is the only way to test block 2, and that gate is the thing that stops a wrong address from writing gain nibbles into unrelated registers. Do not relax it for a feature this speculative.
- `COUNT = 9` would run the patched span from `0xE1981194` to `0xE19811E8`, **into block 1** (which starts at `0xE19811CC`). Leave it at 8.

### Honest ceiling

The biggest risk is not the address, it is the post-processing. The 200D hit exactly this wall: full-frame video uses line skipping, and line skipping plus dual-ISO line alternation *"breaks cr2hdr and mlvapp code"* — which is why 200D movie dual-ISO shipped for x5/x10 zoom only. Spike 006's evidence shows the 6D2 reporting identical binning/skipping across all tested modes, which does not yet tell us whether an unskipped mode exists. **We may well succeed at capturing dual-ISO video on the 6D2 and still have no tool that can develop the result.** Budget for x5/x10 zoom being the only usable mode.

Second honest limit: the stills measurement of +1.71 EV corresponds to **no menu index** — the ROM's table promises 1 EV per gain code, and 1.71 EV is not a whole number of anything. The index that was actually set is unknown and unconstrained over {1..6}; the answer is sitting in `ML/SETTINGS/dual_iso.cfg` on the card currently in the body, which is a file copy, not a test. Until that is read (or an index sweep is run), **no honest EV claim can be made about movie dual-ISO either**, and Layer 3 item 4 makes overclaiming a first-order risk rather than a cosmetic one.

- **Needs:** one `adtglog2` capture (rides on the shared session), ~6 lines desk, then 1–2 body sessions to test and shoot. Spike 007's own estimate was 4–7 sessions to a working movie capture with phase 0 done; realistically **2–3 body sessions** now that stills are confirmed, plus 1–2 agent sessions of desk work.
- **Unblocks:** the only extended-dynamic-range video route on this body. `FEATURE_MATRIX.md` section 5 classifies HDR video as needing `CONFIG_FRAME_ISO_OVERRIDE` plus `FRAME_ISO` / `FRAME_BV` constants — XL, hw/fw differs, attempted by nobody on modern DIGIC. Chris asked for HDR video by name (INTENT §4.3). Movie dual-ISO is the answer that exists.
- **Brick risk:** none structural. Everything is an `apply_patches()` write into the heap copy; `IS_ROM_PTR()` is false for the target, `apply_patches()` `memcmp`s the pre-image and fails closed on mismatch, `unpatch_memory()` reverts, and a power cycle discards the whole DMA'd copy. Nothing touches FROM, ROM or the bootflag. Realistic worst cases: nothing happens (the *most likely* first result — plan for it), striped or uniform-brightness frames from an "unusual" gain pair, or LiveView loss / ERR70 / ERR80 needing a battery pull.
- **Upstreamable:** the **measurement** is, immediately and well — it resolves an open question in stephen-e's own 6D2 branch, where `FRAME_CMOS_ISO_*` is simply never set. The **patch** is not, until a developed frame exists. Submitting six lines of constants derived from an identification that our own review refuted is precisely the untested-LLM-patch pattern Layer 3 item 2 says costs the maintainer more than it saves.

---

## Item 5 — lossless LJ92 raw compression

**The big prize, and the only route to it.**

### The payoff, against a measured card rather than an assumed one

The card was benchmarked on the body: **82.6 MB/s write, 95.7 MB/s read** at 16 MiB buffers, cross-checked to better than 1% against the actual recordings ([/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/008-lossless-compression-scoping/card-benchmark-results.md](.planning/spikes/008-lossless-compression-scoping/card-benchmark-results.md)). Frame size is measured, not computed: every VIDF block in all 16 MLVs is exactly 3,629,056 B.

| Mode | Uncompressed | Today | 14-bit LJ92 @60% | Verdict with lossless |
|---|---|---|---|---|
| 1080p23.976 | 87.0 MB/s | burst 29.0 s | 52.2 MB/s | **sustained**, 63% duty |
| 1080p25 | 90.7 MB/s | burst 15.8 s | 54.4 MB/s | **sustained**, 66% duty |
| 1080p29.97 | 108.8 MB/s | burst 4.9 s | 65.3 MB/s | **sustained**, 79% duty (86% on a noisy scene) |
| 1080p59.94 | 217.5 MB/s | burst 0.95 s | 130.5 MB/s | still a burst, 2.7 s. No card fixes it — the UHS-I bus ceiling is ≤104 MB/s |

Two corrections the measurement forced, both of which matter to the value case:

- **29.97p upgrades from "marginal, needs 12-bit" to sustained at 14-bit.** That was not true against the assumed number.
- **1080p23.976 uncompressed is only 4.4 MB/s short of sustained today** — 29-second takes with no compression work at all. The "one-second burst" figure the project has been quoting is specific to 59.94p. Anything above a 5% saving tips 24p over the line; 25p needs ≥9%, 30p needs ≥24%.

That last point looks like it weakens the case, and it would — except that **the cheap alternative does not exist on this body**. The 10/12-bit output menu options are fake on the 6D2 (upstream `a9e01b972a`), so there is no bit-depth-only route to a modest saving. LJ92 is the only mechanism available. The honest headline is therefore: *lossless converts the 6D2 from a burst raw camera to a sustained one at 24/25/30p, and 24p was already nearly there.*

### What is done

Phase 1 static RE is **complete for the purposes of writing code**. Three Ghidra passes named every address ML needs. The `mlv_lite` side was already written and is exercised on DIGIC 5 today — `OUTPUT_14BIT_LOSSLESS`, `compress_task`, per-frame slot shrinking, the `MLV_VIDEO_CLASS_FLAG_LJ92` header flag, the ratio estimator. The 6D2 is locked out by **one `if` at mlv_lite.c:4633** whose own comment says *"no lossless support on D4, D678 (yet)"*, and `lossless_init()` is still called unconditionally at :4668 with `compress_task` created at :4674 on every body. The infrastructure is live.

Key results, with the corrections that matter:

- **`0xE04E3280` is `PostStageEvent`, not `StateTransition`** — it allocates a 16-byte message and posts it to a task queue. Pass 2's headline was wrong.
- **The real `StateTransition` is `0xDF00A192`, in the DryOS core in RAM**, not in ROM0 — it was recovered by `pmemsave` from a live qemu-eos boot. Its object layout is byte-for-byte `struct state_object` from ml/src/state-object.h, and **ML's `STATE_FUNC` indexing is correct as written**. Adversarial review flags this address as **single-source and unverifiable from ROM0** — treat the exact offsets as one observation, not a measurement.
- **Matrix rows are local, base 20.** The resolver at `0xE03274F8` subtracts the base before touching the matrix. `M3` (lossless) is at `0xE090EC80`, 7 rows × 4 states. The trap: `obj->max_inputs` is **27** while the table has **7** rows, because Canon passes the cumulative global event upper bound as the 4th `CreateStateObject` argument. Hooking a single cell is safe (`STATE_FUNC` uses `max_states`), but **any code that enumerates or bounds-checks the matrix from `max_inputs` runs 20 rows — 160 bytes — past the end of a 224-byte table.**
- The compressed byte count arrives as the third argument of the input-25 handler; hooking `M3[local 5][state 3]` at `0xE090ED3C` captures it with no extra machinery.
- **There is no safe mid-flight abort.** State 3 has exactly one non-NULL cell; `StopMem1ToRaw` clears the stored completion CBR, which strands the state object in state 3 forever with resources locked. The correct discipline is stop-issuing-then-drain, bounded at **two** outstanding encodes (the `DEVELOP_COMPONENT` table has exactly two records and `SSSStateList` is created with depth 2).
- Geometry is a hard ROM ASSERT: `res_x % 16 == 0`, `res_y % 8 == 0`.

### What precisely remains

1. **`0xE02E839A(job)` is decompiled — and the answer removes the cheapest hoped-for route.** The spike flagged this as "the highest-value 30-minute follow-up" on the theory that it might be a settable shooting-menu property ML could flip, letting Canon drive the whole encode. It is not. Eight instructions: `bl 0xE04EEA60; tst.w r0, #0x1D000`. `0xE04EEA60(job)` is a plain getter returning `job[+0x10]`, the picture-type bitfield set at job creation. The predicate is `(job->picttype & 0x1D000) != 0` — a bit test on a per-job field, not a menu setting. **Phase 2 does not collapse to "flip the flag."** This is a negative result and it should be carried forward as one; the spike's stated next action needs rewriting.
2. **The job. Still the blocker, now with a shape.** ML cannot synthesise a `JobClass` object: it must be registered in the two-slot `DEVELOP_COMPONENT` table, carry a `0xE04F3B74` parameter block whose `[+0xD20]` mode word is not one of four excluded values, and land on `0x1000`/`0x10000` for `GetUnitPictType`. Every one of those is an untraced dependency chain. **The route is to borrow one, not build one:** a passive hook on Canon's `StartJob` (M1 local 1, cell `0xE090EB2C`, handler `0xE0327E88`) during a normal still capture, which yields `(ctx, job)` and a live memSuite for free. Read-only, and it is the correct first experiment.
3. **`0xE032A27C` has never been traced into JPCORE registers.** The `0xD0100000` window and the `0xD0003000` SharememTbl writes are known to exist; the write sequence behind events 6/7 was not followed.
4. **`0xE051B560` / `0xE051B582` (`SetMem1ToRaw` / `StartMem1ToRaw`) are directly callable**, `(argsPair, cbr)` and `()`. That is a genuinely lower-level entry that bypasses the resource lock and the allocator. Untested. Second experiment.
5. **qemu-eos does not map JPCORE at all for this body.** Its `eos_handle_jpcore()` is a logging stub with no codec, and its address map is the DIGIC 4/5 layout — the D7 window `0xD0100000..0xD0101FFF` is not mapped. A one-line window addition is the cheapest way to get any of this *observed* rather than reasoned about. **Nothing in passes 1–3 has been executed.**
6. **Nothing is validated against hardware.** The `0xDF000000` addresses come from one emulator boot; everything else is static.

### Honest session count

Pass 3 revised its own estimate to **4–8 sessions** (phase 2: 2–3, phase 3: 3–6). I do not think that number survives, for three reasons: it partly assumed item 1 above would collapse phase 2 and it does not; nothing has been executed, so the first execution session will surface its own surprises; and the single biggest unknown is untouched and is body-only.

That unknown is **whether JPCORE is available while the 6D2 is in LiveView movie mode, and what happens to Canon's own pipeline when ML takes it.** PR #292 on DIGIC 4 needed an "Evf EngineError trim so borrowing JPCORE cannot ASSERT the camera" and found JPCORE froze LiveView outright — enough that a whole soft-preview subsystem was written to compensate, 1388 added lines *with a same-family sibling to copy from*. We have no sibling. On the 6D2 it is sharper: `CONFIG_EVF_STATE_SYNC` is already set, raw video already routes through `raw_rec_vsync_cbr` via `vsync_func` so the encoder would contend with a path ML is already hooked into, DIGIC 7 has more concurrent engine consumers, and this port has an unresolved dead-state/re-arm history. Second-order: `LosslessEncMode`'s valid values are unknown and a wrong one is a plausible ASSERT.

**Realistic: 6–10 agent sessions, of which 2–4 are body sessions**, with a genuine probability of terminating at *"stills lossless DNG works; movie integration blocked by LiveView contention"*. That outcome is still worth having — it is a working D7 lossless encoder and a publishable RE document — but it is not sustained raw video.

- **Needs:** mostly desk. Phase 2 (stills, via `silent.mo`'s `save_lossless_dng` path) is the right start precisely because it isolates *"does the encoder work at all"* from *"can we steal it during recording"* — engine idle, no LiveView contention, no real-time deadline, one frame, and an output file verifiable byte-exactly on a PC. QEMU can validate stub resolution, call-sequence survival and ResLock ordering; it **cannot** validate compressed output, geometry, ratio or contention. Those are body-only.
- **Unblocks:** sustained 1080p24/25/29.97 raw. Also fixes DIGIC 4 and every other D678 body if the `version != 5` whitelist at mlv_lite.c:4633 is replaced with a capability test (`if (!lossless_init())`) rather than another version number.
- **Brick risk:** none structural — no FROM, ROM or bootflag writes anywhere in this path. The realistic hazards are ASSERTs, a stranded state object with engine resources locked (recovered by power cycle), and freezes requiring a battery pull.
- **Upstreamable:** in principle this is **the most valuable thing this project could contribute upstream** — the first working lossless backend on modern DIGIC, benefiting every D6/7/8 body. In practice it is also the item most likely to produce confident, untested code, which is the exact failure Layer 3 item 2 names. Firm rule: **nothing from item 5 goes upstream until a byte-verifiable lossless DNG comes off the body.** Until then the contribution is the RE writeup, which is welcome in its own right.

---

## The body-session budget — the §4.4 test

This is the number that decides whether the direction is affordable.

**Session S1 — the batched session, ~40 minutes, two card syncs.** It closes items 1, 2 and 3 outright and takes the gating measurement for item 4.

*Part A, on the known-good daily build* (adtglog2 is a module; it needs no `features.h` change, so the measurement is protected from an untested build):
1. dual-ISO block discriminator — movie LiveView, raw video on, dual-ISO **off**, step ISO 200 → 400, `adtglog2` writes `adtg.log`.
2. The `fps_get_current_x1000()` probe from item 0, self-recording to `RAWDIAG.LOG`.
3. Custom-WB discriminator — the one item never run from `BODY_TEST_PLAN.md` session 5, ~1 minute, settles whether lens.c's `PROP_CUSTOM_WB` parse is right on D7.
4. Copy `ML/SETTINGS/dual_iso.cfg` off the card — a file copy, and it answers the unresolved "which index produced +1.71 EV" outright.

*Part B, after syncing the experimental build:*
5. Boot sanity, then focus-box autohide in LV (eyes on the LCD, ~2 min).
6. Cropmarks in LV, then one playback frame.
7. Free memory / disk log present; sticky half-shutter; `selftest` last.

**Session S2 (~20 min):** movie dual-ISO with the constants set to whatever S1's capture identified. Reach stable raw LiveView *first*, then enable dual ISO at **index 1 (100/200)** — one gain code of separation, both codes inside the same amplifier configuration, least likely to hit the 200D's "unusual pattern" behaviour. Observe LiveView; only then record.

**Session S3 (~20 min):** dual-ISO footage at a usable index, plus a stills index sweep to map gain code → achieved EV (the number needed to make an honest claim). Mergeable into S2 if S2 looks clean.

**Sessions S4–S7:** lossless. Each iteration is one build plus one still capture; realistically 2–4 before either a valid LJ92 file or a stop.

**Total: 5–7 body sessions, compressible to 2 for everything except lossless.** Roughly 85% of the total labour is desk or QEMU work that can proceed with Chris absent — but progress is *capped* by those sessions, and they are strictly ordered: item 4's diff cannot be written before S1's capture, and item 5's integration cannot start before its stills encode works.

**Three protections against losing a session to our own bugs**, all of them already proven in this project:

1. **Move the evidence capture into the machine.** `RAWDIAG.LOG` (patch 0006 rev 3) turned a session of console photography into a text log, and the two sessions that were wasted were wasted on instrumentation the machine could have checked. Every test in S1 above self-records except the two that need eyes on the LCD.
2. **Verified instructions are an artifact.** [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/docs/6D2_CONTROLS.md](docs/6D2_CONTROLS.md) exists because Chris corrected our button names. Use it for every step of S1.
3. **The build must boot before it goes on the card.** Today the only pre-flight check is "it compiled" — and `make clean` does not rebuild modules, so a rev-2 build once silently shipped a rev-1 `.mo` with an identical size and a fresh mtime. The forced-rebuild incantation and the "verify with `strings` on `build/zip/`, never the source tree" rule are in patches/README.md and are not optional.

---

## The coupling to direction 1, stated plainly

Protection 3 above is the honest weak point, and it is not solvable inside this direction. The thing that would actually de-risk S1 is **ML booting under QEMU** — the `[CPU1] ASSERT SystemIF::KerRLock.c:205` gate, prime suspect the single global `current_task_addr = 0x28` at `hw/eos/model_list.c:619` on a 2-core machine. That work belongs to direction 1.

So: **direction 3's cost is a function of whether direction 1 is done first.** With a headless QEMU loop, feature enables get A/B'd before they reach a card, the spike-005 pool interaction becomes a desk question, and item 5's plumbing (stub resolution, call-sequence survival, ResLock ordering) can be exercised with no camera in the room. Without it, every enable is a coin flip resolved by a human sitting in front of a camera.

This does not make direction 3 dependent on direction 1 — items 1, 2 and 3 are shippable today at the cost of one session's risk — but it does mean the two are complements rather than alternatives, and that sequencing 1 → 3 costs fewer of Chris's sessions than 3 alone.

---

## What stays with the human either way

Inserting the card, powering the camera, pressing shutter and START/STOP, changing Canon menu settings, watching the LCD, pulling the battery on a freeze. Pushing PRs and posting the #223 comment under his GitHub account. Copying `ML/SETTINGS/dual_iso.cfg` and the `.MLV`/`adtg.log` files back off the card. Everything else — the diffs, the builds, the ROM analysis, the log reading, the diagnosis, the PR prose — runs without him.

---

## Sequencing options (the fork)

- **Batch-and-ship (recommended).** Land items 0–3 as one `features.h` batch, run S1 to close them and take item 4's measurement, then decide item 4 on the evidence. Item 5 runs as background desk work throughout, since its next steps are all static and need no camera. Fastest path to a visible capability, which is the §4.3 test.
- **Lossless-first.** Treat item 5 as the only real deliverable and do the small items as riders on its body sessions. Highest ceiling, longest time to anything visible, and it front-loads the item most likely to end in a negative result.
- **Measurement-first.** Run S1 Part A alone on the known-good build, take no risk with `features.h` at all, and decide the whole queue on what the capture says. Cheapest and safest; wastes the other 35 minutes of a session Chris is already spending.

---

## What would make me abandon this direction

Per item, with the specific trigger:

- **Item 2** — if reading `0x2CBC` faults on this body, or the playback branch visibly misbehaves: turn off the `cropmarks_play` option and keep LiveView cropmarks. Do **not** start hunting the real address; it buys playback overlays and nothing else, and no modern-DIGIC port has found it.
- **Item 3** — if a second feature enable reproduces the spike-005 allocator-pool zeroing, stop enabling features one at a time. The category has stopped being cheap and the underlying interaction has to be understood first.
- **Item 4** — abandon if S1's capture shows a `buf_addr` outside all six `0x304` base records and the `0x305` record, or a `reg 0x10` word of `10717620`/`10717e20`. That means no mapped block is the movie table and the six-line diff has no target; the item becomes open-ended RE and should be dropped rather than tried blind against blocks 1/2/3. Also abandon if the capture identifies block 2 — testing it requires relaxing the one sanity gate that stops a wrong address writing gain nibbles into unrelated registers, and that is not a trade worth making for a speculative feature. And abandon the *shipping* half if full-frame proves line-skipped and cr2hdr/MLVApp cannot develop x5/x10 output: stop at a documented negative result, which is upstream-valuable on its own.
- **Item 5** — abandon if any of: the passive `StartJob` hook cannot obtain a usable `(ctx, job)` on the body; the first stills encode ASSERTs on `LosslessEncMode` or geometry and the value space is not discoverable within two sessions; or JPCORE proves unavailable during movie LiveView and the workaround is another soft-preview subsystem at PR #292's scale with no sibling to copy. In any of those cases: ship stills lossless DNG if it works, publish the RE, and stop.

Direction-level:

- **If upstream contribution turns out not to be an end in itself.** INTENT lists this under "what Chris has NOT said": whether upstreaming matters for its own sake or only as evidence the method works. If the answer is the latter, item 5's 6–10 sessions stop being justified — items 0–4 still deliver personal camera capability, item 5 mostly delivers a contribution.
- **If the body-session budget cannot be met.** The queue needs 5–7 short sessions with Chris holding the camera. If those are not available on a timescale that keeps the work coherent, the honest move is to run S1 alone, bank items 0–3, and park the rest — rather than half-executing item 4 or 5 and leaving another paused track.
- **If a maintainer signals that 6D2-specific feature patches are unwelcome without a second reviewer.** Layer 3 records that untested LLM patches are a net cost to them and that they do not accept LLMs for review. If the review capacity is not there, the queue's upstream value collapses to the bug reports (items 0 and 4's measurement), which are still worth filing but do not justify the feature work as a contribution strategy.

---

## Corrections this file makes to existing project documents

Recorded here rather than edited into the source documents, because those are owned elsewhere.

1. **`FEATURE_MATRIX.md` Tier 3 overstates the `IMGPLAY_ZOOM_LEVEL_ADDR` item.** Cropmarks is not blocked on finding an address — seven D6/7/8 ports enable it with a placeholder they document as wrong, all four consumers read the value only, and the 6D2 cannot write to it because it lacks `IMGPLAY_ZOOM_POS_X`. Cropmarks should move from section 4 (Blocked / stub missing / M) to a two-line Tier-1 enable. The other three features have no modern-DIGIC precedent at all and should be recorded as *untested*, not *unblocked*.
2. **Spike 008's flagged "highest-value 30-minute follow-up" is already answered, negatively.** `0xE02E839A(job)` is `(job->picttype & 0x1D000) != 0`, a bit test on a field set at job creation — not a settable shooting-menu property. Phase 2 does not collapse; the stated next action needs rewriting.
3. **Spike 007's block-0 identification is refuted, not merely uncertain**, and the body-test plan's `buf_addr` candidate list is incomplete (six `0x304` base records, not five, plus a `0x305` record). Both are already annotated in the spike; this file treats the annotation as the operative version.
4. **`BODY_TEST_PLAN.md` session 5 item 2 (custom-WB discriminator) was never run** and is the cheapest unrun measurement in the project. It should ride on S1.

---

## Key references

- Movie dual-ISO: [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/007-dual-iso-scoping/movie-table-analysis.md](.planning/spikes/007-dual-iso-scoping/movie-table-analysis.md) and its adversarial-verification section; [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/007-dual-iso-scoping/development-results.md](.planning/spikes/007-dual-iso-scoping/development-results.md) for the measured +1.71 EV and the cr2hdr result; module code at ml/modules/dual_iso/dual_iso.c lines 332-410 (the patcher), 1148-1217 (the DMA-descriptor scan), 1298-1315 (the 6D2 branch).
- The assert that interrupts it: [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/007-dual-iso-scoping/crash-analysis.md](.planning/spikes/007-dual-iso-scoping/crash-analysis.md), including the verdict that its own proposed fix must not be applied.
- Lossless: [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/008-lossless-compression-scoping/README.md](.planning/spikes/008-lossless-compression-scoping/README.md) — Ghidra passes 1, 2 and 3 with their adversarial annotation; the measured card figures in [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/008-lossless-compression-scoping/card-benchmark-results.md](.planning/spikes/008-lossless-compression-scoping/card-benchmark-results.md).
- Raw-video state and the self-recording pattern: [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/006-rawvideo-memory/README.md](.planning/spikes/006-rawvideo-memory/README.md).
- Focus box and clean HDMI: [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/003-cheap-wins-scoping/README.md](.planning/spikes/003-cheap-wins-scoping/README.md), 2026-08-15 section; the drafted comment at [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/prs/DRAFT-comment-on-upstream-PR-223.md](.planning/prs/DRAFT-comment-on-upstream-PR-223.md).
- Feature classification and the cheap-win ranking: [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/FEATURE_MATRIX.md](FEATURE_MATRIX.md).
- Build traps, the module-staleness gate, and the state of every patch: [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/patches/README.md](patches/README.md).
- Session ordering and the standing camera rules: [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/BODY_TEST_PLAN.md](.planning/BODY_TEST_PLAN.md), [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/ROADMAP.md](.planning/ROADMAP.md).
- Control names for any instruction written for Chris: [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/docs/6D2_CONTROLS.md](docs/6D2_CONTROLS.md).
