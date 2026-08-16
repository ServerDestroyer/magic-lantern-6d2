# MLV analysis #2 — post-"0006" fps un-shadow build

Date: 2026-08-15. Analysed with a throwaway stdlib block-chain scanner (same parse
as `tools/mlv_preview.py`), plus one decoded mid-file frame per new recording.

Files: `footage/M15-1612.MLV` (baseline, pre-fix), `M15-1750.MLV` (pre-fix),
`M15-1826.MLV` and `M15-1828.MLV` (post-fix "0006" build).

## Per-file table

| | M15-1612 (baseline) | M15-1750 | M15-1826 | M15-1828 |
|---|---|---|---|---|
| File size | 90,727,424 B | 203,228,160 B | 206,857,216 B | 870,974,464 B |
| VERS build stamp | 2026-08-15 18:50:39 UTC | 2026-08-15 18:50:39 UTC | **2026-08-16 00:43:41 UTC** | **2026-08-16 00:43:41 UTC** |
| MLVI version | v2.0 | v2.0 | v2.0 | v2.0 |
| **sourceFpsNom / Denom** | **178993 / 1000** | **229442 / 1000** | **215430 / 1000** | **21545 / 1000** |
| **implied header fps** | **178.993** | **229.442** | **215.430** | **21.545** |
| RAWI resolution | 1920x1080 | 1920x1080 | 1920x1080 | 1920x1080 |
| VIDF count | 25 (0..24) | 56 (0..55) | 57 (0..56) | 240 (0..239) |
| videoFrameCount in header | 25 | 56 | 57 | 240 |
| Finalized? | yes (matches VIDF count) | yes | yes | yes |
| VIDF block size (all frames) | 3,629,056 B | 3,629,056 B | 3,629,056 B | 3,629,056 B |
| frame_space | 32 | 32 | 32 | 32 |
| first / last VIDF ts (µs) | 104,668 / 505,034 | 90,008 / 1,007,532 | 89,461 / 1,023,508 | 85,223 / 10,053,405 |
| median Δts | 16,671 µs | 16,683 µs | 16,684 µs | 41,711 µs |
| **fps from median Δts** | **59.983** | **59.941** | **59.936** | **23.975** |
| fps from mean Δts | 59.945 | 59.944 | 59.954 | 23.976 |
| Δts min / max | 16,606 / 16,753 | 16,497 / 16,856 | 16,574 / 16,822 | 41,507 / 41,917 |
| Duration (incl. last frame) | 0.417 s | 0.934 s | 0.951 s | 10.010 s |
| RTCI wall clock | 2026-08-15 16:12:38 | 2026-08-15 17:50:25 | 2026-08-15 18:26:07 | 2026-08-15 18:28:11 |
| Block inventory | MLVI RAWI RAWC IDNT EXPO LENS RTCI WBAL VERS NULL + VIDF | same | same | same |

Notes on the numbers:

- Every VIDF is byte-identical in size (3,629,056 = 64 B of headers + 1920x1080x14/8
  payload, padded up to a 512 B boundary). Uncompressed 14-bit, no LJ92
  (`videoClass = 1`). No audio blocks in any file.
- File size accounts exactly for `nVIDF x 3,629,056 + ~1 KB of metadata`, and the
  final block ends exactly on EOF — nothing truncated.
- All four headers are finalized: `videoFrameCount` is written and equals the actual
  VIDF count.

## Key questions

### 1. Did the fps un-shadow fix correct `sourceFps`? — NO

The two post-fix files still carry garbage: **215.430 fps** for a 59.94 p take and
**21.545 fps** for a 23.976 p take. Neither is ≈59.94, ≈59940/1000, nor ≈25.000.

The VERS block confirms the two builds are genuinely different (`18:50:39 UTC` for
1612/1750 vs `00:43:41 UTC` for 1826/1828), so the fixed build *is* what recorded
1826/1828 — it simply does not touch this value.

Root cause, from the source: the MLVI header is written by
`init_mlv_chunk_headers()`, which makes its **own** call

```c
/* mlv_lite.c:3096 */
int fps = fps_get_current_x1000();
if (fps == 0) file_hdr[i].sourceFpsNom = 1;
else          file_hdr[i].sourceFpsNom = fps;
file_hdr[i].sourceFpsDenom = 1000;
```

`init_mlv_chunk_headers()` is called at mlv_lite.c:3460; the spike-006 fix is at
mlv_lite.c:3476 — *after* the header is already written, and on a different
variable. The 3476 change is still correct and still fixes the outer `fps` for the
recording loop, but it was never on the header path.

The real defect is one level down: `fps_get_current_x1000()`
(src/fps-engio.c:912) returns `TG_FREQ_FPS / ((get_fps_register_b() & 0xFFFF) + 1)`
where `TG_FREQ_FPS = get_current_tg_freq()` = `TG_FREQ_BASE * 1000 / timerA` and
`timerA` comes from `get_fps_register_a()`. On the 6D2 these are unproven:
`platform/6D2.111/fps-engio_per_cam.c` documents that reg A cannot be read back
("No way found so far...", `get_fps_register_a_default()` returns a hardcoded
`1122 << 16`), and there is no `CONFIG_6D2` branch selecting a measured
`TG_FREQ_BASE` in src/fps-engio.c. So the header fps is a bogus timer computation,
not a shadowed variable.

Supporting hint for whoever chases the timers: relative to the true rate, the
60 p error (215.430 / 59.94 = 3.594x) is almost exactly **4x** the 24 p error
(21.545 / 23.976 = 0.899x), i.e. the returned value does not scale with the mode
the way a correct `TG_FREQ_BASE / (timerA x timerB)` would.

Practical fix options: either stamp the header from the frame-interval the recorder
already measures, or fix `fps_get_current_x1000()` for the 6D2 (measure
`TG_FREQ_BASE` and verify the reg A/B stubs at `0xe04471de` etc.).

### 2. Does the VIDF-timestamp fps agree with the header? — NO

Timestamps are healthy and are the trustworthy source: 59.94 fps for 1750/1826
(median Δ 16.68 ms) and 23.975 fps for 1828 (median Δ 41.71 ms). The headers claim
215.430 and 21.545. Headers and timestamps disagree by 3.59x and 0.90x respectively.
Downstream tools (MLV App, mlv_dump) will therefore still get the wrong frame rate
from these files unless they re-derive it from VIDF timestamps.

### 3. Is M15-1828 the 25p test? — It is the long take, but it is 24p, not 25p

240 frames, 10.010 s, median Δts 41,711 µs → **23.975 fps** (NTSC 23.976). Not 25.000.
Either the camera was in NTSC mode (24p instead of 25p) or the intended 25 p setting
did not apply. Worth re-shooting in PAL if a true 25 p sample is required.

### 4. Anomalies

- **No dropped or skipped frames** in any file: frame numbers are contiguous
  `0..N-1`, no duplicates, no gaps.
- **Timestamps strictly monotonic** in all files; zero non-monotonic pairs. Jitter is
  ±1.5 % of the interval at 60 p (16,497..16,856 µs) and ±0.5 % at 24 p — no interval
  is more than 25 % off the median, so there is no evidence of a skipped VSync.
- **No truncation**: every block fits inside the file and the last block ends exactly
  at EOF. All frames are full-size.
- **All headers finalized** — `videoFrameCount` written and correct, so the writer's
  close/rewrite path works.
- **RAWC differs on M15-1826**: it reports `sensor_res 5184x3456`, while 1612, 1750
  and 1828 all report `6240x4128` (binning/skipping identical at 3/0/1/2 in all
  four). Same RAWI output resolution and visually the same field of view, so this
  looks like a stale/incorrect `sensor_res` field rather than a real mode change —
  a second metadata field worth auditing alongside `sourceFps`.
- **RTCI has `gmtoff = 0` and an empty timezone string** in all files. Also, the
  camera clock (18:26 local) is behind the workstation build stamp
  (00:43 UTC = 18:43 local) even though the build necessarily preceded the take, so
  the camera RTC is off by roughly 20 minutes. Cosmetic, but it makes RTCI unusable
  for correlating with host-side logs.
- `EXPO` shutter value differs between 1612 (`0x5863`) and the others (`0x1f40`);
  `WBAL`, `IDNT` (Canon EOS 6D Mark II / 97D16330F8) identical throughout.

## Decoded frames (visual sanity check)

Written to `footage/previews/` (half-res 960x540, gray-world WB, gamma 2.2):

- `M15-1750_frame28.png`
- `M15-1826_frame28.png`
- `M15-1828_frame120.png`

All three are **geometrically correct**: correct 16:9 aspect, no shear, no row
offset, no tearing or stripe artifacts, correct Bayer phase (no checkerboard or
colour-fringe pattern), clean edges to all four borders. Content is a dark interior
scene with a bright window — the images are underexposed and green-cast because of
the naive gray-world white balance and fixed 2400/15000 black/white points in
`mlv_preview.py`, not because of a decode defect. 1826 and 1828 share the same
framing; 1750 was shot from a slightly different position.
