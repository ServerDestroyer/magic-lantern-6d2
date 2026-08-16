# Spike 011 — Hardware-in-the-loop on the 6D2 with what's on hand

**Date:** 2026-08-16
**Status:** SCOPED (6-agent parallel exploration + 2 red-teams complete)
**Renumbered:** was 010; yielded 010 to the concurrent `010-jtag-digic7` spike (hardware/JTAG path). This spike is the software / no-solder path. Execution spikes spawned from it: **012** (USB debugger bring-up), **013** (emulator ground-truth loop), **014** (UART crash console, deferred).
**Question:** Can we get interactive hardware-debug / live register access on the *real* 6D2 using only camera + USB + WiFi + Bluetooth + PC — no soldering, no donor board? If not, what's the cheapest path that actually works, and what's the highest-value thing buildable short of full JTAG?

---

## Verdict (read this first)

**Reframe, from both red-teams:** we do **not** need hardware-in-the-loop to move the project forward right now. Stock firmware boots in QEMU, every shipped feature (MOV limit, raw video, re-arm, dual-ISO) landed without a debug port, and the emulator agent showed that **most** open questions are answerable at the desk in QEMU — only ~5 items are genuinely hardware-bound. So this spike is about **building a capability / contributing to the maintainer's named lever (hardware in the loop)**, not unblocking the roadmap. Frame it that way honestly, to ourselves and to upstream.

**Within "what can we do without soldering," ranked by value-per-effort:**

| # | Path | Verdict | Cost | Risk |
|---|------|---------|------|------|
| 1 | **On-camera peek-to-SD ML module** | **DO FIRST** — fastest real-hardware readback | ~tens of lines, all pieces proven on 6D2 | battery-pull only |
| 2 | **USB peek/poke/call debugger** | The prize; one QEMU pass from testable | RE done (candidate found) + validation | brick vector, mitigable |
| 3 | **Emulator-first for desk-answerable questions** | Do before any hardware | GDB scripts half-written | none |
| 4 | **UART (minimal hardware)** | Cheaper than thought, but camera likely comes open | ~$5 read-only adapter + cover off | low, not "no hardware" |
| 5 | **drysh / Mon* via `call()`** | Compiled in ROM, reachability unproven | — | MPU map unknown |
| 6 | **Full JTAG** | Parked — needs donor board + soldering | out of scope by definition | high |

**Two free moves both red-teams endorse:** (a) ask kitor / names_are_hard on Discord — kitor has DIGIC 8 GDB working and asked for donor boards; the 6D2 pinout could come from collaboration. (b) The `io_trace.c` DIGIC 7 port is *not* a quick win (see below) and is the wrong tool for on-demand peeks — deprioritized.

**Recommended first action:** build the on-camera peek-to-SD module (#1). It reads real hardware today, zero ROM archaeology, and it de-risks path #2 by letting us sanity-check addresses before wiring up USB peek/poke.

---

## The directions, with evidence

### 1. On-camera peek-to-SD module — FASTEST, buildable today
Everything needed is already proven on this exact 6D2:
- `save_mem_to_file(start, size, filename)` — `ml/src/fio-ml.c:816-825`, three-line wrapper over `FIO_Create/Write/CloseFile`, all confirmed-present 6D2 stubs.
- Trigger template already in-tree: `ml/src/debug.c:610-615` — `core_dump_requested` flag checked in a task loop → `save_mem_to_file(...,"COREDUMP.DAT")`. Add a menu item / config int for `(start,size)` and reuse this shape.
- `log_finish()`/`dump_file()` (`ml/src/log-d678.c:472`) already runs on the 6D2 — it captured the 175 MPU spells.

Effort: tens of lines, no new stub. Limitation: not interactive — menu-edit + re-trigger + pull file per address.

### 2. USB peek/poke/call debugger — findable, one QEMU pass from testable
The machinery is fully written: opcode `0x9999`, `GetMemory`/`SetMemory`/`CallFunction` in `ml/src/ptp-chdk.c:115/193/297`. It is dead on the 6D2 only because one firmware stub is missing: `ptp_register_handler`.

**Stub hunt result — strong candidate `0xE04BF152`** (INFERENCE, not proof):
- 3-arg signature `(id, handler_fn, priv)` matching `ml/src/ptp.h:97-107`.
- Reached via Canon's `./PtpMgr/PtpApp/PtpOperation.c` module strings (`AddListOperationFunction`, `GetRegisterPTPOperationCode`, …) resolved by 16-bit Thumb ADR xref.
- Calls `AddListOperationFunction` at `0xE04BF7A0` (16-byte node: id@+8, handler@+12, semaphore-guarded, returns err `0x13` on dup id).
- **Called 175× across ROM0** in tight clusters (27 consecutive sites at `0xE05FA754`, 0xC apart) — the shape of Canon registering all PTP opcodes at boot. This is the decisive signal.
- Stub entry would be `THUMB_FN(0xE04BF152, ptp_register_handler)`.

**The 200D placeholder is NOT a hint:** `platform/200D.101/stubs.S:509` `//NSTUB(0xFF9ED888, ptp_register_handler)` is byte-identical to the DIGIC 4 `50D.109/stubs.S:258` — a copy-paste scaffold, not a DIGIC 7 measurement. Every DIGIC 6/7/8 body in the tree has zero live PTP stub.

**Only `ptp_register_handler` blocks it** — the other 10 "missing" stubs from spike 002 are unrelated subsystems (grepped: zero hits in `ptp*.c`). `fio_malloc`/`ptpPropSetUILock` are ML wrappers / DIGIC-V dead code.

**Validation path (zero risk):** QEMU now boots stock 6D2 firmware, so set a GDB breakpoint at `0xE04BF152` during boot and confirm the call signature/args before ever touching the body. Then add stub → build `CONFIG_PTP` → card test.

**Brick caveats (red-team, stand):** `GetMemory` (`ptp-chdk.c:170`) is a raw `*(uint32_t*)addr` with no validation — MMIO reads can pop FIFOs or hang the bus (→ MPU ERR80, same failure as a JTAG halt). `CallFunction` is arbitrary RCE and the one true unrecoverable-brick vector (can hit flash/NVRAM routines). Discipline: exercise `GetMemory` on RAM only, in QEMU first; never `SetMemory` the vector table (0x0-0x20) or page tables; treat flash-touching functions as off-limits.

### 3. Emulator-first — most open questions are desk-answerable
Per the emulator agent, of every open unknown in `PU1_INVESTIGATION.md` §6 and `ASSERT_INVESTIGATION.md` §6, nearly all are answerable in QEMU with GDB + monitor `pmemsave`/`xp` + `-d` flags — many with runs the docs already scripted (the `0xE0494208` bisect, the PU1Wait giver via watchpoint on `0x41F0+0x38`, the ShtCap handle via `break 0xDF00B450; print r4`). Tooling: `debugmsg.gdb`, `-d io/io_log/calls/tasks`, the real spells in `mpu_spells/6D2.h`.

**Genuinely hardware-bound residue (only these 5):**
1. Authoritative values of unmodelled MMIO — the gyro/IS word at `0xD9008696` (MEMDIV region returns 0 for never-written addrs), and whatever the `0xE0494208` bisect points at — captured via `-d io_log` register list + dm-spy.
2. Physical constants with no ROM source — TG_FREQ_BASE-class timer frequencies (`fps-engio.c:248-280`).
3. Peripheral identity — the I2C device at address 0x64; the nature of the `0x82100000` region.
4. One more MPU capture, *only if* the replayed Movie-group payload (`6D2.h:12`) proves not to carry PROP_MOVIE_PARAM.
5. Final on-body safety validation of autoexec.bin — the one item that can never move to the desk.

### 4. UART — cheaper than assumed, but the camera probably comes open
- 6D2 = FZC-8 connector (JST 08FZC-SM1-GAN-TB, CLAIMED part). Corrected family pinout (topic 7531 posts 38-43): pins **2/3 = ICU RX/TX 1.8V**, **4 = GND**, **6/7 = MPU TX/RX 3.3V**. **Never measured on a 6D2** — inherited from the R/RP/200D family; multimeter-verify before driving anything.
- **Read-only is nearly free and needs no level shifter** (corrects an earlier claim): a plain 3.3V FTDI reads the 1.8V ICU TX out of the box — a1ex confirmed this on the EOS M's identical 1.8V line (3.3V receivers register 1.8V highs). Only *driving* the camera's RX needs a 2×470Ω divider or shifter. So boot-log + DebugMsg capture = a ~$2-5 USB-serial at 115200 8N1.
- **Access on the 6D2 is undocumented.** The 200D (same generation, same FZC-8) is claimed rubber-cover-accessible, but even its clean session began "I took apart the 200D." A 2025 teardown shows the 6D2 rear cover is screws-only (no soldering), one LCD-harness hazard, no visible debug hole. Order of operations: peel the thumb-rest rubber first (2 min, reversible) and look; if nothing, back cover off.
- **What UART uniquely adds over the card log we already capture:** pre-DryOS **bootloader** visibility, and output when the camera **dies before the card flushes** — directly relevant to the CRASH00 / re-arm investigations. (`uart_printf` already stubbed at `platform/6D2.111/stubs.S:284` = `0xe04eb7a0`.) Plus interactive drysh, demonstrated live over UART on family bodies.
- Correction: an interactive **bootloader menu on autoexec return is UNVERIFIED for DIGIC 7** — do not budget on it.
- Physical contact: FZC-8 is 0.5mm pitch, no off-the-shelf mating cable — needle probes, a trimmed 8-way FFC stub, or a custom flex breakout (coon's OSH Park design, ~$6/3).

### 5. drysh / Mon* RPC — in the ROM, reachability unproven
- **drysh strings ARE in `roms/6D2/ROM0.BIN`** (`drysh`, `Dry[LIME]>`/`Dry[MusaPUX]>`/`Dry[ZICO]>` per-coprocessor prompts, `akashimorino` start event). So it's compiled into 1.1.1.
- But nobody has demonstrated reaching it on a 6D2, and interactive use needs UART. Reconciles the A-vs-F conflict: **compiled in (ROM-confirmed), reachability unproven.**
- **Hardware-free angle:** drysh commands + `MonOpen`/`MonRead`/`MonClose` are event procedures, callable from ML `call()` with no UART — the `mpu_dump` module already does exactly this (`ml/modules/dev_tools/mpu_dump/mpu_dump.c`). Blocker: the 6D2's MPU memory map is unknown (hardcoded addrs are for the old TMP19A43 MPU).
- Factory mode also present (`FACTORY ADJUSTMENT MENU`, card-triggered via `Factory.mac`) but writes calibration NVRAM — risky, undocumented for the 6D2.

### 6. Full JTAG — parked
Off the "no soldering / no donor board" table by definition. When wanted, kitor's DIGIC 8 recipe (published OpenOCD dual-Cortex-A9 config, IDCODE `0x4ba00477`, resistance-signature pin-ID) transfers to the 6D2's identical dual-Cortex-A9 at 1.8V. See memory `jtag-on-digic`.

---

## Red-team summary

**No-hardware-claims red-team:** USB-PTP path was LIKELY-FATAL *as stated* (stub unknown, needs RE, never built on a modern body) — but the stub hunt then produced a candidate, moving it to "validatable." `GetMemory` no-validation and `CallFunction` brick vector are real (SERIOUS-RISK). UART-under-cover is extrapolation, not verified for the 6D2 (SERIOUS-RISK). drysh as a *planning assumption* was LIKELY-FATAL (no EOS demonstration) — tempered by the ROM strings being present.

**Framing red-team:** the open questions live register access would answer are curiosities, not roadmap blockers — every shipped feature came without a debug port. "No soldering, no donor board" rules out essentially every full-HITL path. **Collapse to three cheap in-scope actions:** ask about kitor's thread (free), fix `io_trace.c` DIGIC 7 branch (software-only), glance at whether the 6D2 rubber cover hides a UART pad before any screwdriver. Correctly flagged that `docs/jtag-research.html` is stale (predates the kitor-thread retrieval) and that the "taken from 200D" comment is on the D8 entries, not the 6D2 (`model_list.c:618-627` has one fixme only). NOTE: its "kitor premise unsupported" was itself based on the stale artifact — the retrieved thread confirms kitor's D8 GDB session + donor-board ask.

**io_trace.c reality check (stub-hunt agent):** NOT a quick port. ~11 of 17 `CONFIG_DIGIC_VI` sites are gate-widening, but ~6 program a Cortex-R **MPU** protection region that does not exist on the 6D2's Cortex-A **MMU** — the equivalent is patching a page-table entry + TLB invalidate (reuse `change_mmu_tables` @ `0xe04dcad2`), a new mechanism, not an `#ifdef` swap. Plus an unknown TCM scratch-stack layout for DIGIC 7. Comparable to spike 008's multi-session RE, and it's a passive full-capture tool, wrong for on-demand single-register peeks.

---

## Next actions (ranked)

1. **Build the on-camera peek-to-SD module** — reuse `save_mem_to_file` + the `core_dump_requested` pattern. Reads real hardware today, de-risks path #2.
2. **Validate `0xE04BF152` in QEMU** — GDB breakpoint during stock boot, confirm the `(id, handler, priv)` signature and the 175 call sites. Zero risk.
3. If validated: add `THUMB_FN(0xE04BF152, ptp_register_handler)`, build `CONFIG_PTP`, card-test GetMemory (RAM only) over USB.
4. **Ask kitor / names_are_hard** about the DIGIC 8 thread and 6D2 collaboration — free, possibly dominant.
5. Work the desk-answerable questions in QEMU (emulator agent's classification) before spending any hardware effort.
6. Passive-check the 6D2 rubber cover for a UART pad — deferred, needs the body in hand.

## Provenance
6 parallel agents (fable: native channels, UART, emulator leverage; sonnet: stub hunt, both red-teams). Scratch disassembly scripts: session scratchpad `adr_scan.py`, `bl_scan.py`. Candidate address `0xE04BF152` is INFERENCE pending QEMU validation.
