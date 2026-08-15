# Record Path Analysis: "Early stop (8)", "No memory suites.", fps 178993

Task 3 of spike 006. Source: `ml/modules/raw_video/mlv_lite/mlv_lite.c` (note: path is
`modules/raw_video/mlv_lite/`, not `modules/mlv_lite/`), `ml/src/fps-engio.c`,
`ml/platform/6D2.111/fps-engio_per_cam.{h,c}`, `ml/modules/raw_video/mlv_rec/mlv.c`.
All line numbers from the working tree (dev + patches 0001-0004; none of the patches touch these files).

**Verdict in one paragraph:** All three observations are explained, and none of them is a
new 6D2 port bug in the record path itself. "Early stop (8)" is the ordinary
buffers-full/slow-card stop — the "8" is not a reason code, it is the size of the last
completed write burst — and the numbers match the physics exactly (24 slots / 59.94 fps =
0.4004 s = the observed 0.400 s VIDF span). The endless "No memory suites." is a
post-recording polling loop: recording cleanup frees both memory suites unconditionally,
and the only code that reallocates them never gets triggered because its re-arm condition
(an lv/video-mode state flip) doesn't fire — printing every 250 ms until the user pokes
the camera. The fps 178993 is `fps_get_current_x1000()` computing with `TG_FREQ_BASE =
66.8 MHz`, which on 6D2 is only correct in 24/25/30p; in 1080/60p the timer clock is
~22.37 MHz, so the result is 2.99x too high — the exact register values reproduce 178993
bit-for-bit. Along the way, one real code bug was found (a shadowed `fps` variable that
disables the writer's overflow throttle), but it did not cause any of the observed
symptoms.

---

## (a) "Early stop (8)" — what the 8 means, and the write-speed math

### There is no reason-code enum

The number in "Early stop (%d)" is `last_block_size` — the number of writing-queue
entries in the **last successfully completed write group** — not an error code:

- `mlv_lite.c:3354` — `int last_block_size = 0; /* for detecting early stops */`
- `mlv_lite.c:3699` — after each successful `write_frames()`:
  `last_block_size = MOD(after_last_grouped - w_head, COUNT(writing_queue));`
- `mlv_lite.c:3766-3788` — the stop message:

```c
abort_and_check_early_stop:
    ...
    if (last_block_size > 3)
        bmp_printf(..., "Early stop (%d). Should have recorded a few more frames.", last_block_size);
    else
        bmp_printf(..., "Movie recording stopped automagically");
```

So "Early stop (8)" = "recording stopped on `buffer_full`, and the last completed write
burst contained 8 queue entries". `beep_times(last_block_size)` at 3779 is why it beeps
8 times.

### How the stop is reached — this IS the buffers-full/slow-card path

The only ways into `abort_and_check_early_stop` with `last_block_size != 0`:

1. `mlv_lite.c:3502-3505` — top of the writer loop: `if (buffer_full) goto abort_and_check_early_stop;`
2. (`abort:` at 3763 zeroes `last_block_size` first — that's the write-error path, which
   prints "stopped automagically" instead, plus "Write error." from `write_frames`,
   `mlv_lite.c:3257-3261`. Not our case: no write errors were printed and the file is clean.)

`buffer_full` is set in four places:

| Line | Condition | Our case? |
|------|-----------|-----------|
| 2909 | `choose_next_capture_slot() < 0` and not pre-recording — **no free slot, card too slow** | **Yes** |
| 2864 | EDMAC still active when next frame arrives ("EDMAC timeout" NotifyBox) | No (no NotifyBox seen) |
| 2794, 2801 | compressed frame larger than slot (OUTPUT_COMPRESSION only) | No (uncompressed) |

`buffer_full` latches: `raw_rec_vsync_cbr` returns immediately once it is set
(`mlv_lite.c:2950`), so mlv_lite stops recording at the **first** dropped frame by
design. The writer notices the flag at the top of its loop — possibly *after* completing
one more large write — which is why a big `last_block_size` at stop time is normal on a
badly write-starved card, despite the message implying an anomaly. The
"should have recorded a few more frames" heuristic was written for setups where write
speed nearly sustains the data rate; at a 3x deficit it always fires with whatever the
last burst size was.

### The quantitative check — observed stop point vs physics

Constants (all derived from source, matching the file on card):

- `max_frame_size` = `(64 + 1920*1080*14/8 + 4 + 511) & ~511` = **3,629,056 B** = 3.461 MiB
  (`mlv_lite.c:716,723`) — exactly the observed per-VIDF size, so uncompressed frames
  fill their slot exactly.
- Real capture rate (see section c): **59.94 fps** (1080/60p).
- Required sustained write: 3,629,056 x 59.94 = **217.5 MB/s** (207.5 MiB/s).
- Card side: UHS-I bus tops out at 104 MB/s; realistic large-block exFAT writes through
  FIO on this class of body: 40-70 MB/s. **Deficit >= 3x. Sustained recording is
  physically impossible in this mode; only the buffer pool length is negotiable.**
- Buffer pool this cycle: 24 slots x 3.461 MiB = **83.1 MiB** (cycle 2: 11 shoot + 13 SRM
  slots, prints at `mlv_lite.c:1617,1630`).

Fill-time model: time to exhaust N slots = `N / (59.94 - W/3.461)` seconds, W = drain in MiB/s.

- W = 0 (writer still inside its first big `FIO_WriteFile`): t = 24/59.94 = **0.4004 s**
- W = 40 MB/s: t = 0.50 s (~30 frames)
- W = 70 MB/s: t = 0.60 s (~36 frames)

**Observed: 25 VIDF spanning exactly 0.400 s.** That is the W~=0 case to four significant
figures: the pool filled at essentially full sensor rate while the writer's first large
write (plus exFAT first-write cluster allocation on a fresh 256 GB card) was still in
flight. 25 frames in 24 slots means exactly ~1 slot had been freed during the window
(one small early write completed — 3.46 MiB in 0.4 s ~= 9 MB/s effective, dominated by
first-write latency), then a group of 8 was mid-write when the vsync found no free slot
at t~=0.4 s. Sequence:

1. t=0: recording starts, slots fill at 59.94/s.
2. Writer completes a small first group (frees ~1 slot), starts a larger group of 8
   (28 MiB — 0.4-0.7 s of card time on its own).
3. t~=0.400 s: `choose_next_capture_slot()` returns -1 -> `buffer_full = 1` (2909). Capture over.
4. Writer finishes the 8-entry group, loops, sees `buffer_full` -> "Early stop (8)".
5. Post-stop flush (`mlv_lite.c:3843-3908`) writes the ~16 still-queued frames
   ("Flushing buffers... N frames left" counts down; the observed line was the last one),
   `finish_chunk()` at 3922 patches `videoFrameCount=25` -> the valid, finalized file.

**Conclusion (a): quantitatively consistent with buffers-full physics; no record-path bug.
The file being perfect is expected — this stop path loses zero captured frames.**

### Side finding: the writer's overflow throttle is dead code (shadowed `fps`)

`raw_video_rec_task` declares `int fps = 1;` at `mlv_lite.c:3358`. The value actually
read from the camera, `int fps = fps_get_current_x1000();` at `mlv_lite.c:3466`, is a
**new declaration inside the `if (card_index == 0)` block** — it shadows the outer
variable and dies at 3480. The group-size throttle at `mlv_lite.c:3625-3641` therefore
computes `overflow_time = free_slots * 1000 * 10 / fps` with `fps == 1`, i.e. ~10,000x
too large, and the subsequent `frame_limit` multiplication overflows int for typical
write speeds; the `frame_limit >= 0 && frame_limit < num_frames` guard then usually
skips the clamp, so the "write fewer frames when about to overflow" optimization never
runs (and when the overflow lands positive, it could clamp nonsensically). Both lines
came from commit `f0dc17db9b` ("mlv_lite: adapt ilia's card spanning code") — an
upstream magiclantern_simplified bug, not a 6D2 patch artifact. It did **not** affect
this recording (`measured_write_speeds[0]` is only set by the 1 Hz status poll at
`mlv_lite.c:1931-1944`, and the recording lasted 0.4 s, so the throttle was inert
regardless), but it should be fixed: drop the `int` at 3466.

---

## (b) The endless "No memory suites."

### Who prints it and when

Single occurrence in the tree: `setup_buffers()` at `mlv_lite.c:1566-1570` — printed and
`return 0` when **both** `shoot_mem_suite` and `srm_mem_suite` are NULL. It performs no
allocation and has no other side effect (slot counts already zeroed at 1563-1564), so
each print is O(1) and harmless per se.

Call chain that repeats it:

1. Recording cleanup **unconditionally frees both suites**: `mlv_lite.c:3920-3935`
   (`cleanup:` -> `free_buffers()` at 3933, which does `shoot_free_suite`/`srm_free_suite`
   and NULLs both, 1482-1510). This is upstream behavior (predates the card-spanning
   commit), not a patch artifact.
2. `raw_rec_polling_cbr` (registered as `CBR_SHOOT_TASK`, `mlv_lite.c:4611`) runs
   continuously. Once `raw_recording_state` returns to `RAW_IDLE` (3960), it calls
   `refresh_raw_settings(0)` every poll (`mlv_lite.c:2080-2083`).
3. `refresh_raw_settings` gates on `should_run_polling_action(250, &aux)`
   (`mlv_lite.c:1013`) -> calls `setup_buffers()` at 1018 -> **"No memory suites." at 4 Hz**.
   (With ML menu open the polling path is skipped, but the menu updater calls the same
   function: `raw_main_update` -> `refresh_raw_settings(0)`, `mlv_lite.c:1050` — same 4 Hz.)

"A dozen+ lines, still printing seconds later" = 4 Hz x a few seconds. It is **not** a
stuck writer task — raw_rec_task1 exited cleanly after finalizing the file; this is the
idle-time polling path.

### Why it never stops by itself

The **only** call to `realloc_buffers()` (the function that re-acquires the suites,
`mlv_lite.c:1513-1528`) is in the polling CBR at `mlv_lite.c:2069-2077`, gated on a
`realloc` flag that is set **only when `current_state` changes** (2033-2050):
`raw_video_active` (= `raw_video_enabled && lv && is_movie_mode()`), `RECORDING_H264`,
`pic_quality`, `video_mode_resolution/fps/crop`. Finishing a raw recording changes none
of these, so after cleanup: suites NULL, `realloc == 0`, and the 4 Hz failure print runs
forever.

Upstream presumably escapes this because cleanup calls `PauseLiveView()` /
`ResumeLiveView()` (`mlv_lite.c:3808-3811, 3958`), which flips `lv` via
`prop_request_change_wait(PROP_LV_ACTION, ...)` (`src/powersave.c:38-57`) — the lv flip
toggles `raw_video_active`, sets `realloc`, and the next poll reallocates. On the 6D2
that re-arm did not fire. Two candidate explanations, both testable:

1. **PROP_LV_ACTION write denied** on this port, same as the observed PROP_ICU_UILOCK
   denials (patch 0004 prints them) -> `lv` never flips -> no state change. Most likely,
   given UILock denials were observed at stop time (`gui_uilock(UILOCK_EVERYTHING)` at
   3794/3814 goes through the same denied-prop path).
2. `gui_state != GUISTATE_IDLE` blocking the realloc branch (2069) — but this would only
   delay it, and the flag would still need setting first.

### Harmful or cosmetic?

- The print storm itself: **cosmetic** (console spam, 4 Hz, no allocation attempts, no
  CPU cost worth naming).
- The underlying state: **functionally harmful for the next recording.** With both
  suites NULL, pressing record again runs `setup_buffers()` from `raw_video_rec_task`
  (3429), which fails, and nothing checks the return value (the SJE comment at
  1537-1538 says exactly this). The task proceeds to create a file, write headers, then
  the first `process_frame` finds zero slots -> instant `buffer_full` -> a stopped
  recording with a header-only MLV. Recovery today: anything that flips
  `current_state` with gui idle — exit/re-enter LV, open/close Canon menu, change video
  mode, toggle raw video off/on. (This is exactly what the observed cycle 1 -> cycle 2
  did: menu visit freed + realloc'd the suites.)
- It also explains why re-recording "just worked" for upstream cameras: their lv flip
  during cleanup re-arms the realloc.

**Answer to the task's question: it keeps firing until the polling CBR sees a state
change (LV/mode flip), yes — there is no timeout and no self-recovery.**

---

## (c) fps: where 178993/1000 comes from — exact reproduction

### Source of MLVI sourceFpsNom

`init_mlv_chunk_headers()`, `mlv_lite.c:3086-3091`:

```c
int fps = fps_get_current_x1000();
file_hdr[i].sourceFpsNom  = fps;      // (1 if fps==0)
file_hdr[i].sourceFpsDenom = 1000;
```

`fps_get_current_x1000()` (`src/fps-engio.c:912-919`):

```c
int fps_timer = (get_fps_register_b() & 0xFFFF) + 1;
int fps_x1000 = TIMER_TO_FPS_x1000(fps_timer);   // = calc_tg_freq(timerA) / timerB
```

with `calc_tg_freq(timerA) = TG_FREQ_BASE*1000/timerA` (fps-engio.c:424-428, 451-454),
`timerA = (get_fps_register_a() & 0xFFFF) + 1` (fps-engio.c:438-444), and for
`CONFIG_6D2`: `TG_FREQ_BASE 66800000` (**fps-engio.c:305-306**).

The registers are real, live reads on 6D2 — not guesses: `FPS_REGISTER_A/B =
0xd0006008/0xd0006014` and ROM accessors `_get_fps_register_a/b` at
`0xe044726a/0xe04471de` (`platform/6D2.111/fps-engio_per_cam.h`, `platform/6D2.111/stubs.S:278-279`).

### The arithmetic reproduces 178993 exactly

The 6D2 comment block in fps-engio.c (lines 308-322) logs the real timer values per mode:

| Canon mode | timer_a, timer_b (raw reg) | implied timer clock |
|-----------|---------------------------|---------------------|
| 23.98p | 0x588, 0x7b0 | 66.88 MHz |
| 25p    | 0x588, 0x760 | 66.83 MHz |
| 29.97p | 0x588, 0x626 | 66.86 MHz |
| 50p    | 0x3ae, 0x3b0 | 44.46 MHz |
| **59.94p** | **0x1d8, 0x314** | **22.32 MHz** |

Plugging the 59.94p registers into the code's fixed-66.8MHz model:
timerA = 0x1d8+1 = 473, timerB = 0x314+1 = 789;
`calc_tg_freq(473)` = (66800000/473)*1000 + (66800000%473)*1000/473 = 141,226,215;
141,226,215 / 789 = **178,993** with remainder 738. **Bit-exact match with the MLVI
value.** So the camera was in Canon 1080/60p, the registers were read correctly, and the
sole error is `TG_FREQ_BASE`: the 6D2's timer clock is mode-dependent (as the port
author already noted: "Variable, like 200D? Different base clock though."), and 66.8 MHz
is only right for the 24/25/30p family. In 60p the constant is 66.8/22.37 = 2.99x too
high: 178,993 / 2.99 = 59,940 -> the true 59.94 fps.

### Why the VIDF timestamps are right anyway

VIDF timestamps come from a completely different source: `mlv_set_timestamp()` uses
`get_us_clock()` (`modules/raw_video/mlv_rec/mlv.c:235-243`), stamped per frame at
`mlv_lite.c:2915`. Real wall-clock microseconds, no timer constants involved. The
observed 0.400 s span over 25 frames = **24 intervals** of 16.68 ms = **59.95 fps** —
i.e. the timestamps independently confirm Canon 1080/59.94p (the prompt's "~62.5 fps"
divided by 25 instead of 24). MLVI header wrong, VIDF timestamps trustworthy —
mlv_App/post tools that honor VIDF timestamps will play this file correctly; tools that
trust MLVI sourceFpsNom will play it 3x fast.

### Does the wrong fps distort the early-stop/slot/speed math?

**No — nothing in the stop decision consumes fps.** `buffer_full` is pure slot
availability; slot count is pure memory-suite geometry. The only fps consumer inside the
recording loop is the group-size throttle at `mlv_lite.c:3630` — which, per the shadowing
bug in (a), reads `fps == 1`, so not even the wrong 179k value reaches it. The wrong fps
does affect (all cosmetic/metadata): the menu's required-write-speed and recording-time
predictions (`mlv_lite.c:835ff, 1808ff`), pre-record/time-limit frame conversions
(`mlv_lite.c:1259, 1284`), on-screen elapsed time (`mlv_lite.c:2672ff`, will show ~1/3 of
real elapsed), and the MLVI header. In Canon 24/25/30p modes all of these would be
correct on the current build.

---

## (d) Would 48 slots have bought ~2x the frames? Yes — but never sustained recording

Pool scaling is linear in the starved regime. Frames before buffer_full ~=
`N / (1 - W/(3.461*59.94))` where the denominator barely differs from 1 at any real SD
speed, so frames ~= N x (1 + W_ratio):

| Pool | W ~= 0 (this take) | W = 40 MB/s | W = 70 MB/s |
|------|------------------|-------------|-------------|
| 24 slots (43 MB shoot + 45 MB SRM, cycle 2) | 25 frames / 0.40 s | ~30 / 0.50 s | ~36 / 0.60 s |
| 48 slots (135 MB shoot + 45 MB SRM, cycle 1) | ~49 frames / 0.80 s | ~60 / 1.0 s | ~72 / 1.2 s |

So yes: the 92 MB of shoot memory lost between cycle 1 and cycle 2 cost almost exactly
half the recording (48 -> 24 slots, 3.461 MiB per slot; cycle-1 math: (135-4.4)/3.461 ~=
35 shoot slots + 13 SRM = 48; cycle-2: (43-4.4)/3.461 ~= 11 + 13 = 24 — both match the
console). Reclaiming the shoot memory doubles the take length but the ceiling stays ~1
second. The data rate (217 MB/s) is ~3x anything the SD interface can do; usable raw
recording on this body needs the data rate cut, not the buffer grown: Canon 1080/24-25p
(87 MB/s — still above sustainable, but buffer lasts 5-10x longer), reduced vertical
resolution/aspect, 10/12-bit (`setup_bit_depth`), or lossless compression once the lj92
path is validated on D678. The debug features (SHOW_TASKS etc.) are not implicated by
anything in this code path; the shoot-suite shrink is Canon-side allocation state between
suite acquisitions (cycle 1 acquired at LV entry, cycle 2 re-acquired after menu
round-trip) — quantifying that belongs to the memory task, not the record path.

---

## Actionable fixes, smallest first

1. **Un-shadow `fps`** — delete `int` at `mlv_lite.c:3466` so the outer `fps` (3358)
   gets the real value; restores the overflow throttle and removes an int-overflow.
   One-word diff. (Upstream bug — worth reporting to magiclantern_simplified.)
2. **MLVI fps on 6D2** — until mode-dependent TG_FREQ is understood, derive
   sourceFpsNom from Canon's `video_mode_fps` property (x1000, with 1000/1001 for NTSC
   modes) when on D678, or add a per-mode TG_FREQ table for 6D2 from the existing
   comment (66.8 MHz for <=30p, 44.5 MHz for 50p, 22.37 MHz for 59.94p). The register
   reads themselves are correct.
3. **"No memory suites." storm / broken re-record** — in `raw_rec_polling_cbr`, treat
   "suites NULL while raw_video_active and RAW_IS_IDLE" as a realloc trigger (or set
   `realloc = 1` at the end of recording cleanup). Also fixes the second-recording
   failure without relying on PROP_LV_ACTION working.
4. **Verify PROP_LV_ACTION on 6D2** — check the stop-time console for a denial print
   from patch 0004; if denied, PauseLiveView/ResumeLiveView are no-ops on this port
   (affects more than mlv_lite).

## What to test next on hardware (cheap, high-signal)

- Record in Canon 1080/25p: MLVI should read ~25000/1000 (confirms the TG story), and
  the take should last ~5x longer (~2 s, confirms the pool model).
- After a recording stops, wait: confirm "No memory suites." persists indefinitely; then
  half-press/menu-flip and confirm it stops after `realloc_buffers` prints reappear.
- Attempt a second recording without touching anything: expect instant
  "Movie recording stopped automagically" + header-only MLV (confirms the harmful side
  of (b)).
