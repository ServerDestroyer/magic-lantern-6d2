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

## Status per track (update in place, one line each)

- A: not started (A/B untried) — next: features-off build
- B: not started — next: gdb break at spin address
- C: not started — next: fork + branch for MOV time-limit PR
- D: FEATURE_MATRIX.md exists, classification IN FLIGHT; #221 scoping PARTIAL
- E: not started
- F: pending Chris (body run is the only human step blocking the main line)
