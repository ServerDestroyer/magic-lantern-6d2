# Photo session 2 — 2026-08-15 18:25–18:30 — patch 0006 instrumented build

Source photos: `Pics of debuging/20260815_1825*.jpg` … `20260815_1830*.jpg` (15 frames),
plus the 17:47–17:49 boot/LV batch (7 frames) for context.
Transcribed from the ML console overlay (white-on-dark block over LiveView).

## Build identity — CONFIRMED CORRECT

`20260815_183015.jpg` (ML Help/About page) reads, partly occluded by the console overlay:

```
...on: 2026-08-15.6D2.111
...a4 dev
...00:43:40 UTC by chris@legion.
```

This matches `ml/platform/6D2.111/build/version.bin` byte-for-byte:

```
Magic Lantern 2026-08-15.6D2.111
Camera   : 6D2
Firmware : 111
Commit: 3f24042a4 dev
Built on : 2026-08-16 00:43:40 by chris@legion
```

`ml/platform/6D2.111/build/autoexec.bin` (mtime 2026-08-15 17:43:40 local = 00:43:40 UTC)
contains the string `probe`. **The camera was running the correct patch-0006 diagnostic
build.** The absence of `[probe]` and `raw inactive:` lines in the photos is NOT a wrong-build
problem — see Findings (a) and (d) for the real mechanisms.

The 17:47 batch is the *same* build (boot at 17:47, first LV at 17:49); the console shows
`[i] 404: edmac_format_size 100061 / 103721` + `Modules loaded`, which is normal ML startup
output on this port, not a separate "startup logger" build.

## Transcription table

Canon UI constant across the whole 18:25 batch unless noted: Movie mode `M`, timer `29:59`,
battery full, `SERVO AF`, `1/125`, `f/2.8`, `EC ±0`, `ISO AUTO` (changes to `f/4.0`, `ISO 800`
from 18:28:04 onward). ML `RAW video ON, 1920x1080 1.75x`.

| Time | Canon UI | Console lines (verbatim where legible) |
|---|---|---|
| 17:47:42 / 17:47:56 | "Sensor cleaning" splash (boot) | `[i] 404: edmac_format_size 100061` / `[i] 404: edmac_format_size 103721` / `Modules loaded` |
| 17:49:16 | LV, M, 29:59, 125 / 2.8 / ISO AUTO | `Trying double buffer…` / `Using double-buffer…` / `45008a40: 28MB after full-res buffer` / `35 slots from shoot_…` / `Allocated 40 slots.` / `Black level: 2137` / `2352` / `2476` / `2378` / `2345` / `2360` / `2405` / `2420` / `2226` / `2400` |
| 17:49:22 / 17:49:26 | LV | `srm_malloc_suite(0)…` / `[SRM] alloc all buffers` / `UILock: 00000000 -> 41000001 => 00000000 (!!!)` / `[SRM] buffer 65a4c070` / `srm_malloc_suite => 10f0b0` / **`Shoot memory: 135MB`** / **`SRM memory: 45MB`** / `UILock: 00000000 -> 41000000 => 00000000` / `Black level: 2376` / `Setting up buffers (frame size 3.5MB, fullres size 4.3MB)` / `Trying double buffering (shoot, full size 4.3MB)…` / `Using double-buffering (frame size 3.5MB, wasted 16kB).` / `45008a40: 28MB after full-res buffer.` / `?? slots from shoot_malloc` / **`Allocated 47 slots.`** / `UILock: 00000000 -> 41000000 => 00000000` ×2 |
| 17:49:28 / 17:49:32 | LV | same block, LCD-refresh ghosting; tail `Allocated 47 slots.` / `Black level: 2409` |
| **18:25:54 / 18:25:59** | LV, raw armed, idle | `srm_malloc_suite(0)…` / `[SRM] alloc all buffers` / `UILock: 00000000 -> 41000001 => 00000000 (!!!)` / `[SRM] buffer 4c3f0070` / `srm_malloc_suite => 18ed40` / **`Shoot memory: 135MB`** / **`SRM memory: 45MB`** / `UILock: 00000000 -> 41000000 => 00000000` / `Black level: 2138` / `Setting up buffers (frame size 3.5MB, fullres size 4.3MB)` / `Trying double buffering (shoot, full size 4.3MB)…` / `Using double-buffering (frame size 3.5MB, wasted 16kB).` / `45008a38: 28MB after full-res buffer.` / `35 slots from shoot_malloc.` / **`Allocated 40 slots.`** — **no `[probe]` lines above `srm_malloc_suite(0)…`** |
| **18:26:08** | LV, NotifyBox | NotifyBox: **`Early stop (9). Should have recorded a few more frames.`** / `Flushing buffers… 3? frames left`. Console tail: `UILock: 00000000 -> 4100017f => 0000?0?0 (!!!)` / `EDMAC copy resources unlocked.` / `UILock: 00000000 -> 4100017f => 00000000 (!!!)` |
| **18:26:12** | LV, NotifyBox | `Early stop (9)…` / `Flushing buffers… 1 frames left`. Console: heavy LCD ghosting; ~11 `UILock: … -> 41???0?? => 00000000 (!!!)` lines, then `…Buffer…` line, then first **`No memory suites.`** ×2 |
| **18:26:15** | LV, NotifyBox | NotifyBox unchanged. Console: **16 consecutive `No memory suites.` lines** (full window) |
| 18:27:48 | LV (photo out of focus) | Same `Early stop (9)` NotifyBox; console illegible but bottom rows read `No memory suites.` ×2 |
| **18:27:58** | LV, f/4.0-era | Realloc block mid-print, ghosted: `…41000001 => … (!!!)` ×3 / `[SRM] buffer …2070` / `srm_malloc_suite => 10ed60` / `…MB 41000000 => 00000000` / `Setting up buffers …fullres size 4.3MB)` / `…double-buffering …wasted 16kB)` / `…28MB after full-res buffer` / `…slots from shoot_malloc.` / `Black level: 2?0?`. Tail box: `No memory suites.` ×2 |
| **18:28:04 / 18:28:07** | LV, `f/4.0`, `ISO 800`; 18:28:07 shows red LV frame corners | `UILock: 00000000 -> 41000001 => 00000000 (!!!)` / `[SRM] buffer 0?4?2070` (≠ `4c3f0070`) / `srm_malloc_suite => 10ed60` / **`Shoot memory: 135MB`** / **`SRM memory: 45MB`** / `UILock: 00000000 -> 41000000 => 00000000` / `Black level: 2247` / `Setting up buffers (frame size 3.5MB, fullres size 4.3MB)` / `Trying double buffering (shoot, full size 4.3MB)…` / `Using double-buffering (frame size 3.5MB, wasted 16kB).` / `0?4?0220: 28MB after full-res buffer.` / `35 slots from shoot_malloc.` / **`Allocated 40 slots.`** / `Black level: 2226` / `Black level: 2104`. Tail box: `No memory suites.` ×2 (LCD-refresh ghost of the older frame) |
| **18:28:13** | **REC ACTIVE** — red movie icon top-right, `00:00`, `~60.0MB/s` write-rate readout | Ghosted block ending: `…Allocated ?? slots.` / **`Starting new recording…`** / **`EDMAC copy resources locked.`** Tail box: `No memory suites.` ×2 (ghost) |
| **18:28:23** | LV, NotifyBox | NotifyBox: **`Flushing buffers… 1 frames left`** (no `Early stop` line visible). Console: ghosted `…copy resources unlocked.` ×2, then ~11 `UILock … (!!!)` lines, then `No memory suites.` |
| **18:28:30** | LV, NotifyBox `Flushing buffers… 1 frames left` | Console: `No memory suites.` ×16 (full window) |
| 18:29:27 | LV idle, no NotifyBox | Console: `No memory suites.` ×16, still scrolling |
| **18:29:39** | **ML menu open — Movie tab** | Menu: `MOV/MP4 time limit  180 min` (selected) / `RAW video  ON, 1920x1080  1.75x`. Footer help: `recording limit` / `makes empty files on ExFAT, ok on FAT32`. Console (drawn over menu footer): `No memory suites.` ×3 **still printing while ML menu is open** |
| **18:30:15** | ML menu — Help tab | `Press INFO — Context help` / `Press Q / PLAY — Open submenu` / `SET / main dial — Edit values` / `⧉ or Zoom In — Edit in LiveView` / `SET at startup — Bypass loading ML` / `Key Shortcuts`. Version footer (occluded): `…on: 2026-08-15.6D2.111` / `…a4 dev` / `…00:43:40 UTC by chris@legion.` Console: `No memory suites.` ×3 |

Notes on legibility: many frames show doubled/overlapping glyphs. That is the phone camera
catching the LCD mid-refresh with two console frames interleaved, not corrupted output.
Where a frame is ambiguous, the same content is legible in an adjacent frame.

## Findings

### (a) `[probe]` lines — NONE captured, and none were capturable

Not a build problem. Mechanism:

- `shoot_malloc_autodetect()` (ml/src/exmem.c:207-241) probes in 4 MB steps from 4 MB upward
  and prints one `[probe]` line per step. A 135 MB result means `tested_size` reached 132 MB
  (135 = 132 + 4 backup − 1), i.e. **33 `ok` probes + 1 final `TIMEOUT` = 34 lines**.
- The ML console ring buffer is **21 lines** (`CONSOLE_H 21`, ml/src/console.c:19-25).
- 34 probe lines therefore overflow the console by themselves, and the ~13 lines printed
  immediately afterwards (`srm_malloc_suite(0)…` through `Allocated 40 slots.`) evict what
  is left. In every photo the topmost visible line is `srm_malloc_suite(0)…` — exactly the
  first line printed *after* the probe burst.

**Verdict: the probe instrumentation ran and its output was destroyed by its own volume
before a human could photograph it.** Step 2's discriminator produced zero usable data.
Fix for the next build: replace the per-probe print with one summary line accumulated inside
the loop — e.g. `[probe] max=%d MB, %d steps, slowest %d ms, timeout@%d MB` — or dump probes
to a log file instead of the console.

Consequence: **no timing data, and no `TIMEOUT` observation either way.** Bug 3 hypothesis
(b) (a >100 ms probe silently truncating autodetect) remains untested.

### (b) `Shoot memory:` across cycles — 135 MB every single time, no decay

| Observation | Shoot memory | SRM memory | SRM buffer addr | `srm_malloc_suite =>` | Slots |
|---|---|---|---|---|---|
| 17:49:22 (session start) | **135MB** | 45MB | `65a4c070` | `10f0b0` | 47 |
| 18:25:54 (pre-REC #1) | **135MB** | 45MB | `4c3f0070` | `18ed40` | 40 (35 from shoot_malloc) |
| 18:28:04 (realloc after REC #1) | **135MB** | 45MB | `0?4?2070` | `10ed60` | 40 (35 from shoot_malloc) |

**The 135 → 43 MB shrink from the 16:12 session did NOT reproduce.** Three independent
allocations across two power cycles all returned the identical 135 MB. The SRM buffer address
moved every time (`65a4c070` → `4c3f0070` → `0?4?2070`), reconfirming that Canon's layout
shifts between cycles without affecting the shoot-pool size.

The slot count differing (47 at 17:49 vs 40 at 18:25/18:28) with an identical 135 MB pool is
worth noting — the fullres carve landed at a different address (`45008a40` vs `45008a38` vs
`0?4?0220`), so alignment waste changed, not pool size.

This is evidence *against* a monotonic-decay model, but it is **not** the intended five-cycle
LV→menu→LV test (see verdict for test 2). Bug 3 remains open with the 16:12 43 MB reading
still unexplained and now looking like a one-off rather than a systematic decay.

### (c) `No memory suites.` / `stopped automagically` — dead state CONFIRMED, but re-REC in the dead state was NOT exercised

- `No memory suites.` spam is **fully confirmed twice**: from 18:26:12 continuously through
  18:27:58 (~105 s), and again from 18:28:23 through at least 18:30:15 (~112 s and still
  running when the last photo was taken). It fills the 21-line console at the 250 ms poll rate.
- It persists **while the ML menu is open** (18:29:39, 18:30:15) — the polling CBR keeps
  running and keeps hitting `setup_buffers()` with NULL suites (mlv_lite.c:1566-1569).
- **`stopped automagically` was never seen.** No error dialog, no `EDMAC timeout.` NotifyBox.
- Critically: the second recording (18:28:13) was started **after** a successful realloc
  (18:28:04, `Allocated 40 slots.`), not from the dead state. There is **no photo of a REC
  press while the console showed `No memory suites.`**, and no header-only-MLV evidence. The
  ~100 s gap between 18:26:15 and 18:27:58 is when the re-arm happened.
- What re-armed it: `current_state` (mlv_lite.c:2031-2044) has no exposure term, so the
  f/2.8→f/4.0 and ISO AUTO→800 changes visible at 18:28:04 cannot have triggered it. The
  `raw_video_active` bit (`raw_video_enabled && lv && is_movie_mode()`) is the only plausible
  flip — i.e. LiveView was exited and re-entered (Canon menu, Q screen, or ML menu) during
  that gap. That is exactly the documented workaround, applied unwittingly.

**Verdict: Bug 2's dead state is hardware-confirmed (the suites stay NULL and the poll spams
forever, and only a state flip recovers it). Its sharpest prediction — an instant
"stopped automagically" + header-only MLV on a second REC with no menu flip — is still
unexercised.** Check the card for MLV files written 18:26–18:29: if there are exactly two
valid short MLVs and no header-only file, that settles it negatively for this session.

### (d) `raw inactive: lv=… movie=… gui=…` — NEVER PRINTED, and could not have been

The print (mlv_lite.c:2060) sits inside a guard:

```c
if (!raw_video_active && RAW_IS_IDLE)
{
    if (shoot_mem_suite || srm_mem_suite)   /* <-- guard */
    {
        printf("raw inactive: lv=%d movie=%d gui=%d\n", lv, is_movie_mode(), gui_state);
        ...free_buffers();
    }
    return 0;
}
```

Recording cleanup (mlv_lite.c:3933) already frees **both** suites, so by the time the owner
opened the ML menu at 18:29:39 both pointers were NULL and the branch was a no-op. The line
can only appear when raw goes inactive **while buffers are still held** — i.e. arm raw in LV,
do *not* record, then open the ML menu.

**Verdict: test 4 was run in the wrong order (after two recordings instead of before any),
so it produced nothing. The `lv` vs `is_movie_mode()` question is still open.** No source
change is needed; only the protocol order.

### (e) UILock lines, dialogs, anomalies

- **UILock `(!!!)` denials present and benign, as in the 16:12 session.** Two distinct
  values this time: `00000000 -> 41000001 => 00000000 (!!!)` (srm_shutter_lock around SRM
  alloc, src/exmem.c:479-484) and `00000000 -> 4100017f => 00000000 (!!!)` (UILOCK_EVERYTHING
  during record stop / EDMAC unlock). Non-`(!!!)` writes of `41000000` (UILOCK_NONE) succeed.
  Camera stayed responsive; no livelock; battery never pulled. Patch 0004 holds.
- **`Early stop (9)`** at 18:26:08 (was `(8)` at 16:12). Same buffer-full physics; `9` is
  `last_block_size`, one more frame per write group than last time.
- `Flushing buffers… 3? frames left` → `… 1 frames left` — the flush loop drains correctly,
  so both takes should be valid finalized MLVs.
- The second take (18:28:13) shows a **`~60.0MB/s` write-rate readout** and also early-stopped
  by 18:28:23 — consistent with a UHS-I card far below the 217 MB/s demand at 1080p60 14-bit.
- **No `EDMAC timeout.` NotifyBox** in either take → the alternate `buffer_full` setter at
  mlv_lite.c:2864 stays excluded, as at 16:12.
- No error dialogs, no ERR codes, no reboots.
- `RAW video  ON, 1920x1080  1.75x` — the 1.75x crop mode was in use, worth pinning in future
  sessions since it changes `raw_info.width/height` and therefore slot math.
- Nothing anywhere in the session hints at a Canon fps change; the takes were 50/60p.

## Tests completed vs. skipped / incorrect

1. **Dead-state confirmation — PARTIAL.** ✅ `No memory suites.` spam confirmed on hardware,
   twice, persisting ~100 s each time until a LiveView state flip re-armed it.
   ❌ The load-bearing half — **immediate re-REC without touching menus** — was not performed
   (or not photographed). The second REC at 18:28:13 followed a completed realloc. No
   `stopped automagically`, no header-only MLV. **Re-run: REC → early stop → REC again within
   ~2 s, photograph the console immediately.**

2. **Shrink discriminator — NOT PERFORMED AS SPECIFIED.** ❌ No LV→ML menu→LV ×5 cycle
   sequence exists in the photos. Three incidental allocations were captured, all 135 MB,
   which argues against monotonic decay but does not discriminate hypothesis (a) from (b).
   ❌ `[probe]` output unobtainable by design (34 lines into a 21-line console) — the
   instrumentation itself must be changed before this test can ever succeed.

3. **fps model (Canon 1080/25p) — NOT PERFORMED.** ❌ No 25p recording. Both takes were
   60p (`Early stop (9)`, ~0.4 s of frames, ~60 MB/s observed). Bug 1's mode-dependent-clock
   model is untested. Requires switching the Canon movie fps to 25p, recording, and pulling
   the MLVI header off the card.

4. **Menu-free flag (`raw inactive:`) — PERFORMED IN THE WRONG ORDER, NO DATA.** ❌ The ML
   menu was opened only *after* two recordings had already freed both suites, so the guarded
   print was skipped. **Re-run: boot → enter LV with raw armed → confirm `Allocated N slots.`
   → open ML menu WITHOUT recording → photograph.**

### Net

One of four tests produced usable evidence, and only half of that one. The build was correct;
the failures were protocol order (tests 1 and 4), an omitted procedure (test 2's five cycles,
test 3 entirely), and one instrumentation design flaw (probe output self-flushing the console).

### Required changes before session 3

- **exmem.c**: collapse the per-probe print into a single post-loop summary line, or route
  probes to a log file. As written it can never be read.
- **Protocol order**: test 4 first (before any recording), then test 2 (five clean LV↔menu
  cycles, no recording), then test 1 (record → immediate re-REC), then test 3 (25p).
- Photograph the console **within ~1 s** of each event; at 250 ms poll + 21-line window,
  interesting output survives roughly 5 seconds.
