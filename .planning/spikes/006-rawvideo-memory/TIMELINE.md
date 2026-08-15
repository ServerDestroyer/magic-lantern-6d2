# Spike 006 — RAW video memory: annotated console timeline

Date: 2026-08-15. Session: real 6D2, movie LiveView, 16:12, build = dev + patches 0001+0004, exFAT 256GB SD.
All paths relative to repo root; `ml/` = magiclantern_simplified (dev + patches 0001-0004).

## Actors (tasks and events)

- **ShootTask** — runs `raw_rec_polling_cbr` (registered `CBR_SHOOT_TASK`, `ml/modules/raw_video/mlv_lite/mlv_lite.c:4611`, body at `:2020`) every ShootTask polling iteration (tens of ms). This is the task that allocates and frees all memory while idle.
- **LiveViewTask** — runs `raw_rec_vsync_cbr` (`:4608`) once per LV frame → `process_frame()` (`:2838`). This is the capture side; it is what sets `buffer_full`.
- **raw_rec_task1** — created on REC keypress (`task_create("raw_rec_task1", ..., raw_video_rec_task, 0)`, `:3979`). The writer task: prepares buffers, creates the file, writes groups, flushes, cleans up.
- **compress_task** — `:4592`, drains `compress_mq`; for uncompressed output it only shepherds frame completion.
- **RscMgr (Canon task)** — executes `srm_malloc_cbr` (`ml/src/exmem.c:463`) when ML requests SRM buffers.

State machine: `RAW_IDLE → RAW_PREPARING → RAW_RECORDING → RAW_FINISHING → RAW_IDLE`, all transitions in `raw_video_rec_task`.

## Cycle 1 — entering movie LV with RAW video ON

Trigger: `raw_rec_polling_cbr` computes `current_state` (`mlv_lite.c:2033-2044`); on LV entry `raw_video_active` flips 0→1, so `current_state != prev_state` sets `realloc = 1` (`:2046-2049`). Next iteration with `RAW_IS_IDLE && gui_state == GUISTATE_IDLE`, it locks the UI and calls `realloc_buffers()` (`:2069-2077`). `realloc_buffers()` (`:1513-1528`) = `free_buffers()` + `shoot_malloc_suite(0)` + `srm_malloc_suite(0)` + the two summary prints. All of this runs in ShootTask under `settings_sem`.

| Console line | Source | Function | What it means |
|---|---|---|---|
| `srm_malloc_suite(0)...` | `ml/src/exmem.c:602` | `_srm_malloc_suite` (via `srm_malloc_suite` wrapper `ml/src/mem.c:1056` taking `mem_sem`) | Called from `realloc_buffers` (`mlv_lite.c:1523`) because "Use SRM memory" is ON. Arg 0 = "give me every SRM buffer you can". `shoot_malloc_suite(0)` ran just before this line but prints nothing (`exmem.c:285-302`, its qprintf is commented out). |
| `[SRM] alloc all buffers` | `ml/src/exmem.c:496` | `srm_alloc_internal` | First SRM use since power-on (`srm_allocated==0`). Calls `srm_shutter_lock()` (`exmem.c:479` → `gui_uilock(icu_uilock \| UILOCK_SHUTTER)`) — this is what produces the `UILock: ... -> 41000001` line (see below). |
| `[SRM] buffer 4c3f0070` | `ml/src/exmem.c:556` | `srm_alloc_internal` | One line per SRM buffer obtained from `SRM_AllocateMemoryResourceFor1stJob` (Canon RscMgr calls back `srm_malloc_cbr`, `exmem.c:463`). `0x4c3f0070` = the RAW-photo capture buffer Canon handed over. Size is the hardcoded `SRM_BUFFER_SIZE = 0x2D20000` = 47,316,992 B = 45.1 MiB (`ml/platform/6D2.111/consts.h:101`). Exactly one line because `SRM_MAX_BUF_COUNT_VIDEO_MODE = 1` on 6D2 (`consts.h:102` — "4 is okay in LV but not video, NG AllocMem1"). Note: with count=1 and the alloc succeeding, the timeout branch (`exmem.c:524-554`) is never reached, so the shutter "stays locked" until free — moot here since patch 0004 denies UILOCK writes anyway. |
| `srm_malloc_suite => 18f748` | `ml/src/exmem.c:642` | `_srm_malloc_suite` | `0x18f748` = the `struct memSuite *` from Canon's `CreateMemorySuite` (`exmem.c:624`) — a small DryOS-heap descriptor object (hence the low address), wrapping the single 45 MiB chunk at `0x4c3f0070`. This handle is what `srm_free_suite` later receives. |
| `Shoot memory: 135MB` | `ml/modules/raw_video/mlv_lite/mlv_lite.c:1526` | `realloc_buffers` | `shoot_mem_suite->size` after `shoot_malloc_suite(0)`. Alloc-all path = `shoot_malloc_autodetect()` (`exmem.c:206-239`): probes `AllocateMemoryResource` in 4 MiB steps until failure, final size = last_ok + 4 MiB backup − 1 MiB. 135 = 132+4−1, i.e. the probe succeeded up to 132 MiB. |
| `SRM memory: 45MB` | `mlv_lite.c:1527` | `realloc_buffers` | `srm_mem_suite->size` = 1 × 47,316,992 B = 45.1 MiB. |
| `Setting up buffers (frame size 3.5MB, fullres size 4.3MB)` | `mlv_lite.c:1572-1573` | `setup_buffers` | Called from `refresh_raw_settings` (`:1018`) — the 4×/s parameter poll (`should_run_polling_action(250,...)`, `:1013`) that ShootTask runs while idle and outside menu (`:2080-2083`). `frame size` = `max_frame_size` = 1920×1080×14/8 + 64 (VIDF hdr) + 4, 512-aligned = **3,629,056 B** — exactly the VIDF block size found in the recovered MLV. `fullres size` = `raw_info.width × (raw_info.height+2) × 14/8` (`:1549`) = 4.3 MiB = the full LV raw buffer (used for double-buffer copy source). |
| `Trying double buffering (shoot, full size 4.3MB)...` | `mlv_lite.c:1588` | `setup_buffers` | fullres (4.3 MiB) < 20 MiB threshold (`:1578`), so it wants a dedicated full-size copy buffer carved from the shoot suite. |
| `Using double-buffering (frame size 3.5MB, wasted 16kB)` | `mlv_lite.c:1387-1388` | `alloc_fullsize_buffer` | Picked the shoot chunk minimizing `(chunk_size − fullres − 64) % max_frame_size` (`:1371`); only 16 KiB of that chunk is unusable. `fullsize_buffers[0]` now points into a shoot chunk; `fullsize_buffers[1]` = Canon's own LV raw buffer (`:1604`). |
| `45008a38: 28MB after full-res buffer.` | `mlv_lite.c:1427` | `add_mem_suite` | While slicing the shoot suite into frame slots, the chunk that hosts the fullres buffer is re-entered at `ptr + fullres_buf_size`: `0x45008a38` = first byte after the 4.3 MiB fullres buffer, 28 MiB of that chunk remain → 8 slots of 3.46 MiB. |
| `35 slots from shoot_malloc.` | `mlv_lite.c:1617` | `setup_buffers` | `valid_slot_count` after slicing the shoot suite: 35 × 3.46 MiB ≈ 121 MiB usable out of 135 (rest lost to the fullres buffer, 64-byte alignment, chunk fragmentation, and the 32M−512K group splits at `:1461-1468`). |
| `Allocated 48 slots.` | `mlv_lite.c:1630` | `setup_buffers` | Total after also slicing the SRM suite (`:1618`): 48 − 35 = **13 SRM slots** (floor(47,316,992 / 3,629,056) = 13). Matches "SRM constant, 13 slots both cycles". |
| `Black level: 2339` | `ml/src/raw.c:1343` | `raw_update_params_work` | Autodetected black mean; printed only when it moves ≥10 from the stored value (`raw.c:1341`). Runs inside `raw_update_params()` from the same 250 ms poll, but only recomputes when the raw backend is dirty — that decoupling is why this line lands *after* the slot prints in cycle 1 and *before* them in cycle 2. 6D2 has no `BLACK_LEVEL` nail-down constant in `platform/6D2.111/consts.h`, so the raw autodetect value is used as-is. |
| `UILock: 00000000 -> 41000001 => 00000000 (!!!)` | `ml/src/gui-common.c:690` | `gui_uilock` | `0x41000001` = `UILOCK_REQUEST (0x41000000) \| UILOCK_SHUTTER (0x0001)` (`ml/src/property.h:222,226`) → caller is `srm_shutter_lock` during SRM alloc. Result `00000000` = the D678 firmware denied the `PROP_ICU_UILOCK` write; patch 0004 skips the `prop_request_change_wait` timeout on denied writes, so no livelock. `(!!!)` = requested lower-16 ≠ actual. The polling CBR's `gui_uilock(UILOCK_EVERYTHING)` / `(UILOCK_NONE)` bracket around realloc/free (`mlv_lite.c:2059-2076`) prints the same pattern with `...017f` / `...0000`. Denials are cosmetic for memory work, but mean **no UI locking actually protects realloc/record on 6D2**. |

## Menu open — free cycle

Observed: `srm_free_suite(18f748)` then `[SRM] free all buffers` (same handle as cycle 1's alloc — this is mlv_lite's suite, not `guess_free_mem`'s; that debug path would also print `shoot buffer:`/`srm buffer:` lines, `ml/src/mem.c:1196,1245`, which did not appear).

| Console line | Source | Function | What it means |
|---|---|---|---|
| `srm_free_suite(18f748)` | `ml/src/exmem.c:658` | `_srm_free_suite` | Freeing the exact suite allocated in cycle 1. Marks the chunk's backing buffer unused in `srm_buffers[]`, `DeleteMemorySuite`, then: |
| `[SRM] free all buffers` | `ml/src/exmem.c:574` | `srm_free_internal` | No SRM buffer in use anymore → returns the 45 MiB buffer to Canon (`SRM_FreeMemoryResourceFor1stJob`) and calls `srm_shutter_unlock()` (another denied UILock write). |

Caller chain: `free_buffers()` (`mlv_lite.c:1482`, which also does `shoot_free_suite`, silent) ← **the only path consistent with this moment is `raw_rec_polling_cbr:2054-2064`**: "raw video turned off? free any resources". That branch requires `raw_video_active == 0`, i.e. one of `raw_video_enabled` / `lv` / `is_movie_mode()` (`:2027`) went false while the ML menu was open. `realloc_buffers` is excluded (needs `gui_state == GUISTATE_IDLE`, false in menu, and would print alloc lines immediately after); the recording-cleanup and H.264-proxy frees are excluded (no recording). So: **on this port, opening the ML menu makes `raw_video_active` evaluate false — most plausibly the `lv` propvalue drops.** On classic bodies the ML menu does not free the buffers; worth one log line on `lv`/`is_movie_mode()` at menu open to pin which flag flaps. Consequence is benign but wasteful: every menu visit costs a full free + 1-2 s realloc, and the Canon-side layout may change across it (it did — see cycle 2).

Note: the same `raw_video_active == 0` condition also runs `raw_video_disable()` → `raw_lv_release()` (`:1794-1800`), so raw LV capture stops too while the menu is open.

## Cycle 2 — back in LV (~35 s later)

Trigger: same as cycle 1 — `raw_video_active` 0→1 flips `current_state`, `realloc = 1`, ShootTask reallocates once `gui_state` is idle again. Lines have identical sources; the deltas are the story:

| Observation | Meaning |
|---|---|
| `[SRM] buffer 65a4c070`, `srm_malloc_suite => 18f5c0` | Canon handed a *different* 45 MiB raw-job buffer, and the suite descriptor landed at a different heap address — Canon-side memory layout changed across the menu visit. |
| `Shoot memory: 43MB` | Autodetect stopped at 40 MiB (43 = 40+4−1). **92 MiB of the shoot pool that existed at cycle 1 was not obtainable.** SRM unaffected (fixed-size job buffer). |
| `Black level: 2641` | Re-autodetected, moved ≥10 (2339→2641); prints because the delta check fires. Sensor warmed up / mode re-init; not a memory symptom. |
| `11 slots from shoot_malloc.` / `Allocated 24 slots.` | 4.3 fullres + 11×3.46 = 42.4 of 43 MiB — consistent. +13 SRM = 24 total. The recording that follows ran on **24 slots ≈ 83 MiB** of frame buffer. |

Candidate mechanisms for the 92 MiB shrink (not resolved by this timeline):

1. **Autodetect timeout, not genuine exhaustion**: `shoot_malloc_suite_int` treats any `AllocateMemoryResource` that takes >100 ms as "memory full" (`take_semaphore_nc(sem, 100)`, `ml/src/exmem.c:177`). If Canon's allocator got slower (fragmentation after menu/LV re-init), the probe under-reports. Cheap test: bump the timeout, or retry the probe a second time in the same cycle and compare.
2. Canon genuinely holding ~92 MiB more after the menu visit (LV re-init, raw path re-arm via `lv_save_raw` off/on that accompanied the free cycle).
3. FEATURE_SHOW_TASKS/CPU_USAGE/GUI_EVENTS (ON in this build) — considered per the peer session, but these draw from the small ML heaps, not the shoot pool; 92 MiB is implausible from them. Keep them out of the suspect list unless a build without them changes the numbers.

Repeating the LV-enter/menu/LV-enter sequence and watching whether the pool keeps shrinking (leak) or oscillates 135↔43 (state-dependent) is the discriminating experiment.

## Record attempt — REC press

REC → `raw_rec_keypress` → `task_create("raw_rec_task1", ...)` (`mlv_lite.c:3979`) → `raw_video_rec_task`: state `RAW_PREPARING` (`:3372`), `raw_update_params` (`:3421`), `update_resolution_params` + `setup_buffers` (`:3428-3429` — returned 2 = "config unchanged", hence no new buffer prints), file create (`:3440`), headers written (`:3451`), `fps = fps_get_current_x1000()` (`:3466`), state `RAW_RECORDING` (`:3479`). Capture side: `raw_rec_vsync_cbr` → `process_frame` (`:2838`) grabs a free slot per LV frame and queues it; writer loop (`:3500`) groups contiguous queued slots and writes them.

| Console/screen line | Source | Function | What it means |
|---|---|---|---|
| `Early stop (8). Should have recorded a few more frames.` | `mlv_lite.c:3776-3778` (bmp_printf — on-screen overlay, not console printf) | `raw_video_rec_task`, `abort_and_check_early_stop` label | The capture side found no free slot and set `buffer_full = 1` (`process_frame`, `:2909` "card too slow"; other setters `:2794/:2801` are compression-only, `:2864` is EDMAC timeout). Writer loop sees it (`:3502-3505`) and jumps to the abort label. **8 is not an error code** — it is `last_block_size` (`:3699`), the frame count of the last group successfully written before the abort. The `> 3` heuristic (`:3774`) means "the writer was still moving healthy-sized groups when capture overflowed", i.e. stop-due-to-overflow rather than gradual starvation; it also beeps 8 times. |
| `Flushing buffers... 1 frames left` | `mlv_lite.c:3845-3847` (bmp_printf) | `raw_video_rec_task` post-loop flush | After `RAW_FINISHING` (`:3797`), remaining queued-but-unwritten slots are written one at a time (`:3843-3908`); the counter is `MOD(writing_queue_tail - writing_queue_head, ...)`. Reaching "1" and completing explains the clean 25-frame, properly `FINALIZED` file: `finish_chunk` at `:3922` patches `videoFrameCount=25`. |
| `No memory suites.` (repeated, one per ~250 ms) | `mlv_lite.c:1568` (printf) | `setup_buffers` | Cleanup freed everything: `free_buffers()` at `:3933`. After that, ShootTask's idle poll keeps calling `refresh_raw_settings(0)` (`:2080-2083`) → `setup_buffers()` every 250 ms; both suites are NULL → this line, forever. **Nothing re-arms `realloc`**: the `current_state` fingerprint (`:2033-2044`) is identical before/after a raw recording, so `realloc` stays 0 until a mode change, menu round-trip, or raw-video toggle. Consequences: (a) the console spam observed; (b) an immediate second REC press would enter `raw_video_rec_task` with 0 slots (`setup_buffers` returns 0, return value unchecked per the comment at `:1537`) and die with "Movie recording stopped automagically" after creating and deleting an empty file. Cheap fix candidate: set `realloc = 1` in the cleanup path. |

### Write-speed sanity check — is "Early stop (8)" just physics?

Yes. Required sustained rate: 3,629,056 B × 59.94 fps = **207.5 MiB/s**. 6D2 SD interface (UHS-I) delivers ~40-90 MB/s. Buffer pool: 24 slots × 3.46 MiB = **83 MiB**. Time to overflow ≈ 83 / (207.5 − W): 0.50 s at W=40, 0.71 s at W=90. Observed: VIDF timestamps span 0.400 s (24 intervals) — squarely in that window. 25 frames on 24 slots = all slots filled once plus ~1 recycled after early writes; 25 × 3.46 MiB ≈ 86.5 MiB written total (file is 90,727,424 B with headers ✓). The stop path taken (`buffer_full` → `abort_and_check_early_stop` → `last_block_size 8 > 3` → "Early stop") is exactly what the buffers-full path produces when the writer is mid-stream; the sibling branch ("Movie recording stopped automagically", `:3783`) appears when the last group had ≤3 frames. No bug required to explain the stop itself. To record 1080p continuously this camera needs compression + lower bit depth + smaller resolution, or it remains a ~0.5 s burst recorder.

One real (secondary) defect does touch this path: the anti-overflow throttle (`:3625-3641`) computes `overflow_time = free_slots * 1000 * 10 / fps` with the **3× too high fps** (below), so `frame_limit` is ~3× too small and the writer chops groups smaller than optimal. It cannot save a 207 MiB/s stream, but it will make marginal (compressed) settings stop earlier than they should. Fixing fps fixes this for free.

## The 179 fps anomaly — root cause found in source

- Header write: `mlv_lite.c:3086-3091` — `file_hdr.sourceFpsNom = fps_get_current_x1000()`, `sourceFpsDenom = 1000`. Recorded: 178993/1000.
- `fps_get_current_x1000` (`ml/src/fps-engio.c:912-919`): `fps = TIMER_TO_FPS_x1000((regB & 0xFFFF) + 1)` where `TIMER_TO_FPS_x1000(t) = TG_FREQ_FPS / t` (`:454`) and `TG_FREQ_FPS = calc_tg_freq((regA & 0xFFFF) + 1)` (`:438-444,451`) built on **`TG_FREQ_BASE 66800000`** for CONFIG_6D2 (`:306`). Registers read via ROM stubs `_get_fps_register_a/b` (`ml/platform/6D2.111/stubs.S:278-279`, glue in `platform/6D2.111/fps-engio_per_cam.c`).
- The port's own calibration comment (`fps-engio.c:308-322`) says the 6D2 timing-generator clock is **not constant**: ≈66.8 MHz only in 23.98/25/29.97 modes; ≈**44.46 MHz at 50p** and ≈**22.32 MHz at 59.94p** ("Variable, like 200D"). ML has no mode-dependent correction for this — the constant is simply wrong by ~3× in 60p.
- Arithmetic check, 1080p59.94 (logged timers `0x1d8, 0x314` → timerA=473, timerB=789): `66.8e6 × 1000 / 473 / 789 = 178,994` — reproduces the recorded **178,993** to rounding. True rate: `22.32e6 / (473 × 789) ≈ 59.8`. Ratio 178,993/59.94 = 2.99 ≈ 66.8/22.32.
- Ground truth from the file: 25 VIDF timestamps span 0.400 s = 24 intervals × 16.67 ms = **59.94 fps exactly**. (The "~62.5" first-pass estimate divided the span by 25 instead of 24.) So the sensor ran plain Canon 1080p60; only ML's fps *readout* is 3× off.

Where the wrong value flows: MLVI header (`:3086`), writer throttle (`:3466` → `:3630`), recording-time/frames-remaining estimates (`:1808`, `:2672`), pre-record frame budget (`:1259`, `:1284` — inactive this session). It does **not** flow into slot allocation (`setup_buffers` has no fps term), so the 48→24 slot difference is purely the shoot-pool shrink, not fps. Fix direction: make `TG_FREQ_BASE` (or `calc_tg_freq`) mode-aware on 6D2 — e.g. derive the actual TG clock per video mode from the logged (timerA, timerB, true fps) triples in the port comment, or read whatever divisor the 200D-style variable-clock cameras expose. Postprocessing of today's clip just needs MLVI fps overridden to 59940/1000 (frame timestamps in the file are correct).

## Summary of open items feeding spike 006

1. **92 MiB shoot-pool shrink after menu round-trip** — discriminate autodetect-timeout (`exmem.c:177`) vs genuine Canon-side consumption; repeat-cycle experiment.
2. **Menu open frees buffers** — identify which of `lv` / `is_movie_mode()` goes false in ML menu on this port (`mlv_lite.c:2027`); decide whether that is acceptable.
3. **fps 3× wrong in 50/60p** — mode-dependent TG clock unported for 6D2 (`fps-engio.c:306` vs `:316-322`); also skews writer throttle and time estimates.
4. **Post-recording "No memory suites." spam / no realloc until state change** — `realloc` never set after cleanup (`mlv_lite.c:2046`, `:3933`); second REC without a mode change starts with 0 slots.
5. **UILOCK writes denied on D678** — all `gui_uilock` protection during realloc/record is currently a no-op on 6D2 (patch 0004 makes it non-blocking); revisit once a working lock method exists.
6. **Early stop (8) is physics** — 207.5 MiB/s needed vs ≤90 MB/s card; not a bug. Continuous recording requires compression/lower bpp/smaller res.
