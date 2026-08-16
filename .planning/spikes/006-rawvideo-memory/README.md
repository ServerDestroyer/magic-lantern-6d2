# Spike 006 — 6D2 raw video: memory lifecycle, early stop, fps anomaly

**Status (2026-08-15 evening):** analysis complete, hardware-verified where possible;
next-test spec ready below. Inputs: body session 16:12 (movie LV, patches 0001+0004,
exFAT 256 GB UHS-I card) + four source analyses ([TIMELINE.md](TIMELINE.md),
[MEMORY_LIFECYCLE.md](MEMORY_LIFECYCLE.md), [RECORD_PATH.md](RECORD_PATH.md),
[UPSTREAM.md](UPSTREAM.md), raw notes [NOTES.md](NOTES.md)) + adversarial verification
(every load-bearing file:line re-read, arithmetic recomputed). All paths below are
under `ml/` unless noted. Line numbers refer to dev@3f24042a4 (= upstream tip; no
newer fixes exist).

## What the body test PROVED

1. **Patch 0004 livelock fix confirmed on hardware.** PROP_ICU_UILOCK writes are
   denied instantly and printed (`UILock: 00000000 -> 41000001 => 00000000 (!!!)`,
   src/gui-common.c:690); no livelock, camera responsive throughout, battery never
   pulled. The 0x41000001 writes are srm_shutter_lock (src/exmem.c:479-484) —
   meaning no UI locking actually protects SRM alloc/record on this port (benign so far).
2. **First-ever ML raw video on a 6D2.** `footage/M15-1612.MLV`
   (md5 d83961297c2a6d78255ea1129d7b8b5c), 90,727,424 bytes = 25 × 3,629,056 + 1,024
   exactly: MLV v2.0, 25 valid uncompressed 14-bit 1920x1080 VIDF frames (0..24),
   properly finalized (videoFrameCount=25), pixel-valid (frames 0/12/24 decode clean).
   File creation, writer task, flush, and finalization all work. Upstream's own
   baseline for 6D2 mlv_lite is "mostly hangs cam or reboots" (commit fd11ca5040) —
   this run exceeds it.

## Explained — not bugs

- **"Early stop (8)" is buffer-full physics, not an error.** 8 = `last_block_size`,
  frames in the last completed write group (modules/raw_video/mlv_lite/mlv_lite.c:3699,
  message gated on >3 at :3776-3778); a write error would print "stopped automagically"
  instead (:3783). `buffer_full` latched when no free slot (:2909). Math is exact:
  24 slots / 59.94 fps = 0.4004 s = the observed 0.400 s VIDF span; demand 217 MB/s
  (3,629,056 B × 59.94) vs ≤104 MB/s UHS-I bus. The flush loop (:3843-3908) +
  finish_chunk (:3921) are why the file is valid. No fix possible at 1080p60 14-bit;
  usable recording needs 24/25p, lower res, or compression (10/12-bit menu options
  are fake on 6D2 — upstream a9e01b972a).
- **Menu-open buffer free is the polling CBR's raw-video-inactive branch**
  (mlv_lite.c:2054-2066; frees shoot suite silently, then SRM which prints) — by-design
  realloc-on-state-change behavior. Which flag (`lv` vs `is_movie_mode()`) goes false
  in ML menu is the only unproven detail (one log line settles it, see next test).

## Bug 1 — MLVI fps 3x too high in 50/60p (CONFIRMED, bit-exact)

`fps_get_current_x1000()` = TG_FREQ_BASE·1000/(timerA·timerB) with fixed
TG_FREQ_BASE=66,800,000 (src/fps-engio.c:306, :912-919). The live 59.94p registers
0x1D8/0x314 → 473×789 → **exactly 178,993**, reproducing the MLVI value to the LSB.
The 6D2 timer clock is mode-dependent — ~22.32 MHz at 59.94p, ~44.46 MHz at 50p, per
the port's own measurement table (fps-engio.c:316-322, "Variable, like 200D?"); same
unsolved problem as 200D (upstream 742587f10f). VIDF timestamps use get_us_clock()
(modules/raw_video/mlv_rec/mlv.c:235-244) and independently prove the sensor ran
exactly 59.94 fps (0.400 s = 24 × 16.67 ms).

- Impact: MLVI header + all fps-based time estimates wrong in 50/60p; slot math
  unaffected (setup_buffers :1540-1654 has no fps term).
- ~~"Wrong fps makes the writer anti-overflow throttle 3x too small"~~ — REFUTED:
  the throttle's `fps` is shadowed to 1 by a separate upstream bug (`int fps` redeclared
  at mlv_lite.c:3466 inside the card_index==0 block, outer declaration :3358, both from
  upstream f0dc17db9b), so the throttle is dead code either way. Un-shadowing is a
  one-word upstream-reportable fix.
- ~~"fps register misread"~~ — refuted: register reads are correct ROM calls
  (platform/6D2.111/stubs.S:278-279); only the clock constant is wrong.
- Today's clip is salvageable: patch MLVI sourceFpsNom/Denom to 59940/1000
  (VIDF timestamps are already correct).

## Bug 2 — post-record dead state / "No memory suites." spam (SOURCE-FORCED)

Recording cleanup unconditionally frees both suites (mlv_lite.c:3933). The only
realloc trigger is a `current_state` fingerprint flip (:2031-2050) — which finishing
a recording never produces. The intended re-arm, PauseLiveView/ResumeLiveView
(:3808-3811 via src/powersave.c:50), writes PROP_LV_ACTION — **silently dropped on
this build**: D678 prop_request_change drops anything not in the whitelist
(src/property.c:388-401), the 6D2 whitelist holds only 4 properties
(platform/6D2.111/property_whitelist.h:35-41), and `lv` is set only by the
PROP_LV_ACTION handler (src/propvalues.c:238-241). So the 250 ms poll (:1013-1018)
hits setup_buffers with NULL suites forever (print at :1566-1569), and a **second REC
without a menu/mode flip starts with 0 slots** (return unchecked at :3429) → instant
stop, header-only MLV. Prediction source-forced but unexercised on hardware.
Workaround meanwhile: open/close ML menu between takes.

## Bug 3 — 92 MB shoot-pool shrink between cycles (135→43 MB) — OPEN, two suspects

Not an ML leak: all free_buffers call sites verified balanced (:1517, :2061, :3401,
:3933); the fullres/"28MB after full-res buffer" lines are pointer carves inside the
suites, allocating nothing (:1354-1392, :1422-1428). Both observed sizes are exact
outputs of the shoot_malloc autodetect staircase — max = last_ok + 4 MB − 1 MB, so
every result ≡ 3 mod 4 (135=132+3, 43=40+3; src/exmem.c:206-239) — probed with a
100 ms semaphore timeout (exmem.c:177) that cannot distinguish a slow RscMgr response
from out-of-memory. Surviving hypotheses:
(a) Canon consumed ~92 MB (raw LV stream torn down/rebuilt around menu cycles; SRM
    buffer address moved 0x4c3f0070→0x65a4c070, proving Canon's layout changed);
(b) one >100 ms probe response silently truncated the autodetect.
Struck: ~~mlv_lite leak~~; ~~FEATURE_SHOW_* debug features~~ (display-only, and cycle 1
already measured 135 MB with them running); ~~raw.c 45 MB RAW_LV_BUFFER path~~
(compiled out — 6D2 has no CONFIG_EDMAC_RAW_SLURP, src/raw.c:84-124). Unreported upstream.

## NEXT TEST — instrumented build for the next card session

Proposed **patch 0006** (diagnostic; do NOT apply to ml/ yet — build tree is owned by
another session). Four edits:

```diff
--- a/modules/raw_video/mlv_lite/mlv_lite.c   (line 3466, un-shadow fps — real upstream bug)
-        int fps = fps_get_current_x1000();
+        fps = fps_get_current_x1000();
--- a/modules/raw_video/mlv_lite/mlv_lite.c   (line 2054, in the free branch, before free_buffers)
+        printf("raw inactive: lv=%d movie=%d gui=%d\n", lv, is_movie_mode(), gui_state);
--- a/src/exmem.c   (in shoot_malloc_autodetect loop, ~line 220; t0/t1 = get_ms_clock() around the probe)
+        printf("[probe] %d MB: %s (%d ms)\n", tested_size>>20, ok ? "ok" : "TIMEOUT", t1 - t0);
--- a/modules/raw_video/mlv_lite/mlv_lite.c   (raw_rec_polling_cbr, re-arm fix — optional, see step 3)
+        /* re-arm: both suites NULL while raw video active and idle -> realloc */
+        if (!shoot_mem_suite && !srm_mem_suite && raw_video_active && RAW_IS_IDLE) { buffers_dirty = 1; }
```

On-camera protocol (console photos into `Pics of debuging/`; strict order):

1. **Dead-state confirmation (BEFORE the re-arm fix, or with it #if 0'd):** record raw
   in 1080p60, let it early-stop, then immediately press REC again without touching
   menus. Expect instant "stopped automagically" + a header-only MLV, and "No memory
   suites." persisting until a menu open/close. → Confirms Bug 2 end-to-end; the
   re-arm fix is then justified. (Also watch for "EDMAC timeout." NotifyBox — its
   absence excludes the alternate buffer_full setter at mlv_lite.c:2864.)
2. **Shrink discriminator:** LV→ML menu→LV five times; photograph `Shoot memory: X`
   each cycle plus the new `[probe]` lines. Monotonic decay with all probes fast →
   Canon-side retention (hypothesis a) → next step is Canon raw-LV teardown analysis.
   Any `TIMEOUT` probe or recovery to ~135 → truncation (hypothesis b) → fix =
   retry-once-on-timeout (or larger timeout) at exmem.c:177.
3. **fps model:** switch Canon to 1080/25p, record raw. Expect MLVI ≈ 25000/1000
   (TG_FREQ_BASE is valid ≤30p) and a ~5x longer take (~87 MB/s demand). → Confirms
   the mode-dependent-clock model; the fix is a per-mode TG_FREQ table for 6D2
   (66.8 MHz ≤30p / 44.46 MHz 50p / 22.32 MHz 59.94p per fps-engio.c:316-322).
4. **Menu-free flag:** read the new `raw inactive:` line when opening ML menu —
   settles lv vs is_movie_mode.

Each outcome maps to exactly one fix; nothing in this session requires pulling the
battery. Spell capture (Session 2 of BODY_TEST_PLAN.md) stays first priority — this
runs in the session after it.

## NEW SYMPTOM (2026-08-15 ~19:07, rev-1 0006 build): stop-path hang at "Flushing buffers... 1 frames left"

Photo `Pics of debuging/20260815_190714.jpg`: after stopping a raw take, the
overlay froze at `Flushing buffers... 1 frames left` with a solid column of
`No memory suites.` spam beneath it and a UILock denial line — the writer is
draining its last frame while the memory suites are already torn down. UI
appeared hung (user report). BUT both takes from that session
(`footage/M15-1901.MLV` 2.0 GB/558 frames, `M15-1906.MLV` 1.35 GB/373 frames)
are FINALIZED (videoFrameCount set), so the file close does complete — the
hang is in the post-stop UI/cleanup path, same neighborhood as Bug 2's dead
state, now seen at stop time rather than re-REC time. Second photo
(`20260815_190630.jpg`) shows the allocation printout garbled/interleaved with
LV — console redraw corruption during buffer setup, cosmetic but note it.
Session ran the REV 1 build (card sync to rev 2 hadn't happened yet), so fps
headers are still garbage (21567/22481) and probe/dead-state instrumentation
was the old kind. Retest under Session 4b (rev 2) still pending.

## FPS HEADER FIX HARDWARE-VALIDATED (2026-08-15 ~19:25, rev-2 build)

Session ran rev 2 (rev-3 sync hadn't happened). Three takes, headers now stamp
measured fps exactly: `footage/M15-1921.MLV` 169f @ 29.970, `M15-1924.MLV`
393f @ **25.000** (the PAL test — done correctly), `M15-1925.MLV` 173f @
29.970. Bug 1 (garbage sourceFps) is FIXED and validated on hardware.
Tests 1/2/4 console data lost (display-only build, no photos) — rerun on
rev 3, which self-records to ML/LOGS/RAWDIAG.LOG. Card now carries rev 3
(autoexec 8dd0cd24).

## RAWDIAG SESSION 1 (2026-08-15 ~19:30, rev 3): DEAD STATE CONFIRMED, RE-ARM FIX ENABLED (rev 4)

First photo-free session — `tools/RAWDIAG-session1.txt` captured everything:
- **Bug 2 confirmed end-to-end with state values.** After auto-stop:
  `No memory suites. lv=1 movie=1 gui=0 rawact=1 rec=0 suites=0/0` at 1 Hz for
  7 s, then `rec=1 suites=0/0` — REC pressed in dead state **starts recording
  with zero slots and hard-freezes** (battery pull; screen stayed lit through
  power-off). Worse than the predicted instant auto-stop. First take of the
  pair finalized fine (`footage/M15-1934.MLV`, 57f @ 59.943 measured).
- **Probe stop-condition answered:** all 4 autodetect runs end at 136 MB via
  allocator TIMEOUT (98–100 ms ≈ the 100 ms `take_semaphore` cap in
  `shoot_malloc_suite_int`), max stable at 135 MB — no shrink, but autodetect
  always terminates by timeout, never by clean failure.
- **Menu-cycle mechanism:** every ML menu open drops LV → free branch fires
  (`raw inactive: lv=0 movie=1 gui=1`) → realloc + full re-probe on close.
  This is why the menu-open workaround cures the dead state.
- **Action taken:** re-arm fix un-#if-0'd (mlv_lite.c ~2117) = **rev 4**, built,
  patch 0006 regenerated, card synced (mlv_lite.mo `4bed61bb`). Retest: repeat
  test 1 — expect the second REC to just work (suites realloc within a polling
  tick). Remaining hazard: REC while suites are momentarily 0/0 still hangs —
  a refuse-to-start guard is the defensive fix if re-arm proves insufficient.
