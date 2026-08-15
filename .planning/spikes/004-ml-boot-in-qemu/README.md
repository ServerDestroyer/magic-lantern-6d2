---
spike: 004
name: ml-boot-in-qemu
type: standard
validates: "Given our built autoexec.bin, when loaded in qemu-eos alongside the 6D2 ROMs, then ML's own init runs and its stage of failure is identified"
verdict: PENDING
related: [001, 002]
tags: [qemu, ml-build, boot]
---

# Spike 004: Boot Our Own ML Build in QEMU

## What This Validates

**Given** the `autoexec.bin` we built from `platform/6D2.111`,
**when** it is loaded in qemu-eos alongside the real 6D2 ROMs,
**then** ML's own init code runs and we identify exactly how far it gets and
where it fails.

This is Phase A step 5 — the debug rig. It was previously assumed blocked on
"build ML first," but the build already exists:
`ml/platform/6D2.111/build/autoexec.bin` (243 KB, 1296 symbols in
`6D2_111.sym`), built 2026-08-15.

## Research

Depends on spike 001. Stock firmware currently halts at the `RscMgr` assert
before the GUI, so ML's boot may not be reachable until that clears. Two
possible outcomes, both useful:

- If ML loads before the assert point, we get ML-specific failure data now.
- If not, this spike is gated on 001 and says so explicitly rather than guessing.

Run this **after** 001 in the same session — both need exclusive use of the
emulator and the SD card image, so they must not run concurrently.

## How to Run

    nix-shell "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/shell.nix"
    cd /home/chris/ml6d2/qemu-eos/magiclantern
    python3 run_qemu.py 6D2 -q /home/chris/ml6d2/qemu-eos-build

with our `autoexec.bin` placed on the emulated card. For source-level debugging,
qemu's `-s -S` plus `arm-none-eabi-gdb` against `build/autoexec` (the unstripped
ELF) and `6D2_111.sym`.

## What to Expect

ML boot messages distinguishable from Canon's, or a clear statement that the
Canon assert fires first and gates this.

## Investigation Trail

_Updated as the spike progresses._

## Results

_Pending._
