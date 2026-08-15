# Task 2 — mlv_lite memory lifecycle: the 135MB → 43MB shoot_malloc shrink

Analysis of the 2026-08-15 16:12 session (patches 0001+0004, movie LV, exFAT 256GB).
All line numbers refer to `ml/modules/raw_video/mlv_lite/mlv_lite.c` (NOT `ml/modules/mlv_lite/` — that path does not exist in this tree) and `ml/src/exmem.c` at HEAD `3f24042a4`.

**Bottom line first:** mlv_lite's own suite lifecycle is balanced — every `shoot_malloc_suite`
has a matching `shoot_free_suite` on every path, and nothing in mlv_lite can retain 92MB.
The shrink happens *inside* `shoot_malloc_suite(0)`'s size autodetection
(`exmem.c:shoot_malloc_autodetect`), which measures "all the memory Canon will give us
right now" from scratch on every cycle. Both observed numbers fit its formula exactly
(max = 4·k + 3 MB: 135 = 132+4−1, 43 = 40+4−1). So either Canon's pool genuinely had
~92MB less free at cycle 2, or a single slow RscMgr response (>100ms) truncated the
probe staircase. Neither is an ML-side leak. Discriminating experiment at the end.

---

## 1. Buffer lifecycle, end to end

### Allocation — `realloc_buffers()` (mlv_lite.c:1512-1528)

```
free_buffers();                                   /* always frees old suites first */
shoot_mem_suite = shoot_malloc_suite(0);          /* "all you can give me" */
srm_mem_suite   = use_srm_memory ? srm_malloc_suite(0) : 0;
printf("Shoot memory: %s\n", ...); printf("SRM memory: %s\n", ...);
```

- `use_srm_memory` defaults to 1 (mlv_lite.c:162).
- Called from exactly ONE place: the polling CBR (mlv_lite.c:2069-2077), guarded by
  `realloc && (RAW_IS_IDLE || RAW_IS_PREPARING) && gui_state == GUISTATE_IDLE`.
- The `realloc` flag is set only when a state hash changes (mlv_lite.c:2031-2050):
  `raw_video_active | RECORDING_H264<<1 ^ pic_quality<<4 ^ video_mode_resolution<<8
  ^ video_mode_fps<<16 ^ video_mode_crop<<24`. Menu open/close flips `raw_video_active`
  (bit 0), which is why closing the menu re-triggers allocation.

### `shoot_malloc_suite(0)` — where the number 135/43 actually comes from (exmem.c)

`_shoot_malloc_suite(0)` (exmem.c:284-302) does NOT ask Canon "how much is free".
It runs `shoot_malloc_autodetect()` (exmem.c:206-239):

1. Allocate a 4MB "backup" suite.
2. Loop `size_mb = 4, 8, 12, ...`: `AllocateMemoryResource(tested_size)`, wait on a
   semaphore with a **100ms timeout** (exmem.c:177), free it, repeat.
3. First probe that misses the 100ms deadline ends the loop. The request stays queued
   inside Canon's RscMgr; freeing the backup suite is what lets it complete later, at
   which point `allocCBR` sees `timed_out` and frees it immediately (exmem.c:97-108).
4. Result: `max_size = last_ok + 4MB − 1MB`, then one real allocation of that size.

Consequences:
- Every reported size is ≡ 3 (mod 4) MB. **135 = 132+3 ✓, 43 = 40+3 ✓** — both observed
  values are exactly what this staircase produces. The real free space is only known to
  ±4MB, and only *if* the terminating timeout was a genuine out-of-memory.
- A single RscMgr response slower than 100ms — with memory still available — is
  indistinguishable from "memory full" and silently truncates the result. Comment at
  mlv_lite.c:1519-1521 acknowledges the whole procedure is slow (1-2s) and approximate.
- Known micro-leak, irrelevant at this scale: the 16-byte `alloc_msg_t` of a timed-out
  probe leaks if the queued CBR never fires.

### `srm_malloc_suite(0)` — the SRM side (exmem.c:599-644)

6D2 consts (`ml/platform/6D2.111/consts.h:101-102`):
`SRM_BUFFER_SIZE = 0x2d20000` (45.1MB), `SRM_MAX_BUF_COUNT_VIDEO_MODE = 1`.
So `srm_buffers[]` has exactly ONE slot: `srm_alloc_internal` allocates one 45MB
1st-job buffer, prints `[SRM] buffer …`, loop ends without hitting the timeout branch
(so no use-after-free trickery on 6D2), `srm_malloc_suite` wraps it in a suite.
That matches the log: one `[SRM] buffer` line, "SRM memory: 45MB", 13 slots, and the
constant SRM size across both cycles — **the SRM path round-trips perfectly; the loss
is confined to the shoot pool.**

Side note (not memory, but real): `srm_shutter_lock()` (exmem.c:479-484) works via
`gui_uilock`, and patch 0004 denies `PROP_ICU_UILOCK` writes — the observed
`UILock: 00000000 -> 41000001 => 00000000 (!!!)` lines are exactly these calls being
refused. The SRM anti-ERR70 shutter lock is therefore a no-op on this build.

### Carving — `setup_buffers()` (mlv_lite.c:1539-1654)

Everything below is **pointer arithmetic inside the two suites; no further allocation**:

- Full-size (double-buffer) buffer: `alloc_fullsize_buffer` (mlv_lite.c:1354-1392) just
  *picks a chunk address* inside a suite. "Using double-buffering (… wasted 16kB)".
- `add_mem_suite` (mlv_lite.c:1410-1479) walks each suite chunk and slices it into
  `max_frame_size` slots. The chunk that holds the fullres buffer is entered at
  `ptr + fullres_buf_size` — that is the "`45008a38: 28MB after full-res buffer`" line
  (mlv_lite.c:1427): a ~32MB RscMgr chunk minus the 4.3MB fullres carve. Not a leak.
- `fullsize_buffers[1] = UNCACHEABLE(raw_info.buffer)` — Canon's own LV raw buffer,
  never allocated or freed by us.
- Failure paths return 0/2 *before* any allocation happens; nothing to unwind.

Slot math confirms all memory is accounted for:
- Cycle 1: 35 shoot slots ×3.5MB ≈ 122.5MB + 4.3MB fullres + alignment/fragment waste ≈ 135MB. 48 total = 35 + 13 SRM.
- Cycle 2: 11 shoot slots ≈ 38.5MB + 4.3MB ≈ 43MB. 24 total = 11 + 13 SRM.

### Freeing — `free_buffers()` (mlv_lite.c:1481-1510)

Zeroes the config/slot globals, then `shoot_free_suite(shoot_mem_suite)` and
`srm_free_suite(srm_mem_suite)`, both nulled afterwards. `_shoot_free_suite`
(exmem.c:76-91) calls `FreeMemoryResource` and **blocks** on the free CBR
(`take_semaphore(free_sem, 0)` = infinite wait) — when it returns, RscMgr has
acknowledged the free. The camera did not hang at menu open, so the CBR fired: from
ML's side the 135MB was returned.

Complete caller list (verified — there are no others):

| Caller | Line | When |
|---|---|---|
| `realloc_buffers()` | 1517 | always, before re-allocating |
| polling CBR idle branch | 2061 | raw video no longer active (menu open / left LV / disabled) |
| `raw_video_rec_task` H.264-proxy start | 3401 | frees before Canon's layout changes |
| `raw_video_rec_task` cleanup | 3933 | **after every recording** |
| dead code `if (0)` srm-only free | 1626 | never runs |

### The polling loop on LV/menu transitions (mlv_lite.c:2019-2089)

- Menu open → `raw_video_active` goes false → idle branch (2054-2066):
  `gui_uilock(EVERYTHING)` (denied by patch 0004, harmless here), `free_buffers()`,
  `gui_uilock(NONE)`. Also `raw_lv_request_update()` (mlv_lite.c:1781-1804) calls
  `raw_video_disable()` → `raw_lv_release()` → `raw_lv_disable()` →
  `call("lv_save_raw", 0)` (raw.c:2504-2517) — **Canon's raw LV stream is torn down
  and rebuilt around every menu cycle too.**
- Menu close → state hash flips → `realloc = 1` → next iteration with
  `gui_state == GUISTATE_IDLE` runs `realloc_buffers()`. The ~35s gap to cycle 2 is
  just how long it took to be back in idle LV with the hash flipped.

## 2. Direct answers

### (a) Is the menu-open free supposed to free the shoot suite too — and does it?

**Yes and yes.** The only free path reachable at menu open is `free_buffers()` via the
polling CBR idle branch, and it frees the shoot suite *first* (mlv_lite.c:1500-1504),
then SRM (1505-1509). It only *looks* SRM-only in the console because
`shoot_free_suite` prints nothing while `_srm_free_suite`/`srm_free_internal` print
`srm_free_suite(%x)` / `[SRM] free all buffers` (exmem.c:658, 574). The shoot free also
blocks until Canon's free CBR fires, so it completed. This is intended behavior: don't
hold ~180MB of Canon's memory while idling in menus.

### (b) Which allocation could survive and eat 92MB?

**None on the ML side.** Audit of every candidate:

- Shoot/SRM suites: freed on every path (table above); `realloc_buffers` frees before
  allocating; suite pointers nulled after free.
- Fullres buffer, "28MB after full-res buffer" chunk, all 48 slots, reserved slots:
  carved *inside* the suites — freed with them, cannot outlive them.
- `setup_buffers` early returns (0/2): occur before any allocation.
- Double-buffering split: two pointers into existing memory (suite chunk + Canon's buffer).
- Genuine leaks found, all tiny: 16-byte `alloc_msg_t` per timed-out probe;
  suite/chunk *metadata* structs. Nothing within two orders of magnitude of 92MB.

The only ML-*originated* mechanism that could pin large memory is the **timed-out probe
request left queued inside Canon's RscMgr** by `shoot_malloc_autodetect` (exmem.c step 3
above). On D45 the backup-free drains it; if D7's RscMgr queues behave differently
(request pinned at queue head reserving space), cycle 1's terminating ~136MB request
could still be pending at cycle 2. Unproven — needs the instrumentation below.

### (c) Is the pool shared with other consumers?

**Yes.** `shoot_malloc` = Canon's RscMgr resource memory (`AllocateMemoryResource`),
the same pool Canon uses for the H.264 encoder, LV pipeline and image jobs, and which
ML's generic allocator can also hand out for large requests (mem.c allocator table,
`.name = "shoot_malloc"`, mem.c:287). On this build, though:

- Patch 0001's `FEATURE_SHOW_TASKS/CPU_USAGE/GUI_EVENTS`: display-only, no large
  allocations — **ruled out** as the 92MB consumer.
- raw.c's 45MB `RAW_LV_BUFFER_ALLOC_SIZE` allocation (raw.c:123-124, 856) is **compiled
  out on 6D2**: it requires `CONFIG_EDMAC_RAW_SLURP`, which 6D2 does not define
  (6D2 uses `RAW_LV_EDMAC_CHANNEL_ADDR 0xd0058000`, consts.h:103). Ruled out.
- Canon-side: cannot be ruled out from source. The menu cycle tears down and restarts
  the raw LV stream (`lv_save_raw` 0→1) and repositions the SRM 1st-job buffer — its
  address moved 0x4c3f0070 → 0x65a4c070 between cycles, which proves Canon's layout DID
  change. 92MB ≈ 2 × SRM_BUFFER_SIZE is suggestive of two full-res-sized Canon buffers,
  but that is correlation, not proof.

So there are exactly two surviving hypotheses:

1. **Canon consumed ~92MB between cycles** (raw-stream/encoder buffers allocated on the
   second `lv_save_raw` restart, or deferred allocations that ML's cycle-1 full-pool
   grab had blocked, which landed after ML freed at menu open). Cycle 1 would then be
   the anomalous reading (ML raced Canon at first raw enable) and 43MB the steady state.
2. **Autodetect truncation**: one >100ms RscMgr response at the 44MB probe ended the
   staircase early; memory was free but never measured. (Variant: cycle 1's stale queued
   probe request pinning the pool, per (b).)

Note the shrink is **not** required to be monotonic under hypothesis 2 — that is the
discriminator (see §4).

## 3. Related observed symptoms explained by the same lifecycle

**"No memory suites." spam after recording** — expected with this tree, not 6D2 damage.
`raw_video_rec_task`'s cleanup calls `free_buffers()` (mlv_lite.c:3930-3935; already
present in the pre-6D2 magiclantern_simplified lineage, though the 2020-11 import
7c004cee96 did *not* free buffers there — upstream added it during the rework). After
that, `refresh_raw_settings` runs 4×/s from the polling CBR (mlv_lite.c:2080-2083,
throttle at 997-1027) and calls `setup_buffers()`, which prints "No memory suites."
(mlv_lite.c:1566-1570) every 250ms because both suite pointers are null and the state
hash has not flipped, so `realloc` never fires. Consequence worth flagging: **a second
record attempt without an intervening menu/mode cycle starts with 0 slots** —
`setup_buffers` at 3429 fails, nothing checks the return, first vsync finds no capture
slot → `buffer_full = 1` (mlv_lite.c:2905-2910) → instant "stopped automagically".
Workaround until fixed: open/close the ML menu (or change video mode) between takes.

**"Early stop (8)" is buffers-full physics, not a distinct bug.** `buffer_full` is set
by `process_frame` when no free slot exists ("card too slow", mlv_lite.c:2905-2910);
the writer sees it at loop top (3502-3505) and jumps to `abort_and_check_early_stop`;
`last_block_size` is simply *the frame count of the last successfully written group*
(3699), and >3 prints "Early stop (N)" (3774-3780). So "8" is not an error code.
Numbers: 3.63MB/frame at the real ~62.5 fps cadence = ~227MB/s incoming vs ~40-90MB/s
UHS-I → with 24 slots (87MB) the buffer fills in ~0.5-0.6s ≈ 30-35 captured frames;
flush ("Flushing buffers… 1 frames left", 3839-3846) then writes out what's held —
25 frames on disk matches exactly. Even with cycle 1's 48 slots this mode records only
~1.1s. The memory shrink halved an already sub-second recording; it did not cause the stop.

**fps 179 interaction with slot math**: wrong fps does NOT change slot counts (those
come purely from suite sizes / `max_frame_size`). It enters the writer via
`fps = fps_get_current_x1000()` (3466) into the overflow throttle (3630-3641):
`overflow_time = free_slots*1000*10/fps` — a 2.86× overestimated fps shrinks
`frame_limit`, forcing smaller write blocks, which lowers sustained card throughput and
brings `buffer_full` slightly earlier. Secondary effect; the fps root-cause hunt is a
separate task.

## 4. Upstream check

`ml/` HEAD `3f24042a4` **is** the current tip of `origin/dev`
(verified via `git ls-remote` against reticulatedpines/magiclantern_simplified on
2026-08-15) — there are **no upstream commits, leak fixes or otherwise, beyond this
tree** for `src/exmem.c` or `modules/raw_video/mlv_lite/mlv_lite.c`. Working-tree
diffs (patches 0001+0004) touch neither file. Recent relevant history: `f0dc17db9`
(card spanning) reshuffled the cleanup block; `e77bd879a` "6D2: mostly working raw
video" is the port baseline; `ca800c05e` made `SRM_BUFFER_SIZE` per-cam.

## 5. Discriminating experiments (next camera session)

1. **Cycle test (no code change):** with console open, do LV → menu → LV five times,
   recording "Shoot memory: X" each cycle. Monotonic decrease ⇒ real retention/leak
   (hypothesis 1 or the pinned-request variant); fluctuation or recovery to ~135
   ⇒ autodetect truncation (hypothesis 2). Also note whether the SRM buffer address
   keeps moving.
2. **Instrument the staircase** (build-tree owner; 2 lines in
   `exmem.c:shoot_malloc_autodetect`): print per-probe `tested_size`, success/timeout,
   and elapsed ms. One slow-but-successful-later probe is then directly visible.
3. **Timeout test:** raise the 100ms `take_semaphore` timeout (exmem.c:177) to 1000ms.
   If cycle-2 sizes jump back to ~135MB, hypothesis 2 is confirmed.
4. **Isolation:** repeat with `use_srm_memory = 0` (removes SRM interplay), and with a
   video-mode change instead of a menu cycle (different Canon teardown path).
5. **Between-takes workaround check:** confirm that a menu open/close after a recording
   restores buffers before the next take ("No memory suites." spam stops, sizes print).
