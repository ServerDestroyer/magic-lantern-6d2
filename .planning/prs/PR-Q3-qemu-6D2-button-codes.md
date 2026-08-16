# PR Q3 — qemu-eos: 6D2 button codes, decoded statically from ROM0

- **Target repo:** `reticulatedpines/qemu-eos`
- **Target branch:** `qemu-eos-v4.2.1` (based on `4b667a1d3c`)
- **Source branch:** none yet — see PR Q2 for why no branch exists in the shared clone.
- **Files:** `hw/eos/mpu_spells/button_codes.h` (+37), `hw/eos/mpu.c` (+1)
- **Patch file:** `.planning/prs/PR-Q3-qemu-6D2-button-codes.patch`
  (verified to apply cleanly to a `git archive HEAD` extraction, and to merge
  cleanly alongside PR Q2 in either order — the two `mpu.c` hunks are ~60 lines
  apart)
- **Commits:** 1

## Title

```
mpu_spells: add 6D2 button codes, decoded statically from ROM0
```

## PR body (ready to paste)

```markdown
Silences `[MPU] FIXME: no MPU button codes for 6D2.` and restores the four things
`mpu_spells_init()` skips when it hits that FIXME and returns: the
`BGMT_UNPRESS_UDLR` fan-out, the `dedicated_movie_mode == -1` key disable,
`show_keyboard_help()`, and the power-down notifier / `atexit` shutdown check.

## How the table was produced

`extract_button_codes.py` cannot run on this camera, for four independent
reasons:

1. It reads `<model>/ROM1.BIN`. On the 6D2 the main firmware is `ROM0.BIN`;
   `bindReceiveSwitch`, `GUI_Control`, `pRequestChange` and `Unknown DIRECTION`
   have **zero** hits in ROM1.
2. It hardcodes `rom_offset = 0x100000000 - rom_size`, i.e. `0xFE000000` for a
   32 MiB image, not `0xE0000000`.
3. `outils.py:find_func_from_string` only recognises the ARM32 literal forms
   `add<cond> Rd,pc,#imm` and `ldr<cond> Rd,[pc,#imm]`. 6D2 firmware is Thumb-2
   and uses the 16-bit `ADR Rd,label` encoding; and a scan of the whole 32 MiB
   image for the 4-byte LE values `0xE00DAD30` / `0xE00DC7BC` finds **no literal
   pool entry either**, so the `ldr` branch also finds nothing. The function
   returns `None` and the script dies.
4. Unicorn is initialised `UC_MODE_ARM` and would execute Thumb-2 as garbage.

Fortunately none of that is necessary here. On the 6D2, `bindReceiveSwitch` is a
plain two-level Thumb-2 `tbb` jump table that decodes straight out of ROM0:

| item | address | evidence |
|---|---|---|
| `bindReceiveSwitch` | `0xE00DA9F5` | `stmdb sp!,{r2-r9,sl,lr}`; `mov sl,r0` (=a), `mov r5,r1` (=b) |
| its `DebugMsg` call | `0xE00DAA12`/`0xE00DAA14` | `adr r2, 0xE00DAD30` = `"bindReceiveSwitch (%d, %d)"` |
| `GUI_Control` | `0xE00DC459` | `adr r2, 0xE00DC7BC` = `"GUI_Control:%d 0x%x"` at `0xE00DC468` |
| switch-id dispatch table | `tbb [pc, sl]` at `0xE00DAA2E`, 44-byte table at `0xE00DAA32` | guarded by `cmp.w sl,#44` / `bcs` at `0xE00DAA26` |
| direction sub-table (id `0x0B`) | `tbb [pc, r5]` at `0xE00DAB2C`, table at `0xE00DAB30` | guarded by `cmp r5,#10` |
| GUI event emit | `bl 0xE00DC458` at `0xE00DAA84`, `r0 = r4` (code) | `r4` sentinel `0xFFFF` = no event, set at `0xE00DAA0E` |

The structure is identical to DIGIC 4/5, just recompiled to Thumb-2. A ~140-line
static decoder (`objdump` + Python, no Unicorn) walks both levels and emits the
table.

## Cross-checks — three independent sources agree

**1. Against a real body log.** A `CONFIG_STARTUP_LOG` capture on the body
records `bindReceiveSwitch (a, b)` and the `GUI_Control:` that follows, during
Canon's own boot-time switch scan. Six pairs, all reproduced exactly by the
static decode:

| body log | static decode | `gui.h` |
|---|---|---|
| `(17,1)` → `85` (0x55) | id 0x11 → `0x55` | sibling of `GMT_GUICMD_LOCK_OFF = 0x54` |
| `(18,0)` → `87` (0x57) | id 0x12, `b != 1` → `0x57` | `GMT_GUICMD_OPEN_SLOT_COVER = 0x56` for `b == 1` |
| `(19,0)` → *nothing* | id 0x13 → both branches jump past the `r4` load | — |
| `(34,0)` → *nothing* | id 0x22 → same | — |
| `(43,0)` → `120` (0x78) | id 0x2B, `b != 1` → `0x78` | `// BGMT_LOCK_SW_UNLOCK 0x78` |
| `(38,1)` → `75` (0x4B) | id 0x26 → `0x4B` unconditionally | `GMT_GUICMD_PRESS_BUTTON_SOMETHING = 0x4B` |

**2. Against `platform/6D2.111/gui.h` in magiclantern_simplified.** The decode
independently reproduces every labelled constant there — SET 0x04/0x05, MENU
0x06, INFO 0x07, PLAY 0x0B, TRASH 0x0D, ZOOM_IN 0x12/0x13, Q 0x1D, LV 0x1E,
LIGHT 0x20, the multi-controller block 0x2E–0x36 in order, LOCK_OFF 0x54,
OPEN_SLOT_COVER 0x56, and both commented-out lock-switch codes 0x77/0x78. Those
values were hand-guessed when `gui.h` was written; this is their first
independent confirmation.

**3. Against `button_codes_200D[]`.** Copying the 200D table would have been
wrong in four places, which is worth recording since `button_codes_200D[]`
itself was hand-written rather than generated (`make_button_codes.sh` never
mentions the 200D, and its entries carry comments like `/* same as 100D */`):

- arrows: 200D uses `0x18xx`/`0x19xx`/`0x1Axx`/`0x1Bxx`; on the 6D2 those ids
  produce GUI codes `0x26`–`0x2D`, not the multi-controller. The 6D2's real
  d-pad is id `0x0B` with a 10-way direction sub-code.
- magnify: 200D `0x0901`, 6D2 `0x0801`.
- rear dial: the 200D has none; the 6D2 has `0x0E01`/`0x0EFF`
  (`SUB DIAL RIGHT`/`LEFT`).
- power: 200D `GMT_GUICMD_START_AS_CHECK = 0x1100`; on the 6D2 id `0x11` is the
  LOCK switch.

## What is NOT claimed

- **No key has ever been pressed in QEMU with this table and observed to reach
  Canon's GUI.** The GUI is not reachable on the 6D2 yet — the stock boot stalls
  at `NFCMgr nfcmgrstate_Initialize ce_init` / `I2C_Read[CH3]`.
- **Almost every entry is decode-only.** The table has 30 button codes plus
  `BGMT_END_OF_LIST`. Exactly **three** of them appear in the body log:
  `GMT_GUICMD_LOCK_ON` (0x1101), `GMT_GUICMD_CLOSE_SLOT_COVER` (0x1200) and
  `GMT_GUICMD_PRESS_BUTTON_SOMETHING` (0x2601). The other three body-log pairs
  quoted above validate the *decoder* but land on switch ids that produce no
  table entry — two emit no GUI event at all, and `0x78`'s `gui.h` name is
  commented out. So 27 of 30 entries rest on the static decode alone, and none
  of the 30 was produced by a deliberate button press.
- **Two entries are not from the 6D2 ROM.** `BGMT_PRESS_ZOOM_OUT = 0x0A01` and
  `BGMT_UNPRESS_ZOOM_OUT = 0x0A00` are inferred from the 200D's switch
  numbering, not decoded. They are present only because `show_keyboard_help()`
  calls `exit(1)` (`mpu.c:938`) when a `key_map` entry has no button code, and
  `show_keyboard_help()` runs unconditionally at the end of `mpu_spells_init()`.
  The 6D2 has no physical zoom-out button. They are marked `/* internal */` in
  the table. If the maintainer prefers `MPU_EVENT_DISABLED` or a `key_map`
  change instead, say so and it will be changed.
- **`GMT_GUICMD_START_AS_CHECK` is absent, deliberately.** It is not reachable
  through `bindReceiveSwitch` on the 6D2. QEMU's F10 power-down key and
  `mpu_send_powerdown()` therefore have no code. Not found, not faked.
- **`GMT_GUICMD_OPEN_BATT_COVER` / `CLOSE_BATT_COVER` are absent, deliberately.**
  `extract_button_codes.py` fakes these as `OPEN_SLOT_COVER + (1,0)` = `0x1301`.
  On the 6D2 id `0x13` returns no event on either branch — confirmed both in ROM
  and in the body log (`bindReceiveSwitch (19, 0)` produced no `GUI_Control`).
  The upstream heuristic is wrong here, so the entries are omitted rather than
  invented.
- **`BGMT_MENU = 0x0001` is convention, not proof.** Switch id `0x00` is
  dispatched unconditionally; the handler never tests `b`. One body press
  confirms the code.
- **Switch id `0x28` is unidentified.** It is a *second* 10-way direction control
  emitting GUI codes `0x38`–`0x3C`, which appear nowhere in `gui.h`. Candidates
  are the touch-AF pad or a top-plate control. Left out.
- **A dozen real buttons have no ML name yet.** Ids 0x02, 0x05, 0x06, 0x09, 0x0A,
  0x16, 0x17, 0x1E, 0x24, 0x25, 0x27, 0x29 produce GUI codes with no name in
  `gui.h` (AF-ON, AE-lock, DOF preview, AF-point, M-Fn, rate, …). Naming them is
  a `gui.h` job in magiclantern_simplified, not a qemu-eos one.

## This is not a boot fix, and does not claim to be

`button_codes[]` is read only by `translate_scancode_2()`, whose only callers are
`translate_scancode()` → `mpu_send_keypress()` and `key_avail()`.
`mpu_send_keypress()` in turn is called only from `eos_key_event()` (the
`qemu_add_kbd_event_handler` callback — a human pressing a key in the QEMU
window) and `mpu_send_powerdown()` (a `qemu_register_powerdown_notifier`
callback). Neither fires during boot.

Measured: the FIXME is printed at machine-construction time, **314 log lines
before the first MPU byte is exchanged**, and `mpu_spells_init()` selects the
init spells and runs `mpu_check_duplicate_spells()` *before* reaching it. Boot
behaviour is identical with and without this table.

## Offered separately: a DIGIC 6/7/8 extraction method

The decoder used here is ~140 lines of `objdump` + Python with an `assert`-based
self-check against the body-log pairs above. It works on any Thumb-2 body whose
`bindReceiveSwitch` uses `tbb` dispatch, which is the whole DIGIC 6/7/8 line —
where the Unicorn-based `extract_button_codes.py` cannot run at all. If there is
interest it can be contributed as a sibling script; it is deliberately not part
of this PR, which is data only.
```

## Suggested commit message

```
mpu_spells: add 6D2 button codes, decoded statically from ROM0

extract_button_codes.py cannot run on DIGIC 7: it reads ROM1 (the 6D2's
firmware is in ROM0), hardcodes rom_offset = 0x100000000 - rom_size,
recognises only the ARM32 literal-addressing forms in
find_func_from_string (6D2 firmware is Thumb-2 and uses 16-bit ADR, and
there is no literal pool entry for the string addresses anywhere in the
32 MiB image), and initialises Unicorn in UC_MODE_ARM.

Decoded statically instead. bindReceiveSwitch (0xE00DA9F5) is a
two-level Thumb-2 tbb table: 44-entry switch-id table at 0xE00DAA32
(tbb at 0xE00DAA2E, bounded by cmp.w sl,#44), plus a 10-way direction
sub-table at 0xE00DAB30 for id 0x0B, tailing into GUI_Control
(0xE00DC459).

Cross-checked three ways: the ROM decode reproduces six
bindReceiveSwitch -> GUI_Control pairs recorded on a real body during
Canon's boot-time switch scan ((17,1)->85, (18,0)->87, (19,0)->none,
(34,0)->none, (43,0)->120, (38,1)->75), and independently reproduces
every labelled constant in magiclantern_simplified's
platform/6D2.111/gui.h.

Copying button_codes_200D[] would have been wrong in four places: the
d-pad ids, the magnify code, the missing rear dial, and switch id 0x11
(LOCK on the 6D2, power on the 200D).

Not claimed: no key has been pressed in QEMU with this table and
observed to reach the GUI -- the 6D2 boot does not get that far yet.
Of the 30 codes in the table, exactly three appear in the body log
(LOCK_ON, CLOSE_SLOT_COVER, PRESS_BUTTON_SOMETHING); the rest rest on
the static decode alone, and none came from a deliberate press.
BGMT_PRESS_ZOOM_OUT / BGMT_UNPRESS_ZOOM_OUT (0x0A01 / 0x0A00) are NOT
decoded from the 6D2 ROM; the 6D2 has no zoom-out button and those two
entries exist only to satisfy the show_keyboard_help() completeness
check that exit(1)s at mpu.c:938. GMT_GUICMD_START_AS_CHECK is not
reachable through bindReceiveSwitch and is omitted rather than faked,
as are the batt-cover entries that extract_button_codes.py invents as
OPEN_SLOT_COVER + (1,0) -- 6D2 switch id 0x13 emits no event on either
branch, confirmed in ROM and in the body log.

This is not a boot fix: button_codes[] is read only by
translate_scancode_2(), reachable only from eos_key_event() and
mpu_send_powerdown(), neither of which fires during boot. The FIXME it
silences is printed 314 log lines before the first MPU byte.
```

## Exact commands for Chris (branch + push)

```sh
# Same throwaway-clone approach as PR Q2 -- never branch in the shared clone.
cd "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/qemu-eos"
git clone --no-hardlinks . /tmp/qemu-eos-pr-q3
cd /tmp/qemu-eos-pr-q3
git checkout -b 6d2-button-codes 4b667a1d3c

git apply "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/prs/PR-Q3-qemu-6D2-button-codes.patch"
git add hw/eos/mpu_spells/button_codes.h hw/eos/mpu.c
git commit -F - <<'EOF'
<paste the commit message above>
EOF

git remote add fork git@github.com:<YOUR_GITHUB_USER>/qemu-eos.git
git push fork 6d2-button-codes

gh pr create --repo reticulatedpines/qemu-eos \
  --base qemu-eos-v4.2.1 --head <YOUR_GITHUB_USER>:6d2-button-codes \
  --title "mpu_spells: add 6D2 button codes, decoded statically from ROM0" \
  --body-file <(sed -n '/^```markdown$/,/^```$/p' \
      "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/prs/PR-Q3-qemu-6D2-button-codes.md" \
      | sed '1d;$d')
```
