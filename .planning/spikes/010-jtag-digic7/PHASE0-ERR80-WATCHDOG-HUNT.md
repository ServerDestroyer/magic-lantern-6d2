---
spike: 010
phase: 0
name: ERR80 / MPU-watchdog static ROM hunt
date: 2026-08-16
scope: static ROM research only — no camera, no QEMU run, no hardware
inputs: roms/6D2/ROM0.BIN (ICU, 32 MB, maps @0xE0000000), ml/platform/6D2.111, qemu-eos/hw/eos
verdict: MPU-side ERR80 trigger is NOT in the dumped ROMs (wrong chip). No DIGIC-5-style
         suppressible watchdog register found on the ICU side. Halt-debug is feasible only
         as "peek-and-resume inside a ~10 s window" unless the MPU serial link is kept fed.
---

# Phase 0 — ERR80 / MPU-watchdog static hunt (6D2, DIGIC 7)

## 0. TL;DR

- **The blocker cannot be solved the DIGIC-5 way.** DIGIC 5's watchdog fix was writing 0 to an
  *ICU-side* MMIO register (`0xC0410000`). The 6D2 blocker is a *different, MPU-side* watchdog,
  and the MPU is a physically separate microcontroller whose firmware **is not in ROM0/ROM1**.
  You cannot find or disable it by reading the ICU ROM. Hunting ROM0 for "the MPU watchdog"
  is a category error — it is the wrong chip.
- **No suppressible ICU-side watchdog register was found** analogous to DIGIC 5's `0xC0410000`.
  The DIGIC-5 address does appear in ROM0, but only as a dead entry inside a hardware-address
  table (see §2.3) — not as a live, hammered control register. DIGIC 7 remapped the whole
  `0xC0xxxxxx` space.
- **No MPU "keep-alive"/"disable-watchdog" spell exists** in ML's reverse-engineered MPU
  protocol. The only timeout-ish properties are inactivity auto-poweroff, which is unrelated.
- **Net feasibility:** halt-based JTAG on the 6D2 is workable for short interactive windows
  (< ~10 s halt, then resume before the MPU trips ERR80). ERR80 is recoverable (battery pull),
  not a brick. Indefinite halts need a hardware shim that answers the MPU serial link, or a
  per-core halt that leaves the MPU-comm core running — both are Phase-1+ hardware problems.

## 1. What ERR80 is and its fault path

Two-processor architecture (well established in ML, re-confirmed by web cross-check
2026-08-16):

- **ICU** — the main ARM running DryOS. On DIGIC 7 this is a dual Cortex-A9. **This is the chip
  ROM0.BIN / ROM1.BIN come from**, and the chip JTAG halts.
- **MPU** — a *separate* microcontroller (historically Toshiba TX19A-class; later Canon parts
  differ but the two-chip split holds). It owns power sequencing, the shutter/mirror, the
  physical buttons, and **the top-panel LCD**. Its firmware lives on the MPU, **not** in the
  ICU ROM dump.
- The two talk over a serial link. In ML/qemu terms this is the **MPU messages ("spells")**,
  carried by the **SIO3** and **MREQ** interrupts (`qemu-eos/hw/eos/mpu.h`:
  `mpu_handle_sio3_interrupt`, `mpu_handle_mreq_interrupt`; MREQ MMIO block `0xC0203000` in
  `qemu-eos/hw/eos/eos.c:627`).

Error taxonomy:
- **ERR70** — mechanical/shutter fault, or an invalid Property written to NVRAM. ICU-detectable.
- **ERR80** — *"a passive watchdog where hardware detects that firmware is no longer
  responding."* This is Horshack's own wording, preserved verbatim in the tree at
  `ml/src/installer.c:37-58`. He induced it deliberately: an infinite loop on the ICU with
  IRQ/FIQ disabled → after **~10 seconds** the body showed **"Error 80" on the top LCD**
  (the panel the MPU drives directly). Back buttons (ICU-serviced) were already dead; the top
  buttons (MPU-serviced) still worked. That is the mechanism in one experiment: **the MPU
  notices the ICU has gone silent on the serial link and faults the camera itself.**

Fault path under a JTAG halt:

    JTAG debug-request halts ICU  ->  ICU stops servicing the SIO3/MREQ link
      ->  MPU stops receiving expected traffic  ->  MPU internal timeout (~10 s)
      ->  MPU asserts ERR80, drives it onto the top LCD, cuts/holds the camera.

The ICU is halted the whole time, so **the ICU-side error dialog never runs** — the MPU paints
ERR80 without the ICU's help. This is why the ICU-side `ErrForCamera_handler` (below) is a red
herring for *this* failure.

## 2. Candidate addresses / symbols found (with evidence)

### 2.1 `ErrForCamera_handler` @ `0xe076bd64` (THUMB) — ICU-side error DIALOG
- Evidence: existing stub, `ml/platform/6D2.111/stubs.S:235`, annotated "ERR70, ERR80 etc
  (DlgErrForCamera.c)". Cross-camera consistent (200D `0xe06217f1`, 5D4 `0xfe59c176`, etc.).
- What it actually is: the ICU routine that *draws a Canon error dialog on the main screen* for
  **ICU-detected** errors. It is **not** the MPU-side ERR80 trigger, and it **cannot execute
  while the ICU is halted**. Value to a future session: breakpoint it to enumerate ICU-side
  error codes and their arg registers — useful for error taxonomy, useless for halt-survival.
- Sibling: `ErrCardForLVApp_handler` @ `0xe07d0810` (`stubs.S:218`) — card/LV error dialog,
  not watchdog-related.

### 2.2 DryOS assert path (context, not the watchdog)
- `debug_assert` @ `0xe0617620`; `DRYOS_ASSERT_HANDLER = 0x4000` (`consts.h:11`). This is the
  software assert path (e.g. `KerRLock.c:205` that currently blocks ML's own boot in QEMU).
  Distinct from the MPU hardware watchdog; noted so it is not conflated with ERR80.

### 2.3 `0xC0410000` (the DIGIC-5 watchdog base) in ROM0 — NEGATIVE
- Raw occurrences of the little-endian word `0xC0410000` in ROM0: **6**, of which only **2 are
  word-aligned** (literal-pool candidates), at file offsets `0x1982fb4` and `0x198331c`
  (vaddr ≈ `0xE1982FB4` / `0xE198331C`).
- Both aligned hits sit **inside a dense table of `0xC0xxxxxx` hardware addresses**: the ±0x40
  neighbourhood is 100% / 55% C0-range words, and the surrounding `0x1982000-0x1984000` page is
  13% C0-range. That is the signature of a **register/descriptor table (data)**, not a code
  literal that a watchdog-kick routine loads.
- The whole `0xC041xxxx` block in ROM0 is populated with ~34 *different* addresses
  (`0xc0410000`, `0xc0410084`, `0xc0418830`, `0xc041b2b0`×5, `0xc041dad0`, …), i.e. it reads as
  a **RAM/DMA/buffer region on DIGIC 7**, not a single hammered control register.
- Conclusion: **no evidence DIGIC 7 reuses `0xC0410000` as a suppressible watchdog.** The
  DIGIC-5 register map does not transfer. (For reference, the DIGIC-5 register per the ML wiki:
  base `0xC0410000`; `+0x00` config at init; `+0x04` pinged with `0xAA55` periodically;
  `+0x08` carries a "timed out" flag; writing 0 disables it. None of that structure is visible
  at the 6D2's `0xC041xxxx`.)

### 2.4 Dominant `0xC0xxxxxx` literal pages — per-unit banks, not a watchdog
- Top ICU MMIO literals cluster at `0xC0xxF800` on a **`0x40000` stride** (`0xc000f800`:497,
  `0xc004f800`:138, `0xc008f800`:129, `0xc00cf800`:97, `0xc010f800`:107, …). A fixed offset
  repeated at a regular stride is a **per-channel/per-unit register bank** (EDMAC/DMA/interrupt
  fan-out), not a watchdog. 4580 distinct C0-range register pages are referenced in total; none
  has the "one register, written once then pinged with a magic constant" shape that a watchdog
  would.

### 2.5 MPU spell set — no watchdog / keep-alive message — NEGATIVE
- `qemu-eos/hw/eos/mpu_spells/{known_spells.h,MpuProperties.h,Shutdown.h}` and the captured
  `tools/6D2_spells_qemu.h` contain **no** watchdog/timeout/keep-alive/"I'm alive" message.
- The only timeout-adjacent properties are **inactivity auto-poweroff**, which is a different
  feature: `PROP_AUTO_POWEROFF_TIME` (`0x80000024`) and `PROP_ICU_AUTO_POWEROFF`
  (`0x80030009`). `MPU_SHUTDOWN` (`0xFFFF`) is a qemu sentinel, not a real spell.
- Implication: there is **no known "tell the MPU to stop watchdogging me" spell** to send
  before a halt. If such a spell exists it is outside the ~23-spell set ML has mapped for the
  6D2 and would need a full body-side capture to find.

## 3. Is a suppress mechanism feasible?

**Not as a single register write, and not from the ICU ROM.** Reasoning:

1. The trigger is on the MPU. The MPU's timeout timer and its ERR80 assertion are MPU firmware.
   The ICU cannot write an MMIO register to stop the MPU's own timer — that timer is not in the
   ICU's address space, it is inside the other chip.
2. The ICU ROM shows **no DIGIC-5-style ICU watchdog register** to zero out (§2.3/§2.4).
   (Note: a *separate* ICU-side hardware watchdog may still exist — one that reboots the ICU if
   the ICU firmware stalls — but a JTAG debug-halt typically stops the core cleanly and the ML
   record is silent on an ICU reset preceding ERR80; Horshack's stall produced ERR80, not an
   ICU reboot. So the ICU-side watchdog, if present, is not the thing that fires first.)
3. There is **no MPU spell** to disable the timeout (§2.5).

What *is* feasible instead — keep the MPU link alive so the timeout never arms:
- **(A) Peek-and-resume.** Halt, do the inspection, resume — all inside the ~10 s budget. No
  suppress needed. Covers register reads, RAM reads, short single-step bursts. This is the
  realistic near-term capability and needs zero new mechanism.
- **(B) Per-core halt.** DIGIC 7 is dual Cortex-A9 and kitor's DIGIC-8 OpenOCD config is
  already dual-core/SMP. If the SIO3/MREQ servicing is pinned to one core, halting only the
  *other* core could keep the MPU fed. Unverified whether MPU comms is core-pinned and whether
  the debugger can hold one core while running the other; this is a Phase-1 bench question.
- **(C) Hardware shim.** A small MCU on the ICU↔MPU serial line that replays the expected
  keep-alive while the ICU is halted. Highest effort; last resort.
- **(D) MPU firmware route.** Dump and neuter the MPU's timeout on the MPU itself. This is a
  separate, much larger project (different chip, different dump path) and is out of scope here.

## 4. VERIFIED vs ASSUMED

**VERIFIED (from files/ROM in this workspace or a direct web source):**
- ERR80 = MPU-detected "firmware not responding", ~10 s after the ICU goes silent, shown on the
  top LCD. Source: `ml/src/installer.c:37-58` (Horshack), corroborated by ML forum/wiki.
- MPU and ICU are separate processors; ROM0/ROM1 are the ICU's ROMs. Source: ML architecture +
  web cross-check (MPU historically Toshiba TX19A-class; ICU the ARM).
- `ErrForCamera_handler` @ `0xe076bd64` handles ERR70/ERR80 dialogs on the ICU. Source:
  `stubs.S:235`.
- `0xC0410000` appears in ROM0 only as dead entries in a hardware-address table; no live
  watchdog-register shape. Source: direct ROM0 scan (this phase).
- No watchdog/keep-alive MPU spell in the mapped 6D2 set. Source: `mpu_spells/*`, `6D2.h`.
- DIGIC-5 watchdog register structure (`0xC0410000` +0x00/+0x04/+0x08, ping `0xAA55`, write-0
  disables). Source: ML Register Map wiki (web).
- `objdump` is available on this machine at `/run/current-system/sw/bin/objdump` for targeted
  disassembly (arm-none-eabi-objdump is only on PATH inside `nix-shell`).

**ASSUMED / INFERRED (needs confirmation):**
- The ~10 s budget is roughly fixed and starts when ICU traffic stops. (Horshack: "at least
  10 s"; exact value and whether it resets on any partial traffic is unmeasured.)
- The MPU watchdog watches *link liveness / expected periodic traffic* rather than one specific
  keep-alive byte. (Consistent with the evidence; not proven.)
- SIO3/MREQ is the serial path the MPU watchdog watches on DIGIC 7. (Strongly implied by the
  qemu model; not confirmed against a real 6D2 capture.)
- Whether an ICU-side hardware watchdog also exists on DIGIC 7 and whether it keeps counting
  during a debug-halt. (Unknown; not the first-firing fault per current evidence.)

## 5. Concrete next step

**Highest-value experiment (still in-scope, static + one cheap on-body measurement):**

1. **Static (continue this spike):** Disassemble the ICU-side MPU serial ISR to find the
   servicing cadence and whether the ICU emits any periodic MPU write. Path:
   `objdump -b binary -m arm -M force-thumb -D --adjust-vma=0xE0000000 \
   --start-address=0x... --stop-address=0x... roms/6D2/ROM0.BIN`, seeded from the SIO3/MREQ
   ISR (find it via the interrupt table and the MREQ `0xC0203000` reference). Goal: identify
   what "keeps the MPU happy" from the ICU side, and whether it is periodic (a heartbeat) or
   purely reactive (answer-when-asked). Put only addresses + interpretation in output; never
   ROM bytes.
2. **On-body confirmation (cheap, non-JTAG, uses the proven UART/log path):** Extend Horshack's
   stall test into a *timed* one — stall the ICU for N seconds under UART logging and sweep N to
   nail the exact halt→ERR80 budget and whether any activity resets it. This converts "at least
   10 s" into a hard number that defines the peek-and-resume window a real JTAG session gets.

The single most valuable outcome is a **measured halt-to-ERR80 budget + the MPU servicing
cadence**: it turns the open blocker from "unknown" into a known time budget, which decides
whether option (A) peek-and-resume is enough or whether (B)/(C) hardware work is required before
any indefinite-halt debugging.
