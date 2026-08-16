# Direction 5 — Community, collaboration and the knowledge corpus

**Status:** recorded (not decided, not planned)
**Recorded:** 2026-08-16
**Judged against:** [INTENT.md](INTENT.md), with particular weight on **Layer 4 §4.2** — this
direction is *almost entirely outward-facing communication*, which is exactly the layer
Chris said he cannot audit.

**Relationship to the peer file:** [direction-community-and-corpus.md](direction-community-and-corpus.md)
records the same direction at summary depth. This file is the full build-out across the four
strands, and it **corrects one load-bearing claim that file inherits from the README** (see
§A.0). Where the two disagree, the evidence citations here are the ones to check.

---

## One-sentence goal

Convert the people, archives and public records around Magic Lantern into project inputs —
a DIGIC 7 JTAG pinout obtained by collaboration rather than by destroying a body, a searchable
corpus that stops the agent re-deriving answers the community already has, and a division of
labour with volunteers that the maintainers will actually accept.

## The four strands, and their honest shape

| Strand | What it is | Status | Unattended? | Verdict up front |
|---|---|---|---|---|
| **A — Collaboration** | Ask kitor / names_are_hard / coon for the DIGIC 7 JTAG method | Nobody's task | Draft yes, send no | **Do it, after a fact-check.** Highest value per unit of effort in the folder |
| **B — Forum mirror** | Wayback mirror of magiclantern.fm | **RUNNING**, 0 pages downloaded so far | **100%** | **Keep. Build nothing on top of it yet** |
| **C — Discord logger** | Read-only logging bot + index | Built, never invited | No | **Abandon.** Not "defer" — abandon, with a stated reversal condition |
| **D — Volunteers** | Non-coders check LLM output | Idea only | Draft yes, execute no | **One version survives, and it is not the one proposed** |

Three of the four are *communication*. That is the defining property of this direction and the
source of both its leverage and its risk (§E).

---

## Strand A — Collaboration with kitor, names_are_hard and coon

### A.0 The claim this strand is built on is unverified, and it is wrong-shaped

**"kitor asked for donor boards" is not supported by any primary source in this repository.**

It appears as established fact in four places — [README.md](README.md) line 44
("he asked for donor boards"), [PLANS-IN-FLIGHT.md](PLANS-IN-FLIGHT.md) line 33
("**kitor asked for donor boards.**"), `.planning/spikes/011-hardware-in-the-loop/README.md`
line 25, and the peer direction file — and every one of them is downstream of the same
digest. The actual primary-source statements are:

- `docs/jtag-research.html:485` — *"coon independently confirmed the RP pads **on a donor
  board**"*. That is coon reporting that he used one. It is not a request.
- `docs/jtag-research.html:720` — *"a few hours of scope work on a donor body would answer
  it."* That is **our own** research document's conclusion, not kitor's.
- The `jtag-on-digic` memory records kitor's method, tooling, IDCODE and pinouts in detail and
  **does not contain a donor-board request.**

The raw HTML of forum topic 27350 was not kept — `docs/jtag-research.html:702` records that it
was retrieved on 2026-08-16 and the findings folded in, and a filesystem search finds no
retained copy. So the claim cannot currently be checked against anything on disk.

**Why this matters more than a footnote:** the proposed opening move is a message to kitor. If
that message is premised on *"you asked for donor boards"* and he never did, it is a
confidently-stated false claim delivered to the one person who has already publicly accused
Chris of acting in bad faith. That is the "first-ever raw video" failure again, aimed at a
worse target. **INTENT §4.2 says Chris cannot audit this class of error.** So it has to be
caught here.

**Gate on strand A:** re-retrieve topic 27350 from Wayback, grep it for `donor`, and either
(a) find the request and quote it, or (b) drop the premise and rewrite the message. This is
~2 minutes of unattended work and it blocks the whole strand. It is the single first action
this direction should take.

### A.1 What is actually confirmed about kitor's work

All from `docs/jtag-research.html:485-486` and the `jtag-on-digic` memory, both traced to
topic 27350 (last captured post: coon, 2025-09-02):

- **Full dual-core GDB session on a PowerShot SX740 HS** (DIGIC 8): IDCODE `0x4ba00477`
  (generic ARM CoreSight JTAG-DP, mfg 0x23b — *not* a Canon-unique code), 6 breakpoints,
  4 watchpoints, GDB server on :3333 via `gdb-multiarch`, registers dumped from a running
  camera (pc=`0xe006e600`, sp_irq=`0xdf000100`, which independently corroborates qemu-eos's
  DIGIC 8 ROM map).
- **OpenOCD dual-Cortex-A9 SMP config published verbatim** in-thread (`jtag newtap …
  -expected-id 0x4ba00477`, two `cortex_a` targets coreid 0/1, `target smp`; `-dbgbase` left
  as an open TODO).
- **Pin-ID method: resistance-to-ground signature.** TDI/TCK/TMS/TDO ≈ 100–200 kΩ (~128 kΩ on
  the R, ~160 kΩ on the SX740); /TRST ≈ 10 kΩ pulldown. With the camera running, /TRST and TDO
  read low, TDI/TCK/TMS read high.
- **Tooling:** Altera USB Blaster, 1.8 V-compatible (DIGIC 6–8 logic is 1.8 V), OpenOCD,
  gdb-multiarch, microscope for tracing desoldered boards.
- **Pinouts located** for SX740, EOS R and EOS RP, with PCB photos at `kitor.pl/eos/jtag/`.
  coon confirmed the RP pads on a donor board.

**What is NOT confirmed and must never be implied:** that JTAG has ever talked on an *EOS*
body. kitor's full GDB success was on a PowerShot compact. The EOS R/RP pinouts are *located*,
not *demonstrated*. As of the last captured post nobody had finished solder-and-talk on an EOS.

### A.2 The thing we can offer that is real, unattended, and flatters nobody

This is the part that makes the message worth sending rather than just worth asking.

`.planning/spikes/010-jtag-digic7/README.md` §2 establishes a mechanism kitor's PowerShot work
cannot have encountered: **PowerShots have no MPU. EOS bodies do, and it runs a firmware
watchdog that faults the camera with ERR80 within seconds of the ICU halting** (g3gg0, ML
forum: *"That's different from EOS — there, it locks up and the MPU throws ERR80 shortly
afterwards… There's no MPU on PowerShots"*). DIGIC 5 had a suppressible ICU-side watchdog at
`0xC0410000` (write zero, via CHDK). **No DIGIC 7 or DIGIC 8 address is published.**

So the honest position is: *kitor solved the hard part on a chip with no watchdog; the EOS
version of his method has an unsolved second problem, and that problem is a static ROM search,
which is desk work we can do at 3 a.m. with no hardware.*

That is a real contribution to *his* problem, it costs one agent-session, it is queueable
while Chris is asleep (§4.1), and it does not require anyone's permission. It also converts
the message from "please give me something" into "here is the piece you don't have."

Second warm thread already open, from the Discord log: names_are_hard on the MPU spells —
*"The spells stuff is interesting - Alex repeatedly refused to explain some of the problems I
saw with 200D emulation, even after I'd dumped MPU logs. I ended up improving the emulation in
many places, but never knew how to import recorded MPU traffic. Might be able to use the
existing scripts now I know where they are."* That is an unanswered offer of help he asked for.
It belongs to strand A as much as to direction 4, it is the only interaction in the whole
thread where he was unambiguously pleased, and nobody has followed up on it.

### A.3 The social starting position (read this before drafting anything)

From `docs/discord/2026-08-16-ml-discord-thread.md`, unedited:

- kitor's first and only words to Chris: *"That's a lot of words just to say you want to fed
  all of our data to LLMs. Three days after joining, zero messages and straight to asking us to
  allow your bot scrape the server."* Then: *"I'll let @names_are_hard to decide but this is a
  pretty unusual introduction to this community."* He has not spoken to Chris since.
- names_are_hard rejected *"First-ever raw video recorded on a 6D2"* outright and added the
  damage assessment: *"because I know that's not true, I have to question whether 'All of this
  is tested on a real body' is true. LLMs lie a lot."*
- He also flagged the format: *"the bold headings LLM speak is kind of annoying and I would
  prefer talking like a human."*

That is the ledger the next message is written against. Four outward-facing artifacts in two
days (bot request, emoji status post, "first-ever" claim, PR #298 description) — three landed
badly. The base rate is bad and the sample is not small enough to ignore.

### A.4 The draft message — forum thread first, not Discord

**Venue:** ML forum topic 27350, kitor's own thread, Reverse Engineering board. Reasons: it is
where the work lives; it is technical rather than social; it reaches coon (who has the donor
boards and the RP pads) as well as kitor; it is publicly archived so the claim record is
durable; and it does not reopen the Discord conversation that went badly. magiclantern.fm is
Cloudflare-JS-challenged to non-browser clients — Chris posts from a browser, no agent can.

**Draft (assumes A.0 resolved as "no donor-board request found", i.e. the safe version):**

```
6D2 (DIGIC 7) owner here. I've been reading this thread rather than guessing —
thank you for publishing the OpenOCD config and the resistance-signature method,
that is far more than was public before.

I have two questions and one thing I can offer.

Questions:

1. Has anyone probed a DIGIC 7 board? I can't find a pinout for any DIGIC 7 body.
   The 6D2 is the same dual Cortex-A9 at 1.8 V, and qemu-eos models D7 and D8
   identically, so I'd expect your pin-ID procedure to transfer, but I don't want
   to assume that in public without asking someone who has actually done it.

2. On the EOS side specifically — did the ERR80 problem come up? On EOS bodies the
   MPU runs its own watchdog and faults the camera when the ICU stops answering.
   PowerShots have no MPU, so your SX740 session wouldn't have hit it. DIGIC 5 had
   a suppressible watchdog at 0xC0410000; I can't find a published DIGIC 7 or
   DIGIC 8 equivalent.

What I can offer: I have 6D2 ROM dumps and a working static-analysis setup, and
finding that watchdog/ERR80 path in ROM is desk work I can just do. If it would be
useful for the EOS R/RP work as well, I'll take it on and post whatever I find here
either way, including if I find nothing.

I have not soldered anything and I don't have a donor body, so nothing I say here
is from measurement yet. I'd rather ask first than publish a guessed pinout.
```

### A.5 What the message must NOT say — a checklist, not a sentiment

| Do not | Why |
|---|---|
| Claim a 6D2 pinout, a JTAG session, or any "first" | `docs/jtag-research.html:486`: DIGIC 7 has no published pinout and *"any pin assignment you see claimed for a 6D2 is fabricated"*. The last "first" claim cost the project its credibility with this exact audience |
| Say "you asked for donor boards" | Unverified — §A.0. Kills the message if wrong |
| Offer a donor board, hardware, money or Chris's time | He has not agreed to buy one. This is exactly why `DRAFT-comment-on-upstream-PR-223.md` was classifier-blocked: *"an assistant should not promise someone else's time on a public thread"*. That block was correct and generalizes |
| Use bold headings, emoji, bulleted feature lists, or the word "comprehensive" | Named by the maintainer as the tell |
| Ask kitor to do work (re-measure, write up, teach) in the first message | The first contact already read as extraction. Ask questions he can answer from memory in two sentences, or offer instead |
| Lead with the LLM workflow — or conceal it | Chris already disclosed it publicly (*"It is llm slop!"*). Hiding it on the forum after disclosing it on Discord is worse than either. Mention it plainly if asked |
| Attach a status update of 6D2 progress | Different message, different thread, and the last one was rejected |
| Send it from an agent, or from any account that is not Chris's | Standing constraint; automating Chris's Discord account is a ToS-ban self-bot |

**Follow-up discipline:** one message, then wait. No bump, no DM chaser, no cross-posting the
same text to Discord. If there is no reply in three weeks, the answer is no (§F kill criteria).

### A.6 What strand A is worth if it works

Direction 2's Phase 1 needs a donor body plus ~$200 of tooling
(`.planning/spikes/010-jtag-digic7/README.md` §3), and the bench procedure is 7 ordered steps
with a real chance of terminating at "nothing found across all pads in both nTRST states."
A reply containing a DIGIC 7 pin location, or a "the method transfers, here is what to watch
for", or an existing donor board in someone else's hands, removes most of that. A reply
containing *"nobody has probed a D7, and here is why the EOS watchdog will stop you"* is also
worth having — it is a cheap negative result on a direction that otherwise costs a camera.

**Expected value is high and the cost is one message. The failure mode is silence, which costs
nothing but the three weeks.** Both spike-011 red-teams endorsed this move and it has been
nobody's task since.

---

## Strand B — The ML forum mirror

### B.1 Measured state, 2026-08-16 11:51

Not the summarized state — what the machine is actually doing:

- Process alive: PID 2185613, `python3 /home/chris/ml-mirror/wayback_mirror.py`, started 10:22.
- **Still in `build_list()`** — CDX enumeration at **page 260 of 309**, 37,325 unique URLs so far.
- **`~/ml-mirror/site/` is empty. Zero pages downloaded.** The directory exists and contains
  nothing; total footprint of `~/ml-mirror/` is 12 KB (the script and the log).
- The log opens with a traceback: the first invocation died at
  `int(fetch(CDX + "&showNumPages=true").strip())` → `ValueError: invalid literal for int()
  with base 10: b'- -'`. It was fixed and restarted. There is already one silent-failure
  precedent in this pipeline.
- Wayback is returning frequent 504s — 12 retry lines in the last 30 log lines. The script
  retries 5× with escalating backoff and continues past a failed page (`cdx page N FAILED,
  continuing`), so **a partial URL list is a possible silent outcome**, and nothing checks for it.

**Extrapolation (stated as estimate, not measurement):** ~89 minutes for 260 CDX pages → the
remaining 49 pages finish in ~17 minutes. The unique-URL count is climbing steeply in the tail
(18,609 at page 200 → 37,325 at page 260), so the final list is plausibly 45,000–55,000 URLs.
The download loop sleeps 0.4 s per URL plus fetch latency plus 504 retries — realistically
**15–25 hours of wall clock**, and the disk cost is unmeasured (SMF topic pages plus retained
`action=dlattach` attachments; order of a few GB, not verified).

**So: `PLANS-IN-FLIGHT.md` "RUNNING · already started" is accurate but reads as further along
than it is.** Today the mirror yields nothing. Tomorrow it yields a pile of raw HTML.

### B.2 What the corpus actually contains, and its hard limit

Deliberate design choices in `wayback_mirror.py`, worth knowing before anyone plans on it:

- Latest capture of each URL, raw original bytes (`/web/<ts>id_/`), links **not** rewritten —
  it is a grep target, not a browsable offline site.
- `.msgNNNN` permalink duplicates and SMF action URLs filtered out; attachments deliberately kept.
- **Coverage ends ~2026-03-10** — Archive.org's crawler was blocked around 2026-03-29
  (`ml-forum-mirror-pipeline` memory). Everything posted in the last five months is invisible
  and will stay invisible while Cloudflare stands.

That limit has a concrete cost for strand A: the last captured post in topic 27350 is coon's,
2025-09-02. **The mirror cannot tell us whether the EOS R JTAG attempt succeeded since then.**
That is a question only a human with a browser — or kitor — can answer, which is another
argument for sending the message.

### B.3 What it is worth — one measured instance, and one honest gap

**Measured:** the entire kitor finding came out of a single Wayback retrieval of topic 27350.
Before it, `docs/jtag-research.html` asserted that nobody had ever done JTAG on DIGIC 6/7/8;
after it, the document's central claim was corrected, spike 010 was written, and spike 011's
framing red-team had to retract its "kitor premise unsupported" verdict *because that verdict
was itself based on the stale artifact* (spike 011 line 92). One retrieval overturned a
project-level belief and a red-team conclusion in the same day.

**Gap:** that is *one* instance, and it happened without the mirror — a targeted CDX fetch of a
single known topic did it. **The general claim ("the agent re-derives what the community
knows") remains unmeasured, and the mirror is not what produced the one win.** The peer file is
right to flag this and the right response is a test, not more infrastructure.

**The concrete test — three questions this project is currently paying for:**

1. The **DIGIC 7/8 MPU-watchdog suppress address** (spike 010 §2 — the one genuinely new
   problem versus kitor's PowerShot case).
2. The **6D2 FZC-8 access route** — spike 014 records the pinout as inherited from the
   R/RP/200D family and *"never measured on a 6D2"*, and whether the thumb-rest rubber hides a
   pad is unknown.
3. **TG_FREQ_BASE-class timer constants for the 6D2** — spike 011 §3 lists these under
   "physical constants with no ROM source" (`fps-engio.c:248-280`).

Grep the finished mirror for all three. **0 of 3 answered → the mirror is a library, not a
lever; keep it, build nothing on it.** 2 or 3 of 3 → the memory faculty is real and earns an
index.

### B.4 Do not build GraphRAG

Chris named a *"custom GraphRAG"* as the plan on Discord. Against 45k HTML files the lazy tools
already installed cover it: `ripgrep` for lookup, and the codebase knowledge graph (`ml-6d2`,
`qemu-eos-hw`, already indexed per PLANS-IN-FLIGHT B3) for code. A retrieval index over the
forum is worth building **only after** the 3-question test says the content is there. Building
it first is speculative infrastructure on an unmeasured premise, and it is the branch of this
direction most likely to consume a week and produce a demo.

One cheap improvement worth making *now*, while the process is still enumerating: nothing
verifies the URL list is complete after the 504-retry path. A count-and-compare against a fresh
`showNumPages` at the end would catch a silently truncated corpus. That is a few lines, and it
is the difference between "the forum doesn't mention it" and "we didn't download that page."

### B.5 Why strand B outranks its apparent importance

It is the only item in the entire VibePlan folder that requires **no permission, no account, no
hardware, no human, and no reply from anyone**, and it is already running. Against INTENT §4.1
("what can proceed while I am not here") it scores higher than anything else in this direction
and most things outside it. It costs nothing to keep. It just should not be *believed in* until
it is tested.

---

## Strand C — The Discord logger

**Verdict: abandon it.** Not defer, not park pending legal work. The reasoning below is why,
and §C.5 states the one thing that would reverse it.

### C.1 The built artifact is the prohibited design, verbatim

`discord-bot/bot.py` is 72 lines and does exactly this: for **every** text channel in **every**
guild the bot can read, backfill 5,000 messages, then log live, writing
`**{msg.author.display_name}** ({ts}): {body}` to `logs/<server>/<channel>/YYYY-MM-DD.md`.

Set that against `docs/legal/2026-08-16-discord-logging-gdpr-memo.md`:

| Memo requirement | `bot.py` as written |
|---|---|
| §A.2 "Design B — extract the finding, discard identity and message text" | Stores `display_name` + verbatim body. **This is Design A**, the one the memo says gives Art 3(2)(b) *"a serious case against you"* |
| §B.5 "dev/technical channels only, never off-topic or social" (Art 9 special categories) | No channel allowlist at all — `for ch in guild.text_channels` |
| §B.3 / Developer ToS §5 — export-by-user-ID and delete-by-user-ID, **demonstrated to admins before any invite** | Neither exists |
| Checklist — retention period, encryption at rest, kill switch | None |
| Checklist — published privacy policy linked in the Developer Portal | Does not exist |

So "built and verified" is true of the code and false of the design. **Essentially nothing of
it survives into a compliant version** except the discord.py boilerplate — maybe 20 lines. The
sunk cost is not a reason to continue; there is no sunk cost.

### C.2 The compliant design is cheap to code and expensive to land

The safe design is a **citation index**: parse each message into a technical proposition, keep
the proposition plus a message link, discard the text and the author. Deletion is free — the
link dies with the message. The memo is right that this is *fewer* lines than what exists.

The cost is not the code. It is: a published privacy policy, a documented Art 6(1)(f)
balancing test, a pinned per-channel notice, demonstrated export/delete, a stated retention
period, encryption at rest, and — flagged **unverified** in the memo (§B.6) — possibly an
Art 27 EU representative, which is genuinely awkward for a US individual. The memo calls the
paperwork *"a weekend, not a quarter."* That is the cost of *being* compliant. It is not the
cost of *being believed*, which is the actual gate.

### C.3 The gate is social, and a legal answer makes it worse

The memo's own Layer 1, point 7: *"Two of the three gates here are not legal. kitor's objection
was social, and the server admins can refuse for any reason at all. **Being right about
Art 3(2) does not get the bot invited.**"*

Returning to a former GDPR DPO with a legal memo that says his framing was slightly wrong
(consent is one of six lawful bases; legitimate interests is the normal one) is *correct* and
*socially fatal*. The memo says so explicitly: *"arguing that point is a losing move socially."*
And the person who objected first was not arguing law at all — kitor objected to the posture.
There is no document that fixes a posture problem.

### C.4 The decisive point is value, not law

Even granting a perfect compliant design and a friendly reception:

- **Discord's marginal value over strand B + GitHub is unmeasured**, and it is the only one of
  the three sources that requires anybody's permission.
- The **need it was built for is already met**. The stated need was "search past discussion
  while developing." The thread that mattered is saved at
  `docs/discord/2026-08-16-ml-discord-thread.md` — Chris's own scrollback of a conversation he
  was in, which the memo (§D.3) identifies as materially different and which the
  `6d2-discord-bot` memory already names as the legal-fallback pattern. That covers the real
  requirement at zero cost and zero risk.
- The friction is denominated in the one currency this project is short of: goodwill with three
  or four named people, whose cooperation **strand A depends on**. Spending it on a logging bot
  to save scrolling is a bad trade even at a good exchange rate.
- Rule 16 kills the design Chris actually described on Discord (*"so the llm has a better idea
  of what to do"* over who-said-what — a person-graph). Rule 21 forbids training on message
  content; the citation index is retrieval-only and *probably* fine, but "probably" is
  Discord's call, not ours.

### C.5 What would reverse this, and the housekeeping either way

**Reversal condition:** an admin or maintainer *proactively* asks for a searchable index. The
seed exists — iaburn, in that same thread: *"I always thought that you guys gave a lot of
useful information on this channel and it's super hard to find anything into tons of chats and
messages... which is a pity."* If that ever becomes a request, the posture inverts from taking
to providing, and the correct build is different anyway: a tool the **admins** run on their own
server, not a bot Chris is invited to point at it. The route there is to be visibly useful
first (strands A and D), not to ask a second time.

**Housekeeping now:** the Discord application `ml-devlog-readonly` (client ID
1538248909204226158) exists with a live bot token that Chris holds. If the strand is abandoned,
delete the application. A registered app with a live token and no purpose is a small standing
liability and a reminder of a bad first impression.

---

## Strand D — "Volunteers check LLM output"

### D.1 What was proposed and what was refused are not the same thing

Chris (Discord, 8:40 AM): *"there may be a way to set up volunteers to help debug the LLM slop
as you have so many people that want to help but don't know how to code. It's possible I could
make it so the outputs could go over what to check for the volunteers."*

names_are_hard (8:41 AM): *"I don't think LLMs are good enough to do PR review. Maybe in the
future. The better compromise for now is for a human, if they are using an LLM, to try to
understand what the LLM wants to do, in order to understand what the better thing to do is."*

Read precisely, he refused **LLM-as-reviewer**. Chris proposed **LLM-as-test-designer with
humans as the instrument**, which is a different thing and which the counter does not address.
But two of his *other* statements bite on it much harder, and they are the ones that matter:

- On PR #298: *"The core finding… might be very useful! But first we have to test that
  **(which LLMs can't do as it needs multiple physical cams)**."*
- On cost: *"I have to read 4 over-confident paragraphs about the change, in order to work out
  what might be the correct action."*

**So what he needs from other humans is hardware coverage, not review. And what he does not
want is more LLM prose to read.** That is the shape the surviving version has to fit.

### D.2 The version that survives

**Not "volunteers check LLM output." "Volunteers run a falsifiable test on a camera we do not
own, and report what it did."**

It fits every binding constraint at once:
- It targets the maintainer's own named bottleneck — physical hardware in the loop, and
  specifically the "multiple physical cams" he says LLMs cannot supply.
- It is queued work in the §4.1 sense: the plan is written unattended, and executed whenever a
  volunteer has a spare hour. Chris's availability is not in the loop at all.
- It respects §4.4: body-session time is the scarcest resource, and this project has already
  lost two of its own camera sessions to instrumentation defects the machine should have caught
  (34 log lines self-evicting from a 21-line console; a diagnostic print behind a guard that
  was already false). A test plan sent to a stranger has exactly one shot.
- It produces evidence rather than a diff, which is the mode the maintainer asked for.

**The first instance already exists and is nobody's task.** PR #298 / `PROP_LV_ACTION`: the
maintainer said the finding may be very useful but must be tested across cameras.
thebilalfakhouri has an M50 and asked for the code twice. Jok3r has a 200D and has already
done adjacent EDMAC work. That is three camera models and two willing people, in the same
thread, for the exact test the maintainer named as the blocker. Writing that test plan is desk
work, it is unattended, and it converts the project's worst-received PR into its most useful
contribution.

### D.3 Rules for the artifact — these are the whole design

1. **Falsifiable in advance.** State what result would *refute* the hypothesis, in the plan,
   before anyone runs it. Otherwise it is confirmation-gathering and this audience will see it.
2. **The firmware records the evidence, not the person.** §4.4's lesson: the fix that worked
   was `RAWDIAG.LOG` self-recording, not asking Chris to photograph a screen. A volunteer
   returns a file, never a transcription.
3. **Instructions are an artifact with the same rigour as code.** Chris himself had to correct
   the button instructions — *"I think your directions don't sound correct to the model I even
   have… you may want to look up what the buttons are on Canon"* — which produced
   `docs/6D2_CONTROLS.md`. Directions to a stranger's camera get verified against that camera's
   documented controls before they are sent.
4. **Never distribute a build we produced.** Hard line. An untested LLM-generated ML build on
   somebody else's body is a strictly worse version of the untested-PR problem, on hardware
   Chris does not own and cannot replace. Volunteers run *upstream* builds, or builds from the
   maintainer's tree, and report observations. If a test cannot be expressed that way, it does
   not get sent.
5. **Do not call it "checking LLM slop."** That frames volunteers as janitors for our output.
   Frame: here is a symptom, here is the exact reproduction, tell me what your camera does.
6. **No platform.** No web app, no form, no dashboard, no result database. A markdown file in a
   forum post is the entire product.

### D.4 The honest limit

Stripped of ambition, strand D is: *write good test plans and ask politely in a thread.* There
is no technology in it, which is precisely why it might work — the version with technology
(volunteer portal, automated ingestion, build distribution) requires trust, hosting and a
population of people, none of which exist. It also has no mechanism to make anyone participate.
Two people asking for code in one thread is interest, not a commitment, and the request that
follows a rejected PR carries the rejection with it.

And the original framing — using volunteers to substitute for code review at scale — does not
survive in any form. The maintainer refused it, non-coders cannot review a diff, and the
project's own experience says the useful non-coder contribution is *measurement*, not judgement.

---

## §E — The Layer 4 §4.2 judgment, which governs this whole direction

INTENT §4.2 says it directly: Chris supplies hardware, accounts and goals; the LLM supplies
domain and social judgement — and **"Chris cannot easily catch a wrong call in that layer,
because not knowing the terminology is precisely why he delegated it."**

**Three of this direction's four strands are outward-facing communication.** There is no
technical artifact to check them against, no test that fails, no build that breaks. It is the
single worst-audited surface in the project, and the measured base rate is poor: of four
outward-facing artifacts produced in two days, three landed badly (bot request → hostile reply;
emoji status post → "annoying"; "first-ever raw video" → rejected, and it contaminated the true
claims), and the fourth was caught only because a classifier blocked it for promising Chris's
time to a stranger.

A "Chris approves the wording" gate does not fix this — he cannot evaluate the wording. The
gate that works converts an unauditable judgement into an auditable one:

1. **Agents draft, Chris sends.** No agent account, no automated posting, ever. Automating his
   personal Discord account is a self-bot and a ban.
2. **A claims ledger accompanies every outward message.** Each factual assertion tagged
   `verified` / `inferred` / `unknown`, with the file, address or measurement behind it. Chris
   can check *"did we measure this?"* even when he cannot check *"is this the right
   terminology?"* — that is the whole point. This is the mechanism that would have caught
   §A.0's donor-board claim (`unknown`, no source) **and** "first-ever raw video"
   (unverifiable in principle — you cannot verify a negative about the whole internet).
3. **No-commitment rule.** No message promises Chris's time, hardware, money or attention
   unless he has already said yes to that specific thing. This is the PR-223 block, generalized
   into a rule instead of a lucky catch.
4. **A literal banned-phrase list:** "first", "first-ever", "fully working", "comprehensive",
   "production-ready", bold section headings, emoji headers, and any superlative. Crude, but it
   catches the exact failures on record.

That ledger is the only genuinely new *thing* this direction builds, it is four rules and a
checklist, and it is what makes the rest of it safe to execute.

---

## §F — Cost, sequencing, and what would make me abandon this

### Cost and unattended fraction

| Strand | Agent cost | Chris cost | Unattended fraction | Calendar |
|---|---|---|---|---|
| A — verify §A.0, draft, ROM watchdog search | 1 session verify + draft; 1–3 sessions for the ROM search | ~10 min to read and post | ~90% up to the send | Reply in days, or never |
| B — mirror | 0 (running) | 0 | **100%** | 15–25 h to finish downloading |
| B — 3-question test | 1 session after download | 0 | 100% | 1 session |
| C — Discord | 0 (abandoned) | 5 min to delete the app | n/a | n/a |
| D — PROP_LV_ACTION test plan | 1–2 sessions | ~10 min to post | ~90% up to the send | Uptake unknowable |

Nothing here costs money and nothing risks the camera. The scarce resource being spent is
**goodwill with four named people**, and it is close to overdrawn.

### Sequencing

1. **Verify §A.0** (re-retrieve topic 27350, grep for `donor`). Blocks strand A. ~2 minutes.
2. **Let strand B finish.** Do nothing to it except add the URL-list completeness check.
3. **Do the ROM0 watchdog/ERR80 static search** — it is desk work, it is spike 010's Phase 0
   anyway, and it converts the strand-A message from an ask into an offer.
4. **Send the strand-A forum post**, with the claims ledger attached for Chris.
5. **Run the 3-question test on the mirror** when it finishes. It decides whether the memory
   faculty gets any further investment.
6. **Draft the PROP_LV_ACTION test plan** (strand D) — desk-only until someone volunteers.
7. **Delete the Discord application.**

### What would make me abandon this direction

- **Strand A:** no reply to the forum post within three weeks, and no reply to one direct
  follow-up. Then collaboration is unavailable, strand A is dead, and direction 2's donor-body
  budget is the only remaining path — which is a *useful* negative result, because it prices
  the decision Chris has not yet made. Also abandon immediately if a reply declines to share
  method; do not press a second time.
- **Strand B:** if the 3-question test returns **0 of 3**, build nothing on the mirror. Keep the
  files (they cost nothing) and stop treating "the corpus" as a project component. Separately,
  if the download exceeds ~24 hours or the disk cost becomes material, narrow the URL list to
  topic pages and drop attachments.
- **Strand C:** already abandoned. Reverse only on an unprompted request from an admin.
- **Strand D:** abandon if the first test plan gets zero uptake, and abandon *immediately* if
  the design ever requires sending a build we produced to a stranger's camera.
- **The whole direction:** abandon if four weeks pass with no artifact that changes what the
  project actually does. This is an *enabling* direction — if the enabled thing never happens,
  it was pure overhead. And abandon it if one more outward message lands badly: with this group,
  a fourth bad landing is not recoverable, and at that point the correct move is to stop
  talking and ship something verifiable instead.

---

## Honest weaknesses

- **It produces no code and no camera capability.** INTENT §4.3 says a direction that ends in no
  visible camera capability cannot demonstrate the method. This one cannot satisfy §4.3 by
  itself — it must be paired with direction 1 or 3, and it should never be the *only* thing
  running.
- **Strand A depends entirely on a stranger's goodwill**, requested immediately after a first
  contact that drew a hostile reply from that exact stranger. The most likely single outcome is
  silence.
- **The corpus premise is largely unmeasured.** One measured instance (the topic-27350
  retrieval, which overturned a project belief and a red-team verdict), and that instance did
  not need the mirror. The general claim is plausible and unproven, which is why §B.3 is a test
  rather than a plan.
- **The mirror has downloaded zero pages** as of this writing and will take most of a day. Any
  plan that assumes a usable corpus this week is wrong.
- **Strand D has no forcing function.** It cannot make anyone participate, and its audience just
  watched a PR from this project get sent back.
- **The failure mode specific to this direction: it is pleasant to work on.** It produces
  documents and messages, which look like progress, cost almost nothing to generate, and cannot
  be falsified by a build. It is the direction an LLM will over-produce in and the one Chris is
  least equipped to check. The claims ledger in §E is the mitigation; naming the bias is the
  rest of it.

## How this relates to the other directions

| Direction | Relationship |
|---|---|
| **1 — Automation harness** | Complementary and non-overlapping. Harness = perception and hands; this = memory and relationships. Direction 1's addendum already names the corpus as the memory faculty it needs |
| **2 — JTAG on DIGIC 7** | **Strand A may replace most of its cost.** One message, before any hardware is bought. Strand A's ROM0 watchdog search *is* spike 010's Phase 0, so the two share their only unattended task |
| **3 — Feature roadmap** | Strand D is how paused features get tested on cameras nobody here owns. Otherwise unrelated |
| **4 — Upstream push** | Same relationship, same people, same goodwill budget. Strands A and D make the PR conversation easier; more untested patches make both worse. These two should be sequenced together or they will spend the same credit twice |

## Key references

- Discord transcript (the whole social record): `../docs/discord/2026-08-16-ml-discord-thread.md`
- Legal analysis, incl. Developer Policy rules 15/16/21 and Developer ToS §5:
  `../docs/legal/2026-08-16-discord-logging-gdpr-memo.md`
- The built logger, and why it is the wrong design: `../discord-bot/bot.py`,
  `../discord-bot/README.md`, `../discord-bot/DM_TO_ADMIN.md`
- kitor's confirmed results and the DIGIC 7 gap: `../docs/jtag-research.html` §§485-486, 702;
  memory `jtag-on-digic`
- EOS MPU watchdog / ERR80 mechanism, and Phase 0's ROM search:
  `../.planning/spikes/010-jtag-digic7/README.md` §2, §3
- "Ask kitor" as an endorsed free move: `../.planning/spikes/011-hardware-in-the-loop/README.md`
  lines 25, 103
- The outward-communication gate that worked once already:
  `../.planning/prs/DRAFT-comment-on-upstream-PR-223.md`
- Mirror pipeline and its Cloudflare/Wayback constraints: `~/ml-mirror/wayback_mirror.py`,
  `~/ml-mirror/progress.log`, memory `ml-forum-mirror-pipeline`
- Maintainer norms, distilled: memory `ml-upstream-contribution-norms`
