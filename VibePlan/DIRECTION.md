# The Direction — Magic Lantern on the Canon EOS 6D Mark II

**Written:** 2026-08-16 · **For:** Chris · **Status:** synthesis + recommendation, not a committed plan

This is the "step back and look at everything" document Chris asked for. There is
more than one plan running at once right now (five parallel spikes, 010–014, plus
a couple of also-rans). This file records **the intent**, **everything behind
that intent**, **all the ideas on the table**, and **the best single direction
that reconciles them**. It is meant to be the place you re-read before deciding
which plan gets the effort.

Ground-truth state lives in the memory file `6d2-project-state`, the spike
READMEs under [.planning/spikes/](.planning/spikes/), and
[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/PLAN_OF_ACTION.md](PLAN_OF_ACTION.md).
This document points at those; it does not replace them.

---

## 1. The intent

**Core goal:** make Magic Lantern fully functional on the Canon EOS 6D Mark II
(DIGIC 7), using QEMU emulation plus the real body, and contribute the results
upstream.

**The narrowed scope (Chris's decision, 2026-08-16):** the only active work is
**JTAG and what connects to it.** Everything else — lossless compression, movie
dual-ISO, further generic QEMU boot work, PR follow-ups — is paused unless it
feeds the hardware-in-the-loop path. Do not re-open the other spikes without
Chris saying so.

**Why that scope, in Chris's framing:** the ML maintainer (reticulatedpines)
named **JTAG / hardware-in-the-loop** as the real bottleneck — "hardware in the
loop, not tokens" — and it is the one contribution nobody else is currently
making. Brute-forcing features with an LLM is cheap and largely done; putting a
real debug channel on a running DIGIC 7 is the scarce, valuable thing.

---

## 2. Everything behind that intent

**The project already largely succeeded — this changes what "remaining work"
means.** As of 2026-08-16, on the real body and in QEMU, these are confirmed:

- ROMs dumped and verified; `platform/6D2.111` is the correct firmware (1.1.1).
- MOV time-limit override — **hardware-confirmed**, upstream PR open (#294/#297).
- Raw video (MLV) — **recorded on the body**, pixel-valid, re-arm fix verified.
- Dual-ISO stills — **engaged on the body**, cr2hdr merges end-to-end.
- Stock 6D2 firmware **completes startup in QEMU** (was the big blocker; solved
  by capturing 175 real MPU spells off the body — first DIGIC 7 spell set in
  qemu-eos).
- ML itself boots in QEMU and is exonerated (it parks legitimately waiting on a
  GUI stage the emulator doesn't reach).

So the remaining frontier is **not** "make ML work." Most feature work is done or
shippable. The frontier is a **debug capability** — the ability to see and poke
the real silicon — which is exactly what the maintainer flagged as the top lever.

**The maintainer relationship (drives the contribution value):**

- He named JTAG as his top lever; implementation and physical contacts unknown to
  him. Nobody in the community has a working modern-EOS debug port.
- He wants **bug reports with reasoning**, not untested LLM-generated fixes (see
  memory `ml-upstream-contribution-norms`). On PR #298 he preferred fixing the
  root property path over a new-cam-only workaround.
- The MPU-spell capture work drew genuine interest — he never knew how to import
  recorded MPU traffic; others asked for the scripts (200D, M50).
- Reception of the LLM-driven workflow was mixed; over-claiming ("first-ever raw
  video on a 6D2") was rejected and cast doubt on true claims. Honest, verified,
  reasoned contributions land; hype does not.

**The honest reframe (from spike 011's two red-teams — read this before
committing effort):** we do **not** need hardware-in-the-loop to move the roadmap
forward. Every shipped feature landed without a debug port, and most open
questions are answerable at the desk in QEMU — **only ~5 items are genuinely
hardware-bound.** So the whole 010–014 cluster is about **building a capability
and contributing the maintainer's named lever**, not unblocking anything. Frame
it that way — to ourselves and to upstream. That reframe is the single most
important input to picking the direction, because it means we can choose the
cheapest capability that delivers the contribution, not the most powerful one.

**Constraints that bound every option:**

- **One body, brick risk.** Chris's own 6D2 is the only hardware. Card-boot and
  battery-pull are the safe recovery nets; anything that can corrupt flash/NVRAM
  is the one unrecoverable-brick vector.
- **No soldering preferred.** Full JTAG needs a donor board and soldering to the
  SoC; the cheaper paths need at most peeling a rubber cover.
- **EOS MPU watchdog (ERR80).** On EOS bodies, halting the ICU makes the MPU
  fault the camera within seconds — the DIGIC 7 suppress address is unpublished.
  This specifically threatens **halt-based** debugging (JTAG), not passive read
  channels (USB peek, peek-to-SD, UART).
- **Copyrighted ROMs** (never commit/redistribute) and a **Cloudflare-blocked
  forum** (retrieve via Wayback) — logistics, already handled.

---

## 3. All the ideas on the table

These are the plans currently in motion. All of them "connect to" the JTAG goal
in the sense that matters: they all deliver **hardware in the loop**. They differ
enormously in cost, risk, and how much they buy.

| Idea | Spike | Status | What it buys | Cost / risk |
|---|---|---|---|---|
| **Emulator-first desk answers** | 013 Track A | startable **now** | Answers most open questions in QEMU (GDB + `pmemsave`/`xp` + `-d` flags); shrinks the hardware-bound set to ~5 | none — desk-only |
| **On-camera peek-to-SD module** | 011 #1 (bundled into 012/013) | buildable **today** | Reads real RAM/registers to the card; tens of lines, all stubs proven on 6D2; de-risks addresses before USB | battery-pull only |
| **USB peek/poke/call debugger** | 012 | PLANNED, phase 1 desk-ready | **Live** read/write/call of the running 6D2 from the PC over USB — an LLM-drivable loop against real silicon, no soldering. Gated on one stub (`ptp_register_handler`, candidate `0xE04BF152`) | brick vector via `CallFunction`; mitigable (RAM-only reads first, QEMU-validate the stub) |
| **Emulator ground-truth loop** | 013 Track B | PLANNED (needs a read channel) | Feed measured values back into qemu-eos → faithful emulator → shrinks future hardware need; some fixes help every DIGIC 7/8 body | none beyond the read channel |
| **UART crash console** | 014 | DEFERRED | The one thing ML-code channels can't do: **see a dead camera** — crash tail when the card log is blank, and pre-boot/bootloader output | needs opening the camera (cover, no solder); low |
| **Full JTAG on DIGIC 7** | 010 | PLANNED, no hardware | CPU **halt + single-step**; hard-brick recovery; emulator self-validation; the 3 register questions marked unanswerable in `PU1_INVESTIGATION.md` | donor board + soldering + microscope; ERR80 watchdog unresolved; highest |
| *io_trace.c port to DIGIC 7* | — | deprioritized | MMIO tracer (`0xC0000000`–`0xCFFFFFFF`); "very useful for emulation" | wrong tool for on-demand peeks; 9 `#ifdef` sites; not a quick win |
| *drysh / Mon\* RPC via `call()`* | — | reachability unproven | Native Canon shell / memory RPC, hardware-free | 6D2 MPU memory map unknown |

---

## 4. The best direction

**A laddered hardware-in-the-loop capability, cheapest-first.** Each rung is
lower cost/risk than the next and reaches most of the value before the expensive
rungs are ever needed. This honors the "JTAG and what connects to it" scope —
every rung *is* what connects to it — while deferring the one rung that actually
requires soldering and a donor body.

1. **Now — desk, zero risk (spike 013 Track A).** Answer everything answerable in
   QEMU with GDB: the `0xE0494208` non-return bisect, the PU1Wait giver, the
   ShtCap handle, the `model_list.c` field checks. This alone shrinks the
   must-use-hardware set to ~5 items and costs nothing. Do it first regardless of
   what happens above it.

2. **Next — build, battery-pull risk (peek-to-SD module).** The fastest real
   readback: reuse `save_mem_to_file` + the `core_dump_requested` trigger shape
   already in-tree. Reads the actual silicon today, no ROM archaeology, and
   de-risks the addresses the USB path will use.

3. **Then — one card install + USB (spike 012).** Add the `ptp_register_handler`
   stub (QEMU-validate `0xE04BF152` first, free), build `CONFIG_PTP`, install
   once. Result: `GetMemory`/`SetMemory`/`CallFunction` over the USB cable — a
   live, LLM-drivable loop against the running 6D2, **no soldering.** This *is*
   the maintainer's "hardware in the loop," delivered at the cheap end. Read-only
   RAM first; never `CallFunction` a flash/NVRAM routine.

4. **Feed back (spike 013 Track B).** Every measured value replaces a guessed
   qemu-eos field → the emulator gets more faithful → more of rung 1 becomes
   answerable at the desk → fewer body reads needed. The loop tightens itself.

5. **On demand (spike 014 UART).** Pull off the shelf only when a real
   crash/freeze produces a blank card log and no ML-code channel can see it.
   Read-only serial is nearly free (3.3V FTDI reads the 1.8V line; `uart_printf`
   already stubbed).

6. **Capstone (spike 010 full JTAG).** Pursue only for what nothing above can do
   — CPU halt/single-step and hard-brick recovery — and only once the ladder is
   exhausted or a specific need forces it. Needs a donor board, soldering, and a
   resolution to the ERR80 watchdog. Collaboration with kitor (who has DIGIC 8
   GDB working and asked for donor boards) is the highest-leverage first move
   here, not soldering Chris's only body.

---

## 5. The crux — what JTAG uniquely buys vs. what the ladder already reaches

This is the decision the whole thing turns on, and it's why the ladder puts full
JTAG last rather than first.

**Reachable *without* JTAG, via the ladder:**

- Arbitrary RAM/register **reads** on the running camera → USB peek (012) and
  peek-to-SD.
- Arbitrary **writes / function calls** to test a theory → USB poke/call (012).
- Boot log, crash tail, bootloader output → UART (014).
- Ground truth for the emulator's guessed fields → the 013 feedback loop.
- Nearly all of the open `PU1_/ASSERT_INVESTIGATION` questions → QEMU + GDB (013
  Track A).

**Uniquely JTAG (nothing else can):**

- **CPU halt + single-step** of the live core — peek/poke channels need the
  firmware *running*; they cannot stop it.
- **Hard-brick recovery** — reviving a body with a dead bootloader / corrupted
  flash, when card-boot itself is gone.
- **State during a total wedge** where no firmware channel runs at all (UART sees
  what was *printed*; JTAG sees the *registers* of a stopped core).

**Consequence:** roughly 80% of JTAG's value is reachable at a fraction of the
effort through the ladder's cheap rungs. JTAG earns its keep as the **capstone**
— CPU-halt debugging and un-bricking — not as the starting point. The scope
decision ("JTAG and what connects to it") is best honored by building *what
connects to it* first.

---

## 6. Open decisions for Chris

1. **Confirm the ladder ordering**, or reassert full-JTAG-first if the goal is
   specifically the CPU-halt/un-brick capability rather than register visibility.
2. **The USB path's first physical step** is a one-time card install + a boot —
   are you willing to run `CONFIG_PTP` on the body once? (Read-only, battery-pull
   recoverable; the stub is QEMU-validated before it ever touches the camera.)
3. **The ERR80 watchdog** is the unresolved Phase 0 blocker for *halt-based*
   debugging only. It does not threaten rungs 1–5. Worth resolving before rung 6.
4. **kitor collaboration** for the JTAG capstone — reach out for a donor-board
   pinout rather than soldering your only body? He already asked for donors.

**Recommended immediate action:** start spike 013 Track A (desk, free) and build
the peek-to-SD module (rungs 1–2) in parallel — both are zero-to-low risk, both
feed the USB debugger, and neither commits you to soldering anything.
