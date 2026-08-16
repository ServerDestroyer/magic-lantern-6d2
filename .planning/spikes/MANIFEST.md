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
| 005 | mpu-spell-capture | standard | Given a startup-log ML build, when its `DEBUGMSG.LOG` is fed to `extract_init_spells.py`, then a valid `mpu_spells/6D2.h` is produced — the artifact 001 says qemu-eos is missing | **VALIDATED** ✓ | qemu, mpu, logging, upstream, body-test |
| 006 | rawvideo-memory | standard | Given the first raw recordings on the body, when each defect (garbage fps header, dead state freeze, pool shrink) is instrumented and retested, then each is root-caused and fixed or downgraded | **VALIDATED** ✓ | raw-video, body-test, mlv |
| 007 | dual-iso-scoping | scoping | Given the dual_iso module and our ROM dump, when per-model requirements and D7 prior art are mapped, then the port difficulty and first action are known | **VALIDATED** ✓ | dual-iso, rom, scoping |
| 008 | lossless-compression-scoping | scoping | Given mlv_lite's lossless path and the 6D2 ROM, when the encoder subsystem and per-body needs are mapped, then feasibility, viable modes, and effort are known | **VALIDATED** ✓ | compression, rom, scoping |
| 010 | jtag-digic7 | scoping | Given kitor's confirmed DIGIC 8 JTAG method, when the same technique is applied to a DIGIC 7 (6D2) donor body, then a live IDCODE is found and a debug session established | **PLANNED** — hardware work not started | jtag, hardware, digic7, scoping, planning |
| 011 | hardware-in-the-loop | scoping | Given camera + USB + PC (no soldering, no donor board), when every no-solder path to live 6D2 register access is mapped and red-teamed, then the viable paths are ranked with first actions | **VALIDATED** ✓ — 6-agent sweep + 2 red-teams; USB peek/poke/call is the spine, gated on one stub | hitl, usb, ptp, scoping, planning |
| 012 | usb-debugger-bringup | execution | Given the `0xE04BF152` stub candidate + ML's existing CHDK-PTP handler, when the stub is added and `CONFIG_PTP` is built and run on the body, then `GetMemory` returns correct RAM from the running 6D2 over USB | **PLANNED** — phase 1 (QEMU stub validation) is desk-only, ready to start | usb, ptp, debugger, reversing, body-test |
| 013 | emulator-groundtruth-loop | execution | Given a read channel to the real 6D2 (spike 012 or peek-to-SD), when measured register values replace qemu-eos's guesses, then the emulator becomes faithful and the must-use-hardware set shrinks | **PLANNED** — Track A (desk) startable now; Track B needs the read channel | emulator, groundtruth, feedback, reversing |
| 014 | uart-crash-console | execution | Given the 6D2's ICU UART, when read-only serial capture is established, then output is visible when the camera dies before the card flushes (CRASH00/re-arm) | **DEFERRED** — needs opening the camera; pull off the shelf when a freeze produces a blank card log | uart, crash, hardware, deferred |

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

- **005 PARTIAL** — the capture pipeline works end to end and produced a real
  23-spell `mpu_init_spells_6D2[]`, but from *synthetic* traffic, so it cannot
  fix QEMU. Two live blockers: `log_start()`'s allocation now fails,
  and the cause is not yet established — the controlling A/B is untried.

**The dependency to break — restated 2026-08-15.** 001 says QEMU boot needs 6D2
MPU spells. 005 refines this: the capture *mechanism* is not the limit (ML's dump
task ran at t=19.5 s and wrote a complete 102744-byte file), but **both**
obstacles stand — qemu-eos replays a generic MPU model, so anything captured
inside QEMU is the emulator talking to itself, *and* boot stops early enough that
22 of 23 spells land in the 270 ms before the assert. The spells must come off the
real body.
