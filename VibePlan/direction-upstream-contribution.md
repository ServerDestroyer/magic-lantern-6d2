# Direction 4 — The Upstream Contribution Push

**Status:** recorded (not decided, not planned)
**Recorded:** 2026-08-16
**Judged against:** [INTENT.md](INTENT.md), especially Layer 3 (maintainer feedback is binding) and Layer 4 §4.1 / §4.2.
**Live state verified today** against GitHub (`gh pr list/view`, `gh api`), not against the summaries in this folder. Two things in [PLANS-IN-FLIGHT.md](PLANS-IN-FLIGHT.md) turned out to be wrong; they are corrected below.

---

## One-sentence goal

Land the work this project has already done into `magiclantern_simplified` and `qemu-eos` — and repair the trust that was spent getting the first five PRs open — without costing the one active maintainer more than the contribution is worth to him.

---

## Where this actually stands, verified 2026-08-16

### The five ML PRs

| PR | Title | Diff | Body words | Maintainer response | Real status |
|---|---|---|---|---|---|
| [#294](https://github.com/reticulatedpines/magiclantern_simplified/pull/294) | 6D2: override the 29:59 MOV/MP4 limit | +14 / 2 files | 165 | none | **Clean.** 6D2-only, `consts.h` + `features.h`. Hardware-confirmed. Nothing to do but wait. |
| [#295](https://github.com/reticulatedpines/magiclantern_simplified/pull/295) | property: don't wait out the timeout on denied writes (D678) | +8 / 1 file | 174 | none on GitHub | **Should be reworked** — see §2. It is the right instinct at the wrong altitude. |
| [#296](https://github.com/reticulatedpines/magiclantern_simplified/pull/296) | log-d678: don't spin forever when the buffer alloc fails | +17 −2 / 1 file | 107 | none | **Cleanest of the five.** `src/log-d678.c` is not wired into any platform build, so the blast radius is literally zero for shipping firmware — and the PR does not say so. One sentence would raise its merge odds. |
| [#297](https://github.com/reticulatedpines/magiclantern_simplified/pull/297) | mlv_lite: stamp measured fps into the MLVI header | +36 −2 / 1 file | 628 | **YES — 2026-08-16T12:07Z** | **Needs an answer today.** See §3. |
| [#298](https://github.com/reticulatedpines/magiclantern_simplified/pull/298) | mlv_lite: reallocate buffers after an auto-stop | +10 / 1 file | 617 | on Discord, not on the PR | **Needs rework.** See §2. |

**Correction 1 to PLANS-IN-FLIGHT.md.** It records "#298 needs rework — maintainer wants `PROP_LV_ACTION` fixed properly". That is true *in substance* but wrong about *where*: `gh pr view 298 --comments` shows exactly one comment, authored by ServerDestroyer. The maintainer's objection was made on Discord at 8:45 AM with a link to #298's diff, and **has never been written on the PR itself**. Anyone reading the PR thread cold sees an unanswered, unreviewed PR. That matters: the objection is invisible to every other reader, and answering it only on Discord leaves the public record showing a maintainer who ignored a contributor.

**Correction 2 — new since this folder was written.** There is now a real maintainer comment on GitHub, on **#297**, posted 2026-08-16T12:07:05Z. Nothing in `.planning/` or `VibePlan/` records it. In full:

> This sounds like it hides the real problem (incorrect value returned by fps_get_current_x1000()) ?
>
> Fixing the real problem would be greatly preferred.
>
> The LLM text above suggests a risk: behaviour may be bad on other cams. Have you done any testing in this area?

That is a direct question with a factual answer that is currently unflattering, and it is the highest-priority item in this whole direction.

**The measurable pattern.** The three PRs with bodies of 107–174 words drew no complaint. The two with bodies of 617 and 628 words are exactly the two that drew "I have to read 4 over-confident paragraphs about the change, in order to work out what might be the correct action". Peer PRs in the same queue run 179–587 words. **Under ~200 words is the observed safe band**, and it is not a stylistic preference — it is the maintainer's stated cost complaint, measured.

### The four qemu-eos PRs

Drafted, patches verified to apply against `git archive HEAD` (`.planning/prs/qemu-eos-submission-plan.md` §2), and **not pushed**. Blocking facts found today:

- **ServerDestroyer has no `qemu-eos` fork.** `gh repo list ServerDestroyer --fork` returns four forks; `qemu-eos` is not among them. Step zero is a fork Chris must create.
- **`qemu-eos` is close to dormant.** Branch `qemu-eos-v4.2.1` (our base, `4b667a1d3c`) last received a commit **2025-02-03** — 18 months ago. `master` last moved 2021-12-05. Three PRs are open; the oldest, "Fix docker build" (#17), has been open since 2025-07-24 with no reply.
- **Q1 is already upstream, in someone else's open PR.** `qemu-eos` PR **#18** (jed2nd, EOS R DIGIC 8 bring-up, draft since 2026-06-17) changes `hw/eos/mpu_spells/outils.py` with the *same* `os.environ.get("ML_PLATFORM_DIR", …)` override and the same default string, plus a `try/except` that degrades gracefully instead of dying. Our Q1 is a strict subset of a two-month-old open PR. **Q1 must not be filed.**
- **Q2 and Q4 collide with that same PR.** #18 touches `hw/eos/mpu.c` (Q2's registration site), `hw/eos/eos.c` and `hw/eos/eos.h` (Q4's entire surface), and adds `hw/eos/mpu_spells/R.h` — a DIGIC 8 spell set. Someone else is doing the same category of work, and this project did not know.
- **`qemu-eos` PR #19** (ssubbotin, 2026-08-10) ports `extract_init_spells.py`, `extract_button_codes.py` and `annotate_mpu_log.py` to Python 3. Those are the scripts that produced our spell set. It has zero comments.

**This is the memory-faculty failure INTENT Layer 3 names, caught in the act.** Three open upstream PRs overlap this project's work, none was noticed, and one of our four planned submissions is a duplicate. The cost of *not* having the corpus (direction 5) is not hypothetical; it is one wasted PR and two near-misses, found in ten minutes of `gh api` calls.

---

## §1 — Trust economics, quantified

The maintainer's objection is an economic one, so it deserves numbers rather than sympathy.

**The team is one person.** On `dev` in the last 90 days: 28 commits, **26 of them by `stephen-e`** — the git identity of `reticulatedpines`, who is `names_are_hard` on Discord. The other two are by WalterSchulz. There is no second reviewer.

**External contribution throughput is 5–11 merged PRs per year, and currently zero.**

| Year | PRs merged |
|---|---|
| 2021 | 11 |
| 2022 | 10 |
| 2023 | 11 |
| 2024 | 5 |
| 2025 | 6 |
| 2026 (to Aug 16) | **0** |

The most recent merged PR is #237 (kitor, M6II port), **2025-11-12 — nine months ago**. Twenty-one PRs are open; the oldest dates from 2022.

**What Chris's five PRs represent:** 5 of 21 open PRs — **24% of the entire open queue** — filed inside 14 hours, by a contributor who had publicly said "It is llm slop! I didn't even review the code or the explanation." Five PRs is roughly *one full year of this repo's merge throughput* arriving at once.

**Two fair caveats, or this section overstates.**
1. PR merges undercount the maintainer's real work. He commits directly, and the four merges in the last 12 months came from established contributors with hardware (kitor ×3, bilalfakhouri ×1). "Zero merges in 2026" measures the external-contribution channel, not the project.
2. He explicitly offered to do the work himself: *"It should be pretty easy to cleanup and push, I may look at it today, but got a few things in the queue"* (8:31 AM). **The realistic landing path for this work is not "he merges my PR" — it is "he rewrites it and pushes it himself."** That reframes what a good submission is: not a mergeable diff, but a *finding clean enough that reimplementing it is cheap.* Which is precisely what he asked for — *"report potential bugs, with reasoning, rather than speculative fixes without testing."*

**What a genuinely welcome cadence looks like, given those numbers.** One outward-facing artifact per 72 hours, maximum, while the trust deficit stands. Bug reports with reasoning outnumbering patches at least 2:1. Every patch either 6D2-only (blast radius zero for him) or accompanied by an explicit statement of what could *not* be tested and who needs to test it. Under 200 words. No superlatives. That is a rate of roughly ten artifacts a month, which is already more than the repo has merged in nine months — so even this is generous to us, not to him.

---

## §2 — #298 and the PROP_LV_ACTION fix he actually wants

His words, Discord 8:45 AM, linking #298's diff:

> Probably, the better thing to do is fix PROP_LV_ACTION, rather than write a complicated workaround for new cams to stop it being used only for those cams
>
> But I have to read 4 over-confident paragraphs about the change, in order to work out what might be the correct action, then write code for that, then test it on a range of cams
>
> The core finding, that lack of handling for PROP_LV_ACTION causes a problem on new cams, might be very useful! But first we have to test that (which LLMs can't do as it needs multiple physical cams)

He is right, and the root cause is one level deeper than either #295 or #298 reaches.

### The actual defect

`src/property.c:391-401` — on D678, `prop_request_change()` returns `void` and, for any property not in the platform's `prop_write_allow[]`, `return`s having done nothing. The caller cannot tell.

`platform/6D2.111/property_whitelist.h` allows exactly four writes: `PROP_ICU_AUTO_POWEROFF`, `PROP_BUTTON_ASSIGNMENT`, `PROP_REMOTE_SW1`, `PROP_REMOTE_SW2`. The 200D allows three. **Every other `prop_request_change_wait()` call site in the tree — there are about thirty — is a silent no-op on every D678 body.**

Then `src/powersave.c:38-57`:

```c
    int x = 1;
    BMP_LOCK(
        lv_zoom_before_pause = lv_dispsize;
        prop_request_change_wait(PROP_LV_ACTION, &x, 4, 1000);   // dropped on D678
        msleep(100);
        clrscr();
        lv_paused = 1;                                            // ...set anyway
    )
    ASSERT(LV_PAUSED);                                            // #define LV_PAUSED (lv_paused)
```

`lv_paused = 1` is set unconditionally, and the `ASSERT` checks ML's own shadow variable, not the camera. So on every D678 body **`PauseLiveView()` returns having told the rest of ML that LiveView is paused when LiveView is still running.** That is the bug. `mlv_lite`'s missing re-arm is one downstream symptom; there are ~30 other call sites with the same exposure, and `src/fileprefix.c:59` is the only one found that checks the return value at all.

### The three-part fix, split by who can test it

**(a) Make denial distinguishable — ~5 lines, desk-checkable, zero risk.**
`prop_request_change_wait()` currently returns `0` for "denied" *and* `0` for "timed out". #295 makes the denial fast but keeps it indistinguishable. Return a distinct negative value on denial instead. Purely additive: every existing caller tests truthiness, so behaviour is unchanged for all of them. **This supersedes #295** — same latency win, plus the information the caller needs.
*Unreviewed edge #295 introduces and nobody has checked:* the early `return 0` skips `prop_reset_ack(property)` (`src/property.c:420`), so a stale ack from an earlier successful write to the same property is no longer cleared. Probably harmless; not verified either way; must be stated rather than glossed.

**(b) Stop lying about LiveView state — ~6 lines in `powersave.c`, testable on our body.**
Do not set `lv_paused = 1` when the write was denied; return failure from `PauseLiveView()` and let callers see it. Once ML's LV state is honest, `mlv_lite`'s existing state-fingerprint path notices the transition on its own and **#298's guard becomes unnecessary.** That is exactly "fix `PROP_LV_ACTION` rather than write a workaround for new cams."

**(c) Decide whether `PROP_LV_ACTION` should be writable on D678 at all — cannot be done here.**
This is the part he is really pointing at, and it is gated by the enormous warning at `src/property.c:330-337`: before enabling a write on a new port you must verify the meaning and valid range match a fully-working port. For `PROP_LV_ACTION` (`0x80050022`, `0 == LV_START`, `1 == LV_STOP`, len 4) that means decoding the property's handler in each D678 ROM and then testing on each body. **This project has one D678 body and one ROM.** So (c) ships as a *bug report with reasoning* — the `powersave.c` evidence above, plus whatever the 6D2 ROM decode shows — and explicitly asks him or another D678 owner to confirm. Which is the mode he requested.

### What to do with #298 concretely

Close it, or convert it to a bug report, and say why in one short comment. Do not push (a)+(b) as a replacement PR in the same breath — that is more patch volume aimed at a person who just asked for less. Post the finding; offer the patch only if he wants it.

---

## §3 — #297: the honest answer, and the finding that answers it for free

Two questions were asked. Both have answers this project can give today.

### "Have you done any testing in this area?"

**No — and no substitute was attempted.** The honest reply is one sentence: this was tested on one 6D2 across four takes; no other body and no other ROM exists here (`roms/` contains exactly `6D2/ROM0.BIN` and `ROM1.BIN`; a whole-filesystem search for `ROM*.BIN` found nothing else — recorded in `.planning/prs/qemu-eos-submission-plan.md` §3.6). Any claim about other cameras in that PR body is inference, not measurement. Saying that plainly is the single cheapest trust repair available, and it costs nothing but the admission.

### "This sounds like it hides the real problem"

He is right, and the real problem is one his own commit already documented.

`src/fps-engio.c` carries two comment blocks he wrote in commit **`ffef459f0d`** ("fps-engio: add some measurements from real cams", stephen-e, 2025-07-10). The 200D block (`:286-303`) ends *"Variable? We're missing something on this cam. Possibly a clock multiplier / divisor?"*. The 6D2 block (`:305-320`) ends *"Variable, like 200D? Different base clock though."*

Take his own logged `(timer_a, timer_b)` pairs, apply `fps_get_current_x1000()`'s actual `+1` on each register, and compute the effective timing-generator clock per mode:

| mode | 6D2 (a, b) | 6D2 effective TG | 200D (a, b) | 200D effective TG |
|---|---|---|---|---|
| 23.98p | 0x588, 0x7b0 | 66.89 MHz | 0x461, 0x618 | 41.99 MHz |
| 25p | 0x588, 0x760 | 66.92 MHz | 0x461, 0x5d8 | 41.99 MHz |
| 29.97p | 0x588, 0x626 | 66.89 MHz | 0x461, 0x4e0 | 42.00 MHz |
| 50p | 0x3ae, 0x3b0 | 44.56 MHz | 0x2e9, 0x2ec | 27.94 MHz |
| 59.94p | 0x1d8, 0x314 | 22.37 MHz | 0x175, 0x270 | 14.01 MHz |

**Both cameras show the same ratio set, 1 : 1/1.5 : 1/3, to within 0.6%:**
6D2 → 66.89 / 44.56 = **1.501**, 66.89 / 22.37 = **2.990**.
200D → 41.99 / 27.94 = **1.503**, 41.99 / 14.01 = **2.997**.

Equivalently: a common master clock with integer dividers **/2, /3, /6** selected by video mode. That is a direct, specific answer to the question he wrote in his own comment — "possibly a clock multiplier / divisor?" — **yes, and it looks like /2, /3, /6, on both cameras.** It is derived entirely from numbers already in his tree. No hardware, no ROM, no capture.

Two consequences worth stating, one confirmed and one flagged as a question:

- **Confirmed for the 6D2.** `TG_FREQ_BASE 66800000` equals the ≤30p effective clock, so `fps_get_current_x1000()` is *correct at ≤30p* and wrong by exactly ×1.5 at 50p and ×3 at 59.94p. This reproduces the observed header value bit-exactly, through ML's own staged integer arithmetic: `calc_tg_freq(473)` = `(66800000/473)*1000 + (66800000%473)*1000/473` = 141,226,215, then `/789` truncates to **178,993** — the value found in the MLV (`.planning/spikes/006-rawvideo-memory/RECORD_PATH.md:248`). Naive float division gives 178,994; the truncation is what makes it exact, which is itself a check that the model is right.
- **A question, not a claim, for the 200D.** Its `TG_FREQ_BASE` is `84000000` — almost exactly *twice* its measured ≤30p effective clock of ~42 MHz. Arithmetically that predicts ML reporting ~2× the true fps at ≤30p on a 200D, which someone would probably have noticed by now. So either the register values in the comment are not what `get_fps_register_a/b()` actually return on that body, or something else is going on. **Ask, do not assert.** (Related loose end, tangential: `platform/6D2.111/fps-engio_per_cam.c:get_fps_register_a_default()` returns `1122 << 16` — and 1122 is `0x461 + 1`, the 200D's timer A. A 200D value appears to have been copied into the 6D2 port as a fallback.)

**The correct fix he asked for** is therefore a mode-aware TG clock — either a per-mode divider derived from the video mode, or the divider register itself once located — replacing the single `TG_FREQ_BASE` constant on 6D2 and 200D. Locating that register is real reverse-engineering work and is not scoped here.

**What to do with #297.** It bundles two unrelated changes, and one of them he already praised on Discord — *"the shadowed fps var is hard to spot"*. `raw_video_rec_task()` redeclares `int fps` inside the `card_index == 0` block, leaving the outer `fps` stuck at 1 for the whole recording and feeding the writer's overflow throttle a one-second frame interval. That is an unambiguous, body-agnostic, few-line bug fix **currently held hostage by the contested header-stamp change in the same PR.** Split it out. Then reply to the #297 comment with the two answers above, and let him decide whether the measured-fps stamp is a workaround worth keeping in the interim.

---

## §4 — The retraction

### What was claimed and what it cost

Discord, 8:30 PM: *"🎬 Raw video is real — First-ever raw video recorded on a 6D2"*, under the header *"All of this is tested on a real body, not just emulation."*

His reply, 12:50 AM:

> E.g. "First-ever raw video recorded on a 6D2" - no. #off-topic-general
>
> Still always appreciate people improving things, but please don't trust LLM to write good descriptions
>
> (and then because I know that's not true, I have to question whether "All of this is tested on a real body" is true. LLMs lie a lot)

The claim also contradicted something Chris himself had written six hours earlier: *"raw video was already 'mostly working' in the tree thanks to stephen-e — this is finishing work on that foundation."* The overclaim was not just wrong, it was inconsistent with this project's own record.

**Damage is not confined to Discord.** The claim is still live in three places:
1. `.planning/ROADMAP.md` line 68 — *"RAW VIDEO RECORDED ON THE BODY (2026-08-15 16:12 — first ever on a 6D2)"*.
2. Git commit `5c009d7`, subject *"docs(roadmap): raw video recorded on the body — first ever on a 6D2"*.
3. `patches/README.md` §0007 — *"First DIGIC 7 spell set in qemu-eos."*

**`ServerDestroyer/magic-lantern-6d2` is a PUBLIC repository** (verified: `gh repo view … --json visibility` → `PUBLIC`, last push 2026-08-16). All three are published. The commit subject cannot be edited without a history rewrite, so it needs a correcting commit rather than a rewrite.

Verified clean: the phrase appears in **none** of the five posted PR bodies. The overclaim never reached GitHub's PR threads.

### Draft retraction — Discord, same channel as the original post

Written to be short, first-person, free of headings and bold, and to make no attempt to re-stake a narrower "first". Chris posts it under his own name.

> Correction to my status post last night. "First-ever raw video recorded on a 6D2" was wrong, and I've taken it out of my notes. Raw video was already largely working in the tree from stephen-e's work — what I did on top of it was find and fix specific defects: the denied property write that stalled buffer allocation, the dead state after a buffer-full auto-stop, and the garbage fps in the MLV header. I should have checked before claiming a first, and I understand that getting that wrong makes the rest of what I wrote harder to take at face value.
>
> On "tested on a real body" — it is true, the MLV files and the timing logs came off my camera, but you have no reason to take my word for it after the other claim. So from now on I'll attach the evidence with each change and drop the superlatives entirely.

### Where else it goes

- **`.planning/ROADMAP.md` line 68** — delete the parenthetical. Replace with something factual and unfalsifiable, e.g. *"raw video recorded and finalized on the body (2026-08-15 16:12), building on existing tree support"*.
- **New commit** whose message states the correction explicitly, since `5c009d7` cannot be edited. That commit is the public record of the retraction.
- **`patches/README.md` §0007** — replace *"First DIGIC 7 spell set in qemu-eos"* with the checkable form: *"`hw/eos/mpu_spells/` currently stops at DIGIC 5 bodies; this adds a set captured from a DIGIC 7 body."* Same information, no superlative, and it survives the fact that `qemu-eos` PR #18 is adding a DIGIC 8 set concurrently.
- **`.planning/prs/PR-Q2-qemu-6D2-mpu-spells.md` line 26** — same edit. It currently opens *"This adds the first MPU init spell set for a DIGIC 7 body"*. Do not ship a superlative in the PR that is meant to rebuild credibility.

**Sequencing matters.** The retraction goes out *before* any new submission, and ideally in the same message as the #297 answer, so the first thing he sees after the complaint is the correction plus a substantive reply — not another PR.

---

## §5 — The qemu-eos set: what to submit, and what to offer as a report instead

This is the strongest card the project holds, and it is worth being precise about *why*. He said, 12:43 AM:

> The spells stuff is interesting - Alex repeatedly refused to explain some of the problems I saw with 200D emulation, even after I'd dumped MPU logs. I ended up improving the emulation in many places, but never knew how to import recorded MPU traffic. Might be able to use the existing scripts now I know where they are

Read that carefully. **He does not want our spell file. He wants the method.** He has his own 200D MPU logs and could not import them. The highest-value deliverable is therefore not `6D2.h` — it is a short, reproducible account of *how a DebugMsg capture becomes a spell header*, which is a thing he can then apply to his own 200D dumps and to every future body. Q2's PR body already contains that account; the mistake would be to bury it under 12KB of 6D2-specific evidence.

Note also that ML PR **#293** (ssubbotin, 2026-08-10) is literally *"developer_guide: write the MPU section"* — someone is writing that documentation upstream right now, in the ML repo. The right move may be to contribute the capture-to-spells recipe *there*, not to open a fifth qemu-eos PR.

### Verdict per PR

- **Q1 (`outils.py` / `ML_PLATFORM_DIR`) — DO NOT SUBMIT.** Already present in `qemu-eos` PR #18, in a strictly better form. Instead: comment on #18 confirming the fix works, stating that these scripts produced a working DIGIC 7 spell header end-to-end, and that #18's `try/except` fallback is the right call because button names are optional for init spells. Two sentences, helps another contributor, costs the maintainer nothing.
- **Q2 (6D2 MPU spells + `assert_log` address) — SUBMIT, but trimmed.** It fixes a concrete boot failure with strong static evidence, it is additive (a new data file plus two lines in `mpu.c`), and it carries no cross-model risk. Trim the body hard — the current draft is 12.8KB. Lead with the failure, the cause, and the one-line reproduction; move the eight-SD-card elimination history to a collapsed section or drop it. Fix the superlative first (§4). Note the `mpu.c` hunk may conflict with #18 once that lands; say so.
- **Q3 (button codes) — SUBMIT, after Q2, or hold.** Nothing in it is on the boot path (measured), so it can wait indefinitely with no cost. 28 of 30 codes are decoded from ROM0 and cross-checked three ways; two (`BGMT_PRESS_ZOOM_OUT`/`BGMT_UNPRESS_ZOOM_OUT`) are inferred from the 200D and are not in the 6D2 ROM at all. Only six have body-log confirmation, and those came from Canon's boot-time switch scan rather than deliberate presses. Given the cadence limit in §1, this is the one to defer: it is the weakest evidence in the set and the least urgent.
- **Q4 (per-core interrupts) — DO NOT SUBMIT AS A PR. Offer as a bug report first.**

### Why Q4 should be a report, not a patch

This is the case where the maintainer's stated preference and the evidence agree completely.

**What it is:** a 534-line change to `hw/eos/eos.c`, `eos.h` and `dbi/logging.c` — core code every model in `model_list.c` compiles against and that 20 dual-core models execute (5 DIGIC 7, 8 DIGIC 8, 3 DIGIC X, plus the 6D2).

**What it proves:** one sharp, real result. Core 1 received **6,520 IRQs in 60 s where it previously received zero** — the DryOS timer `1Bh` armed on bank 1 at `0xD5011010`, silently discarded by qemu-eos because `eos_handle_intengine()` had no case label for any core-1 address. That is a genuine defect with a genuine measurement.

**What it does not prove:** anything about the other 20 models. `roms/` contains one model. `.planning/prs/qemu-eos-submission-plan.md` §3.6 states this plainly — *"This could not be done, and no partial substitute was attempted."* The submission plan's own risk review then enumerates six ways it can regress, including one that is specific and sharp: `eos.c:1825` deliberately starts DIGIC X's cpu1 halted *"to avoid bad race around MMU table access"*, and the new `0xD233A010` case label makes `irq_enabled[1][]` settable, so `eos_deliver_int()` can now un-halt it — reintroducing exactly the race the halt was added to prevent.

**Apply the maintainer's rule to that.** *"If you want to continue with this approach, it would be much easier for me, if you instead report potential bugs, with reasoning, rather than speculative fixes without testing."* Q4 is a large, untested-across-models fix to shared code. It is the single clearest instance in this project of the thing he asked us not to send. The core finding — *qemu-eos drops every interrupt armed on core 1, on every dual-core model, because the handler has no case label for the core-1 bank* — is the useful part, it is three sentences long, and it is fully supported by ROM decode (`0xE0835820` bank table, dispatcher at `0xE026ABD4`, `INTID & 1` at `0xE026ABF4`) plus one measurement. **Send that. Offer the patch as "I have a working implementation if you want it," and let him ask.**

Two pre-flight fixes the submission plan already identified and which should be applied whether or not the patch is ever sent: add the missing `static int warned` guard to the `ITARGETSR` warning (§3.3 item 6), and either drop the DIGIC X case labels or guard `eos_deliver_int()` against halted CPUs (§3.4).

**And say this plainly regardless of route:** `qemu-eos-v4.2.1` has not moved since 2025-02-03. Expected time-to-merge for anything in that repo is unbounded. Submitting there is a cheap public artifact, not a delivery mechanism.

---

## §6 — Judged against INTENT Layer 4

### §4.1 — how much of this proceeds without Chris?

**Labour: roughly 85% unattended-able.** Everything drafts, splits, derives and rewrites without him: the retraction wording, the #297 reply, the TG-clock derivation (done — it is in §3), the `powersave.c` root-cause analysis (done — §2), splitting the un-shadow fix out of #297, trimming Q2's body, the qemu-eos fork's branch layout, checking for further upstream collisions.

**Delivery: 0% unattended-able.** Every artifact leaves through Chris's GitHub account or Chris's Discord identity. Nothing in this direction is queueable-to-completion.

**And the reward is on a third party's clock.** The last merged PR was nine months ago; #223 has sat unanswered since 2025-08-31. Even a perfect submission may produce nothing observable for months.

**That inverts §4.1.** Layer 4 says the objective function is *decoupling progress from Chris's availability*, and that a change letting an iteration happen at 3 a.m. beats a change making iterations 3× faster. This direction produces a lot of 3 a.m. work whose output cannot be *delivered* at 3 a.m. and whose *value* arrives on someone else's schedule. Measured against §4.1 alone, it ranks last of the five directions.

**The counter-argument, which is decisive for part of it.** Some of this is *debt*, not investment. The retraction is owed. The #297 comment is an unanswered direct question from the one person whose goodwill this project depends on, and it has been open since 12:07 today. Debt gets paid on its own schedule regardless of ROI. So this direction splits cleanly:

- **Debt (do it, now, small):** retract; answer #297; correct the four published superlative claims; put the #298 objection on the PR thread so the public record is honest. Total: one Discord message, two GitHub comments, three file edits. Hours, not sessions.
- **Investment (optional, low near-term return):** the qemu-eos submissions. Defensible on its merits — the MPU import method is genuinely wanted, and a public artifact has value beyond a merge — but it should not displace a direction that creates queued work.

### §4.2 — the gate, given that Chris cannot audit the social register

§4.2 is explicit: Chris delegated this layer *because* he does not know the terminology, so he cannot catch a wrong call in it, and *"any automation of outward-facing communication needs a human-meaningful gate."* A gate of the form "Chris approves the wording" fails on its own premise. The gate has to consist of things he can genuinely judge.

**Four rules, all auditable by someone with no domain knowledge:**

1. **Superlative ban, mechanically enforced.** No outward-facing text ships containing `first`, `ever`, `never`, `always`, `all`, `every`, `proves`, `confirms`, or `only` as a claim about the world. This is a `grep`, not a judgement call, and it is precisely the failure mode that has already cost the project once. Any hit must be rewritten descriptively before send.
2. **Commitment disclosure, one line, at the top of every draft.** Every outward-facing artifact is handed to Chris with a single line naming what it promises — *"this promises: one body test session"*, or *"this promises: nothing"*. He approves the **promise**, not the prose. He can judge whether he is willing to spend a body session; he cannot judge whether the register is right. This is the rule that would have caught the #223 draft, which quietly commits him to running someone else's test (`.planning/prs/DRAFT-comment-on-upstream-PR-223.md` says so itself: *"an assistant should not promise someone else's time on a public thread"*).
3. **Cadence cap, countable.** At most one outward-facing artifact per 72 hours to this maintainer while the trust deficit stands, and bug reports must outnumber patches 2:1. Volume is the harm here, and volume is the one dimension Chris can audit perfectly.
4. **Chris sends, always.** No agent posts to GitHub or Discord under his identity. Not because the text would be worse, but because §4.2's exposure is unbounded on the upside of harm and bounded on the upside of speed.

The existing harness classifier that blocked the #223 comment was doing rule 2's job by accident. Making it a rule turns a lucky block into a designed one.

### §4.3 — does this terminate in a visible camera capability?

**No.** This direction ships nothing to the camera. Layer 4 §4.3 warns that a direction producing no visible capability cannot demonstrate the method. That is a real mark against the investment half, and it is another reason to keep the qemu-eos push small and sequence a feature direction alongside it.

---

## Cost

| Item | Effort | Gated on |
|---|---|---|
| Retraction (Discord + 3 file edits + correcting commit) | ~1 hour drafting, 5 min to send | Chris's Discord |
| #297 reply (answers already derived in §3) | ~30 min | Chris's GitHub |
| Split the un-shadow fix out of #297 into its own PR | ~1 hour | Chris's GitHub |
| Put the #298 objection on the PR thread + close or convert | ~30 min | Chris's GitHub |
| PROP_LV_ACTION root-cause bug report (§2 a/b/c) | ~2–3 hours; (b) needs one body test to confirm | Chris's GitHub + one body session |
| Comment on `qemu-eos` #18 confirming the `outils.py` fix | ~15 min | fork not needed; Chris's GitHub |
| Fork `qemu-eos`, build branches, trim Q2, submit | ~2–3 hours | **Chris must create the fork** |
| Q4 as a bug report instead of a PR | ~1 hour (extract 3 sentences from an existing 19KB draft) | Chris's GitHub |
| Q3 | defer | — |

**Money: zero.** No hardware, no purchases. This is the only direction in the folder with no capital cost.

**The real cost is not ours.** Every artifact spends a fraction of the review attention of a one-person team that has merged nothing in nine months. That is the budget this direction actually draws on, and it is not replenishable.

---

## What would make me abandon this direction

Concrete, checkable triggers — not vibes:

1. **He asks for a pause.** Any message of the form "please stop opening PRs" or "let me get through the queue". Stop immediately, close the open PRs, and do not reopen. There is no version of this project that is worth being the person who burned out the last maintainer.
2. **No response to any of the five PRs plus the retraction within 30 days.** Silence after a good-faith correction means the channel is closed, and continuing to push into it is pure cost. Fall back to publishing findings in this project's own public repo and stop submitting.
3. **A second overclaim ships.** If the superlative ban fails once more after the retraction, the credibility cost exceeds anything the contributions can return. Stop all outward communication and fix the gate first.
4. **Q2 is rejected on the grounds that the spell data is not wanted.** That is the strongest card; if it does not play, the rest of the qemu-eos set is weaker and the investment half should be dropped entirely (the debt half still gets paid).
5. **`qemu-eos` PR #18 lands and supersedes the MPU work**, or another contributor ships a DIGIC 7 spell set first. Then Q2's value collapses to the 6D2 data alone, which is small.
6. **A body-test session is needed to validate a fix and Chris declines it.** Without hardware validation this project is exactly the thing the maintainer objected to, and submitting anyway is worse than not submitting.

**What would NOT make me abandon it:** slow merges. Nine months of no merges is the repo's normal state, not a signal about us.

---

## Open decisions to resolve before planning

1. **Does Chris want upstream contribution for its own sake, or only as evidence the method works?** INTENT Layer 3 flags this as never stated, and the two motives diverge sharply here: if it is evidence, a public artifact in his own repo serves nearly as well and costs the maintainer nothing.
2. **Split or supersede on #295/#298?** Reworking both into one root-cause change is technically right and adds patch volume at the worst possible moment.
3. **Fork `qemu-eos` at all?** Given the branch has not moved in 18 months, the alternative is to publish the four patches in this project's own public repo and link them from a comment on #18. Lower ceiling, near-zero maintainer cost.
4. **Q3 now or never?** It is the weakest evidence in the set. There is a defensible case for simply not submitting it.

---

## Key references

- Live PR state: `gh pr list --repo reticulatedpines/magiclantern_simplified --author ServerDestroyer --state all`; maintainer comment at https://github.com/reticulatedpines/magiclantern_simplified/pull/297#issuecomment-5307351175
- Maintainer's words: [../docs/discord/2026-08-16-ml-discord-thread.md](../docs/discord/2026-08-16-ml-discord-thread.md) — 12:35 AM, 12:43 AM, 12:50 AM, 8:31 AM, 8:41 AM, 8:45 AM, 8:55 AM.
- Root cause of #298: `ml/src/property.c:303-315` (`is_prop_allowed`), `:391-401` (silent drop), `:413-419` (#295's guard); `ml/platform/6D2.111/property_whitelist.h` (4 allowed writes); `ml/src/powersave.c:38-57` (`lv_paused` set after a denied write); `ml/src/propvalues.h:41`.
- Root cause of #297: `ml/src/fps-engio.c:286-303` (200D) and `:305-320` (6D2), both from upstream commit `ffef459f0d`; `.planning/spikes/006-rawvideo-memory/UPSTREAM.md` and `RECORD_PATH.md`.
- qemu-eos submission analysis, including the untestable-cross-model admission: [../.planning/prs/](../.planning/prs/) → `qemu-eos-submission-plan.md` §3.6, §5, §6.
- Upstream collisions: `qemu-eos` PRs #18 (jed2nd) and #19 (ssubbotin); ML PRs #293 (MPU dev-guide section), #262 (750D `ptp_register_handler` stub — the same mechanism direction 1's B2 depends on, open and unreviewed since 2026-05-01).
- Published overclaims: [../.planning/](../.planning/) → `ROADMAP.md` line 68; commit `5c009d7`; [../patches/README.md](../patches/README.md) §0007.
- Blocked draft that promises Chris's time: [../.planning/prs/](../.planning/prs/) → `DRAFT-comment-on-upstream-PR-223.md`.

---

## What this direction does not establish

- **Whether he will accept any of it.** Zero PRs have merged in 2026; the last was 2025-11-12. Nothing here changes that base rate, and no submission quality is known to.
- **Whether `PROP_LV_ACTION` is safe to whitelist on D678.** Requires ROM decode plus a live test on more than one body. One body exists here.
- **Whether the /2, /3, /6 clock-divider reading is right.** It fits both cameras' recorded numbers to 0.6% and reproduces the 6D2's observed 178,993 bit-exactly, but the divider register has not been located and the 200D absolute-base discrepancy is unexplained.
- **Whether Q4 regresses any of the 20 other dual-core models.** Untestable here; six specific regression paths are enumerated and none is retired.
- **Whether the retraction repairs anything.** It is the right thing to do independent of whether it works. It may simply be noted and moved past.
- **Whether the `outils.py` convergence with PR #18 was independent.** Same env var name, same default string, two months apart. Convergence is plausible — the default string is in the code and the name is obvious — but it has not been checked, and Q1 must not be filed either way.
