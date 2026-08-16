# MOVIE-mode MPU spell capture — extraction & diff vs PHOTO-mode

Source log: `tools/6D2-DEBUGMSG-body-movie.txt` (2,097,090 bytes, 28,463 lines after sanitising).
Generated header archived as `tools/6D2_spells_body_movie.h` (504 lines).
Baseline compared against: `qemu-eos/hw/eos/mpu_spells/6D2.h` (PHOTO mode, 256 lines) — **not modified**.

## 1. Extraction

Procedure (as prescribed):

1. Sanitised a copy: read bytes, strip `\x00`, `decode('utf-8', errors='ignore')`, re-encode →
   `<scratch>/movie/6D2-startup.log`. The body log contained **0 NUL bytes** but 9 invalid UTF-8
   bytes were dropped (2,097,090 raw → 2,097,081 chars). The `<MODEL>-…` filename is required
   because `extract_init_spells.py` derives the model from `log_filename[:index("-")]`.
2. `ML_PLATFORM_DIR=/home/chris/ml6d2/magiclantern_simplified/platform/ python3 extract_init_spells.py <scratch>/movie/6D2-startup.log > 6D2-movie.h`
3. Exit 0. Emits `static struct mpu_init_spell mpu_init_spells_6D2[]` with the usual 7 trailing `#include`s.

### Problems hit

* **Only Python `SyntaxWarning`s** (unescaped regex sequences in the extractor itself) plus one
  `GUI_Control without bindReceiveSwitch` on the very first GUI_Control line. Neither affects output.
* **No DIAG trailer, log ends mid-stream** — as expected. The last three emitted entries are
  repeated `{ 0x10, 0x0f, 0x0e, 0x3d, … 0x2e, 0xe0 }` blocks; the final one is the truncation point.
  The extractor still closes it correctly (`// { 0 } } },` + closing brace), so the header is
  syntactically valid C. The last block's reply list is simply incomplete — it is in the commented
  tail anyway, so nothing usable is lost.
* **Most of the file is commented out.** The extractor emits `NotifyGUIEvent` (entry 44) as a
  commented block and then hits `PROP_SHOOTING_TYPE` (entry 45), which sets `comment_all_blocks = True`
  permanently. Everything from index 44 to the end is therefore `//`-prefixed. This is the same
  mechanism that trimmed the photo-mode capture; it is not a movie-specific failure.

### Counts

| | MOVIE | PHOTO (`6D2.h`) |
|---|---|---|
| spell entries emitted | **128** | **47** |
| … active (uncommented) | **44** | **45** |
| … commented out | 84 | 2 |
| reply spells total | 188 | 104 |
| … inside active entries | 122 | 102 |
| distinct reply `(class,id)` keys | 111 | 82 |

The active window is essentially the same length in both modes (44 vs 45 spells). The extra 84
commented entries in the movie capture are post-init runtime traffic (LiveView `09 xx` polling,
`0e xx` display/OLC chatter, `PROP_BV`/`PROP_LV_BV` metering) that the photo log did not reach
before its own cut-off.

## 2. Request-spell diff (first byte array of each entry)

**No structurally new request spell exists in movie mode.** Comparing active entries only:

MOVIE-only request byte arrays (4):

| request | note |
|---|---|
| `08 06 00 00 01 07 00 00` — Complete WaitID PROP_ISO | ordering artefact: same ack shape, different property, present in photo's `Init` window |
| `08 06 00 00 01 34 00 00` — Complete WaitID PROP_CARD1_IMAGE_QUALITY | same |
| `08 06 00 00 01 35 00 00` — Complete WaitID PROP_CARD2_IMAGE_QUALITY | same |
| `0a 08 03 06 00 00 15 71 00 00` — PROP_AVAIL_SHOT | **value only**: 0x1571 (5489) vs photo 0x1576 (5494). Free-shot counter, not a mode difference |

PHOTO-only request byte arrays (8) — `PROP_AVAIL_SHOT(0x1576)`, `PROP_BATTERY_REPORT`,
`COM_FA_CHECK_FROM`, `PROP_ACTIVE_SWEEP_STATUS`, `PROP_GPS_TIME_SYNC`, `PROP_BURST_COUNT(0x0f)`,
`PROP_TFT_STATUS(0x00)`, `PROP_DL_ACTION`. All eight **do appear in the movie capture** — they are
just past the `PROP_SHOOTING_TYPE` cut and therefore commented out (movie entries 47–49, 51, …).

Conclusion: the init request sequence is mode-independent. Only the MPU's **reply payloads** change.

## 3. Reply diff — same request, different reply

18 `(class,id)` reply keys carry different bytes between the two captures. Split by cause:

### 3a. Genuine mode-dependent replies (merge candidates)

| class/id | property | PHOTO | MOVIE |
|---|---|---|---|
| `01 4f` | **PROP_FIXED_MOVIE** | `… 01 4f 00 00` | `… 01 4f 01 00` |
| `01 48` | **PROP_LIVE_VIEW_MOVIE_SELECT** | `… 01 48 01 00` | `… 01 48 02 00` |
| `02 0f` | **Movie group** (94 B) | `[8]=0x01`, `[51]=0x00` | `[8]=0x02`, `[51]=0x03` |
| `02 0e` | **Mode group** (148 B) | `[8]=0x02`, `[92]=0x01` | `[8]=0x03`, `[92]=0x00` (variant 2 also differs at `[6] 03→05`, `[10] 03→00`, `[41] 6d→70`, `[65] 8d→88`, `[118] 00→07`, `[122] 01→00`, `[136] 00→01`) |
| `02 0d` | Card group (48 B) | `[27]=0x03` | `[27]=0x00` (movie clip counter / no-still-count) |
| `02 10` | AF group (72 B) | `[14]=0xff`, `[15,18,20-24]=0x00` | `[14]=0x00`, `[15,18,20-24]=0xff` (AF point set differs in LV) |

### 3b. Environmental noise — do NOT merge

| class/id | why |
|---|---|
| `02 12` **Lens group** | movie capture is **all zeros** — no lens was mounted (or lens comms had not completed) when the movie log was taken. The photo-mode Lens group (EF 24-105 style payload, `01 20 50 01 eb …`) is the good one. |
| `03 1d` PROP_BATTERY_REPORT | 0x5f vs 0x63 — battery level |
| `03 38` PROP_BOARD_TEMP / `03 17` PROP_EFIC_TEMP | 0x80/0xa2 vs 0x9a / 0x9c vs 0x9b — temperature |
| `01 7a` PROP_GPS_SATELITE_STATUS, `03 52` (GPS/WGS-84 record) | GPS fix state |
| `0a 08` PD_NotifyOlcInfoChanged | embeds the same shot counter 0x1571 vs 0x1576 |
| `0e 2d`, `06 22`, `03 42` PROP_LED_LIGHT, `03 5c`, `01 a7` | top-LCD / button / LED state at capture time |

### 3c. Movie-only reply `(class,id)` keys (35)

13 of them land in **active** (uncommented) entries and are therefore directly mergeable:
`PROP_CARD2_EXISTS (01 21)`, `PROP_PICTURE_STYLE (01 1d)`, `PROP_ISO (01 07)`,
`PROP_HIGHISO_NOISE_REDUCTION (01 74)`, `PROP_HTP (01 75)`, `PROP_CARD1_IMAGE_QUALITY (01 34)`,
`PROP_CARD2_IMAGE_QUALITY (01 35)`, `PROP_AFFRAME_ENABLE_SETTING (03 4e)`, `PROP 80030075 (03 6d)`,
`PROP_AFPOINT (01 0a)`, `PROP_AF_SELECT_FOCUS_AREA (01 6c)`, `PROP 8004005F (01 9f)`,
`PROP 80040060 (01 a0)`.

The remaining 22 are in the commented tail and are LiveView/metering runtime traffic:
`PROP_LV_BV (09 0a)`, `PROP_BV (09 10, 6 variants)`, `PROP_LV_HALF_SHUTTER (09 0c)`,
`PROP_ORIENTATION (09 0f)`, `PROP_STROBO_CHARGE_INFO_MAYBE (09 0e)`, `09 1c`, `09 34`,
`PROP_SHOOTING_TYPE (04 0c)`, `PROP_SHUTTER (01 05)`, `PROP_IMAGE_ASPECT_RATIO (01 92)`,
`PROP_CARD_EXTENSION (01 37)`, `05 16`, `05 17`, and a batch of `0e xx` display records.
These are **not init spells** and must not be pasted into the init table verbatim — but they are the
raw material for a future LiveView/movie-state extension of `LiveView.h`.

Only 6 keys are photo-only: `PROP_MIRROR_DOWN_IN_MOVIE_MODE (03 37)`, `04 30`,
`NotifyGUIEvent (04 00)`, `PROP_BATTERY_CHECK (03 16)`, `PROP_ACTIVE_SWEEP_STATUS (04 0d)`,
`PROP_DL_ACTION (04 15)` — all of which the extractor deliberately suppresses or which sit past the
movie log's comment cut.

## 4. Frame-rate / video-format finding (the point of the exercise)

`known_spells.py` documents the `02 0f` **Movie group** as carrying, among others,
`0x80000039 = PROP_VIDEO_MODE` (a.k.a. `PROP_MOVIE_PARAM`) and `0x8004001C = PROP_LIVE_VIEW_MOVIE_SELECT`.

Findings on the 94-byte `02 0f` record:

* Byte `[8]` of the Movie group tracks `PROP_LIVE_VIEW_MOVIE_SELECT` exactly — it moves `0x01 → 0x02`
  in lockstep with the standalone `01 48` reply. `0x02` is the movie-enabled value. This is the
  single cleanest movie/photo discriminator in the whole capture.
* Byte `[51]` moves `0x00 → 0x03` in the movie `Init` reply. The second `02 0f` occurrence later in
  the movie log has `[51] = 0x00` again, so this looks like a transient state field rather than the
  format record.
* **The frame-rate constants are byte-identical in both modes.** Bytes `[55..62]` are
  `00 03 0e 10 00 00 0b b5` in photo *and* movie. `0x0BB5 = 2997` = 29.97 fps ×100, and `0x0E10 = 3600`
  is the paired timer/denominator field. This is the practically important result for QEMU: **the
  existing photo-mode `6D2.h` already feeds the emulated ICU a well-formed frame-rate record.** The
  old "frame-rate switch receiving garbage" failure cannot be blamed on a missing movie-mode
  Movie-group payload — the payload was already correct; only the mode selector bytes were wrong.
* `PROP_VIDEO_MODE` as a **standalone** spell (`01 4e`) appears **zero times** in the movie log, as do
  `PROP_AE_MODE_MOVIE (01 50)` and `PROP_SW2_MOVIE_START (01 8a)`. The 6D2 carries all of it inside the
  `02 0f` aggregate. There is nothing extra to capture for frame rate; there is only the aggregate.
* `Mode group (02 0e)` byte `[8]` also flips `0x02 → 0x03` — the mode-dial/shooting-mode field, whose
  movie value is 3. `PROP_SHOOTING_MODE (01 00)` itself reads `0x03` in *both* captures, so `02 0e[8]`
  is a distinct field (likely the "current operating mode" the ICU keys its LiveView setup off).

## 5. Merge recommendation

**Do not add a second spell set. Do not replace the photo-mode base.** Ship a single
`mpu_init_spells_6D2[]` that stays photo-derived, and hand-patch six reply bytes into it.

Rationale: the request sequence is identical between modes (§2), so a mode-dependent spell table
would duplicate ~45 entries to change ~6 bytes. `qemu-eos`'s `MPU_SPELL_SET(cam)` macro
(`hw/eos/mpu.c:1207-1233`) binds exactly one static array per model and there is no runtime hook to
swap it — adding one would mean inventing a `-mpu-mode` machine option and threading it through
`mpu_spells_init()`, which is a real upstream API change for a six-byte delta. Not worth it.

Concretely, the minimal merge is:

1. In `6D2.h`, in the `Init` block, change `PROP_FIXED_MOVIE` `01 4f 00 00` → `01 4f 01 00` and
   `PROP_LIVE_VIEW_MOVIE_SELECT` `01 48 01 00` → `01 48 02 00` **only if** we want QEMU to boot
   straight into movie mode. If QEMU should keep booting into photo mode (the current, verified-good
   behaviour), leave them alone — these are the switch, not a fix.
2. Regardless of (1), **append the 13 movie-only active replies from §3c** (`PROP_ISO`,
   `PROP_PICTURE_STYLE`, `PROP_CARD1/2_IMAGE_QUALITY`, `PROP_HTP`, `PROP_HIGHISO_NOISE_REDUCTION`,
   `PROP_AFPOINT`, `PROP_AF_SELECT_FOCUS_AREA`, `PROP_AFFRAME_ENABLE_SETTING`, `03 6d`, `01 9f`,
   `01 a0`, `PROP_CARD2_EXISTS`) into the corresponding existing photo-mode entries. These are
   properties the photo log never delivered at all, and unanswered property reads are exactly the
   class of bug that produced the original garbage-read. This is a strict addition with no risk to
   the currently-passing boot.
3. Take **nothing** from §3b — in particular do not import the movie capture's all-zero
   `Lens group (02 12)`; it would regress the emulated lens to "none attached".
4. Keep `tools/6D2_spells_body_movie.h` as the archive of record for the commented LiveView tail
   (`09 xx` / `0e xx` traffic). If we later want QEMU to actually *enter* LiveView, that tail — not
   the init table — is the source, and it belongs in a 6D2-specific extension of `LiveView.h`,
   which is already `#include`d by the generated header.

Sequencing: land (2) first and re-run the existing `6D2-ship-qemu-verification` pass; it should be a
no-op for boot and a net gain in property coverage. Only then consider (1), behind a deliberate
decision about which mode the emulated 6D2 should present.

Nothing in `qemu-eos/` was modified, no rebuild was run, no commit was made.
