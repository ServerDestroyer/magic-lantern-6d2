---
spike: 001
name: qemu-rscmgr-assert
type: standard
validates: "Given stock 6D2 firmware in qemu-eos, when the emulated SD card geometry is varied, then the RscMgr/EstimatedSize.c:1521 assert clears and boot proceeds toward the GUI"
verdict: PENDING
related: [004]
tags: [qemu, boot, sd-card]
---

# Spike 001: QEMU RscMgr Assert

## What This Validates

**Given** stock 6D2 firmware booting in qemu-eos,
**when** the emulated SD card geometry / image size is varied (and the earlier
`[SDIO] Error` and `[TA10] Irregular TotalSheets` warnings are ruled in or out),
**then** the `ASSERT : Resource/./EstimatedSize.c, Task = RscMgr, Line 1521`
clears and boot proceeds further toward the Canon GUI.

This is the gate blocking Phase A step 4. Until firmware reaches the GUI, there
is no debug rig for any ML feature work.

## Research

Prior run (2026-08-15) established the exact failure point. Boot reaches:

    [EOS] loading ROM0.BIN to 0xE0000000-0xE1FFFFFF
    [EOS] loading ROM1.BIN to 0xF0000000-0xF0FFFFFF
    <<<<< Musa(PU0) Boot Ver 0.19 >>>>>
    K406 READY
    K406 ICU Firmware Version 1.1.1 ( 6.4.9 )
    [SD] Name: QEMU! Size: 247(7bc00)
    [FSU] efat_map_filesys / Attach SC 1 0 80 20 248

then halts at:

    [FSU] AllocateMemoryStrictly For Speed Class!!!
    ASSERT : Resource/./EstimatedSize.c, Task = RscMgr, Line 1521

The assert fires in the resource manager's size estimation immediately after
the filesystem unit performs a **speed-class** allocation for the emulated card.
247 MB is small and QEMU-synthesised — prime suspect.

## How to Run

    nix-shell "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/shell.nix"
    cd /home/chris/ml6d2/qemu-eos/magiclantern
    python3 run_qemu.py 6D2 -q /home/chris/ml6d2/qemu-eos-build

`-q` is required — `get_default_dirs` resolves via `realpath`, which follows the
symlink farm back to the space-containing project path and finds no build dir.

## What to Expect

Baseline reproduces the assert above. A successful variation shows the assert
either disappearing or moving to a different line/task — both are signal.

## Investigation Trail

_Updated as the spike progresses._

## Results

_Pending._
