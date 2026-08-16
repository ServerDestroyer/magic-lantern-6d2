# Parallel Tracks — session coordination (2026-08-15)

Chris runs multiple concurrent Claude sessions and is merging them. This file is
the track assignment + contention rules. State ground truth lives in
`HANDOFF.json`, `ROADMAP.md`, and `spikes/005-mpu-spell-capture/.continue-here.md`
— read those before starting any track.

## Critical path (sequential — one dedicated session)

**Track A — spike 005 tasks 5→6→7:**
1. A/B build: four debug features commented out in `platform/6D2.111/features.h`
   (comment, don't delete — another session's work), read
   `diag_total_before`/`diag_free_before` via qemu monitor. ~5 min.
2. Fix/work around the 0/0 memory pool based on the A/B result.
3. **Body run (Chris, ~10 min):** sync whole `build/zip/ML/` tree + `autoexec.bin`
   from the same CONFIG_STARTUP_LOG build, boot ~25 s, pull battery, copy
   `DEBUGMSG.LOG`. Do NOT format the card in-camera.
4. Generate real `6D2.h`; register in `qemu-eos/hw/eos/mpu.c` — BOTH the
   #include list (~L38-51) AND the MPU_SPELL_SET list (~L1218-1231).
5. Rebuild qemu, confirm the generic-spells warning (mpu.c:1245) is gone and
   the RscMgr assert clears.

## Independent parallel tracks

- **Track B — spike 004 spin debug:** gdb break at `*0x001037A8`; decide
  boot-d678 `_reloc` bug vs qemu-eos secondary-core gap. Needs a build+boot →
  use a SCRATCH COPY of `ml/`, not the shared tree (see contention rules).
- **Track C — upstream PRs (no hardware, no build contention):**
  (a) MOV time-limit patch (`patches/0001-*`, hardware-tested);
  (b) `outils.py` `ML_PLATFORM_DIR` (`patches/0003-*`);
  (c) `while(!buf)` brick-risk fix in `src/log-d678.c` (collapse the vestigial
  #ifdef at log-d678.c:346-350 first, per HANDOFF.json decisions).
- **Track D — source-only Phase B/C:** finish `FEATURE_MATRIX.md`
  classification; scope clean-HDMI / focus-box-hide (upstream issue #221,
  spike 003 PARTIAL).
- **Track E (optional) — 200D raw video feasibility:** read-only 200D vs 6D2
  platform comparison to cost the port before committing.
- **Track F — Chris only:** body run for Track A; Discord-bot portal setup.

## Contention rules (violations have already caused misdiagnoses)

1. **One session builds `ml/` at a time.** Single build tree, single
   `autoexec.bin`; every rebuild shifts all RAM/BSS addresses any probing
   session depends on. Tracks A and B: serialize, or B works in a scratch copy.
2. **qemu monitor socket is shared**
   (`/home/chris/ml6d2/qemu-eos/magiclantern/qemu.monitor`). `pgrep -f
   qemu-system-arm` before trusting monitor output; never run two QEMUs
   against the same socket.
3. **Never read `sd.qcow2` while qemu runs**; `grep -a` on DEBUGMSG logs.
4. The four uncommitted `platform/6D2.111` files (`consts.h`, `features.h`,
   `internals.h`, `stubs.S`) belong to another session — comment, never delete.
5. Persist anything in `ml/`/`qemu-eos/` worth keeping as a `patches/` entry
   (both clones are gitignored). Patches 0001-0003 are already applied in the
   working trees — `git apply --check --reverse` before any forward apply.
6. Re-resolve every RAM address with `arm-none-eabi-nm` after each rebuild.
7. **`magiclantern_simplified/` is a symlink to `ml/` — same repo.** It is NOT
   a separate clone; treat any operation on either path as hitting the shared
   tree. (Discovered 2026-08-15 when a Track C branch switch clobbered a
   Track A measurement, twice.)
8. **Branch switches in `ml/` count as builds under rule 1** — a checkout
   swaps `platform/6D2.111` headers and empties `build/`.
9. `stash@{0}` in `ml/` ("track-C: found state...") was **verified redundant**
   in the 2026-08-15 evening housekeeping pass (Chris-approved): its diff was
   compared byte-for-byte against patches 0001+0002+0004(+0005) applied to
   `dev@3f24042a4` — the only difference is transient A/B comment wording in
   `features.h`, no functional content. Cleared for Chris to drop
   (`git stash drop` was permission-blocked for the session). Current shared
   tree (after Track A, 2026-08-15 ~16:30): branch `dev`, patches
   0001+0002+0004 applied plus 0005 (the three `FEATURE_SHOW_*` flags
   commented out — they zero the allocator pool in capture builds); `build/`
   holds the packaged capture build (autoexec.bin md5
   969d407d01fc2b140cdfd3b20a9f9f34).
10. Track C builds happened only in isolated worktrees; both worktrees are
    cleared for removal in the housekeeping pass (`trackC-wt2` was reused
    detached-HEAD for the stash verification; the branches live in the shared
    repo refs and as format-patches in `.planning/prs/`). Track C branches:
    `6d2-mov-time-limit`, `d678-prop-wait-denied`, `log-d678-no-brick-spin`.

## Status per track (update in place, one line each)

- A: A/B DONE (2026-08-15) — cause of the 0/0 pool is the three `FEATURE_SHOW_*` flags (leg 1 all-off: pool 9437184/5970756, capture OK; leg 2 MOV-limit-on/SHOWs-off: identical, so MOV limit + consts.h/internals.h/stubs.S all exonerated; which of the three SHOWs, and why, not narrowed). Body-ready capture package in `card_packages/capture/` (md5sums + SYNC_README inside), config saved as `patches/0005`, QEMU-verified twice (DIAG trailer, 23 mpu_send + 3 mpu_recv) — next: Track F body run (Chris), then task 7 (6D2.h + qemu-eos registration)
- B: DONE 2026-08-15 — "spin" was a misattribution: PCs are log-d678.c logger fns (`my_DebugMsg`/`pre_isr_log`/`post_isr_log`; `_reloc` is at 0x15504C), no ML boot bug; stall did not reproduce (4/4 full boots with the exact spike-004 binary) → nondeterministic qemu-eos SGI race, fix proposal in spike 004 README §2026-08-15 (not applied)
- C: DONE (2026-08-15) — 3 build-tested branches in the shared repo (`6d2-mov-time-limit` e6cad78b6, `d678-prop-wait-denied` 7454309f7, `log-d678-no-brick-spin` 2b32a614d, all off dev@3f24042a4, gcc 15.2.1, MOV branch symbol-verified with FEATURE_SHOW_* excluded) + 4 ready-to-post PR docs & patch copies in `.planning/prs/` — next: Chris reviews, pushes to his fork (commands in each PR doc; PR-2 body retest recommended first)
- D: DONE (2026-08-15) — FEATURE_MATRIX classification complete (0 unknowns, counts rebuilt, new cheap-wins ranking); #221 scoped, spike 003 flipped to VALIDATED: LCD half = upstream PR #223's proven 1-line enable, HDMI half = surface/context re-latch, phased sketch + draft diff (UNBUILT) in spike README
- E: not started
- F: pending Chris (body run is the only human step blocking the main line)
- F: raw video — spike 006 opened (2026-08-15 body run: patch 0004 confirmed, first valid 6D2 MLV — 25 frames, finalized), next-test spec + patch-0006 diff ready in `spikes/006-rawvideo-memory/README.md`; scheduled as BODY_TEST_PLAN Session 4, after spell capture
