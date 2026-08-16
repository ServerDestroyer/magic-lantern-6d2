# VibePlan — Choosing the Direction for Magic Lantern on the Canon 6D Mark II

**Created:** 2026-08-16
**Purpose:** There is more than one plan in flight for this project. This folder lays the candidate directions side by side so we can compare them honestly and commit to the single best one, instead of drifting between them.

This is a *decision workspace*, not the project's status ledger. The live status ledger stays in [../.planning/ROADMAP.md](../.planning/ROADMAP.md) and [../PLAN_OF_ACTION.md](../PLAN_OF_ACTION.md). VibePlan is where we decide *what to point the effort at next*.

---

## How to read this folder

1. **`INTENT.md`** — Chris's intent and everything known behind it (project state, the key findings from the 2026-08-16 investigation session, the constraints). Read this first; every direction is judged against it. **Layer 3** was appended by a second session and carries the ML Discord evidence — Chris's own statement of his objective, and the maintainers' binding feedback.
2. **`PLANS-IN-FLIGHT.md`** — the raw inventory every direction is assembled from: all 20+ live plans with status, cost, and dependencies, plus the contradictions between them, stated openly.
3. **`direction-*.md`** — one file per candidate direction. Two are built out today (1 and 5); the rest are summarized below and get full files when we build them out.

---

## Candidate directions

| # | Direction | One-line | Human-gated? | Brick risk | Status here |
|---|-----------|----------|--------------|------------|-------------|
| 1 | **Automation harness** | Close the dev loop around the LLM: edit→build→run→read-trace→diagnose→fix, on emulator and (optionally) tethered camera | Partially removes it | Only the PTP-tether option | **Fully recorded** → `direction-automation-harness.md` |
| 2 | **JTAG on DIGIC 7** | Establish a live IDCODE + dual-Cortex-A9 GDB debug session on the 6D2 | Heavily (donor body + ~$200 tooling) | N/A (donor body) | Summarized below |
| 3 | **Feature roadmap continuation** | Ship the paused camera features (movie dual-ISO, zoom-addr unblock, focus-box autohide, cheap-win enables, lossless raw) | Yes (body-test sessions) | Low | Summarized below |
| 4 | **Upstream contribution push** | Push and shepherd the 5 ML + 4 qemu-eos PRs; respond to maintainers | Yes (Chris's GitHub account) | None | Summarized below |
| 5 | **Community + knowledge corpus** | Ask kitor for the DIGIC 7 pinout instead of buying a donor body; build the corpus (forum mirror + GitHub) that stops the agent re-deriving known answers | Yes (Chris's accounts) | None | **Fully recorded** → `direction-community-and-corpus.md` |

Direction 1 is deliberately the one recorded in full first, because it is the one that *reduces the human gating shared by all the others* — see `INTENT.md`.

---

## Direction summaries (not yet fully built out)

### 2 — JTAG on DIGIC 7
Establish hardware debug on the 6D2's dual Cortex-A9. kitor's Aug-2025 DIGIC 8 method (OpenOCD dual-A9 config, IDCODE `0x4ba00477`, resistance-signature pin-ID) transfers. **This became the active goal on 2026-08-16.** Split: a software-only **Phase 0** (retrieve kitor's forum thread via Wayback; statically search ROM0 for the DIGIC 7 MPU-watchdog / ERR80 fault path) can start now with zero hardware; **Phase 1** bench work needs a donor body (never the working camera) plus ~$200 tooling, both of which only Chris can supply. Honest framing from [../docs/jtag-research.html](../docs/jtag-research.html): JTAG **blocks nothing already planned** — its value is organizational (a self-checking hardware-verification path the maintainer asked for) and insurance (inspecting a wedged body, a few register-level questions). Overlaps direction 1: JTAG is the *maximal* hardware-in-the-loop path; the automation harness reaches most of the same day-to-day value without a probe.

### 3 — Feature roadmap continuation
The paused camera features, cheapest-first: **movie-mode dual-ISO** (~6-line diff + one adtglog2 body capture), **`IMGPLAY_ZOOM_LEVEL_ADDR`** (one ROM address unblocks cropmarks + SET-maindial + fast LV focus box + half of raw-zebras — best value-per-address), **focus-box autohide** (1-line enable, already hardware-tested upstream on a 6D2), **cheap-win enables** (free-memory, disk-log, console-to-UART, sticky half-shutter, low-risk modules), and the big one, **lossless (LJ92) raw compression** for sustained 1080p recording (Ghidra RE ~60–70% done, 8–14 sessions remaining). Every item needs either a body-test session or QEMU-past-GUI — which is exactly what direction 1 automates.

### 4 — Upstream contribution push
Five ML PRs are already open (#294 MOV limit, #295 D678 prop-wait, #296 log-d678 no-brick-spin, #297 measured-fps MLV header, #298 re-arm-after-autostop) plus a drafted comment on #223. Four qemu-eos PRs are drafted and verified-applying (ML_PLATFORM_DIR, 6D2 MPU spells, 6D2 button codes, per-core interrupts) but not yet pushed. Needs Chris to push under his GitHub account and respond to maintainer feedback.

### 5 — Community + knowledge corpus
**Now fully recorded → `direction-community-and-corpus.md`.** Headline finding: **ask kitor before buying any hardware.** He has a working dual-core GDB session on DIGIC 8, published the pinouts, OpenOCD config, and the resistance-signature pin-ID method — and he asked for donor boards. One message may replace most of direction 2's ~$200-and-a-destroyed-body budget, and this is currently nobody's task. Second half is the corpus (memory faculty): the forum mirror is already running from Wayback, GitHub is untouched and free, and Discord stays parked — the binding constraint there is Discord's Developer Policy rules 16 and 21, not GDPR.

---

## Decision status

**Not decided.** This folder exists to reach a decision. Today's deliverable (per Chris) is: record direction 1 in full, plus intent and context. The next step is to build out directions 2–5 to the same depth (or prune the ones we reject), then pick the best single direction — likely a *sequence*: which one first, which it unblocks.

**Standing observation to test during comparison:** directions 2, 3, 4, and 5 all share the same bottleneck — a human doing physical/account actions in the loop. Direction 1 is the only one whose explicit goal is to *shrink that bottleneck*. That makes it a strong candidate to sequence first, because it lowers the cost of executing every other direction. Whether that holds is what the full comparison should decide.
