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
| 001 | qemu-rscmgr-assert | standard | Given stock 6D2 firmware in qemu-eos, when the emulated SD card geometry is varied, then the `RscMgr`/`EstimatedSize.c:1521` assert clears and boot proceeds toward the GUI | **INVALIDATED** ✗ | qemu, boot, sd-card |
| 002 | stub-verification | standard | Given `platform/6D2.111/stubs.S`, when each address is checked against the dumped ROM, then every stub resolves to a plausible function entry rather than a wrong or guessed address | **PARTIAL** ⚠ | rom, stubs, reversing |
| 003 | cheap-wins-scoping | standard | Given the MOV time limit and focus-box/clean-HDMI asks, when the responsible code paths are traced in ML and the 6D2 ROM, then each has a concrete implementation route and effort estimate | **PARTIAL** ⚠ | features, scoping, upstream |
| 004 | ml-boot-in-qemu | standard | Given our built `autoexec.bin`, when loaded in qemu-eos alongside the 6D2 ROMs, then ML's own init runs and its stage of failure is identified | **VALIDATED** ✓ | qemu, ml-build, boot |

### Verdict summary

- **001 INVALIDATED** — the hypothesis was wrong in the most useful way. The SD
  card is not the cause; the assert fires with no card in the machine. Real cause
  is a switch-with-no-default over frame rate receiving garbage (81) because
  qemu-eos has **no 6D2 MPU spells**. The firmware does not even halt — it
  finishes startup via `ErrorSend (101, ABORT)`.
- **002 PARTIAL** — the stub table is sound (135/135 code stubs hit real function
  entries), so bad stubs explain nothing. Located the DryOS kernel image at ROM0
  `0x0100553C`. One fake stub (`LCD_Palette`), 25 DRAM pointers unverifiable.
- **003 PARTIAL** — MOV time limit is a genuine cheap win with ROM addresses now
  independently CONFIRMED; focus-box hide is not cheap (2-5 days, four blockers).
- **004 VALIDATED** — ML boots and prints its own banner. It was never gated on
  001. Fails just after the banner with both cores spinning inside ML's relocated
  image.

**The circular dependency to break:** 001 says QEMU boot needs 6D2 MPU spells;
the spell-capture pipeline says capture needs a complete boot. Neither resolves
inside QEMU — the spells must come off the real body.
