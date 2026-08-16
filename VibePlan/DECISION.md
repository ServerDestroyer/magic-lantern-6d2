# DECISION — which direction gets the effort, and in what order

**Written:** 2026-08-16
**Judged against:** [INTENT.md](INTENT.md), all four layers, with Layer 4 §4.5 as the explicit
objective function.
**Inputs read in full:** [README.md](README.md), [PLANS-IN-FLIGHT.md](PLANS-IN-FLIGHT.md),
[DIRECTION.md](DIRECTION.md), and all five direction files —
[direction-automation-harness.md](direction-automation-harness.md),
[direction-jtag-hardware.md](direction-jtag-hardware.md),
[direction-feature-roadmap.md](direction-feature-roadmap.md),
[direction-upstream-contribution.md](direction-upstream-contribution.md),
[direction-community-collaboration.md](direction-community-collaboration.md).
**Underlying evidence re-checked, not paraphrased:** spikes 004, 011, 012, 013 and the manifest;
[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/ROADMAP.md](.planning/ROADMAP.md);
the qemu-eos source at `/home/chris/ml6d2/qemu-eos`; live GitHub PR state; the running mirror.
**New measurements taken while writing this file are marked [measured 2026-08-16].**

This is a decision, not a menu. The recommendation is in §2. The case against it is in §7, and
it is a real case.

---

## 0. The three findings that changed the ordering

Everything below follows from the objective function in INTENT Layer 4 §4.5, plus three things
I checked myself today that the direction files did not have.

### 0.1 Direction 1's headline unlock rests on a suspect I can refute at the desk

Direction 1 names its single most valuable item as *"get ML itself to boot under QEMU past the
`[CPU1] ASSERT KerRLock.c:205` gate. Prime suspect: the single global `current_task_addr=0x28`
on a 2-core machine (`hw/eos/model_list.c:619`, marked `fixme`)."* That suspect is repeated in
[INTENT.md](INTENT.md) step 4, [PLANS-IN-FLIGHT.md](PLANS-IN-FLIGHT.md) D5, and the task brief.

**[measured 2026-08-16]** A recursive grep of the whole qemu-eos tree for `current_task_addr`
returns exactly ten sites outside the model table:

| File | Use |
|---|---|
| `hw/eos/model_list.h:93` | the struct field |
| `hw/eos/eos.c:2199, 2207` | `eos_get_current_task_name()` |
| `hw/eos/eos.c:2233, 2240` | `eos_get_current_task_id()` |
| `hw/eos/eos.c:2275, 2282` | `eos_get_current_task_stack()` |
| `hw/eos/dbi/logging.c:1629, 1635` | task-switch detection for `-d tasks` |
| `util/log.c:320` | the help string for `-d tasks` |

Every one of them is **host-side introspection**. The field is read by QEMU *about* the guest,
via `cpu_physical_memory_read`, to annotate trace lines with a task name. **No guest instruction
ever reads it, and nothing in the machine model depends on it.** The KerRLock assert is printed
by Canon's own ASSERT printer at ROM `0xE0040EFC` — it is the *guest* asserting about *guest*
state. A host-side logging address cannot cause it.

Two corollaries, both load-bearing:

- **The cause of the KerRLock assert is unknown, not "suspected."** The remaining candidate
  classes are guest-visible: per-core banked CP15 state, GIC per-CPU interface modelling,
  LDREX/STREX exclusive-monitor behaviour under SMP, or a lock-owner field the second core reads.
  None has been investigated. Budget for it as open-ended reverse engineering, not as a
  one-field fix.
- **[measured 2026-08-16]** `current_task_addr = 0x28` appears **9 times** in `model_list.c` —
  every DIGIC 7/8 body shares it, including the 200D immediately above the 6D2 entry. So even if
  it were worth changing, it is not a 6D2-only change. It is shared-code, cross-model, untestable
  here — the exact shape [direction-upstream-contribution.md](direction-upstream-contribution.md)
  §5 says must not be submitted as a patch.

This does not kill direction 1. It relocates its value: the *harness* half is cheap and already
paying (spike 004's entire measurement chain came out of exactly that tooling), while the
*ML-boots-to-menu* half is a research project of unknown length behind at least four sequential
gates — KerRLock → `SCS_Initialize` (flag `0x40000`) → sequencer stages 3–5 → WINSYS writes
`_rgb_vram_info` → `my_big_init_task` runs. Spike 004 §7 measured every one of those; only the
first is even named.

### 0.2 The unanswered maintainer question is now a day old

**[measured 2026-08-16, live `gh` query]** PR #297 carries one comment, by `reticulatedpines`,
posted `2026-08-16T12:07:05Z`, still unanswered. PR #298 carries exactly one comment, authored by
`ServerDestroyer` — confirming
[direction-upstream-contribution.md](direction-upstream-contribution.md) Correction 1: the
maintainer's #298 objection exists only on Discord and is invisible on the public record. #294,
#295 and #296 have zero comments.

The #297 question — *"Have you done any testing in this area?"* — has a specific, currently
unflattering answer, and the accompanying question (*"possibly a clock multiplier / divisor?"*,
his own words in commit `ffef459f0d`) has a good answer already derived at the desk. Leaving both
unanswered while starting a new direction is the single cheapest way to make every other
direction that touches these people more expensive.

### 0.3 The corpus is further from useful than the plans assume

**[measured 2026-08-16, ~2.5 h into the run]** PID 2185613 is still in CDX enumeration at **page
290 of 309, 45,516 unique URLs**. `~/ml-mirror/site/` contains **zero files**; total footprint
16 KB. The tail is full of Wayback 503s.
[direction-community-collaboration.md](direction-community-collaboration.md) §B.1 measured
260/309 earlier today and extrapolated ~17 minutes for the remaining 49 pages; 30 pages have taken
longer than that, because of retries. Its 15–25 h download estimate is if anything optimistic.

Consequence for sequencing: **nothing may be planned on the strength of the mirror this week.**
Anything needed from the forum in the next few days must come from a targeted Wayback print-view
fetch of a known topic — which is the method that produced the kitor finding in the first place,
and which costs two minutes.

---

## 1. The comparison, on the axes that decide it

Columns are the objective function from Layer 4 §4.5, plus the two constraints that bind
everything (money/brick risk) and the dependency question.

| | **1 Automation harness** | **2 JTAG on DIGIC 7** | **3 Feature roadmap** | **4 Upstream push** | **5 Community + corpus** |
|---|---|---|---|---|---|
| **Unattended fraction** (§4.1) | **95%** for Half A (desk/QEMU only); ~70% for the USB channel after one install | **15–20%**, all front-loaded in Phase 0, then hard stop | ~85% of labour, but **capped** by 5–7 body sessions, strictly ordered at 2 points | ~85% of labour, **0% of delivery** | 85–90% of labour; strand B is **100%** and already running |
| **Human-gate type** | **None** for Half A. **Physical** (one card install + one boot) for the USB channel | **Purchase, then physical** — the hardest kind. Sourcing, buying, opening, probing, soldering | **Physical** (body sessions) + **account** (#223 comment) | **Account** only — every artifact leaves via Chris's GitHub/Discord | **Account** only (forum needs a browser; Cloudflare blocks non-browser clients) |
| **Money** | **$0** | **$80–$600** ($30–400 tooling, $60–400 donor body; the repo's own "~$200" assumes a bench nobody has checked) | **$0** | **$0** | **$0** |
| **Brick risk** | Zero for Half A and peek-to-SD. **Real** for `CallFunction` — arbitrary RCE, flash/NVRAM = unrecoverable | N/A to the working body **by construction** — the donor is a camera that never takes another picture | **None structural** anywhere in the queue. All writes are heap copies; `apply_patches()` memcmps the pre-image and fails closed; worst case is ERR70/80 → battery pull | **None** | **None** |
| **Ends in a visible camera capability?** (§4.3) | **No** — infrastructure. The USB channel is a *method* artifact, not a camera feature | **No.** A pinout, an IDCODE, maybe a GDB prompt. Four conditional hops to any feature | **Yes — by construction.** The only direction whose deliverables *are* camera capabilities | **No** | **No.** Explicitly cannot satisfy §4.3 alone |
| **Serves the maintainers' named bottleneck?** | **Partially, and cheaply** — a live peek/poke channel on a running D7 body is hardware in the loop with no solder. *Inference: he named JTAG as the route, "physical hardware in the loop" as the bottleneck* | **Yes, most directly**, and it is the one artifact immune to every "untested LLM output" objection | Partially — items 0 and 4's measurement are exactly the "bug report with reasoning" mode | **No — it consumes their bottleneck.** Review attention from a one-person team | **Yes, twice** — strand A funds the JTAG answer; strand D supplies the "multiple physical cams" he says LLMs cannot |
| **What it unblocks** | Desk A/B of every feature enable; the spike-005 pool interaction; item 5's plumbing; spike 013 Track B; the 5 genuinely hardware-bound questions | **Nothing on this roadmap.** The repo's own finding, from two independent red-teams (spike 011) and [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/docs/jtag-research.html](docs/jtag-research.html) §05 | HDR video (Chris asked by name), sustained 1080p24/25/30 raw, cropmarks, four stale features | Nothing technically. The **debt** half unblocks every direction that touches these people | Potentially **all of direction 2's budget** for the price of one message |
| **Score against §4.1** | **1st** (Half A) / 2nd overall | **5th, not close** — it converts queued work into human-gated work | 3rd | 4th | 2nd |

**What the table says that no single direction file could.** Directions 2, 4 and 5 all draw on
*the same non-replenishable account*: goodwill with four named people, spent through Chris's
identity. Directions 1 and 3 draw on *Chris's hands*. Only direction 1's Half A draws on nothing
scarce at all. That is the real dependency structure, and it is why the answer is a sequence with
one item on each scarce resource, not a winner.

---

## 2. The recommended sequence

Seven steps. Steps marked **∥** run concurrently because they consume different scarce resources.
Steps that must not overlap are called out explicitly.

### Step 0 — Pay the debt. Today. Hours, not sessions. *(direction 4, debt half only)*

Answer #297; post the retraction in the same message; put the #298 objection on the PR thread so
the public record is honest; correct the four published superlatives (`.planning/ROADMAP.md`
line 68, `patches/README.md` §0007, `.planning/prs/PR-Q2-…md` line 26, and a correcting commit for
`5c009d7`, which cannot be edited).

**Why first, and why not on ROI grounds.** This is owed, and unpaid it degrades directions 2, 5,
and item 1 of direction 3 — all of which need the same people. It is also, on its merits, the
strongest single play available: the #297 answer is a derivation from numbers already in the
maintainer's own tree (commit `ffef459f0d`), showing both the 6D2 and the 200D running a common
master clock with integer **/2, /3, /6** dividers to within 0.6%, which answers the question he
wrote himself. That is a bug report with reasoning, delivered as an answer to his own question
rather than as another patch — precisely the mode Layer 3 says is welcome.

**Cost:** ~3–4 hours of drafting (mostly done inside
[direction-upstream-contribution.md](direction-upstream-contribution.md) §2–§4), plus ~10 minutes
of Chris's time to send.
**Unblocks:** step 5 (the forum ask) — do not send a cold ask into a thread while an unanswered
question from the same community sits open.

### Step 1 ∥ — The desk queue. Starts the same day, no permission needed. *(directions 1, 3, 5)*

Four tracks, all unattended, all with different failure modes, none competing for a scarce
resource:

**1a — build the S1 body-session package.** *(direction 3)* Build `adtglog2.mo` for `6D2.111`
from `ml/modules/dev_tools/adtglog2/` — **[measured 2026-08-16]** it carries
`hooks_thumb_6D2.c`, so it is genuinely 6D2-ported, and it appears in no `modules.included`, so
it is build-and-copy-by-hand. Add the ~10-line `diag_log` probe inside `fps_get_current_x1000()`
to the daily build. Stage the experimental `features.h` build as a **separate second sync**
(`FEATURE_LV_FOCUS_BOX_AUTOHIDE` + `FEATURE_CROPMARKS` with `IMGPLAY_ZOOM_LEVEL_ADDR 0x2CBC` +
`FEATURE_SHOW_FREE_MEMORY` + `FEATURE_DISK_LOG` + `FEATURE_STICKY_HALFSHUTTER`), so Part A's
measurement runs on a known-good build and is protected from an untested one.
**[measured 2026-08-16]** `ml/platform/6D2.111/features.h:25` still reads
`//#define FEATURE_CROPMARKS // wants IMGPLAY_ZOOM_LEVEL_ADDR`, and lines 51–53 still carry
spike 005's A/B with the three `FEATURE_SHOW_*` flags commented out — batch all edits into one
change or they collide.

**1b — the JTAG/community Phase 0, which is one task, not two.** *(directions 2 and 5 share it)*
Re-retrieve ML forum topic 27350 and topic 7531 posts 38–43 via direct Wayback print-view fetch;
grep for `donor` to settle whether "kitor asked for donor boards" is real — it is asserted in four
places in this repo and supported by no primary source; and read kitor's photos to answer the
question nobody has asked: **are the EOS R/RP JTAG pads on the FZC-8 service connector, or on
separate pads?** If they are elsewhere, the 6D2's 8-pin FZC-8 is the wrong place to look and the
whole pin-economics argument is aimed at the wrong target. Then run the ROM0 watchdog/ERR80 static
search, which converts the forum message from an ask into an offer.

**1c — validate `0xE04BF152` in QEMU.** *(direction 1)* GDB breakpoint during a stock 6D2 boot;
confirm the `(id, handler_fn, priv)` signature and the ~175 registration call sites. Free, zero
risk, and it is the gate on the whole USB channel. If it is the wrong function, the ADR/BL hunt
re-runs at no cost.

**1d — the harness itself, and the corrected KerRLock question.** *(direction 1, Half A)* Wrap
`run_qemu.py` + `-d io calls tasks debugmsg nochain` into a build→boot→capture→parse loop with a
baseline diff. This is thin and it is the tooling that already produced spike 004's results.
Re-open the KerRLock investigation with `current_task_addr` **removed** from the suspect list per
§0.1, and treat it as open-ended — do not schedule around it.

**Cost:** ~4–6 agent sessions total, $0, zero of Chris's time.
**Unblocks:** step 2 (S1 cannot run without 1a), step 3 (needs 1c), step 5 (needs 1b).

### Step 2 — Body session S1. ~40 minutes, two card syncs, four queue items closed. *(direction 3)*

Part A on the known-good daily build: the `adtglog2` dual-ISO block discriminator (movie LiveView,
raw video on, dual-ISO **off**, ISO 200 → 400); the `fps_get_current_x1000()` probe self-recording
to `RAWDIAG.LOG`; the custom-WB discriminator that was never run from session 5; and copy
`ML/SETTINGS/dual_iso.cfg` off the card — a file copy that answers outright which index produced
the measured +1.71 EV, and without which **no honest EV claim about dual-ISO can be made at all**.
Part B after the second sync: focus-box autohide, cropmarks, free memory / disk log / sticky
half-shutter, `selftest` last.

**Why this is the highest-value 40 minutes anywhere in the folder.** It converts four queued
diffs into shipped camera capability, takes the one measurement that decides item 4, closes a
contributor PR that has waited since 2025-08-31, and produces the visible camera capability
§4.3 demands. Every test in it self-records except the two that need eyes on the LCD — which is
§4.4's lesson applied.

**Hard precondition:** the forced-rebuild incantation and the `strings`-on-`build/zip/` check
from `patches/README.md`. `make clean` does not rebuild modules; a rev-2 build has already once
shipped a rev-1 `.mo` with an identical size and a fresh mtime.

**Must not overlap with:** any other body session. S1 is the only claim on Chris's hands in this
sequence.

### Step 3 ∥ — The USB peek channel: one card install, then live silicon at the desk. *(direction 1, Half B)*

Only after 1c validates the stub. Add `THUMB_FN(0xE04BF152, ptp_register_handler)`, build
`CONFIG_PTP`, and **bundle it into the same card image as the peek-to-SD module** so one install
buys two capabilities and a fallback. Read-only `GetMemory` on known RAM first. `SetMemory` and
`CallFunction` stay off until read-only is solid, and flash/NVRAM-touching functions stay off
permanently.

**Why this position.** This is the only item in the entire folder that *structurally* converts
human-gated work into queued work in the §4.1 sense: after one boot, an agent reads registers off
the running camera at 3 a.m. with Chris asleep. It is simultaneously the cheapest credible answer
to the maintainer's named bottleneck and the most legible possible demonstration of the method.

**Honest limits, stated up front.** qemu-eos emulates no USB PTP transport at all (spike 012
confirms zero PTP source under `hw/eos`), so only the stub address and signature are
QEMU-validatable — the round trip is body-only. `0xE04BF152` is inference, not proof. And ML
PR #262 (750D `ptp_register_handler` stub) has been open and unreviewed since 2026-05-01, so
someone else is on the same track and may get there first.

**Gate:** Chris must agree to run `CONFIG_PTP` on the body once. That is open question §6.7.

### Step 4 — Movie dual-ISO, decided on S1's evidence, not before. *(direction 3 item 4)*

The diff is ~6 lines of constants written **RAM-relative** (`PHOTO_CMOS_ISO_START - 0xb30 +
0xef4`) — a bare ROM address is a silent no-op on this body, per upstream's own comment at
`dual_iso.c:1148-1156`. Kill it immediately if S1's capture shows a `buf_addr` outside all six
`0x304` base records or the `0x305` record, or a `reg 0x10` word of `10717620`/`10717e20`; and
kill it if the capture names block 2, because testing block 2 requires relaxing the `0x0d03`
sanity gate that is the only thing stopping a wrong address writing gain nibbles into unrelated
registers.

This is the step that answers Chris's own question — *"can we do HDR video?"* — with the answer
that exists on this body.

### Step 5 ∥ — The forum ask, once the debt is paid and the premise is verified. *(direction 5 strand A)*

One message to topic 27350: the DIGIC 7 gap, the two questions, and the offer of the ROM0
watchdog search. Chris sends from a browser. Then wait. No bump, no DM chaser, no cross-post.

**Sequencing constraint that is easy to get wrong:** steps 0 and 5 both spend the same goodwill
budget and must be at least 72 hours apart, with the debt going first. Do not run direction 4's
*investment* half (the qemu-eos submissions) in this window at all.

### Step 6 — Lossless LJ92, as background desk work throughout, escalating only if 2–4 land. *(direction 3 item 5)*

Its next steps are all static and need no camera, so it costs nothing to keep running underneath
everything else. Start with the passive `StartJob` hook (M1 local 1, cell `0xE090EB2C`, handler
`0xE0327E88`) during a normal still capture — read-only, and the correct first experiment. Then
the stills path via `silent.mo`'s `save_lossless_dng`, which isolates *"does the encoder work"*
from *"can we steal it during recording."*

Honest expectation: **6–10 agent sessions of which 2–4 are body sessions, with a genuine
probability of terminating at "stills lossless DNG works, movie integration blocked by LiveView
contention."** That outcome is still worth having. It is not sustained raw video.

### Where JTAG Phase 1 goes: nowhere, until two things happen

Direction 2's Phase 0 is already inside step 1b — it is the same task as strand A's ROM search.
Phase 1 does not get scheduled until (a) Chris answers whether he will buy a donor body, and
(b) the forum ask has had three weeks. This is not "JTAG is dead." It is **JTAG's next executable
action is a message and a ROM search, not a purchase** — which direction 2's own Part 5, both of
spike 011's red-teams, and direction 5's strand A all say independently.

### What is being dropped outright

- **Direction 4's investment half** (fork qemu-eos, submit Q2/Q3/Q4) — deferred behind open
  question §6.3. Q1 must never be filed: it is a strict subset of `qemu-eos` PR #18, open since
  2026-06-17.
- **The Discord logger** — abandoned, not deferred. Delete the application
  (`ml-devlog-readonly`, client ID 1538248909204226158); a registered app with a live token and
  no purpose is a standing liability.
- **GraphRAG over the forum corpus** — do not build it. Run direction 5's 3-question test when
  the mirror finishes; 0 of 3 means the corpus is a library, not a lever.
- **`io_trace.c` DIGIC 7 port** — ~6 of 17 `CONFIG_DIGIC_VI` sites program a Cortex-R MPU region
  the 6D2's Cortex-A MMU does not have. Multi-session RE for the wrong tool.
- **Chasing `IMGPLAY_ZOOM_LEVEL_ADDR`'s real value** — enable cropmarks with the placeholder seven
  sibling ports already use; finding the true address buys playback overlays and nothing else.

---

## 3. Trade-off (a) — the JTAG scope decision paused a producing track

**The decision was right about the target and wrong about the ordering, and the pause bought
nothing.**

Right about the target: the maintainers named hardware-in-the-loop as *their* bottleneck,
unprompted, and a measured DIGIC 7 pinout is the one artifact in this folder immune to every
objection they have raised about LLM output. Layer 3 makes that binding. Nothing else here is a
direct answer to something a maintainer asked for.

Wrong about the ordering, for a specific reason: **JTAG's next executable action is unattended
desk work and one message.** The bench phase cannot start until Chris buys a donor body, and
nobody has asked him whether he will. So the pause did not free a critical path — it stopped a
track that produced, in one night, dual-ISO confirmed on the body, cr2hdr merging end to end,
stock firmware reaching full startup in QEMU, ML exonerated as the emulator blocker, and five
PRs, in exchange for a track whose first four weeks are identical whether the pause happened or
not. That is the §4.6 inversion, paid for and not used.

**The condition under which the pause would have been right:** if Chris had already bought a
donor body and blocked out bench time, so that JTAG had a real critical path competing for his
attention and for build-and-instructions effort. Then serialising would be correct, because two
tracks would be contending for the same scarce resource. Today they are not: one contends for
agent sessions (not scarce) and the other for a purchase decision (not made).

**The narrower condition, stated so it can be acted on:** if the forum ask returns *"nobody has
probed a DIGIC 7, and here is what to watch for,"* and Chris says yes to a donor body, then JTAG
Phase 1 becomes the right primary claim on his hands — and at that point direction 3's remaining
body sessions should genuinely be paused, because a bench session and a shooting session are the
same resource.

---

## 4. Trade-off (b) — maintainer trust is depletable and PR throughput spends it

The numbers, all verified in
[direction-upstream-contribution.md](direction-upstream-contribution.md) §1 and re-checked live
today:

- The team is **one person**: 26 of 28 `dev` commits in 90 days are `stephen-e`.
- External merges: 11, 10, 11, 5, 6, then **0 in 2026**. Last merge 2025-11-12.
- 21 PRs open. **Chris's five are 24% of the queue, filed in 14 hours**, by a contributor who had
  publicly said *"It is llm slop! I didn't even review the code or the explanation."*
- **[measured]** The two PRs with 617/628-word bodies are exactly the two that drew *"I have to
  read 4 over-confident paragraphs."* The three at 107–174 words drew nothing.

Three consequences the sequence enforces rather than hopes for:

1. **One outward artifact per 72 hours, bug reports outnumbering patches 2:1, under ~200 words.**
   Volume is the harm and volume is the one dimension Chris can audit perfectly.
2. **Directions 2, 4 and 5 spend the same account and must be sequenced against one budget.**
   This is the single most common way this folder's plans could go wrong: three files each
   describing a "cheap" outreach action, executed in the same week, adding up to four messages to
   the same four people.
3. **The realistic landing path is not "he merges my PR" — it is "he rewrites it and pushes it
   himself."** He said so: *"It should be pretty easy to cleanup and push."* That reframes a good
   submission as *a finding clean enough that reimplementing it is cheap*, not a mergeable diff.
   It is also why step 0's #297 answer is worth more than any patch in the queue.

And the gate, because §4.2 says Chris cannot audit the register he delegated: **a claims ledger
(every assertion tagged verified / inferred / unknown with its file, address or measurement), a
one-line commitment disclosure at the top of every draft, a mechanical superlative grep, and
Chris sends — always.** He approves the *promise*, not the prose. That ledger would have caught
both "first-ever raw video" (unverifiable in principle) and "kitor asked for donor boards"
(unknown, no source). The classifier that blocked the #223 comment was doing this job by
accident; making it a rule turns a lucky catch into a designed one.

---

## 5. Trade-offs (c) and (d)

### (c) The method versus the camera capability that makes it legible

Layer 3: the 6D2 is the benchmark for an agent-driven RE method, not the deliverable. Layer 4
§4.3: a direction producing no visible camera capability cannot demonstrate the method. Both are
true and the resolution is not to choose between them — it is to notice which directions satisfy
neither.

- **Direction 3 produces a camera capability every session** and demonstrates the method only
  weakly, because "an LLM enabled a `#define` seven other ports already have" is not a striking
  result.
- **Direction 1's USB channel demonstrates the method most strikingly** — an agent reading
  registers off a running camera unattended — and produces no camera feature.
- **Directions 2, 4 and 5 produce neither**, individually. Direction 2's terminal artifact is a
  pinout on a camera that will never take another picture.

So the pair that satisfies both readings is **3 + 1c**, which is what the sequence builds. The
directions that satisfy neither are exactly the ones the sequence reduces to their cheapest
executable move (2 → a message and a ROM search; 4 → the debt half; 5 → strand A plus the mirror
running for free).

**The honest counterweight, and it is real:** to the ML maintainers specifically — the audience
Layer 3 makes binding — a DIGIC 7 pinout is *more* legible than another feature. Direction 2 fails
§4.3 as written while partially serving the reason §4.3 exists. That tension is not resolved by
this document; it is deferred to the donor-body answer, which is the honest place for it.

### (d) What happens to each direction if Chris does NOT buy a donor body

| Direction | Effect |
|---|---|
| **1 Automation harness** | **Unaffected.** Nothing in Half A, peek-to-SD, or the USB channel needs a second body |
| **2 JTAG** | **Collapses to Phase 0 + one forum message** — which is a subset of direction 5. Per its own kill criterion #2, the file should then be *closed*, not kept alive as an aspiration |
| **3 Feature roadmap** | **Unaffected.** Every item runs on the working body |
| **4 Upstream** | **Unaffected** |
| **5 Community** | **Unaffected, and strand A's value rises** — it becomes the only remaining route to a DIGIC 7 pinout, and a negative reply becomes a genuinely useful result because it prices a decision |

**One question gates exactly one direction — and it is the direction currently holding the
scope.** That is the strongest structural argument in this document for asking it before anything
else is re-planned around JTAG.

---

## 6. Open questions only Chris can answer

Framed as decisions with consequences, so each is a sentence to answer.

1. **Buy a donor body — yes, no, or not yet?** *Yes* → JTAG Phase 1 becomes schedulable and
   competes with direction 3 for body time; a dead **200D/800D/77D is $60–150 versus $150–400 for
   a 6D2** and answers the generation-level question just as well. *No* → close
   [direction-jtag-hardware.md](direction-jtag-hardware.md) and fold its Phase 0 into direction 5.
   *(Layer 3 lists this under "what Chris has NOT said"; nobody has asked.)*
2. **Do you own an oscilloscope and a multimeter?** Recorded nowhere in this repo, and it swings
   direction 2's tooling cost by an order of magnitude ($30 vs. $400). Also decides whether the
   UART path (spike 014) is nearly free.
3. **Does upstream contribution matter for its own sake, or only as evidence the method works?**
   *For its own sake* → fork qemu-eos, submit Q2, and item 5's 6–10 sessions are justified.
   *Only as evidence* → publish in your own public repo, submit nothing further, and item 5 stops
   being a contribution strategy and becomes a personal-capability item.
4. **Is the method meant to become a product, a public writeup, or stay private?** Decides whether
   the credit question matters at all — if kitor does the JTAG work, the contribution is his, and
   that only costs something under one of the three answers.
5. **How many 20–40 minute body sessions are available, and on what cadence?** Direction 3 needs
   5–7 for the full queue, 2 for everything except lossless. If they are not available on a
   coherent timescale, the honest move is to run S1 alone, bank items 0–3, and park the rest
   rather than leaving a second half-executed track.
6. **Budget and timeline.** Never stated, anywhere, in four layers of intent.
7. **Will you run `CONFIG_PTP` on the body once?** One card install, one boot, read-only reads
   first, battery-pull recoverable, stub QEMU-validated before it touches the camera. *Yes* →
   step 3 proceeds and the project gets its 3 a.m. hardware channel. *No* → the USB channel dies
   and peek-to-SD (menu-edit, re-trigger, pull the file per address) is the fallback.
8. **Will you create a `qemu-eos` fork?** You have none — `gh repo list ServerDestroyer --fork`
   returns four, and `qemu-eos` is not among them. Only needed if §6.3 is answered "for its own
   sake."
9. **Do you accept the outward-communication gate?** Claims ledger + one-line commitment
   disclosure + superlative grep + 72-hour cadence + you always send. This is the thing you *can*
   consent to, given that §4.2 says you cannot audit the wording.
10. **Will you copy `ML/SETTINGS/dual_iso.cfg` off the card at S1?** Trivial, and it is the only
    thing that makes any dual-ISO EV claim honest — the measured +1.71 EV corresponds to no menu
    index and the index actually used is currently unknown.

---

## 7. The strongest objection to this recommendation

**Objection:** *This is drift wearing a sequence's clothes.* The whole reason VibePlan exists is
that Chris asked for the plans to stop competing and for one direction to be built out. This
document answers by keeping all five alive — four concurrent desk tracks, a body session, a USB
channel, an outreach message, and a background RE project — and calls it an ordering. Whatever
its faults, the 2026-08-16 JTAG scope decision had one virtue this recommendation lacks: **it was
a decision to stop doing things.** A sequence in which nothing is cancelled is not a decision.

**This is the right objection and it deserves a real answer, not a reframe.**

**Answer, in three parts.**

**(i) The test is not how many labels are live; it is how many things compete for a scarce
resource.** There are exactly three scarce resources in this project: Chris's hands, the
maintainers' attention through Chris's accounts, and agent sessions. The sequence puts **one**
item on his hands (session S1), **one** track on the goodwill account (the debt, then a 72-hour
cadence), and everything else on agent sessions — which are the one resource that is not scarce,
and which Chris asked three times in one session to have used while he is absent. Concurrency on
a non-scarce resource is not drift; it is the direct answer to §4.1. What *would* be drift is two
body-session tracks or two outward-communication tracks at once, and the sequence forbids both
explicitly.

**(ii) Things are actually being cancelled, and they should be named as cancellations rather than
deferrals.** The Discord logger is abandoned and its application deleted. GraphRAG is not built.
Q1 is never filed. The `io_trace.c` port is dropped. The hunt for the real
`IMGPLAY_ZOOM_LEVEL_ADDR` is dropped. Direction 4's entire investment half is parked behind a
question. **And JTAG Phase 1 — the direction that currently holds the scope — is explicitly not
scheduled.** That last one is the substance of the decision, and it should be read as a
cancellation-until-answered, not a "later."

**(iii) The part of the objection I concede.** If Chris's answer to §6.5 is "one body session a
month," this sequence is too wide and should be cut to steps 0, 1a, 1b and S1, with everything
else parked — because at that cadence direction 3's queue cannot stay coherent and direction 1's
USB install competes with S1 for the same rare slot. I do not know his cadence; nobody has asked.
**The width of this sequence is contingent on an answer nobody has, and if the answer is
"rarely," narrow it on the spot.**

**A second objection, briefly: I am deprioritising the one thing a maintainer directly asked
for.** Partly true, and the answer is that I am not deprioritising the *bottleneck*, only the
*route*. His words name "getting the physical hardware in the loop" as the hard part and JTAG as
the route he can see. A working USB peek/poke channel on a running DIGIC 7 body is a different
route to the same bottleneck, needs no solder, no donor and no purchase, and — *my inference, not
his claim* — scales better across owners than a per-body pinout does, because every ML user
already owns a USB cable. Step 3 is therefore an attempt at his bottleneck, not a retreat from it.
If he says plainly that JTAG specifically is what he wants and USB is not interesting, that is
new evidence and the sequence should change.

---

## 8. What would make me abandon this recommendation

Written now so it cannot be rationalised away later.

1. **Chris answers §6.5 with a body cadence of roughly one session a month or less.** Cut to steps
   0, 1a, 1b and S1; park directions 1c, 4-investment, and item 5. The sequence's width is not
   defensible at that cadence.
2. **The maintainer asks for a pause** — any message of the form "please stop opening PRs."
   Stop immediately, close the open PRs, and drop directions 4 and 5 entirely. There is no version
   of this project worth being the person who burned out the last maintainer.
3. **A second overclaim ships after the retraction.** Halt all outward communication and fix the
   gate before another word leaves.
4. **`0xE04BF152` is wrong and the re-hunt produces no candidate within two sessions.** Step 3
   dies; peek-to-SD becomes the read channel and the sequence loses its §4.1 centrepiece — at
   which point direction 3 alone is the honest recommendation.
5. **S1 reproduces the spike-005 allocator-pool zeroing on a second feature enable.** The cheap-win
   category has stopped being cheap; stop enabling features one at a time and understand the
   interaction first.
6. **S1's capture shows no mapped block is the movie dual-ISO table.** Step 4 dies rather than
   being tried blind against blocks 1/2/3.
7. **kitor or coon replies offering to do the DIGIC 7 JTAG work.** Stop the solo hardware path the
   same day and ship a board. This is the cheapest possible outcome and it is a success, not a
   failure.
8. **Four weeks pass with no artifact that changes what the camera does.** That is this sequence
   failing at §4.3, and the correct response is to collapse to direction 3 alone and ship
   something.
9. **Two consecutive Chris-gated steps each slip more than two weeks.** §4.1 is telling you the
   sequence is wrong for this project regardless of its merits.

---

## 9. Start here tomorrow

### Runs unattended — begins immediately, needs no permission and no hardware

1. **Draft the #297 reply.** The derivation is done
   ([direction-upstream-contribution.md](direction-upstream-contribution.md) §3): the honest
   "no cross-model testing was possible — one body, one ROM" plus the /2, /3, /6 divider reading,
   under 200 words, with a claims ledger attached for Chris. Flag the 200D `TG_FREQ_BASE 84000000`
   discrepancy as a **question**, not a claim.
2. **Draft the retraction** and prepare the three file edits plus the correcting-commit message.
   **Do not commit — the main session commits.**
3. **Re-retrieve topic 27350 and topic 7531 posts 38–43** by direct Wayback print-view fetch. Grep
   for `donor`. Read kitor's photos for the FZC-8 question. ~2 minutes for the grep; budget for
   Wayback 503s.
4. **Build the S1 card package** — `adtglog2.mo` for `6D2.111`, the `fps_get_current_x1000()`
   probe on the daily build, the batched experimental `features.h` build as a separate sync. Verify
   with `strings` on `build/zip/`, never the source tree.
5. **Validate `0xE04BF152` in QEMU** — GDB breakpoint during stock boot, confirm signature and the
   ~175 call sites.
6. **Write S1's instructions as an artifact**, every button name checked against
   [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/docs/6D2_CONTROLS.md](docs/6D2_CONTROLS.md).
   Two camera sessions have already been lost to instrumentation and instruction defects.
7. **Add the URL-completeness check** to `~/ml-mirror/wayback_mirror.py` — a count-and-compare
   against a fresh `showNumPages` at the end. It is the difference between "the forum doesn't
   mention it" and "we didn't download that page." Otherwise leave the mirror alone.
8. **Re-open the KerRLock question** with `current_task_addr` struck from the suspect list (§0.1),
   and record the refutation somewhere the next session will find it.

### Needs Chris — in this order

1. **Send the #297 reply and the retraction** (same message, retraction first). ~10 minutes. This
   is the most time-sensitive item in the folder; the question has been open since
   2026-08-16T12:07Z.
2. **Answer §6.1 — donor body, yes/no/not yet.** One word. It closes or schedules an entire
   direction.
3. **Answer §6.5 — how many body sessions, and how often.** It sets the width of everything above.
4. **Run session S1** (~40 minutes, two card syncs) when the package and the instructions are
   ready.
5. **Post the forum message** from a browser — magiclantern.fm is Cloudflare-challenged to every
   non-browser client, so no agent can post it — at least 72 hours after step 1, and only once the
   donor-board premise has been verified or dropped.
6. **Do not post the #223 comment until S1 is actually on the calendar.** It promises your time on
   a public thread; an unfunded public promise costs more than silence.
7. **Delete the Discord application** `ml-devlog-readonly` (client ID 1538248909204226158).
8. **Create a `qemu-eos` fork only if §6.3 is answered "for its own sake."**

---

## 10. Corrections this document makes to the folder

Recorded here rather than edited into the source files, which are owned elsewhere.

1. **`current_task_addr = 0x28` is not a candidate cause of the KerRLock assert**, and should be
   struck from [INTENT.md](INTENT.md) step 4, [PLANS-IN-FLIGHT.md](PLANS-IN-FLIGHT.md) D5, and
   [direction-automation-harness.md](direction-automation-harness.md). It is read only by
   `eos_get_current_task_name/id/stack()` and `dbi/logging.c`'s task-switch detector — host-side
   introspection, never by the guest. It also appears 9× in `model_list.c`, so it is not a 6D2
   field.
2. **Direction 1's "single most valuable unlock" should be re-costed** as open-ended RE behind four
   sequential gates, not as a one-field fix.
3. **The mirror is at CDX page 290/309 with 45,516 URLs and zero pages downloaded** as of ~14:00
   today; direction 5's own extrapolation is optimistic because of Wayback 503 retries.
4. **`README.md`'s candidate table lists direction 5's full build-out as
   `direction-community-and-corpus.md`.** The full version is
   [direction-community-collaboration.md](direction-community-collaboration.md); the older file is
   the summary and disagrees with it on the donor-board claim.
5. **PR #298's only comment is ServerDestroyer's own cross-reference** — re-verified live today,
   confirming direction 4's Correction 1. The maintainer's objection remains invisible on the
   public record.

---

## 11. Key references

- The objective function this decision is scored against: [INTENT.md](INTENT.md) Layer 4 §4.1–§4.6.
- The four scarce-resource claims: [direction-feature-roadmap.md](direction-feature-roadmap.md)
  "The body-session budget"; [direction-upstream-contribution.md](direction-upstream-contribution.md)
  §1; [direction-community-collaboration.md](direction-community-collaboration.md) §E;
  [direction-jtag-hardware.md](direction-jtag-hardware.md) Part 8.
- ML's real stopping point in QEMU, measured with gdb, and the four gates behind it:
  [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/004-ml-boot-in-qemu/README.md](.planning/spikes/004-ml-boot-in-qemu/README.md)
  §3–§8.
- The "we do not need hardware-in-the-loop to move the roadmap" reframe, from two independent
  red-teams:
  [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/011-hardware-in-the-loop/README.md](.planning/spikes/011-hardware-in-the-loop/README.md).
- The USB channel's plan and its honest limits:
  [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/012-usb-debugger-bringup/README.md](.planning/spikes/012-usb-debugger-bringup/README.md).
- The self-reducing emulator loop the USB channel feeds:
  [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/013-emulator-groundtruth-loop/README.md](.planning/spikes/013-emulator-groundtruth-loop/README.md).
- Build traps that must be honoured before any card sync:
  [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/patches/README.md](patches/README.md).
- Control names for every instruction written for Chris:
  [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/docs/6D2_CONTROLS.md](docs/6D2_CONTROLS.md).
- qemu-eos source checked today: `/home/chris/ml6d2/qemu-eos/hw/eos/eos.c:2197-2290`,
  `hw/eos/dbi/logging.c:1629-1638`, `hw/eos/model_list.c` (6D2 entry and the nine `0x28` entries).
