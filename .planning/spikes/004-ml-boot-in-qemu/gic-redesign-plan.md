# qemu-eos multi-core interrupt redesign for the 6D2

Design document. **No source was edited and nothing was built** to produce it.
All line numbers are against the working tree as of 2026-08-15 (`qemu-eos`
at `4b667a1d3c` + uncommitted `hw/eos/eos.c`, which already contains
`patches/0008-qemu-eos-gic-pending-irq-fix.patch`).

Everything below marked "ROM 0x…" was read out of
`roms/6D2/ROM0.BIN` (base `0xE0000000`, file offset = address − base) and
disassembled as Thumb-2 (SCTLR.TE=1 on this firmware — confirmed by the
observed `SCTLR_S <- 0x48C5187D`, bit 30 set — so the vector table and every
handler below are Thumb, not ARM).

---

## 0. Headline

The existing ad-hoc GIC model is not merely "single-CPU"; it is modelling the
**wrong device**. Canon's 6D2 firmware treats `0xC1000000` as a real Cortex-A9
GIC that carries only **four** interrupt IDs, and puts all 448 device
interrupts behind **two** Canon interrupt controllers — one per core, at
`0xD4011000` (core 0) and `0xD5011000` (core 1). qemu-eos implements one global
Canon controller and never decodes the core-1 window at all.

The correct fix is to make the Canon controller **per bank** and let the bank
decide the delivery target. It is roughly 60 lines. Adopting `intc/arm_gic.c`
would not help, because `arm_gic.c` cannot model the Canon controller — that
part would still have to be hand-written. Recommendation and reasoning in §4.

---

## 1. What the 6D2 firmware actually does

### 1.1 The two-level interrupt architecture (measured from ROM)

```text
  448 device interrupts (Canon ids 1 .. 0x1BF)
        |                                    |
   [Canon intc bank 0]                 [Canon intc bank 1]
     0xD4011000                          0xD5011000
        |                                    |
   GIC SPI 0x20 ------> CPU0            GIC SPI 0x21 ------> CPU1
        \                                    /
         `---- GIC @ 0xC1000000 (Cortex-A9 private memory region) ----'
                     also carries SGIs 0x0..0xF (0xA and 0xD in use)
                     and Canon ids >= 0x1C0 mapped to INTID (id - 0x1C0)
```

The per-core bank base table is **ROM `0xE0835820` = `{ 0xD4010000, 0xD5010000 }`**
(referenced from ROM `0xE026AFE4` and `0xE01E4E4C`). Register offsets are
`base + 0x1000 + n`.

### 1.2 The common IRQ dispatcher — ROM `0xE026ABD4`

Entered from the IRQ vector at ROM `0xE026AA68` (`VBAR = 0xE026A9E0`, so the
IRQ entry is `0xE026A9F8` → `0xE026AA68`). Verbatim decode:

```asm
e026abd8  mov.w r0, #0xC1000000
e026abdc  ldr.w r7, [r0, #0x10c]     ; r7 = GICC_IAR  (0xC100010C)
e026abe2  ubfx  r1, r7, #0, #10      ; r1 = INTID = iar & 0x3FF
e026abee  cmp.w r0, r1, lsr #1       ; r0 == 16 here
e026abf2  bne.n 0xe026acba           ; INTID not in {0x20,0x21} -> SGI/other path
e026abf4  and.w r8, r1, #1           ; r8 = BANK = INTID & 1   <-- the core index
e026abf8  ldr   r1, [pc, #1000]      ; -> 0xE0835820
e026abfa  ldr.w r0, [r1, r8, lsl #2] ; r0 = bank base (0xD4010000 / 0xD5010000)
e026abfe  add.w r0, r0, #0x1000
e026ac02  ldr   r5, [r0, #0]         ; r5 = INT REASON  (0xD4011000 / 0xD5011000)
...       spinlock, handler table at *(0xE026AFEC) = 0x65A08, entry = {fn, arg}
e026ac5c  mov.w r0, #0xC1000000
e026ac60  str.w r7, [r0, #0x110]     ; GICC_EOIR  (0xC1000110)
```

The non-`{0x20,0x21}` path at `0xE026ACBA`:

```asm
e026acba  sub.w r0, r1, #0x300 ; subs r0, #0xff ; beq -> return   ; INTID 0x3FF = spurious
e026acc2  ldr   r0, [pc,#796] ; ldr r0,[r0,#4]                    ; SGI handler table
e026acc6  add.w r0, r0, r1, lsl #3 ; ldr r2,[r0] ; blx r2         ; dispatch
e026acf6  str.w r7, [0xC1000110]                                  ; EOI
```

Two strings confirm the model: ROM `0xE026AFF0` = `"-- Illegal inter 0x%x(%d)[puId %d] --"`
and ROM `0xE026B018` = `"-- Illegal GIC inter 0x%x(%d)[puId %d] --"`. Neither
appears in any captured log.

**Consequences that matter to the emulator**

- `GICC_IAR` is read on **every** interrupt entry on **both** cores.
- `GICC_EOIR` is written on **every** interrupt exit on **both** cores.
- The value returned by `GICC_IAR` is the *only* thing that tells the firmware
  which core's reason register to read. qemu-eos hardcodes `0x20`, so **core 1
  is never told it has a device interrupt** and always reads core 0's bank.

### 1.3 GIC initialisation — ROM `0xE00D9ACA`

```asm
e00d9af2  r0 = 0x20, r1 = 0 ; bl 0xE00D9C14   ; GICD_ITARGETSR[0x20] |= 1<<0
e00d9afe  0xC1001420 <- 16 (byte)             ; GICD_IPRIORITYR[0x20] = 16
e00d9b02  r0 = 0x20 ; bl 0xE00D9A96           ; GICD_ISENABLER[0x20]
e00d9b0c  r0 = 0x21, r1 = 1 ; bl 0xE00D9C14   ; GICD_ITARGETSR[0x21] |= 1<<1
e00d9b18  0xC1001421 <- 16 (byte)             ; GICD_IPRIORITYR[0x21] = 16
e00d9b1e  r0 = 0x21 ; bl 0xE00D9A96           ; GICD_ISENABLER[0x21]
```

`set_gic_target(intid, cpu)` at ROM `0xE00D9C14` is
`GICD_ITARGETSR[intid] |= 1<<cpu` (byte access at `0xC1001800 + intid`), and it
**refuses if the interrupt is already enabled**.

`gic_enable(intid)` at ROM `0xE00D9A96` first does
`if ((GICD_ITARGETSR[intid] & 3) == 0) return -1;` (`lsls r1,r1,#30; beq`)
before writing `GICD_ISENABLER`. **qemu-eos's `target[]` read path is therefore
load-bearing today** — if it returned 0, the firmware would never enable
INTID 0x20 and nothing would boot.

`GICC_CTLR = 1` and `GICC_PMR = 0xFF` are written at ROM `0xE00D9A84` and never
read back, which is why qemu-eos getting away with no-ops there is fine.

### 1.4 The Canon bank accessors — ROM `0xE01E4D7C` … `0xE01E4E48`

| ROM | operation | register written |
|---|---|---|
| `0xE01E4D8E`–`0xE01E4DC4` | init loop `for (cpu=0; cpu<2; cpu++)` | `bank+0x010C`, `bank+0x1200`, `bank+0x3074`, 16 status words |
| `0xE01E4DC6` | `enable_int(cpu, id)`, bounds `1 <= id < 0x1C0` | `bank+0x1010 = id` |
| `0xE01E4DF6` | `disable_int(cpu, id)`, same bounds | `bank+0x1018 = id` |
| `0xE01E4E26` | `is_int_enabled(cpu, id)` | reads `bank + 4 + (id%16)*16`, bit `id/16` |

The DryOS wrapper at ROM `0xE026AD00` picks the core:

```asm
e026ad0a  cmp.w r4, #0x1C0
e026ad10  ble   -> Canon bank path
e026ad12  sub.w r0, r4, #0x1C0 ; bl 0xE00D9A96   ; id >= 0x1C0 -> raw GIC enable
e026ad1c  mov.w r0, #0x1000
e026ad22  ldr   r0, [r0, #8]                     ; r0 = *(u32*)0x1008 = THIS CORE'S ID
e026ad24  bl    0xE01E4DC6                       ; enable_int(cpu, id)
```

and the registration path at ROM `0xE026AEAA` passes an explicit `cpu` argument
(kept in a 2-bit-per-id ownership map at `0x65A08 + 0x1000 + (id>>4)*4`).

**This is the routing oracle the emulator needs and currently throws away:
the owning core of interrupt `id` is the bank whose `+0x1010` the guest wrote.**

### 1.5 SGIs — ROM `0xE015FCE4`

```asm
e015fce4  orr.w r0, r0, r1, lsl #16
e015fce8  movw r1,#0x1F00 ; movt r1,#0xC100
e015fcf0  str  r0, [r1]                 ; ICDSGIR = (targetmask << 16) | sgi_id
e015fcf2  dsb sy
```

Standard GICv1 `ICDSGIR`: `[3:0]` INTID, `[23:16]` CPUTargetList,
`[25:24]` TargetListFilter (always 0 here — explicit list). Two senders:

- ROM `0xE00D9C54`: `send_sgi(0xA, 1 << cpu)` — the `dcache_clean_multicore`
  handshake (`dcache_clean_multicore` itself is at `0xE00D9CCC`, named in
  `platform/6D2.111/stubs.S:37`).
- ROM `0xE0093184`: `send_sgi(0xD, 3 & ~(1 << self))` — a stop-the-world
  rendezvous that then spin-waits on a memory flag with a `0x800000` timeout.

There is also a wait-for-specific-SGI loop at ROM `0xE015FCFC`:

```asm
e015fd02  dsb sy
e015fd06  wfi
e015fd08  r1 = 0xC100010C ; r2 = *r1        ; read GICC_IAR
e015fd12  subs r1, r2, r0                   ; compare to expected SGI id
e015fd14  r1 = 0xC1000110 ; *r1 = r2        ; EOI whatever we got
e015fd1e  bne -> 0xe015fd02
```

**This loop reads IAR and writes EOIR on every spurious wake.** With one global
`iar` (eos.c:2825) and one global EOIR reset (eos.c:2910), a core spinning here
consumes and destroys the *other* core's pending SGI. That is the concrete
mechanism behind the evening session's nondeterministic stall.

### 1.6 Things the 6D2 firmware does **not** use (measured, negative results)

- **A9 global timer (`0xC1000200`) and private timers (`0xC1000600`)**: zero
  references in ROM0. No need to model them, and no need for `a9mpcore`.
- **`0xC1100000` is not "Multicore"** — it is a **PL310 L2 cache controller**.
  ROM `0xE00D9C64` writes `+0x104` (aux ctrl), `+0x108`/`+0x10C` (RAM latency),
  `+0x900+i*8` (lockdown ×8), `+0x220 = *(+0x21C)` (int clear from raw status),
  `+0x214 = 0` (**interrupt mask = 0, i.e. L2 raises no interrupts**),
  `+0xF60`/`+0xF80` (prefetch/power), `+0x100 = 1` (enable);
  `+0x730` / `+0x77C` / `+0x7B0` are clean/invalidate ops used by
  `dcache_clean_multicore`. eos.c:2627–2646 mislabels `0x100` as
  "Wake Up CPU1?" and `0x214` as "Signal to CPU1?". Behaviour (return 0) is
  adequate; **the comments should be corrected so this block stops appearing on
  suspect lists.**

---

## 2. Every single-CPU assumption in the interrupt path

Grouped by severity. "Bank" below means the Canon interrupt controller instance
(`0xD4011000` = bank 0 / core 0, `0xD5011000` = bank 1 / core 1).

### 2.1 Blocking defects — wrong behaviour today

| # | file:line | code | why it is wrong |
|---|---|---|---|
| B1 | `hw/eos/eos.h:322` | `uint32_t irq_id;` | one reason-register latch for two banks. Bank 1's reason register cannot be represented. |
| B2 | `hw/eos/eos.h:320` | `uint32_t irq_enabled[INT_ENTRIES];` | one enable bitmap for two banks; core ownership is unrepresentable. |
| B3 | `hw/eos/eos.c:554-555` | `{0xD4011000,…,parm 1}` / `{0xD5011000,…,parm 2}` | both windows route to `eos_handle_intengine`, which **ignores `parm` entirely** (function at 2713 switches on `address` only). |
| B4 | `hw/eos/eos.c:2720-2726` | `case 0xD4011000: …` | **`0xD5011000` has no case.** A core-1 reason-register read falls through the whole switch, returns 0, does not clear `irq_id`, does not clear `CPU_INTERRUPT_HARD`. |
| B5 | `hw/eos/eos.c:2754-2757` | `case 0xD4011010: …` | **`0xD5011010` has no case.** Every interrupt DryOS enables on core 1 is silently dropped; `irq_enabled[id]` stays 0, so `eos_trigger_int` defers it (2450-2454) and `eos_interrupt_timer_body` (980) never releases it. **Permanently undeliverable.** |
| B6 | — | *(nothing)* | **`bank+0x1018` (disable, ROM `0xE01E4DF6`) has no case for either bank.** Disables are no-ops; qemu only ever clears an enable as a side effect of delivery (1002 / 2442). |
| B7 | `hw/eos/eos.c:2856`, `2896` | `ret = 0x20;` … `ret = iar;` | `GICC_IAR` **never returns `0x21`**. Core 1 is never told a device interrupt is its own; it reads bank 0 and services core 0's interrupt under core 0's DryOS ISR state. |
| B8 | `hw/eos/eos.c:2825` | `static int iar = 0x20;` | one IAR slot for two banked CPU interfaces. Either core's `GICC_IAR` read consumes it (2873-2896). |
| B9 | `hw/eos/eos.c:2910` | `iar = 0x20;` in `GICC_EOIR` | either core's EOI destroys the other core's pending SGI. Combined with the ROM `0xE015FD06` spin loop, this is a reliable SGI-loss generator. |
| B10 | `hw/eos/eos.c:2443` | `cpu_interrupt(CPU(CURRENT_CPU), CPU_INTERRUPT_HARD)` | delivery target is "whichever vCPU was executing" (`CURRENT_CPU` = `cpus[current_cpu ? current_cpu->cpu_index : 0]`, eos.h:60). Called from vCPU context by `engine.c:242,683,1203,1315`, `mpu.c:104,181,314,323,344,368,447`, `serial_flash.c:321,340`, and eos.c:1712, 3052, 3394, 3775, 3965, 4046, 4115, 4191. |
| B11 | `hw/eos/eos.c:2742`, `2795` | `cpu_reset_interrupt(CPU(CURRENT_CPU), …)` | clears the shared `CPU_INTERRUPT_HARD` line that the SGI path (2992-2994) also asserts. Acking a device interrupt cancels a pending SGI. |
| B12 | `hw/eos/eos.c:2991-2994` | `if (cpu_index == 0) cpu_interrupt(cpu1) else cpu_interrupt(cpu0)` | **`ICDSGIR`'s CPUTargetList (`[23:16]`) and TargetListFilter (`[25:24]`) are ignored.** Correct by accident for 2 cores when filter=0 and list=other; wrong for a self-directed SGI. |

### 2.2 Latent defects — currently harmless, will bite

| # | file:line | code | note |
|---|---|---|---|
| L1 | `hw/eos/eos.c:2977` | `if(target_int && type && MODE_WRITE)` | `&&` where `&` was meant. `MODE_WRITE` is `0x20`, always true, so the guard is `target_int && type != 0` and fires on reads too. Harmless only because reads pass `value == 0`. |
| L2 | `hw/eos/eos.c:2979` | `MMIO_VAR(enabled[target_int]);` | writes the raw `ICDSGIR` value into the `GICD_ISENABLER` shadow at index = SGI id (0..15), corrupting `enabled[0..15]`. Harmless only because `enabled[]` is never consulted. |
| L3 | `hw/eos/eos.c:2941` | `MMIO_VAR(enabled[word]);` for `GICD_ISENABLER` | assignment, not set-semantics. `GICD_ICENABLER` at 2953 correctly does `&= ~value`. |
| L4 | `hw/eos/eos.c:2824`, `2969` | `static int target[1024];` / `MMIO_VAR(target[id])` | recorded and read back (load-bearing, see §1.3) but **never consulted for routing**. |
| L5 | `hw/eos/eos.c:2973-2996` | `case 0xf00` | no `break;`. Safe only because it is the last case. |
| L6 | `hw/eos/eos.h:61` | `#define OTHER_CPU eos_state->cpus[current_cpu ? 0 : current_cpu->cpu_index]` | NULL-derefs when `current_cpu == NULL`, and returns `cpus[0]` when it is not. Never used. Delete it. |
| L7 | `hw/eos/eos.h:321` | `uint32_t irq_schedule[INT_ENTRIES];` | global; a deferred interrupt loses its bank. Fixable without a second dimension (see §5). |
| L8 | `hw/eos/eos.c:2884-2894` | the applied patch 0008 re-assert | correct as a stopgap but **must be removed** by this work, not stacked: with per-bank `irq_id` the IAR read never drops a live device interrupt in the first place. |
| L9 | `hw/eos/eos.c:2272`, `2277-2278`, `3012`, `4763`, `4865`, `6294`, `dbi/backtrace.c`, `dbi/memcheck.c` | `CURRENT_CPU->env.regs[…]` | logging/attribution only. Correct as written (they *want* the executing core). No change needed — listed so they are not mistaken for defects. |

### 2.3 Not a defect (verified)

- `eos_interrupt_timer_cb` (eos.c:1087-1091) is a `QEMU_CLOCK_VIRTUAL` timer, so
  it runs on the main loop with `current_cpu == NULL` → `CURRENT_CPU` = `cpus[0]`.
  Timer-sourced interrupts already land on core 0, which is correct for the 6D2.
- MMIO dispatch takes the BQL (`mmio_ops` at eos.c:719 does not set
  `.global_locking = false`), and the timer callback holds it too. **All the
  state below is BQL-serialised — the fix needs no atomics and no new locks**,
  despite MTTCG running the two vCPUs in separate host threads (QEMU 4.2.1).
- `eos_state->cpus[]` is a union with `cpu0`/`cpu1` (eos.h:296-304), so
  `cpus[0] == cpu0` and `cpus[1] == cpu1`. Indexing by bank is safe.

---

## 3. Which core should each interrupt target

| interrupt class | correct target | evidence |
|---|---|---|
| GIC INTID `0x20` (SPI 32) | **core 0** | ROM `0xE00D9AF2`-`0xE00D9AF4`: `set_gic_target(0x20, 0)` sets bit 0 of `ITARGETSR[0x20]` |
| GIC INTID `0x21` (SPI 33) | **core 1** | ROM `0xE00D9B0C`-`0xE00D9B10`: `set_gic_target(0x21, 1)` sets bit 1 of `ITARGETSR[0x21]` |
| Canon device id `1 .. 0x1BF` | **the bank whose `+0x1010` enabled it** | ROM `0xE026AD1C`-`0xE026AD24` (`cpu = *(u32*)0x1008`), ROM `0xE026AEAA` (explicit `cpu` arg), ROM `0xE01E4DC6` |
| Canon device id `>= 0x1C0` | GIC INTID `id - 0x1C0`, per `ITARGETSR` | ROM `0xE026AD12`-`0xE026AD16` |
| SGI `0x0..0xF` | `ICDSGIR[23:16]` mask, filtered by `[25:24]` | ROM `0xE015FCE4` |

**What the hardware actually did.** `tools/6D2-DEBUGMSG-body.txt` (6534 lines, a
real 6D2 boot with `CONFIG_STARTUP_LOG`, ML's `[%d] ` prefix = `get_cpu_id()`):

| core | messages | distinct tasks | ISR pseudo-tasks observed |
|---|---|---|---|
| 0 | 6511 | 72 | `**INT147h*` ×412, `**INT-2Ah*` ×117, `**INT-28h*` ×79, `**INT-37h*` ×8, `**INT-1Bh*` ×7, `**INT15Ah*` ×5, `**INT-A8h*` ×1, `**INT-1Ah*` ×1 |
| 1 | 19 | 4 (`init1`, `FmidCtrl`, `GlobalVect`, `ShtSs`) | **none** |

So on real hardware, in the first ~0.8 s of boot, **every logged interrupt is
serviced on core 0** — 0x147 (MPU SIO3), 0x2A (MPU MREQ), 0x28 (hptimer), 0x1B
(DryOS timer), 0x37, 0x15A, 0xA8, 0x1A. Core 1 runs a small task set
(`FMID_SYS_Initialize`, `FmidCtrl_EventDispath`, `GlobalVectorInit`,
`CORE_CreateTaskRawToYuv`) and, in this window, services no logging interrupt.

The task-name attribution is trustworthy because core 1's names differ from
core 0's, i.e. ML's current-task read is per-core-correct.

**Practical conclusion.** Bank 0 / core 0 is the right default for essentially
everything on this body. The per-bank work is therefore *correctness and
determinism*, not an expected unblock — unless the measurement in §6.1 shows
`0xD5011010` writes, in which case it is also an unblock. Do not build the
routing on a hardcoded table; build it on the bank the guest writes, which
costs the same and is self-correcting for the 200D/77D/800D/M5.

---

## 4. The FIXME at eos.c:2814 — should we adopt `intc/arm_gic.c`?

> `/* fixme: reuse QEMU implementation from intc/arm_gic.c */`

### 4.1 What adopting it would actually entail

1. Instantiate `TYPE_ARM_GIC` (or, more realistically, `hw/cpu/a9mpcore.c`'s
   `TYPE_A9MPCORE_PRIV`, which bundles SCU + GIC + global timer + private
   timers) with `num-cpu=2`, `revision=1`, `num-irq` ≥ 64, mapped at
   `0xC1000000`.
2. Wire it up: `qdev_connect_gpio_out(gic, i, qdev_get_gpio_in(DEVICE(cpu_i), ARM_CPU_IRQ))`
   for each core, and hold `qemu_irq` handles for INTIDs 0x20/0x21.
3. **Rewrite every interrupt source.** eos.c does not use `qemu_irq` at all — it
   calls `cpu_interrupt()` directly. `eos_state->interrupt` (eos.h:316) is
   declared and unused. All ~18 `eos_trigger_int` call sites plus
   `eos_interrupt_timer_body` would have to raise a GIC line instead.
4. **Still hand-write the Canon controller.** `arm_gic.c` has no concept of
   `0xD4011000`/`0xD5011000` — a 448-input multiplexer with a read-to-clear
   reason register, a write-to-enable register at `+0x10` and a write-to-disable
   register at `+0x18`. That block is the actual source of every device
   interrupt on this camera and would remain bespoke; it would simply drive
   `qemu_irq` 32 and 33 instead of `cpu_interrupt()`.
5. **Regression surface.** `eos_handle_intengine_gic` is shared by every DIGIC 7
   model (200D, 77D, 800D, 6D2, M5, M6, M100, SX740…) and the
   `cpu_interrupt`-based delivery is shared by *every* model back to DIGIC 2.
   A GIC swap touches machine init and all delivery paths for ~25 cameras that
   currently boot.

### 4.2 What the 6D2 firmware actually needs from a GIC

| GIC feature | used by 6D2 firmware? |
|---|---|
| `GICC_IAR` / `GICC_EOIR` | yes, on every interrupt, both cores |
| `GICD_ISENABLER` / `ICENABLER` | yes, for INTID 0x20, 0x21 and ids ≥ 0x1C0 |
| `GICD_ITARGETSR` (byte) | yes — written once for 0x20/0x21, **read back as a precondition** for enabling |
| `ICDSGIR` with explicit target list | yes — SGI 0xA and 0xD |
| spurious INTID `0x3FF` | yes — checked at ROM `0xE026ACC0` |
| priority / preemption | **no** — both SPIs get priority 16, `GICC_PMR = 0xFF`, no nesting via priority |
| binary point, running priority, active state | **no** |
| banked PPIs, private/global timers | **no** — zero references to `0xC1000200` / `0xC1000600` |
| more than 2 CPU interfaces | **no** |

### 4.3 Recommendation: **do not adopt `arm_gic.c`. Per-CPU-ise the existing code.**

Reasoning, in order:

1. The FIXME's premise is wrong for this machine. `arm_gic.c` would replace the
   *small* half of the problem (4 registers, 4 INTIDs) and leave the *large*
   half (the two Canon banks, 448 ids, the enable/disable/reason protocol)
   exactly as hand-written as it is now. The routing bug is in the Canon half.
2. The feature table above is a four-register subset. A faithful `arm_gic.c`
   gives priority preemption, active-state tracking and banked PPIs that this
   firmware never exercises — cost with no measurable return.
3. The blast radius is wrong-shaped: a ~60-line change confined to two functions
   versus a rewrite of the delivery path for 25 working camera models. The
   spike's own history (a 12-line patch removed a total interrupt refusal) says
   the marginal return on the next increment is high and the risk should stay
   low.
4. Nothing in the per-bank design forecloses `arm_gic.c` later. If a future
   DIGIC 8/X body turns out to use priority preemption or the A9 private timers,
   the Canon-bank code written here is exactly what would then drive
   `qemu_irq` lines instead of `cpu_interrupt()` — it is a prerequisite either
   way, not a detour.

**Revisit the FIXME if and only if** a model appears that (a) uses GIC priority
or preemption, (b) uses the A9 private/global timers, or (c) has more than two
cores. Leave the FIXME comment in place with that condition appended.

---

## 5. Concrete patch plan

Ordered so each step is independently testable. Steps 1–3 are the fix; 4–6 are
cleanups that should ride along because they are one line each.

### Step 0 — revert patch 0008 first

`patches/0008-qemu-eos-gic-pending-irq-fix.patch` (currently live at
eos.c:2884-2894) is **superseded**, not extended. Step 3 makes the `GICC_IAR`
read stop clearing `CPU_INTERRUPT_HARD` while the same core has a latched
device interrupt, so the re-assert becomes dead code that can only mask a
future regression. Remove those 12 lines as part of step 3 and drop 0008 from
the series (or supersede it with a new numbered patch that includes the revert).

**Risk: none.** The behaviour it provides is subsumed.

### Step 1 — per-bank Canon interrupt controller state

`hw/eos/eos.h:320-322`:

```c
-    uint32_t irq_enabled[INT_ENTRIES];
-    uint32_t irq_schedule[INT_ENTRIES];
-    uint32_t irq_id;
+    /* One Canon interrupt controller per core.  DIGIC 7: bank 0 = 0xD4011000,
+     * bank 1 = 0xD5011000 (eos.c handler table, parm 1 and 2).  Single-core
+     * models use bank 0 only.  Guest-side bank table: 6D2 ROM 0xE0835820. */
+    uint32_t irq_enabled[2][INT_ENTRIES];
+    uint32_t irq_schedule[INT_ENTRIES];   /* bank is re-derived at delivery */
+    uint32_t irq_id[2];
```

Also delete `OTHER_CPU` (eos.h:61) — unused and broken.

Add one helper next to `eos_trigger_int` (eos.c, just before line 2410):

```c
/* Which core owns interrupt `id`?  The one whose intengine bank enabled it:
 * DryOS writes the id to bank+0x1010 from the core that registers the handler
 * (6D2 ROM 0xE026AD1C: cpu = *(uint32_t *)0x1008; ROM 0xE01E4DC6). */
static int eos_irq_bank(int id)
{
    return (eos_state->cpu1 && eos_state->irq_enabled[1][id]) ? 1 : 0;
}
```

**Risk: MEDIUM-LOW.** Mechanical, but it touches every `irq_enabled` /
`irq_id` reference, i.e. every camera model. The compiler catches all of them
(array rank change). `INT_ENTRIES` is 0x200, so the struct grows 2 KiB — no
issue.

### Step 2 — deliver to the owning bank, not to `CURRENT_CPU`

`eos_trigger_int`, eos.c:2436-2455:

```c
+    int bank = eos_irq_bank(id);
-    if(!delay && eos_state->irq_enabled[id] && !eos_state->irq_id)
+    if(!delay && eos_state->irq_enabled[bank][id] && !eos_state->irq_id[bank])
     {
         …
-        eos_state->irq_id = id;
-        eos_state->irq_enabled[eos_state->irq_id] = 0;
-        cpu_interrupt(CPU(CURRENT_CPU), CPU_INTERRUPT_HARD);
+        eos_state->irq_id[bank] = id;
+        eos_state->irq_enabled[bank][id] = 0;
+        cpu_interrupt(CPU(eos_state->cpus[bank]), CPU_INTERRUPT_HARD);
     }
     else
     {
         …
-        if(!eos_state->irq_enabled[id]) delay = 1;
+        if(!eos_state->irq_enabled[bank][id]) delay = 1;
```

`eos_interrupt_timer_body`, eos.c:973-1013 — identical transformation at lines
980, 1001, 1002, 1004.

**Risk: MEDIUM.** This is the behaviour change with real teeth: interrupts that
today land on whichever vCPU was executing will now always land on core 0
(bank 0) unless bank 1 enabled them. That is what the hardware does (§3), and
it makes delivery deterministic — which is the point — but it will change vCPU
scheduling patterns on every dual-core model. Watch the 200D, which is the
other well-tested D7 target.

### Step 3 — per-CPU GIC CPU interface

`eos_handle_intengine_gic`, eos.c:2815-3008.

**3a. State** (eos.c:2825):

```c
-    static int iar = 0x20;
+    static int iar[2] = {0x20, 0x20};   /* pending SGI per CPU interface, 0x20 = none */
+    int cpu = current_cpu ? current_cpu->cpu_index : 0;
+    assert(cpu < 2);
```

**3b. `GICC_IAR` read** (eos.c:2852-2903) — replace the whole body:

```c
case 0x0C:
{
    msg = "GICC_IAR";
    if (type & MODE_READ)
    {
        if (iar[cpu] != 0x20)
        {
            /* an SGI we raised in the ICDSGIR case below */
            ret = iar[cpu];
            /* Only drop the CPU line if this core has nothing else pending.
             * A device interrupt (irq_id[cpu]) is on the same
             * CPU_INTERRUPT_HARD line and must survive the SGI ack. */
            if (!eos_state->irq_id[cpu])
                cpu_reset_interrupt(CPU(eos_state->cpus[cpu]), CPU_INTERRUPT_HARD);
        }
        else if (eos_state->irq_id[cpu])
        {
            /* 6D2 ROM 0xE026ABE2..0xE026ABFE: INTID 0x20/0x21 means
             * "read the reason register of bank (INTID & 1)". */
            ret = 0x20 + cpu;
        }
        else
        {
            ret = 0x3FF;   /* spurious; ROM 0xE026ACBA returns immediately */
        }
    }
    else
    {
        ret = 0x20;
    }
    break;
}
```

The re-assert block from patch 0008 disappears here.

**3c. `GICC_EOIR` write** (eos.c:2910): `iar = 0x20;` → `iar[cpu] = 0x20;`

**3d. `ICDSGIR` write** (eos.c:2973-2996) — replace:

```c
case 0xf00:
{
    msg = "ICDSGIR";
    if (type & MODE_WRITE)
    {
        int sgi_id = value & 0xF;
        int filter = (value >> 24) & 3;          /* TargetListFilter */
        int list   = (value >> 16) & 0xFF;       /* CPUTargetList    */
        int targets = (filter == 1) ? (~(1 << cpu) & 3)   /* all except self */
                    : (filter == 2) ? (1 << cpu)          /* self only      */
                    :                 list;               /* explicit list  */
        /* ponytail: one pending SGI slot per CPU interface, newest wins.
         * The 6D2 uses SGI 0xA (ROM 0xE00D9C54) and 0xD (ROM 0xE0093184);
         * upgrade to a per-CPU pending bitmap if a collision is ever
         * observed in a -d int trace. */
        for (int t = 0; t < 2; t++)
        {
            if (!(targets & (1 << t)) || !eos_state->cpus[t]) continue;
            iar[t] = sgi_id;
            cpu_interrupt(CPU(eos_state->cpus[t]), CPU_INTERRUPT_HARD);
        }
    }
    break;
}
```

This also removes L1 (`type && MODE_WRITE`), L2 (`MMIO_VAR(enabled[target_int])`)
and L5 (missing `break`).

**Risk: the `0x3FF` return in 3b is the single highest-risk line in this plan.**
Today the handler returns `0x20` unconditionally; every D7/D8 model's IRQ
dispatcher therefore always takes the "read the bank reason register" path.
Returning `0x3FF` when nothing is pending is spec-correct and matches ROM
`0xE026ACC0`, but it is a behaviour change for models nobody re-tests here.
**Fallback if any other D7/D8 model regresses:** return `0x20 + cpu`
unconditionally instead of `0x3FF` — that is bug-compatible with today for
core 0 and still fixes core 1. Try `0x3FF` first; it is the one that stops
bogus dispatches of handler-table entry 0.

Everything else in step 3 is low risk: `iar[2]` and the SGI target decode are
strictly more correct and, on a 2-core machine with `filter == 0`, the target
decode reproduces today's "kick the other CPU" behaviour exactly.

### Step 4 — decode the core-1 Canon bank

`eos_handle_intengine`, eos.c:2713-2810. Derive the bank from the `parm` the
handler table already passes and stop ignoring it:

```c
+    /* eos.c handler table: parm 2 = D7 CPU1, 5 = DX CPU1, 9 = D8 CPU1 */
+    int bank = (parm == 2 || parm == 5 || parm == 9) ? 1 : 0;
```

Then add the missing case labels and index by bank:

- reason register (2720-2752): add `case 0xD5011000:` (and, for consistency,
  `0xD0231000`, `0xD233A000`). Replace `eos_state->irq_id` with
  `eos_state->irq_id[bank]` at 2736, 2737, 2738, 2741, and make 2742
  `cpu_reset_interrupt(CPU(eos_state->cpus[bank]), CPU_INTERRUPT_HARD)` —
  **only if `bank == cpu`**, otherwise it is a cross-core reset; assert equality
  instead, because the firmware only ever reads its own bank.
- enable register (2754-2782): add `case 0xD5011010:` (+ `0xD0231010`,
  `0xD233A010`), `eos_state->irq_enabled[bank][value] = 1;` at 2763.
- **new: disable register.** Add `case 0xD4011018: case 0xD5011018:` →
  `eos_state->irq_enabled[bank][value] = 0;` (ROM `0xE01E4DF6`). Today
  disables are silently dropped.
- reset register (2784-2802): add `case 0xD5011200:` (+ siblings), index
  `irq_id[bank]` at 2794 and `cpus[bank]` at 2795.

**Risk: LOW-MEDIUM.** Purely additive for single-core models (`bank` is always
0, every existing case label unchanged). The new `+0x18` disable case is the
only place where a previously-ignored guest write starts taking effect — if a
model regresses, that is the first thing to disable.

### Step 5 — one-line correctness cleanups (optional, take them)

- eos.c:2941 `MMIO_VAR(enabled[word]);` → set-semantics on write:
  `if (type & MODE_WRITE) enabled[word] |= value; else ret = enabled[word];`
- eos.c:2627-2646 — correct the `eos_handle_multicore` comments: the region is a
  **PL310 L2 cache controller**, `0x100` is L2 Control (not "Wake Up CPU1"),
  `0x214` is the L2 Interrupt Mask (not "Signal to CPU1"), `0x730`/`0x77C`/
  `0x7B0` are clean/invalidate operations. Behaviour unchanged.
- eos.c:2814 — keep the FIXME, append the condition from §4.3.

**Risk: none** (comments) / **LOW** (the `|=`, since `enabled[]` is unused).

### Step 6 — the one runnable check

Non-trivial branch logic (bank selection, IAR arbitration) needs one cheap
assertion that fails loudly if the model and the firmware disagree. Put it in
the `GICD_ISENABLER` write path, gated on DIGIC 7:

```c
/* The 6D2/200D-class firmware programs GICD_ITARGETSR before enabling
 * (ROM 0xE00D9AA0 refuses otherwise): SPI 0x20 -> core 0, 0x21 -> core 1.
 * If a model ever differs, the bank routing in eos_irq_bank() is wrong. */
if (eos_state->model->digic_version == 7 && word == 1 &&
    (target[0x20] != 1 || target[0x21] != 2))
{
    fprintf(stderr, "[GIC] unexpected ITARGETSR: 0x20=%d 0x21=%d "
                    "(expected 1 and 2) -- bank routing may be wrong\n",
                    target[0x20], target[0x21]);
}
```

A warning rather than an `assert` so an unfamiliar model degrades instead of
aborting. This is the whole test: it fires if and only if the assumption this
design rests on stops holding.

---

## 6. Predictions and the discriminating measurement

### 6.1 The one measurement that decides the shape of the residual stall

**Count `0xD5011010` writes over a full boot.** Two `fprintf`s in step 4 (bank
and id on every enable) plus `-d io` is enough; no new tooling.

| result | meaning | consequence |
|---|---|---|
| **zero** `0xD5011010` writes | DryOS registers no interrupt on core 1 during this boot. Bank 1 exists but is never armed. | The per-bank work is correctness/determinism only. The residual stall at `DbgMgr [PM] Enable` is **not** a dropped core-1 interrupt, and will not clear. Go straight to the MPU/GUI-spell thread. |
| **non-zero** | a whole class of interrupts is currently undeliverable (defect B5) | Expect real forward progress. Re-measure the boot ceiling immediately. |

Based on §3 (zero core-1 ISRs in 6534 lines of real-hardware log) the honest
prior is **zero**, i.e. expect this fix to remove nondeterminism and a
correctness hazard, not to move the boot ceiling. Stating that up front is more
useful than discovering it after the patch.

### 6.2 What will change

| # | prediction | how to see it |
|---|---|---|
| P1 | Cross-core `iar` consumption becomes impossible. The evening session's **nondeterministic** stall class (1-in-N `GlobalVectorInit` hang, "continuous SGI 0xa ping-pong") cannot recur. | Stress-boot loop, ≥20 runs, plus `-accel tcg,thread=single` vs default MTTCG. Pre-fix, the evening session saw it once in a handful of runs; post-fix, zero in 20. |
| P2 | Device interrupts stop landing on a random core. 100 % of deliveries go to core 0 unless bank 1 armed them. | `-d int` with a core tag on each `trigger int` line. |
| P3 | Guest `disable_interrupt()` starts working (defect B6). | Count `0xD?011018` writes; each should now clear an enable. |
| P4 | Core 1 will, for the first time, be able to receive `GICC_IAR == 0x21`. | Grep the trace for `iar: 0x21`. Expect **zero occurrences** if 6.1 is zero — that is consistent, not a failure. |
| P5 | SGI target-list decoding becomes correct. On a 2-core machine with `filter == 0` this reproduces current behaviour exactly. | No visible change expected. Stated so it is not read as a fix. |

### 6.3 What will **not** change

| # | prediction | why |
|---|---|---|
| N1 | The boot ceiling stays at `nfcmgrstate_Initialize:ce_init` → `DbgMgr [PM] Enable (ID = 10, cnt = 0/1)`, ~473 stderr lines — **if 6.1 returns zero**. | Both recorded stall PCs are ordinary idle loops, not deadlocks. See N2/N3. |
| N2 | CPU0 will still be found at `0xE02C6100`. | That is the **PowerMgr idle loop** `0xE02C608C`–`0xE02C6106`: `while (!*(state)) ;` then `cli`, then `mode==1 → wfi` at `0xE02C60FE`, then restore CPSR at `0xE02C6100` and loop. Identified by its own literals `"[PM] pmSelfRefresh : In"` (`0xE02C61D0`) and the task name `"PowerMgr"` (`0xE02C6208`). PSR `600000F3` (I=1) is the in-critical-section state, which is normal — WFI wakes regardless of the I bit. |
| N3 | CPU1 will still be found at `0xE00D97E0`. | `0xE00D97DE` is `wfi`, `0xE00D97E0` is `b .-2`. PSR `40000073` has **I=0**, so an interrupt *is* taken from here, the vector runs, and `rfe` returns to `0xE00D97E0`. This is core 1's healthy idle park, not a wedge. |
| N4 | Missing GUI-stage MPU dialogue (no 6D2 button codes, the unknown reply `08 06 01 a7 00 01`) is untouched. | Different subsystem. |
| N5 | The `I2C_Read[CH3] : 0xa8,…` from `NFCMgr` still has no backing model. | eos.c:614 registers I2C only at `0xC0090000`, a DIGIC ≤5 address. There is no D7 I2C handler. |
| N6 | The `EstimatedSize` / `RscMgr` soft assert (spike 001) is unrelated and unaffected. | Established in spike 001. |

### 6.4 Distinguishing "GIC still broken" from "GIC fine, starved of data"

Run post-fix with `-d int,verbose`, sample `info registers -a` every 5 s for
60 s past the last debugmsg, and read these five signals **in order**. The first
three are decisive on their own.

| # | signal | "GIC still broken" | "GIC fine, waiting on missing MPU/GUI data" |
|---|---|---|---|
| 1 | `Taking exception 5 [IRQ]` events in the 60 s after the last debugmsg | **0** — nothing is being delivered | **non-zero and still climbing at the last sample**. Measured baseline for the rate: the pre-fix trace fired `trigger int 0x28` 60 times over that same 60 s window, i.e. ~1 Hz, so expect at least tens. The absolute count matters less than "still increasing". |
| 2 | ratio of `[EOS] trigger int` lines to `Taking exception 5 [IRQ]` lines | ≫ 1, or every line tagged `(delayed!)`. Pre-fix baseline for the **whole run**: 60 × `trigger int 0x28` vs 19 × `Taking exception 5` total. | ≈ 1 : 1 |
| 3 | `irq_id[0]` / `irq_id[1]` sampled at the stall (add a monitor print or a `-d int` dump) | **non-zero and never returning to 0** — the latch is stuck and gating everything (this was exactly the pre-0008 failure) | **0 between interrupts** |
| 4 | CPU1 PC across all samples | anything other than `0xE00D97DE`/`0xE00D97E0`, or pinned mid-ISR | `0xE00D97DE` / `0xE00D97E0` (`wfi; b .-2`), varying between the two |
| 5 | CPU0 PC across all samples | pinned at a single non-idle PC, or inside an ISR | inside `0xE02C608C`–`0xE02C6106` (PowerMgr idle), and observed to move between samples |

**The single number to report:** signal 1 — IRQ exceptions taken per core in the
60 s window after the last debugmsg. Non-zero and steady on core 0 means the
interrupt system is alive and the guest is blocked on data, which retires the
GIC from this investigation and hands the thread to the MPU/button-code work.
Zero means the GIC is still the problem and steps 1–4 above did not finish the
job.

Note that the existing evidence file
`evidence/2026-08-15-night-stockint.txt` already gives the pre-fix baseline for
signal 1 (0 deliveries / 60 refusals of `0x28` after log line 438) and
`evidence/2026-08-15-night-runs.txt` gives the register samples for signals 4
and 5. **No equivalent post-0008 capture exists yet** — the only recorded
post-fix observation is "473 stderr lines, same stall point", with no register
sampling and no interrupt counts. Capturing signals 1 and 3 against the
*current* tree, before implementing any of this, is the cheapest next action
and may retire the whole plan.

---

## 7. Things this document could not establish

1. **Whether any interrupt is enabled on bank 1 during a 6D2 boot.** It requires
   running the emulator, which this task excluded. §6.1 is the measurement.
2. **Whether the residual stall is MPU-related.** The last messages before the
   stall are `NFCMgr` doing `I2C_Read[CH3] : 0xa8,…` → `nfcmgrstate_Initialize
   ce_init`. On real hardware (`tools/6D2-DEBUGMSG-body.txt` lines 1372-1419)
   the next events are `CSMgrTask` `SDEventHandler(ID=1:Event=8)`, `SDPowerOn`,
   `SD_DeviceCreate`, `sdIdentifyDrive Start`, plus `CE_Main` PM traffic. So the
   candidate blockers are the unmodelled D7 I2C block **and** the SD/CSMgr
   event chain — not established, and not the same subsystem as the GIC.
3. **Whether `*(uint32_t *)0x1008` (the per-core id DryOS reads at ROM
   `0xE026AD22`) is a per-core MMU mapping of the same virtual address.** Both
   cores use the literal address `0x1000` for their interrupt-context block
   (ROM `0xE026AA78`, `0xE026AC0C`). If it is one shared page, DryOS's ISR
   bookkeeping is genuinely shared and the emulator's `current_task_addr = 0x28`
   is ambiguous per core. Not investigated; it does not affect this plan, but it
   would affect any future per-core task-name work.
4. **Post-0008 register/interrupt-count evidence.** None was captured. §6.4
   names exactly what to capture.
