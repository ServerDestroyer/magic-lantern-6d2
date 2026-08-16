# Plans in flight

**As of 2026-08-16.** Every plan alive in this project, whoever started it — the raw
inventory the candidate directions in [README.md](README.md) are assembled from. Grouped by
the component of the loop it serves (see [INTENT.md](INTENT.md) Layer 3).

Status vocabulary: **RUNNING** (work happening now) · **READY** (startable, nothing
blocking) · **BLOCKED** (waiting on something named) · **PAUSED** (deliberately stopped by
the JTAG scope decision) · **DONE** · **DEAD**.

---

## A. Perception — closing the hardware gap

| # | Plan | Status | Cost | Blocking on |
|---|---|---|---|---|
| A1 | **On-camera peek-to-SD module** (spike 011 rec. #1) | **READY** | ~tens of lines; all pieces proven on 6D2 | nothing |
| A2 | **USB PTP debugger** — peek/poke/call (spike 012) | **READY** (phase 1 desk-only) | stub validation + one body boot | nothing to start |
| A3 | **Emulator ground-truth loop, Track A** (spike 013) | **READY** | GDB scripts half-written | nothing |
| A4 | **Emulator ground-truth loop, Track B** (spike 013) | **BLOCKED** | batch camera session | needs A1 or A2 working |
| A5 | **JTAG on DIGIC 7** (spike 010) | **BLOCKED** | donor board + soldering + 1.8 V USB Blaster | a donor body Chris does not have |
| A6 | **UART crash console** (spike 014) | **DEFERRED** | ~$5 adapter + camera opened | pull off the shelf when a freeze yields a blank card log |

**Key facts already established, do not re-derive:**
- `ptp_register_handler` candidate **`0xE04BF152`** — inference, unverified; the ONE stub
  that lights up ML's already-written USB peek/poke/call. Validate in QEMU with a GDB
  breakpoint first (zero risk).
- **JTAG on Canon is solved on DIGIC 8** by kitor (Aug–Sep 2025): dual-core GDB on a
  PowerShot SX740, IDCODE `0x4ba00477`, published OpenOCD config and pinouts, pin-ID by
  resistance-to-ground signature. The 6D2 (DIGIC 7) has **no published pinout**, but is the
  same dual Cortex-A9 at 1.8 V — the method should transfer. **This is the novel
  contribution available.**
- **kitor asked for donor boards.** Collaboration may be cheaper than solo hardware work.
- Brick vectors: `CallFunction` is arbitrary RCE (flash/NVRAM = unrecoverable);
  `GetMemory` has zero address validation, MMIO reads can hang the bus → ERR80. RAM only,
  QEMU first.
- Halting the ICU makes the MPU throw ERR80; the DIGIC 7/8 watchdog-suppress address is
  unpublished.

## B. Memory — the knowledge corpus

| # | Plan | Status | Cost | Blocking on |
|---|---|---|---|---|
| B1 | **ML forum mirror from Wayback** | **RUNNING** (detached, resumable) | already started | nothing — check `~/ml-mirror/progress.log` |
| B2 | **Discord logging + GraphRAG** | **BLOCKED — legal/social** | see the memo | admin consent + a design that clears Discord's rules |
| B3 | **Codebase knowledge graph** (`ml-6d2`, `qemu-eos-hw`) | **DONE** | indexed | nothing |
| B4 | **JTAG-focused corpus over public sources** | **READY** | small | nothing |

**Key facts:**
- magiclantern.fm is Cloudflare-JS-challenged to every non-browser client; the mirror runs
  from Wayback, whose coverage ends ~2026-03-10 but spans essentially the whole forum.
- Discord is gated by its **Developer Policy rule 16** (no profiling users, identities, or
  *relationships between users* — that is the person-graph design) and **rule 21** (no
  training ML/AI models on message content without express permission). Full analysis:
  `docs/legal/2026-08-16-discord-logging-gdpr-memo.md`.
- The safe Discord design is a **citation index**: store the technical finding plus a link
  to the message, never the message text or the author.
- **B4 is the convergence point** — a JTAG corpus over the forum mirror + GitHub + the ROM
  serves the scoped work and needs nobody's permission.

## C. Verification and contribution

| # | Plan | Status | Notes |
|---|---|---|---|
| C1 | **Upstream PRs #294–#298** | **NEEDS REWORK** | maintainer wants #298 fixed at `PROP_LV_ACTION`, not a new-cam workaround |
| C2 | **qemu-eos PRs Q2/Q3/Q4** (spells, button codes, per-core interrupts) | **READY to submit** | the MPU spell set is the first DIGIC 7 one; the maintainer said the spells work is *interesting* and he never knew how to import MPU traffic |
| C3 | **Comment on upstream PR #223** (focus-box autohide) | **BLOCKED on Chris** | drafted at `.planning/prs/DRAFT-comment-on-upstream-PR-223.md`, classifier-blocked |
| C4 | **Retract the "first-ever raw video" claim** | **READY** | rejected by the maintainer; it taints the true claims |
| C5 | **Adversarial verification practice** | **RUNNING** | has refuted 3 of this project's own confident conclusions; keep |
| C6 | **"Volunteers check LLM output" scheme** | **IDEA ONLY** | maintainer's counter: *"I don't think LLMs are good enough to do PR review"* |

## D. Paused by the JTAG scope decision

Not dead — parked, with the work already banked so it can resume cheaply.

| # | Plan | Where it stopped |
|---|---|---|
| D1 | Lossless compression (spike 008) | Ghidra pass 3: real StateTransition is `0xDF00A192` in DryOS RAM; next step is decompiling `0xE02E839A(job)`. Payoff: sustained 1080p raw |
| D2 | Movie dual-ISO (spike 007) | Table identification NOT supported on review — an open 4-way choice; one adtglog2 capture at ISO 400 discriminates all four. Stills dual-ISO already works and ships hidden |
| D3 | Raw-video defects (spike 006) | fps header + re-arm both hardware-validated; pool shrink never reproduced |
| D4 | Feature matrix / cheap wins | `FEATURE_MATRIX.md`; the three `FEATURE_SHOW_*` flags break the startup-log allocation — keep them out of capture builds |
| D5 | QEMU boot ceiling | Stock firmware completes startup; real gate is `[CPU1] ASSERT SystemIF::KerRLock.c:205`. **Run every boot with `-d nochain`** — triples progress |

---

## Contradictions on the record

1. **Spike 011 says hardware-in-the-loop is not needed; the scope decision makes it the
   only work.** Both stand — see [INTENT.md](INTENT.md) §4. The objective is the method and
   the community's named bottleneck, not the fastest next feature.
2. **Chris wants LLM throughput; the maintainer wants fewer, better-evidenced
   submissions.** Unresolved. Affects C1/C2 directly.
3. **The Discord corpus is the most convenient memory source and the most legally
   constrained.** The forum mirror (B1) is neither — which is why it is running.
