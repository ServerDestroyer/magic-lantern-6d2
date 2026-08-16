---
spike: 010
name: jtag-digic7
type: scoping
validates: "Given kitor's confirmed DIGIC 8 JTAG method (dual-core GDB on a PowerShot SX740 HS, Aug-Sep 2025), when the same resistance-signature pin-ID method and OpenOCD config are applied to a DIGIC 7 (6D2) donor body, then a live IDCODE is found and a debug session is established"
verdict: PLANNED — no hardware work started yet, this is the ordered plan
related: [001, 004, 005]
tags: [jtag, hardware, digic7, scoping, planning]
---

# Spike 010: JTAG on DIGIC 7 (6D2)

## Verdict, up front

**No soldering has happened yet. This spike is the plan, not a result.**
Chris scoped the project down to "JTAG and what connects to it" on
2026-08-16 (see `PROJECT_STATE` memory) — this is the first artifact under
that decision. The plan below is ordered by dependency and cost: every step
before Phase 1 is pure research or software, zero hardware risk.

Full background research is in
[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/docs/jtag-research.html](../../../docs/jtag-research.html)
(updated 2026-08-16 with the kitor correction below).

## 1. Why JTAG, given the alternatives

Three non-JTAG debug options already exist or are close:

| Option | Status | What it can't reach |
|---|---|---|
| Port `ml/src/io_trace.c` to DIGIC 7 | Not started — 9 `#ifdef CONFIG_DIGIC_VI` sites need a DIGIC 7 branch | Only traps `0xC0000000`-`0xCFFFFFFF` (MMIO). DryOS RAM (e.g. `0xDF00B450`) is outside its range. |
| QEMU + gdb on the emulated guest | Already working today (used to trace `rgb_vram_preinit`) | Debugs the *emulated approximation*. Can't validate its own guessed model fields — 6 of 8 6D2 qemu-eos model fields are `fixme` or copied from the 200D. |
| UART / `CONFIG_STARTUP_LOG` / `DEBUGMSG.LOG` | Proven, used for MPU-spell capture and the re-arm fix | Firmware-cooperative only — blind during a wedge (nothing running = nothing logged). |

What none of the three can ever reach, per
[docs/jtag-research.html §05](../../../docs/jtag-research.html):

- The three questions `PU1_INVESTIGATION.md` marks unanswerable: the value
  of `r4` at `0xDF00B450`, which code hands out the PU1Wait semaphore, why
  `0xE0494208` never returns.
- Ground truth for the emulator's own guessed config (the 6 `fixme`/copied
  fields above) — the emulator cannot validate itself.
- Any state during a wedge, when no firmware-cooperative channel runs.

That's the actual case for JTAG: not "the emulator needs register values"
in general (most of that is already solved — stock firmware completes
startup in QEMU as of commit `85ad7df`), but these specific residual gaps
plus emulator self-validation.

## 2. What actually happens when JTAG halts an EOS body (mechanism)

Worth being precise about this before wiring anything up, because it
changes what a debug session can and can't do:

- The halt itself is a **hardware** feature of the ICU's silicon
  (ARM CoreSight/EmbeddedICE debug-request halt). JTAG never touches the
  MPU — it's a physically separate chip.
- Once halted, USB/button non-responsiveness is a **firmware** side
  effect, not a hardware one: nothing disables the USB peripheral, the
  ICU's firmware (which drives the USB stack) simply stops executing.
- On EOS bodies specifically (unlike the PowerShot kitor used, which has
  no MPU), **the MPU is running its own firmware watchdog** that notices
  the ICU has stopped answering and faults the camera with ERR80 within
  seconds — g3gg0, ML forum: *"That's different from EOS — there, it
  locks up and the MPU throws ERR80 shortly afterwards... There's no MPU
  on PowerShots."* This is why kitor's PowerShot success doesn't
  automatically mean an EOS session stays alive as long.
- DIGIC 5 had a suppressible ICU-side watchdog (`0xC0410000`, write
  zero via CHDK). **No DIGIC 7 address is published for the MPU-side
  fault.** This is an open blocker — see Phase 0 below.

## 3. Phase 0 — software-only, zero hardware risk, do first

- [ ] Fully retrieve kitor's thread (topic 27350) beyond the summary
      already in memory — exact resistance values, complete OpenOCD
      config text, any DIGIC 7-specific remarks. Wayback CDX, same
      method as before (live forum is Cloudflare-blocked).
- [ ] Pull coon's EOS R/RP pinout posts (topic 7531, posts 38-43) — the
      closest documented EOS bodies to the 6D2 architecturally.
- [ ] **Statically search ROM0 for the MPU-watchdog/ERR80 fault path.**
      This is the one genuinely new problem versus kitor's PowerShot
      case. Finding the trigger logic (or a suppressible register, DIGIC
      5-style) before soldering turns "faults within seconds of a halt"
      from a hard stop into a known, workable window.
- [ ] Line up a donor body. **Never the working camera** — open a body
      and the warranty is void absolutely, no authorised route back.
      ML developers have offered dead bodies for exactly this before;
      worth asking in the forum thread Chris already has contact on.
- [ ] Order tooling: Altera USB Blaster (must be 1.8 V-compatible —
      DIGIC 6-8 logic is 1.8 V), OpenOCD, gdb-multiarch, a scope,
      JTAGulator or JTAGenum, 330 Ω resistors. ~$200 total per the
      research doc's verdict.

## 4. Phase 1 — bench work on the donor body, ordered by dependency

Each step de-risks the next; do not skip ahead.

1. Find and photograph the **FZC-8** footprint — same connector family as
   R/RP/90D/250D/850D, conventionally near the USB port on the PCB (not
   sharing pins with it — see the corrected connector-netlist facts in
   the research doc).
2. Passive scope survey at idle: logic levels on all 8 pins, which pin
   bursts at boot (TX candidate).
3. Classify each pin through a 330 Ω series resistor: input, pulled-up,
   pulled-down, or actively driven. Pulled-low pins are nTRST candidates.
4. Bring up UART first — proves the solder job and voltage assumptions
   independent of any debug port, and hands over a DryOS shell either way.
5. Scan for SWD before JTAG (JTAGulator/JTAGenum sweep both in seconds;
   SWD's search space is far smaller and it's the likelier target).
6. **Repeat every scan with each pulled-low candidate forced high.**
   This is the step that turned a dead scan into a live IDCODE on both
   prior DIGIC successes (DIGIC 4, DIGIC 5) and on kitor's DIGIC 8 work.
   Target signature: `0x4ba00477` (ARM CoreSight DP).
7. **Decision point.** IDCODE found → OpenOCD dual-Cortex-A9 SMP config
   (kitor's template transfers directly) + the MPU-watchdog fight from
   Phase 0. Nothing found across all pads in both nTRST states → stop and
   reconsider; the next tier (X-ray, BGA tracing) costs an order of
   magnitude more for much lower odds — don't just escalate blindly.

Safety, non-negotiable: no DIGIC I/O voltage has ever been published for
this generation beyond the 1.8 V inference from kitor's DIGIC 8 work.
Measure every pad's idle level before driving anything; ground first;
series resistors in every probe line during discovery; start at 100 kHz;
read-only until the map is understood.

## 5. Where the emulator currently stands (context, not a JTAG task)

Not part of this spike's scope (Chris's decision pauses non-JTAG work),
but relevant to why JTAG is being pursued rather than more emulator work:
stock 6D2 firmware completes startup in QEMU (commit `85ad7df`, 473→1581
debugmsg lines). ML's own boot is blocked at
`[CPU1] ASSERT SystemIF::KerRLock.c:205` → `SCS_Initialize` never
completes, identical with and without ML loaded. Leading suspect:
`hw/eos/model_list.c:619`'s single global `current_task_addr = 0x28` on
what's actually a 2-core machine — potentially fixable in pure software,
still open. `-d nochain` already triples progress (1558→4770 debugmsgs)
without resolving it. This is a live, cheap lever independent of JTAG,
but it can never validate the 6 `fixme`/guessed qemu-eos model fields —
only silicon (JTAG) can do that.

## Next action

Phase 0's ROM search for the MPU-watchdog/ERR80 path and the full kitor
thread retrieval are both pure research, no camera needed — either can
start immediately. Donor-body sourcing and tooling orders are on Chris.
