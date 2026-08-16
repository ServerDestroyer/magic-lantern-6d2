# DECISION-REDTEAM — adversarial review of `DECISION.md`

**Written:** 2026-08-16
**Posture:** adversarial by assignment. I assumed the recommendation was wrong and tried to
demonstrate it. Where it holds, I say so — a red team that finds nothing correct is not
credible, and there is a lot in `DECISION.md` that survives contact with the primary sources.
**Target:** [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/VibePlan/DECISION.md](VibePlan/DECISION.md), §0–§11.
**Not edited:** `DECISION.md`, `README.md`, `INTENT.md`, `PLANS-IN-FLIGHT.md`,
`direction-automation-harness.md`. Nothing committed.

**What I re-derived rather than read:** the `current_task_addr` grep against
`/home/chris/ml6d2/qemu-eos` (mine agrees with §0.1's counts and disagrees with its
conclusion — §7.1); spike 004's assert evidence file; spike 008's own revised session
estimates; spike 011's ranking; `ml/platform/6D2.111/features.h`;
`ml/tools/card-flags/edit_card_flags.py`; the contents of `Backup SD card/ML/SETTINGS/`;
a `git grep` for the retracted superlative; and one live `gh pr view 297 --comments`.

**What I could not verify:** the state of the physical SD card today (I can only read the
2025-09-29 backup and the project's own memory record); Chris's body-session cadence; anything
about his budget. Those gaps are load-bearing and I flag them where they are.

---

## 0. Verdict up front

**The recommended sequence does not survive as written.** Its skeleton does — debt before
outreach, exactly one body session, JTAG Phase 1 unscheduled, agent work in parallel — and I
would keep all four of those. But three of its seven steps carry defects that cost real
resources if executed:

- **Step 0 would ship a retraction that is itself false.** It names four published sites for
  the retracted claim. A `git grep` over tracked files finds **seven**, including line 77 of
  the repository's own public front-page `README.md`. Posting *"I've taken it out of my notes"*
  while three uncorrected copies remain live is DECISION.md's own abandon-criterion #3 firing
  on the day of the retraction. §2.1.
- **Step 2 (session S1) cannot load ML as specified.** The card has been in stock-boot mode
  since 2026-08-16 at Chris's request; `BOOTDISK`/`EOS_DEVELOP` were cleared from both exFAT
  VBRs. Neither S1 nor its "hard precondition" mentions re-arming them. §4.1.
- **Step 2 contains a task whose input file does not exist.** `ML/SETTINGS/dual_iso.cfg` was
  never written. This was established and recorded in project memory at 11:48 on 2026-08-16,
  24 minutes before `DECISION.md` was written at 12:12, and `DECISION.md` promotes it to a
  named question for Chris (§6.10) and a step in S1. §5.2.
- **And its headline finding draws the wrong action from correct evidence.** §0.1's mechanism
  is right — `current_task_addr` is host-side introspection and cannot cause a guest assert.
  Its prescription (§10 correction 1: strike it from three files) is wrong. The project's own
  evidence file shows the field **is** demonstrably mislabelling CPU1's trace lines, which
  corrupts the exact traces step 1d's harness is built to read. §7.1.

The amendment is in §10. It keeps the skeleton, cuts step 1 from four tracks to two, deletes
one step outright, and adds two artifacts that cost nothing and are currently in nobody's plan.

---

## 1. Axis 1 — is the objective function right?

### 1.1 The alternative reading, stated at full strength

`DECISION.md` scores every direction against INTENT Layer 4 §4.1 — *decoupling progress from
Chris's availability* — and the §1 table's bottom row is literally **"Score against §4.1"**.
The brief's challenge is whether that is Chris's objective or an artifact of him asking "what
can you do without me" three times on a night he was busy.

The alternative reading is: **§4.1 is a scheduling question, not a goal.** "Is there anything
left you can do without me?" is what someone asks when they are about to stop working for the
evening. Reading it as a utility function is inferring a preference from a logistics question
asked three times in one sitting — which is a smaller sample than it looks, because it is one
context, not three.

### 1.2 Why the alternative reading loses, and why that does not rescue the sequence

I set out to argue this and could not sustain it. The strongest counter is not the revealed
preference at all — it is Layer 3's **[stated]** quote, which is a direct statement of goal and
not a scheduling remark:

> *"see if I could spin up enough LLMs to see if I could make as much as possible work with
> **little to no work on my part**."*

That is unambiguous, and it converges with Layer 1's independent finding. §4.1 stands.

**But `DECISION.md` optimises the wrong functional of it.** "Little to no work on my part" is
*minimise Chris-actions per unit of result*. `DECISION.md` maximises *agent-hours that can run
while he is away*. Those two come apart precisely where the sequence makes its biggest call:

- Under **minimise-Chris-actions**, step 3 (the USB channel) is **negative-valued at this
  point in the sequence**. It spends one of the project's scarcest events — a card install
  plus a boot — to buy an agent capability that produces no camera output, in a project whose
  §4.3 test is "does it end in a visible camera capability."
- Under **maximise-unattended-agent-hours**, step 3 is the centrepiece. `DECISION.md` calls it
  *"the only item in the entire folder that structurally converts human-gated work into queued
  work"* (§2, step 3).

The tell is in `DECISION.md`'s own §7(i): it defends four concurrent desk tracks by saying
agent sessions "are the one resource that is not scarce." If agent sessions are not scarce,
then **running four tracks concurrently rather than sequentially buys Chris nothing.** The only
thing concurrency changes is *when their outputs land* — and here is the actual cost:

| Track | Terminates in |
|---|---|
| Step 0 | Chris sends a message (account) |
| 1a | Chris runs S1 (hands) |
| 1b | Chris posts to the forum (account) |
| 1c → step 3 | Chris installs a card and boots (hands) |
| 1d | nothing — the only genuinely terminal desk track |
| Step 6 | 2–4 further body sessions (hands) |

**Five of six parallel tracks terminate in a Chris-gated action, and running them concurrently
makes those five arrive at the same time.** Concurrency on a non-scarce resource converts
directly into a queue on the scarce one. That is the mechanism of drift, and §7(i)'s defence —
"how many things compete for a scarce resource" — measures the wrong instant: it counts
contention *during* the tracks and ignores contention *at their outputs*.

**Finding 1.1.** The objective function is right; the sequence optimises a proxy for it that
diverges at exactly the decision that distinguishes this recommendation from a narrower one.
Under the correct functional, step 3 is deferred and step 1 is cut to the tracks that either
terminate at the desk (1d) or feed the one body session already scheduled (1a).

### 1.3 A second, smaller misreading

§4.5 lists **four** conclusions, and `DECISION.md` says it judges against §4.5 while scoring on
§4.1. Item 4 of §4.5 is *"body-session time is the scarcest resource — automation that protects
it outranks automation that merely accelerates desk work."* The sequence's step 1 contains no
protection for S1 at all: no pre-flight boot check, and §0.1 has just removed the mitigation
direction 3 was relying on (§5.1 below). Under §4.5 item 4, building the pre-flight check
outranks three of step 1's four tracks. That check exists and is cheap — see §10, amendment A3.

---

## 2. Axis 2 — does it respect the maintainer constraint?

This is where the recommendation is weakest, and it is weakest in the step it puts first.

### 2.1 The retraction as drafted is materially false

`DECISION.md` step 0 lists four sites for the retracted superlative: `.planning/ROADMAP.md`
line 68, `patches/README.md` §0007, `.planning/prs/PR-Q2-…md` line 26, and a correcting commit
for `5c009d7`.

`git grep` over tracked files (excluding `VibePlan/` and the Discord transcript, which is a
record of what was said and should keep it):

```
.planning/BODY_TEST_PLAN.md:17     **First-ever ML raw video on a 6D2**
.planning/ROADMAP.md:68            first ever on a 6D2                        [listed]
.planning/spikes/006-rawvideo-memory/README.md:19  **First-ever ML raw video on a 6D2.**
README.md:77                       the first DIGIC 7 MPU spell set
patches/README.md:183              First DIGIC 7 spell set in                 [listed]
.planning/prs/PR-Q2-…md:26         the first MPU init spell set for a D7 body [listed]
commit 5c009d7 (subject)                                                      [listed]
```

Three uncorrected sites, one of them **line 77 of the repository's public front-page
`README.md`**, which is the first file any maintainer who follows the fork link will read.
`ServerDestroyer/magic-lantern-6d2` is public — direction 4 verified this — so all three are
published.

The drafted retraction (direction 4 §4) says *"I've taken it out of my notes."* Sending it with
three copies still live makes the retraction itself a false statement, to the specific person
who wrote *"LLMs lie a lot"* and whose stated reason for doubting *"tested on a real body"* was
one prior inaccuracy. This is `DECISION.md`'s own abandon-criterion #3 — *"a second overclaim
ships after the retraction"* — firing on day one.

The bitterly instructive part: `DECISION.md` §4 designs the gate that catches this — *"a
mechanical superlative grep"* — and step 0 does not run it. **Finding 2.1: the gate was
specified and not applied to the step that needed it most.** Cost to fix: one `git grep`, three
edits. This is the single highest-value correction in this document.

### 2.2 The sequence adds to the queue and subtracts nothing from it

§4 establishes the trust economics precisely and correctly: one active maintainer, 21 open PRs,
Chris's five are 24% of that queue filed in 14 hours, zero external merges in 2026. The
conclusion `DECISION.md` draws is a *rate limit* — one outward artifact per 72 hours, under 200
words, bug reports outnumbering patches 2:1.

The conclusion it does not draw is the one the numbers actually support: **the cheapest gift to
a one-person team with a 21-item queue is to make the queue shorter.** Nothing in the seven
steps closes, withdraws, or converts a single PR. Step 0 *adds* comments to it.

This is not my invention; it is `DECISION.md` overruling its own source without saying so.
[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/VibePlan/direction-upstream-contribution.md](VibePlan/direction-upstream-contribution.md)
§2, "What to do with #298 concretely":

> **Close it**, or convert it to a bug report, and say why in one short comment. Do not push
> (a)+(b) as a replacement PR in the same breath — that is more patch volume aimed at a person
> who just asked for less.

`DECISION.md` step 0 renders this as *"put the #298 objection on the public PR thread so the
public record is honest."* That is a strictly worse move: it keeps the PR open, adds a comment,
and — read from the maintainer's side — publicly transcribes a criticism he chose to make in
Discord onto a permanent GitHub thread. Honesty about the record is a real value, and the way
to serve it is *"closing this — the right fix is at `PROP_LV_ACTION`, reasoning below,"* which
is honest, shortens the queue, and needs no quoting of his private remarks.

**Finding 2.2.** Step 0 substitutes a comment for a closure, on a recommendation whose own §4
proves closure is what the evidence supports. Same for #295, which `direction-upstream-contribution.md`
§2(a) says is **superseded** by a better fix *and* carries an unreviewed edge nobody has
checked (the early `return 0` skips `prop_reset_ack()` at `src/property.c:420`). Leaving an
open PR that this project's own analysis calls superseded-and-unverified is precisely the
"untested LLM patch as a net cost" pattern Layer 3 makes binding.

### 2.3 Step 0 breaks the sequence's own cadence rule on day one

§4 rule 1: *"One outward artifact per 72 hours."* Step 0 is a comment on #297, a comment on
#298, and a Discord retraction — three outward artifacts, same day. §2 step 5's own sequencing
constraint (72 hours between outward acts) is applied to the forum ask and not to step 0
itself. Either the rule means "one per 72 hours" or it does not; as written the sequence
violates it in the step that exists to repair trust.

Defensible answer: the retraction and the #297 answer belong in one message (direction 4 §4
argues this well, and I agree). But that is *two* artifacts at most — the message, and the #298
disposition — not three, and the #298 action should be a closure, which reads as subtraction
rather than as more traffic.

### 2.4 The one uncontested win in the queue is not in the sequence

`direction-upstream-contribution.md` §3, last paragraph: #297 bundles two unrelated changes,
and the maintainer **praised** one of them on Discord — *"the shadowed fps var is hard to
spot."* `raw_video_rec_task()` redeclares `int fps` inside the `card_index == 0` block, leaving
the outer `fps` pinned at 1 for the whole recording. That is body-agnostic, few-line, already
endorsed, and *currently held hostage by the contested header-stamp change in the same PR.*
Direction 4's instruction is one word: **split it out.**

Step 0 does not split it. I verified the maintainer's comment live today:

> This sounds like it hides the real problem (incorrect value returned by
> fps_get_current_x1000()) ? / Fixing the real problem would be greatly preferred. / ... Have
> you done any testing in this area?

He asked for the real fix. Step 0 replies with a derivation of why the current value is wrong
and leaves the PR containing the workaround open. Splitting out the shadowed-`fps` fix converts
that exchange from "I explained my workaround" into "here is the part you already agreed is a
bug, separated so you can merge it." **Finding 2.4: the highest-probability merge in the entire
queue is omitted from a step whose stated purpose is trust repair.**

### 2.5 Credit where due

Step 0's technical content is good, and I checked it. The `/2, /3, /6` derivation in
`direction-upstream-contribution.md` §3 reproduces from the maintainer's own `ffef459f0d`
numbers; the 6D2 ratios (1.501, 2.990) and 200D ratios (1.503, 2.997) are consistent to well
inside 0.6%; and the check that makes it convincing — reproducing the observed MLV header value
**178,993** bit-exactly through ML's staged integer truncation, where naive float division
gives 178,994 — is the kind of evidence that is hard to fake and hard to argue with. Flagging
the 200D `TG_FREQ_BASE 84000000` discrepancy as a question rather than a claim is correct. This
is the mode Layer 3 asks for, and it should be sent.

---

## 3. Axis 3 — does it honour the scope decision Chris already made?

### 3.1 The reversal is argued, not smuggled — this charge does not land

I looked for a quiet reversal and did not find one. §3 is a titled, explicit argument ("the
JTAG scope decision paused a producing track"), it concedes the decision was *right about the
target*, it states the condition under which the pause would have been correct (a donor body
already bought and bench time blocked out), and it states the narrower condition under which
JTAG becomes the right primary claim on Chris's hands. §5(d) tabulates what happens to every
direction if the answer is no. §7's objection section names the reversal as the substance of
the decision. That is the correct way to overturn an owner's call.

I also verified the decision exists and is attributed to Chris, which no file in `VibePlan/`
does. It is recorded in project memory (`6d2-project-state.md`, line 76) and quoted in
[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/010-jtag-digic7/README.md](.planning/spikes/010-jtag-digic7/README.md):
*"Chris scoped the project down to 'JTAG and what connects to it' on 2026-08-16."* The memory
entry ends: **"Do not re-open the other spikes without Chris saying so."** There is no
corresponding record in `ROADMAP.md` or `PLAN_OF_ACTION.md`.

### 3.2 Where it does land: the sequence re-opens four paused spikes before asking

That memory line is an instruction with a named precondition, and `DECISION.md` satisfies the
precondition nowhere. Steps 1a, 2, 4 and 6 re-open spikes 007, 008 and the feature queue —
exactly the items named as paused — and step 1d re-opens QEMU boot work, also named. The
argument in §3 is a good argument for asking Chris to lift the scope. It is not a substitute
for asking him.

And `DECISION.md` already knows the question that decides it: §6.1, *"Buy a donor body — yes,
no, or not yet?"*, of which it says **"nobody has asked."** §7(iii) then concedes the sequence's
*width* also depends on §6.5, of which it says **"I do not know his cadence; nobody has asked."**

**Finding 3.1.** A seven-step sequence is proposed whose scope rests on one unasked question
and whose width rests on a second unasked question, both of which the document identifies and
neither of which it puts in front of the one step that already requires Chris's attention.
Chris is being asked to send a GitHub message in step 0 regardless. The two questions cost one
extra sentence in the same handoff. Putting a 42 KB plan in front of him before that sentence
inverts the order.

This also collides with a recorded preference:
`/home/chris/.claude/projects/-home-chris-Vibe-Coding-6D-Mark-II-Magic-Lantern-6D2/memory/chris-plans-substance-before-menus.md`
— substance first, then a *pointed question in prose*, not a decision menu. `DECISION.md` §6 is
a ten-item question list, which is closer to the menu he twice rejected than to the one pointed
question the situation actually needs. The substance is now written. Two questions is the right
size of ask; ten is not.

---

## 4. Axis 4 — sequencing errors and false concurrency

### 4.1 S1 will not load ML as specified — the card is in stock-boot mode

`6d2-project-state.md` line 84:

> **CARD IS IN STOCK-BOOT MODE since 2026-08-16 (Chris's request — camera used ML-free for a
> day).** `BOOTDISK`+`EOS_DEVELOP` cleared from both exFAT VBRs; ALL ML files still on the
> card, untouched. Camera boots pure Canon firmware until re-enabled. Re-enable:
> `sudo python3 tools/sd_ml_toggle.py on /dev/sdX1` … **Do NOT diagnose "ML not loading" until
> flags are back on.**

`tools/sd_ml_toggle.py` exists. Step 2's "hard precondition" is the forced-module-rebuild
incantation and the `strings` check — both correct and both necessary — and says nothing about
boot flags. Nothing later in the folder supersedes the memory record.

If S1 runs without re-arming, ML does not load, and every one of the seven tests in Parts A and
B returns nothing. That is a whole session lost to an instrumentation defect the machine could
have checked — the exact failure INTENT §4.4 says has already happened **twice** and which
`DECISION.md` §2 step 2 cites approvingly ("§4.4's lesson applied"). It is also a `sudo` action
on Chris's PC with the card in a reader, i.e. a Chris-gated step that appears in no step list.

**Finding 4.1.** Highest-probability single point of failure in the sequence, cheapest to fix,
not mentioned. Verify the flag state before writing S1's instructions, and put the re-arm at
step 0 of S1's instruction artifact.

### 4.2 Step 3 is a second claim on Chris's hands, and the sequence says there is only one

§2 step 2: *"Must not overlap with: any other body session. **S1 is the only claim on Chris's
hands in this sequence.**"* §7(i) repeats it as the core of the anti-drift defence: *"one item
on his hands."*

Step 3 requires a card install and a boot (spike 012 phase 2: *"Chris: sync the whole
`build/zip/ML/` tree to the card, boot the camera once"*), then a USB session on the body for
phase 3. Step 6 budgets **2–4 further body sessions**. Adding the card re-arm from §4.1, the
true count of physical Chris-events in the sequence is **at least four**, not one.

The claim is not merely inaccurate; it is the load-bearing premise of §7(i)'s answer to the
drift objection. With the real count, §7(i) reduces to "everything except four things runs on
agent sessions," which is not an answer to "this keeps all five directions alive."

### 4.3 Step 3 inverts spike 011's own ranking and orphans the zero-risk fallback

[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/011-hardware-in-the-loop/README.md](.planning/spikes/011-hardware-in-the-loop/README.md)
ranks the no-solder paths and its verdict table puts **peek-to-SD at #1, "DO FIRST"**, USB at
#2. Its "Recommended first action" is explicit:

> build the on-camera peek-to-SD module (#1). It reads real hardware today, zero ROM
> archaeology, and **it de-risks path #2** by letting us sanity-check addresses before wiring
> up USB peek/poke.

In `DECISION.md`, peek-to-SD appears **only** as a passenger inside step 3 ("bundle it into the
SAME card image"), which is gated on 1c validating `0xE04BF152`. So:

- If 1c fails, step 3 dies — and abandon-criterion #4 says *"peek-to-SD becomes the read
  channel."* But peek-to-SD was never built, because its only appearance was inside the step
  that just died. The stated fallback does not exist at the moment it is needed.
- Peek-to-SD is ~tens of lines, needs no stub, no QEMU validation, and has zero brick risk
  ([spike 011 §1](.planning/spikes/011-hardware-in-the-loop/README.md): `save_mem_to_file` at
  `ml/src/fio-ml.c:816-825` plus the `core_dump_requested` trigger at `ml/src/debug.c:610-615`,
  all confirmed-present 6D2 stubs). It is a `.mo` file. **It can ride S1's Part B card sync at
  zero marginal Chris-cost.**

`DECISION.md` inherited the bundling from spike 012 phase 2, which was written when no other
card install was scheduled. Once S1 exists with two syncs, the bundle should follow S1, not
create a third install.

**Finding 4.3.** Fold peek-to-SD into S1's Part B sync. It converts a hypothetical fallback
into a real one, removes step 3's dependency on 1c for the *read* capability, and costs one
extra file on a card that is already being written. Honest cost: one more variable in Part B's
build, so it goes on as a module (independently loadable, independently disableable) and not as
a compile-time change.

### 4.4 1a and 1d contend for the one thing this project has already been burned by

`DECISION.md` asserts step 1's four tracks have "different failure modes, none competing for a
scarce resource." Two of them compete for `ml/platform/6D2.111/build/`.

- **1a** cuts the S1 card package and must verify it with `strings` on `build/zip/`.
- **1d** builds and boots ML/stock images in qemu-eos; spike 004's own reproduction block
  rebuilds the card image from `ml/platform/6D2.111/build/zip/*` on every run.

[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/patches/README.md](patches/README.md)
lines 306–321 records why this matters, and it is not theoretical:

> **Build-system trap (worse than previously recorded).** `make clean` … silently shipped the
> rev-1 `mlv_lite.mo`. Force a real module rebuild with: … and always verify with `strings` on
> `build/zip/…`, never on the source tree.

A concurrent build in the same tree invalidates 1a's `strings` check between verification and
card sync. The failure mode is "the card carries a stale module with a plausible size and a
fresh mtime" — which has already happened once in this project and is unfalsifiable from the
card. Fix is trivial and lazy: give 1d its own `git worktree` or its own `BUILD_DIR`, or
serialise 1a's package cut before 1d starts. Stating "these are concurrent" without stating
that is how the trap gets re-sprung.

### 4.5 Two smaller ones

- **Step 5 is marked ∥ and is not.** It is hard-serialised at ≥72 h after step 0 and gated on
  1b's premise check. Marking it concurrent overstates the parallelism.
- **§0.1 says treat KerRLock as open-ended and "do not schedule around it"; step 1d schedules
  it**, inside a "~4–6 agent sessions total" budget shared with three other tracks. Pick one.
  (My view: it belongs in 1d, but re-scoped — see §7.1.)

---

## 5. Axis 5 — cost realism

### 5.1 S1 is the same session direction 3 designed, but with its stated protection removed

Step 2's S1 is verbatim `direction-feature-roadmap.md`'s S1 — I diffed them; same seven tests,
same two-sync structure, same ~40 minutes. So the estimate is inherited, not invented, which is
fine.

What is not fine is that `direction-feature-roadmap.md` names three protections and then says
of the third:

> Protection 3 above is the honest weak point … The thing that would actually de-risk S1 is
> **ML booting under QEMU** — the `[CPU1] ASSERT SystemIF::KerRLock.c:205` gate, prime suspect
> the single global `current_task_addr = 0x28`.

§0.1 removes that suspect and re-costs the fix as open-ended RE behind four sequential gates.
**S1's stated de-risking path is therefore gone, and `DECISION.md` schedules S1 unchanged
without re-examining its risk.** The session got more dangerous and the plan did not react.

This matters concretely because Part B batches **five** `features.h` enables into one untested
body build, and this project has measured what a `features.h` batch can do. From
`ml/platform/6D2.111/features.h:44-50`:

> Spike 005 task 5 A/B (2026-08-15, measured in QEMU): with these three enabled,
> `GetMemoryInformation()` reports **0 total / 0 free** at `log_start()` and every
> `_AllocateMemory` fails … With them off … the pool is 9437184/5970756 and capture works.

Spike 005 §Blockers adds that the boot-time consequence of a failed allocation is *"a camera
that looks bricked."* If Part B's build reproduces that, all five items fail together and are
mutually unattributable — items 1, 2 and 3 of the queue lost in one boot.

The good news, and `DECISION.md` misses it: **that A/B was run in QEMU.** The allocator failure
is desk-detectable *today*, without ML reaching the GUI, without KerRLock, without any of the
four gates. The pre-flight check S1 needs already exists in executed form. It is one boot of
the batched build with `CONFIG_STARTUP_LOG`, checking `GetMemoryInformation()` at `log_start()`.
That is a five-minute use of the tooling step 1d is building anyway, and it is worth more than
the other three tracks of step 1 combined under §4.5 item 4.

**Finding 5.1.** Add the allocator pre-flight to step 1a as a gate on the Part B sync. It is
the only protection available now that §0.1 has removed the other one, and it is already proven.

### 5.2 The `dual_iso.cfg` task has no input

Step 2 Part A item 4, §6.10, and the synthesis's open-question list all rest on copying
`ML/SETTINGS/dual_iso.cfg` off the card, described as *"a file copy that answers outright which
index produced the measured +1.71 EV"* and *"the only thing that makes any dual-ISO EV claim
honest."*

`6d2-project-state.md` line 84, modified **2026-08-16 11:48** — 24 minutes before `DECISION.md`
was written:

> memory previously said the dual-ISO menu index is recoverable from `ML/SETTINGS/dual_iso.cfg`
> on the card — **it is not; no dual_iso.cfg was ever saved** (only a 0-byte `dual_iso.en`), so
> the index must come from Chris or a fresh body session.

Independently: `Backup SD card/ML/SETTINGS/` contains exactly `magic.cfg` and `MENUS.CFG`,
both dated 2025-09-29. No dual-ISO config in any form.

*Honest caveat:* the backup predates the dual-ISO sessions, so it is corroboration, not proof
about the live card; the live card is the authority and I cannot read it. But the memory
record is a direct check of the live card, it is dated, and nothing supersedes it.

**Consequence, and it is not cosmetic.** The honest-EV question does not collapse to a file
copy — it collapses to `direction-feature-roadmap.md`'s **session S3**: *"a stills index sweep
to map gain code → achieved EV (the number needed to make an honest claim)."* That is a body
session, not a `cp`. So the sequence is short one body session for a claim it says cannot
honestly be made without it, and §6.10 asks Chris a question whose premise is already refuted
in this project's own records.

This is the same failure mode as §0.1: **a claim that was refuted at layer N is still being
acted on at layer N+2 because the summaries were not re-read against the source.** Three
independent instances of it appear in this review (§0.1's suspect, this, and §2.1's superlative
count). See §6.2.

### 5.3 Where the cost numbers are honest — and where the citation is not

Lossless (step 6) is **conservative, not optimistic**, and I want that on the record because
the brief warned about the opposite:

| Source | Estimate |
|---|---|
| `VibePlan/README.md` line 38 | 8–14 sessions remaining |
| Spike 008 §Verdict (line 41) | 8–14 |
| Spike 008 Ghidra pass 2 (line 1237) | **Total 6–11**, down from 8–14 |
| Spike 008 Ghidra pass 3 (line 1740) | **Total 4–8**, down from 6–11 |
| `direction-feature-roadmap.md` line 255 | 6–10, of which 2–4 body — argues 4–8 "does not survive" |
| `DECISION.md` step 6 | 6–10, of which 2–4 body |

`DECISION.md` correctly follows the direction file's argued push-back over the spike's own
newest number, and states the likely terminal outcome ("stills lossless DNG works, movie
integration blocked by LiveView contention") up front. That is the right handling. **The stale
number is in `README.md` (8–14), which `DECISION.md` §10 does not list among its five
corrections.** Minor, but it is the folder's front page.

Step 1's "~4–6 agent sessions total" for four tracks is the one estimate I do not believe,
because 1b alone is a Wayback retrieval whose own §0.3 measurement documents 503-retry pain,
plus a photo interpretation, plus a ROM0 static search for an unpublished watchdog address that
spike 010's memory record calls *"the one unresolved Phase 0 blocker."* That is not a fraction
of a session. But this matters little, because agent sessions are the resource the sequence
itself calls non-scarce.

### 5.4 A stale "[measured]" claim, as a caution about the tagging discipline

§0.3 and §10 correction 3 state the mirror had *"zero files"* and was at CDX page 290/309 "as of
~14:00 today." At 12:19 by this machine's clock, `~/ml-mirror/cdx_list.tsv` is complete at
4.0 MB and `~/ml-mirror/site/` is populated. The direction of travel is what matters and the
conclusion ("nothing may be planned on the strength of the mirror this week") still stands —
but a `[measured]` tag with an unstated timezone and a fast-moving subject decays within hours.
If the claims ledger of §4 is going to carry weight, measured claims need a timestamp with a
zone and a re-check rule.

---

## 6. Axis 6 — the unexamined option

Two directions are absent from the folder, and one of them dominates a direction that is in it.

### 6.1 The method write-up — absent, and it is the stated deliverable

Layer 3's whole point is that **the 6D2 is the benchmark, not the deliverable** — the
deliverable is an agent-driven RE method. `DECISION.md` §6.4 asks *"is the method meant to
become a product, a public writeup, or stay private?"* and then treats the answer as gating
nothing except a credit question.

But there is no direction in the folder whose output *is* the method, and the method write-up
scores better on `DECISION.md`'s own table than three of the five directions it does score:

- **Unattended fraction: 100%.** Agents draft it; it is text over artifacts that already exist.
- **Money: $0. Brick risk: none. Body sessions: zero. Maintainer goodwill spent: zero** — it
  goes in Chris's own repo, which §6.3's "only as evidence" branch already identifies as the
  right destination.
- **§4.3 (visible camera capability): satisfied by reference** — dual-ISO stills at +1.71 EV,
  14-bit raw video, the MOV limit override, the first DIGIC 7 MPU spell set, and QEMU startup
  are *already* real. The write-up does not need to produce a capability; it needs to *account
  for* the ones already produced.
- **It is the only artifact that survives every one of the nine abandon criteria in §8** —
  including criterion 2 ("the maintainer asks for a pause"), under which directions 4 and 5 die
  and this one is unaffected.

There is one more argument for it, and it is the strongest: this project's distinctive asset is
not the 6D2 port. It is the **adversarial verification practice** (C5 in `PLANS-IN-FLIGHT.md`),
which has now refuted a proposed code fix, a ROM table identification, three sub-claims inside
spike 004's own headline, `DECISION.md`'s §0.1 target, and — in this document — four more.
*That* is the transferable result, it is fully documented in-repo, and nobody is writing it up.

I am not recommending it as step 1. I am recording that a direction with a 100% unattended
fraction, zero cost on every scarce resource, and a direct line to the stated deliverable was
never placed on the table, while five directions that each consume a scarce resource were.

### 6.2 Consolidation — the option the evidence in this review argues for

Three of my four heaviest findings are not technical errors. They are **summarisation drift**:

1. `current_task_addr` was a parenthetical "suspicious" aside in spike 004 §8; it became "prime
   suspect" in `INTENT.md` step 4, `PLANS-IN-FLIGHT.md` D5 and `direction-automation-harness.md`;
   `DECISION.md` §0 then spent its lead finding refuting the paraphrase.
2. `dual_iso.cfg`'s non-existence was recorded in memory at 11:48 and re-asserted as an S1 task
   and a question for Chris at 12:12.
3. The superlative count was recorded as four sites when a one-line grep finds seven.

The project now carries `PLAN_OF_ACTION.md`, `.planning/ROADMAP.md`, `.planning/BODY_TEST_PLAN.md`,
14 spike folders, `FEATURE_MATRIX.md`, `VibePlan/DIRECTION.md`, `VibePlan/README.md`,
`VibePlan/PLANS-IN-FLIGHT.md`, four layers of `INTENT.md`, five direction files, and now
`DECISION.md`. Each derived document is a place a refuted claim can survive.
`DECISION.md` adds the twelfth planning document and, in §10, records five corrections *"here
rather than edited into the source files, which are owned elsewhere"* — i.e. it deliberately
leaves the refuted claims live in the files people will read next.

This is the strongest available form of §7's own objection, and §7 does not reach it. The
objection is not "five directions are alive." It is **"the folder's failure mode is not
choosing wrong, it is acting on stale summaries, and adding another summary layer makes that
worse."** The corresponding option — collapse to one ledger, fix the refuted claims in place,
delete the rest — is not in the folder and would take one agent session.

### 6.3 One free artifact nobody has scheduled

`6d2-project-state.md` line 84 records, as a JTAG-scope-paused item:

> upstream `ml/tools/card-flags/edit_card_flags.py` line 133 has a precedence bug in its exFAT
> VBR checksum (`|` instead of the spec's add-with-carry rotate) — wrong checksum whenever a
> carry reaches bit 31; candidate upstream bug report.

I verified it. Line 133 reads:

```python
checksum = uint32((checksum << 31) | (checksum >> 1) + value)
```

Python binds `+` tighter than `|`, so this evaluates as `(checksum << 31) | ((checksum >> 1) +
value)`. The exFAT VBR checksum is a rotate-right-by-one **followed by an add that carries into
bit 31**. Here `(checksum >> 1) + value` can carry into bit 31 (max `0x7FFFFFFF + 0xFF`), and
the `|` merges that with the rotated-in bit instead of adding it — so the result diverges from
the spec exactly when the old LSB is 1 and the addition carries. Rare, real, and silent: a
wrong VBR checksum on a card the user then cannot boot.

Score it against Layer 3: body-agnostic, desk-verifiable, needs no hardware and no ROM, is a
**bug report with reasoning rather than a speculative patch** (the exact mode requested), and
this project already has an independent reference implementation in `tools/sd_ml_toggle.py` to
demonstrate the divergence with. It costs one short comment and consumes no scarce resource
except one slot in the 72-hour cadence.

It is in no direction file and in no step of the recommended sequence. On the maintainer axis
it is worth more than step 3 and costs a thousandth as much.

---

## 7. Findings the axes did not ask for

### 7.1 §0.1's mechanism is right and its prescription is wrong

I re-ran the grep. `DECISION.md`'s counts are accurate: the field is read only by
`eos_get_current_task_name/id/stack()` (`hw/eos/eos.c:2197-2290`, all via
`cpu_physical_memory_read`), by `dbi/logging.c`'s task-switch detector, and by `util/log.c`'s
help string; and `current_task_addr = 0x28` appears exactly **9 times** in `model_list.c` (plus
three at `0x20`). No guest instruction reads it. **The assert cannot be caused by it. §0.1's
mechanism holds.**

§10 correction 1 then says to strike it from `INTENT.md`, `PLANS-IN-FLIGHT.md` and
`direction-automation-harness.md`. That deletes a live defect. From `DECISION.md`'s own cited
evidence file,
[.planning/spikes/004-ml-boot-in-qemu/evidence/2026-08-15-night2-nochain-shtcap-assert.txt](.planning/spikes/004-ml-boot-in-qemu/evidence/):

```
line 17:  [CPU1] [     Startup:e0040efd ] (89:06) ASSERT : SystemIF::KerRLock.c, Task = ShtCap
line 38:  [CPU0] [ShootCapture:e0040efd ] (89:06) ASSERT : ./Shoot/ShtPath/…, Task = ShootCapture
```

The bracketed name is QEMU's annotation, produced from `current_task_addr`. The `Task = …`
text is Canon's own ASSERT payload. **On CPU0 they agree (`ShootCapture` / `ShootCapture`). On
CPU1, at the same timestamp, they disagree (`Startup` / `ShtCap`).** That is the exact
signature of one global current-task pointer on a two-core machine: core 0's annotation is
right, core 1's is another core's task.

*Honest caveat:* Canon's payload might name the task the assert is *about* (e.g. a lock owner)
rather than the running task, so this is a strong observable, not proof. Settling it costs one
boot with `-d tasks` — which is already listed as a desk task in
[spike 013 Track A](.planning/spikes/013-emulator-groundtruth-loop/README.md) line 19,
*"`current_task_addr=0x28` (verify via `-d tasks`)"*.

**Why it changes an action.** Step 1d builds a harness whose entire product is
*"build→boot→capture→parse"* over `-d io calls tasks debugmsg` output, with a baseline diff.
If CPU1's task annotations are wrong, every trace line that harness reads about the second core
is mislabelled — and the second core is where the blocking assert lives. Building a diagnostic
loop on top of a known-suspect annotation is the same category of error as the two body
sessions lost to instrumentation defects.

So the correct disposition is the opposite of striking it: **keep `current_task_addr` on the
list, re-scoped from "cause of the KerRLock assert" (refuted) to "trace-fidelity defect on
CPU1" (evidenced, one boot to confirm), and fix it before step 1d's parser is trusted.** The
`fixme: read from virtual memory` comment on the same line is the hint about how.

Second-order point: `DECISION.md` presents §0.1 as one of "three findings that changed the
ordering." It changes the *cost* of direction 1's ML-boots-to-menu half, correctly. It changes
no step: 1d's action ("wrap `run_qemu.py`… re-open KerRLock") is what spike 004 §8 lever 1
already prescribed — *"disassemble around `0xE0040EFC` and find the KerRLock entry that fails"* —
and that is untouched by the refutation.

### 7.2 §1's table claims an unblock that §0.1 has just made impossible

§1, direction 1, "What it unblocks": *"**Desk A/B of every feature enable**; the spike-005 pool
interaction; item 5's plumbing; spike 013 Track B; the 5 genuinely hardware-bound questions."*

Two of the five features in step 1a's batch are `FEATURE_LV_FOCUS_BOX_AUTOHIDE` and
`FEATURE_CROPMARKS` — both LiveView/GUI-visible. Spike 004 §7 measured that ML *cannot* reach
GUI in QEMU, that `_rgb_vram_info` stays 0 in **every** run (chained and nochain, stock and ML),
and that this is gated behind the sequencer stages §0.1 itself just re-costed as open-ended.
So "desk A/B of every feature enable" is false for exactly the enables S1 exists to test.

The true and still-valuable claim is narrower: **the harness can A/B boot-time and
allocation-level effects today** — which is precisely the spike-005 measurement quoted in
`features.h`, and precisely the pre-flight check §5.1 recommends. Stating the narrow version
makes step 1d's value concrete and immediate; stating the wide version oversells direction 1
in the same document that re-costs it.

### 7.3 The retraction's second sentence promises a gate that does not exist yet

The drafted retraction ends: *"from now on I'll attach the evidence with each change and drop
the superlatives entirely."* The claims ledger, the commitment disclosure line, and the
superlative grep are proposed in §4 and are the subject of open question §6.9 — i.e. Chris has
not agreed to them, and none is built. Sending a public commitment to a process that does not
exist is a small version of the same defect as the retraction's factual error. Build the grep
first (it is one command), then send.

---

## 8. What survives contact — stated so the amendment does not throw it away

- **Debt before outreach.** The 72-hour ordering between step 0 and step 5, and the rule that
  the debt goes first, are right and well argued.
- **The `/2 /3 /6` derivation** (§2.5). Sound, checkable, and the correct register.
- **JTAG Phase 1 not scheduled, and §6.1 identified as the one question that gates one whole
  direction.** Correct, and §5(d)'s per-direction table is the best analysis in the folder.
- **The explicit cancellations** — Q1 (subset of qemu-eos PR #18), the `io_trace.c` port (spike
  011's MPU-vs-MMU finding, which contradicts the older memory note and is better evidenced),
  the `IMGPLAY_ZOOM_LEVEL_ADDR` hunt, GraphRAG, the Discord application. All defensible.
- **Step 4's kill criteria** (`buf_addr` outside the six `0x304` records, `reg 0x10` of
  `10717620`/`10717e20`, block 2) are specific, pre-committed and falsifiable. This is the best
  paragraph in the document.
- **§8's nine abandon criteria**, written in advance. Rare and worth keeping.
- **§7 concedes the objection that actually lands** (width contingent on an unasked cadence
  question) rather than reframing it away.

---

## 9. Verdict

**Does not survive as written.** The skeleton survives; the execution details of steps 0, 2 and
3 do not, and the headline finding's prescription is backwards.

Ranked by cost of executing the recommendation unamended:

1. **Step 0 sends a false retraction** (three uncorrected published sites, one on the public
   front page) to the person whose stated objection is that LLM output cannot be trusted. This
   is worse than doing nothing today.
2. **Step 2 loses a body session** — the project's scarcest resource, already lost twice — to
   an un-re-armed card, and contains a task with no input file.
3. **Step 3 spends a physical Chris-event** on infrastructure, before the free zero-risk
   fallback that spike 011 ranks #1 has been built, and while the sequence claims there is only
   one physical event in it.
4. **§10 correction 1 would delete an evidenced trace-fidelity defect** from three files, on the
   strength of a refutation that does not reach it.

None of these is a reason to reject the shape. All four are reasons not to execute the steps as
drafted.

---

## 10. The amendment

Replaces §2's seven steps and §9's "start here." Same skeleton, four fewer moving parts, two
additions that cost nothing.

### A0 — Before anything leaves the machine (one agent session, no permission needed)

- **A0.1** Run the superlative grep. Fix all seven sites, including `README.md:77`,
  `.planning/BODY_TEST_PLAN.md:17` and `.planning/spikes/006-rawvideo-memory/README.md:19`.
  Write the grep down as a committed script so the §4 gate is mechanical rather than
  remembered. *Then* the retraction is true.
- **A0.2** Fix the three refuted claims **in place** in the source files rather than recording
  them in a twelfth document: `current_task_addr` re-scoped per §7.1 (not struck), the
  `dual_iso.cfg` premise removed, `README.md`'s stale 8–14 lossless figure corrected. Whoever
  owns those files should make the edit; the correction should not live only here.
- **A0.3** Verify the card's boot-flag state before writing a single line of S1's instructions.

### A1 — The maintainer message: subtract, then answer (Chris: ~10 minutes, one send)

One message on #297: the honest *"no cross-model testing was possible — one body, one ROM,"*
the `/2 /3 /6` derivation, the 200D `TG_FREQ_BASE` discrepancy as a question. Under 200 words.
Plus, in the same handoff:

- **Close #298**, with one short comment saying the right fix is at `PROP_LV_ACTION` and
  linking the `powersave.c` reasoning. Direction 4 §2's actual recommendation.
- **Split the shadowed-`fps` fix out of #297** into its own small PR — the one change the
  maintainer has already praised, currently held hostage by the contested one.
- **Post the retraction** in the same message as the #297 answer, retraction first, now that
  A0.1 has made it true. Drop the "from now on I'll…" sentence until the gate exists (§7.3).
- **Two questions to Chris, in prose, in the same handoff** — donor body yes/no/not-yet, and
  body-session cadence. Not a ten-item menu (§3.2). Everything below is contingent on the
  second answer.

`edit_card_flags.py` (§6.3) goes in the *next* cadence slot, not this one — it is a gift, not a
debt, and the debt goes first.

### A2 — Desk work: two tracks, not four (unattended, $0)

- **A2.1 (was 1a + the new pre-flight)** Build the S1 package: `adtglog2.mo` for `6D2.111`, the
  `fps_get_current_x1000()` probe on the daily build, the batched `features.h` build as a
  separate second sync — **and boot the batched build in QEMU checking
  `GetMemoryInformation()` at `log_start()` before it is allowed onto the card** (§5.1). Add
  the peek-to-SD module to the Part B sync (§4.3). Own build tree or own `BUILD_DIR` (§4.4).
- **A2.2 (was 1d, re-scoped)** The thin `build→boot→capture→parse` harness, whose **first
  customer is A2.1's pre-flight** — that is what makes it earn its place this week rather than
  next month. Confirm or refute the CPU1 task-annotation defect with one `-d tasks` boot
  (§7.1). Treat KerRLock itself as spike 004 §8 lever 1 already framed it (disassemble
  `0xE0040EFC` callers), unscheduled and unbudgeted.

**Cut from step 1:** 1c (validate `0xE04BF152`) and 1b (the JTAG/community Phase 0). Neither is
wrong; both are premature. 1c gates step 3, which A3 defers. 1b gates step 5, which is gated on
a donor-body answer that A1 is now asking for. Both become the obvious next tranche the moment
Chris answers — which is the point of asking.

### A3 — Body session S1, and nothing else on his hands

S1 exactly as `direction-feature-roadmap.md` specifies it, with four changes:

1. Re-arm the card's boot flags first, in the instruction artifact, as step 0 of the session.
2. Drop Part A item 4 (`dual_iso.cfg`) — the file does not exist. Replace the honest-EV goal
   with an explicit note that it needs the S3 index sweep, so the gap is visible instead of
   silently unclosed.
3. Part B carries peek-to-SD as a module.
4. Part B ships only if A2.1's QEMU allocator pre-flight passes. If it fails, Part A still runs
   on the known-good build and the session is not wasted.

**Defer step 3 (the USB channel) until after S1 returns.** It is not cancelled — the argument
in §2 step 3 that it is the most legible demonstration of the method is a good one, and
`0xE04BF152` is worth validating. It is deferred because it costs a physical Chris-event, the
sequence has miscounted those, and peek-to-SD now delivers the *read* capability on a card sync
that is already happening. Reinstate it the moment Chris answers §6.7 affirmatively **and** the
body cadence turns out to be better than monthly.

### A4 — Everything else waits on two answers

Step 4 (movie dual-ISO) on S1's evidence, with its kill criteria unchanged — that part is
already right. Step 5 (forum) and 1b after the donor-body answer. Step 6 (lossless) as
background desk work only, with no body sessions committed until the cadence answer exists.

**Net change:** four concurrent tracks become two; three Chris-gated physical events become one;
step 0 grows a grep and loses a comment; two zero-cost artifacts (the superlative fix, the
`edit_card_flags.py` report) enter the plan; nothing of the skeleton is lost.

---

## 11. What would make me withdraw this critique

Symmetry with §8 of the target, and the same rule: written now so it cannot be rationalised
later.

1. **The live card's boot flags are already re-armed.** §4.1 evaporates and S1 stands as
   written. I could not check the physical card; I inferred from a dated memory record.
2. **A `ML/SETTINGS/dual_iso.cfg` exists on the live card.** §5.2 evaporates, the "trivial file
   copy" framing is correct, and `DECISION.md` is right that it settles the EV claim.
3. **Chris says the body cadence is weekly or better.** Then the width objection in §1.2 and
   §4.2 weakens sharply: three physical events across several weeks is not contention, and
   step 3's early position becomes defensible on its own terms.
4. **Chris says JTAG specifically is what he wants, USB is not interesting.** §6.3's cheap
   maintainer artifact and A2's re-scoping stand, but the deferral of step 3 stops being an
   improvement and the sequence should go back toward `DECISION.md`'s ordering.
5. **The `-d tasks` boot shows CPU1's annotation is correct** (Canon's `Task = ShtCap` payload
   names a lock owner rather than the running task). Then §7.1's prescription collapses to
   `DECISION.md`'s: strike the field and move on. One boot settles it, and I would rather be
   wrong cheaply than right slowly.
6. **The maintainer replies to #297 before the retraction ships.** Then the sequencing question
   is moot and the reply, not the plan, sets the next move.

---

## 12. Files and lines this critique rests on

- [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/004-ml-boot-in-qemu/README.md](.planning/spikes/004-ml-boot-in-qemu/README.md)
  §6–§8 and the adversarial-verification section; evidence file
  `evidence/2026-08-15-night2-nochain-shtcap-assert.txt` lines 17 and 38.
- [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/011-hardware-in-the-loop/README.md](.planning/spikes/011-hardware-in-the-loop/README.md)
  verdict table and "Recommended first action".
- [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/012-usb-debugger-bringup/README.md](.planning/spikes/012-usb-debugger-bringup/README.md)
  phase 2.
- [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/013-emulator-groundtruth-loop/README.md](.planning/spikes/013-emulator-groundtruth-loop/README.md)
  Track A line 19.
- [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/008-lossless-compression-scoping/README.md](.planning/spikes/008-lossless-compression-scoping/README.md)
  lines 41, 1237, 1739–1740.
- [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/patches/README.md](patches/README.md)
  lines 183, 306–321.
- `ml/platform/6D2.111/features.h` lines 25 and 44–53; `ml/tools/card-flags/edit_card_flags.py`
  line 133; `Backup SD card/ML/SETTINGS/` (directory listing).
- `/home/chris/ml6d2/qemu-eos`: `hw/eos/eos.c:2197-2290`, `hw/eos/model_list.c` (9× `0x28`,
  3× `0x20`), `hw/eos/dbi/logging.c`, `util/log.c`.
- `/home/chris/.claude/projects/-home-chris-Vibe-Coding-6D-Mark-II-Magic-Lantern-6D2/memory/6d2-project-state.md`
  lines 76 and 84; `.../memory/chris-plans-substance-before-menus.md`. (Plain paths — outside
  the workspace.)
- Live: `gh pr view 297 --repo reticulatedpines/magiclantern_simplified --comments`, 2026-08-16.
