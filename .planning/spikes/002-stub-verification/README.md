---
spike: 002
name: stub-verification
type: standard
validates: "Given platform/6D2.111/stubs.S, when each address is checked against roms/6D2/ROM1.BIN, then every stub resolves to a plausible function entry rather than a wrong or guessed address"
verdict: PARTIAL
related: [004]
tags: [rom, stubs, reversing]
---

# Spike 002: Stub Verification Against the Real ROM

## What This Validates

**Given** the stub table in `ml/platform/6D2.111/stubs.S`,
**when** every address is cross-checked against the actual dumped ROM
(`roms/6D2/ROM1.BIN`, and `ROM0.BIN` where relevant),
**then** each stub either resolves to a plausible ARM/Thumb function entry point
or is flagged as wrong, stale, or never-verified.

`platform/6D2.111/README.txt` admits the port "has never been tested on a real
cam." Wrong stubs are the most likely cause of both the QEMU failures and any
future crash on the body. This produces the evidence base for Phase B's
"stub missing / wrong" classification — and it is pure static analysis, so it
carries zero risk to the camera.

## Research

Ground truth already established about the ROMs:

- `ROM0.BIN` = 32 MiB, maps to `0xE0000000-0xE1FFFFFF`
- `ROM1.BIN` = 16 MiB, maps to `0xF0000000-0xF0FFFFFF`
- DryOS marker `akashimorino` present; version string `1.1.1`
- `FIRMWARE_ID 0x80000406`
- Valid Thumb-2 code at file offset `0x40000`, which corresponds to the
  Makefile's `MAIN_FIRMWARE_ADDR 0xE0040000`

So: file offset = address − 0xE0000000 for ROM0, − 0xF0000000 for ROM1.

## How to Run

Static analysis only — no emulator, no camera. Use the ARM toolchain from
`shell.nix` (`arm-none-eabi-objdump`) plus direct byte inspection.

## What to Expect

A per-stub verdict table: address, symbol, which ROM it lands in, whether the
bytes there look like a function prologue, and a confidence rating.

## Investigation Trail

Pure static analysis. The ROMs were opened read-only; no bytes were copied out
of `roms/`.

### 1. Read the macros before trusting any address

[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/include/stub.h](ml/include/stub.h)
defines four macros, and they are not interchangeable:

- `THUMB_FN(addr,name)` → `name = (addr) | 1` — bit 0 is *forced on*. Several
  6D2 entries are written even (`0xdf007b58`) and still resolve to the odd Thumb
  address. Comparing raw literals across platforms without normalising bit 0
  produces false differences.
- `ARM32_FN(addr,name)` → `(addr) & ~3` — unused in the 6D2 table.
- `NSTUB` / `DATA_PTR` → raw address, no bit-0 fixup.

Every subsequent check masks bit 0 before computing a file offset, and re-adds
it when matching against reference sets.

### 2. Region map — the spike premise was slightly wrong

161 stub lines parsed (156 active, 5 commented out). Classified by address:

| Region | Count | Backing |
|---|---|---|
| `0xE0000000–0xE1FFFFFF` | 102 | ROM0.BIN, offset = addr − 0xE0000000 |
| `0xDF000000–0xDF00FFFF` | 30 | DryOS kernel image (see step 4) |
| `0x00000000–0x3FFFFFFF` | 28 | DRAM (1 GiB per qemu `model_list.c`) |
| `0xF0000000–0xF0FFFFFF` | **0** | ROM1.BIN |
| unmapped | 1 | — |

**No stub lands in ROM1.** The spike brief framed this as "checked against
`ROM1.BIN`"; in fact ROM1 is irrelevant to the stub table. Everything is ROM0,
DRAM, or the kernel image.

### 3. Four independent plausibility signals, not one

A "looks like a prologue" test alone is weak — many DryOS leaf functions start
with `mov`, `ldr [pc]`, or `cmp`. Four signals were computed per stub instead:

- **P — prologue.** First instruction disassembled by `arm-none-eabi-objdump
  -Mforce-thumb` at the stub's own VMA matches `push` / `stmdb sp!` / `sub sp`.
- **B — call target.** A 2-byte-granular scan of all of ROM0 decoding Thumb-2
  `BL`/`BLX(imm)` (`hw1 ∈ F000–F7FF`, `hw2 ≥ D000`) and computing the
  sign-extended J1/J2 target. If *nothing anywhere in 32 MiB* branches-and-links
  to an address, that address is not an entry point anybody calls.
- **F — function pointer.** The exact address (odd or even) appears as a 4-byte
  aligned literal somewhere in ROM0 or ROM1 — i.e. a literal pool or a jump
  table holds it.
- **E — entry boundary.** The two halfwords *preceding* the stub terminate a
  function: `bx lr`, `pop {…,pc}`, `ldmia.w sp!,{…,pc}`, `b.n`, `b.w`, or
  alignment padding. This is what rescues the leaf functions that fail P.

### 4. Dead end, then the key discovery: locating the `0xDF000000` image

30 stubs sit at `0xDF00xxxx`. qemu-eos declares that as `ram_extra[0]` — plain
RAM — so at first it looked unverifiable, and worse, **every one of those 30
addresses is byte-identical to
[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/platform/200D.101/stubs.S](ml/platform/200D.101/stubs.S)**,
which reads like copy-paste.

Dead ends tried first:

- Assuming the image is at ROM0 offset `0x30000` because that 64 KiB bucket
  holds 162 dwords in `0xDF00xxxx` range. Wrong: that region is ASCII `f`
  padding plus two disjoint blocks with multi-KiB zero gaps, and the stub
  offsets landed on zeros.
- Correlating `SystemIF::Ker*.c` string offsets against kernel-range dwords to
  solve for a base. Too noisy — top candidates were 18-19 votes and mutually
  inconsistent.
- Searching for the copy loop: `mov.w rX,#0xDF000000` (5 hits, none a copier)
  and the dword `0xDF000000` (zero occurrences in either ROM).

What worked was a byproduct of one of those searches. 82 `movt rX,#0xDF00`
instructions cluster at ROM0 `0x43A000–0x43B000`, and the same region is full of
the ARM word `E51FF004` (`ldr pc,[pc,#-4]`) followed by a target address.
**That is Canon's veneer table at `0xE043A000`** — 1336 entries, every one a
genuine external call target: 237 into the kernel image, 891 into DRAM code, 99
back into ROM0.

That table yields 208 distinct kernel entry points. Brute-forcing a base offset
`B` such that `B + (addr − 0xDF000000)` lands on a `push`-class opcode for as
many of those 208 as possible gave one overwhelming winner:

**The DryOS kernel image is stored at ROM0 file offset `0x0100553C`
(address `0xE100553C`) and is mapped to `0xDF000000` at run time.**

146 of 208 entry points hit a prologue at that base; the runner-up scored 17.
Confirmed independently: `"SystemIF::KerQueue.c"` sits at ROM0 `0x010108F8`,
which under that mapping is kernel address `0xDF00B3BC` — and the four
`msg_queue_*` stubs are at `0xDF00B1D9`–`0xDF00B615`, right around it.
`"KerRLock.c"` maps to `0xDF00B5BE`, with the three `*RecursiveLock` stubs
adjacent. With the base known, all 30 kernel stubs became byte-verifiable.

So the 200D-identical addresses are **not** copy-paste error: the 6D2 ships the
same DryOS kernel binary, and the addresses check out against the 6D2's own ROM.

### 5. The same trick does not work for DRAM code

161 veneer targets fall in `0x20000–0x34000` — the relocated DRAM code holding
`shamem_read`, `_request_RPC`, `clear_RPC_request`. Running the identical
brute-force against them produced no base above noise (best 14/161). That code
is not stored verbatim in either ROM — it is built, relocated, or unpacked at
boot. Those three stubs are therefore verified only by their presence in the
veneer table, which is still strong evidence of a real function entry.

### 6. Spot checks where the comment makes a claim

- `change_mmu_tables` (`0xe04dcad2`) — comment says "Updates TTBRs and does TLB
  maintenance". The bytes: `mov.w r3,#0x55555555; mcr p15,0,r3,c3,c0,0` (DACR),
  `mcr c2,c0,{0,1}` (TTBR0/TTBR1), `mcr c13,c0,1` (CONTEXTIDR), `mcr c2,c0,2`
  (TTBCR). Exact match.
- `dcache_clean` (`0xe06b07a4`) — comment says "loop with MCR p15 c7,c10,1;
  DSB". The bytes: `dsb sy` then a `bic #31` / `mcr c7,c10,1` / `add #32` loop.
  Exact match.
- `icache_invalidate` (`0xe06b0878`) — `mcr c7,c5,1` loop. Match.
- `init_task` (`0xe0040225`) — appears verbatim in `cstart`'s own literal pool
  at `0xe00401dc`, which is the strongest possible confirmation.
- `gui_main_task` (`0xe00dc2ae`) — its second call is `bl 0xe0093578`, which is
  exactly the `gui_init_end` stub. The two stubs corroborate each other.

Scratch scripts (outside the workspace):
/tmp/claude-1000/-home-chris-Vibe-Coding-6D-Mark-II-Magic-Lantern-6D2/7fd303d5-2f0f-4650-82c5-e334e473a37f/scratchpad/ —
`verify_stubs.py` (parse + 4-signal pass), `analyse.py` (boundary test,
cross-platform diffs), `kernel_check.py` (kernel image verification),
`dis.sh` / `disoff.sh` (objdump wrappers).

## Results

### Summary by category

| Category | Count | Verdict |
|---|---|---|
| ROM0 code stubs (`0xE0…`) | 102 | **all plausible** — every one lands on a function entry |
| Kernel code stubs (`0xDF00…`) | 30 | **all plausible** — image located at ROM0 `0x0100553C` |
| DRAM code stubs (`THUMB_FN`, low addr) | 3 | **plausible** — all three are veneer-table targets |
| DRAM data pointers (`DATA_PTR`/`NSTUB`) | 25 | **unverifiable by static ROM analysis** |
| Out of range | 1 | **`LCD_Palette`** — see below |
| **Total stub lines** | **161** | 156 active, 5 commented out |

Zero stubs point at zeros, `0xFF` padding, or past the end of a ROM.

135 stubs are code (102 ROM0 + 30 kernel + 3 DRAM); 26 are data or placeholder.
**Evidence strength across the 132 ROM-backed code stubs.** ROM0 signals are
P=prologue, B=BL target, F=function pointer in a literal pool, E=preceded by a
function terminator. Kernel signals are P, E, V=ARM veneer-table target,
F=kernel pointer in a literal pool.

| Signals | ROM0 | Kernel |
|---|---|---|
| 4 of 4 | 31 | 19 |
| 3 of 4 | 52 | 8 |
| 2 of 4 | 16 | 2 |
| 1 of 4 | 3 | 1 |
| 0 of 4 | **0** | **0** |

### The one hard finding: `LCD_Palette` is out of range

```
NSTUB(0x56500000,  LCD_Palette)   // stubs.S:265
```

`0x56500000` is not in DRAM (1 GiB, `0x00000000–0x3FFFFFFF`), not in ROM0, not
in ROM1, and not in the MMIO window (`0xBFE00000–0xDEFFFFFF`). It is
**unmapped**. The stub's own comment admits it — *"SJE FIXME fake address in
safe writable region"* — and the value is copied verbatim from the 200D, where
it is equally out of range (that camera has only 512 MiB). It appears nowhere in
either ROM. Any code path that writes an indexed palette through this symbol
will fault on real hardware. This is a placeholder, not an address.

### Code stubs resting on the weakest evidence

All were manually disassembled and all are genuine function entries, but they
carry fewer corroborating signals, so re-check these first if the port
misbehaves.

| Address | Symbol | Signals | First instruction |
|---|---|---|---|
| `0xe06b0878` | `icache_invalidate` | -B-- | `cmp.w r1, #0x4000` |
| `0xe01cdac6` | `set_mem_to_mem_cbr` | ---E | `ldr r2, [pc, #168]` |
| `0xe04dcad2` | `change_mmu_tables` | ---E | `mov.w r3, #0x55555555` |
| `0xe0040000` | `firmware_entry` | --FE | Thumb reset vector (`NSTUB`, no bit 0) |
| `0xe00400fd` | `cstart` | P--E | `push {r4, r5, r6, lr}` |
| `0xe06b07a4` | `dcache_clean` | -BF- | `dsb sy` |
| `0xe00d9ccc` | `dcache_clean_multicore` | -B-E | `bic.w r2, r0, #31` |
| `0xe01cdb22` | `lock_and_wake_mem_to_mem` | -B-E | `ldr r0, [pc, #76]` |
| `0xe01cdb46` | `unlock_and_sleep_mem_to_mem` | -B-E | `ldr r0, [pc, #40]` |
| `0xe01cdad0` | `set_default_mem_to_mem_cbr` | -B-E | `ldr r1, [pc, #156]` |
| `0xe01cda22` | `mem_to_mem_setup_copy` | PB-- | `push {r4, r5, lr}` |
| `0xe04e69fe` | `FIO_FindClose` | P--E | `push {r3, r4, r5, lr}` |
| `0xe00dc2ae` | `gui_main_task` | --FE | `ldr r1, [pc, #988]` |
| `0xe015fc9c` | `cli_spin_lock` | -BF- | `mov r2, r0` |
| `0xe032c222` | `gui_change_mode` | P--E | `stmdb sp!, {r1…r9, lr}` |
| `0xe032a9c8` | `gui_massive_event_loop` | P--E | `stmdb sp!, {r0…r9, lr}` |
| `0xe009a074` | `gui_init_event` | P--E | `stmdb sp!, {r4…fp, lr}` |
| `0xe066afcc` | `AllocateContinuousMemoryResource` | PB-- | `stmdb sp!, {r4…r8, lr}` |
| `0xdf008f0b` | `task_create_ex` | P--E | `push {r4…r7, lr}`; no external reference |
| `0xdf009338` | `vsnprintf` | P--E | `stmdb sp!, {r0…r7, …}`; no external reference |
| `0xdf0031a3` | `get_task_by_id` | ---E | `mov r1, r0`; no external reference |
| `0xdf00325d` | `task_trampoline` | P-FE | `push {r3, r4, r5, lr}`; not a veneer target |

`copy_mmu_tables` (`0xe0013b58`, P--E, commented out) and
`fsuDecodePartitionTable` (`0xdf00d365`, veneer target, commented out with a
"wrong — doesn't exist on 6D2" note) both resolve to real function entries
despite being disabled.

### DRAM data pointers — the real blind spot (25 stubs)

`DATA_PTR`/`NSTUB` entries below `0x40000000` are RAM addresses that only exist
once DryOS has initialised. Nothing in a ROM dump can confirm them. The weakest
proxy available is whether the exact 32-bit value appears as an aligned literal
in either ROM. **Six have zero such references:**

| Address | Symbol | Note |
|---|---|---|
| `0x4030` | `pre_isr_hook` | read by the kernel image, plausible |
| `0x65a0c` | `isr_table_param` | likely reached as `isr_table_handler + 4` |
| `0x7c08` | `mpu_send_ring_buffer_tail` | neighbours resolve, this one does not |
| `0xea8c` | `LiveViewApp_dialog` | likely stored via `base + offset` |
| `0x100cc` | `display_refresh_needed` | neighbours `0x100b4/b8/bc` all resolve |
| `0x100d8` | `display_output_mode` | same struct, no direct reference |

The remaining 19 do appear as literals (`gui_main_struct` 43×, `current_interrupt`
29×, `gui_task_list` 12×), which is weak positive evidence only. All 25 need
runtime confirmation — spike 004 is the natural place.

### Missing relative to 5D3.113

5D3.113 has 130 active stubs, 6D2.111 has 156. After matching underscore
variants (`LoadCalendarFromRTC`/`_LoadCalendarFromRTC`,
`get_task_info_by_id`/`_get_task_info_by_id`, both present on 6D2), **34 5D3
symbols have no 6D2 equivalent**, in four functional clusters:

**EDMAC — 10 missing.** `SetEDmac`, `StartEDmac`, `AbortEDmac`,
`ConnectReadEDmac`, `ConnectWriteEDmac`, `RegisterEDmacCompleteCBR`,
`RegisterEDmacAbortCBR`, `RegisterEDmacPopCBR`, and the three `Unregister*`
counterparts. Deliberate — stubs.S line 76 says *"This is a trimmed set of
stubs… the minimal required to support raw video, using
mem_to_mem_edmac_copy()"*. Referenced by 5–10 ML source files each. This is the
ceiling on raw-video work.

**Audio — 11 missing.** `_audio_ic_read`, `_audio_ic_write`, `SetAudioVolumeOut`,
`SetSamplingRate`, `PowerAudioOutput`, `StartASIFDMAADC`, `StartASIFDMADAC`,
`StopASIFDMADAC`, `SetNextASIFADCBuffer`, `SetNextASIFDACBuffer`, and the
matching abort. No audio metering or level control is possible without these.

**Engio — 2 missing.** `_engio_write`, `_EngDrvOut`. These are the register-poke
primitives behind FPS override and most LV tweaks. Their absence constrains
spike 003's "cheap wins" scope directly.

**Assorted — 11 missing.** `ptp_register_handler`, `dialog_set_property_str`,
`camera_engine`, `FSUunMountDevice`, `cf_device_ptr` (N/A — 6D2 has no CF slot),
`GUI_SetRollingPitchingLevelStatus`, `HideUnaviFeedBack_maybe`,
`LiveViewLevelApp_handler`, `LiveViewWbApp_handler`,
`terminateAbort_save_settings`, `terminateShutdown_save_settings`.

Conversely the 6D2 table has 61 symbols the 5D3 lacks — the DIGIC 6/7/8
additions (`XimrExe`, `RefreshVrmsSurface`, `change_mmu_tables`, `_request_RPC`,
the `mem_to_mem_*` family, `memcpy_dryos`).

### Hygiene issues found in passing

- **Duplicate definitions.** `CreateResLockEntry` (lines 78 and 233) and
  `LockEngineResources` (lines 80 and 234) are each defined twice. The values
  agree, so the assembler accepts it, but the second copy is dead weight.
- **Wrong version in a header comment.**
  [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/platform/6D2.111/internals.h](ml/platform/6D2.111/internals.h)
  opens with *"Camera internals for 6D2 1.0.5"* while the platform directory and
  the verified ROM are 1.1.1. Cosmetic, but misleading during triage.
- **200D inheritance is real but legitimate.** 144 symbols exist in both tables;
  39 share an address. 29 of those are the shared DryOS kernel image (correct),
  6 are small DryOS DRAM globals (plausible), and the 4 ROM0 ones are
  `firmware_entry`, `cstart`, `init_task` (all three independently confirmed
  against the 6D2 ROM) plus the fake `LCD_Palette`. The other 106 addresses
  differ — this table is genuine reversing work, not a clone.

### Verdict: PARTIAL

The hypothesis — *every stub resolves to a plausible function entry rather than
a wrong or guessed address* — holds completely for executable code and fails on
two counts elsewhere:

- **Validated:** all 135 code stubs (102 ROM0 + 30 kernel + 3 DRAM) resolve to
  real function entry points. None points at data, padding,
  zeros, or out of range. Wrong stubs are **not** the explanation for the QEMU
  failure in spike 001, and Phase B should not expect a large "stub wrong"
  bucket.
- **Invalidated:** `LCD_Palette` = `0x56500000` is unmapped on this body and is
  an acknowledged placeholder.
- **Not testable:** 25 DRAM data pointers (16 % of the table) cannot be reached
  by any static ROM method; 6 of them have no supporting reference at all.

Follow-on: the kernel image base `0xE100553C → 0xDF000000` is reusable ground
truth — record it wherever the ROM layout facts live, and use it to disassemble
DryOS directly rather than borrowing 200D addresses.
