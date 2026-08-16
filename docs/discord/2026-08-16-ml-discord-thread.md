# ML Discord thread — 2026-08-15/16

Local, private record of Chris's own thread in the Magic Lantern Discord. Not for
redistribution or publishing — bulk copying of other people's messages is the exact
thing `names_are_hard` objected to in this very thread.

Participants: Server Destroyer (Chris), kitor, names_are_hard (maintainer,
reticulatedpines), iaburn, Jok3r, thebilalfakhouri, DefinitivVair0.

## Outcomes

1. **Logging bot / Discord scraping: refused on GDPR grounds.** names_are_hard (a
   former GDPR DPO) said copying the conversations is probably illegal without
   informed consent, subject-access, and deletion mechanisms. No admin approval given.
   Treat the bot as dead unless Chris does the GDPR work.
2. **Disclosed the LLM-heavy workflow** ("It is llm slop! I didn't even review the
   code or the explanation"). Reception: mixed but not hostile — fixes judged ~90% OK,
   descriptions ~50% untrue or overly verbose.
3. **Maintainer's requested contribution mode:** report potential bugs with reasoning,
   NOT speculative untested fixes. Untested LLM PRs shift the cost onto the few devs
   who have the hardware.
4. **Claim to retract:** "First-ever raw video recorded on a 6D2" — names_are_hard says
   no, pointed at #off-topic-general. Also flagged that overclaiming makes the "all
   tested on a real body" claim doubtful too.
5. **PR #298 (PROP_LV_ACTION) — maintainer prefers a different fix:** fix PROP_LV_ACTION
   itself rather than a new-cam-only workaround.
6. Code sharing requested by three people (names_are_hard via DM, thebilalfakhouri and
   Jok3r want to test on M50 / 200D). Chris said he'd use his own repo until it's cleaned.
7. **JTAG is the lever names_are_hard actually wants.** Most cams probably have it;
   very few worked examples; unknown Canon implementation and unknown physical contacts.
   A working JTAG path = hardware debugger in the loop, useful to humans and LLMs.
8. Jok3r: 200D low-bit-depth fix corrected the **EDMAC row size** to the packed pitch,
   NOT by reducing RAW width. thebilalfakhouri: 5D2 doesn't crop RAW either.
9. MLV library: names_are_hard floated sharing one library between ML and MLVApp —
   https://github.com/ilia3101/LibMLV, and his own experiment `modules/raw_video/raw_vidx`
   ("MLV 3") in magiclantern_simplified @ 3f24042a4.

## Transcript

**Server Destroyer — Yesterday 11:18 AM**
Hey! I'm working on the 6D2 port and would like to keep a local, offline index of the dev channels so I can search past discussion while developing.

Would it be OK to invite a read-only logging bot? A few details so you can judge it:

Permissions: View Channels + Read Message History only (permission integer 66560). No Send Messages, no Manage anything — the invite literally can't grant more than that.
Code: ~80 lines, no send calls anywhere, happy to paste the whole thing here or link it.
What it does: reads messages, writes them to local markdown files on my machine. Never posts, reacts, or DMs anyone.
Invite link (you can inspect the requested permissions before accepting): https://discord.com/oauth2/authorize?client_id=1538248909204226158&permissions=66560&integration_type=0&scope=bot

Totally understand if the answer's no — just figured I'd ask since it'd save me a lot of scrolling through old threads.

**Server Destroyer — Yesterday 11:32 AM**
Also should I post what I have done (or are doing) on 6d2 channel?

**kitor — Yesterday 12:44 PM**
That's a lot of words just to say you want to fed all of our data to LLMs.
Three days after joining, zero messages and straight to asking us to allow your bot scrape the server.

**kitor — Yesterday 12:54 PM**
I'll let @names_are_hard to decide but this is a pretty unusual introduction to this community.

**Server Destroyer — Yesterday 12:56 PM**
Sorry, for being wordy. I have no idea what your community is like. I just want to get more of the 6d2 working.

**iaburn — Yesterday 1:42 PM**
Not trying to give an opinion on this particular issue, but I always thought that you guys gave a lot of useful information on this channel and it's super hard to find anything into tons of chats and messages... which is a pitty

**Server Destroyer — Yesterday 2:38 PM**
6D2 1.1.1 — MOV/MP4 29:59 time limit override working

Found the two recording-limit constants in the 6D2 ROM and enabled FEATURE_OVERRIDE_MOVIE_30_MIN_LIMIT:

    #define MVR_TIME_LIMIT_NORMAL_FPS 0xe042ff74
    #define MVR_TIME_LIMIT_HIGH_FPS   0xe042ff78

Tested on the body: set the limit to 1 min, recording stopped on its own at ~60 s. apply_patches() accepted both without an old-value mismatch, so the constants match this firmware.

Three-line diff against platform/6D2.111/. Happy to open a PR.
Next up RAW video

**Server Destroyer — Yesterday 4:41 PM**
6D2 progress (fw 1.1.1, magiclantern_simplified dev @ 3f24042a4)
Working on my body as of today:
MOV/MP4 time-limit override — found and verified the two ROM constants (0xe042ff74/0xe042ff78, each unique in ROM0). Set 1 min, recording stops itself at ~60 s. Three-line platform diff.
Raw video recorded — mlv_lite produced a clean 90.7 MB MLV: 25 frames, 1920x1080 14-bit, valid block chain, debayers fine in MLV App.
Found + fixed a D678-wide stall — prop_request_change_wait() waits its full 2 s timeout on writes the whitelist silently drops; PROP_ICU_UILOCK isn't whitelisted on any D7 body, and mlv_lite calls gui_uilock() around every realloc, so it presents as a freeze. One-guard fix, no new property writes.

Known issues being worked: shoot_malloc pool shrinks 135→43 MB between alloc cycles, "Early stop (8)" + "No memory suites." after stopping, MLVI sourceFps reads garbage, and WBAL gains are bogus (R485/G1024/B610) so footage needs manual WB in post.

Credit where due: raw video was already "mostly working" in the tree thanks to stephen-e — this is finishing work on that foundation. Happy to PR the MOV limit and the prop-wait fix; also have a root-cause writeup for why 6D2 QEMU stalls (no D7 MPU spells → EstimatedSize assert) if useful.

**Server Destroyer — Yesterday 8:30 PM**
📷 Magic Lantern on the 6D Mark II — status update
All of this is tested on a real body, not just emulation.

🎬 Raw video is real — First-ever raw video recorded on a 6D2 — 14-bit 1920×1080 MLV, pixel-valid frames, properly finalized files.

🔧 Camera-side fixes
✅ MOV/MP4 time limit override — 30-min limit lifted, verified auto-stop (PR #294)
✅ DIGIC 7/8 prop-wait livelock fix — denied property writes froze raw buffer allocation for 2-4s per cycle (PR #295)
✅ Startup-logger anti-brick fix + gcc15 build fixes (PR #296)
✅ MLV fps header fix — headers carried garbage (178.9 fps!) because the 6D2 timer base was never measured; now stamped from measured frame timing → exact 25.000 / 29.970 / 59.94 on real files
✅ mlv_lite shadowing bug — inner int fps left the outer stuck at 1 (affects every body)
✅ Dead-state freeze fix — after a buffer-full auto-stop, pressing REC again hard-froze the camera (battery pull). Buffers now re-arm automatically
✅ Self-recording diagnostics — instrumented builds log to a card file with timestamps

🖥️ QEMU side — the 6D2 can now be emulated
✅ First DIGIC 7 MPU spell set in qemu-eos — ~175 property exchanges captured from the real body (photo + movie mode). Stock 6D2 firmware now boots instead of dying at the RscMgr/EstimatedSize assert
✅ That assert root-caused — a frame-rate switch fed garbage because QEMU had no 6D2 property data. Not the SD card, as long suspected
✅ Dual-core GIC interrupt fix — the emulated interrupt controller assumed one CPU; the 6D2's second core permanently wedged all interrupt delivery. Fixed
✅ ML boots in emulation — with real spells our autoexec gets further than stock firmware. The old "ML hangs in QEMU" was the emulator's bug, not ML's

🔭 Scoped next
🔜 Lossless compression — encoder hardware confirmed present in the 6D2 ROM; would make 1080p24/25 raw continuous instead of ~1s bursts
🔜 Dual-ISO — stills mode may already work (ships hidden!); movie mode needs one register table, candidates already located in ROM

Attaching a frame from a real 25p raw take, developed straight from the MLV.
NOT BAD FOR MY FIRST DAY AT THIS

**names_are_hard — 12:29 AM**
Are you a legal entity and will you comply with GDPR rules?

**names_are_hard — 12:35 AM**
These sound useful, the bold headings LLM speak is kind of annoying and I would prefer talking like a human 🙂
Maybe 50% of the "explanations" for fixes are untrue or overly verbose, or both. The fixes are probably 90% okay, LLM likes to invent reasoning

**names_are_hard — 12:43 AM**
The spells stuff is interesting - Alex repeatedly refused to explain some of the problems I saw with 200D emulation, even after I'd dumped MPU logs. I ended up improving the emulation in many places, but never knew how to import recorded MPU traffic. Might be able to use the existing scripts now I know where they are

**names_are_hard — 12:50 AM**
E.g. "First-ever raw video recorded on a 6D2" - no. #off-topic-general
Still always appreciate people improving things, but please don't trust LLM to write good descriptions
(and then because I know that's not true, I have to question whether "All of this is tested on a real body" is true. LLMs lie a lot)
Some of the bug fixes are definitely nice, the shadowed fps var is hard to spot

**Jok3r — 1:07 AM**
The 5D2 fix may be related in the sense that it adjusts RAW EDMAC geometry for lower bit depths, but on the 200D we did not solve it by reducing the requested RAW resolution. We kept the frame geometry and corrected the EDMAC row size to match the actual 10/12-bit packed pitch. The smaller row size comes from lower bit depth, not from intentionally cropping/reducing the RAW width.

**names_are_hard — 1:13 AM**
Possibly. I didn't know about that change on 5D2, hence why I went for the more obvious fix on 200D

**names_are_hard — 1:14 AM**
Is the code for your changes available somewhere?

**names_are_hard — 2:16 AM**
(he DM'd me and will send a link later)
@ilia3101 - would you be interested in updating / creating MLV library code? At least in ML code, it's quite ugly at present. The real code is spread over a few files. There is https://github.com/ilia3101/LibMLV but I don't know if you still use this?
It would seem sensible to use the same library, shared by mlvapp and Magic Lantern, so both projects are always in sync
I made a simple library for an earlier experiment: https://github.com/reticulatedpines/magiclantern_simplified/tree/3f24042a4dfbfba1c4cbfafede50e92a770ed3a9/modules/raw_video/raw_vidx (the "MLV 3" stuff)
That's not ready for general use, it was an experiment so I could test if it was possible to avoid exposing MLV format information to application code (the answer is yes, not very hard to do)

**thebilalfakhouri — 8:28 AM**
AFAIK 5D2 code doesn't crop/reduce RAW resolution..
Could you share the code? I would like to test it on M50
Could you PM me the code?

**Server Destroyer — 8:29 AM**
It is llm slop! I didn't even review the code or the explanation next to the code.
My only goal was to see if I could spin up enough LLMs to see if I could make as much as possible work with little to no work on my part. I'm pretty convinced that most of the hard work has been done for many of the cameras and letting an LLM attempt to Brute Force its way to working code may in fact work.
My goal is to get it wired up to working even if it's poor. Then set up a review process to see if any of those fixes were correct and put it on loops for getting out the rest of the bugs and optimizing the code and the reasons why the code worked in the first place.

**names_are_hard — 8:31 AM**
It should be pretty easy to cleanup and push, I may look at it today, but got a few things in the queue
It's good to get some explanation of degree of LLM-ness. One problem with this approach is it creates a lot of work for PR review
You spend less time, PR reviewer has to spend quite a lot more time
This is painful in open source projects especially, where there are often very few devs

**Jok3r — 8:33 AM**
Ohh got it, I thought the 5D2 reduce the RAW Resolution 😃

**thebilalfakhouri — 8:35 AM**
You are probably applying the same method to fix the same issue on 200D, I can't tell without checking the code 😄

**Server Destroyer — 8:40 AM**
That was my concern too, I will use my own repo and until it has run some loops to clean itself up I won't push anything… However, if there was some way of flagging that this is an LM and it hasn't really been cleaned up it would be nice to get other people involved with having them use llms too. I just don't know a good way of pulling that off for a project like this.
I noticed there was not enough devs that's why I thought an llm might be able to offset it…
I was hoping to build out a process for the llm to make the building process follow a certain specified track. That way it can be just pointed at one camera and it sort of knows what to do… It's looking like that's not the case as there are too many specifics for each camera. However, there may be a way to set up volunteers to help debug the LLM slop as you have so many people that want to help but don't know how to code. It's possible I could make it so the outputs could go over what to check for the volunteers so that way the LLM slop could be cleaned up properly without coding knowledge… I'm just trying to come up with a way to get the project to go forward with the technology that we now have and the large community for this project but the unfortunate lack of Developers.

**names_are_hard — 8:41 AM**
I don't think LLMs are good enough to do PR review. Maybe in the future
The better compromise for now is for a human, if they are using an LLM, to try to understand what the LLM wants to do, in order to understand what the better thing to do is

**Jok3r — 8:44 AM**
I PMed you @thebilalfakhouri 🙂

**names_are_hard — 8:45 AM**
E.g. your PR here: https://github.com/reticulatedpines/magiclantern_simplified/pull/298/changes/6ef3813c062504283486eefb1381ac8d6f6500f6
Probably, the better thing to do is fix PROP_LV_ACTION, rather than write a complicated workaround for new cams to stop it being used only for those cams
But I have to read 4 over-confident paragraphs about the change, in order to work out what might be the correct action, then write code for that, then test it on a range of cams
The core finding, that lack of handling for PROP_LV_ACTION causes a problem on new cams, might be very useful! But first we have to test that (which LLMs can't do as it needs multiple physical cams)
If you want to continue with this approach, it would be much easier for me, if you instead report potential bugs, with reasoning, rather than speculative fixes without testing

**Server Destroyer — 8:54 AM**
Understood, what I'm wanting to do is make it better environment for the llm to grind at the problem with as little as the human in the loop as possible. Eating your time and anyone else's is not a desired outcome.
I actually have a lot of questions about how to build a better environment for an llm to go to town until it produces something good.

**names_are_hard — 8:55 AM**
Wait about 5 years until they stop being over-confident, verbose, and with no sense of what is true or what is a lie? 😉
(really for us I think the hard part is getting the physical hardware in the loop)
We have strong suspicions that most cams have jtag, but we have only a few examples of people working with jtag on these cams
If we could find a way to consistently connect to jtag, that would likely help a lot

**Server Destroyer — 9:06 AM**
Well that leads into my very first question here. I was wanting to grab all the conversations and as much as possible with what everyone is done. I am planning on building a custom GraphRAG to look through everything so that the llm has a better idea of what to do when it comes to emulation.
People have volunteered so much time on this project already and there's already answers to a lot of the possible directions. Using some type of advanced rag that I was planning on custom building for this there should be a way of sorting through what are the best directions to try. That's why I wanted to scrape the Discord along with all the other work everybody is done over the years… perhaps a more cohesive picture can be built out specifically for the llm to try a barrage of possibilities. (That's why I think the key is to have a excellent emulated environment). I think of llms as like an idiot savant given enough tries they can probably figure a lot of this Nitty Gritty stuff out, they just need the right environment and people need to know the things that they absolutely cannot do like an idiot savant can't do.

**names_are_hard — 9:06 AM**
It is very probably not legal for you to do that
Users here have not given consent for their data to be used in that way

**Server Destroyer — 9:09 AM**
To my knowledge they gave consent when they signed up for Discord but I can double check that. I think the rule is an admin has to allow a bot on the Discord but I am not allowed to scrape the Discord myself. That's why I'm asking you right now.

**names_are_hard — 9:09 AM**
They certainly did not give consent for you to copy their data
Have you ever worked as a GDPR Data Protection Officer?
They did give consent for Discord to handle their data, but you are not Discord

**Server Destroyer — 9:11 AM**
No of course not.
It gets more frustrating every time I look into the legality of this it's different in every country and it's different in every state. The law has not been ironed out yet. And I doubt large companies will want it ironed out anytime soon as there is too much to profit off of the law being Gray.

**names_are_hard — 9:11 AM**
The law for GDPR is very clear. It is old and well tested, in many countries
(I have worked as a GDPR DPO)

**Server Destroyer — 9:16 AM**
Well with that being the case is it not okay to use past conversations for RAG?

**names_are_hard — 9:17 AM**
It is probably not legal to copy the conversations without conforming to GDPR
Conforming to GDPR is pretty easy, and well documented. One of the things you need to do is get informed consent for data usage (with a few exceptions for necessary functionality, national security etc, which you would not be covered by)
You would also need to provide a mechanism for any individual to request a copy of data pertaining to them that you have (subject access request), as well as a way to remove all data you hold about them (subject deletion request). There are other things too

**iaburn — 9:24 AM**
Just mention that GDPR is about personal data, I think it does not apply to code comments on a forum

**names_are_hard — 9:24 AM**
Have you checked every comment to make sure it doesn't contain personal data, e.g. name, location?

**Server Destroyer — 9:24 AM**
Hmm, the EU definitely has their own interesting contributions to AI… This is a total tangent from working on the camera but what is the EU going to do about countries that have their own laws. Especially for platforms that what the user agrees to sign is different in each country?
Regardless I'd rather get back on track on how to make the camera work. It sounds like what you're telling me is scraping Discord is too sticky in the EU?
That doesn't sound hard to do. However I'm not training anything on their data more like deleting unnecessary information such as names overlapping information then finding consistencies in what was actually stated. All excess fluff would be removed as it just eats tokens and degrades quality.

**names_are_hard — 9:25 AM**
Bulk collection of personal data is a legal risk in all countries. US companies abide by the GDPR too
Re "countries that have their own laws" - this is all EU law

**Server Destroyer — 9:28 AM**
I can ask my casework for clarification this

**names_are_hard — 9:28 AM**
EU global "laws" are implemented by individual EU countries making their own local laws. There is only a tiny amount of genuinely "EU" law
If you are an EU member country you commit to translating EU laws into your own legal framework

**Server Destroyer — 9:30 AM**
I will look into this

**DefinitivVair0 [S3RL] — 9:32 AM**
Yea. Basically two types. One type is law and stands over the countries laws and the other type must be implemented into the countries laws

**names_are_hard — 9:32 AM**
No, not really

**Server Destroyer — 9:32 AM**
Thanks for your time. I have seen you post so much for years and you have put in so much work, thank you so much.
I will get back when I have looked into jtag alot more

**names_are_hard — 9:33 AM**
jtag is pretty cool, it can act as an interactive hw debugger. This could help a connected LLM (and us real humans!). But we don't know how Canon implemented it, or on which cameras, and we don't know how to identify the physical contacts

**DefinitivVair0 [S3RL] — 9:35 AM**
Really? There are EU regulations which instantly apply to all member states and override conflicting local law and there are EU directives which set a goal for member states, that they have to work towards. At least its how I remember it from my last lecture

**names_are_hard — 9:36 AM**
I could easily be wrong in this area, I'm not a legal professional. Isn't it mostly treaty based? If so, that's a local law (we will abide by treaty X), but you can always leave the treaty
