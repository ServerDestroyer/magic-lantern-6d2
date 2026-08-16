# Session 5 MLV analysis — did the re-arm fix work?

Scope: the five MLVs in `footage/session5/`, cross-checked against `tools/RAWDIAG-session5.txt`,
`tools/CRASH00-session5.txt`, the CR2 EXIF clock, and prior-session MLVs in `footage/`.

Method: own block-walk over every byte of each file (structure from `tools/mlv_preview.py`
plus `ml/modules/raw_video/mlv_rec/mlv.h`), plus a 14-bit pixblock sample of 5 rows
(y = 0, 270, 540, 810, 1079) × 320 pixels of **every** VIDF payload in all five files.
Analysis scripts are in the session scratchpad, not in the repo.

**Headline: the re-arm fix worked.** Four consecutive takes in one boot session, each
preceded by a successful memory-suite rebuild, each producing a complete finalized file.
No freeze, no truncation, no degradation between take 1 and take 2.

---

## 1. Per-file table

All five files: `MLVI v2.0`, `videoClass=1` (uncompressed raw), `fileNum 0 / fileCount 0`
(single-chunk, no spanning), camera `Canon EOS 6D Mark II` model `0x80000406` serial
`97D16330F8`, lens `TAMRON SP 24-70mm F/2.8 Di VC US` @ 24 mm f/2.8, EXPO shutter 22627,
block set `MLVI RAWI RAWC IDNT EXPO LENS RTCI WBAL VERS NULL VIDF×n`.

| | M15-2102 | M15-2103 | M15-2104 | M15-2105 | M15-2106 |
|---|---|---|---|---|---|
| file size (B) | 206857216 | 206857216 | 228631552 | 232260608 | 206857216 |
| **`videoFrameCount` (hdr @0x24)** | **57** | **57** | **63** | **64** | **57** |
| **actual VIDF blocks** | **57** | **57** | **63** | **64** | **57** |
| **finalized?** | **YES** | **YES** | **YES** | **YES** | **YES** |
| `sourceFpsNom/Denom` (@0x2C/0x30) | 59938/1000 | 59946/1000 | 59933/1000 | 59946/1000 | 59941/1000 |
| = fps | 59.938 | 59.946 | 59.933 | 59.946 | 59.941 |
| RAWI xres×yres | 1920×1080 | 1920×1080 | 1920×1080 | 1920×1080 | 1920×1080 |
| RAWI width×height (raw) | 2128×1208 | 2128×1208 | 2128×1208 | 2128×1208 | 2128×1208 |
| RAWI pitch / bpp | 3724 / 14 | 3724 / 14 | 3724 / 14 | 3724 / 14 | 3724 / 14 |
| RAWI black / white | 2047 / 16200 | 2047 / 16200 | 2047 / 16200 | 2047 / 16200 | 2047 / 16200 |
| VIDF blockSize | 3629056 | 3629056 | 3629056 | 3629056 | 3629056 |
| `frameSpace` | 32 | 32 | 32 | 32 | 32 |
| per-frame payload (B) | 3628992 | 3628992 | 3628992 | 3628992 | 3628992 |
| first VIDF ts (µs) | 98783 | 106134 | 88602 | 89292 | 115057 |
| last VIDF ts (µs) | 1033068 | 1040298 | 1123083 | 1140232 | 1049298 |
| span (µs) | 934285 | 934164 | 1034481 | 1050940 | 934241 |
| median Δt (µs) | 16676.0 | 16679.5 | 16685.0 | 16685.0 | 16677.5 |
| **fps from median Δt** | **59.9664** | **59.9538** | **59.9341** | **59.9341** | **59.9610** |
| fps from span, (n-1)/span | 59.9389 | 59.9466 | 59.9334 | 59.9463 | 59.9417 |
| Δt min / max (µs) | 16574 / 16839 | 16526 / 16879 | 16574 / 16815 | 16565 / 16856 | 16569 / 16827 |
| Δt σ (µs) | 65.8 | 62.2 | 56.9 | 60.7 | 55.5 |
| Δt outliers >25 % off median | 0 | 0 | 0 | 0 | 0 |
| frameNumber range | 0…56 | 0…56 | 0…62 | 0…63 | 0…56 |
| gaps / dupes | none / none | none / none | none / none | none / none | none / none |
| ts monotonic increasing | yes | yes | yes | yes | yes |
| RTCI (camera clock) | 21:02:45 | 21:02:50 | 21:03:00 | 21:03:45 | 21:05:57 |
| MLVI fileGuid | 6992804013632433684 | 3671091434550597601 | 13865592701261901716 | 9609178449695513384 | 7618725681781425171 |
| WBAL mode / kelvin | 0 / 5200 | 0 / 5200 | 0 / 5200 | **1** / 5200 | 0 / 5200 |
| WBAL R / G / B | 485/1024/610 | 485/1024/610 | 485/1024/610 | 485/1024/610 | 485/1024/610 |
| VERS (mlv_lite) | 2026-08-16 02:39:11 UTC | same | same | same | same |
| extra VERS | — | — | — | — | `dual_iso built 2026-08-15 18:50:44 UTC` |
| extra block | — | — | — | — | `DISO` (dualMode=0, isoValue=3) |

All VERS strings read `commit (no version)` — the build stamps the timestamp but not the SHA.

### Byte accounting closes exactly on every file

`1024 + n × 3629056 == file size` for all five (57→206857216, 63→228631552, 64→232260608).
The 1024 B is the fixed header-block area (MLVI…VERS plus a NULL pad block); 2106 carries an
extra VERS and a DISO block and is still exactly 1024 B, so the NULL block absorbed them.
`end_pos == file size` on all five — no trailing garbage, no truncated final block.

### Payload sanity (not just block structure)

Every VIDF payload in all five files was unpacked and sampled. Frames 0…n-2 in every file are
real image data: mean ≈ 3100–3360 (14-bit), min ≈ 120–128, max ≈ 15490–15497, zero-byte
fraction 0.006–0.009. No zeroed, constant, or duplicated frame anywhere.

**One pre-existing defect, unchanged:** the *last* frame of every file is dark/unfilled —
2102 f056 mean 1664.6 max 2219; 2103 f056 mean 1665.7 max 2217; 2104 f062 mean 1663.9 max 2226;
2105 f063 mean 1662.0 max 2244; 2106 f056 mean 1662.3 max 2210. Max is barely above the 2047
black level, so it is a slot written out without an EDMAC fill. This is **not** a session-5
regression: prior-session `M15-1945` f056 (mean 1779.5 max 3453) and `M15-1934` f056
(mean 1949.1 max 3498) show the same thing. It costs one frame per take and is identical in
take 1 and take 2, so it does not bear on the re-arm question.

---

## 2. Answers

### Q1 — Which files are the double-REC pair?

**M15-2102 → M15-2103.** Not a pair in isolation, either: it is the front of a run of four
back-to-back takes in one boot session.

Two independent clocks agree.

RTCI (camera RTC, second resolution, from block content — mtime was not used anywhere):

| take | RTCI start | duration | ends | gap to next start |
|---|---|---|---|---|
| 2102 | 21:02:45 | 0.934 s | 21:02:45.9 | **+5 s** |
| 2103 | 21:02:50 | 0.934 s | 21:02:50.9 | +10 s |
| 2104 | 21:03:00 | 1.034 s | 21:03:01.0 | +45 s |
| 2105 | 21:03:45 | 1.051 s | 21:03:46.1 | +132 s |
| 2106 | 21:05:57 | 0.934 s | 21:05:58.0 | — |

`tools/RAWDIAG-session5.txt` boot session A, sub-second resolution — five `[probe]` lines:

```
[2.013]   [probe] max 135MB steps 34 slowest 101ms@136MB last TIMEOUT
[59.511]  [probe] max 135MB steps 34 slowest  91ms@136MB last TIMEOUT
[64.194]  [probe] max 135MB steps 34 slowest 102ms@136MB last TIMEOUT
[75.196]  [probe] max 135MB steps 34 slowest 100ms@136MB last TIMEOUT
[119.865] [probe] max 135MB steps 34 slowest  92ms@136MB last TIMEOUT
[137.538] raw inactive: lv=0 movie=0 gui=0
```

Probe deltas 4.683 / 11.002 / 44.669 s against RTC deltas 5 / 10 / 45 s (±1 s quantization) —
a one-to-one match. So probe@59.511 = 2102, probe@64.194 = 2103, probe@75.196 = 2104,
probe@119.865 = 2105.

**The second REC press landed 4.683 s after the first arm.** Take 1 ran 0.934 s, so the button
was pressed ≈ 3.75 s after auto-stop. That is the double-REC of BODY_TEST_PLAN §Session 5 test 1.

The filename numbering is consistent and is *not* an independent clock: ML names files
`M<dd><hh><mm>`, so 2102 and 2103 (both at 21:02) and 2104/2105 (both at 21:03) collided and
were bumped to the next free suffix. Do not read the suffix as a minute.

2106 is a different boot session (boot B in RAWDIAG): it carries a `dual_iso` VERS block that
2102–2105 do not, and ML modules only load at startup. Its take is a fresh first-take, not a
second-of-pair.

### Q2 — Did the second take record a full, valid, finalized file? **YES.**

This is the headline. `M15-2103` — the take that previously hard-froze the camera:

- `videoFrameCount` at offset 0x24 = **57**; actual VIDF blocks counted by full-file walk = **57**. Header finalized.
- File size **206,857,216 B = 1024 + 57 × 3,629,056** exactly. Nothing truncated, nothing trailing.
- frameNumbers **0…56**, 57 unique, strictly monotonic, **zero gaps, zero duplicates**.
- Timestamps strictly increasing, 98783→…, span 934164 µs, **zero Δt outliers** — no dropped frame, no stall.
- All 57 payloads carry real image data (frames 0–55 mean ≈ 3140–3360, max ≈ 15490); only the
  known last-frame artifact, identical to take 1's.
- Byte-for-byte the same *size* as take 1 (206857216) with a different `fileGuid`
  (3671091434550597601 vs 6992804013632433684) — a genuinely separate recording, not a re-link.

**The direct memory evidence:** `[probe]` is emitted from `ml/src/exmem.c:283` inside
`shoot_malloc_autodetect()`, which runs only from `shoot_malloc_suite(0)` — i.e. only from
`realloc_buffers()` at `ml/modules/raw_video/mlv_lite/mlv_lite.c:1556`, immediately after
`free_buffers()` (`mlv_lite.c:1516`, which calls `shoot_free_suite`/`srm_free_suite` and nulls
both suite pointers). **One `[probe]` line == one successful suite teardown-and-rebuild.**
Boot A logged five of them, all reporting the identical `max 135MB steps 34`. The arithmetic
checks out — the loop steps 4 MB at a time, step 34 at 136 MB fails, so
132 MB + 4 MB backup − 1 MB = 135 MB. If the suites had been torn down and never rebuilt, the
second arm would have produced no probe line at all, or one reporting a much smaller max.
It reported the full 135 MB, four times in a row.

Takes 3 and 4 (2104, 2105) are equally clean: 63/63 and 64/64, gapless, monotonic, byte-exact.

### Q3 — Degradation between first and second take? **None. Full recovery, not partial.**

| | take 1 | take 2 | take 3 | take 4 |
|---|---|---|---|---|
| file | 2102 | 2103 | 2104 | 2105 |
| frames | 57 | **57** | 63 | 64 |
| duration | 0.934 s | 0.934 s | 1.034 s | 1.051 s |
| probe max | 135 MB | 135 MB | 135 MB | 135 MB |

Take 2 matched take 1 exactly — same frame count, same file size to the byte. Takes 3 and 4
recorded *more* frames than take 1 (+6, +7). Buffer recovery is complete, not partial.

For context, prior sessions on the same buffer configuration: `M15-1934` 57, `M15-1945` 57,
`M15-1826` 57, `M15-1750` 56. Session 5's 57/57 is exactly the established buffer-full length;
63/64 exceeds every prior take on this build family.

Unexplained (flagged, not guessed): why 2104/2105 got 6–7 more frames than 2102/2103 when the
probe reported the same 135 MB every time. Buffer-full auto-stop depends on instantaneous card
drain rate as well as buffer size, but nothing in these files measures write throughput — VIDF
timestamps are capture times, not write times. The bench BMPs in `tools/bench/` were not
decoded for this analysis.

### Q4 — Is the measured-fps header stamp still correct? **Yes, to the millifps.**

Stamped `sourceFpsNom/1000` vs `(n−1) × 10⁶ / (last_ts − first_ts)` computed from the VIDF
timestamps in the same file:

| file | stamped | measured from timestamps | error |
|---|---|---|---|
| 2102 | 59.938 | 59.9389 | 0.0009 |
| 2103 | 59.946 | 59.9466 | 0.0006 |
| 2104 | 59.933 | 59.9334 | 0.0004 |
| 2105 | 59.946 | 59.9463 | 0.0003 |
| 2106 | 59.941 | 59.9417 | 0.0007 |

Agreement to <0.001 fps on all five — the stamp is literally the span-derived value truncated
to millifps. All five are 59.94p; the owner did not change frame rate.

Regression check against older builds in `footage/`, which is what makes this meaningful:

| file | build stamp | fps stamped | fps measured |
|---|---|---|---|
| M15-1612 | 2026-08-15 18:50:39 | **178.993** | 59.945 |
| M15-1750 | 2026-08-15 18:50:39 | **229.442** | 59.944 |
| M15-1826 | 2026-08-16 00:43:41 | **215.430** | 59.954 |
| M15-1934 | 2026-08-16 02:17:20 | 59.943 | 59.944 |
| M15-1945 | 2026-08-16 02:39:11 | 59.950 | 59.950 |
| session 5 (all) | 2026-08-16 02:39:11 | 59.933–59.946 | matches |

The fps fix landed between the 00:43:41 and 02:17:20 builds and is still holding in the
02:39:11 build used for the whole of session 5.

### Q5 — WBAL check (test 2)

| file | wb_mode | meaning | kelvin | WBGain R / G / B |
|---|---|---|---|---|
| M15-2102 | 0 | `WB_AUTO` | 5200 | 485 / 1024 / 610 |
| M15-2103 | 0 | `WB_AUTO` | 5200 | 485 / 1024 / 610 |
| M15-2104 | 0 | `WB_AUTO` | 5200 | 485 / 1024 / 610 |
| **M15-2105** | **1** | **`WB_SUNNY`** | 5200 | 485 / 1024 / 610 |
| M15-2106 | 0 | `WB_AUTO` | 5200 | 485 / 1024 / 610 |

Enum from `ml/src/property.h:264-272` (`WB_AUTO 0`, `WB_SUNNY 1`, `WB_CLOUDY 2`,
`WB_TUNGSTEN 3`, `WB_FLUORESCENT 4`, `WB_FLASH 5`, `WB_CUSTOM 6`, `WB_SHADE 8`, `WB_KELVIN 9`).

**One file differs, and it is the wb_mode field that moved.** M15-2105 records `wb_mode = 1`
(Daylight/Sunny) while every other file in session 5 — and every prior-session file checked
(M15-1612, 1750, 1826, 1934, 1945) — records `wb_mode = 0`. The owner changed the WB preset
between 2104 and 2105 (RTC gap 45 s, consistent with a menu trip), and the change was captured.

**Settled: `wb_mode` tracks reality. `WBGain_R/G/B` and `kelvin` do not, and are not supposed to.**
R=485 G=1024 B=610 is byte-identical across all ten files examined, spanning two WB modes.
ML's own field comments say why — `ml/src/lens.h:64-66`: `WBGain_R/G/B` are "only used when
wb_mode = WB_CUSTOM", and `lens.h:63` / `property.h:257`: `kelvin` is "only used when
wb_mode = WB_KELVIN". The camera was never in either mode, so both fields carry a stale slot
value. **This confirms the prior hypothesis** that 485/1024/610 is the unused custom-WB slot
recorded while in auto WB — it is not a parser bug and not a broken metadata path.

Not settled, and it needs another body test: the WB test was run with a *preset* (mode 1), not
with WB_CUSTOM (mode 6). To prove the gains themselves populate, a take with the camera in
Custom WB is still required. A WB_KELVIN take would likewise settle the kelvin field.

---

## 3. Side observations

**Dual ISO was OFF for the video take.** M15-2106 carries a `DISO` block (24 B at file offset
732) with `dualMode = 0`, `isoValue = 3`. Per `ml/modules/dual_iso/dual_iso.c:1222`,
`dualMode` is `dual_iso_is_active()` — so the module was *loaded* but dual ISO was not engaged
during that recording. The stills test (test 3) is in the CR2s, which are outside this analysis.

**Upstream bug in the DISO block: uninitialized timestamp.** The block reports
`timestamp = 21532833` µs, far outside the file's own 0…1049298 µs range, and it sits at byte
offset 732 in the header area. `dual_iso_mlv_rec_cbr()` (`dual_iso.c:1220-1234`) mallocs the
block and sets `blockType`, `blockSize`, `dualMode`, `isoValue` — but never the `timestamp`
field. This is upstream ML code, not a 6D2 change, and is cosmetic.

**The crash log is not in the raw-video path.** `tools/CRASH00-session5.txt`:

```
ASSERT: m_VSize
at ./ImgSeqCoop/ImgSeqCoopStore.c:194, shoot_task:e04471f1
lv:1 mode:0
Magic Lantern version: 2026-08-15.6D2.111
Git commit: 3f24042a4 dev
Built on 2026-08-16 02:39:10 UTC by chris@legion.
Free Memory  : 409K + 2039K
```

A Canon-side assert in `shoot_task` with LiveView on — the stills path, not mlv_lite. It cannot
have interrupted any of the five recordings: all five are byte-exact and finalized. Timing
support (not proof — the crash log carries no wall clock): CR2 EXIF DateTimeOriginal runs
21:06:34, 21:06:46, 21:08:02, 21:08:30, 21:09:36, i.e. entirely *after* the last MLV at
21:05:57, and RAWDIAG boot B's final line `[44.598] raw inactive: lv=1 movie=0 gui=0` is the
switch out of movie mode into photo LiveView. The stills-side failure is a separate
investigation.

**Boot session reconstruction** (RAWDIAG two concatenated sessions + RTC + CR2 EXIF):

- Boot A — probe@2.0 (startup), 2102 @59.5, 2103 @64.2, 2104 @75.2, 2105 @119.9, LV exit @137.5.
- Boot B — dual_iso loaded; probe@1.9, menu @13.2 (`gui=9`), probe@20.3, 2106 @26.0,
  out of movie mode @44.6, then the five CR2s.

The 132 s between 2105 and 2106 covers enabling dual_iso and restarting ML — consistent with
2106 being the only file carrying a dual_iso VERS block.

---

## 4. Verdict

The re-arm fix works, and the evidence is stronger than the test asked for: **four** consecutive
takes in a single boot, each with an independently logged 135 MB memory-suite rebuild, each
producing a complete, finalized, gapless file. The second take — the exact case that previously
required a battery pull — is indistinguishable from the first: 57/57 frames, 206,857,216 B,
zero gaps, zero timestamp outliers, real pixel data in every frame. No freeze, and no partial
recovery.

Residual items, none blocking:

1. Frame-count variance 57 → 63/64 across takes at a constant 135 MB probe is unexplained.
2. `WBGain_R/G/B` still unproven — needs one take shot in WB_CUSTOM (mode 6).
3. The dark last frame of every take is pre-existing and costs one frame per take.
4. `CRASH00` assert `m_VSize` in the stills path is open and unrelated to raw video.
5. VERS strings say `commit (no version)` — the build stamps time but not SHA.

---

## ADVERSARIAL VERIFICATION VERDICT: HEADLINE SURVIVES, THREE DETAILS CORRECTED

Independent re-parse of all 5 session-5 + 11 prior MLVs confirms: **the re-arm fix
works** — 2102→2103 is a genuine back-to-back pair, the second take is complete,
finalized, gapless, and identical in length to the first (57/57 frames).

Corrections to this document:
1. **REFUTED — "dark final frame in every take".** There is no dark final frame.
   Last-frame mean-vs-rest z-scores across the five files: -0.00, -0.23, -1.03,
   +1.26, -0.77 sigma — pure noise. `frameSpace = 32` for every VIDF. The original
   reading was a decode artefact, not a defect. Do not carry this as an open bug.
2. **Mechanism restated:** "one `[probe]` line = the arm before a recording" is
   wrong; `free_buffers()` runs unconditionally at the end of every take, so probe
   lines do not map one-to-one onto REC presses the way stated. The *conclusion*
   (each take got a genuine 135 MB rebuild) still holds.
3. The card-write constant derived from take lengths (81.5-82.6 MB/s) was a
   selected subset; solving over all pairings gives 80.3-87.3 MB/s. Use the
   directly measured benchmark figure (82.6 MB/s) instead — see spike 008's
   `card-benchmark-results.md`.
