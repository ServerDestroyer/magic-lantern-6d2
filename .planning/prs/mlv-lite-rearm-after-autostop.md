# PR — mlv_lite: reallocate buffers after a recording stops on its own

Branch: `mlv-lite-rearm-after-autostop` (fork `ServerDestroyer/magiclantern_simplified`)
Base: `dev` @ `3f24042a4`
Commit: `6ef3813c0`

## Title

```
mlv_lite: reallocate buffers after a recording stops on its own
```

## PR body (ready to paste)

```markdown
### What

One guard in `raw_rec_polling_cbr()`: if both memory suites are gone while
raw video is active and idle, ask for a reallocation.

### Why

Recording cleanup frees both suites unconditionally. The only thing that sets
`realloc` in the polling CBR is a change in the state fingerprint built from
LiveView, movie mode, resolution and friends — and finishing a recording
changes none of those. Raw video is therefore left enabled with no buffers at
all.

The intended re-arm exists: the record task calls PauseLiveView /
ResumeLiveView on the way out, which writes `PROP_LV_ACTION` and would flip
the fingerprint. On DIGIC 6/7/8 that write is dropped when the property is
not in the port's whitelist, and `prop_request_change` gives no indication,
so the re-arm silently never happens.

In that state the next REC press starts a recording with zero slots and hangs
the camera. Opening and closing the ML menu is an accidental cure: losing
LiveView takes the free branch just above, and closing the menu triggers a
full realloc and re-probe.

Setting `realloc` directly when both suites are missing closes the gap
regardless of whether the property write landed. The guards on the
reallocation itself (`RAW_IS_IDLE || RAW_IS_PREPARING`, `gui_state ==
GUISTATE_IDLE`, the semaphore and UI lock) are untouched — this only schedules
work the polling CBR was already able and allowed to do.

### How tested

- Builds clean for `6D2.111` with `-Werror`
  (gcc-arm-embedded 15.2.1, `ML_MODULES="raw_video/mlv_lite"`), no new
  warnings.
- **Validated on a real 6D2 (2026-08-15), two logged sessions on the same
  build lineage, before and after.**

  *Before* (diagnostic build without this guard): after a take auto-stopped on
  buffer exhaustion, the polling CBR logged
  `No memory suites. lv=1 movie=1 gui=0 rawact=1 rec=0 suites=0/0` once a
  second for seven seconds — raw video active, both suites gone, exactly the
  dead state described above. Pressing REC then logged `rec=1 suites=0/0`:
  recording started with zero slots and froze the camera hard enough to
  require a battery pull. The take before it (`M15-1934.MLV`, 57 frames)
  finalized normally, so the failure is specific to the post-stop state.

  *After* (same build plus this guard): zero dead-state lines logged. The
  re-arm fired ~1 s after the take auto-stopped (t = 12.1 s), the camera
  stayed responsive, powered off cleanly at t = 17 s, and
  `M15-1945.MLV` (57 frames) recorded and finalized normally.

### Risk

- The condition is narrow: it needs *both* suites NULL, raw video active, and
  the recorder idle. During recording or while any buffer is still held, it
  cannot fire.
- Worst case if it fires spuriously is one extra reallocation pass, which is
  the same work the state-fingerprint path already performs on every menu
  close.
- Not 6D2-specific. The free-on-stop and the fingerprint-only realloc trigger
  are body-agnostic; the dropped `PROP_LV_ACTION` write makes it certain on
  DIGIC 6/7/8, but any body where the re-arm write does not take effect ends
  up in the same dead state.
- Known remaining hazard, out of scope here: pressing REC during the brief
  window while the suites are legitimately 0/0 still starts a zero-slot
  recording. A refuse-to-start guard in the record path is the defensive
  follow-up if this proves insufficient; on the validated build the re-arm
  closed the window fast enough that it was never observed.
```
