# Spike Manifest

## Idea

Get Magic Lantern features working on the Canon EOS 6D Mark II (DIGIC 7). The
build loop exists — ML compiles for `6D2.111` and qemu-eos boots stock 6D2
firmware — but the emulator halts on a Canon assert before the GUI, and nobody
has established which ML features actually work on this body or why. These
spikes resolve the unknowns blocking Phase B (feature matrix) and Phase C
(shipping a patch upstream).

Full context: `PLAN_OF_ACTION.md` at the project root.

## Requirements

Established constraints — non-negotiable for any spike or build.

- **Never commit or redistribute Canon firmware.** `roms/` and `Backup SD card/`
  are gitignored. ROM dumps are copyrighted.
- **Do not flash our own build to the body yet.** `platform/6D2.111/README.txt`
  states this code has never been tested on a real cam. QEMU must pass first.
- **Do not format the ML SD card in-camera.** It wipes the card-side
  `EOS_DEVELOP`/`BOOTDISK` boot-sector flags and ML silently stops loading.
- **Build and run QEMU from `/home/chris/ml6d2/`**, never the project dir —
  `qemu-eos/configure` hard-rejects paths containing spaces or colons.
- **QEMU binaries only run inside `nix-shell`** — their libraries live in the
  shell closure defined by `shell.nix`.

## Spikes

| # | Name | Type | Validates | Verdict | Tags |
|---|------|------|-----------|---------|------|
| 001 | qemu-rscmgr-assert | standard | Given stock 6D2 firmware in qemu-eos, when the emulated SD card geometry is varied, then the `RscMgr`/`EstimatedSize.c:1521` assert clears and boot proceeds toward the GUI | PENDING | qemu, boot, sd-card |
| 002 | stub-verification | standard | Given `platform/6D2.111/stubs.S`, when each address is checked against `roms/6D2/ROM1.BIN`, then every stub resolves to a plausible function entry rather than a wrong or guessed address | PENDING | rom, stubs, reversing |
| 003 | cheap-wins-scoping | standard | Given the MOV time limit and focus-box/clean-HDMI asks, when the responsible code paths are traced in ML and the 6D2 ROM, then each has a concrete implementation route and effort estimate | PENDING | features, scoping, upstream |
| 004 | ml-boot-in-qemu | standard | Given our built `autoexec.bin`, when loaded in qemu-eos alongside the 6D2 ROMs, then ML's own init runs and its stage of failure is identified | PENDING | qemu, ml-build, boot |
