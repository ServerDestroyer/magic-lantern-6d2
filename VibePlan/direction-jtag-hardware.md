# Direction 2 — JTAG / hardware debug on DIGIC 7

**Status:** recorded (not decided, not planned)
**Recorded:** 2026-08-16 (Opus 5 session)
**Judged against:** [INTENT.md](INTENT.md), all four layers.
**Primary sources read in full:** [../.planning/spikes/010-jtag-digic7/README.md](../.planning/spikes/010-jtag-digic7/README.md), [../.planning/spikes/011-hardware-in-the-loop/README.md](../.planning/spikes/011-hardware-in-the-loop/README.md), [../.planning/spikes/014-uart-crash-console/README.md](../.planning/spikes/014-uart-crash-console/README.md), [../docs/jtag-research.html](../docs/jtag-research.html). New measurements taken this session are marked **[measured 2026-08-16]**.

---

## One-sentence goal

Find where — if anywhere — a hardware debug port comes out on a DIGIC 7 Canon board, publish the pinout, and get an OpenOCD/GDB session onto the 6D2's dual Cortex-A9.

## Why this is not the same as "port kitor's method"

The single most important honest fact in this file, and the one every summary of this direction so far has soft-pedalled:

> **JTAG has never been demonstrated talking on any EOS body, ever.**

kitor's confirmed success is on a **PowerShot SX740 HS** — a compact with **no MPU**. coon located the pads on an EOS R and an EOS RP donor board but, as of the last post Wayback captured (2025-09-02), had **not** completed solder-and-talk on either. The EOS attempt record is: nikfreak acquired six bodies in 2016 explicitly to do this and never reported a result; g3gg0 looked at a 5D3 and a 600D and found a connector on only one of them; coon is mid-attempt. That is roughly **zero successes across every serious EOS attempt on record** ([../docs/jtag-research.html](../docs/jtag-research.html) §02).

So this direction is not "apply a solved recipe to a new generation." It is **attempting the thing nobody has completed on this product line**, with a good recipe for the *adjacent* line. That is simultaneously why it is the novel contribution available and why the failure probability is high.

---

## Part 1 — What kitor established, and precisely what transfers

Source: ML forum topic **27350** "JTAG on Digic 8" (Reverse Engineering board, last captured post by coon 2025-09-02), retrieved via Wayback because magiclantern.fm is Cloudflare-challenged to every non-browser client. Summarised in the project memory note `jtag-on-digic` and folded into [../docs/jtag-research.html](../docs/jtag-research.html) §02.

| What kitor has | Confirmed how | Transfers to DIGIC 7? |
|---|---|---|
| Dual-core GDB session, PowerShot SX740 (DIGIC 8) | Verbatim in-thread; live register dump (pc=`0xE006E600`, sp_irq=`0xDF000100`) matches qemu-eos's D8 ROM map | **Method yes, result no** — the SX740 has no MPU; an EOS body does |
| IDCODE `0x4ba00477` | Read off silicon | **Yes.** This is the generic ARM CoreSight JTAG-DP code (mfg `0x23b` = ARM Ltd), not a Canon part number. It is what you hunt for on any ARM SoC. |
| OpenOCD dual-Cortex-A9 SMP config | Published verbatim (`jtag newtap … -expected-id 0x4ba00477`, two `cortex_a` targets coreid 0/1, `target smp`) | **Yes, structurally.** qemu-eos models D7 and D8 identically — `cortex-a9-eos-arm-cpu` ×2. `-dbgbase` is an unresolved TODO even in kitor's own config, and DIGIC 7's value is unknown. |
| Pin-ID by resistance-to-ground signature: TDI/TCK/TMS/TDO ≈ 100–200 kΩ (~128 kΩ on R, ~160 kΩ on SX740), /TRST ≈ 10 kΩ pulldown; while running, /TRST and TDO low, TDI/TCK/TMS high | Measured across three boards | **Yes — this is the actual transferable asset.** It replaces brute-force permutation scanning with a multimeter and ten minutes. |
| Tooling: 1.8 V-capable Altera USB Blaster, OpenOCD, gdb-multiarch, microscope | Stated | **Yes.** DIGIC 6–8 logic is 1.8 V; DIGIC 7 is the same. Never carry the DIGIC 4 3.3 V datapoint forward. |
| Pinouts for SX740, EOS R, EOS RP, with PCB photos at kitor.pl/eos/jtag/ | Published | **No — the DIGIC 7 pinout does not exist.** Producing it is the contribution. |

**The open question Phase 0 can answer for free, which spike 010 does not name:** on the EOS R/RP, are kitor's JTAG pads *on the FZC-8 service connector*, or on separate pads elsewhere on the board? This matters enormously. coon's published `magic-lantern-dev-kit` netlist shows the EOS service port carrying **two UARTs and no JTAG** (`RXDICU_1V8`/`TXDICU_1V8` at J5 12/13; `RXDMPU`/`TXDMPU` at J5 16/17) — the board's JTAG-capable FTDI pins route to a *separate* header, not to the camera ([../docs/jtag-research.html](../docs/jtag-research.html) §06). If kitor's EOS pads are elsewhere, then the 6D2's 8-pin FZC-8 is probably **not** where to look, and the whole "eight pins, tight for JTAG, likely SWD" pin-economics argument in §02 of the research doc is aimed at the wrong connector. Reading the photos settles it at zero cost.

---

## Part 2 — Phase 0: software-only, startable today, zero hardware

Everything here is desk work an agent can do unattended. Spike 010 lists four items; this section states what each actually yields, and flags one that will probably fail.

### 0.1 — Full retrieval of kitor's thread (topic 27350) and coon's R/RP posts (topic 7531, posts 38–43)

**Yields:** exact resistance values per pad, the complete OpenOCD config text, whether the EOS pads are on the FZC-8 or elsewhere, and any DIGIC 7 remarks. Also settles whether coon ever got the RP talking after 2025-09-02.

**Constraint [measured 2026-08-16]:** the ML forum mirror at `~/ml-mirror/` cannot serve this yet. It is still in the CDX enumeration phase — `progress.log` shows *cdx page 260/309, unique urls: 37325* — meaning it has downloaded **zero** forum pages so far. Phase 0 must use direct Wayback fetches of the flat print view (`action=printpage;topic=N.0`), which is the method that produced the memory note in the first place. Wayback rate-limits hard and returns intermittent 504s (visible in the same log); budget for retries, not for speed.

**Known ceiling:** Archive.org's crawler was blocked around 2026-03-09, so anything posted after that date is unreadable by any route currently available. If DIGIC 7 was solved in the last five months, Phase 0 will not find out. Only asking someone will.

### 0.2 — Static ROM0 search for the MPU-watchdog / ERR80 fault path

Spike 010 calls this "the one genuinely new problem versus kitor's PowerShot case." I ran the first pass this session.

**[measured 2026-08-16]** String inventory of `roms/6D2/ROM0.BIN` (32 MiB) and `ROM1.BIN` (16 MiB):

| Token | ROM0 hits | ROM1 hits |
|---|---|---|
| `ERR80` / `Err80` | 0 | 0 |
| `Watchdog` | 2 | 0 |
| `WDT` | 1 | 0 |

The three real hits, at ROM0 file offsets: `GIC_WatchdogTimer` at `0xd4dd78` and `0xf9d2a8`; `RSTGEN_WDTINT` at `0xf9c834`. (`Wdth:%x` at `0xfb50c` and `<WDt` at `0xad67ab` are unrelated noise.) A follow-up sweep for MPU-supervision language (`alive`, `heartbeat`, `supervis`, `timeout` co-occurring with `MPU`) returned nothing relevant.

**Honest verdict: Phase 0 almost certainly cannot solve ERR80, and the reason is structural.** The ERR80 decision is made *by the MPU*, which is a physically separate chip running its own firmware. That firmware is **not in ROM0 or ROM1** — those are the ICU's. Static analysis of what we have can find the ICU's own watchdog (which is what `GIC_WatchdogTimer` and `RSTGEN_WDTINT` are, and they are the true DIGIC 5 analogue of `0xC0410000`) and the ICU's half of the MPU protocol. Neither disables the MPU's supervision of the ICU. **Writing a register from the ICU cannot stop the MPU from noticing that the ICU stopped, because by then the ICU is halted.**

What the ROM0 hits *are* worth: if the ICU's own watchdog also fires on a halt, you have two faults to suppress rather than one, and this is the half you can actually suppress from software before halting. Worth chasing to a register address. Do not sell it as the ERR80 answer.

### 0.3 — What Phase 0 can substitute for the ERR80 answer

Ranked by cost, all desk-startable:

1. **Hunt the MPU spell corpus for a supervision-disabling message.** We have something nobody else in this thread has: ~175 real captured MPU spells from this exact body (`mpu_spells/6D2.h`, from a 522 KB `DEBUGMSG.LOG` with 71 `mpu_send` / 104 `mpu_recv` — `tools/6D2-DEBUGMSG-body.txt`), plus a working capture rig. If the MPU can be told to stand down — a service/factory mode, a shutdown-pending message, anything that suspends supervision — the message is in that protocol and we have the only DIGIC 7 sample of it. This is the single most promising Phase 0 item, it is pure software, and **spike 010 does not list it.**
2. **Note that the ERR80 window has never been measured on a 6D2.** a1ex's wording is "shortly afterwards" — not a number. If the window is 2 s, a scripted register dump fits inside it comfortably and halt-based debugging is degraded, not dead. Nobody knows. This is cheap to measure once a session exists and expensive to assume either way.
3. **Accept the scoping fact that ERR80 does not block the novel part.** Reading an IDCODE is a TAP-level transaction; it does not require halting a core. **Phase 1 steps 1–7 — the pin hunt, which is the actual contribution — are unaffected by ERR80.** ERR80 bites only when you want a *sustained halt-and-inspect session*, i.e. the last rung. This substantially de-risks the direction's headline deliverable and is worth stating plainly, because both the spike and the research doc imply ERR80 gates the whole thing.

### 0.4 — The two Phase 0 items that are Chris's, not an agent's

Sourcing a donor body and ordering tooling are listed inside spike 010's Phase 0, but they are not software and they are not startable by an agent. They are the wall this direction hits. See Part 4.

**Phase 0 total: 2–4 agent sessions, $0, no hardware, fully unattended.** Then it stops dead.

---

## Part 3 — The ERR80 watchdog, stated precisely

The mechanism, because the summaries compress it into something misleading:

- The halt is a **hardware** feature of the ICU's CoreSight/EmbeddedICE logic. JTAG never touches the MPU — separate chip, separate bus.
- Once the ICU is halted, USB and button non-responsiveness are a **firmware** side effect: nothing disabled the peripherals, the code that services them simply stopped running.
- On an EOS body the MPU runs its own supervision, notices its partner stopped answering, and faults the camera with **ERR80 within seconds**. g3gg0/a1ex, ML forum 2018-04-23: *"That's different from EOS — there, it locks up and the MPU throws ERR80 shortly afterwards… There's no MPU on PowerShots."*
- The DIGIC 5 fix does **not** map. That was an *ICU-side* watchdog on a PowerShot, suppressed by writing zero to `0xC0410000` via CHDK. Different chip, different failure, different generation. **No DIGIC 7 or DIGIC 8 MPU-side address is published.** ([../docs/jtag-research.html](../docs/jtag-research.html) §04.)

The four candidate answers, none proven:

| # | Approach | Cost | Assessment |
|---|---|---|---|
| 1 | Send an MPU message before halting that suspends supervision | Desk (Phase 0.3.1) | Best odds of a clean answer; we uniquely hold the DIGIC 7 protocol sample. Speculative — no such message is known to exist. |
| 2 | Live inside the window | Free | Unmeasured. Could be sufficient, could be 200 ms. |
| 3 | Hold the MPU in reset / cut the supervision line on the donor board | Bench, destructive | Only possible on a board you have already opened and do not care about. Likely breaks other things the camera needs to boot. |
| 4 | Do not halt at all — pin discovery only | Free | **This is the fallback that preserves the deliverable.** A published DIGIC 7 pinout + IDCODE is the contribution the maintainer asked for, and it does not need a halt. |

**Answer to the question the task poses — can Phase 0 solve ERR80? Probably not, and if it does, it will be via route 1 (the MPU spell corpus), not via the ROM0 search that spike 010 proposes.** The ROM0 search should still run; it is cheap and it will find the ICU-side watchdog register. It is just not the thing it is being sold as.

---

## Part 4 — Phase 1: the bench, and who supplies what

Spike 010's ordered procedure and [../docs/jtag-research.html](../docs/jtag-research.html) §07 agree on the sequence. Restated with the costs attached:

1. Obtain a **donor body — never the working camera.** Opening a body voids the warranty absolutely, with no authorised route back.
2. Find and photograph the **FZC-8** footprint (conventionally near the USB port; the 6D2's is undocumented — the 2025 teardown shows a screws-only rear cover, one LCD-harness hazard, no visible debug hole).
3. **Passive scope survey at idle.** Called "the highest-value hour in the whole plan" — it establishes the logic level, killing the largest safety risk, and shows which pin bursts at boot (TX).
4. Classify each pin through a **330 Ω series resistor**: input / pulled-up / pulled-down / actively driven. Pulled-low pins are nTRST candidates. Or, faster, use kitor's resistance-to-ground signature instead.
5. **Bring up UART first.** Proves the solder job and the voltage assumptions independently of any debug port, and hands over a DryOS shell either way. This is also spike 014's deliverable, so the two directions share this step.
6. **Scan for SWD before JTAG.** 8 pads = 56 ordered pairs for SWD vs 1,680 permutations for 4-wire JTAG.
7. **Repeat every scan with each pulled-low candidate forced high.** This is the step both prior Canon successes hinged on. Target: `0x4ba00477`.

**Decision point** (theirs, and it should be honoured): IDCODE found → OpenOCD bringup + the ERR80 fight. Nothing across all pads in both nTRST states → **stop**. The next tier (X-ray, BGA tracing) costs an order of magnitude more for much lower odds.

### What it costs, honestly

The repo contradicts itself here and it should be resolved before anyone spends money. [../docs/jtag-research.html](../docs/jtag-research.html) §07 says *"roughly $30 if you already own a scope, plus a donor body"*; §09 says *"the tooling is mature and costs about $200"*; spike 010 says *"~$200 total per the research doc's verdict."* Both are right for different baskets:

| Item | Cost | Note |
|---|---|---|
| 1.8 V-capable USB Blaster clone | $10–30 | Must be 1.8 V. A 3.3 V-only clone on a 1.8 V pad is how you kill the SoC. |
| USB-serial (UART, read-only) | $2–5 | Plain 3.3 V FTDI reads a 1.8 V TX out of the box — confirmed on the EOS M's identical line. Driving RX needs a 2×470 Ω divider. |
| Resistors, wire, flux | ~$10 | |
| coon's OSH Park FZC-8 flex breakout | ~$6 for 3 | FZC-8 is 0.5 mm pitch with **no off-the-shelf mating cable** — this or needle probes or a trimmed 8-way FFC stub. |
| Oscilloscope | $0 or $150–400 | **Unknown whether Chris owns one.** Nothing in this repo records his bench equipment. Step 3 is the highest-value hour and needs it. |
| JTAGulator | ~$200 retail | Optional — JTAGenum on a spare MCU does the same for ~$5 and more fiddling. |
| Multimeter | $0 or $20 | Needed for kitor's resistance-signature method. Same unknown. |
| **Donor body** | **$60–$400** | See below. |

**Realistic total: $80 at the low end if Chris already has a scope and buys a cheap sibling body; ~$600 at the high end.** The "~$200" figure in the spike is a middle estimate that assumes facts about Chris's bench nobody has checked.

### The donor body — and a cheaper option nobody has recorded

Spike 010 says "line up a donor body… ML developers have offered dead bodies for exactly this before." True, but it assumes a 6D2. Per the ML wiki's `uart_connectors` table ([../docs/jtag-research.html](../docs/jtag-research.html) §02), the DIGIC 7 generation is **6D2, 77D, 200D, 800D — all FZC-8**. A dead 200D or 800D is a fraction of the price of a dead 6D2 and answers the generation-level question ("does DIGIC 7 expose a debug port, and what is the resistance signature") just as well.

**What a sibling board does buy:** the existence answer, the IDCODE, the OpenOCD config validated on DIGIC 7 silicon, the ERR80 window measurement — all of it generation-level, all of it publishable, all of it what the maintainer asked for.

**What it does not buy:** the 6D2's specific pad locations. Boards differ; kitor published *per-body* pinouts for a reason. But per-body pad-finding on a known-good signature is a far smaller job than the open-ended hunt.

**Requirement either way: the body must power on.** Step 3 measures pins with the camera running. A "mechanically broken" donor with a smashed mount is ideal; a water-damaged non-booting one is nearly useless.

### Who supplies it

Only Chris. Sourcing, purchasing, opening, probing and soldering are all his hands, and 0.5 mm-pitch work under magnification is a skill this project has no evidence he has. That is not a criticism — it is the cost line that dominates every other cost line in this file.

---

## Part 5 — The collaboration alternative, which is probably cheaper than all of it

**kitor asked for donor boards.** He has the working method, the microscope, the probe, the tracing experience, and three boards' worth of pattern recognition. Chris has money and access to a body.

The moves, cheapest first (this overlaps [direction-community-and-corpus.md](direction-community-and-corpus.md) Part A deliberately — it is the same move seen from the hardware side):

1. **Post in topic 27350 stating the DIGIC 7 gap and asking whether anyone has probed a 6D2/77D/200D/800D.** One message. Both of spike 011's red-teams endorsed this independently. Also settles the Phase 0.1 ceiling (anything posted after 2026-03-09 that Wayback cannot see).
2. **Ask kitor directly whether a DIGIC 7 board would be useful to him.** If yes, Chris buys a $80 dead 200D, ships it, and gets a pinout produced by the one person on Earth who has done this — for the price of a body and postage, with no soldering, no scope, no risk, and no 3-month learning curve.
3. **Only if both fail, buy the donor and do it solo.**

**Cost of asking: one message. Cost of not asking: the entire Phase 1 budget and Chris's bench time.** This is currently nobody's task in any plan in [PLANS-IN-FLIGHT.md](PLANS-IN-FLIGHT.md).

Two honest caveats. First, this depends on a stranger's goodwill immediately after a first contact that landed badly (a bot request that read as data extraction, followed by an LLM-formatted post that overclaimed — [INTENT.md](INTENT.md) Layer 3 §4). Arriving with "here is the DIGIC 7 gap, can I fund it" is the opposite posture and is honest, but it may still get no reply. Second, if kitor does it, **the contribution is his, not this project's** — which matters only if the goal is credit, and per Layer 3 the goal is the method, not the credit. If anything, "we identified the gap, funded the board, and it got solved" is a *better* story for an agent-driven-RE writeup than "we spent $600 and three months learning to solder."

---

## Part 6 — The strategic case for

1. **It is the community's named bottleneck, stated by the maintainer, unprompted.** *"Really for us I think the hard part is getting the physical hardware in the loop… We have strong suspicions that most cams have jtag, but we have only a few examples of people working with jtag on these cams. If we could find a way to consistently connect to jtag, that would likely help a lot."* ([INTENT.md](INTENT.md) Layer 3.) Nothing else in this folder is a direct answer to something a maintainer asked for.
2. **It is the one contribution that cannot be dismissed as LLM output.** Layer 3 also establishes the binding constraint: untested LLM patches are a net cost to reviewers, LLMs are not accepted for PR review, and overclaiming already damaged trust. A measured pinout and an IDCODE screenshot are *physical evidence*. They are immune to every objection the maintainers have raised about this project's output so far. **This is the strongest argument for this direction and it is not a technical one.**
3. **It is genuinely novel.** No DIGIC 7 pinout exists. No EOS body has ever been confirmed talking over JTAG. The research doc's own verdict: *"That is not a research problem. It is a pad-hunting problem on undocumented hardware, and a few hours of scope work on a donor body would answer it."*
4. **It is the only route to three things nothing else reaches**: CPU halt and single-step of a live core; state during a total wedge where no firmware channel runs; and hard-brick recovery when card-boot itself is gone.

## Part 7 — The case against, including a correction to the repo's own argument

1. **It blocks nothing.** This is the repo's own finding, from two independent red-teams in spike 011 and from [../docs/jtag-research.html](../docs/jtag-research.html) §05. Every shipped 6D2 feature — MOV limit, 14-bit raw video, dual-ISO stills, re-arm, measured-fps header — landed with no debug port. The one real emulation blocker that ever existed was closed by non-JTAG means (real body-captured MPU spells + a per-core interrupt fix). ROM dumping is done. Only ~5 open items are genuinely hardware-bound, and the USB PTP path (spike 012) or peek-to-SD (spike 011 #1) reach most of them without a probe.

2. **One of the three "only JTAG can fix this" bullets is overstated, [measured 2026-08-16].** [../docs/jtag-research.html](../docs/jtag-research.html) §05 claims *"Six of the eight fields in the 6D2's qemu-eos model entry are either marked `fixme` or silently copied from the 200D — including two interrupt IDs carrying the comment 'taken from 200D. Probably valid but Has to be validated.'"* I checked `hw/eos/model_list.c` directly. The 6D2 entry (lines 617–625) has **seven** fields, exactly **one** `fixme` (`current_task_addr = 0x28`), and **no** "taken from 200D" comment — that comment appears on other models' entries (lines 703/704, 715/716, 727/728, …), which is precisely what spike 011's framing red-team said. Three 6D2 fields (`card_led_address = 0xD208016C`, `uart_rx_interrupt = 0x15D`, `uart_tx_interrupt = 0x16D`) are byte-identical to the 200D's, so "inherited rather than measured" is fair for 3 of 7. But **"six of eight" is wrong and should not be used to justify spending money.** The emulator-self-validation argument for JTAG is real but roughly half the size it is being quoted at.

3. **The prior probability is not good, and pretending otherwise is the exact failure mode Layer 3 warns about.** Estimate, labelled as judgement not measurement: **P(a live IDCODE is found on an accessible DIGIC 7 pad set) ≈ 25–40%.** Basis: debug was demonstrably not fused on DIGIC 5 and is open on DIGIC 8, so the silicon almost certainly supports it — but the record on *EOS bodies specifically* is 0 successes across every attempt anyone has published, the 6D2's connector has 8 pins where the successful DIGIC 4 find had 16, and the published EOS service-port netlist carries UART only. The failure mode is not "the port is fused"; it is "the pads are not on that connector and finding them needs X-ray."

4. **It fails the availability test that Layer 4 identifies as the real objective function.** See below.

5. **It duplicates 80% of its practical value with a direction that costs nothing.** [DIRECTION.md](DIRECTION.md) §5 already worked this out: arbitrary reads, arbitrary writes, function calls, boot log, crash tail, and emulator ground truth are all reachable through the ladder (peek-to-SD → USB PTP → UART → feedback loop) at a fraction of the cost. JTAG's unique residue is halt/single-step, wedge inspection, and un-bricking.

---

## Part 8 — Judged explicitly against INTENT.md Layer 4

### §4.1 — Does it create queued unattended work?

Chris asked three times in one session, unprompted: *"Do you have enough to work on a bunch of parts without me for some time?"* / *"is there anything left that you can do without me?"* / *"is there more you can do, without me."* Layer 4 concludes the objective function is **decoupling progress from his availability**, and that a change letting an iteration happen at 3 a.m. is worth far more than one making iterations 3× faster.

**Verdict: this direction scores worst of the five on §4.1, and it is not close.**

- Phase 0 creates **2–4 sessions** of genuinely unattended agent work (Wayback retrieval, ROM0 watchdog hunt, MPU-spell supervision search, OpenOCD config prep, kitor-photo analysis). Real, but bounded and short.
- After Phase 0 the direction **hard-stops on a purchase decision** and cannot resume without it.
- Phase 1 is the inverse of unattended: it is 100% Chris at a bench for 4–12 hours across several sittings, with a skill acquisition curve, plus weeks of shipping latency. An agent's contribution during Phase 1 is limited to writing instructions — and Layer 4 §4.4 records that instructions to Chris are themselves an artifact that has already gone wrong twice and burned two whole camera sessions.
- Worse: this direction **converts queued work into human-gated work**, which is exactly the inversion Layer 4 §4.6 flags. The 2026-08-16 scope decision paused a track that produced, in one night, dual-ISO on the body, cr2hdr merging end-to-end, stock firmware reaching full startup in QEMU, ML exonerated, and five PRs — in order to start a track that cannot begin until a body is bought.

**The one framing under which it passes §4.1:** Phase 0 plus the kitor ask (Part 5) is entirely unattended and costs $0. If this direction is scoped to *that* and nothing more, it is compatible with §4.1. Scoped to include Phase 1, it is the direct opposite of what Chris keeps asking for.

### §4.3 — Does it terminate in a visible camera capability?

Layer 4 §4.3: *"a direction that produces no visible camera capability cannot demonstrate the method, however technically sound it is."* Chris asked *"are we still working to make the video look and work correctly?"*, *"can we do HDR video?"*, *"is Dual-ISO raw going to be hard from here?"* — genuine feature curiosity with a sense of cost.

**Verdict: no. This direction terminates in a pinout, an IDCODE, and possibly a GDB prompt.** No photograph, no clip, no menu item. The chain to a camera capability is: pinout → halt session → measured register values → corrected qemu-eos model fields → a feature previously untestable at the desk. That is four hops, each conditional, and the third hop was just shown to be smaller than advertised (Part 7 item 2).

It is worth naming the aggravating detail: **the donor body is by construction a camera that will never take a picture again.** Judged on Layer 4 §4.3 alone, this is the weakest direction in the folder.

The honest counterweight: §4.3 exists because a visible capability is what makes the method *legible*. To the ML maintainers specifically — the audience whose opinion Layer 3 makes binding — a DIGIC 7 pinout is more legible than another feature. It is the thing they said they wanted. So this direction fails §4.3 as written while partially serving the reason §4.3 exists. That is a real tension, and it should be decided deliberately rather than by which document was read last.

---

## Part 9 — Cost summary

| Phase | Who | Wall-clock | Money | Unattended? |
|---|---|---|---|---|
| Phase 0 (research, ROM search, spell hunt, config prep) | Agent | 2–4 sessions | $0 | **Yes, fully** |
| The kitor / forum ask | Chris sends, agent drafts | 10 min + reply latency (days to never) | $0 | Draft yes, send no |
| Tooling procurement | Chris | 1–3 weeks shipping | $30–$400 (bench unknown) | No |
| Donor body sourcing | Chris | days to weeks | $60–$400 | No |
| Phase 1 bench (steps 1–7) | Chris | 4–12 h over several sittings | — | No |
| Phase 2 (OpenOCD bringup + ERR80) | Both | unbounded — 1 evening or never | — | Partly |

---

## Part 10 — What would make me abandon this direction

Written before starting, so it cannot be rationalised away later.

1. **kitor or coon replies offering to do it.** Stop the solo hardware path the same day; ship a board instead. This is a *success*, not a failure, and it is the cheapest outcome on the table.
2. **Chris declines to buy a donor body.** Then the direction is Phase 0 + the ask, full stop — which is a subset of [direction-community-and-corpus.md](direction-community-and-corpus.md), and this file should be closed rather than kept alive as an aspiration.
3. **Phase 0.1 reveals someone already published a DIGIC 7 pinout after 2026-03-09.** Fold immediately, cite them, redirect to using it.
4. **The bench survey finds nothing across all 8 pads in both nTRST states.** Stop at the research doc's own decision point. Do not escalate to X-ray or BGA tracing — an order of magnitude more cost for much lower odds.
5. **The FZC-8 turns out to carry UART only** (as coon's published dev-kit netlist shows for the EOS service port), meaning any debug port is on unexposed pads elsewhere. Same stop.
6. **A live IDCODE is found but halt requests are ignored** (`DBGEN` tied low / fused). Publish the finding — it is genuinely valuable and closes the question for the whole generation — and stop. No probe defeats authentication tie-off.
7. **The measured ERR80 window is under ~1 s and no MPU-mode workaround exists.** Halt-based debugging is unusable on an EOS body. Publish the pinout and the window measurement; abandon the GDB session goal.
8. **Two consecutive Chris-gated steps slip by more than two weeks each.** That is §4.1 telling you the direction is wrong for this project regardless of its technical merit.

## Part 11 — What only Chris can do

Sourcing and purchasing a donor body; buying tooling; opening a camera; every measurement, probe and solder joint; posting to the forum or messaging kitor under his own account. **Every step of Phase 1 without exception.**

## Part 12 — Sequencing options

- **Phase 0 only, then stop and decide (recommended if this direction is taken at all).** 2–4 unattended sessions, $0, no hardware. Ends with: the full kitor thread, whether EOS JTAG is on the FZC-8, the ICU watchdog register, a verdict on the MPU-supervision message, and a drafted forum post. Every subsequent decision is better informed and nothing is spent.
- **Phase 0 in parallel with the ask.** Same cost; the ask's reply latency runs concurrently instead of after. Strictly better, and it is what Part 5 argues for.
- **Fund kitor instead of tooling up.** Buy a dead 200D, ship it, skip Phase 1 entirely. Cheapest route to the deliverable; costs the credit and depends on a reply.
- **Full solo Phase 0 → Phase 1.** The version implied by the 2026-08-16 scope decision. Highest cost, highest human gating, worst §4.1 score, and the only version that guarantees the pinout is ours.

## Part 13 — Open decisions

1. **Will Chris buy a donor body at all?** Layer 3 lists this under "what Chris has NOT said." Everything past Phase 0 depends on it and nobody has asked.
2. **6D2 donor or a cheaper DIGIC 7 sibling (200D/800D/77D)?** The sibling answers the generation question for a fraction of the price; only the 6D2 gives the 6D2's own pad map.
3. **Does Chris own a scope and a multimeter?** Unrecorded anywhere in this repo, and it swings the tooling cost by an order of magnitude.
4. **Ask before buying?** Part 5 says yes, unambiguously. It is currently nobody's task.
5. **If it succeeds, who publishes it and where** — forum thread, ML wiki `uart_connectors` table, or a PR to kitor's page.

## Key references

- Plan of record: [../.planning/spikes/010-jtag-digic7/README.md](../.planning/spikes/010-jtag-digic7/README.md) — Phase 0 checklist, Phase 1 ordered bench procedure, safety rules.
- The honest red-team: [../docs/jtag-research.html](../docs/jtag-research.html) — §02 the entire evidence base, §03 the three traps that fake a dead port, §04 the EOS MPU blocker, §05 what it would buy the emulator (see Part 7 item 2 for a correction), §07 the bench procedure, §09 the verdict.
- Non-JTAG alternatives and the "we do not need this" reframe: [../.planning/spikes/011-hardware-in-the-loop/README.md](../.planning/spikes/011-hardware-in-the-loop/README.md).
- Shared bench step 5: [../.planning/spikes/014-uart-crash-console/README.md](../.planning/spikes/014-uart-crash-console/README.md) — `uart_printf` already stubbed at `platform/6D2.111/stubs.S:284` (`0xe04eb7a0`); family pinout pins 2/3 = ICU RX/TX 1.8 V, 4 = GND, 6/7 = MPU TX/RX 3.3 V, never measured on a 6D2.
- kitor's findings as captured: project memory note `jtag-on-digic` (ML forum topic 27350; EOS R/RP authoritative pinout = topic 7531 posts 38–43, noting the wiki-linked msg212071 has a known-wrong MPU-RX label).
- The ladder this direction sits at the top of: [DIRECTION.md](DIRECTION.md) §4–§5.
- The collaboration half: [direction-community-and-corpus.md](direction-community-and-corpus.md) Part A.
- Emulator model fields checked this session: `hw/eos/model_list.c` lines 617–625 (6D2 entry) in the qemu-eos clone at `/home/chris/ml6d2/qemu-eos`.
- MPU protocol sample: `mpu_spells/6D2.h` (~175 spells), `tools/6D2-DEBUGMSG-body.txt` (522 KB, 6530 msgs, 71 `mpu_send` / 104 `mpu_recv`).
