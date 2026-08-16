# PR — mlv_lite: stamp the measured frame rate into the MLVI header

Branch: `mlv-lite-measured-fps-header` (fork `ServerDestroyer/magiclantern_simplified`)
Base: `dev` @ `3f24042a4`
Commit: `395bf3139`

## Title

```
mlv_lite: stamp the measured frame rate into the MLVI header
```

## PR body (ready to paste)

```markdown
### What

Two changes in `modules/raw_video/mlv_lite/mlv_lite.c`:

1. `finish_chunk()` now stamps `sourceFpsNom`/`sourceFpsDenom` from the frame
   rate actually measured over the VIDF timestamps, overriding the value
   written when the MLVI header was created.
2. `raw_video_rec_task()` no longer shadows its own `fps` local.

### Why

**Wrong header fps.** The fps stamped at record start comes from
`fps_get_current_x1000()`, i.e. `TG_FREQ_BASE / (timerA * timerB)`. That is
only as good as the port's `TG_FREQ_BASE`. On bodies where it was never
measured — or where the timer clock is mode-dependent — the header is wrong,
and every tool that trusts it plays the MLV back at the wrong speed.

On a 6D2 the error is large and reproducible bit-exactly: 59.94p registers
read 0x1D8/0x314 → 473 × 789, which with the port's placeholder
`TG_FREQ_BASE = 66,800,000` yields exactly **178,993** — the value found in
the file. The real timer clock there is mode-dependent (~22.32 MHz at 59.94p,
~44.46 MHz at 50p per the port's own measurement notes), the same unsolved
problem as the 200D. Fixing `TG_FREQ_BASE` per body per mode is a separate,
much larger job.

The VIDF timestamps mlv_lite already writes per frame come from
`get_us_clock()`, which is independent of the FPS timer registers, so the
frame interval they describe is a direct measurement of what the sensor did.
Deriving the header fps from that span sidesteps the register question
entirely. This is not 6D2-specific: **any port whose `TG_FREQ_BASE` or timer
A was never measured gets a correct MLVI header out of this**, without
needing anyone to measure the timer first.

The estimate requires at least two frames and is sanity-bounded
(`0 < fps_x1000 < 1000000`); when it cannot be computed the header keeps its
original value, so bodies with a correct `TG_FREQ_BASE` see no change.

**Shadowed `fps`.** `raw_video_rec_task()` declares `int fps = 1;` at the top
and then, inside the `card_index == 0` block, redeclares
`int fps = fps_get_current_x1000();`. The outer variable — the one the
writer's anti-overflow throttle reads to compute `overflow_time` — therefore
stays at 1 for the whole recording, making that throttle compute against a
one-second frame interval. Both declarations came in together, so this has
been dead since the throttle was written. The fix is to assign instead of
redeclare.

### How tested

- Builds clean for `6D2.111` with `-Werror`
  (gcc-arm-embedded 15.2.1, `ML_MODULES="raw_video/mlv_lite"`), no new
  warnings.
- **Validated on a real 6D2 (2026-08-15, movie LiveView raw-video session).**
  Three takes recorded and finalized with the measured stamp in place:
  - `M15-1921.MLV` — 169 frames @ **29.970**
  - `M15-1924.MLV` — 393 frames @ **25.000** (PAL)
  - `M15-1925.MLV` — 173 frames @ **29.970**

  A later 59.94p take (`M15-1934.MLV`, 57 frames) stamped **59.943**, against
  the 178.993 the unpatched build wrote for the same mode. Independent
  cross-check on the unpatched capture: 24 slots spanning 0.400 s of VIDF
  timestamps = 24 × 16.67 ms = 59.94 fps, confirming the sensor rate and that
  the register-derived value was the thing in error.

### Risk

- The stamp only ever replaces a value that was already a guess, and only
  when at least two frames were timestamped and the result is in range.
  Otherwise the previous behaviour is kept exactly.
- The three tracking variables are written by the vsync hook and read by
  RawRecTask without a lock. A torn read can only skew the fps estimate
  slightly; it cannot produce an out-of-range value that passes the guard,
  and taking a lock in the vsync hook would be the greater risk.
- The un-shadowing changes behaviour only in that `overflow_time` is now
  computed from the real frame rate rather than from 1 fps. That is the
  throttle working as originally intended; if it turns out to misbehave now
  that it is live, that is a pre-existing bug this change makes visible
  rather than one it introduces.
```
