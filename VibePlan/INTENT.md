# Intent & Context — Automating the Vibe-Coding Loop

**Recorded:** 2026-08-16
**Recorded by:** Claude (Fable 5), from Chris's stated intent and the investigation done this session.

This file captures *why* we are doing this and *everything known behind it*, so any later reader (or a future planning session) can judge each candidate direction against the real intent rather than a paraphrase.

---

## Chris's intent, in two layers

**Layer 1 — the immediate ask.**
Make the vibe-coding development loop for this Magic Lantern 6D2 project *almost completely automated*. Concretely: let the LLM run the full cycle — edit code → build → run → read everything the firmware actually did → diagnose → fix → commit — on its own, so Chris stops being the person who manually builds, reads logs, and swaps SD cards on every iteration. Chris should be left with only the steps that are physically or legally his.

Chris's own words across the session: *"make the vibe coding process more or almost completely automated"* and, earlier, *"this way the llm can have access to everything the code did or did not do."*

**Layer 2 — the meta ask.**
There is more than one plan in flight. Chris wants all the ideas laid out and compared so we can *build out the single best direction* rather than half-pursuing several. This VibePlan folder is that comparison workspace. Recording the automation direction first is not a decision to pursue it — it is the first entry in the comparison.

---

## The chain of reasoning that produced this intent

This intent did not appear from nowhere. It came out of a four-question investigation this session. The steps:

1. **"Can we do raw memory dumps and give the LLM everything the code did?"**
   Finding: yes, and the strongest form is *not* a raw memory dump (those are opaque binaries needing disassembly). It is the **QEMU execution trace** — `run_qemu.py 6D2 -d io calls tasks debugmsg 2> trace.log` — which emits, as plain text an LLM reads directly, every MMIO register access, function call, task switch, and Canon `DebugMsg`. The on-camera equivalent is `DEBUGMSG.LOG` from `ml/src/log-d678.c` (opt-in `CONFIG_STARTUP_LOG` build). So full LLM visibility into "what the code did" already exists and is under-used.

2. **"Could the in-camera DEBUGMSG.LOG get almost all the same readouts as JTAG?"**
   Finding: it gets the *semantic half* (boot flow, tasks, asserts, MPU/property traffic, call-site LRs) and beats JTAG there. It cannot do JTAG's defining tricks: arbitrary register/memory/MMIO reads on demand, breakpoints/watchpoints, and inspecting a *wedged* machine. The right non-JTAG substitute for the MMIO half is `ml/src/io_trace.c` (needs a DIGIC 7 port), not DEBUGMSG.LOG.

3. **"Are the JTAG-only gaps blockers for getting everything planned working?"**
   Finding (grounded in the repo's own red-teams and [../docs/jtag-research.html](../docs/jtag-research.html)): **No.** None of the three JTAG-only capabilities is on the critical path. Every shipped feature landed with no debug port; the one real emulation blocker that ever existed was closed by non-JTAG means (real body-captured MPU spells in patch 0007 + a per-core interrupt fix in patch 0008, derived by static ROM decode); ROM dumping is done. The famous "nobody could determine" register questions in `PU1_INVESTIGATION.md` turned out to be *emulator artifacts* of a QEMU interrupt-model bug, valid on real silicon.

4. **The real blockers, once JTAG was ruled out as a blocker.**
   What actually stands between the project and "everything planned working" is mundane and human:
   - **Things only Chris can do** — push the 9 drafted PRs under his GitHub account; post the #223 comment; source a donor body and buy JTAG tooling; Discord dev-portal setup.
   - **Paused feature work** — several features are "paused by scope," not blocked, and each needs a body-test session or QEMU-past-GUI.
   - **One genuine in-progress technical gate** — making ML *itself* boot under QEMU (stuck at `[CPU1] ASSERT KerRLock.c:205`; prime suspect the single global `current_task_addr=0x28` on a 2-core machine).

**The conclusion that became the intent:** the bottleneck is the *human in the loop*, not a missing technical capability. So the highest-leverage thing to build is the machinery that removes the human from the loop — an automation harness. That is Layer 1.

---

## Where the project actually stands (context for judging any direction)

- **Milestone 1 is essentially complete** per its own definition of done: QEMU boots stock 6D2 firmware to full startup (473→1581 debugmsg lines); `FEATURE_MATRIX.md` classifies every missing feature with 0 unknowns; not one but five upstream PRs are open.
- **Hardware-confirmed camera features already shipped:** MOV/MP4 30-min-limit override, 14-bit 1080p raw video (first ever on a 6D2), dual-ISO stills (+1.71 EV measured), re-arm-after-autostop, measured-fps MLV header, debug displays.
- **Emulation firsts produced:** the first-ever DIGIC 7 MPU spell set (`mpu_spells/6D2.h`, ~175 spells), 6D2 button codes decoded statically from ROM0, and a per-core interrupt fix for qemu-eos.
- **ROM dumps are done and verified** (`roms/6D2/{ROM0,ROM1}.BIN`, 2025-09-29, fw 1.1.1).
- **The 6D2 ML platform port** (`ml/platform/6D2.111`) builds, boots on the body, and has all debug-relevant stub addresses known.

## The tension this intent sits inside

On **2026-08-16 a scope decision narrowed all active work to "JTAG and what connects to it,"** pausing lossless compression, movie dual-ISO, further QEMU boot work, and PR follow-ups. That chosen goal (JTAG bringup) is itself entirely hardware-gated and has not started its bench phase.

So there is a live tension the comparison must resolve: **the currently-chosen direction (JTAG) is the most human/hardware-gated one, while the automation intent points at removing exactly that gating.** These are not necessarily in conflict — automation could make the JTAG work (and everything else) cheaper to execute — but the sequence matters, and that is what VibePlan is for.

---

## Constraints that bind every direction

- **Brick risk.** The PTP `CallFunction` path is arbitrary code execution on the real camera. Any hardware-poke/call capability ships only with guardrails: validate in QEMU first, flash routines off-limits, RAM-only until proven.
- **Never flash our own build to the body until QEMU passes** — the platform README says this code has never run on a real camera; this rule predates and survives all of this.
- **Copyright.** Canon firmware is copyrighted; `roms/` and `Backup SD card/` are gitignored and never committed or redistributed.
- **Don't format the ML SD card in-camera** — it wipes the card-side boot flags.
- **Human/legal actions stay with Chris** — GitHub pushes, Discord dev-portal + logging (Developer-Policy constrained), hardware purchase and handling.
- **Upstream norms** — maintainers want reasoned bug reports and tested patches, not untested LLM output. Automation must produce *evidence*, not just diffs.

---

## What "done" would look like for the automation intent

Chris can hand the LLM a feature or bug, walk away, and come back to a branch with the change made, built, run, its trace read, the diagnosis written, and the fix committed — having been asked to intervene only for a physical action (plug in the camera, insert a card) or an account/legal action (push the PR). The loop that produces that is direction 1, recorded in full in `direction-automation-harness.md`.

---

# Layer 3 — the intent behind the intent

*Appended 2026-08-16 by a second session (Opus 5), from the ML Discord thread of
2026-08-15/16 (`../docs/discord/2026-08-16-ml-discord-thread.md`) — evidence the sections
above did not have. Claims are marked **[stated]** (Chris's own words) or **[inferred]**.*

## The 6D2 is the benchmark, not the deliverable

**[stated, Discord 8:29 AM]** Chris disclosed his actual objective to the maintainers:

> "My only goal was to see if I could spin up enough LLMs to see if I could make as much
> as possible work with little to no work on my part. I'm pretty convinced that most of
> the hard work has been done for many of the cameras and letting an LLM attempt to Brute
> Force its way to working code may in fact work."

> "My goal is to get it wired up to working even if it's poor. Then set up a review
> process to see if any of those fixes were correct and put it on loops for getting out
> the rest of the bugs and optimizing the code and the reasons why the code worked in the
> first place."

**[inferred, high confidence]** The camera is the test fixture for a method: can a fleet of
LLM agents autonomously advance a hardware reverse-engineering project? This is the same
conclusion Layer 1 reached from a different direction — "the bottleneck is the human in the
loop" is the *symptom*; "I am building an agent-driven RE method and the human is the part
I have not automated yet" is the *goal*. **Layer 1 and Layer 3 agree, and that agreement is
the strongest evidence either is right.**

It also explains behaviour that looks irrational under a camera-first reading — chiefly the
JTAG scope decision, which the project's own red-team found is not roadmap-blocking.

## Chris's model of an LLM, and the three gaps it implies

**[stated]** *"I think of llms as like an idiot savant — given enough tries they can
probably figure a lot of this Nitty Gritty stuff out, they just need the right environment,
and people need to know the things that they absolutely cannot do."*

**[inferred]** Every piece of infrastructure started in this project maps to one of three
missing faculties:

| Faculty | What's missing | What was built or attempted |
|---|---|---|
| **Perception / actuation** | The agent cannot observe or poke the real device | JTAG (010), USB PTP debugger (012), peek-to-SD, UART (014), MPU spell capture (005), and the trace-reading harness of direction 1 |
| **Memory** | The agent re-derives what the community already knows, and cannot distinguish a dead end from an untried path | Discord logger + GraphRAG, ML forum mirror, codebase knowledge graph |
| **Verification** | The agent produces confident, sometimes-false work that nobody can check at scale | Adversarial verification waves, red-teams, the "volunteers check LLM output" idea |

**[stated, 8:40 AM]** On verification: *"there may be a way to set up volunteers to help
debug the LLM slop as you have so many people that want to help but don't know how to
code. It's possible I could make it so the outputs could go over what to check for the
volunteers."*

**[stated]** One belief already updated: *"I was hoping to build out a process for the llm
to... be just pointed at one camera and it sort of knows what to do. It's looking like
that's not the case as there are too many specifics for each camera."* The
one-pipeline-fits-all idea is abandoned.

## What the maintainers actually said — binding on every direction

1. **The bottleneck they name is hardware in the loop** — *"really for us I think the hard
   part is getting the physical hardware in the loop... We have strong suspicions that
   most cams have jtag, but we have only a few examples of people working with jtag on
   these cams. If we could find a way to consistently connect to jtag, that would likely
   help a lot."* This is the origin of the JTAG scope decision, and it is why that decision
   is coherent despite JTAG blocking nothing: **it is the community's stated bottleneck,
   not ours.**
2. **Untested LLM patches are a net cost to them** — *"You spend less time, PR reviewer has
   to spend quite a lot more time. This is painful in open source projects especially,
   where there are often very few devs."* Requested mode: **bug reports with reasoning**,
   not speculative fixes. On PR #298 specifically he wants `PROP_LV_ACTION` fixed properly
   rather than a new-cam workaround.
3. **LLMs are not accepted for review** — *"I don't think LLMs are good enough to do PR
   review."* This directly limits the "volunteers + LLM triage" scheme above.
4. **Overclaiming poisons the true claims** — "first-ever raw video on a 6D2" was rejected,
   and the rejection made him doubt "all of this is tested on a real body" as well.
5. **Bulk-copying the server's messages is condition-gated, not refused** — GDPR
   conformance. Full analysis: `../docs/legal/2026-08-16-discord-logging-gdpr-memo.md`.

**[inferred]** Any automation harness must therefore emit *evidence and reasoning as its
primary artifact*, with the diff as a secondary attachment. An automation loop that
maximises PR throughput actively damages the relationship this project depends on. This is
a design constraint on direction 1, not a footnote.

## What Chris has NOT said — ask before committing

- Whether the method is meant to become a product, a public writeup, or stays private.
- **Whether he will buy a donor 6D2 body** — this alone gates the entire JTAG hardware
  path (direction 2).
- Whether upstream contribution matters for its own sake or only as evidence the method
  works. The two motives predict different behaviour when they conflict.
- Budget and timeline. Never stated.

---

# Layer 4 — intent evidenced by the working session itself

*Appended 2026-08-16 by the session that executed the 2026-08-15 night work (raw video,
dual-ISO, QEMU startup, 5 PRs). Layers 1–3 were written from investigation and from the
Discord thread. This layer is different in kind: it is what Chris's **behaviour while
directing actual work** revealed, which is evidence the other layers could not see.
Claims marked **[stated]** are his words from that session; **[inferred]** is my reading.*

## 4.1 The ask that repeats — "what can you do without me?"

Across one session Chris asked, in these words:

- **[stated]** *"Do you have enough to work on a bunch of parts without me for some time?"*
- **[stated]** *"ok is there anything left that you can do without me?"*
- **[stated]** *"is there more you can do, without me"*

Three times, unprompted, the same question. Not "what should we build" — **"what can proceed
while I am not here."** This corroborates Layer 1 from the strongest possible source (revealed
preference, not stated preference), and sharpens it: the automation Chris wants is not
primarily about *speed*, it is about **decoupling progress from his availability**.

**[inferred]** The design consequence is specific and differs from a generic "close the loop"
harness: the highest-value automation is whatever converts a *human-gated* task into a
*queued* one. A change that makes an LLM iteration 3× faster is worth much less to him than a
change that lets an iteration happen at 3 a.m. while he sleeps.

## 4.2 "I don't know the correct terminology" — the expertise ask

**[stated]**, when asked what to post on GitHub:

> *"I was wondering what to comment on github not discord. I dont know all the correct
> terminology for what you might do/should do so that is what I was asking for you to do and
> push to my github."*

This is not a request for labour. It is a request for **domain and social judgement** — what
is worth saying to a maintainer, in what register, and where. In the same session he also
asked *"what should we do on github?"* and *"what do i click"* / *"how do I switch from NTSC
to PAL"*.

**[inferred, high confidence]** Chris's model of the division of labour is: **he supplies the
hardware, the accounts, and the goals; the LLM supplies the expertise** — including
open-source etiquette, the right terminology, and the judgement of what to do next. This is a
materially larger ask than "automate the build loop," and it is mostly **not** satisfied by
tooling. It is satisfied by an agent that knows the domain's norms.

It also creates an exposure the harness design must handle: **Chris cannot easily catch a
wrong call in that layer**, because not knowing the terminology is precisely why he delegated
it. When the classifier blocked a comment that would have promised his time to a stranger's
PR, that block was doing work he could not do for himself. **Any automation of outward-facing
communication needs a human-meaningful gate — not because Chris wants to approve wording, but
because he cannot audit it after the fact.**

## 4.3 The camera is a means, but the footage is not fake

Layer 3 concludes the 6D2 is a benchmark for the method, not the deliverable. The working
session supports that but adds a qualifier that matters for prioritisation. Chris asked:

- **[stated]** *"are we still working to make the video look and work correctly?"*
- **[stated]** *"can we do HDR video?"* … *"which ones are known to give the best results in
  order?"* … *"would 2 be easy is what I was thinking"*
- **[stated]** *"is Dual-ISO raw going to be hard from here or do we need to do more of the
  RAW dump to get it to work better?"*

These are the questions of someone who **wants working video out of his camera**, asked with
genuine feature curiosity and a sense of cost. They are not benchmark questions.

**[inferred]** Both readings are true and they are not in tension: the method is the goal, and
a *real* capability on a *real* camera is what makes the method's success legible — to
Chris, to the maintainers, and to anyone he later shows it to. The practical rule: **a
direction that produces no visible camera capability cannot demonstrate the method, however
technically sound it is.** This is an argument against a long pure-infrastructure phase with
nothing shippable at its end, and it is the strongest counterweight in the folder to the JTAG
scope decision.

## 4.4 Evidence about how he actually works — constraints for any harness

Observed, not stated:

- **He runs the camera tests himself and reports honestly**, including *"I may or may not have
  done all the tests correctly."* An automation design that assumes clean human execution will
  mis-analyse. The fix that worked was making the *firmware self-record* (`RAWDIAG.LOG`)
  instead of asking him to photograph the screen — **move the evidence-capture into the
  machine, not into the instructions.**
- **He corrected the instructions themselves**: *"I think your directions don't sound correct
  to the model I even have… you may want to look up what the buttons are on Canon."* Which
  produced `docs/6D2_CONTROLS.md`. **Instructions to the human are an artifact that needs the
  same rigour as code**, and getting them wrong burns a whole camera session.
- **Two camera sessions were wasted on instrumentation defects** the machine could have caught
  (34 log lines self-evicting from a 21-line console; a diagnostic print behind a guard that
  was already false). Human-session time is the scarcest resource in the project, and it was
  lost to *our* bugs, not his.
- **He interrupts and redirects freely** (several mid-turn interrupts, model switches). The
  harness should be **interruptible and resumable**, not a long uninterruptible batch.

## 4.5 What this layer adds to the comparison

1. **Decoupling from Chris's availability is the real objective function** (§4.1) — rank
   directions by how much queued, unattended work they create.
2. **The LLM must supply domain judgement, not just labour** (§4.2) — and outward-facing
   actions need a gate, because he cannot audit them.
3. **Every direction should terminate in a visible camera capability** (§4.3), or it cannot
   serve the meta-goal.
4. **Body-session time is the scarcest resource** (§4.4) — automation that protects it
   (self-recording firmware, verified instructions, batched test plans) outranks automation
   that merely accelerates desk work.

## 4.6 A tension Layers 1–3 record but do not resolve, restated with evidence

The 2026-08-16 scope decision paused this session's entire workstream — and that workstream
then produced, in one night: dual-ISO stills confirmed on the body, cr2hdr merging them
end-to-end, stock firmware reaching full startup in QEMU (473→1581, then 4770 with
`-d nochain`), ML itself exonerated as the emulator blocker, the lossless encoder mapped to
function level, and five upstream PRs.

That is not an argument that JTAG is wrong — the maintainers named hardware-in-the-loop as
*their* bottleneck (Layer 3), and that is a real reason to work on it. It is an argument that
**the paused track was not stalled, and pausing a producing track to start a hardware-gated
one inverts §4.1**: it trades queued unattended work for work that cannot start until Chris
buys a donor body. Whatever sequence is chosen, this trade should be made deliberately and
on the record, not by drift.
