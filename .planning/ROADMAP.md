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
| 4 | qemu-eos boots stock firmware | **PARTIAL** | Boots to `K406 ICU Firmware Version 1.1.1`, halts at `ASSERT : Resource/./EstimatedSize.c, Task = RscMgr, Line 1521` → spike 001 |
| 5 | Boot our ML build in QEMU | **IN FLIGHT** | Unblocked by step 2 being complete → spike 004 |

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
| 9 | Scope the two cheap wins (MOV time limit; focus box / clean HDMI, issue #221) | **IN FLIGHT** → spike 003 |
| 10 | Work a target: reproduce in QEMU → find the Canon function → patch → test in QEMU → test on body → PR upstream | Not started |
| 11 | Evaluate porting 200D raw video to 6D2 | Not started — biggest prize, biggest cost |

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
