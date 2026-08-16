# Roadmap — Magic Lantern on the Canon EOS 6D Mark II

Narrative context, build traps, and reasoning live in `PLAN_OF_ACTION.md`.
This file is the status ledger: what is done, what is in flight, what is next.

**Milestone 1 definition of done** (from `PLAN_OF_ACTION.md` §4):

1. QEMU boots stock 6D2 firmware **and** our ML build.
2. `FEATURE_MATRIX.md` exists with a reason attached to every missing feature.
3. One upstream-quality patch opened for a cheap target.

## Phase A — build the loop

| # | Step | Status | Evidence |
|---|------|--------|----------|
| 1 | ARM toolchain + deps | **DONE** | `shell.nix` (project-local, deliberately not in the NixOS system config) |
| 2 | Build ML for 6D2 | **DONE** | `ml/platform/6D2.111/build/autoexec.bin`, 243 KB, 1296 symbols in `6D2_111.sym`, built 2026-08-15 12:11 |
| 3 | Dump ROMs from camera | **DONE** | `roms/6D2/{ROM0,ROM1}.BIN`, dumped 2025-09-29, verified genuine |
| 4 | qemu-eos boots stock firmware | **DONE (2026-08-15 body capture)** | Body run captured 522 KB `DEBUGMSG.LOG` (6530 msgs, 0 drops, 71 mpu_send + 104 mpu_recv) → `patches/0007` adds real `mpu_spells/6D2.h` (~175 spells) to qemu-eos. Stock boot verified: **no RscMgr assert, no Irregular TotalSheets, no ErrorSend**; firmware still progressing (NFC/LiveView props) at 90 s kill. Artifacts: `tools/6D2-DEBUGMSG-body.txt`, `tools/6D2_spells_body.h`. Closes spike 001. |
| 5 | Boot our ML build in QEMU | **DONE — ML boots** | `autoexec.bin` loads (`File size : 0x3BA40` = our exact byte count), `boot-d678.c` relocation works, ML prints its own banner from `boot_post_init_task`. Fails just after: both cores spin at `0x001037A8`/`0x0010390C` inside ML's relocated image. → spike 004 |

### The blocker, stated once — RESOLVED 2026-08-15

**Resolved by the Session 2 body run:** real 6D2 MPU spells captured on the
body, extracted to `patches/0007-qemu-eos-6D2-mpu-spells.patch`, verified in
QEMU (RscMgr assert gone, stock firmware boots onward). QEMU is now a usable
debug rig. History below kept for the record.

QEMU cannot boot the 6D2 far enough to be a debug rig until qemu-eos has **6D2
MPU spells**. The loop only breaks by capturing from the real body — see
`capture_mpu_spells.md` and spike 005.

**Corrected 2026-08-15:** this previously said capture was blocked by "a
log-buffering bug in `src/log-d678.c` (MPU lines reach the QEMU console but not
the card-side `DEBUGMSG.LOG`)". No such bug exists — that was a measurement
error, twice over (reading `sd.qcow2` before qemu flushed it, and `grep` treating
the NUL-padded log as binary). The logger is measured correct and a complete
102744-byte card log with 23 `mpu_send` was captured.

The reason a body run is still required is different and structural: qemu-eos
replays its own **generic** MPU model (`[MPU] FIXME: using generic MPU spells for
6D2`), so spells captured inside QEMU are the emulator talking to itself. Capture
does *not* require a complete boot — the log ran to t=19.5 s guest, long past the
assert at ~0.3 s. Spike 005's live blockers are an allocation failure at
`log_start()` and an ISR-hook clash with `tskmon`.

Note this does **not** block Phase C's MOV time-limit patch, which is verifiable
directly on the body and cannot brick anything.

## Phase B — establish what is missing and why

| # | Step | Status |
|---|------|--------|
| 6 | Enumerate 6D2 feature state from source | **IN FLIGHT** |
| 7 | Classify the reason for each gap | **IN FLIGHT** |
| 8 | Produce `FEATURE_MATRIX.md` | **IN FLIGHT** |

Classification vocabulary — every gap gets exactly one: *stub missing*,
*subsystem unported*, *hardware/firmware differs*, *never enabled/tested*.
The last category is where the cheap wins hide.

## Phase C — pick targets and ship

| # | Step | Status |
|---|------|--------|
| 9 | Scope the two cheap wins (MOV time limit; focus box / clean HDMI, issue #221) | **DONE** → spike 003 + verification |
| 10 | Work a target: patch → test on body → PR upstream | **MOV TIME LIMIT CONFIRMED ON HARDWARE (2026-08-15)** — stopped at 60 s with limit set to 1 min. Debug displays also confirmed. `patches/0001`. **UPSTREAM PRs OPEN (2026-08-15):** [#294](https://github.com/reticulatedpines/magiclantern_simplified/pull/294) MOV time limit, [#295](https://github.com/reticulatedpines/magiclantern_simplified/pull/295) D678 prop-wait fix, [#296](https://github.com/reticulatedpines/magiclantern_simplified/pull/296) log-d678 no-brick-spin + gcc15 fix. All from fork ServerDestroyer/magiclantern_simplified. |
| 11 | ~~Evaluate porting 200D raw video~~ **Finish existing raw video** | **RAW VIDEO RECORDED ON THE BODY (2026-08-15 16:12 — first ever on a 6D2).** `footage/M15-1612.MLV`: 90.7 MB, MLV v2.0, 25 clean 1920x1080 14-bit frames, finalized header, full metadata chain. Patch 0004 (D678 denied-prop-wait fix) confirmed on hardware — no livelock, no freeze. Remaining defects → spike 006 (`.planning/spikes/006-rawvideo-memory/`): shoot_malloc pool shrink 135→43 MB, "Early stop (8)" / "No memory suites." after stop, garbage MLVI sourceFps. Body-run order: `.planning/BODY_TEST_PLAN.md`. |

## Active spikes

See `.planning/spikes/MANIFEST.md`. Spikes 001-004 resolve the unknowns gating
Phase A step 5 and Phase C step 10.

## Standing constraints

- Canon firmware is copyrighted — `roms/` and `Backup SD card/` are gitignored,
  never commit or redistribute.
- Do not flash our own build to the body until QEMU passes; the platform README
  says this code has never run on a real camera.
- Do not format the ML SD card in-camera — it wipes the card-side boot flags.
- Build and run QEMU from `/home/chris/ml6d2/`, never the project path.
