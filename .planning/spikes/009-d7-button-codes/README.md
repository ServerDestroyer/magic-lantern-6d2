---
spike: 009
name: d7-button-codes
type: standard
validates: "Given qemu-eos printing '[MPU] FIXME: no MPU button codes for 6D2', when the upstream extraction method is examined against DIGIC 7 firmware, then we establish whether 6D2 button codes can be produced and whether their absence is what blocks QEMU's boot"
verdict: VALIDATED (with a negative on the premise)
related: [001, 004, 005]
tags: [qemu, mpu, rom, reversing, buttons]
---

# Spike 009: DIGIC 7 MPU Button Codes

## Verdict, up front

**Two answers, and they point in opposite directions.**

1. **Yes, we can produce 6D2 button codes — and this spike already did.** Not
   with Unicorn: `bindReceiveSwitch` on the 6D2 is a plain two-level Thumb-2
   `tbb` jump table that decodes statically out of ROM0 in about 100 lines of
   Python. A complete 28-entry `button_codes_6D2[]` is in
   [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/009-d7-button-codes/button_codes_6D2.h](.planning/spikes/009-d7-button-codes/button_codes_6D2.h),
   cross-checked three ways (ROM decode ≡ real body log ≡ `platform/6D2.111/gui.h`).
   Cost to land it in qemu-eos: one 30-line array plus one line in `mpu.c`.

2. **No, the missing table is not what blocks the boot, and never was.**
   `button_codes[]` is read by exactly one code path — the QEMU keyboard
   handler. Nothing in Canon's boot touches it. Measured today: with spike 005's
   real MPU spells in place the `EstimatedSize.c:1521` assert is **gone**, boot
   now reaches `NFCMgr` and stalls there on an I2C read, and the
   `no MPU button codes` FIXME is printed 300 log lines earlier at machine-init
   time with no consequence.

So: do it, because it is nearly free and we will want it the moment the GUI
comes up. Do **not** schedule it as a boot blocker — the boot blocker is
somewhere in the NFC/I2C path, not here.

---

## 1. What the upstream script actually does

[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/qemu-eos/hw/eos/mpu_spells/extract_button_codes.py](qemu-eos/hw/eos/mpu_spells/extract_button_codes.py),
driven by `make_button_codes.sh` (which loops over 18 DIGIC 4/5 bodies, `100D`
through `EOSM2` — no DIGIC 6/7/8 model appears in it).

**Inputs.** `<model>/ROM1.BIN` only, mapped at `0x100000000 - romsize`, plus
`platform/<model>.*/gui.h` from the ML tree.

**The three functions it must locate**, all by DebugMsg format string
(`rom_funcs`, lines 17-21):

| symbol | located by | how |
|---|---|---|
| `bindReceiveSwitch` | `"bindReceiveSwitch (%d, %d)"` | function start, scanning backwards for `STMFD` |
| `DebugMsg` | same string | the first `BL` after the string reference |
| `prop_request_change` | `"pRequestChange"` | function start; patched to `bx lr` so emulation has no side effects |

**How it finds a string reference** (`outils.py:find_func_from_string`): it
scans the ROM in 4-byte steps for exactly two **ARM32** encodings —
`add<cond> Rd, pc, #imm` (`0x028F_d000`) and `ldr<cond> Rd, [pc, #imm]`
(`0x059F_d000`) — with `Rd == r2` (DebugMsg's 3rd argument) and `cond == 0xE`
(AL). Then `locate_func_start` walks backwards for an `STMFD`, and
`locate_next_func_call` scans forward ≤0x100 bytes for a `BL`.

**The algorithm** (lines 82-144). Map ROM + 16 MB RAM in Unicorn (ARM mode),
`SP = 0x1900`, `LR = 0xABCD0000`, neuter `prop_request_change`. Then brute-force
the argument space:

```
for a in range(40):
    if try_button_code(a, 0xFF): for b in range(10): try_button_code(a, b)
    try_button_code(a, 0); try_button_code(a, 1)
```

`try_button_code(a, b)` sets `r0 = a`, `r1 = b`, runs from `bindReceiveSwitch`
stopping at `DebugMsg`, prints the message, and resumes at `LR` — a
poor-man's DebugMsg stub. Two messages are the oracle:

- `"GUI_Control"` in the message → read `r3`, which holds the GUI event code;
  look it up in `gui.h` via `get_switch_names`; record `name_to_mpu[name] = (a,b)`.
- `"Unknown DIRECTION"` → this `a` is a direction-style switch, so re-probe
  `b` over 0..9.

**Output.** A C array printed to stdout, appended by `make_button_codes.sh` into
`mpu_spells/button_codes.h`:

```c
static int button_codes_<CAM>[] = { [BGMT_NAME] = 0xAABB, ... };
```

with one hand-faked entry: `GMT_GUICMD_OPEN_BATT_COVER` is invented as
`OPEN_SLOT_COVER + (1,0)` (lines 143-144), because the emulation never reaches it.

Note the two namespaces: `gui.h` maps *camera GUI code → ML name*; the emitted
`[BGMT_NAME]` **index** resolves against `enum button_codes` in
[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/qemu-eos/hw/eos/mpu.h](qemu-eos/hw/eos/mpu.h)
(line 21), which is qemu's own private ordinal list. Any generated table must be
pruned to names that appear in that enum.

**Why it cannot run on the 6D2 — four independent reasons:**

1. It reads `ROM1.BIN`. On the 6D2 ROM1 is not the main firmware; every string
   it needs is in ROM0 (`grep -c` on ROM1 for `bindReceiveSwitch`, `GUI_Control`,
   `pRequestChange`, `Unknown DIRECTION`: zero hits, all four).
2. It hardcodes `rom_offset = 0x100000000 - rom_size`. For our 32 MiB ROM0 that
   is `0xFE000000`, not `0xE0000000`.
3. **The killer:** `find_func_from_string` only recognises ARM32 literal
   addressing. 6D2 firmware is Thumb-2 and references its strings with the
   16-bit `ADR Rd, label` form (`add rX, pc, #imm8*4`, encoding `0xA2xx`). There
   is also **no literal pool entry anywhere in ROM0** holding `0xE00DAD30` or
   `0xE00DC7BC` (verified by scanning the whole 32 MiB for those 4-byte LE
   values — zero matches), so the `ldr Rd,[pc]` branch finds nothing either.
   The script returns `None` and dies on `[idx]`.
4. Unicorn is initialised `UC_MODE_ARM` and would execute Thumb-2 as garbage.

`outils.py` in our tree already carries one local fix (`ML_PLATFORM_DIR` env
override, replacing the hardcoded `../../../../../magic-lantern/platform/`) from
an earlier attempt — that part is fine and worth keeping.

---

## 2. Do the 6D2 equivalents exist? Yes. Addresses.

Everything is in **ROM0**, nothing in ROM1.

### Strings

| string | address | file offset in ROM0.BIN |
|---|---|---|
| `bindReceiveSwitch (%d, %d)` | `0xE00DAD30` | `0x000DAD30` |
| `bindReceiveSwitch : Ignore (ID == %d)` | `0xE00DB25C` | `0x000DB25C` |
| `Unknown DIRECTION (%d)` | `0xE00DAD50` | `0x000DAD50` (also a copy at `0xE0043330`) |
| `GUI_Control:%d 0x%x` | `0xE00DC7BC` | `0x000DC7BC` |
| `MAIN DIAL LEFT (%d)` / `RIGHT` | `0xE00DAD68` / `0xE00DAD7C` | |
| `SUB DIAL LEFT (%d)` / `RIGHT` | `0xE00DAD94` / `0xE00DADA8` | |
| `LOCK (%d)` | `0xE00DADBC` | |
| `pRequestChange` | `0xE044D030`, `0xE04E50E4` | |

### Functions

| function | address (Thumb) | evidence |
|---|---|---|
| `bindReceiveSwitch` | **`0xE00DA9F5`** (code at `0xE00DA9F4`) | `stmdb sp!, {r2,r3,r4,r5,r6,r7,r8,r9,sl,lr}`; `mov sl,r0` (=a), `mov r5,r1` (=b) |
| its DebugMsg call | `0xE00DAA12` (`adr r2, 0xE00DAD30`) / `0xE00DAA14` (`blx`) | body log records LR `e00daa15` on every `bindReceiveSwitch` line |
| `GUI_Control` | **`0xE00DC459`** (code at `0xE00DC458`) | `adr r2, 0xE00DC7BC` at `0xE00DC468`; body log LR `e00dc46b` |
| `DebugMsg` | **`0xE043B4F0`** | target of every `blx` above |
| the `a` dispatch table | `tbb [pc, sl]` at `0xE00DAA2E`, 44-byte table at **`0xE00DAA32`** | guarded by `cmp.w sl, #44` / `bcs` at `0xE00DAA26` |
| the direction sub-table (id 0x0B) | `tbb [pc, r5]` at `0xE00DAB2C`, table at `0xE00DAB30` | guarded by `cmp r5, #10` |
| a second direction sub-table (id 0x28) | `tbb [pc, r5]` at `0xE00DAB62`, table at `0xE00DAB66` | unidentified control, see gaps |
| GUI event emit | `bl 0xE00DC458` at `0xE00DAA84`, args `r0 = r4` (code), `r1 = 0`, `r2 = r8` | |
| "ignored switch" path | `0xE00DAE8E` → prints `bindReceiveSwitch : Ignore (ID == %d)` | |

The structure is **identical to DIGIC 4/5**, just recompiled to Thumb-2:
`r4` is loaded with the GUI code (sentinel `0xFFFF` = no event, set at
`0xE00DAA0E`), `b == 1` selects press vs unpress, and the tail calls
`GUI_Control(r4, 0, arg)`.

### Ground truth from the body

The premise in the task brief — that our body log shows "GUI_Control without
bindReceiveSwitch" — **is wrong**, and usefully so. Both are present; `grep`
just needs `-a`, because the logs contain stray NUL bytes and GNU grep silently
treats them as binary. From
[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/tools/](tools/) →
`6D2-DEBUGMSG-body.txt` lines 4936-4966:

```
MainCtrl:e00daa15:87:03: bindReceiveSwitch (17, 1)
MainCtrl:e00dac41:87:03: LOCK (1)
MainCtrl:e00dc46b:84:03: GUI_Control:85 0x0
MainCtrl:e00daa15:87:03: bindReceiveSwitch (18, 0)
MainCtrl:e00dc46b:84:03: GUI_Control:87 0x0
MainCtrl:e00daa15:87:03: bindReceiveSwitch (19, 0)      <- no GUI_Control follows
MainCtrl:e00daa15:87:03: bindReceiveSwitch (34, 0)      <- no GUI_Control follows
MainCtrl:e00daa15:87:03: bindReceiveSwitch (43, 0)
MainCtrl:e00dc46b:84:03: GUI_Control:120 0x0
```

and from `6D2-DEBUGMSG-body-movie.txt`: `bindReceiveSwitch (38, 1)` →
`GUI_Control:75`.

Every one of these matches the static decode exactly:

| body log | static decode of `bindReceiveSwitch` | `gui.h` |
|---|---|---|
| `(17,1)` → `85` (0x55) | id 0x11 → `0x55` | (`GMT_GUICMD_LOCK_OFF = 0x54` is the sibling) |
| `(18,0)` → `87` (0x57) | id 0x12, `b != 1` → `0x57` | `GMT_GUICMD_OPEN_SLOT_COVER = 0x56` for `b == 1` ✓ |
| `(19,0)` → nothing | id 0x13 → both branches jump to `0xE00DAA88`, r4 untouched | — |
| `(34,0)` → nothing | id 0x22 → same | — |
| `(43,0)` → `120` (0x78) | id 0x2B, `b != 1` → `0x78` | `// BGMT_LOCK_SW_UNLOCK 0x78` (commented out) ✓ |
| `(38,1)` → `75` (0x4B) | id 0x26 → `0x4B` unconditionally | `GMT_GUICMD_PRESS_BUTTON_SOMETHING = 0x4B` ✓ |

And the decode independently reproduces every labelled constant in
`platform/6D2.111/gui.h` — SET 0x04/0x05, MENU 0x06, INFO 0x07, PLAY 0x0B,
TRASH 0x0D, ZOOM_IN 0x12/0x13, Q 0x1D, LV 0x1E, LIGHT 0x20, the whole
multi-controller block 0x2E-0x36 in the right order, LOCK_OFF 0x54,
OPEN_SLOT_COVER 0x56, and both commented-out lock-switch codes 0x77/0x78. Those
values were guessed by hand when `gui.h` was written; this is the first
independent confirmation of them.

### The result

Reproducible with
[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/009-d7-button-codes/decode_button_codes.py](.planning/spikes/009-d7-button-codes/decode_button_codes.py)
(~140 lines, uses `arm-none-eabi-objdump`, no Unicorn, has an `assert`-based
self-check against the body-log pairs):

```bash
nix-shell "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/shell.nix" --run \
  "cd /home/chris/ml6d2 && python3 '<spikedir>/decode_button_codes.py' roms/6D2/ROM0.BIN"
```

Full 44-id trace: `bindReceiveSwitch-decode.txt`. Emitted table:
`button_codes_6D2.h`.

```c
static int button_codes_6D2[] = {
    [BGMT_MENU]                         = 0x0001,
    [BGMT_INFO]                         = 0x0101,
    [BGMT_PLAY]                         = 0x0301,
    [BGMT_TRASH]                        = 0x0401,
    [BGMT_UNPRESS_ZOOM_IN]              = 0x0800,
    [BGMT_PRESS_ZOOM_IN]                = 0x0801,
    [BGMT_UNPRESS_UDLR]                 = 0x0B00,
    [BGMT_PRESS_UP]                     = 0x0B02,
    [BGMT_PRESS_UP_RIGHT]               = 0x0B03,
    [BGMT_PRESS_UP_LEFT]                = 0x0B04,
    [BGMT_PRESS_RIGHT]                  = 0x0B05,
    [BGMT_PRESS_LEFT]                   = 0x0B06,
    [BGMT_PRESS_DOWN_RIGHT]             = 0x0B07,
    [BGMT_PRESS_DOWN_LEFT]              = 0x0B08,
    [BGMT_PRESS_DOWN]                   = 0x0B09,
    [BGMT_UNPRESS_SET]                  = 0x0C00,
    [BGMT_PRESS_SET]                    = 0x0C01,
    [BGMT_WHEEL_RIGHT]                  = 0x0D01,
    [BGMT_WHEEL_LEFT]                   = 0x0DFF,
    [BGMT_WHEEL_DOWN]                   = 0x0E01,
    [BGMT_WHEEL_UP]                     = 0x0EFF,
    [GMT_GUICMD_LOCK_ON]                = 0x1101,
    [GMT_GUICMD_CLOSE_SLOT_COVER]       = 0x1200,
    [GMT_GUICMD_OPEN_SLOT_COVER]        = 0x1201,
    [BGMT_Q]                            = 0x2001,
    [BGMT_LV]                           = 0x2101,
    [BGMT_LIGHT]                        = 0x2301,
    [GMT_GUICMD_PRESS_BUTTON_SOMETHING] = 0x2601,
    [BGMT_END_OF_LIST]                  = 0x0000
};
```

**This is materially different from the `button_codes_200D[]` table already in
`button_codes.h:624`** — which, note, was hand-written, not generated
(`make_button_codes.sh` never mentions 200D, and the entries carry comments like
`/* same as 100D */`). Copying 200D for the 6D2 would be wrong in four places:

- arrows: 200D uses `0x18xx`/`0x19xx`/`0x1Axx`/`0x1Bxx`; on the 6D2 those ids
  produce GUI codes `0x2A`-`0x2D` and `0x26`-`0x29`, **not** the multi-controller.
  The 6D2's real d-pad is id `0x0B` with a 10-way direction sub-code.
- magnify: 200D `0x0901`; 6D2 `0x0801`.
- rear dial: 200D has none; the 6D2 has `0x0E01`/`0x0EFF` (`SUB DIAL RIGHT/LEFT`).
- power: 200D `GMT_GUICMD_START_AS_CHECK = 0x1100`; on the 6D2 id `0x11` is the
  LOCK switch, not the power switch.

**Known gaps, stated rather than guessed:**

- `GMT_GUICMD_START_AS_CHECK` (0x5A in `gui.h`) is **not reachable through
  `bindReceiveSwitch`** on the 6D2. QEMU's F10 power-down key and
  `mpu_send_powerdown()` will therefore have no code. Not found; not faked.
- `GMT_GUICMD_OPEN_BATT_COVER` / `CLOSE_BATT_COVER`: the upstream script fakes
  these as `OPEN_SLOT_COVER + (1,0)`, i.e. `0x1301`. On the 6D2, id `0x13`
  returns no event on either branch — confirmed both in ROM and in the body log
  (`bindReceiveSwitch (19, 0)` produced no `GUI_Control`). The upstream
  heuristic is simply wrong here. Left out.
- `BGMT_PRESS_HALFSHUTTER` is absent from the table by design: `mpu.c` handles
  half-shutter through the `0x0E0E0000` raw path with explicit spells
  (`mpu.c:798`, `mpu.c:975-985`), not through `button_codes[]`.
- `BGMT_MENU` (id 0x00) is dispatched unconditionally — the handler never tests
  `b` — so `0x0001` is convention, not proof. One body press confirms it.
- Switch id `0x28` is a **second** 10-way direction control emitting GUI codes
  `0x38`-`0x3C`, which appear nowhere in `gui.h`. Unidentified. Candidates:
  touch-AF pad or the top-plate control. Worth a body press if anyone cares.
- Ids 0x02, 0x05, 0x06, 0x09, 0x0A, 0x16, 0x17, 0x1E, 0x24, 0x25, 0x27, 0x29
  produce GUI codes with no name in `gui.h` (0x08-0x11, 0x14-0x1A, 0x1F, 0x21,
  0x22, 0x63, 0x65). These are real buttons whose ML names are still unassigned
  — AF-ON, AE-lock, DOF preview, AF-point, M-Fn, rate, etc. Assigning them is a
  `gui.h` job, and a body capture is the right tool (see §3).

---

## 3. Empirical capture on the body — feasible, and partly already done

**Yes, trivially, and the infrastructure already exists and has already run.**

The ROM prints `bindReceiveSwitch (%d, %d)` at DebugMsg class `0x87`, level 3,
and `GUI_Control:%d 0x%x` at class `0x84`, level 3, for **every** button event —
on the stock firmware, with no patching. ML's DIGIC 6/7/8 startup logger
([/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/src/log-d678.c](ml/src/log-d678.c))
hooks `DryosDebugMsg` at `0xDF006E6C` and records everything with no class/level
filter (the filter at `log-d678.c:63-69` is `#if 0`-ed out). That is exactly the
(a, b) → GUI-code pair the table needs.

Spike 005 already built this and ran it on the body — the six pairs quoted in §2
come out of that existing capture, and they were recorded incidentally during
Canon's own boot-time switch scan, with nobody pressing anything.

**The only obstacle is the capture window.** `startup_log_dump_task` in
[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/src/init.c](ml/src/init.c)
line 650 is `msleep(20000); log_finish();` — 20 seconds, of which the boot burns
~520 KB of the 2 MB buffer (and the movie-mode capture filled it completely,
2097090 of 2097152 bytes).

**Protocol — two one-line edits, one build, one body run:**

1. `src/init.c:650` — `msleep(20000)` → `msleep(120000)`.
2. `src/log-d678.c:63` — re-enable the filter, inverted, so only switch traffic
   is kept: `if (class != 0x87 && class != 0x84) return;`. Boot noise drops by
   two orders of magnitude and 2 MB becomes far more than enough.
3. Build and deploy:
   ```bash
   nix-shell --run 'cd ml/platform/6D2.111 && make disk_image CONFIG_STARTUP_LOG=y \
     ARM_BINPATH="$(dirname $(which arm-none-eabi-gcc))" \
     ML_MODULES="raw_video/mlv_lite file_man bench dual_iso"'
   ```
   (`ML_MODULES` must be explicit — the default list includes `lua`, which does
   not build under gcc 15.)
4. On the body: power on, wait for the ML banner, then press-and-release each
   control **once, slowly, one at a time**, in a written order so the log can be
   segmented by hand: MENU, INFO, PLAY, TRASH, Q, LV/REC, LIGHT, SET, magnify,
   AF-ON, AE-lock, DOF, M-Fn, RATE, AF-point; then each of the 8
   multi-controller directions plus its centre press; then one detent of each
   dial in each direction; then the lock switch both ways; then open and close
   the card door. Roughly 90 seconds of pressing.
5. Power off, pull the card, read `DEBUGMSG.LOG`, and
   `grep -a 'bindReceiveSwitch\|GUI_Control'`. Each button is one adjacent pair.

**Effort: about half a day** including the build/deploy loop, and the risk is
zero — logging build only, no ROM writes, and this exact build has already run
on this body twice.

**But note what it is actually for.** It is *not* needed to produce the qemu
table — §2 already produced that from the ROM. It is worth doing for two other
reasons: (a) it fills the `gui.h` blanks (the dozen unnamed buttons and switch
id 0x28), which is a real gap in the ML port; and (b) it settles `BGMT_MENU`'s
`b` byte and would find whatever produces `GMT_GUICMD_START_AS_CHECK`. Do it as
a `gui.h` completeness task, not as a qemu task.

---

## 4. Sanity check: is this what blocks QEMU? **No.**

### From the source

`button_codes` is a single file-static pointer,
[qemu-eos/hw/eos/mpu.c](qemu-eos/hw/eos/mpu.c) line 677. Every read of it:

| line | context |
|---|---|
| 770 | `translate_scancode_2()` — early `return -1` if the pointer is null |
| 817, 838 | `translate_scancode_2()` — the actual lookup |
| 891 | `key_avail()`, used only by `show_keyboard_help()` |
| 1302-1311 | the `BGMT_UNPRESS_UDLR` fixup inside `mpu_spells_init()` |

`translate_scancode_2` has exactly two callers: `translate_scancode()` (→
`mpu_send_keypress()`, `mpu.c:947`) and `key_avail()`. `mpu_send_keypress()` in
turn has two callers: `eos_key_event()` at
[qemu-eos/hw/eos/eos.c](qemu-eos/hw/eos/eos.c) line 1667 — the
`qemu_add_kbd_event_handler` callback, i.e. a human pressing a key in the QEMU
window — and `mpu_send_powerdown()` (`mpu.c:1144`), a `qemu_register_powerdown_notifier`
callback. **Neither fires during boot.** No Canon code path reads
`button_codes[]`; it is purely an input-injection lookup table.

The FIXME at `mpu.c:1297` does `return` out of `mpu_spells_init()`, so it also
skips four things after it. All four are harmless for boot:

- the `UNPRESS_UDLR` fan-out (only matters if a key is pressed);
- disabling the movie-mode key when `dedicated_movie_mode == -1` (ditto);
- `show_keyboard_help()` (cosmetic — and indeed absent from our log);
- registering the power-down notifier and `atexit(clean_shutdown_check)` (only
  matters on QEMU shutdown).

Crucially, the **MPU init spells are selected earlier**, at `mpu.c:1233`
(`MPU_SPELL_SET(6D2)`), and `mpu_check_duplicate_spells()` runs at 1260 — both
before the FIXME. The spell machinery, which *is* what Canon's boot depends on,
is fully initialised regardless.

### From a measured run, today

Ran headless for 30 s and again for 90 s with the current working tree
(qemu-eos has spike 005's uncommitted `mpu_spells/6D2.h` + `MPU_SPELL_SET(6D2)`;
build `qemu-eos-build/arm-softmmu/qemu-system-arm` dated after them):

```
line   33-37  [MPU] warning: non-empty spell #20 ... has duplicate(s)
line   38     [MPU] FIXME: no MPU button codes for 6D2.
line  352     [MPU] Received: 06 04 02 00 00 00  (Init - spell #1)
...
line  464     NFCMgr  nfcmgrstate_Initialize ce_init
line  468     39:4292891.135 ERROR [I2C] I2C_Read[CH3] : 0xa8,0x00,0x01,0x00
              <end of output>
```

- The FIXME is printed at **machine construction time**, 314 lines before the
  first MPU byte is exchanged. It is not on the boot path; it is a startup notice.
- **The `ASSERT : Resource/./EstimatedSize.c ... Line 1521` from spike 001 no
  longer appears at all.** Spike 005's real MPU spells fixed the actual blocker.
  Spike 001's root-cause analysis was correct and its remedy has landed.
- Boot now gets much further: 19 spells sent, 5 received, through `PWM_Initialize`,
  ADC calibration, the Mode/Lens/Battery groups, `StartupCondition : 1, 0`,
  `PROP_LIVE_VIEW_MOVIE_SELECT`, and into `NFCMgr`.
- It then stops. Tripling the run to 90 s adds six lines of PM housekeeping and
  **not one additional spell** — same 19. The stall is at
  `nfcmgrstate_CeInitialize` / `I2C_Read[CH3] : 0xa8,...`, i.e. an unimplemented
  I2C peripheral, and no keypress was ever sent because none was ever pressed.

Reproduce: `runq.py`-style wrapper around `ml_qemu.run.QemuRunner` with
`display=None`, `d_args=["debugmsg"]`, `sd_file`/`cf_file` from
`qemu-eos/magiclantern/disk_images/`, and a monitor socket path short enough for
`AF_UNIX` (the scratchpad path is too long — use `/tmp/`).

### Conclusion for §4

The missing button-code table is **irrelevant to reaching the GUI**. It becomes
relevant the moment the GUI *is* reachable and someone wants to press MENU. The
current boot blocker is the NFC/I2C path, which is a completely separate
investigation and the natural successor to this spike.

---

## Is it worth doing at all?

**Yes — but reclassify it.** It is a 30-minute chore, not a milestone.

- The table exists (`button_codes_6D2.h` in this directory). Landing it is:
  paste the array into `qemu-eos/hw/eos/mpu_spells/button_codes.h`, add
  `MPU_BUTTON_CODES(6D2)` next to `MPU_BUTTON_CODES(200D)` at `mpu.c:1292`.
  It also silences the FIXME and restores `show_keyboard_help()` and the
  power-down notifier, which are mildly useful now.
- It is upstreamable on its own merits, and it comes with something upstream
  does not have: a DIGIC 7 extraction method. The Unicorn script is dead for
  every D6/D7/D8 body; a ~140-line static `tbb` decoder is not. If the 200D
  table was hand-copied from the 100D (and it looks that way), this method could
  regenerate it correctly too.
- It independently validates 15 constants in `platform/6D2.111/gui.h` that were
  previously hand-guessed. That is worth having on the record regardless.
- **Do not** file it as unblocking QEMU. Nothing about it is on the boot path,
  and the next real question is the `NFCMgr` / `I2C_Read[CH3]` stall.

### Next action

Land `button_codes_6D2[]` + `MPU_BUTTON_CODES(6D2)` in qemu-eos as a small
standalone change (main session commits), then open spike 010 on the
`nfcmgrstate_CeInitialize` / I2C stall — that is where boot actually stops now.

### Artifacts in this directory

- `decode_button_codes.py` — the extractor (objdump + ~100 lines, self-checking)
- `button_codes_6D2.h` — its output, ready to paste
- `bindReceiveSwitch-decode.txt` — full 44-id decode trace with addresses
