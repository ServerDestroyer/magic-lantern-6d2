# PU1 / KerRLock.c:205 investigation

Round scope: the `ASSERT : SystemIF::KerRLock.c, Task = ShtCap, Line 205` wall that
appeared after the EstimatedSize fix. Six analysis lenses (static only), one live
QEMU/gdb agent (8 instrumented boots), two adversarial reviews.

---

## 1. Summary

- **The assert is SOLVED as a symptom, not as a root cause.** One 2-byte write —
  `set *(unsigned short*)0xE0091D04 = 0x4770` — removes it in every run. Boot does
  **not** complete: `startupInitializeComplete` appears 0 times in all 8 runs.
- Root cause of the assert: `EngInit` (0xE0060926) runs on **Core 1**, blocks inside
  `bl 0xE0091D04` (at 0xE0060942), and therefore never reaches `bl 0xE04AA690`
  = `ResMng_Init`, the sole creator of the `ENG_RES_MNG` recursive lock at
  RAM 0x10BFC. `ShtCap` then calls `TakeRecursiveLock` with a NULL handle and the
  kernel's NULL/bit0 guard at 0xDF00B47A–0xDF00B480 asserts line 205.
- **"WaitPU1 TimeOut" and the assert are the same bug, not two.** The stub removes
  both: `WaitPU1` count is 1 in runs 1/3/4/5 and **0** in runs 6/7/8. Core 1 = PU1,
  its init is `EngInit`, and while it is stuck PU1 never signals the `PU1Wait`
  semaphore. This contradicts the "PU1 is irrelevant" framing carried in the
  hypothesis set — see §2.4.
- Progress: DryOS serial message counter **398 → 557**; with `-d debugmsg` the boot
  now reaches `startupPrepareCapture`, `scsInit`, `startupPrepareDevelop`, `sdsInit`,
  `[APROC] AprocCtrl_Initialize`, then parks forever in a gyro-calibration poll.
- The stub is blunt (skips a whole engine-init subtree) and both skeptics refuted the
  claim that this is "closed". The honest status is: **assert cleared, wall moved.**

---

## 2. Observed vs inferred

### 2.1 OBSERVED — live runs (QEMU + gdb)

All artifacts under
/tmp/claude-1000/-home-chris-Vibe-Coding-6D-Mark-II-Magic-Lantern-6D2/97eb1d5b-2948-4584-a307-57ec6310a0cc/scratchpad/pu1/
(`run1.gdb`..`run7.gdb`, `run-1-…-gdb.log` .. `run-8-…-qemu.log`, `r8.txt`).

Counts I re-ran myself with `LC_ALL=C grep -ac` over the `*-qemu.log` files:

| run | patch under test | ASSERT | WaitPU1 | startupInitializeComplete |
|---|---|---|---|---|
| 1 baseline | EstimatedSize only | 5 | 1 | 0 |
| 2 | 0xE00420E8 → `movs r0,#0; nop` (skip PU1 wait) | 5 | 0 | 0 |
| 3 | observe ResMng | 5 | 1 | 0 |
| 4 | bisect 0xE0091D04 | 5 | 1 | 0 |
| 5 | stub 0xE0494208 only | 5 | 1 | 0 |
| 6 | **stub 0xE0091D04** | **0** | **0** | 0 |
| 7 | same, 480 s | **0** | **0** | 0 |
| 8 | same, `-d debugmsg` | **0** | **0** | 0 |

Verbatim gdb output that matters:

- run-1: `ASSERT_HIT core=2 r0=0xdf00b5cc r1=0xdf00b5b4 line=205 lr=0xdf00b4b3 sp=0x1ffeb8`,
  and `x/s $r1` → `"SystemIF::KerRLock.c"`. core=2 is gdb thread 1.2 = **CPU1**.
- run-3: `ENGINIT_ENTER core=2 lr=0xe004055b` printed, `RESMNG_INIT` **never** printed,
  then `RESMNG_USE_NULLLOCK core=2 lr=0xe00d3e1f` and
  `ASSERT_HIT … line=205 … lockhandle=0x0` (that is `*(uint*)0x10BFC`).
- run-4 (breakpoints at 0xE0091D04/D10/D14/D18/D1C/D20/D28/D36/D2E): only
  `pc=0xe0091d04` and `pc=0xe0091d10` were hit → `bl 0xE0494208` did not return.
- run-5 (`PATCH E0494208 = 0x4770`): `REACHED e0091d14 (past 0xE0494208)` and then the
  assert anyway. **0xE0091D2E was not reached.**
- run-6/7 (`PATCH E0091D04 = 0x4770`): `REACHED RESMNG_INIT core=2`,
  `REACHED enginit_end lock=0xb40002`, zero `ASSERT_HIT`.
- run-8 tail (`r8.txt`): line 1496 `startupPrepareCapture`, 1518 `scsInit`,
  1582 `startupPrepareDevelop`, 1652 `sdsInit`, 1736 `[APROC] AprocCtrl_Initialize`;
  first `WAIT AUTO GYRO OFFSET` at line 1650 and 2453 occurrences to EOF at 6664.

### 2.2 OBSERVED — but a skeptic mis-read it

One adversarial verdict claimed the EstimatedSize forcing "was not in force" during
runs 6–8 because no `ESTSIZE_HIT` lines appear. **That is wrong.** `run6.gdb` and
`run7.gdb` deliberately drop the printf from that breakpoint (`silent; set $r0 = 0x7D0;
c`) — only `run1.gdb`/`run2.gdb` print it. The trailing
`Cannot execute this command while the target is running` line is `timeout` killing
gdb at the end of the run, not an early detach. The runs are the intended
"EstimatedSize + EngInit stub" configuration.

### 2.3 INFERRED statically (never executed)

- Address of every function named below comes from `objdump` over
  [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/roms/6D2/ROM0.BIN](roms/6D2/ROM0.BIN),
  base 0xE0000000; the DryOS kernel blob maps ROM0 file 0x0100553C → 0xDF000000.
  The mapping was verified two ways (pointer table at file 0x010143B0 resolves to
  string starts; kernel literal at 0xDF00B3D8 = 0xDF00EE74).
- `EngInit` and `ResMng_Init` are **inferred names** — `grep EngInit ROM0.BIN` and
  `grep ResMng_Init ROM0.BIN` both return nothing. The only ROM strings are
  `ENG_RES_MNG` (0xE04AAA68) and `../.././Src/Engine/ENG/ResMng/ResMng.c` (0xE04AAA78).
- "0xE0091D04 blocks" is inferred from *absence* of a later breakpoint hit, not from a
  stopped PC or a deadlock dump. Strictly it means "did not return within ~2 s before
  the assert".
- Everything in §4 about which *other* calls inside 0xE0091D04 might also block is
  pure disassembly.

### 2.4 Contradictions between reports — stated, not smoothed

1. **"The assert has nothing to do with PU1"** (hypothesis 1) vs the run logs.
   Refuted by the logs themselves: the same one-instruction patch removes both the
   assert and `WaitPU1 TimeOut`. Correct statement: *both are symptoms of CPU1's
   engine init stalling.* Run-2 remains valid and important — skipping the PU1 wait
   does **not** clear the assert, so the wait is downstream, not causal.
2. **"Nothing on the PU0 side ever gives the PU1Wait semaphore"** (static lens) vs
   runs 6–8, where the wait succeeds. Either the static scan (which only looked for
   `[rX,#56]` against the 0x41F0 base) missed the give site, or the give happens on
   CPU1. Unresolved; the observation wins.
3. **"CPU1 gets no timer interrupt and cannot run a scheduler"**
   (hw/eos/eos.c:1004, eos.c:2443, `CURRENT_CPU` → cpus[0]) vs the assert firing on
   gdb thread 1.2 with `ENGINIT_ENTER core=2`. CPU1 demonstrably executes firmware.
   The qemu-eos GIC defects catalogued in that lens are real but are **not** the
   current wall.
4. **"the hang moved exactly one call forward to 0xE0494370"** (hypothesis 3) is
   false. Between the two probes 0xE0091D14 and 0xE0091D2E there are **five** BLs,
   not one — see §4.3. `0xE0494370` was never individually confirmed.
5. **200D `patches.gdb` as precedent** — it is a verbatim copy of the 80D file
   (its own header says `run_canon_fw.sh 80D`), commented out, and 200D's
   `debugmsg.gdb` never sources it. It is not evidence about 200D or about the
   technique.

---

## 3. Mechanism, with addresses

```
0xE004431C  b.w 0xE0060926                  (only entry into EngInit; no BL exists)
0xE0060926  EngInit: push {lr}; builds a 28-byte struct on the stack
0xE0060940    mov r0, sp
0xE0060942    bl 0xE0091D04   <-- BLOCKS under QEMU (runs 3/4)
0xE0060946    bl 0xE04AA690   <-- ResMng_Init, NEVER REACHED
0xE006094A    bl 0xE028FCF4
0xE006094E    bl 0xE0542734

0xE04AA690  ResMng_Init: adr r0,0xE04AAA68 ("ENG_RES_MNG")
0xE04AA694                blx 0xE043B1F8   (veneer -> 0xDF00B696 CreateRecursiveLock)
0xE04AA698                ldr r4,[0xE04AAA74] = 0x00010BF0
0xE04AA69A                str r0,[r4,#12]  -> lock handle at 0x10BFC
            (literal 0x00010BF0 occurs twice in ROM0, both in this module;
             0x00010BFC occurs zero times -> sole creator)

ShtCap -> veneer 0xE043B300 -> kernel 0xDF00B450 TakeRecursiveLock(r0=handle)
0xDF00B456   mov r4, r0
0xDF00B47A   cbz r4, 0xDF00B480        ; handle == 0
0xDF00B47C   lsls r0, r4, #31
0xDF00B47E   beq.n 0xDF00B484          ; only odd handles continue
0xDF00B480   movs r2, #205             ; <-- THE ASSERT (line 205)
0xDF00B4AA   adr r1, 0xDF00B5B4        ; "SystemIF::KerRLock.c"
0xDF00B4AE   blx 0xDF008C6C            ; veneer -> 0xE0617620 (real assert handler)
```

Line 205 is a **handle-validity check**, not a timeout. Timeouts in the same function
return 9 or 11 (0xDF00B498–0xDF00B4A2). Handles are manufactured as `id<<1` by the
create functions, so 0 and even values are always invalid.

The PU1 side of the same cause: `startupPrepareCapture` (entry **0xE00420CC**) does
`mov.w r1,#2000` / `ldr r0,[r4,#0x38]` / `blx 0xE043B4E8` (TakeSemaphore on the
`PU1Wait` semaphore created at 0xE0041452 with the name string at 0xE00417EC).
While CPU1 is stuck in `EngInit`, PU1 never signals → timeout → the ERROR print at
0xE00420F4. The branch at 0xE00420EE falls through either way, so the message is
non-fatal on its own (proved by run-2).

---

## 4. Candidate patches, ranked, with skeptic verdicts

### 4.1 `set *(unsigned short*)0xE0091D04 = 0x4770` — **USE THIS**
Skeptic verdict: **refuted** — but only the *claim*, not the patch. The refutation is
that "PROVEN AND CLOSED" is false (no `startupInitializeComplete`), that the stated
inner blocker is stale, and that it skips an entire init subtree. The empirical result
stands: assert gone in runs 6, 7, 8.

Notes:
- Use the **16-bit** write. The proposed `set *(int*)` variant writes `70 47 00 00`,
  additionally clobbering `mov r4,r0` at 0xE0091D06 — harmless but **never tested**.
- Only one caller exists (0xE0060942), confirmed by a full-ROM Thumb BL scan, so blast
  radius is one call site.
- `bx lr` leaves r0 = sp instead of the tail call's return value; harmless only because
  `ResMng_Init` overwrites r0 immediately at 0xE04AA692.

### 4.2 gdb redirect instead of a ROM write — **do not use as written**
`b *0xE0060942 / set $lr = 0xE006094A / set $pc = 0xE04AA690`.
Skeptic verdict: **refuted, correctly.** `set $lr = 0xE006094A` omits the Thumb bit;
`ResMng_Init` ends with `pop {r4,pc}` (0xE04AA6CE), an interworking branch, so the core
drops to ARM at 0xE0060948 and executes the word 0xF9D3F6A3 — undefined. Correct value
is **0xE006094B**. And the benefit is void: 0xE0091D04 has exactly one caller, so
"protects other callers" is vacuous.

### 4.3 Two-instruction stub `0xE0494208` + `0xE0494370` — **not justified yet**
Skeptic verdict: **refuted on a factual error.** The body of 0xE0091D04 is:

```
e0091d0c  blx 0xE043A434
e0091d10  bl  0xE0494208      <- blocker #1, CONFIRMED (run-4)
e0091d14  bl  0xE0494370      <- suspected only
e0091d18  bl  0xE0228AC0      <- never tested (routes into the same 0xE013Bxxx module)
e0091d1c  bl  0xE0309B5C      <- never tested (MMIO leaf, cannot stall)
e0091d24  bl  0xE01A2972      <- never tested
e0091d2a  bl  0xE0091D36      <- never tested (calls 0xE0494500 twice, 0xE049453A)
e0091d2e  ldmia.w sp!,{r4,lr}
e0091d32  b.w 0xE00D8F6C
```
run-5 kept probes only at D14 and D2E, so it localised the second blocker to a
five-call window, not to 0xE0494370. Running this patch as proposed repeats the same
blindness.

### 4.4 Skip the PU1 wait (`set *(int*)0xE00420E8 = 0xBF002000`) — **killed by experiment**
run-2 applied it, `WaitPU1 TimeOut` vanished, the assert fired anyway. Do not repeat.
Leave it unpatched so the log keeps reporting PU1 state truthfully.

### 4.5 Stub `startupPrepareCapture` 0xE00420CC / `startupPrepareDevelop` 0xE00421F8
(the literal 750D/80D transfer) — **killed by analysis.** 0xE00420CC is genuinely
`startupPrepareCapture` (three-way confirmed: `pop {r4,r5,r6,pc}` at 0xE00420CA,
`push {r4,lr}` at 0xE00420CC, startup-step table at 0xE0FA672C holds 0xE00420CD), but
stubbing it deletes SCS_Initialize (0xE0160768) → scsInit (0xE01E5F76) →
InitializeCapturePath (0xE00F1144), i.e. it destroys *more* lock creation. With the
0xE0091D04 stub the function now completes normally anyway (run-8 line 1496).

### 4.6 Tooling fix — assert breakpoint address is wrong upstream
[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/qemu-eos/magiclantern/cam_config/6D2/debugmsg.gdb](qemu-eos/magiclantern/cam_config/6D2/debugmsg.gdb)
has `b *0xE06170EC` + `assert_log`. 0xE06170EC is inside an AES T-table routine. The
real DryOS assert entry is **0xE0617620** (`push {r4,r5,r6,lr}` / format string
"\nAssert: File %s Line %d\n" at file offset 0x61765C), matching
platform/6D2.111/stubs.S:283 `debug_assert 0xe0617620`. The 0x534 delta is
1.0.3-vs-1.1.1 firmware skew; `mpu_recv_log` in the same file is off by the identical
0x534. No skeptic disputed this. Not applied — concurrent sessions own cam_config.

---

## 5. Recommended next action (cheapest decisive test first)

1. **One run, no new patches: finish the bisect.** Take `run5.gdb` (stub 0xE0494208
   only) and re-add run-4's probes at 0xE0091D18 / D1C / D20 / D28 / D36 / D2E. That
   single run names the true second blocker instead of guessing, and costs nothing new.
2. **Then** decide between the blunt 0xE0091D04 stub and a minimal two- or three-point
   stub set, based on what step 1 shows.
3. **In parallel (no QEMU needed): land the two safe edits.** Fix the assert address to
   0xE0617620 in cam_config/6D2/debugmsg.gdb, and record the working stub. There is no
   6D2 `patches.gdb` upstream and `run_qemu.py` sources nothing
   (ml_qemu/run.py:175-176 only opens the gdb port), so any patch must live in the
   minimal standalone gdb script you launch by hand.
4. **The new wall, when you get to it:** Panning's gyro poll. Static read (untested):
   entry 0xE07DFB1C, `ldr r0,[pc]` → literal 0xE07DFC54 = **0xD9008696**,
   `ldrh r1,[r0]` at 0xE07DFB24, `cmp r1,#0` / `beq 0xE07DFBC2` → DebugMsg
   "WAIT AUTO GYRO OFFSET" (0xE07DFC9C) → re-arm a 100 ms timer (callback 0xE07DDED3,
   `GyroOffsetTimerCBR`). qemu-eos maps 0xD9001600-0xD900FFFF to `eos_handle_memdiv`
   (hw/eos/eos.c:671) whose default case is a write-back `shm` array, so the register
   reads 0 forever. Cheapest probe: `b *0xE07DFB26` + `set $r1 = 1`.
   Caveat: forcing it feeds all-zero gyro samples (0xD900866C / 0xD9008672) downstream.

Minimal working script for step 1 (proven launch pattern — QEMU first, `sleep 12`,
then `arm-none-eabi-gdb -nx -batch -x <script>`; keep the script minimal, the full
debugmsg chain still dies on the SIGTRAP at 0xdf00a5d4):

```gdb
set pagination off
set confirm off
set print thread-events off
set architecture arm
target remote localhost:1234
set *(unsigned short*)0xE0494208 = 0x4770
b *0xE0202374
commands
  silent
  set $r0 = 0x7D0
  c
end
# probe every call boundary inside 0xE0091D04
b *0xE0091D14
b *0xE0091D18
b *0xE0091D1C
b *0xE0091D20
b *0xE0091D28
b *0xE0091D36
b *0xE0091D2E
commands
  silent
  printf "STEP pc=0x%x core=%d\n", $pc, $_thread
  c
end
b *0xE0617620
commands
  silent
  printf "ASSERT core=%d file=%s line=%d lr=0x%x\n", $_thread, (char*)$r1, $r2, $lr
  c
end
cont
```
(`commands` after a bare `b` applies to the last breakpoint only — set the printf
block on each, or use run-4's per-breakpoint form.)

---

## 6. Open questions / nobody could determine

- **Why 0xE0494208 does not return.** Never bisected. It is a long linear init
  (`bl 0xE013B5CE`, 0xE013CD52, 0xE00D8EEC, 0xE036E2A0, 0xE013D634, 0xE0494500 …) with
  an init-once flag at the literal 0xE04945C8. MMIO poll, missing interrupt, missing
  DMA completion and never-given semaphore are all still live candidates.
- **Whether the remaining calls in 0xE0091D04 also block** (0xE0228AC0, 0xE0309B5C,
  0xE01A2972, 0xE0091D36). Never executed in any run.
- **How EngInit is dispatched.** It has zero BL/BLX callers and zero aligned pointer
  references in 32 MiB; the only route found is the tail branch `b.w` at 0xE004431C.
  Live `lr=0xE004055B` at entry does not match that; unresolved.
- **Who gives the PU1Wait semaphore.** Static scan found only create/dump/take/delete
  of `*(0x41F0+0x38)`. Empirically it *is* given once EngInit completes. Site unknown.
- **Whether the ShtCap handle is literally the ENG_RES_MNG one.** run-3 printed
  `*(uint*)0x10BFC == 0` at the assert and run-1's stack held 0x00010BF0 with return
  address 0xE04AA71F, but `r4` at 0xDF00B450 was never read directly. Strong
  circumstantial, not register-level proof.
- **Why boot now parks at the gyro poll** — collateral from the skipped engine init, or
  an independent unmodelled-hardware wall? Untested. The three I2C errors just before
  the loop (`I2C_Read[CH1] 0x64,0x1d`, `0x64,0x1f`, `I2C_Write[CH1] 0x64,0x1f,0x01,0x20`)
  are plausibly the same device at I2C address 0x64; unverified.
- **No run reached `startupInitializeComplete`, and no DIGIC 6/7/8 body ever has**
  upstream — ml_tests/log_test.py:25-75 lists only 5D3, 50D, 60D, 100D, 700D, 500D.
  Reaching it on a dual-core body would be a first. Budget accordingly.
- Every run ended on the harness timeout, so "never returns" means "did not return
  within ~200–450 s of gdb-attached run time".
