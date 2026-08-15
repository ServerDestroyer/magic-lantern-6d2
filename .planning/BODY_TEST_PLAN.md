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

## Session 2 — after Track A lands: MPU spell capture run (the critical path)

Blocked on the A/B build (Track A, running). When `card_packages/capture/`
appears in the repo, that package is QEMU-verified and body-ready:

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
