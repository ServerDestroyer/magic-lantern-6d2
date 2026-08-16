# Discord logging + local RAG index — legal decision-support memo

**Date:** 2026-08-16
**Prepared for:** Chris (US-based natural person, no legal entity)
**Question:** can a read-only Discord logging bot + local GraphRAG index over the Magic Lantern dev channels be operated lawfully, and what would a compliant design look like?

> **This is decision-support, not legal advice, and I am not your attorney.** Nothing here
> is a green light. The one design decision below that actually needs a lawyer is flagged
> in "Escalate to counsel." Citation verification status is stated per source at the end —
> some are read from mirrors/summaries, not originals.

---

## Layer 1 — Plain-language bottom line

1. **GDPR is not the main obstacle. Discord's own developer contract is.** Two Discord rules bite harder and apply regardless of where you live: you may not use API data to **profile users, their identities, or their relationships with other users** (Developer Policy rule 16), and you may not use message content to **train ML/AI models including LLMs** without Discord's express permission (rule 21). A "GraphRAG over who said what" is close to the first. Retrieval at query time is probably not "training", but the wording is broad and it is Discord's call, not yours.

2. **Whether GDPR applies to you at all is a live question with a real answer — and the answer depends on your design, not your intentions.** You are a US natural person with no EU establishment, so Art 3(1) is out. That leaves Art 3(2), which needs either offering goods/services in the EU (you don't) or **monitoring behaviour** of people in the EU. A bot that continuously records identified individuals and builds a person-keyed graph looks like monitoring. A pipeline that extracts technical facts and discards identity does not. **Design your way out of scope; that is far cheaper than complying.**

3. **The "purely personal or household" exemption is arguable but not safe to lean on.** It is read narrowly, and one of the three tests is that the activity has no connection to anything professional — you're feeding an open-source project with contributors and PRs. Do not build a plan whose only defence is this exemption.

4. **Stripping usernames does NOT take you out of scope.** Pseudonymised data is still personal data (Recital 26). Verbatim messages remain attributable by content. Only discarding the message and keeping the *technical proposition* gets you meaningfully toward anonymous.

5. **The maintainer's ask is stricter than the law requires in one respect.** He said "informed consent". GDPR requires *a* lawful basis, of which consent is one of six; **legitimate interests (Art 6(1)(f))** is the normal basis for this kind of corpus. But — see point 7 — arguing that point is a losing move socially.

6. **If you are in scope, the compliance kit is genuinely small at your scale**, because the corpus is local, small, and keyed on a stable Discord user ID: a public notice, a privacy page, a documented balancing test, and a delete-by-user-ID script. That is a weekend, not a quarter.

7. **What you may NOT conclude from this memo:** that you can proceed because the law probably doesn't reach you. Two of the three gates here are not legal. kitor's objection was social, and the server admins can refuse for any reason at all. Being right about Art 3(2) does not get the bot invited.

---

## Layer 2 — Analysis

### A. Does the GDPR apply to Chris at all?

Two independent gates must both be passed before any obligation attaches: **material scope (Art 2)** and **territorial scope (Art 3)**.

#### A.1 Material scope and the household exemption — Art 2(2)(c)

Art 2(2)(c) disapplies the GDPR to processing "by a natural person in the course of a purely personal or household activity". Recital 18 adds that such activities have "no connection to a professional or commercial activity", and expressly names "social networking and online activity undertaken within the context of such activities".

The CJEU reads this **narrowly**. In *Jehovan todistajat* (C-25/17, ¶42): an activity is not purely personal or domestic "where its purpose is to make the data collected accessible to an unrestricted number of people or where that activity extends, even partially, to a public space and is accordingly directed outwards from the private setting of the person processing the data". *Ryneš* (C-212/13) held that a home CCTV camera capturing a public footpath falls outside the exemption, because the exceptions "must be construed narrowly" and the processing must be *purely* household, not merely personal. *Lindqvist* (C-101/01) put publication to an unlimited audience outside it.

Applied to the facts, the three commentary criteria split:

| Criterion | Reading | Cuts |
|---|---|---|
| **Space** of the processing | The source is a public, open-invite Discord server; commentary treats "generally available websites" as outside the exemption. The *storage* is private and local. | **Against** (source), for (storage) |
| **Social aspect** / number of recipients | Recipients = one. Nothing published, nothing redistributed. This is the strongest fact you have. | **Strongly for** |
| **Purpose** (Recital 18: no professional connection) | Unpaid hobby, but it feeds an open-source project with PRs, contributors, and an outward audience. "Non-commercial" ≠ "non-professional". | **Against** |

**Conclusion:** genuinely contested, and it collapses the moment any output is shared with another developer. Treat the household exemption as a supporting argument, never the plan.

#### A.2 Territorial scope — Art 3

Art 3(1) needs an establishment in the Union. You have none, so it does not apply. Art 3(2) applies to a non-EU controller processing data of people **in the Union** where the processing relates to:

- **(a) offering goods or services** to them — no. You offer nothing to anyone.
- **(b) monitoring of their behaviour** as far as it takes place in the Union.

Recital 24 defines the test for (b): whether "natural persons are tracked on the internet including potential subsequent use of personal data processing techniques which consist of profiling a natural person, particularly in order to take decisions concerning her or him or for analysing or predicting her or his personal preferences, behaviours and attitudes." The EDPB extends this beyond web tracking to other technologies. Commentary also notes the processing must relate to EU data subjects **intentionally**, not incidentally.

This is the hinge, and it is design-dependent:

- **Design A — log everything, keep verbatim messages with authorship, build a graph of who said what and who works on what.** This is continuous observation of identified individuals' online activity, structured by person, for the purpose of analysing what each of them knows and prefers. That is a serious Art 3(2)(b) case against you. The stated goal "so the LLM knows who to ask" is, in GDPR vocabulary, analysing personal preferences and attitudes.
- **Design B — ingest, extract technical propositions, discard identity and message text, index only the propositions.** No tracking of persons, no person-keyed structure, nothing that analyses or predicts anything about an individual. Art 3(2)(b) has little to bite on, and under Recital 26 much of the corpus stops being personal data at all.

**The single highest-leverage decision in this whole matter is A vs B.** It decides whether the law applies, not merely how much paperwork it generates.

#### A.3 Does pseudonymising or dropping usernames fix it? — No.

Recital 26, sentence 2: "Personal data which have undergone pseudonymisation, which could be attributed to a natural person by the use of additional information should be considered to be information on an identifiable natural person." Sentence 3 requires accounting for "all the means reasonably likely to be used, such as **singling out**".

A corpus of verbatim messages with names replaced by `user_07` is pseudonymous, not anonymous: the content itself singles people out (self-reference, writing style, cross-links to GitHub handles, "I maintain X"). Only where the retained artefact is a technical claim no longer *relating to* a person does Recital 26's anonymous-information carve-out realistically apply.

Practical line:
- ❌ "Keep the messages, strip the names" — still personal data.
- ✅ "Keep the finding, drop the message" — approaching anonymous.

### B. If in scope: the minimum compliant design

The maintainer listed consent, SAR, erasure, "and other things too". The accurate list:

1. **Lawful basis — Art 6(1)(f) legitimate interests**, not consent. Retroactive consent from years of past posters is unobtainable, and consent must be freely given and withdrawable. Legitimate interests requires a documented three-part balancing test (legitimate interest / necessity / not overridden by the data subjects' rights and reasonable expectations). Write it down; the documentation *is* the compliance. Consent remains available for *future* messages if the server prefers it and is the better social answer (§C).
2. **Art 14 notice — data not obtained from the data subject.** You must tell people. Art 14(5)(b) exempts you where notice is impossible or "would involve a disproportionate effort, in particular for … scientific or historical research purposes or statistical purposes" — but it is a **balancing test that must be documented**, and it still requires "appropriate measures … including making the information publicly available". At your scale, direct notice is not disproportionate anyway: **a pinned channel notice plus a public privacy page discharges this cheaply.** Do that instead of arguing the exemption.
3. **Art 15 access / Art 17 erasure / Art 21 objection.** With a local corpus keyed on Discord user ID this is a script, not a programme: export-by-user-ID, delete-by-user-ID, and a documented turnaround (GDPR's default is one month). Handle objections under Art 21 by deleting rather than litigating "compelling legitimate grounds".
4. **Art 5 principles.** Purpose limitation (dev channels only, named purpose), minimisation (drop attachments, DMs, off-topic channels), storage limitation (a stated retention period with automatic expiry), integrity and confidentiality (full-disk or corpus-level encryption — it is a laptop), accountability (a one-page record).
5. **Art 9 special categories.** A chat corpus incidentally contains health, political, and sexual-orientation content, which needs a *separate* Art 9 condition and mostly doesn't have one. Mitigation: dev/technical channels only, never off-topic or social channels. This is a real reason to keep the scope narrow.
6. **⚠ Art 27 EU representative — verify.** If Art 3(2) applies, a non-EU controller generally must designate a representative in the Union, subject to an exemption for occasional, low-risk processing. I did not read Art 27 in this session. **Confirm before relying on either the obligation or the exemption.** This is the obligation people most often miss, and it is the most awkward one for an individual.

### C. Discord's terms — the binding layer, GDPR or not

These flow from the developer agreement you accept by running a bot. They bind you contractually **even if GDPR does not reach you**, and Discord can act on them unilaterally.

| Source | Requirement | Effect on this project |
|---|---|---|
| Developer Policy **rule 16** | "Do not use API Data to: profile Discord users, their identities, or **their relationships with other users**" | **Directly targets the GraphRAG-over-people design.** A knowledge graph whose nodes are people and whose edges are who-discussed-what-with-whom is the described harm. A graph over *topics* is not. |
| Developer Policy **rule 21** | "Do not use message content obtained through the APIs to train machine learning or AI models (including large language models) unless express permission is granted by Discord." | Fine-tuning or embedding-training on the corpus: **prohibited without permission.** Retrieval at query time does not update weights and is defensibly not "training" — but this is Discord's interpretation to make. Do not fine-tune anything on this corpus. |
| Developer Policy **rule 15** | API Data only for what is "necessary to provide your stated functionality"; improvement use only if "aggregated or de-identified such that it cannot be associated with, or used to identify, any individual" | Your stated functionality must be declared and narrow, and the corpus must serve it. |
| Developer ToS §5 | Delete API Data promptly when no longer necessary, when you stop operating the app, when Discord asks, when **the user** asks, or when law requires; "give users an easily accessible way to ask for their API Data to be modified and deleted" | The SAR/erasure machinery is required by contract, not just by GDPR. |
| Developer ToS §5 | "comply with all applicable privacy laws … including the GDPR"; provide and adhere to a **public privacy policy** linked in the Developer Portal describing what you collect, how you use it, and how users request deletion | You owe a published privacy policy regardless of the Art 3(2) analysis. |

**Reframe worth putting to the maintainer:** almost everything he asked for, Discord already requires of every bot operator. Meeting his conditions is not an unusual accommodation; it is baseline compliance with the developer terms.

Not researched here: **copyright.** Forum and chat posts are copyrightable works owned by their authors; the EU DSM Directive's text-and-data-mining exceptions and US fair use are the relevant doctrines. Flagged, not analysed.

### D. Cheaper alternatives that dodge most of this

1. **Index the public Magic Lantern forum and the GitHub history instead.** Years of deep technical discussion, public web rather than Discord's developer contract, no rule 16/21 problem, and arguably the higher-signal corpus for emulation work. **This is the best value-per-unit-of-risk on the list.**
2. **Ask for forward-looking opt-in only.** Log from date X, only from members who opt in via a reaction or a role. Clean consent, no retroactive problem, and it converts a data grab into a community project.
3. **Chris's own conversations.** Copying threads he participated in is materially different from bulk collection of everyone's.
4. **Ask an admin to run the extraction.** They are already the controller of the server's content; a curated technical FAQ produced by an admin and shared is a different legal posture entirely. It also costs them work, so it is an ask, not a fix.

---

## Deliverable — compliant-design checklist to put in front of the server admins

Ordered so that each item is verifiable by a skeptical reader.

**Scope and data minimisation**
- [ ] Named technical channels only — never off-topic, social, or DM channels (limits incidental Art 9 special-category data).
- [ ] No attachments, no images, no voice, no member lists, no presence/activity data.
- [ ] Ingest is one-way and local: nothing leaves the machine, no cloud sync, no third-party upload.

**Identity handling — the decisive choice**
- [ ] Default to **extract-and-discard**: parse each message into technical propositions, retain the proposition, delete the message text and author identity after a short buffer window.
- [ ] Where provenance genuinely matters, retain a **stable pseudonymous key** plus a separate, encrypted mapping file — so deletion is one row, and the mapping can be destroyed wholesale.
- [ ] **No person-graph.** Graph nodes are topics, subsystems, cameras, and findings — never users or user-to-user relationships (Discord Developer Policy rule 16).

**Training and model use**
- [ ] No fine-tuning, no model training, no embedding-training on Discord message content (rule 21). Retrieval-at-query-time only, and say so explicitly in the privacy page.

**Transparency**
- [ ] A published privacy page: what is collected, why, lawful basis, retention period, how to get a copy, how to get it deleted, contact address. Linked in the Discord Developer Portal (required by Developer ToS §5).
- [ ] A pinned notice in each logged channel, in plain language, before logging starts.
- [ ] Documented Art 6(1)(f) balancing test, one page, dated.

**Rights machinery**
- [ ] `export --user <id>` and `delete --user <id>` implemented, tested, and demonstrated to the admins **before** any invite.
- [ ] Deletion propagates to the derived index, not just the raw log — demonstrate this, it is the part people fake.
- [ ] Stated response window (30 days), and an opt-out that works prospectively too.
- [ ] Global kill-switch: on admin request, delete the entire corpus and prove it.

**Retention and security**
- [ ] Stated retention period with automatic expiry.
- [ ] Corpus encrypted at rest.
- [ ] Deletion on: purpose exhausted, bot removed, Discord request, user request (Developer ToS §5).

**Governance**
- [ ] Admin-revocable: removing the bot stops everything and triggers deletion.
- [ ] Nothing derived from the corpus is published or redistributed without separate agreement.

---

## Escalate to counsel

- **Before deploying any identity-preserving design**, get an EU privacy practitioner to sign off on the Art 3(2)(b) analysis and the Art 27 representative question. That single opinion is the difference between "I read a memo" and "I took advice", and it is what makes the offer credible to a former DPO.
- Copyright in the messages is unanalysed here.
- Whether to seek Discord's express permission under rule 21 (and thereby put the project on their radar) is a judgment call, not a legal question.

---

## Citation verification status

Per the two-check standard, these are **not** filing-grade until re-verified in the originals:

| Source | How read | Status |
|---|---|---|
| GDPR Arts 2, 3, 4, 6, 14; Recitals 18, 26 | Verbatim text, gdpr-info.eu mirror | ⚠ EUR-Lex fetch returned empty — **confirm against EUR-Lex CELEX 32016R0679 before outward use** |
| *Ryneš* C-212/13; *Jehovan todistajat* C-25/17 ¶42; *Lindqvist* C-101/01 | GDPRhub summaries + commentary (secondary) | ⚠ curia.europa.eu is JS-rendered and did not fetch — **read the judgments before quoting** |
| Recital 24 (monitoring test) | Quoted inside GDPRhub Art 3 commentary | ⚠ secondary — confirm verbatim |
| EDPB Guidelines 3/2018 (territorial scope) | PDF fetched but not text-extracted; relied on via commentary and search summaries | ⚠ **read the PDF before citing it** |
| Discord Developer Policy rules 15, 16, 21 | Verbatim, official page via r.jina.ai proxy (discord.com blocks direct fetch, HTTP 403) | ✅ verbatim, ⚠ proxy — re-read on discord.com in a browser |
| Discord Developer ToS §5 (retention, deletion, privacy policy, privacy-law compliance) | Verbatim, same proxy | ✅ verbatim, ⚠ proxy |
| GDPR Art 27 (EU representative) | **Not read this session** | ❌ unverified — assertion flagged in text |
