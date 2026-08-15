# Spike 006 — input notes (do not delete; synthesis should fold these in)

- Card config baseline before the 16:12 test (from the body-test session):
  `mlv_lite.cfg` had `raw.output_format=0` = 14-bit uncompressed. Consistent
  with the observed 3,629,056-byte VIDF frames (1920x1080x14/8 + headers).
- Frames 0/12/24 decoded to PNG with `tools/mlv_preview.py` (pure-stdlib
  implementation of raw.h:72 pixblock layout): geometrically correct image,
  no stripe/bayer artifacts → capture is pixel-valid end to end, not just
  structurally valid. Previews in `footage/` (gitignored).
- Camera clock is ~7 h behind the PC — never filter card files by mtime.
- The MLV itself: `footage/M15-1612.MLV`, md5 `d83961297c2a6d78255ea1129d7b8b5c`,
  MLV v2.0, 25 VIDF (0..24), finalized header videoFrameCount=25, clean end.
  MLVI sourceFps 178993/1000 (garbage); VIDF timestamp span 0.400 s / 25 frames.
