# Direction 5 — Community collaboration + the knowledge corpus

**Recorded:** 2026-08-16 (Opus 5 session)
**Covers:** README direction 5, expanded. The README frames it as "ask kitor, stand up the
Discord logger". That undersells it: this is the **memory faculty** of the loop
([INTENT.md](INTENT.md) Layer 3) plus the cheapest known route to the JTAG pinout.

---

## The claim

Two of this project's hardest problems have the same solution, and it is not code.

1. **The 6D2 JTAG pinout does not exist publicly.** Direction 2 proposes to derive it by
   buying a donor body, desoldering, and probing resistance signatures. **kitor already did
   this work on DIGIC 8 and asked for donor boards.** Asking is one message; the hardware
   path is ~$200, a destroyed body, and weeks.
2. **The agent re-derives what the community already knows.** The forum, GitHub, and the
   Discord archive hold years of answers to questions currently being rediscovered by ROM
   archaeology.

## Part A — Collaboration

**What kitor has, confirmed** (ML forum topic 27350, retrieved via Wayback):

- Full dual-core GDB session on a PowerShot SX740 HS (DIGIC 8). IDCODE `0x4ba00477`, 6
  breakpoints, 4 watchpoints, GDB server on :3333, registers dumped from a *running*
  camera.
- Published OpenOCD dual-Cortex-A9 SMP config, verbatim in-thread.
- The pin-ID method: resistance-to-ground signature — TDI/TCK/TMS/TDO ≈ 100–200 kΩ,
  /TRST ≈ 10 kΩ pulldown.
- Pinouts for SX740, EOS R, EOS RP, with PCB photos at kitor.pl/eos/jtag/.
- **He asked for donor boards.**

**Why this transfers:** DIGIC 7 is the same dual Cortex-A9 at 1.8 V with the same ROM map;
qemu-eos models D7 and D8 identically. **The 6D2 has no published pinout — producing one is
a genuinely novel contribution**, and it is the specific thing names_are_hard said would
"help a lot".

**The moves, cheapest first:**

1. Reply in the JTAG thread with the DIGIC 7 gap and ask whether anyone has probed a 6D2.
   Cost: one message. Both red-teams in spike 011 endorsed this.
2. Ask kitor directly whether a 6D2 board would be useful to him, and whether he will share
   the probing procedure for a body he does not have. Converts direction 2 from solo
   hardware work into collaboration.
3. Only if both fail: buy the donor body (direction 2, Phase 1).

**Cost of asking: near zero. Cost of not asking: the entire direction-2 budget.** This
should happen before any hardware is purchased, and it is currently nobody's task.

**Handled correctly, this is also relationship repair.** The first contact was a bot
request that read as data extraction, followed by an LLM-formatted status post that
overclaimed. Arriving with "here is the DIGIC 7 gap, can I help close it" is the opposite
posture, and it is honest.

## Part B — The corpus

Three sources, in descending order of value-per-unit-of-friction.

### B1 — ML forum mirror · RUNNING

magiclantern.fm is Cloudflare-JS-challenged to every non-browser client (curl, wget, and
curl_cffi with Chrome TLS impersonation all get 403). The mirror therefore runs from the
Wayback Machine: `~/ml-mirror/wayback_mirror.py`, detached, resumable, progress in
`~/ml-mirror/progress.log`. Coverage ends ~2026-03-10 because Archive.org's crawler was
blocked in March, which still spans essentially the whole forum history.

**This is already the highest-value corpus and it needs no permission from anyone.** It is
where kitor's JTAG thread came from.

### B2 — GitHub · READY, not started

Issues, PRs, review comments, and commit history across magiclantern_simplified and
qemu-eos. Public API, built for this, no Cloudflare, no developer-policy problem. The
highest-signal record of *why* changes were made — exactly the "reasons why the code worked
in the first place" Chris named as his goal.

### B3 — Discord · BLOCKED, and the constraint is not the one everyone assumed

Full analysis: [../docs/legal/2026-08-16-discord-logging-gdpr-memo.md](../docs/legal/2026-08-16-discord-logging-gdpr-memo.md).

- **Discord's Developer Policy binds regardless of GDPR.** Rule 16 forbids using API data
  to profile users, their identities, **or their relationships with other users** — that is
  the GraphRAG-over-people design, described almost exactly. Rule 21 forbids using message
  content to train ML/AI models including LLMs without express permission.
- Retrieval at query time updates no weights and is defensibly not "training". **Never
  fine-tune or train embeddings on this corpus.**
- GDPR itself is a weaker constraint than assumed: no EU establishment, so it turns on Art
  3(2)(b) "monitoring of behaviour" — **identity-preserving designs are in scope,
  extract-the-finding-and-discard-identity largely is not.** Stripping usernames does *not*
  exit scope (Recital 26); dropping the message and keeping the technical proposition does.
- names_are_hard set conditions, not a refusal. Most of them (public privacy policy,
  deletion on user request, GDPR compliance) are already required of every bot operator by
  Discord's Developer ToS §5 — worth saying back to him.

**The safe design, if it happens at all: a citation index.** Store the technical finding
plus a link to the message; never the message text, never the author. Deletion is free —
the link dies with the message. Fewer lines than the logger already written.

### The recommendation for Part B

**Build a JTAG-scoped corpus over B1 + B2 only.** It serves the scoped work, needs nobody's
permission, and defers the entire Discord question. If the JTAG corpus proves the value of
the memory faculty, that is a far better argument to bring back to the server admins than
the one that was brought the first time.

---

## How this direction relates to the others

| Direction | Relationship |
|---|---|
| **1 — Automation harness** | Complementary. The harness is perception + hands; this is memory. Neither substitutes for the other. |
| **2 — JTAG on DIGIC 7** | **Part A may replace most of it.** Ask before buying hardware. |
| **3 — Feature roadmap** | Paused; the corpus makes resuming cheaper but does not unblock it. |
| **4 — Upstream push** | Part A is the same relationship. Arriving as a collaborator makes the PR conversation easier; arriving with more untested patches makes it worse. |

## What only Chris can do

- Post in the forum thread / message kitor (personal account — agents prepare, Chris sends).
- Decide whether a donor body gets bought at all, and whether to ask before buying.
- Any renewed approach to the Discord admins.

## Honest weaknesses of this direction

- **It produces no camera feature and no code.** Judged on shipped functionality it looks
  like zero progress.
- **Part A depends on a stranger's goodwill**, immediately after a first contact that
  landed badly. It may simply get no reply.
- **The corpus is speculative infrastructure.** The claim "the agent re-derives what the
  community knows" is plausible and mostly unmeasured. Worth one concrete test — pick three
  questions this project burned real time on and check whether the forum already answered
  them — before investing further.
