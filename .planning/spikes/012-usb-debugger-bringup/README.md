# Spike 012 — USB debugger bring-up (peek/poke/call on the running 6D2)

**Date:** 2026-08-16
**Type:** execution
**Status:** PLANNED
**Parent:** spike 011 (hardware-in-the-loop scoping)
**Depends on:** nothing to start (phase 1 is desk-only); the candidate stub `0xE04BF152` from spike 011.

## Goal

Turn the CHDK-protocol PTP handler that is **already written** in ML (`ml/src/ptp-chdk.c`, opcode `0x9999`: `GetMemory`/`SetMemory`/`CallFunction`) into a working, live link between the PC and the running 6D2 over the USB cable. Once up, the PC (Claude-driven) can read any register/memory on the real camera, write, and call functions — with no card shuffle per query.

## Validates

Given the candidate `ptp_register_handler = 0xE04BF152` and ML's existing CHDK-PTP handler, when the stub is added, `CONFIG_PTP` is built for the 6D2, and the build is run on the body with a USB host tool, then `GetMemory` returns correct RAM contents from the running camera.

## The catch (why it can't fully self-bootstrap)

- ML loads from the card, so the handler must be **installed once** via a card build + one boot. One physical step, not one-per-query.
- **qemu-eos does not emulate the USB PTP transport** (confirmed: zero PTP source under `hw/eos`). So the stub *address/signature* is QEMU-validatable, but the end-to-end USB round-trip can only be proven on the real body.
- Division of labor: Claude drives the desk/USB side; Chris does the physical actions on request (power-cycle, card swap, plug USB, read the screen). Power-cycles are cheap (seconds) and are also the brick-recovery net.

## Plan

### Phase 1 — QEMU validation (desk, free, iterate freely)
1. GDB breakpoint at `0xE04BF152` during a stock 6D2 boot in qemu-eos. Confirm it is called with `(id, handler_fn, priv)` and fires ~175× (the PTP-opcode registration burst). If it is the wrong function, re-run the ADR/BL hunt (scripts in session scratchpad) for the next candidate.
2. Get `CONFIG_PTP=y` building clean for `6D2.111` with `THUMB_FN(0xE04BF152, ptp_register_handler)` added to `platform/6D2.111/stubs.S`. Resolve any link errors (only this one stub is expected — the other 10 "missing" stubs are unrelated subsystems).

### Phase 2 — one card install (first physical step)
3. Build ONE ML image carrying **both** `CONFIG_PTP` (the USB handler) **and** the peek-to-SD fallback module (see spike 013 / bundled here). One build, two capabilities.
4. Chris: sync the whole `build/zip/ML/` tree to the card, boot the camera once.

### Phase 3 — prove the USB channel (body, read-only first)
5. Plug USB. From the PC, run a chdkptp-style host (`ptpcam --chdk` / chdkptp `luar`) and issue `GetMemory` on a **known RAM address** with a known value. Confirm the value matches.
6. If USB works → the channel is live; card is done until code changes. If it doesn't → the bundled peek-to-SD (spike 013) still harvested readings from the same session; fall back and diagnose USB separately.

### Phase 4 — widen carefully
7. `GetMemory` on the 5 hardware-bound targets (feeds spike 013). Read-only, RAM + known-safe MMIO only.
8. Only after read-only is solid: `SetMemory` / `CallFunction` for targeted tests. **Never** call a function suspected of touching flash/NVRAM (the one unrecoverable-brick vector). Battery-pull recovers any RAM-crash soft hang.

## What this unlocks

- **Live read of any register/memory on the real running 6D2** from the PC — the 5 hardware-bound questions become answerable by reading, not guessing.
- **Write/call to test a theory in seconds** without a build+flash cycle each time.
- **A fast, LLM-drivable loop against real silicon** — the "hardware in the loop" the maintainer named as his top lever, with Chris as the hands and no soldering.
- **A first for ML on any DIGIC 6/7/8 body** — no modern Canon body has ever had working ML PTP memory access. Genuinely novel, upstreamable, and directly useful to kitor/thebilalfakhouri (200D/M50).

## Risks / kill conditions

- `0xE04BF152` is the wrong function (INFERENCE, not proven) → phase 1 catches it at zero cost; re-hunt.
- Canon's PTP responder won't route opcode `0x9999` in the mode ML can enter → phase 3 reveals it; falls back to peek-to-SD (spike 013) which needs no PTP at all.
- `GetMemory` has no address validation — a bad MMIO read can hang the core → MPU ERR80. Mitigate: RAM-only until the map is trusted; Chris power-cycles to recover.

## Deliverable

A working `GetMemory`-over-USB session against the running 6D2, plus a stub-verified `platform/6D2.111/stubs.S` entry for `ptp_register_handler`. Feeds spike 013.
