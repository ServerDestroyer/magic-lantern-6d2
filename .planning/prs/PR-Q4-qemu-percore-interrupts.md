# PR Q4 — qemu-eos: per-core Canon interrupt controllers and a per-CPU GIC interface

- **Target repo:** `reticulatedpines/qemu-eos`
- **Target branch:** `qemu-eos-v4.2.1` (based on `4b667a1d3c`)
- **Source branch:** none yet — see PR Q2 for why no branch exists in the shared clone.
- **Files:** `hw/eos/eos.c` (+200/−74), `hw/eos/eos.h` (+12/−3),
  `hw/eos/dbi/logging.c` (+5/−5)
- **Patch file:** `.planning/prs/PR-Q4-qemu-percore-interrupts.patch` (534 lines)
- **Commits:** 1
- **Submit after PR Q2 has landed** — the measurement below was taken with Q2's
  MPU spells in place, because without them the 6D2 boot dies before the
  interrupt behaviour is observable.

> **Do not use `patches/0008-qemu-eos-gic-pending-irq-fix.patch` for this.** That
> file contains only the `hw/eos/eos.c` hunks and does not compile on its own —
> the `irq_enabled` / `irq_id` array-rank change lives in `eos.h` and
> `dbi/logging.c` reads those fields. `PR-Q4-qemu-percore-interrupts.patch` is
> the complete form.

## Title

```
eos: per-core Canon interrupt controllers and a per-CPU GIC interface
```

## PR body (ready to paste)

```markdown
## The defect

DIGIC 7 has a **two-level** interrupt architecture. `0xC1000000` is a real
Cortex-A9 GIC carrying only four INTIDs, and all 448 device interrupts sit
behind **two Canon interrupt controllers, one per core**: `0xD4011000` (core 0)
and `0xD5011000` (core 1). The 6D2's per-core bank base table is at ROM
`0xE0835820` = `{0xD4010000, 0xD5010000}`, referenced from `0xE026AFE4` and
`0xE01E4E4C`.

The common IRQ dispatcher at ROM `0xE026ABD4` decodes it like this:

    e026abdc  ldr.w r7, [r0, #0x10c]     ; r7 = GICC_IAR
    e026abe2  ubfx  r1, r7, #0, #10      ; INTID = iar & 0x3FF
    e026abf2  bne.n 0xe026acba           ; INTID not in {0x20,0x21} -> SGI path
    e026abf4  and.w r8, r1, #1           ; BANK = INTID & 1        <-- core index
    e026abfa  ldr.w r0, [r1, r8, lsl #2] ; bank base
    e026ac02  ldr   r5, [r0, #0]         ; INT REASON of THAT bank

`GICC_IAR` is the only thing that tells the firmware which core's reason
register to read.

qemu-eos registered the `0xD5011000` window in its handler table (`parm 2`), but
`eos_handle_intengine()` switched on `address` alone and had **no case label for
any core-1 address**. Every interrupt DryOS armed on core 1 was silently dropped
and permanently undeliverable. `GICC_IAR` returned a hardcoded `0x20`, so core 1
was never told a device interrupt was its own. A single global `iar` served both
banked CPU interfaces, and device delivery went to `CURRENT_CPU` — whichever
vCPU happened to be executing.

There is a concrete corruption path from the single global `iar`: ROM
`0xE015FCFC` is a wait-for-specific-SGI loop that reads `GICC_IAR` and writes
`GICC_EOIR` on **every** spurious wake. With one global `iar` cleared on any
core's `GICC_EOIR` write, a core spinning there consumes and destroys the other
core's pending SGI.

## What changed

- **`eos.h`** — `irq_enabled[INT_ENTRIES]` → `irq_enabled[2][INT_ENTRIES]`,
  `irq_id` → `irq_id[2]`: one enable bitmap and one read-to-clear reason
  register per bank, which is what the hardware has. `OTHER_CPU` (unused, and
  NULL-derefs when `current_cpu == NULL`) is deleted; `CURRENT_BANK` and
  `CURRENT_IRQ_ID` are added for the `dbi/logging.c` call sites.
- **`eos_update_irq_line(bank)`** (new) — a core's IRQ line is the OR of a
  latched device interrupt and a pending SGI. Every path that changes either
  recomputes the line through this one function, so acking an SGI can no longer
  drop a live device interrupt and acking a device interrupt can no longer drop
  a pending SGI. It becomes the only caller of
  `cpu_interrupt`/`cpu_reset_interrupt` in `hw/eos`.
- **`eos_deliver_int(id)`** (new) — latches `id` in every bank that has it armed
  and is not already servicing something, and raises those cores' lines.
  Replaces `cpu_interrupt(CPU(CURRENT_CPU), …)` in both `eos_trigger_int()` and
  `eos_interrupt_timer_body()`. Delivering to *every* armed bank rather than to
  a single owner is load-bearing: the 6D2 arms the DryOS timer `1Bh` on both
  banks, and a last-writer-wins owner starves whichever core armed it first.
- **`eos_handle_intengine`** — derives `bank` from the `parm` the handler table
  already passes (`2` = D7 CPU1, `5` = DX CPU1, `9` = D8 CPU1) and adds the
  missing case labels for `0xD5011000/010/200`, `0xD0231000/010/200`,
  `0xD233A000/010/200`. Adds the **disable** register `0xD4011018`/`0xD5011018`
  (ROM `0xE01E4DF6`) — guest `disable_interrupt()` was a no-op before. Also
  bounds `irq_enabled[bank][value]` on `value < INT_ENTRIES`; the old
  `irq_enabled[value] = 1` had no bound at all.
- **`eos_handle_intengine_gic`** — `static int iar` → `gic_sgi_pending[2]`, one
  slot per CPU interface, cleared on `GICC_IAR` read (GICv1 semantics) rather
  than on any core's `GICC_EOIR` write. `GICC_IAR` now returns the pending SGI,
  else `0x20 + cpu` when that core has a latched device interrupt, else `0x3FF`
  (spurious — ROM `0xE026ACBA` returns immediately on `0x3FF` instead of
  dispatching handler-table entry 0 for a reason register that reads 0).
  `ICDSGIR` decodes the real `CPUTargetList` `[23:16]` and `TargetListFilter`
  `[25:24]` instead of unconditionally kicking "the other CPU", and no longer
  scribbles the raw register value into the `GICD_ISENABLER` shadow.
- **`eos_handle_intengine_vx`** — `COUNT(eos_state->irq_enabled)` → `INT_ENTRIES`.
  Required, not cosmetic: after the rank change `COUNT()` evaluates to 2, which
  would silently break the bound check on the DIGIC 2/3 + 60D `0xC0200000` block.
- **Runtime self-checks** (two `fprintf`s, no new options). On a
  `GICD_ISENABLER` write that enables SPI `0x20`/`0x21` on a dual-core model,
  warn if `ITARGETSR` is not `{1, 2}` — the assumption the bank routing rests on.
  And a one-shot warning if a core ever reads the *other* bank's reason
  register. Neither fired in any 6D2 boot.
- **Comment corrections** — `0xC1100000` is a **PL310 L2 cache controller**, not
  a multicore/mailbox block. ROM `0xE00D9C64` writes `+0x104` (aux ctrl),
  `+0x108`/`+0x10C` (RAM latency), `+0x900+i*8` (lockdown), `+0x220` (int clear),
  `+0x214 = 0` (int mask — the L2 raises no interrupts), `+0xF60`/`+0xF80`
  (prefetch/power), `+0x100 = 1` (enable). So `+0x100` is L2 Control, not "Wake
  Up CPU1?", and `+0x214` is the L2 Interrupt Mask, not "Signal to CPU1?".
  Behaviour (return 0) was already adequate and is unchanged; only the labels
  and a dead `#if 0` block go. The `arm_gic.c` FIXME is kept, with the condition
  under which it becomes worth doing spelled out.

## Measured — on the 6D2 only

Stock 6D2 firmware, headless, with this repository's 6D2 MPU spells.

**60 s, `-d debugmsg,int`:**

| signal | before | after |
|---|---|---|
| `Taking exception 5 [IRQ]`, total | 6790 | **13310** |
| …at `0xE00D97E0` (**core 1** idle park, `wfi; b .-2`) | **0** | **6520** |
| …at `0xE04DCA82` (core 0, the insn after `msr CPSR` re-enables IRQs) | 6368 | 6716 |
| `trigger int 0x147` immediate / delayed / delayed! | 22 / 152 / 176 | 22 / 152 / 176 |
| `trigger int 0x28` immediate | 58 | 61 |
| SGI sends / acks | 5 / 5 | 5 / 5 |

**Core 1 receiving 6520 IRQs where it previously received none is the whole
result.** They are the DryOS timer `1Bh` (`model_list.c dryos_timer_interrupt`
for DIGIC 6/7), which the guest arms on bank 1 (`0xD5011010`) about 100×/s and
which qemu-eos silently discarded. The explicit `eos_trigger_int` device counts
are unchanged — those interrupts were and remain core-0 work, exactly as the
real-hardware log predicted. SGI logging now shows
`cpu 0 sending SGI 0xa to cpumask 2` / `cpu 1 ack SGI 0xa`, versus the old
`cpu 1 ack SGI 0x0, iar: 0xa`.

**120 s, `-d debugmsg`, no regression:** 1582 stderr lines, 1019 unique message
texts, zero `ASSERT` / `Irregular TotalSheets` / `ErrorSend`, startup completes
normally (`startupCompleteCallback 0x10`, `[SEQ] NotifyComplete (Startup,
Flag = 0x10)`), and the boot reaches the same stopping point as without the
patch. Four earlier runs at the previous boot ceiling produced identical unique
message sets (390 texts, same last message); the few-line run-to-run delta is
SGI log format plus the coalesced `CACHEMAINT … xN (omitted)` counts.

**The boot ceiling did not move**, exactly as predicted before the work started.
The interrupt system is not what blocks this boot; the remaining candidates are
the unmodelled DIGIC 7 I2C block and the SD/CSMgr event chain.

## Testing gap — please read before merging

**This has been tested on exactly one model.** The submitter has ROM dumps for
the 6D2 and for nothing else, so booting any other camera was impossible here.
That is stated as a limitation, not glossed.

`.max_cpus = 2` in `model_list.c` covers 20 models besides the 6D2:

- **DIGIC 7:** 200D, 77D, 800D, EOSM5
- **DIGIC 8:** EOSM50, EOSM6mk2, EOSR, EOSRP, SX70, SX740, 850D, 90D
- **DIGIC X:** EOSR5, EOSR6, XF605

**The two boots most worth doing before merge are a 200D (dual-core DIGIC 7,
shares `eos_handle_intengine_gic` with the 6D2) and any single-core DIGIC 6 body
(80D / 750D / 5D4 — for the new `0xD4011018` case).**

### What is safe by construction

For every `.max_cpus = 1` model — all DIGIC 3/4/5/6 plus 5D3eeko —
`eos_state->cpu1` is NULL, so `bank` is always 0, `eos_deliver_int()` skips bank
1 and reduces to the old `irq_enabled[id] && !irq_id` condition, and
`eos_update_irq_line(0)` reduces to the old `cpu_interrupt` /
`cpu_reset_interrupt` (`gic_sgi_pending[0]` can only be set from
`eos_handle_intengine_gic`, i.e. `0xC1000000`, which no pre-DIGIC-7 firmware
touches). The array-rank change is mechanical for them.

### What is genuinely new behaviour, and for whom

1. **`0xD4011018` disable register, DIGIC 6 and 7.** Writes there were previously
   ignored; they now clear the enable bit. Nine single-core DIGIC 6 models share
   that address window. If one of them currently boots *because* qemu-eos ignored
   a `disable_interrupt()`, honouring it now starves that interrupt. Cheap
   fallback: restrict the case to `0xD5011018`, or gate on `digic_version == 7`.
2. **`ICDSGIR` target decoding, all dual-core models.** The old code kicked "the
   other CPU" unconditionally. The comment preserved in this patch names the
   dependency: *"0xa is required to wake cpu1 from a wfi loop while cpu0 does
   early init. See e.g. 200D 1.0.1 `0xe0004d30`"*. Filters 0/1/2 are all handled;
   the failure mode is a model writing filter 0 with an empty target list, which
   would now drop the SGI. Not observed on the 6D2 (ROM `0xE015FCE4` builds an
   explicit non-empty list); not checkable against other ROMs here.
3. **`GICC_IAR` returning `0x3FF` when nothing is pending** (was `0x20`
   unconditionally), and `0x20 + cpu` rather than always `0x20`. Spec-correct
   GICv1 and matched to 6D2 ROM `0xE026ACBA`, but shared by every DIGIC 7 model.
   Bug-compatible fallback if one regresses: return `0x20 + cpu` unconditionally.
4. **`gic_sgi_pending` cleared on IAR read, not on EOIR write.** This is the fix
   for the cross-core SGI destruction described above, but it changes SGI timing
   for all dual-core models.
5. **DIGIC 8 / DIGIC X CPU1 bank labels.** `0xD0231000/010/200` and
   `0xD233A000/010/200` were previously unhandled; they are now live. **DIGIC X
   deserves specific attention:** `eos.c` starts its cpu1 halted *"to avoid bad
   race around MMU table access"*, and `eos_deliver_int()` calls `cpu_interrupt()`
   on a bank-1 interrupt, which in QEMU makes a halted CPU runnable. If R5/R6/
   XF605 firmware arms a bank-1 interrupt before it means to release cpu1, this
   patch could re-introduce that race. **If the maintainer prefers, the DIGIC X
   case labels can be dropped from this PR** and left to whoever has a DX ROM; the
   6D2 result does not depend on them.

Note also that no `0xD0231018` / `0xD233A018` disable labels were added, only the
DIGIC 6/7 pair — an asymmetry that should be resolved one way or the other.

## What is NOT claimed

- **Not a boot fix.** The 6D2 stalls at exactly the same place with and without
  this patch. It is a correctness fix that makes core 1 functional; it does not
  advance the boot.
- **Magic Lantern still does not boot under emulation.** With ML's `autoexec.bin`
  on the card and `boot=1`, both cores spin at `0x001037A8` / `0x0010390C` inside
  ML's relocated image. This patch does not change that.
- **No other model was booted.** See the testing gap above.
- **The two runtime self-checks are not a test suite.** They fire only if the
  bank-routing assumption stops holding. They did not fire on the 6D2, which is
  evidence about the 6D2 and nothing else.
- **This corrects an earlier prediction of ours.** The design note that preceded
  this work predicted **zero** `0xD5011010` writes over a boot, inferring from a
  real-hardware log that showed no core-1 ISRs, and concluded the work would be
  "correctness/determinism only". Measured: non-zero — core 1 arms `1Bh` about
  100×/s plus eight UTimer ids once each. Also, the 6368 pre-fix IRQ exceptions
  at `0xE04DCA82` are **real core-0 timer ticks** landing on the instruction
  right after a critical section re-enables interrupts (ROM `0xE04DCA72`:
  `mrs r1,CPSR; bic r1,#0x80; orr r1,r0; msr CPSR_fsxc,r1; bx lr`), not a
  spurious storm. A high exception count at a single PC is not by itself evidence
  of health or of livelock.
```

## Suggested commit message

```
eos: per-core Canon interrupt controllers and a per-CPU GIC interface

DIGIC 7 puts all 448 device interrupts behind two Canon interrupt
controllers, one per core -- 6D2 bank base table at ROM 0xE0835820 =
{0xD4010000, 0xD5010000}. The common dispatcher at ROM 0xE026ABD4 reads
GICC_IAR, takes INTID & 1 as the bank index (0xE026ABF4) and reads that
bank's reason register.

qemu-eos registered the 0xD5011000 window in the handler table (parm 2)
but eos_handle_intengine() switched on address alone and had no case
label for any core-1 address, so every interrupt DryOS armed on core 1
was silently dropped and permanently undeliverable. GICC_IAR returned a
hardcoded 0x20, so core 1 was never told a device interrupt was its own.
One global iar served both banked CPU interfaces, and delivery went to
CURRENT_CPU -- whichever vCPU happened to be executing. ROM 0xE015FCFC
is a wait-for-SGI loop that reads IAR and writes EOIR on every spurious
wake, so with one global iar a core spinning there consumed and
destroyed the other core's pending SGI.

  - eos.h: irq_enabled[INT_ENTRIES] -> irq_enabled[2][INT_ENTRIES],
    irq_id -> irq_id[2]. Drop the unused OTHER_CPU (which NULL-derefs
    when current_cpu == NULL); add CURRENT_BANK / CURRENT_IRQ_ID.
  - eos_update_irq_line(bank): a core's IRQ line is the OR of a latched
    device interrupt and a pending SGI; every path that changes either
    recomputes it here. Now the only caller of cpu_interrupt /
    cpu_reset_interrupt in hw/eos.
  - eos_deliver_int(id): latch in every bank that armed it and is idle.
    Delivering to every armed bank matters -- the 6D2 arms the DryOS
    timer 1Bh on both, and a single-owner model starves one of them.
  - eos_handle_intengine: derive bank from parm (2 = D7 CPU1,
    5 = DX CPU1, 9 = D8 CPU1); add the missing 0xD5011000/010/200,
    0xD0231000/010/200, 0xD233A000/010/200 labels; add the disable
    register 0xD4011018 / 0xD5011018 (ROM 0xE01E4DF6), previously a
    no-op; bound irq_enabled[bank][value] on value < INT_ENTRIES (the
    old write had no bound).
  - eos_handle_intengine_gic: gic_sgi_pending[2] replaces the global
    iar, cleared on GICC_IAR read per GICv1 rather than on any core's
    EOIR write. GICC_IAR returns the pending SGI, else 0x20 + cpu when
    that core has a latched device interrupt, else 0x3FF (ROM
    0xE026ACBA returns immediately on 0x3FF). ICDSGIR decodes the real
    CPUTargetList [23:16] and TargetListFilter [25:24].
  - eos_handle_intengine_vx: COUNT(irq_enabled) -> INT_ENTRIES. Required
    -- COUNT() on the 2-D array is 2 and would break the D2/D3 + 60D
    bound check.
  - Two runtime self-checks: warn if ITARGETSR for SPI 0x20/0x21 is not
    {1,2} on a dual-core model, and one-shot if a core reads the other
    bank's reason register. Neither fired on the 6D2.
  - 0xC1100000 is a PL310 L2 cache controller, not a multicore/mailbox
    block (ROM 0xE00D9C64). Correct the +0x100 and +0x214 labels and
    drop a dead #if 0; behaviour unchanged.

Measured on the 6D2, 60s, -d debugmsg,int: IRQ exceptions at 0xE00D97E0
(core 1's idle park, wfi; b .-2) go from 0 to 6520 -- the DryOS timer
1Bh, armed on bank 1 about 100x/s and previously discarded. Total IRQ
exceptions 6790 -> 13310. Explicit eos_trigger_int device counts are
unchanged (0x147: 22/152/176 both before and after), as the real
hardware log predicted -- those are core-0 work. 120s -d debugmsg shows
no regression: 1582 stderr lines, zero ASSERT / Irregular TotalSheets /
ErrorSend, same boot ceiling.

TESTED ON ONE MODEL ONLY. The submitter has ROM dumps for the 6D2 and
no other camera, so no cross-model boot was possible. 20 other models
have .max_cpus = 2 and execute these paths. The riskiest items for them
are the ICDSGIR target decoding (the in-tree comment names 200D 1.0.1
0xe0004d30 as depending on SGI 0xa to wake cpu1), GICC_IAR returning
0x3FF instead of 0x20, the new 0xD4011018 disable case on single-core
DIGIC 6, and delivery to a DIGIC X cpu1 that eos.c deliberately starts
halted. Please boot a 200D and one DIGIC 6 body before merging.
```

## Exact commands for Chris (branch + push)

```sh
# Same throwaway-clone approach as PR Q2 -- never branch in the shared clone.
cd "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/qemu-eos"
git clone --no-hardlinks . /tmp/qemu-eos-pr-q4
cd /tmp/qemu-eos-pr-q4
git checkout -b eos-percore-interrupts 4b667a1d3c

git apply "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/prs/PR-Q4-qemu-percore-interrupts.patch"
git add hw/eos/eos.c hw/eos/eos.h hw/eos/dbi/logging.c
git commit -F - <<'EOF'
<paste the commit message above>
EOF

git remote add fork git@github.com:<YOUR_GITHUB_USER>/qemu-eos.git
git push fork eos-percore-interrupts

gh pr create --repo reticulatedpines/qemu-eos \
  --base qemu-eos-v4.2.1 --head <YOUR_GITHUB_USER>:eos-percore-interrupts \
  --title "eos: per-core Canon interrupt controllers and a per-CPU GIC interface" \
  --body-file <(sed -n '/^```markdown$/,/^```$/p' \
      "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/prs/PR-Q4-qemu-percore-interrupts.md" \
      | sed '1d;$d')
```

## Fix before pushing (one line)

`eos.c`, the `[GIC] SPI ... enabled with ITARGETSR ...` warning inside the
`GICD_ISENABLER` case has no `static int warned` guard, unlike its sibling
`[INT] cpuN read bank M reason register` warning. It fires on *every*
`GICD_ISENABLER` word-1 write, so on a model whose `ITARGETSR` layout differs it
spams stderr instead of warning once. Add the guard before pushing — a reviewer
who boots a 200D and sees a wall of identical lines will read it as a fault in
the patch.
