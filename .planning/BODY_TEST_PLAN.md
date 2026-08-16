# Body Test Plan — batched so each SD-card round trip tests the maximum

Updated 2026-08-15 (evening session). Card sessions are ordered; Session 1 needs
**no PC work at all** — the card already carries the right build.

Standing rules: never format the card in-camera; photograph the console on any
error (into `Pics of debuging/`); after any freeze, pull the battery, don't
half-press-wait.

## Session 1 — DONE 2026-08-15 16:12: raw video retest (patch-0004 build)

Results (full record: `spikes/006-rawvideo-memory/README.md`):

1. Boot sanity: PASS — ML loaded, mlv_lite present, RAW video `ON, 1920x1080 1.75x`.
2. **Patch 0004 confirmed on hardware** — UILock denials printed (`... (!!!)`),
   no livelock, camera responsive throughout, battery never pulled.
3. **First-ever ML raw video on a 6D2**: `footage/M15-1612.MLV`, 25 valid
   1920x1080 14-bit frames, properly finalized, pixel-valid. "Early stop (8)"
   is buffer-full physics (217 MB/s demand vs UHS-I), not a bug.
4. MOV/MP4 time limit: menu item present (180 min); 1-min auto-stop not re-run
   this session (already hardware-confirmed earlier, commit e14469c).
5. Open bugs logged in spike 006: MLVI fps 3x wrong in 50/60p; post-record
   dead state ("No memory suites." spam, second REC would fail); 92 MB
   shoot-pool shrink between alloc cycles.

## Session 2 — DONE 2026-08-15 17:24: MPU spell capture run (the critical path)

Results: capture SUCCEEDED on the first run. `DEBUGMSG.LOG` landed at the
**card root** (not `ML/LOGS/`), 522 KB, DIAG trailer intact, 6530 messages,
0 drops, **71 mpu_send + 104 mpu_recv** (QEMU could only give 23+3). Console
photo shows "Modules loaded" over the sensor-cleaning screen. Extraction
needed a UTF-8 sanitize pass (raw bytes in the body log). Output:
`tools/6D2_spells_body.h` (~175 spells) → `patches/0007` wires it into
qemu-eos. **Verified: stock 6D2 firmware in QEMU no longer hits the RscMgr
assert** — boots on through NFC/LiveView property init. Spike 001 closed.
Card restored to the raw-video daily build afterwards (Session 3 also done).

Original steps for the record:

1. PC: `tools/sync_card.sh <card-mount> card_packages/capture`
   (script verifies md5s; refuses to pass a bad sync).
2. Camera: insert card, **photo mode**, power on, leave it alone ~25 s
   (the logger dumps at ~20 s), then power off / pull battery.
3. PC: copy `ML/LOGS/DEBUGMSG.LOG` off the card into `tools/`
   (it will be renamed `6D2-DEBUGMSG-body.txt` — `.log` is gitignored).
   Remember `grep -a` if you peek at it.

This single 30-second run unblocks: real 6D2 MPU spells → qemu-eos 6D2 support
→ the RscMgr assert fix → QEMU as a usable debug rig for everything else.

## Session 3 — restore the daily build

After Session 2: `tools/sync_card.sh <card-mount>` (defaults back to the live
`ml/platform/6D2.111/build/zip`). Card is then back on the raw-video debug build.

## Session 4b — spike 006 retest with rev-2 instrumentation (READY, card sync pending)

Session 4 (2026-08-15 18:25) ran the correct build but only 1 of 4 tests
yielded data — two tests were unrunnable by construction (34 probe lines
self-evicted from the 21-line console; `raw inactive:` guard already false at
menu time) and 25p was impossible (camera is NTSC). All fixed in patch 0006
rev 2 (single `[probe]` summary line; `No memory suites.` now prints
`lv/movie/gui/rawact/rec/suites` at 1 Hz; measured-fps MLVI header stamp).
Autoexec md5 `54eb1339…`, mlv_lite.mo `ca38b52a…`. Instructions below use the
control names from `docs/6D2_CONTROLS.md`.

Prep (camera, once): MENU → `[z4]` tab → **Movie Servo AF** → **Disable**
(default is Enable and it refocuses mid-take).

1. **Dead-state:** Flip the **Live View shooting / Movie shooting switch**
   (the collar around START/STOP on the back) to the **movie-camera icon**.
   Movie rec. size **1920 59.94p**. Erase button (trash icon) → ML menu →
   Movie → RAW video ON → Erase again to close. Press **START/STOP** to
   record, let it stop by itself, then **immediately press START/STOP again
   touching nothing else**. Photograph the console — the money line is
   `No memory suites. lv=… movie=… gui=… rawact=… rec=… suites=0/0`.
2. **Shrink probe:** Press the **Erase** button to open the ML menu, then
   again to close, five times. Photograph `Shoot memory: X MB` and the single
   `[probe] max …MB steps … slowest …ms@…MB last …` line each cycle.
3. **True 25p:** MENU → yellow **`[53]` Set-up 3** → **Video system** →
   **For PAL**; then MENU → red **`[z1]`** → **Movie rec. size** → **1920
   25.00p** (it resets when Video system changes). Record raw ~10 s.
   Afterwards switch Video system back to **For NTSC**.
4. **Free-branch flag:** With RAW video still ON and not recording, flip the
   **Live View shooting / Movie shooting switch back to the still-camera
   icon**. Photograph the `raw inactive: lv=… movie=… gui=…` line (this is
   the moment the guard is true — NOT when opening the menu).

Bring back: console photos into `Pics of debuging/` + all new `.MLV` files.
The 25p MLV also validates the new measured-fps header (expect ≈25000/1000).

## Session 4 — raw video follow-up (spike 006 next-test)

After Session 2/3 — spell capture stays first priority. Needs a PC build first:
patch 0006 (four diagnostic edits, exact diff in
`spikes/006-rawvideo-memory/README.md` §NEXT TEST), then `tools/sync_card.sh`.
On camera, in strict order, console photos into `Pics of debuging/`:

1. **Dead-state check:** record raw 1080p60, let it early-stop, immediately
   press REC again with no menu touch. Expect instant "stopped automagically"
   + header-only MLV + persistent "No memory suites." (Bug 2 confirmed).
2. **Shrink discriminator:** LV→ML menu→LV five times, photograph
   `Shoot memory: X` + the new `[probe]` lines each cycle. Monotonic decay =
   Canon-side retention; any TIMEOUT/recovery = autodetect truncation.
3. **fps model:** Canon 1080/25p, record raw. Expect MLVI ≈ 25000/1000 and a
   ~5x longer take.
4. **Menu-free flag:** photograph the new `raw inactive: lv=... movie=...`
   line when opening ML menu.

No battery pull expected. Bring back photos + all `.MLV` files.

## Not camera work, still only-Chris

- Send the drafted Discord DM to the ML admins (`discord-bot/DM_TO_ADMIN.md`) —
  the read-only logger bot is built and waiting on the invite.
- When the upstream PR branches are ready for review (`.planning/prs/`), read
  the PR bodies and decide which to push under your GitHub account.
