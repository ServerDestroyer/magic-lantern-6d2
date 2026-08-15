# Upstream recon: 6D2 raw-video memory / early-stop / fps symptoms

Recon date: 2026-08-15. Repo: reticulatedpines/magiclantern_simplified (default branch `dev`).
Local checkout: `ml/` HEAD = 3f24042a4dfbfba1c4cbfafede50e92a770ed3a9 (2026-08-02 20:05 +0100).
Upstream `pushed_at` = 2026-08-02T19:07:17Z → **our checkout IS upstream HEAD. There are no newer upstream commits to pull.** The only newer activity is open PR #292 (2026-08-06, LJ92 for Digic 4 — irrelevant to 6D2).

## Verdict per symptom

1. **6D2 raw video is known-broken upstream, by the author's own commit message.** Our result (valid 25-frame MLV, no hang) is *better* than the state upstream describes.
2. **The ~179 fps MLVI value is a documented open unknown**: upstream measured that the 6D2 (and 200D) FPS timer clock is *variable* per video mode, while `fps-engio.c` assumes a fixed `TG_FREQ_BASE`. In 59.94p the real clock is ~22.32 MHz but ML computes with 66.8 MHz → reported fps ≈ 3x too high (66.8/22.32 ≈ 2.99; 178.993/59.94 ≈ 2.986). Mechanism matches exactly.
3. **"Early stop (8)" is the buffer-full path, not a write/file error.** No upstream bug reports; the message with a nonzero count is only reachable via `buffer_full` (see code notes below). At ~60 real fps × 3.63 MB/VIDF ≈ 218 MB/s needed vs UHS-I ~40–90 MB/s, 24–48 slots drain in ~1 s → ~25 frames is physics.
4. **"No memory suites." spam and the 135→43 MB shoot_malloc shrink between cycles: no upstream issue, commit, or PR describes this.** This appears to be unreported territory (or 6D2-specific fallout of the known-broken port).
5. **exFAT / file creation: nothing relevant** — and our file creation demonstrably worked.

## Relevant commits (all IN our checkout unless noted)

| sha | date | subject | why it matters |
|---|---|---|---|
| fd11ca5040 | 2025-09-08 | **6D2: broken mlv_lite implementation** | Full message: "Works sometimes, but mostly hangs cam or reboots, when trying to capture raw video. Rarely however, real frames are captured." Upstream's own assessment of the exact code we're running. Sets expectations: our symptoms are the known baseline, not a regression we introduced. |
| 53791dafe0 | 2025-07-10 | 6D2: fps reg a and reg b found, probably | "Not thoroughly tested, this is mostly prep work for... raw video." FPS register discovery on 6D2 is explicitly tentative. Touches `platform/6D2.111/fps-engio_per_cam.c`. |
| ffef459f0d | 2025-07-10 | fps-engio: add some measurements from real cams | Adds the 6D2 comment block in `src/fps-engio.c` (~line 305): `TG_FREQ_BASE 66800000`, measured 59.94p timers 0x1d8/0x314 → **22.32 MHz effective clock**, "Variable, like 200D?". This is the documented root of the 179 fps anomaly: `fps_get_current_x1000()` divides the fixed 66.8 MHz base by timers that were programmed against a ~22.3 MHz clock in 60p → ~3x overreport. mlv_lite copies that into `sourceFpsNom` (mlv_lite.c:3086–3090). |
| 742587f10f | 2026-04-06 | 200D: document some testing around FPS timer | Sister-cam evidence the problem is unsolved: `get_fps_register_a()` marked "This is wrong, probably some shutter related func.", shamem reads return 0, candidate register hunt exhausted. D678 fps register discovery is an open work item upstream. |
| 9d0f59b542 | 2024-08-29 | PROP_VIDEO_MODE: fix for D678 fps | D678 reports fps ×100 (50 → 5000); shows the Canon-side fps plumbing on these cams differs and has already needed one divide-fix. |
| b8126b0168 / d58f4d0e4c | 2024 | 200D fps-engio partial support / per-cam FPS_REG consts | Context for how per-cam fps consts are structured; 6D2 inherits the same partial framework. |
| a950d3ed3b | 2023-07-09 | mlv_lite: more conservative behavior when buffer becomes full | The buffer-full → stop path we hit is deliberate, tuned behavior; not a malfunction. |
| 871827f07d | 2013-08-02 | raw_rec: diagnostic code for early stops | Origin of the "Early stop (N)" diagnostic and its beep-count convention. |
| d261b85ddf | 2023-07-11 | mlv_lite: keep memory allocated during standby (experiment) | Lineage of alloc/free-on-menu behavior. Freeing suites when the ML menu opens (observed `srm_free_suite` on menu open) is expected mlv_lite behavior, later re-tuned by this experiment. |
| 09ac4accbd | 2025-04-09 | mlv_lite: set slot counts better, improve logging | Source of the "Allocated N slots" / slot-count logging we observed; recent slot-math changes are already in our build. |
| f3c7d1aa3e | 2025-04-09 | mlv_lite: check for division by zero | Recent guard in fps/slot math paths; already in checkout. |
| f0dc17db9b | 2025-09-30 | mlv_lite: adapt ilia's card spanning code | Newest mlv_lite change upstream; in checkout. Nothing newer exists for mlv_lite.c. |
| a9e01b972a | 2025-08-29 | 6D2, 7D2: fake allow 10 and 12 bit | 10/12-bit menu options on 6D2 are fake (`EngDrvOut()` is a nop) — only 14-bit is real, matching our 3629056-byte VIDFs. |
| 8d5b5c9d3e | 2025-09-23 | 7D2: mlv_lite raw video, full width only | Sister-port note: their memcpy path tops out ~190 MB/s — same order as what 60p 1080p14 demands; upstream is aware these bodies are bandwidth-marginal. |
| d960d4f375 | 2025-04-09 | raw: 200d, 7d2, 6d2, fix skip_left skip_top | Most recent 6D2-specific raw.c geometry fix; already in checkout. |
| f31c041a01 | 2021-07-25 | mem/exmem: flag to disable SRM, fix guess_free_mem_task leak on SRM error | Only upstream commit about leaked memory in the guess-free-mem path; already in tree. No newer fix exists for the cycle-2 shoot_malloc shrink. |
| ca800c05e9 | 2024-10-11 | srm: make hardcoded size into per cam const | SRM sizing is per-cam const now; our SRM behaved identically both cycles (13 slots), consistent with this being solid. |
| 5794a2634d | 2025-07-11 | 7d2: enable SRM (not fully tested) | D678 SRM enablement is recent and lightly tested upstream. |

## Relevant issues / PRs

| # | state | date | title | why it matters |
|---|---|---|---|---|
| 67 | open | 2022-08-03 | Check SRM functionality on D678 with crop_rec_4k code | Standing upstream doubt about SRM on D678 ("validate if D678 is still broken around SRM"). Zero comments since 2022. Our observation (SRM suite identical across cycles) suggests SRM is fine on 6D2.111; the instability is on the shoot_malloc side. |
| 248 | open | 2025-12-11 | We incorrectly assume FIO functions return pointer | FIO handle 0 is valid but treated as NULL → phantom "file create error" on some D8 cams. Not what we hit today (file creation worked), but the closest upstream item to any file-creation failure class; keep in mind if FIO_CreateFile "fails" later. |
| 292 | open (PR) | 2026-08-06 | enable LJ92 lossless on Digic 4 | Only activity newer than our checkout; irrelevant to 6D2. |
| 285 | open | 2026-07-15 | T2i mlv_lite fails to start 2nd time (Sync Beep = On) | Only upstream "second recording cycle fails" report; root cause is the sync-beep path on Digic 4, not memory. Not our bug, but the closest symptom match to our cycle-2 degradation. |
| 191 | open | 2025-04-02 | 200D: screenshot broken in LV with raw recording ON | Only other D678 mlv_lite runtime issue on file; unrelated to memory. |
| 82 | open | 2023-01-26 | Digic X: new memory handling | Digic X (R5) only — RscMgr2 replaces SRM there. Not applicable to 6D2 (Digic 7). |
| 242/243/183/213 | mixed | 2025 | T3i/T2i/D4-cam SRM & mlv_lite issues | All Digic 4/5 bodies; different memory backend behavior, not applicable. |
| 221 | open | 2025-08-31 | 6D2 focus box autohide | Checked per instruction: comments contain **no** mention of raw/memory. Not relevant. |

## Search coverage (for reproducibility)

`gh api search/issues` and `search/commits` on repo reticulatedpines/magiclantern_simplified for: "No memory suites" (0 issues, 0 commits), "Early stop" (0 issues, 2 commits), shoot_malloc (0 issues, 36 commits — all 2013–2018 era), "memory suite" (0 issues, 5 commits), srm (12 issues, 85 commits), mlv_lite (14 issues), raw video (12 issues), exfat (3 issues — all installer/make_bootable), fps (285 commits, filtered to D678), guess_free_mem (1 commit), fragmentation/"free memory" (4 issues, none relevant). Commit history walked for `modules/raw_video/mlv_lite/mlv_lite.c` (newest: f0dc17db9b), `src/raw.c` (newest 6D2-relevant: 63be9ec2d9 era), and `repos/.../commits?since=<checkout date>` (empty).

## Local code anchors for the observed messages (read-only notes)

- "No memory suites." — `ml/modules/raw_video/mlv_lite/mlv_lite.c:1568`, printed by `setup_buffers()` when `!shoot_mem_suite && !srm_mem_suite`. Repeated spam ⇒ something re-invokes buffer setup after both suites failed/were freed. No upstream report of this.
- "Early stop (%d)" — `mlv_lite.c:3777`. Reached via `abort_and_check_early_stop`; the `buffer_full` check (`mlv_lite.c:3682-3685`) jumps there with `last_block_size` = size of the previous write group (`mlv_lite.c:3699`). Write errors instead take `goto abort` (`mlv_lite.c:3692`), which zeroes `last_block_size` and prints "Movie recording stopped automagically". **Therefore "Early stop (8)" ⇒ buffer_full ⇒ card-too-slow physics, not an I/O failure.**
- `sourceFpsNom` — `mlv_lite.c:3086-3090`, fed by `fps_get_current_x1000()`; 6D2 variable-clock caveat documented at `src/fps-engio.c` ~line 305 (`CONFIG_6D2` block).

## Bottom line

Nothing to pull: we are at upstream HEAD. The 6D2 port's raw video is upstream-labeled "broken"; the fps overreport is a documented, unsolved variable-clock problem shared with 200D (feeds garbage into MLVI and any fps-based estimate, but the early stop itself is write-bandwidth physics); the cycle-2 shoot_malloc shrink and "No memory suites" spam are unreported upstream — worth filing once root-caused locally.
