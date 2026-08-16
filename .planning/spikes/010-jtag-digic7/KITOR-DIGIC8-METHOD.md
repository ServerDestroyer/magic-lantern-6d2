# kitor's DIGIC 8 JTAG method — implementation-ready distillation

**Purpose.** Everything kitor published about getting a live dual-core GDB
session on a DIGIC 8 body, structured so it can be reused on a DIGIC 7 (6D2)
donor. Verified against the primary source; assumptions and unknowns are
flagged explicitly at the end.

## Provenance

- **Primary source:** ML forum topic **27350**, "JTAG on Digic 8", by kitor
  (Reverse Engineering board). Posts: kitor #0 (2025-08-27), kitor #1
  (2025-08-30), coon #2 (2025-09-02).
  Retrieved via Wayback (live forum is Cloudflare-blocked to non-browsers):
  `https://web.archive.org/web/20260206101918/https://www.magiclantern.fm/forum/index.php?topic=27350.0`
  Only page 0 is archived; Wayback's crawler was itself blocked after
  2026-03-09, so posts after that date are unread — re-check periodically.
- **kitor's image host:** `https://kitor.pl/eos/jtag/` (photos of the SX740
  debug connector, EOS R/RP/SX70/250D pads, measurements). Referenced but not
  mirrored here.
- **Supporting primary sources** used for the DIGIC-generation contrast:
  - CHDK forum topic **13408** "DIGIC 5 JTAG" (nada / Versaloon, 2018) — the
    only prior published DIGIC-5 OpenOCD session.
  - ML forum topic **22030** "JTAG on DIGIC chips" (2018, a1ex/g3gg0) — the
    ICU/MPU/ERR80 watchdog distinction.
  - ML forum topic **7531** "Battery grip pins / UART" (coon/kitor) — EOS
    R/RP/5D3 UART pinouts and the FZC-8 connector family.

---

## VERIFIED — from the primary source (topic 27350)

### What kitor achieved

A full **dual Cortex-A9 GDB session on a PowerShot SX740 HS (DIGIC 8)**:
single ARM TAP with IDCODE **`0x4ba00477`** (mfg `0x23b` ARM Ltd, part
`0xba00`, ver `0x4` — the standard ARM CoreSight DAP), halt + live register
dumps of both cores, hardware breakpoint/watchpoint units per core (the
research doc records 6 bp / 4 wp), attached over GDB. Example halted-core
dump he posted: `pc 0xe006e600`, `lr 0xe025eb33`, `sp 0x1ccd08`,
`sp_irq 0xdf000100`, `lr_irq 0xe0514976` — RAM/ROM addresses consistent with
a real DryOS ICU, confirming the session was genuine.

### The OpenOCD config (verbatim, final simplified form)

kitor started from OpenOCD's bundled TI `am437x` example (which expects a TI
ICEPICK router, `0x0b98c02f`), saw the scan return the ARM DAP directly
instead, and simplified to a hand-written single-TAP config:

```tcl
reset_config trst_and_srst
set _CHIPNAME digic8
# Dual Cortex-A9
set _TARGETNAME0 $_CHIPNAME.cpu0
set _TARGETNAME1 $_CHIPNAME.cpu1

jtag newtap $_CHIPNAME cpu -irlen 4 -expected-id 0x4ba00477
dap create $_CHIPNAME.dap_cpu -chain-position $_CHIPNAME.cpu

target create $_TARGETNAME0 cortex_a -dap $_CHIPNAME.dap_cpu -coreid 0 -rtos hwthread
target create $_TARGETNAME1 cortex_a -dap $_CHIPNAME.dap_cpu -coreid 1 -rtos hwthread
#what about -dbgbase?

target smp $_TARGETNAME0 $_TARGETNAME1
```

Key facts embedded here:
- **Single TAP, `irlen 4`, expected IDCODE `0x4ba00477`.** DIGIC 8 exposes
  the ARM CoreSight DAP directly on the scan chain. It did **not** need the TI
  ICEPICK routing that DIGIC 5 required (see contrast below).
- **`transport`/adapter** is set by the interface file kitor sourced
  separately (an Altera USB Blaster clone — see hardware). The
  `reset_config trst_and_srst` line reflects that both nTRST and nSRST exist
  on the connector.
- **Dual core via one DAP:** two `cortex_a` targets on the same
  `dap_cpu`, `-coreid 0` and `-coreid 1`, joined with `target smp`.
  `-rtos hwthread` presents the two cores as GDB threads.
- kitor's own open question, left in the file: `#what about -dbgbase?` — he
  did not supply per-core debug base addresses; autoprobe found them.
- **Xtensa cores not reached:** "OpenOCD autodetection returned just [the]
  ARM one." DIGIC 8's secondary Xtensa cores were not accessible through this
  TAP.

### Pin identification by resistance-to-ground (the reusable procedure)

This is the transferable core of the method — no datasheet, just a
multimeter against a powered-down/idle board:

1. **Find the debug connector by shape.** On EOS R and RP the debug connector
   "starts with clearly visible **5 pogopin testpoints** in the same shape."
   kitor found it by educated guess from the connector geometry.
2. **Classify each pad by resistance to GND:**
   - **TDI / TCK / TMS / TDO** → **100–200 kΩ to ground** (kitor measured
     ~128 kΩ on EOS R, ~160 kΩ on SX740).
   - **/TRST** → **~10 kΩ pull-down to GND** (distinctly lower than the
     signal lines — this is how you tell it apart).
3. **Confirm with live logic levels while the camera runs:**
   - **/TRST and TDO are pulled LOW** (to ground) while running.
   - **TDI, TCK, TMS are HIGH.**
   - (On the SX740 he cross-checked measured boot levels against a reference
     pinout; the only mismatch was a pad described as "maybe /SRST" that read
     low.)
4. **Wire the knowns, brute-force the rest.** Connect /TRST, TDO, VREF and GND
   (identifiable from steps 2–3), then **guess the order of the remaining
   three** (TDI/TCK/TMS). Search space is only 3! = 6 permutations. kitor got
   it on the first try.

Porting the pad location to a new model (what coon and kitor did next):
- coon located the JTAG test pads on a **broken RP donor board** (DIGIC 8
  desoldered) by matching kitor's annotated R photo; pad **order differs from
  R** but is the same on the unsoldered big connector.
- kitor traced signals on a **water-damaged SX70 board** by removing the
  DIGIC and following traces **under a microscope** back to the chip.
- **250D:** has a provision for a similar connector but, after checking
  grounds, the **pinout is definitely different**; also no UART on that
  connector (250D UART is on the external FZC-8).

### Hardware / tooling kitor actually used

- **Adapter:** an **Altera USB Blaster** (clone). Tell: OpenOCD logged
  *"This adapter doesn't support configurable speed"* — the signature of the
  cheap USB Blaster clone. His one multi-hour failure was a **swapped
  connector orientation** ("got the Blaster pinout wrong, swapped left with
  right side of connector"), not a method error.
- **Software:** OpenOCD (config above) + GDB (`info registers` dumps shown).
- **Bench instruments:** multimeter (resistance + level classification),
  microscope (trace-back on the donor board).
- kitor did **not** cable nTRST to the probe in the working session — he pulls
  /TRST to VCC to enable JTAG and leaves it (see DIGIC 5 contrast: /TRST is
  active-low and tied low, so it must be released to VCC to bring the TAP up).

### DIGIC-generation contrast (verified from the three threads)

| | DIGIC 5 (CHDK topic 13408) | DIGIC 8 (kitor topic 27350) |
|---|---|---|
| TAP seen | TI **ICEPICK** JRC, IDCODE `0x1b93a02f` (mfg TI) | **ARM CoreSight DAP** direct, IDCODE `0x4ba00477` (mfg ARM) |
| OpenOCD needs | ICEPICK tapenable event to expose the DAP | plain single-TAP `jtag newtap … -irlen 4` |
| nTRST | tied low (active); pull to VCC to enable | /TRST ~10 kΩ pull-down; pull to VCC to enable |
| bp/wp units | 2 breakpoint/watchpoint units | per-core hardware bp/wp (research doc: 6 bp / 4 wp) |
| body type | PowerShot (no MPU watchdog) | SX740 PowerShot (no MPU); EOS R/RP pads mapped, not yet halted |

---

## Parts list (to replicate on a DIGIC 7 donor)

- **1.8 V-compatible JTAG adapter.** kitor used an Altera USB Blaster clone.
  DIGIC 6–8 core logic is **1.8 V**; verify the adapter tolerates/drives 1.8 V
  or add a level translator. (An FT2232H-based probe with adjustable VREF is
  the safer modern choice.)
- **Multimeter** (resistance to GND + logic-level classification).
- **330 Ω series resistors** for every probe line during discovery.
- **Oscilloscope** for the passive idle/boot survey.
- **JTAGulator or JTAGenum** for automated pinout brute-forcing (optional —
  kitor's 3!-permutation hand method is enough once TDO/TRST/VREF/GND are
  pinned).
- **Microscope + fine soldering** for tracing pads on a donor board and
  attaching to 0.5 mm-pitch pads.
- **Donor board — never the working camera.** kitor's whole method depends on
  desoldering the DIGIC from a dead board to trace signals; he explicitly
  requested dead EOS R / DIGIC 6+ boards from the EU community and service
  centers.
- OpenOCD + gdb-multiarch (`arm-none-eabi-gdb`).

---

## VERIFIED vs ASSUMED vs UNKNOWN

**VERIFIED (primary source, DIGIC 8):**
- OpenOCD dual-Cortex-A9 SMP config text (above), IDCODE `0x4ba00477`,
  `irlen 4`, single ARM DAP TAP.
- Resistance signatures: 100–200 kΩ (TDI/TCK/TMS/TDO), ~10 kΩ pull-down
  (/TRST); running levels /TRST+TDO low, TDI/TCK/TMS high.
- Adapter class (USB Blaster clone, 1.8 V logic), microscope trace-back
  method, the 3-permutation guess for TDI/TCK/TMS.
- DIGIC 8 exposes ARM DAP directly (no ICEPICK), unlike DIGIC 5.
- EOS R and RP debug connectors located and pad-mapped by coon+kitor (order
  differs between them); 250D connector confirmed different.

**ASSUMED (reasonable, not measured on target):**
- DIGIC 7 (6D2) is the same dual Cortex-A9 at 1.8 V → the SMP config template
  and the resistance-signature procedure should apply structurally.
- The debug connector on a 6D2 will present a similar pogopin/testpoint
  cluster near the DIGIC (kitor found EOS bodies' connectors by shape).

**UNKNOWN (must be discovered on a 6D2 donor):**
- **The 6D2 IDCODE.** DIGIC 7 could present the ARM DAP directly (DIGIC 8
  style, `0x4ba00477`) **or** behind a TI ICEPICK (DIGIC 5 style,
  needing the tapenable event). No DIGIC 7 IDCODE is published. This is the
  single biggest open variable and it changes the OpenOCD config shape.
- **6D2 debug-pad location and order.** No 6D2 JTAG pinout exists. The 6D2 is
  a different body from R/RP/250D; its pad order is its own.
- **`irlen`** for DIGIC 7 (4 assumed from DIGIC 8; ICEPICK path would differ).
- **Whether any secondary cores are reachable** (kitor could not reach DIGIC
  8's Xtensa cores).

---

## What transfers cleanly to DIGIC 7 vs what does not

**Transfers cleanly:**
- The **resistance-signature pin-ID procedure** — it is chip-agnostic
  (100–200 kΩ signal lines, ~10 kΩ /TRST pull-down, TDO/TRST low while
  running). This is the highest-value reusable asset.
- The **microscope trace-back on a dead donor board** to map pads → DIGIC.
- The **OpenOCD dual-Cortex-A9 SMP skeleton** — the `target create cortex_a
  … -coreid 0/1` + `target smp` structure is correct for any dual-A9 DryOS
  ICU; only `-expected-id`, `irlen`, and (possibly) an ICEPICK wrapper change.
- The **1.8 V adapter requirement** and the swapped-orientation gotcha.

**Does NOT transfer / genuinely new on a 6D2:**
- The **exact IDCODE and TAP topology** (ARM-direct vs ICEPICK) — must be
  scanned. Start OpenOCD in autoprobe mode (`jtag newtap … -irlen 4 -ignore-version`
  / `-expected-id 0`) and read what comes back before committing kitor's
  `expected-id`.
- The **pad map** (6D2-specific).
- **The MPU/ERR80 watchdog problem** — kitor's SX740 is a PowerShot with **no
  MPU**, so a halt just stalls. On an **EOS** body the MPU faults **ERR80**
  within seconds of the ICU going unresponsive (a1ex, topic 22030). DIGIC 5
  had a suppressible ICU-side watchdog at `0xC0410000`; **no DIGIC 7 MPU-side
  suppression address is published.** This is the one hazard kitor's method
  never had to solve, and it is the DIGIC-7 EOS-specific blocker to a *stable*
  session (see spike 010 README Phase 0). A halt will still work; staying
  halted for more than a few seconds is the open question.
