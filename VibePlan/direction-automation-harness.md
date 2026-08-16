# Direction 1 — The Automation Harness

**Status:** recorded (not yet decided or planned)
**Recorded:** 2026-08-16
**Judged against:** `INTENT.md` in this folder.

---

## One-sentence goal

Build a closed-loop harness so the LLM can run the dev cycle itself — make a change, build it, run it, read everything the firmware actually did, diagnose, fix, repeat — so Chris stops being the person who manually builds, reads logs, and swaps cards on every iteration.

## The loop today vs. the target loop

**Today:** I edit → Chris builds/runs and reads the result (or I run QEMU by hand) → I diagnose → repeat. The human steps are the bottleneck.

**Target:** `edit → build → boot → capture full trace → parse → diagnose → fix → commit`, run by the LLM unsupervised on a work branch, iterating until a stated success condition is met. Chris is asked to step in only for physical actions (plug in camera, insert card) or account/legal actions (push a PR).

The capability that makes this possible already exists and is under-used: QEMU's `-d` traces and the on-camera `DEBUGMSG.LOG` give the LLM full *text* visibility into what the firmware did (see `INTENT.md`, step 1). The harness is the machinery that runs the loop around that visibility.

---

## The two halves

### Half A — Emulator loop (software only, zero brick risk, highest leverage)

A headless harness that:
1. Builds the ML or qemu-eos change.
2. Boots it in qemu-eos (`run_qemu.py 6D2 …`).
3. Captures the full execution trace + DEBUGMSG to a file, strips ANSI color, and hands the LLM clean text.
4. (Optionally) parses the trace into a structured diff vs. a known-good baseline, so the LLM reads a summary, not 100k lines.

**The one genuine new dev task underneath it:** get **ML itself to boot under QEMU** past the `[CPU1] ASSERT KerRLock.c:205` gate. Prime suspect: the single global `current_task_addr=0x28` on a 2-core machine (`hw/eos/model_list.c:619`, marked `fixme`). Stock firmware already boots in QEMU; ML does not yet. **Once ML boots under QEMU, the entire ML feature cycle runs headless** — feature changes get tested with no camera in the room and no brick risk. This is the single most valuable unlock in the whole direction.

### Half B — Camera loop (hardware-in-the-loop, removes the handoffs the emulator can't)

Two rungs, safe-first:

**B1 — peek-to-SD module (safe first rung).**
A small ML module that dumps chosen RAM regions to the card on command, reusing the proven `save_mem_to_file` + `core_dump` pattern. Lets the LLM read real-silicon state. Read-only, **zero brick risk**. Still needs Chris to insert the card and power-cycle — so it de-risks everything else but is not hands-off. The plan-extract ranked this "DO-FIRST" among no-solder hardware-in-the-loop paths.

**B2 — PTP USB peek/poke/call debugger (the real automation win, higher risk).**
The peek/poke/call-over-USB path. `GetMemory` / `SetMemory` / `CallFunction` are **already written**; the only blocker is a missing `ptp_register_handler` stub (strong candidate `0xE04BF152`). This turns the tethered camera into a target the LLM drives over the cable — read/write memory, call functions — with **no card swaps and no battery pulls**. It is what makes real-hardware iteration nearly hands-off.
**The catch:** `CallFunction` is arbitrary code execution → real brick risk. Guardrails are non-negotiable: validate the stub signature in QEMU first (zero risk), keep `GetMemory` RAM-only until proven, and flash routines strictly off-limits.

---

## Build items and their current state

Most of this is *finishing and wiring together pieces that already exist*, not greenfield.

| Item | Half | New or half-built? | Notes |
|------|------|--------------------|-------|
| Headless build→boot→trace→parse harness | A | New (thin) | Wraps existing `run_qemu.py` + `-d` flags; the parse/diff step is the only real new code |
| ML boots under QEMU (KerRLock:205 fix) | A | In-progress | The one hard technical task; likely pure-software (`current_task_addr`) |
| Trace parser / baseline-diff | A | New | Turns 100k-line traces into an LLM-readable summary; optional but high-value |
| peek-to-SD module | B1 | Half-built | Tens of lines; all pieces proven on this 6D2 |
| PTP `ptp_register_handler` stub | B2 | Half-built | Validate `0xE04BF152` in QEMU, then add stub; peek/poke/call code already written |
| Brick-safe guardrail layer (QEMU-first, allowlist) | B2 | New | Required before any real-hardware poke/call |

## Sequencing options (the fork)

- **Emulator-loop-first (recommended).** Build Half A, fix ML-under-QEMU, prove the headless loop with zero hardware and zero brick risk. Highest leverage, safest, unblocks the whole ML cycle. Then add B1, then B2.
- **Camera-tether-first.** Attack the real human bottleneck directly by building B2, so real-hardware iteration stops waiting on manual card/battery cycles. Faster payoff on the exact pain, but front-loads the brick risk.
- **Parallel.** Both tracks at once — maximum coverage, more moving parts.

## Autonomy & risk posture (a second fork)

- **Fully autonomous + guardrails (matches "almost completely automated").** LLM runs edit→build→run→diagnose→fix→commit on a branch unsupervised, stopping only for irreversible or brick-risk actions (hardware pokes/calls, force-push, GitHub/Discord/legal).
- **Supervised checkpoints.** LLM proposes each change and waits for approval before running or committing. Safer, more of Chris's attention, less automated.

## What stays with the human either way

Plugging in / handling hardware, inserting cards, power-cycling; pushing PRs under Chris's GitHub account; Discord dev-portal and any logging; buying tooling. Everything else runs without him.

---

## Why this direction is a strong candidate to sequence first

Every other candidate direction in VibePlan (JTAG, feature roadmap, upstream push, community) shares the same bottleneck: a human doing physical or account actions in the loop. This is the only direction whose *explicit goal is to shrink that bottleneck*. Building it first lowers the execution cost of all the others — e.g., a headless QEMU loop makes the paused features testable without a body session, and a validated PTP debugger makes body validation nearly hands-off. Whether "first" is right is for the full comparison to decide, but the leverage argument is why it was recorded first.

## Open decisions to resolve before planning

1. **How far into hardware-in-the-loop:** PTP tether (B2, max automation, brick risk) vs. peek-to-SD only (B1, safe) vs. QEMU-only for now (Half A alone).
2. **Autonomy/risk posture:** fully autonomous + guardrails vs. supervised checkpoints.
3. **Sequencing:** emulator-first (recommended) vs. camera-first vs. parallel.

These were surfaced but not yet answered — they belong in the plan-phase for this direction if it is chosen.

## Key references

- Full-visibility capability: `ml/src/log-d678.c` (DEBUGMSG.LOG), qemu-eos `run_qemu.py` + `-d io calls tasks debugmsg`.
- ML-under-QEMU gate: `[CPU1] ASSERT KerRLock.c:205`; `hw/eos/model_list.c:619` (`current_task_addr=0x28`, `fixme`).
- peek-to-SD: reuse `save_mem_to_file` / `core_dump_requested`.
- PTP debugger: opcode `0x9999`; stub candidate `ptp_register_handler` `0xE04BF152`; `GetMemory`/`SetMemory`/`CallFunction` already written.
- MMIO fidelity alternative (related, not part of this direction): `ml/src/io_trace.c` needs a DIGIC 7 port (~6 of 17 `CONFIG_DIGIC_VI` sites program a Cortex-R MPU region the 6D2's Cortex-A MMU lacks — needs a page-table patch, so it is a stretch, not an afternoon).
- Rationale and project state: `INTENT.md` in this folder; [../docs/jtag-research.html](../docs/jtag-research.html); [../PLAN_OF_ACTION.md](../PLAN_OF_ACTION.md).

---

## Addendum — reconciling with INTENT.md Layer 3 (evidence-first)

*Appended 2026-08-16 (Fable 5 session) after a peer session added Layer 3 to `INTENT.md` from the ML Discord evidence. This is a design constraint on direction 1, not a footnote.*

**The primary artifact of the loop is evidence + reasoning, not the diff.** Layer 3 establishes that the 6D2 is a *benchmark for an agent-driven RE method*, and the maintainers' feedback is binding: untested LLM patches are a net cost to them, they do not accept LLMs for PR review, and overclaiming ("first-ever raw video") poisoned even the true claims. So the harness must, on every iteration, emit a reasoned report — what it changed, *why*, what the trace actually showed, and an explicit split of *verified* vs *assumed* — with the diff as a secondary attachment. A loop tuned to maximize PR throughput actively damages the relationship the project depends on. Success is a *checkable* fix, not a *submitted* one.

**This direction is one of three faculties, not the whole method.** Per Layer 3, the agent-driven method needs perception/actuation, memory, and verification. Direction 1 is the **perception/actuation** faculty (trace-reading + peek/poke). It is necessary but not sufficient and must interlock with:
- **Memory** — the knowledge corpus (forum mirror, GitHub, codebase graph) so the agent stops re-deriving what the community already knows and can tell a dead end from an untried path. (See direction 5 / `direction-community-and-corpus.md`.)
- **Verification** — an adversarial self-check baked into the loop *before* a fix is presented as done (the same adversarial-wave pattern already used in this project), because the agent's output is "sometimes-false" and "tests pass" is not proof.

**Implication for sequencing:** a bare edit→build→run→fix loop is incomplete for the actual goal. The minimum viable version of direction 1 is edit→build→run→**verify (adversarial)**→**write evidence report**→commit. The verification and reporting steps are not polish; they are what makes the method's output trustworthy at fleet scale.
