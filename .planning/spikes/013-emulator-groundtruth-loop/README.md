# Spike 013 — Emulator ground-truth loop (real values → faithful qemu-eos)

**Date:** 2026-08-16
**Type:** execution
**Status:** PLANNED
**Parent:** spike 011. **Pairs with:** spike 012 (the read channel).
**Depends on:** the *desk* half needs nothing; the *body* half needs spike 012's USB channel (or the bundled peek-to-SD fallback).

## Goal

Use the ability to read the real 6D2 to make qemu-eos faithful: replace the emulator's guessed/zeroed values with measured ones, and answer the open questions — most in emulation, a few from the body. Each real reading permanently shrinks how much the camera is needed.

## Two tracks (run in this order; track A needs no camera)

### Track A — desk-only, start immediately (no camera, no risk)
Per the spike 011 emulator agent, most open unknowns are answerable in QEMU with GDB + monitor `pmemsave`/`xp` + `-d` flags — many with runs the docs already scripted:
- `PU1_INVESTIGATION.md` §6: the `0xE0494208` non-return bisect; who gives the PU1Wait semaphore (watchpoint on `0x41F0+0x38`); the ShtCap handle (`break 0xDF00B450; print r4`); EngInit dispatch (`-d calls`).
- `ASSERT_INVESTIGATION.md` §6: property-buffer→struct trace (`break 0xE0202312`); is `0x7D0` correct (one boot with the real Movie-group payload from `mpu_spells/6D2.h:12`); `patch_200D` question (`-d romcpy`).
- `model_list.c` 6D2 fields: `current_task_addr=0x28` (verify via `-d tasks`); the MPU/UART-interrupt values (already exercised by every boot).

### Track B — body reads, batch them (needs spike 012 or peek-to-SD)
The genuinely hardware-bound set (only these 5). Prepare all addresses in QEMU first, then harvest in as few camera sessions as possible:
1. **Unmodelled MMIO values** — the gyro/IS word at `0xD9008696` (MEMDIV region returns 0 for never-written addrs), plus whatever the `0xE0494208` bisect points at. Read via `GetMemory` / peek-to-SD; cross-reference with `-d io_log`'s register list.
2. **Physical constants with no ROM source** — TG_FREQ_BASE-class timer frequencies (`fps-engio.c:248-280`). NOTE: some (timer A) are write-only on the real chip and cannot be read back even here — flag those as permanently unmeasurable.
3. **Peripheral identity** — the I2C device at address 0x64; the nature of the `0x82100000` region.
4. **One supplementary MPU capture** — only if the replayed Movie-group payload proves not to carry PROP_MOVIE_PARAM.
5. **Final on-body safety validation of autoexec.bin** — the one item that can never move to the desk.

### The feedback step (what makes the loop self-reducing)
For each measured value → edit the corresponding qemu-eos handler / `model_list.c` field to return the real value → the emulator behaves like the real camera at that point → more of Track A becomes answerable → fewer future Track B reads needed. The loop tightens with every reading.

## What this unlocks

- **A faithful 6D2 emulator** — the guessed fields and zeroed MMIO get real values; qemu-eos stops lying.
- **The open questions answered** — potentially pushing stock firmware (and ML) further in QEMU past the current ceiling.
- **A shrinking must-use-hardware set** — camera dependence drops over time; the fast/safe desk loop absorbs more of the work.
- **General emulator gains** — several qemu-eos corrections are not 6D2-specific; they improve the rig for every DIGIC 7/8 body, which is the environment the LLM-brute-force workflow runs in.

## Deliverable

A set of qemu-eos patches replacing guessed/zeroed values with measured ones, an updated open-questions ledger in `PU1_INVESTIGATION.md` / `ASSERT_INVESTIGATION.md`, and a shortened "genuinely needs hardware" list.
