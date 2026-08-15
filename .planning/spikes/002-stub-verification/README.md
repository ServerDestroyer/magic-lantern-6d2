---
spike: 002
name: stub-verification
type: standard
validates: "Given platform/6D2.111/stubs.S, when each address is checked against roms/6D2/ROM1.BIN, then every stub resolves to a plausible function entry rather than a wrong or guessed address"
verdict: PENDING
related: [004]
tags: [rom, stubs, reversing]
---

# Spike 002: Stub Verification Against the Real ROM

## What This Validates

**Given** the stub table in `ml/platform/6D2.111/stubs.S`,
**when** every address is cross-checked against the actual dumped ROM
(`roms/6D2/ROM1.BIN`, and `ROM0.BIN` where relevant),
**then** each stub either resolves to a plausible ARM/Thumb function entry point
or is flagged as wrong, stale, or never-verified.

`platform/6D2.111/README.txt` admits the port "has never been tested on a real
cam." Wrong stubs are the most likely cause of both the QEMU failures and any
future crash on the body. This produces the evidence base for Phase B's
"stub missing / wrong" classification — and it is pure static analysis, so it
carries zero risk to the camera.

## Research

Ground truth already established about the ROMs:

- `ROM0.BIN` = 32 MiB, maps to `0xE0000000-0xE1FFFFFF`
- `ROM1.BIN` = 16 MiB, maps to `0xF0000000-0xF0FFFFFF`
- DryOS marker `akashimorino` present; version string `1.1.1`
- `FIRMWARE_ID 0x80000406`
- Valid Thumb-2 code at file offset `0x40000`, which corresponds to the
  Makefile's `MAIN_FIRMWARE_ADDR 0xE0040000`

So: file offset = address − 0xE0000000 for ROM0, − 0xF0000000 for ROM1.

## How to Run

Static analysis only — no emulator, no camera. Use the ARM toolchain from
`shell.nix` (`arm-none-eabi-objdump`) plus direct byte inspection.

## What to Expect

A per-stub verdict table: address, symbol, which ROM it lands in, whether the
bytes there look like a function prologue, and a confidence rating.

## Investigation Trail

_Updated as the spike progresses._

## Results

_Pending._
