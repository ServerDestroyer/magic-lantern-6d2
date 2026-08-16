# qemu-eos upstream submission plan

Target repo: `reticulatedpines/qemu-eos`, branch `qemu-eos-v4.2.1`, base commit
`4b667a1d3c` ("run_qemu: update location for disk image files") — the local
clone's HEAD, confirmed by `git remote -v` / `git log --oneline -3`.

Everything below was reconstructed **without touching the shared `qemu-eos/`
working tree**: no commits, no branches, no stash, no index writes. The split
was verified by extracting `HEAD` with `git archive` into a scratch directory
and applying the four proposed patches there in order.

---

## 1. The split

Five candidate changes exist. The recommendation is **four PRs, five commits,
one deliberate exclusion**.

| PR | Commits | Files | Upstream? |
|---|---|---|---|
| **Q1** | 1 | `hw/eos/mpu_spells/outils.py` | yes — already drafted |
| **Q2** | 2 | `hw/eos/mpu_spells/6D2.h` (new), `hw/eos/mpu.c`, `magiclantern/cam_config/6D2/debugmsg.gdb` | yes |
| **Q3** | 1 | `hw/eos/mpu_spells/button_codes.h`, `hw/eos/mpu.c` | yes, with caveats stated |
| **Q4** | 1 | `hw/eos/eos.c`, `hw/eos/eos.h`, `hw/eos/dbi/logging.c` | yes — core change, needs maintainer testing |
| — | — | `magiclantern/cam_config/6D2/debugmsg.gdb` EstimatedSize hunk | **no — obsoleted by Q2** |

### Q1 — `outils.py`: honour `ML_PLATFORM_DIR`

**Body file: the existing [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/prs/PR-4-qemu-outils.md](.planning/prs/PR-4-qemu-outils.md), unchanged.**
Patch: `.planning/prs/PR-4-qemu-outils-ML_PLATFORM_DIR.patch`, byte-identical to
`patches/0003-qemu-eos-outils-ML_PLATFORM_DIR.patch` (verified with `cmp`).

Stands alone. One line, no dependency, and it is the tool that produced Q2's
data file — a maintainer who wants to reproduce Q2 needs it first. **Submit
first.**

### Q2 — 6D2 MPU init spells, and the 6D2 `assert_log` address fix

Two commits in one PR:

1. `mpu_spells: add 6D2 (DIGIC 7) init spells captured from the body`
2. `6D2: fix the assert_log breakpoint address in debugmsg.gdb`

**Why together.** Both are 6D2 emulation-support data with strong, independent,
static evidence; both are reviewed by the same person looking at "6D2 support";
the second is 1 line + a comment. Bundling costs the reviewer nothing and saves
a round trip.

**Why not with Q3.** See below — the button-code table contains two entries that
are *not* decoded from the 6D2 ROM. Q2 is the change that actually fixes a boot
failure, and it should not be held hostage to the weakest claim in the set.

Both hunks live in `mpu.c` (lines ~49 and ~1230) far from Q3's hunk (~1290), so
Q2 and Q3 merge in either order without conflict — verified by applying both to
a pristine `HEAD` extraction.

### Q3 — 6D2 button codes

One commit: `mpu_spells: add 6D2 button codes, decoded statically from ROM0`.

**Stands alone, deliberately.** Not because of the file layout — it touches the
same `mpu.c` as Q2 — but because of *evidence quality*. The table holds 30
button codes plus `BGMT_END_OF_LIST`; 28 are decoded from ROM0's `tbb` dispatch
tables and cross-checked three ways. Two (`BGMT_PRESS_ZOOM_OUT` /
`BGMT_UNPRESS_ZOOM_OUT`) are **not from the 6D2 ROM at all**; they exist only
because `mpu.c:938` calls `exit(1)` when
`show_keyboard_help()` finds a `key_map` entry with no button code. A reviewer
may reasonably want to argue about those two, and that argument must not block
the spells.

Also: nothing in Q3 is on the boot path (measured — see the PR body), so it can
land at any time.

### Q4 — per-core Canon interrupt controllers

One commit: `eos: per-core Canon interrupt controllers and a per-CPU GIC
interface`.

**Must be its own PR.** It is a change to shared code that every model in
`model_list.c` compiles against and that 20 dual-core models execute. It has one
strong, specific result (core 1 receiving interrupts for the first time) and one
large untested surface (every other model). Mixing it with 6D2 data files would
make it impossible for a maintainer to merge the safe half and hold the risky
half.

**Submit last**, and after Q2 has landed: the measurement that justifies Q4 was
taken with Q2's spells in place, because without them the boot dies before the
interrupt behaviour is observable.

### Not upstreamed — the EstimatedSize gdb workaround

`patches/0004b` bundles two independent changes to
`magiclantern/cam_config/6D2/debugmsg.gdb`. Only one of them belongs upstream.

The EstimatedSize half installs a breakpoint at `0xE0202374` that forces
`r0 = 0x7D0` so `GetEstimatedSize()` sees a legal frame rate. It was debugging
scaffolding built when the *cause* of the illegal frame rate (81) was still
qemu-eos falling back to generic MPU spells. **Q2 removes that cause.**

Measured today, 120 s stock-firmware boot with Q2's spells and **no gdb script
attached at all**: `grep -c 'ASSERT\|Irregular TotalSheets\|ErrorSend\|EstimatedSize'`
over 1582 stderr lines returns **0**. The workaround has nothing left to work
around.

Shipping it anyway would be actively harmful: it would silently force a legal
frame rate for anyone who later regenerates or edits `6D2.h`, converting a loud
`ASSERT` into a silent wrong value. It stays in `patches/0004b` for local use
and is documented there.

### Also not upstreamed (not ours to submit)

The `qemu-eos/` working tree carries three untracked files from another
workstream — `magiclantern/cam_config/named_functions.idc`,
`magiclantern/cam_config/state_objects.py`, `magiclantern/test_00.png`. None is
part of any proposed PR. `test_00.png` is a QEMU framebuffer screenshot and must
not be swept into a commit by a `git add -A`.

`patches/0001`, `0002`, `0004`, `0005`, `0006` target
`magiclantern_simplified`, not `qemu-eos`, and are out of scope here.

---

## 2. Patch artifacts

| File | Contents | Verified |
|---|---|---|
| `.planning/prs/PR-4-qemu-outils-ML_PLATFORM_DIR.patch` | Q1 | applies to `HEAD` |
| `.planning/prs/PR-Q2-qemu-6D2-mpu-spells.patch` | Q2, both commits | applies to `HEAD` |
| `.planning/prs/PR-Q3-qemu-6D2-button-codes.patch` | Q3 | applies to `HEAD` |
| `.planning/prs/PR-Q4-qemu-percore-interrupts.patch` | Q4 | applies to `HEAD` |

Verification performed:

```
git archive HEAD hw/eos magiclantern/cam_config | tar -x -C <scratch>
cd <scratch> && git apply --check <each patch>      -> OK, all four
cd <scratch> && git apply <each patch, in order>    -> all applied, no rejects
diff <scratch>/<file> qemu-eos/<file>               -> IDENTICAL for all 8 files,
                                                       except debugmsg.gdb, which
                                                       differs by exactly the
                                                       deliberately-excluded
                                                       EstimatedSize hunk
```

### Corrections to `patches/README.md` found while doing this

1. **`patches/README.md` §0007 says "~175 spells".** Counted in the actual file:
   `6D2.h` has **69 request spells carrying 117 replies** (272 lines). 175 is
   not a count of anything in the file. The PR bodies use the measured numbers.
2. **`patches/README.md` §0008 says the patch touches `eos.c`, `eos.h` and
   `dbi/logging.c`.** The patch *file* touches only `eos.c` — see below.

**`patches/0008` is incomplete and must not be used as-is.** It contains only
the `hw/eos/eos.c` hunks (`grep -c '^diff --git'` = 1), despite its own README
stating that "a diff of `eos.c` alone would not compile" — the
`irq_enabled[2][INT_ENTRIES]` / `irq_id[2]` rank change lives in `eos.h`, and
`dbi/logging.c` reads those fields. `PR-Q4-qemu-percore-interrupts.patch`
(534 lines, 3 files) is the complete form and is what should be pushed.

---

## 3. Regression risk review — Q4

The interrupt change touches code every model executes. This section enumerates
what could break and for whom, then states plainly what could and could not be
tested here.

### 3.1 Model classification

From `hw/eos/model_list.c` (`.max_cpus`, set once per DIGIC family block and
inherited):

- **`max_cpus = 1`** — every DIGIC 3, 4, 5 and 6 model plus `5D3eeko`
  (35 entries, `5D` … `EOSM10`). `eos_state->cpu1 == NULL`, so `bank` is
  always 0.
- **`max_cpus = 2`, DIGIC 7** — `200D`, `6D2`, `77D`, `800D`, `EOSM5`.
- **`max_cpus = 2`, DIGIC 8** — `EOSM50`, `EOSM6mk2`, `EOSR`, `EOSRP`, `SX70`,
  `SX740`, `850D`, `90D`.
- **`max_cpus = 2`, DIGIC X** — `EOSR5`, `EOSR6`, `XF605`.

So 20 models other than the 6D2 execute the dual-core paths.

### 3.2 Single-core models (D3–D6): mechanical, with one real behaviour change

Safe by construction:

- `irq_enabled[id]` → `irq_enabled[0][id]`, `irq_id` → `irq_id[0]`: `bank` is 0
  for every handler-table `parm` these models use (`0`, `1`, `3`, `4`, `8`), and
  the `bank` expression additionally requires `eos_state->cpu1`, which is NULL.
- `eos_deliver_int(id)` skips bank 1 (`if (!eos_state->cpus[bank]) continue`),
  so its condition reduces to the old `irq_enabled[id] && !irq_id`.
- `eos_update_irq_line(0)` reduces to the old `cpu_interrupt` /
  `cpu_reset_interrupt` on `cpus[0]`: `gic_sgi_pending[0]` can only be set from
  `eos_handle_intengine_gic` (`0xC1000000`), which no pre-DIGIC-7 firmware
  touches, so it stays at its `0x20` sentinel.
- `COUNT(eos_state->irq_enabled)` → `INT_ENTRIES` in `eos_handle_intengine_vx`:
  **required, not cosmetic.** After the rank change `COUNT()` on the 2-D array
  evaluates to 2, which would have silently broken the bound check for the
  DIGIC 2/3 + 60D `0xC0200000` interrupt block. The patch gets this right.
- `OTHER_CPU` deleted: `grep -rn OTHER_CPU hw/` returns nothing. No users.
- `eos_handle_multicore` case `0x100`/`0x214`: message strings and a dead
  `#if 0` block only; the `assert(eos_state->cpu1)` is retained unchanged.

Real behaviour changes for single-core models:

1. **New `0xD4011018` "disable interrupt" case.** Writes there previously fell
   through to `default` and were ignored; they now clear
   `irq_enabled[bank][value]`. `0xD4011000-0xD4011FFF` is the DIGIC 6 *and* 7
   core-0 bank, so this affects nine single-core DIGIC 6 models (`80D`, `750D`,
   `760D`, `7D2`, `7D2S`, `5D4`, `5D4AE`, `EOSM3`, `EOSM10`). If any of them
   currently boots *because* qemu-eos ignored a `disable_interrupt()` the
   firmware issued, honouring it now starves that interrupt.
   **This is the most likely single-core regression and it is untested.**
   Cheap fallback if it bites: restrict the new case to `0xD5011018`, or gate it
   on `digic_version == 7`.
2. **New `if (value < INT_ENTRIES)` bound on the enable register.** The old code
   did `eos_state->irq_enabled[value] = 1` with no bound — an out-of-bounds
   write into `EOSState` for any `value >= 0x200`. Strictly a fix; the only
   observable change is that such a write no longer corrupts adjacent fields.

### 3.3 Dual-core DIGIC 7 (200D, 77D, 800D, EOSM5): highest risk

These share `eos_handle_intengine_gic` with the 6D2 and get every change.
Ordered by how badly they could fail:

1. **`ICDSGIR` now decodes `CPUTargetList`/`TargetListFilter`.** The old code
   unconditionally kicked "the other CPU". The in-tree comment that survives in
   the patch names the dependency explicitly: *"0xa is required to wake cpu1
   from a wfi loop while cpu0 does early init. See e.g. 200D 1.0.1
   0xe0004d30"*. The new code covers filter 0 (explicit list), 1 (all but self)
   and 2 (self only). The failure mode is a model that writes filter 0 with an
   **empty** target list and relied on the old "kick the other one" behaviour:
   its cpu1 would never wake, and the 200D would hang in early init.
   Not observed on the 6D2 (ROM `0xE015FCE4` builds an explicit non-empty list),
   not checked on any other ROM.
2. **`GICC_IAR` returns `0x3FF` when nothing is pending** (was `0x20`
   unconditionally). Spec-correct GICv1 and matched to 6D2 ROM `0xE026ACBA`,
   which returns immediately on `0x3FF`. A D7 ROM that dispatches
   unconditionally on `0x20` and tolerates a zero reason register now takes its
   spurious-interrupt path instead. Bug-compatible fallback if needed: return
   `0x20 + cpu` unconditionally.
3. **`GICC_IAR` returns `0x20 + cpu`** (was always `0x20`). Core 1 is now told
   to read bank 1's reason register. On a model that routes everything through
   bank 0 and expects core 1 to read bank 0, core 1 now reads an empty register.
   Note the patch's own one-shot `[INT] cpuN read bank M reason register`
   warning does **not** catch this — in that path `bank == CURRENT_BANK`. The
   `ITARGETSR` check is the one that would fire.
4. **`gic_sgi_pending` is cleared on `GICC_IAR` read, not on `GICC_EOIR`
   write.** This is what stops one core destroying the other's pending SGI (6D2
   ROM `0xE015FCFC` reads IAR and EOIRs whatever it got on every spurious wake),
   but it changes SGI timing for all four models.
5. **`MMIO_VAR(enabled[target_int])` removed from the `ICDSGIR` case.** The old
   code indexed the `GICD_ISENABLER` shadow with an SGI id and wrote the raw
   register value into it. Removing that changes what a subsequent
   `GICD_ISENABLER` read returns for word index == SGI id (0xA and 0xD on the
   6D2). Low risk, but it is a change.
6. **Nit to fix before submitting:** the `[GIC] SPI ... enabled with ITARGETSR`
   sanity warning has no `static int warned` guard, unlike its sibling
   `[INT] cpuN read bank M` warning. It fires on *every* `GICD_ISENABLER` word-1
   write. On a model whose `ITARGETSR` layout differs it will spam stderr rather
   than warn once. One line to fix; recommend fixing it before pushing.

### 3.4 Dual-core DIGIC 8 and DIGIC X: one specific, sharp risk

The new `0xD0231000/010/200` (D8 CPU1) and `0xD233A000/010/200` (DX CPU1) case
labels turn previously-ignored CPU1 bank accesses into live ones.

**DIGIC X is the concrete hazard.** `eos.c:1825` deliberately starts cpu1
halted:

```c
if (eos_state->model->digic_version == 10)
    CPU(eos_state->cpu1)->halted = 1; // DX starts with one off to avoid bad
                                      // race around MMU table access
```

`eos_deliver_int()` calls `cpu_interrupt(CPU(cpus[1]), CPU_INTERRUPT_HARD)` the
moment a bank-1 interrupt is armed and fires, and in QEMU that makes a halted
CPU runnable again. Before this patch, writes to `0xD233A010` fell through to
`default`, so `irq_enabled[1][]` was never set and cpu1 stayed parked. If
`EOSR5` / `EOSR6` / `XF605` firmware arms a bank-1 interrupt before it intends
to release cpu1, this patch re-introduces exactly the race the halt was added
to avoid.

Mitigations, in increasing order of caution: skip banks whose CPU is
`cpu_is_stopped()` inside `eos_deliver_int()`; or gate the DX case labels on
`digic_version != 10`; or drop the DX labels from this PR entirely and let
whoever owns DX add them with a DX ROM in hand.

Minor asymmetry: `0xD0231018` / `0xD233A018` disable-register labels were **not**
added, only the D6/D7 `0x…1018` pair. Either add them or say why not.

### 3.5 `dbi/logging.c`

`eos_state->irq_id` → `CURRENT_IRQ_ID` at three sites, including
`assert(CURRENT_IRQ_ID)` in `eos_callstack_log_exec`. Identical for single-core.
For dual-core it is a fix — the logger now names the interrupt the *executing*
core is servicing rather than a global. Only exercised under `-d callstack` /
`-d calls`, which was not run on any model here.

### 3.6 Cross-model testing: **impossible on this machine. Stated plainly.**

The task asked for at least two other camera models to be booted. **This could
not be done, and no partial substitute was attempted.**

- `roms/` contains exactly one model directory: `roms/6D2/` with `ROM0.BIN`
  (33554432 bytes) and `ROM1.BIN` (16777216 bytes).
- `/home/chris/ml6d2/roms` is a symlink to that same directory.
- A whole-filesystem `find / -name 'ROM*.BIN'` returned only those two files and
  btrfs snapshot copies of the same paths under `/home/.snapshots/`.

qemu-eos cannot instantiate a model without that model's ROM dump, so there is
no way to boot a 200D, a 5D3, a 5D4 or anything else here. **Q4 is therefore
tested on exactly one model, and the PR body says so in those words and asks
the maintainer to boot a 200D (dual-core D7) and one single-core DIGIC 6 body
before merging.**

### 3.7 What *was* measured, by this task, today

Re-ran the stock 6D2 boot against the current binary
(`/home/chris/ml6d2/qemu-eos-build/arm-softmmu/qemu-system-arm`, built 22:24:29,
newer than every source file in the four patches — so the binary does include
all of them, and they compile):

| signal | value |
|---|---|
| run length | 120 s, headless, `-d debugmsg`, stock firmware (`boot=False`) |
| stderr lines | **1582** |
| `ASSERT` / `Irregular TotalSheets` / `ErrorSend` / `EstimatedSize` | **0** |
| unique message texts | 1019 |
| startup completion | `[STARTUP]startupCompleteCallback 0x10` → `[SEQ] NotifyComplete (Startup, Flag = 0x10)` |
| final state | `NFCMgr nfcmgrstate_Initialize ce_init`, then RTCMgr I2C / DbgMgr PM housekeeping |
| `[MPU] FIXME: no MPU button codes for 6D2` | absent (Q3 applied) |
| `[MPU] warning: non-empty spell #N has duplicate(s)` | 5 (benign; `mpu_interpret_command()` resumes from the previous spell) |

This independently reproduces the recorded 1581-line figure (1582 here; the
band is run-to-run jitter in the coalesced `CACHEMAINT` counts) and the
zero-assert claim. No fresh `-d int` run was taken; the core-1 interrupt counts
quoted in the Q4 body are the ones recorded in `patches/README.md` §0008 and are
labelled there as such.

---

## 4. Copyright and hygiene check

### 4.1 No ROM bytes, no Canon firmware code

Scanned all four submission patches. Every ROM reference is an **address in a
comment** (`0xE0202374`, `0xE0617620`, `0xE026ABF4`, `0xE0835820`, …) or a
decoded instruction sequence quoted in prose. No file in any patch contains a
byte copied out of `ROM0.BIN` or `ROM1.BIN`.

`hw/eos/mpu_spells/6D2.h` contains **MPU bus traffic**, not firmware: the byte
sequences the MPU coprocessor sends to the ICU over the serial link, recorded by
ML's own `log-d678.c` DebugMsg hook and converted by upstream's own
`extract_init_spells.py`. That is observed inter-chip protocol data, the same
category as every other file in `hw/eos/mpu_spells/`.

The 522 KB source log (`tools/6D2-DEBUGMSG-body.txt`) is **not** in any patch and
must not be — verified by `grep '^diff --git'` on each patch file.

### 4.2 Upstream precedent for the spell tables — checked, consistent

`hw/eos/mpu_spells/` already ships 14 such files (`450D` … `EOSM2`, `100D`,
`5D2`, `5D3`, `6D`, `60D`, `70D`, `700D`). Decoding the printable ASCII runs out
of the hex byte arrays in the existing files shows they carry exactly the same
kind of contributor-specific payload:

| upstream file | embedded strings |
|---|---|
| `100D.h`, `EOSM2.h` | `$EF-S18-55mm f/3.5-5.6 IS STM` |
| `450D.h`, `600D.h`, `60D.h` | `$EF-S18-55mm f/3.5-5.6 IS` |
| `50D.h` | `$EF-S18-55mm f/3.5-5.6` |
| `5D2.h` | `$19-35mm`, `LP-E6` |
| `5D3.h` | `$EF-S24mm f/2.8 STM`, `LP-E6` |
| `6D.h`, `70D.h` | `LP-E6`, `$50-150mm` |
| `EOSM.h` | `$EF-S17-55mm f/2.8 IS USM` |

Our `6D2.h` carries the same three categories and nothing beyond them:

- `PROP_LENS_NAME` = `TAMRON SP 24-70mm F/2.8 Di VC USD G2 A032` — the lens that
  happened to be mounted. Directly precedented by seven upstream files.
- `PROP_BATTERY_REPORT` = `LP-E6` plus a 4-byte battery pack identifier
  (`47 fa 89 04`). Precedented by `5D3.h` / `60D.h` / `6D.h`, which carry the
  identical record shape with `ae 7e 3b 61`.
- `WGS-84` — a GPS *datum* constant in an otherwise all-zero GPS record.

### 4.3 No personal data

- **No GPS coordinates.** `PROP_MPU_GPS` (`reply #30.6`) is a 2-byte all-zero
  payload; the three `03 52` GPS records (`#30.8`, `#30.9`, `#30.10`) have every
  coordinate field zero. `WGS-84` is the datum name, not a position.
- **No camera body serial number.** The MPU does not carry it — `PROP_BODY_ID`
  comes from the ICU, not this bus — and a scan of every printable run ≥4 bytes
  in `6D2.h` found only the four strings listed above.
- **No owner / artist / copyright fields.** Searched; absent.
- **No filesystem paths, usernames, hostnames or e-mail addresses** in any of
  the four patches. `grep -in 'chris|/home/|legion|deocracy|@|Vibe Coding'` over
  all four returns only unified-diff `@@` hunk markers.
- `PROP_AVAIL_SHOT` carries `0x15 0x76` (5494 remaining shots on the card that
  was in the body). Operational, not identifying, and its all-zero sibling is
  what upstream's generic spells produce today.

**Owner decision, flagged not decided:** the lens name and battery identifier
are precedented and harmless, but they are contributor-specific. If Chris would
rather not publish which lens was mounted, both records can be zeroed before
pushing — neither is load-bearing for the boot (the 6D2 boots to
`startupCompleteCallback` with `PROP_LENS_NAME` present, and the record is a
fixed reply, not a computed one). Zeroing them has not been done and has not
been tested.

### 4.4 Style hygiene

`git apply` reports two trailing-whitespace warnings in `6D2.h`, both on
commented-out spell lines (`… .out_spells = { `). These come from upstream's own
`extract_init_spells.py` output format and are present in `5D3.h` at the same
positions, so leaving them keeps the file byte-consistent with its siblings. Fix
only if the maintainer asks.

---

## 5. Recommended order and gating

1. **Q1** — merge on sight, one line.
2. **Q2** — the substantive fix. Independent of everything.
3. **Q3** — any time after Q2; not on the boot path.
4. **Q4** — after Q2 has landed (its measurement narrative depends on Q2), and
   only after the maintainer or someone with other ROMs has booted a 200D and
   one single-core DIGIC 6 body. Say this in the PR rather than implying the
   change is safe.

Before pushing Q4, apply the one-line fix from §3.3 item 6 (`static int warned`
on the `ITARGETSR` warning) and decide §3.4 (drop the DIGIC X labels, or guard
`eos_deliver_int()` against halted CPUs).

---

## 6. What this plan does not establish

- Whether any model other than the 6D2 still boots with Q4 applied. Untestable
  here; no other ROMs exist on this machine.
- Whether the 6D2 button-code table is correct for the 22 entries that no one
  has ever pressed. Only 6 (a, b) → GUI-code pairs have body-log confirmation,
  and those were recorded during Canon's own boot-time switch scan, not from
  deliberate presses.
- Whether `BGMT_PRESS_ZOOM_OUT` / `BGMT_UNPRESS_ZOOM_OUT` = `0x0A01` / `0x0A00`
  are right. They are inferred from the 200D's switch numbering, not decoded
  from the 6D2 ROM.
- Whether ML itself boots under emulation. It does not — spike 004 measured both
  cores spinning at `0x001037A8` / `0x0010390C` inside ML's relocated image, and
  none of these four PRs changes that.
- Why the boot still stalls at `NFCMgr nfcmgrstate_Initialize ce_init` /
  `I2C_Read[CH3] : 0xa8,…`. Candidates are the unmodelled DIGIC 7 I2C block and
  the SD/CSMgr event chain; not narrowed.
