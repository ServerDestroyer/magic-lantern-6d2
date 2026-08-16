# Spike 007 — the 6D2 MOVIE-mode dual-ISO CMOS table, decoded from ROM

**Status:** static analysis complete. No camera, no builds, `ml/` unmodified.
**Date:** 2026-08-15
**Inputs:** [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/roms/6D2/](roms/6D2/) → `ROM0.BIN` (32 MiB @ `0xE0000000`), `ROM1.BIN`;
[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/modules/dual_iso/dual_iso.c](ml/modules/dual_iso/dual_iso.c);
[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/src/patch.c](ml/src/patch.c).

**Reproducible check:** every load-bearing numeric claim below is asserted against `ROM0.BIN` by
`/tmp/claude-1000/-home-chris-Vibe-Coding-6D-Mark-II-Magic-Lantern-6D2/d1809f97-1ab5-4672-8a2b-1ab8dcfa3d5e/scratchpad/verify_movie_table.py`
(runs in <1 s, prints `all checks pass`). Copy it somewhere durable if this spike is to be re-verified later.

---

## 0. Verdict first

```c
FRAME_CMOS_ISO_START = base ? base - 0xb30 + 0xef4 : 0;   /* RAM ≡ ROM 0xE1980EF4 */
FRAME_CMOS_ISO_COUNT = 8;
FRAME_CMOS_ISO_SIZE  = 0x54;
```

`0xE1980EF4` — the address the spike README labelled "candidate 2". The README's "candidate 3"
(`0xE1980F10`) is **eliminated, and not by preference**: it is not a second table. It is record 1 of
the *same* array — the ISO +1/3 stop entry. Pointing `FRAME_CMOS_ISO_START` at it patches ISO
125/250/500/1000/… and leaves every full stop untouched, so dual-ISO would silently do nothing at
any ISO the user can select from a full-stop menu.

Two further tables the README did not find are also present, and both are worse candidates
(§3c, §4).

**The existing `patch_cmos_iso_values_6d2()` needs no rework.** The README predicted "a modest
rework there" for a strided table; that is wrong. `dual_iso.c:378` reads
`*(uint32_t *)(old_values + item_size * i)` and writes at the same stride into a full-size copy
made by `memcpy` — arbitrary `item_size` already works, and the bytes between patched words are
preserved verbatim. The diff really is six lines.

---

## 1. What the blob is

All 122 ISO-shaped command words in ROM0 (`0x0d0?aXY0`) live inside `0xE1980000–0xE1982000`, one
contiguous 8 KiB region. ROM1 contains none. (One isolated `0d02a200` at `0xE0F3C3F8` is inside
code and is a coincidence.)

The ROM names this region itself. At `0xE0066B58` there is a `{address, filename}` table used by a
Canon factory debug command that dumps FROM regions to card:

| Address literal | Adjacent string | File offset of string |
|---|---|---|
| `0xF0890000` | `TuneData.bin` | `0x066B34` |
| `0xF0B30000` | `TuneData2.bin` | `0x066B48` |
| **`0xE1980000`** | **`FixData.bin`** | **`0x066B5C`** |

Corroborating strings in the same table: `CheckSumOfFixData` (`0xE0066C04`), `SaveFixToFile`
(`0xE0066CF4`), `VerifyFixData` (`0xE0066E58`). A second reference at `0xE0065FAC` sits between
`[MISC] SetTuningFlag Done` and `\nSum Value = 0x%x\n` — a checksum walk over `0xE0040000` and
`0xE1980000`. A third at `0xE0040968` sits among `PROPAD_CreateFROMPropertyHandle : CUSTOM (%#x)` /
`: FIX (%#x)` strings.

So the blob is Canon's **FixData** factory-adjustment region, DMA'd whole to heap at runtime.
`get_photo_cmos_iso_start_6d2()` ([dual_iso.c:1163-1217](ml/modules/dual_iso/dual_iso.c)) recovers
the destination base by scanning `0x780000–0x880000` for a DMA descriptor whose source is
`0xE1980000`, then returns `probe[6] + 0xb30`. The dev guide's logged `buf_addr: 415a7ae8` pins the
mapping **RAM `0x415A7000` ↔ ROM `0xE1980000`**, and `dual_iso.c:1301` still carries the
now-commented `PHOTO_CMOS_ISO_START = 0x415a7b30` from before the scan existed. Every ROM offset in
this document is therefore directly usable as `ram_base + offset`.

### 1a. Internal structure

The blob is a sequence of sections delimited by `ffffffff <id> ffffffff ffffffff ffffffff`, with
`<id>` in `0x00000301 … 0x00000309`. Twenty-two sections:

| id | count | data starts |
|---|---|---|
| `0x301` | 1 | `+0xAE8` |
| `0x302` | 1 | `+0xB30` ← **stills ISO table** |
| `0x303` | 5 | `+0xC34`, `+0xC78`, `+0xCAC`, `+0xCF0`, `+0xD44` |
| `0x304` | 6 | `+0xD8C`, `+0xDD4`, `+0xE1C`, `+0xE64`, `+0xEAC`, **`+0xEF4` (0xE0C bytes)** |
| `0x305` | 7 | `+0x1D14` … `+0x1EF4` |
| `0x308` | 1 | `+0x1F30` |
| `0x309` | 2 | `+0x1F88`, `+0x1FE0` |

Two kinds of section appear:

- **Base register sets** — one 13-word record listing every CMOS register the mode writes, in
  register order. `0x301` (`+0xAE8`) is the stills one; `0x304`'s five small sections
  (`+0xD8C`, `+0xDD4`, `+0xE1C`, `+0xE64`, `+0xEAC`) are the LiveView ones.
- **Per-ISO override tables** — the values of the *subset* of registers that vary with ISO.
  `0x302` (`+0xB30`) is the stills one; the single large `0x304` section (`+0xEF4`) holds the
  LiveView ones.

---

## 2. The command word, and how ML's constants map onto it

`dual_iso.c:373-377` states the 6D2 format as `0xURUUU AB F`: nibble `R` = CMOS register,
`A`/`B` = the two ISO gain fields, `F` = flag. For `0x0d03a440`: register `0xd`, gain fields
`A=4`, `B=4`, flag `0`. `CMOS_ISO_BITS = 4`, `CMOS_FLAG_BITS = 4`, `CMOS_EXPECTED_FLAG = 0`
(`dual_iso.c:1310-1312`).

`patch_cmos_iso_values_6d2()` (`dual_iso.c:332-410`) does exactly two things per entry:

1. **Sanity gate** — `if ((val & 0xffff0000) == 0x0d030000)`. Anything else is skipped silently.
2. **Rewrite field `B` only** — `iso_mask = 0x000000f0`; `val &= ~iso_mask; val |= other_iso_bits`,
   where `other_iso_bits = table[get_alternate_iso_index()] & 0xf0`.

Field `A` is left at the entry's own gain code, so entry *i* patched with alternate index *j*
becomes `0x0d03a{i}{j}0` — alternating sensor lines at gain code *i* and gain code *j*. The dev
guide's `0x0d03a040` ("ISO 100 and 1600") is this shape with *i*=0, *j*=4.

Consequences that matter for choosing a table:

- **The alternate-ISO menu index is used as a table subscript.** `get_alternate_iso_index()`
  (`dual_iso.c:186-215`) returns 0…`COUNT-1`; `other_iso_bits` is read out of the table at that
  index. If the table's index→gain map is not the identity, the menu label lies.
- **Only `0x0d03…` words are touched.** A table of `0x0d01…` words produces an all-identity patch:
  no error, no effect.

---

## 3. The three tables, decoded

### 3a. Stills — `0xE1980B30`, stride 4, count 8 (known good, hardware-confirmed)

Section `0x302`, 0xF0 bytes. It is **column-major**: eight rows (gain codes 0…7) × six register
columns, then a 12-word trailer.

```
col0 @0xE1980B30 reg 0x0d: 0d03a000 0d03a110 0d03a220 0d03a330 0d03a440 0d03a550 0d03a660 0d03a770
col1 @0xE1980B50 reg 0x38: 38120000 38120000 3c120000 3c120000 3c120000 3c120000 3c120000 3c120000
col2 @0xE1980B70 reg 0x72: 72000001 72000001 72000000 72000000 72000000 72000000 72000000 72000000
col3 @0xE1980B90 reg 0x80: 8000000c 8000000c 80000008 80000008 80000008 80000008 80000008 80000008
col4 @0xE1980BB0 reg 0x9x: 93210ba0 93210ba0 98210ba0 98210ba0 98210ba0 98210ba0 98210ba0 98210ba0
col5 @0xE1980BD0 reg 0xd0: d000e9f1 d000e9f1 d000e9f1 d000e9f1 d000e9f1 d000e9f1 d000e9f0 d000e9f0
trailer @0xE1980BF0:       f0000000 70000000 80000000 f0000000 71024015 87a30ba2 61000001 60000001
                           72000001 8000000e 61000001 60000001
```

`PHOTO_CMOS_ISO_START/COUNT/SIZE = 0xB30 / 8 / 4` reads exactly column 0. Decoded:

| index | word | gain code | nominal ISO |
|---|---|---|---|
| 0 | `0d03a000` | 0 | 100 |
| 1 | `0d03a110` | 1 | 200 |
| 2 | `0d03a220` | 2 | 400 |
| 3 | `0d03a330` | 3 | 800 |
| 4 | `0d03a440` | 4 | 1600 |
| 5 | `0d03a550` | 5 | 3200 |
| 6 | `0d03a660` | 6 | 6400 |
| 7 | `0d03a770` | 7 | 12800 |

**Note column 1 through column 4: every one of them changes value between index 1 and index 2, and
nowhere else.** Gain codes 0–1 use `reg 0x38 / 72000001 / 8000000c / 93210ba0`; codes 2–7 use
`reg 0x3c / 72000000 / 80000008 / 98210ba0`. This is a hardware gain-stage boundary, and it recurs
in every LiveView block below. It is load-bearing for §6.

### 3b. Runtime composition — proof the model is right

The dev guide's worked example ([ml/developer_guide/02_01_hardware.md](ml/developer_guide/02_01_hardware.md), ADTG section) is a
CMOS_write logged **from a 6D2** at `buf_addr: 415a7ae8`. That is `blob + 0xAE8` = section `0x301`,
the stills base record. Compare ROM against the log:

```
ROM  0xE1980AE8: 0d03a000 10717220 21a30100 38120000 4476520a 50000010 60000021
                 72000001 8000000c 90210ba0 a0000000 d000e9f1 e00009f1 ffffffff
log  0x415A7AE8: 0d03a440 10717220 21a30100 3c120000 4476520a 50000010 60000021
                 72000000 80000008 98210ba0 a0000000 d000e9f1 e00009f1 ffffffff
                 ^^^^^^^^                   ^^^^^^^^                   
                 col0[4]                    col1[4]  col2[4] col3[4]  col4[4]
```

Five words differ, and all five are exactly row 4 (gain code 4 = ISO 1600) of the §3a columns.
So: **Canon holds a base record, copies the per-index override values into it, and hands the
result to `CMOS_write`.** ML patches the *override table*, not the buffer — which is why
`PHOTO_CMOS_ISO_START` is `+0xB30` and not `+0xAE8`, and why the same approach transfers to the
movie table unchanged.

### 3c. LiveView / movie — one array of 104 records at `0xE1980EF4`, in four blocks

Section `0x304`'s large member (`+0xEF4`, 0xE0C bytes) is **row-major**: a contiguous run of
104 records of 7 words (`0x1C`) each, i.e. **four blocks of 26 records**, block stride `0x2D8`.
The 7 words are the 7 registers that vary in LiveView — the stills six plus register `0x10`.

Each 26-record block is a **1/3-stop ISO ladder**. Run lengths of the gain code are
`2,3,3,3,3,3,3,6`: three 1/3-stops per full stop, with the first full stop having no −1/3 entry
below it and the top gain code covering the digital-push region. Full stops therefore sit at
record `3k`, which is what makes `SIZE = 0x54 = 3 × 0x1C` the documented
"lie about the size to skip 1/3 stops" idiom (`dual_iso.c:411-419`).

| block | address | offset from stills base | cmd prefix | reg 0x10 word | gain ladder (26 records) |
|---|---|---|---|---|---|
| **0** | **`0xE1980EF4`** | **+0x3C4** | `0d03` | `10717220` | `0 0 1 1 1 2 2 2 3 3 3 4 4 4 5 5 5 6 6 6 7 7 7 7 7 7` |
| 1 | `0xE19811CC` | +0x69C | `0d03` | `10717220` | `0 0 1 1 1 3 3 3 3 3 3 4 4 4 5 5 5 6 6 6 7 7 7 7 7 7` |
| 2 | `0xE19814A4` | +0x974 | **`0d01`** | `1871723e` | `0 0 1 1 1 3 3 3 3 3 3 4 4 4 5 5 5 6 6 6 7 7 7 7 7 7` |
| 3 | `0xE198177C` | +0xC4C | `0d03` | `10717a20` | `0 0 1 1 1 3 3 3 3 3 3 4 4 4 5 5 5 6 6 6 7 7 7 7 7 7` |

Blocks 1, 2 and 3 **skip gain code 2 entirely**, using code 3 for six consecutive 1/3-steps
(nominal ISO 320 through 1000). Block 0 is the only one with the full monotone 0…7 ladder.

Block 0 in full, with the eight records a `SIZE = 0x54, COUNT = 8` walk actually reads:

```
 rec  address     off    ISO~     record (7 words)
  0  0xE1980EF4  +0x3C4    100   0d03a000 10717220 38120000 72000001 8000000c 93210ba0 d000e9f1  <== sampled
  1  0xE1980F10  +0x3E0    125   0d03a000 10717220 38120000 72000001 8000000c 93210ba0 d000e9f1
  2  0xE1980F2C  +0x3FC    160   0d03a110 10717220 38120000 72000001 8000000c 93210ba0 d000e9f1
  3  0xE1980F48  +0x418    200   0d03a110 10717220 38120000 72000001 8000000c 93210ba0 d000e9f1  <== sampled
  4  0xE1980F64  +0x434    250   0d03a110 10717220 38120000 72000001 8000000c 93210ba0 d000e9f1
  5  0xE1980F80  +0x450    320   0d03a220 10717220 3c120000 72000000 80000008 98210ba0 d000e9f1
  6  0xE1980F9C  +0x46C    400   0d03a220 10717220 3c120000 72000000 80000008 98210ba0 d000e9f1  <== sampled
  7  0xE1980FB8  +0x488    500   0d03a220 10717220 3c120000 72000000 80000008 98210ba0 d000e9f1
  8  0xE1980FD4  +0x4A4    640   0d03a330 ...
  9  0xE1980FF0  +0x4C0    800   0d03a330 10717220 3c120000 72000000 80000008 98210ba0 d000e9f1  <== sampled
 10  0xE198100C  +0x4DC   1000   0d03a330 ...
 11  0xE1981028  +0x4F8   1250   0d03a440 ...
 12  0xE1981044  +0x514   1600   0d03a440 10717220 3c120000 72000000 80000008 98210ba0 d000e9f1  <== sampled
 13  0xE1981060  +0x530   2000   0d03a440 ...
 14  0xE198107C  +0x54C   2500   0d03a550 ...
 15  0xE1981098  +0x568   3200   0d03a550 10717220 3c120000 72000000 80000008 98210ba0 d000e9f1  <== sampled
 16  0xE19810B4  +0x584   4000   0d03a550 ...
 17  0xE19810D0  +0x5A0   5000   0d03a660 ... d000e9f0
 18  0xE19810EC  +0x5BC   6400   0d03a660 10717220 3c120000 72000000 80000008 98210ba0 d000e9f0  <== sampled
 19  0xE1981108  +0x5D8   8000   0d03a660 ... d000e9f0
 20  0xE1981124  +0x5F4  10000   0d03a770 ... d000e9f0
 21  0xE1981140  +0x610  12800   0d03a770 10717220 3c120000 72000000 80000008 98210ba0 d000e9f0  <== sampled
 22  0xE198115C  +0x62C  16000   0d03a770 ... d000e9f0
 23  0xE1981178  +0x648  20000   0d03a770 ... d000e9f0
 24  0xE1981194  +0x664  25600   0d03a770 ... d000e9f0
 25  0xE19811B0  +0x680  32000   0d03a770 ... d000e9f0
```

The `ISO~` column is inferred from the 1/3-stop run-length structure anchored at gain code 0 ↔
ISO 100 (the stills correspondence); it is not written anywhere in the ROM. The top four records
reuse gain code 7 with digital gain, exactly as the 200D comment predicts for its own top entries
(`dual_iso.c:1487-1490`).

The eight sampled words are **bit-for-bit identical to the stills table**:

```
block0 @ stride 0x54: 0d03a000 0d03a110 0d03a220 0d03a330 0d03a440 0d03a550 0d03a660 0d03a770
stills @ stride 0x04: 0d03a000 0d03a110 0d03a220 0d03a330 0d03a440 0d03a550 0d03a660 0d03a770
```

The same gain-stage discontinuity as stills appears at the code 1→2 boundary (records 4→5):
`38120000 → 3c120000`, `72000001 → 72000000`, `8000000c → 80000008`, `93210ba0 → 98210ba0`.

**Tail of the section.** After block 3 (`0xE1981A54 … 0xE1981CC4`) come two column-major arrays of
26 rows × 3 columns — register `0x10` as `10717620 / 10717a20 / 10717e20`, and register `0x38/0x3c`
as `…120000 / …12000d / …12001a` — followed by one 15-word record beginning `0f03a000`. These are
per-ISO overrides for three further readout variants of the same ladder. They contain no
`0x0d03…` words and are not dual-ISO patch targets, but they show the section is shared by more
modes than the four blocks alone.

---

## 4. Which one is the movie table, and why

### 4a. What the referencing code says: nothing (honest negative result)

I searched all 32 MiB of ROM0 at both 4-byte and 2-byte alignment for the literals `0xE1980B30`,
`0xE1980EF4`, `0xE1980F10`, `0xE19811CC`, `0xE198177C`, `0xE19814A4` and `0xE1982000`.

**Zero occurrences of any of them.** The only literal in the ROM is the blob base `0xE1980000`
(5 occurrences: `0xE0040968`, `0xE0065FAC`, `0xE0066B58`, `0xE0067018`, plus one unaligned
coincidence at `0xE0B1FC7E`), and all four aligned ones are in the FixData *save/checksum/property*
plumbing described in §1 — `SaveFixToFile`, `CheckSumOfFixData`, `PROPAD_CreateFROMPropertyHandle`.
The nearest Canon source-path strings in that region are
`./DevCommon/PathParam/Utility/Yuv2JpegEncode.c` (`0xE0067200`) and `./ShootVfx/ShootVFX.c`
(`0xE0067B14`) — unrelated translation units that merely happen to be adjacent.

**There is no "referencing function" to find, and no LiveView TU path string to attribute.** The
tables are not addressed by literal at all. Canon walks the DMA'd copy by parsing the
`ffffffff <id>` section markers and indexing records; the section id and record index come from
sensor-mode state, not from a compiled-in address. This is a real limit on what static analysis can
settle here, and it is why §4c ends in a ranking rather than a proof.

### 4b. Two candidates eliminated outright

**`0xE1980F10` is not a table.** It is `0xE1980EF4 + 0x1C` — record 1 of block 0, the ISO +1/3
entry. Its 8-word stride-`0x54` walk does produce gain codes 0…7 (that is why the README's scanner
flagged it), but every word it lands on is a 1/3-stop-above-full-stop record. Patching it means:
at ISO 100/200/400/800/…, dual-ISO has no effect; at ISO 125/250/500/1000/… it works. That is
worse than not shipping — it is an intermittent feature that looks like a hardware flake. The
README's reading of these two as "two *phases* of one structure — very likely the 200D's
video / video LV pair" is wrong: they are one array, and the 200D's four arrays are separated by a
whole array length (0xC0), not by one record (0x8).

**`0xE19814A4` (block 2) is un-patchable by the current code.** All 26 of its records carry the
`0x0d01` prefix, and `patch_cmos_iso_values_6d2()` gates on `(val & 0xffff0000) == 0x0d030000`
(`dual_iso.c:379`). The `other_iso_bits` pre-check *passes* (the gain nibble is still valid), so
there is no error message; every item is skipped and `apply_patches()` installs an identity patch.
Symptom: dual-ISO reports enabled, produces nothing. If a future session wants to test block 2 it
must relax the gate to `(val & 0xfff00000) == 0x0d000000` — which should not be done casually,
since the gate is what stops a wrong address from writing gain nibbles into unrelated registers.

### 4c. Block 0 over blocks 1 and 3 — the positive case

| evidence | block 0 (`0xEF4`) | blocks 1, 3 (`0x11CC`, `0x177C`) |
|---|---|---|
| stride-`0x54` sample vs known-good stills table | **bit-identical** | index 2 and index 3 both yield `0d03a330` |
| index → gain code map | identity (0…7), as ML assumes | not injective; menu "400" and "800" are the same setting |
| offset from stills base | +0x3C4 | +0x69C, +0xC4C |
| 200D's video table offset from its stills base | +0x3BC (8 bytes away) | +0xC0 and +0x290 further out |
| gain-stage boundary | at code 1→2, as in stills | code 2 absent entirely |

Three independent points favour block 0:

1. **ML's model holds exactly.** `dual_iso.c` assumes table index *i* selects gain code *i* —
   `get_alternate_iso_index()` returns "full stops of ISO. 0: 100, 1: 200, 2: 400" (`dual_iso.c:180-183`)
   and the menu renders `raw2iso(72 + index*8)` (`dual_iso.c:924-927`). Only block 0 satisfies that.
   On block 1 or 3 the menu would offer "400" and "800" as distinct choices that behave identically.
2. **The 200D's video table sits at +0x3BC from its stills base; block 0 sits at +0x3C4** — eight
   bytes apart across two different bodies of the same DIGIC generation. Blocks 1 and 3 are 0xC0
   and 0x290 further out. On the 200D, +0xC0 past the video table is the *photo-LiveView* table
   ("changes photo LV (but not photos), and neither vid LV nor video", `dual_iso.c:1508-1512`).
3. **Block 0 is the only LiveView block that uses the sensor's full analog range.** Blocks 1–3 skip
   gain code 2, i.e. they trade one analog step for digital gain across nominal ISO 320–1000. That
   is the signature of a *reduced* readout, not of the primary one.

**What this does not prove.** No ROM evidence names which capture mode block 0 drives. It could be
movie 1x, movie + video LiveView (as on the 200D, where one array serves both), or photo LiveView.
Static analysis narrows four candidates to one strongly-preferred and two testable fallbacks; it
cannot close the last step. **The measurement that closes it is Phase 1 of the spike plan already:**
run `adtglog2`, step ISO in movie LiveView, and read `buf_addr` — it will be one of the `0x304`
base records (`+0xD8C`, `+0xDD4`, `+0xE1C`, `+0xE64`, `+0xEAC`), and the register values written
into it identify the block by their `reg 0x10` word: `10717220` → block 0 or 1, `1871723e` →
block 2, `10717a20` → block 3. Two ISO steps across the code 1→2 boundary (e.g. ISO 200 then
ISO 400) separate block 0 from block 1 in one capture: block 0 writes `0d03a220`, block 1 writes
`0d03a330`.

---

## 5. The proposed diff

Cross-checking the 200D (`dual_iso.c:1478-1520`), a DIGIC 7 body needs: a bespoke
`patch_cmos_iso_values_XXX()` (6D2 already has one), `FRAME_CMOS_ISO_*` inflated by 3× to skip
1/3 stops (200D uses `COUNT = 7`, `SIZE = 24 = 0x18 = 8*3`), and the `CMOS_*_BITS` descriptors
(already set for the 6D2). The 6D2's equivalent is the same shape with `SIZE = 0x54 = 0x1C*3` and
`COUNT = 8` (one more native gain code than the 200D — the existing comment at `dual_iso.c:360`
already notes this).

The RAM-base-relative form is required because the DMA destination moves; the precedent is 50D
(`dual_iso.c:1426-1430`) and 650D (`:1547-1551`), both guarded on `PHOTO_CMOS_ISO_START != 0`.

**Do not apply — `ml/` is off-limits for this task.** Proposed change to
[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/modules/dual_iso/dual_iso.c](ml/modules/dual_iso/dual_iso.c), block starting at line 1298:

```diff
     else if (is_camera("6D2", "1.1.1"))
     {
         is_6d2 = 1;
         PHOTO_CMOS_ISO_START = get_photo_cmos_iso_start_6d2();
         PHOTO_CMOS_ISO_COUNT = 8;
         PHOTO_CMOS_ISO_SIZE  = 4;
 
+        // FixData blob (ROM 0xe198_0000, DMA'd to heap; PHOTO start is blob + 0xb30).
+        // LiveView table is blob + 0xef4: 26 records of 0x1c bytes, a 1/3-stop ladder,
+        // so full stops are every 3rd record.  Cross-check: 200D's video table is
+        // +0x3bc from its stills base, this is +0x3c4.
+        // Three sibling blocks at +0x11cc, +0x14a4 (0x0d01 cmd, needs a relaxed sanity
+        // check), +0x177c; all three skip gain code 2, so their index->gain map is not
+        // 1:1 and the menu label would lie.  Try those only if +0xef4 drives the wrong mode.
+        FRAME_CMOS_ISO_START = PHOTO_CMOS_ISO_START
+                             ? PHOTO_CMOS_ISO_START - 0xb30 + 0xef4 : 0;
+        FRAME_CMOS_ISO_COUNT = 8;   // gain codes 0..7 == ISO 100..12800
+        FRAME_CMOS_ISO_SIZE  = 0x54; // 0x1c * 3: skip the 1/3 stops
+
         CMOS_ISO_BITS = 4; // bit size of *each* ISO field
         CMOS_FLAG_BITS = 4; // bit size of all flags
         CMOS_EXPECTED_FLAG = 0;
     }
```

What the patch then writes, at alternate-ISO index 3 (ISO 800), verified against ROM:

```
0xE1980EF4  0d03a000 -> 0d03a030      0xE1981044  0d03a440 -> 0d03a430
0xE1980F48  0d03a110 -> 0d03a130      0xE1981098  0d03a550 -> 0d03a530
0xE1980F9C  0d03a220 -> 0d03a230      0xE19810EC  0d03a660 -> 0d03a630
0xE1980FF0  0d03a330 -> 0d03a330      0xE1981140  0d03a770 -> 0d03a730
```

Mechanics checked, no further changes needed:

- `patch_cmos_iso_values_6d2()` handles the stride natively (§0). One `struct patch` of
  `size = 8 * 0x54 = 0x2A0` at `start_addr`.
- `apply_patches()` supports >4-byte data patches on DIGIC 678X (`patch.c:100-108` requires
  `size >= 4`; `patch.c:143-172` mallocs `size * 2` and `memcmp`s the pre-image). `0x2A0 * 2` =
  1344 bytes of heap.
- **The patched span stays inside block 0.** Last patched word at `0xE1981140`; span ends at
  `0xE1981194`; block 1 begins at `0xE19811CC`. Asserted in the check script. This is worth keeping
  in mind if anyone raises `COUNT` — `COUNT = 9` would run the span to `0xE19811E8`, *into block 1*.
- `dual_iso_refresh()` bounds-checks `FRAME_CMOS_ISO_COUNT` (8) against `COUNT(backup_ph)` (20) —
  the arrays are swapped (`dual_iso.c:635-636`, the latent bug the README noted) but 8 < 20 either
  way, so it is still harmless.
- `dual_iso_disable()` (`dual_iso.c:564-601`) takes the "one large patch → one `unpatch_memory`"
  branch only `if (is_200d)`. The 6D2 falls into the per-item loop, but iteration *i=0* calls
  `unpatch_memory(start_addr)` which is the registered patch address, so the revert succeeds and
  iterations 1–7 fail harmlessly on unregistered addresses. Cosmetic; `is_200d || is_6d2` would be
  correct. This is already the situation for stills today.

---

## 6. Connecting to session 5's +1.71 EV measurement

### What the ROM asserts

The record-index→ISO ladder in §3c is the ROM stating its own intent: record `3k` carries gain
code `k`, and the records between them are 1/3-stop steps. Anchored at gain code 0 ↔ ISO 100
(from the stills table, which is hardware-confirmed), **the ROM says gain code *k* is nominally
ISO 100·2^k — one full stop per code.** So:

| menu index | menu label (`raw2iso(72 + index*8)`) | gain code pair at base ISO 100 | **EV the table promises** |
|---|---|---|---|
| 1 | 200 | (0,1) | 1.00 |
| 2 | 400 | (0,2) | 2.00 |
| 3 | 800 | (0,3) | **3.00** |
| 4 | 1600 | (0,4) | 4.00 |
| 5 | 3200 | (0,5) | 5.00 |

Session 5 measured **+1.705 to +1.709 EV**, repeatable to ±0.005 EV over three frames, with cr2hdr
independently reporting 1.71–1.72 EV.

### The verdict the ROM supports

**1.71 EV corresponds to no index. The table under-delivers.** The ROM's index→ISO map is a
*nominal ISO label*, not a measured analog gain, and there is no scaling of it that lands on 1.71:

- if the menu was at index 3 (the config default, `dual_iso.c:76`), the sensor delivered 0.569 EV
  per nominal stop — 57 % of nominal;
- if the menu was at index 2, it delivered 0.855 EV per nominal stop — 85 % of nominal.

Neither is 100 %, so **"the camera did what it was told" is ruled out either way** — which is the
useful part of this answer, because it holds without knowing the menu setting.

### New ROM evidence that the steps are not uniform

Session 5 could not separate index 2 from index 3 because its noise-model fit assumed a uniform
analog step (0.729 EV/stop average, from which index 3 → 2.19 EV and index 2 → 1.46 EV — the
measurement sits between them). The ROM shows why a uniform model is the wrong prior:

1. **There is a hardware gain-stage boundary between gain code 1 and gain code 2.** In the stills
   table, four of the six register columns change value at exactly that boundary and nowhere else
   (§3a). The same break appears in block 0 between records 4 and 5 (§3c). Codes 0–1 and codes 2–7
   are two different amplifier configurations, so the code 1→2 step is not the same physical size
   as the others.
2. **Gain code 2 is expendable.** Three of the four LiveView blocks omit it entirely, covering
   nominal ISO 320–1000 with code 3 plus digital gain. Canon would not do that if code 2 were a
   clean 1-EV step in those modes.

That is consistent with session 5's analog/digital-split hypothesis and sharpens it: the shortfall
is not evenly spread, it is concentrated near the bottom of the ladder — which is exactly the
region a 100/800 pairing spans.

### What settles it, cheaply

- **The owner's menu readout.** `dual_iso.c:927` renders `MENU_SET_VALUE("%d/%d", raw2iso(iso2), raw2iso(iso1))`
  — "100/800" or "100/400". One question, and the 0.569-vs-0.855 ambiguity is gone.
- **The index sweep already proposed in session 5 §7.3.** Shooting one static scene at indices 1–5
  maps gain code → achieved EV directly. That table is then a *prediction* for movie mode, and it
  doubles as the block-1-vs-block-0 discriminator: whatever index 2 measures in stills, block 0
  must reproduce in movie, and block 1 or 3 would instead reproduce the index-3 value.

---

## 7. Risk assessment for a first movie-mode test

### Transient by construction

Everything here is an `apply_patches()` write into the **heap copy** of FixData, not FixData
itself. `IS_ROM_PTR()` is false for the target (`patch.c:112`), so no MMU/ROM remap is involved;
`unpatch_memory()` reverts it; a power cycle discards the whole DMA'd copy. Nothing writes FROM,
ROM or the bootflag. `apply_patches()` additionally `memcmp`s the pre-image and refuses on
mismatch (`patch.c:161-172`), so a stale or wrong address fails closed rather than corrupting.

### Failure modes, most likely first

1. **Nothing happens.** The most probable outcome, and it is silent in three distinct ways:
   wrong block (block 2 → all items skipped by the `0x0d03` gate, no error), wrong phase
   (`0xF10` → only 1/3-stop ISOs affected), or block 0 simply not being the mode's table. Plan for
   "no visible change" being the *expected* first result, and instrument for it (see §7 test below)
   rather than concluding the address is wrong.
2. **Striped or uniform-brightness frames.** The 200D notes (`dual_iso.c:290-296`) record that
   "unusual" gain pairs misbehave: `4400` and `4040` work, `4440` gives uniform brightness, `6420`
   gives two bright / two dark. If a 6D2 pairing produces a flat frame, vary the ISO pair before
   abandoning the address.
3. **Line-skipping incompatibility — the real ceiling.** `dual_iso.c:1510-1511` on the 200D:
   video "uses line skipping [so] this doesn't work with the current un-dual-iso code, you get odd
   patterns of bright/dark lines". This is a *capture-side* symptom (wrong lines get amplified),
   distinct from the post-processing wall. It is why the 200D shipped movie dual-ISO for x5/x10
   zoom only. Expect it on 6D2 full-frame movie; x5 zoom is the mode most likely to work.
4. **LiveView loss / ERR70 / ERR80.** Observed on other bodies when the CMOS path is fed values it
   dislikes. Recovery is a battery pull. Bounded by the `0x00–0x70` nibble check
   (`dual_iso.c:352-361`) and the `0x0d03` word check — **do not relax either one** to make a
   candidate "look close".
5. **A pre-image race.** New relative to stills: the patch region is `0x2A0` bytes instead of
   `0x20`, so the `memcmp` pre-image window is 21× larger. If Canon rewrites any byte of block 0
   between the `memcpy` in `patch_cmos_iso_values_6d2()` and the `memcmp` in `apply_patches()`,
   the patch is refused with `E_PATCH_OLD_VALUE_MISMATCH` and the menu shows `ISOless LV err(n)`.
   Annoying, not dangerous, and it self-identifies.
6. **`ASSERT: m_VSize` @ `ImgSeqCoopStore.c:194`.** Session 5's crash. Per
   [crash-analysis.md](.planning/spikes/007-dual-iso-scoping/crash-analysis.md), this is ML calling
   `ImgSeqCoopStore::GetVSize()` (the 6D2's only route to FPS timer B) before Canon has called
   `SetVSize()` — a LiveView-startup ordering problem in ML's FPS/raw path. **Nothing in this diff
   touches it**: dual-ISO writes CMOS gain nibbles and never reads a timer. But it will fire on the
   same button presses that get you into raw movie LiveView, so it is a likely *interruption* of the
   test and should not be mistaken for a dual-ISO regression. Reach a stable raw LiveView first,
   *then* enable dual ISO.

### Safest first test

`dual_iso_refresh()` gates the movie path on `raw_mv = is_movie_mode() && lv && raw_lv_is_enabled()`
(`dual_iso.c:632`), so nothing happens at all until raw LiveView is up. Use that:

1. Card with `adtglog2.mo` and the patched `dual_iso.mo`. Battery accessible.
2. Movie mode, raw video enabled, **do not record**. Reach a stable LiveView and confirm the
   `m_VSize` assert has not fired.
3. Log CMOS writes with `adtglog2` while stepping ISO 200 → 400 with dual-ISO **off**. This
   single capture identifies the block before anything is patched: the `buf_addr` names the base
   record, and the `reg 0x10` word (`10717220` / `1871723e` / `10717a20`) plus the gain code at
   ISO 400 (`0d03a220` = block 0, `0d03a330` = block 1/3) name the block. **If the log says a block
   other than 0, stop and change the constant — do not shoot.**
4. Only then enable dual ISO at a *conservative* index — **index 1 (100/200)**, not the default 3.
   One gain code of separation is the smallest change that is still detectable, and it keeps the
   pair inside the same amplifier configuration (codes 0 and 1 are one gain stage, §3a), which is
   the pairing least likely to hit the 200D's "unusual pattern" behaviour.
5. Observe LiveView only. If the image survives, record a short clip and check for the striping of
   failure mode 3 *before* investing in post-processing.

Do not use `adtg_gui` for any of this — its `gdb_add_watchpoint` mechanism does not exist on MMU
cams, and a1ex's "this is not a toy; it can destroy your sensor" warning is about exactly the
free-hand register poking `adtglog2` avoids.

---

## 8. Corrections to the spike README

| README §4d claim | correction |
|---|---|
| "Searching that blob … yields **exactly three tables**" | One stills table plus **one 104-record array in four blocks**. Two of the four blocks the README did not find. |
| Candidates `0xE1980EF4` and `0xE1980F10` are "two *phases* of one structure — very likely the 200D's video / video LV pair" | They are records 0 and 1 of the *same* block. `0xE1980F10` is the ISO +1/3 entry and must not be used. The 200D's arrays are 0xC0 apart, not 0x1C. |
| "Two further arrays … at `0xE19811CC` and `0xE198177C`; these are the 1/3-stop-granular variants" | *All four* blocks are 1/3-stop granular, `0xE1980EF4` included. `0x11CC` and `0x177C` are sibling blocks with a *degenerate* ladder (gain code 2 omitted). A third sibling at `0xE19814A4` was missed entirely. |
| "Also required: `patch_cmos_iso_values_6d2()` … must patch the word at each record's offset 0 rather than a contiguous run. Expect a modest rework" | Not required. The function already indexes by `item_size * i` and preserves intervening bytes. The diff is constants only. |

---

## 9. What could not be established

- **Which capture mode block 0 drives.** No ROM literal references any table address; the mode is
  selected at runtime by section-marker walk. §4c ranks the four blocks on three independent
  grounds and block 0 wins all three, but this is a ranking, not a proof. One `adtglog2` capture in
  movie LiveView settles it (§7 step 3).
- **The meaning of the section ids `0x301`–`0x309`** and of the `0x0d01` vs `0x0d03` command
  prefix. Both are consistent with "mode class" / "sub-command", neither is decoded.
- **The absolute ISO of record 0.** Inferred as 100 from the stills-table gain-code correspondence
  and the 1/3-stop run-length structure; not written in the ROM.
- **EV per gain code.** The ROM stores index codes, never gains. §6 establishes the table's
  *nominal* promise (1 EV per code) and that the hardware does not meet it; the actual per-code
  values require the stills index sweep.
- **Whether a 6D2 movie mode reads the sensor without line skipping.** Unchanged from the README —
  this remains the biggest risk to the whole feature, and it is a post-processing question, not an
  address question.


---

## ADVERSARIAL VERIFICATION — IDENTIFICATION NOT SUPPORTED (treat as open 4-way)

An independent agent re-derived these claims from primary sources (HOLDS: False).
Act on the corrected version below, not on the text above where they conflict.

WHAT IS ACTUALLY TRUE, in the three places the claim set is wrong or overstated:

1. CLAIM 13 (200D parallel) is false. The 200D's video table is +0xC0 from its stills base (0xe0aaa2fc -> 0xe0aaa3bc), not +0x3BC. +0x3BC is measured from 0xe0aaa000, which is only the stills address rounded down and has no counterpart to the 6D2's 0xE1980000 (a real DMA source base that ROM0 names "FixData.bin" at 0xE0066B58). The "8 bytes apart" is a coincidence between two incompatible quantities. The deliverable's comparison table row "200D's video table offset from its stills base | +0x3BC" should read "+0xC0". Delete this point from the evidence; it currently props up the identification. Additionally, the 200D's four sub-arrays all share one shape and include stills, whereas the 6D2's stills table is a different shape in a different section from the 104-record array — so the 6D2 blocks are not the 200D's {stills, video, photoLV, zoom} set and the 200D supplies no ordering.

2. CLAIM 12 over-generalizes. The 0x38-column amplifier break sits at gain code 1->2 only in the stills table (row 2) and block 0 (record 5). In blocks 1, 2, 3 and in the previously unnoticed trailing 26x3 variant array at 0xE1981B8C it sits at record 8, mid-run of gain code 3. The break is anchored to record index (ISO), not to the gain code. This inverts the force of the argument: block 0 is the outlier whose schedule matches STILLS, and on this sensor the movie readout is the line-skipped one that should NOT match stills. So "block 0 uses the full analog range" is at least as consistent with block 0 being photo-LiveView or x5/x10 zoom as with movie.

3. THE HEADLINE overstates two things.
(a) "the table is 0xE1980EF4" is not usable as written. dual_iso.c:1155 states ROM patching does not work on the 6D2, and the shipping stills patch targets the DMA'd RAM copy via get_photo_cmos_iso_start_6d2(). The §5 diff gets this right (PHOTO_CMOS_ISO_START - 0xb30 + 0xef4), so the diff is correct — but the RAM translation is load-bearing and the headline hides it. Anyone reading only the headline would write the ROM address and get a silent no-op.
(b) "constants-only" understates one behavioural change. SIZE=0x54 patches only records 0,3,6,...,21, so dual ISO is silently inactive at every 1/3-stop movie ISO (125,160,250,320,500,640,1000,...). Stills cannot hit this because the 6D2 stills table has only 8 entries — full stops only, 0xC0 bytes, section 0x303. This matches the 200D's known behaviour and is not a defect in the diff, but it is user-visible and should be stated.

TWO FIXES TO THE BODY-TEST PLAN (both concrete, both from my own ROM scan):
- The predicted buf_addr list of 0x304 base records is incomplete. Markers 0x304 sit at 0xE1980D78, DC0, E08, E50, E98, EE0, so the SIX records start at blob +0xD44, +0xD8C, +0xDD4, +0xE1C, +0xE64, +0xEAC. The document lists five and omits +0xD44 (which begins 0d01a000). Also, section 0x305 contains its own 15-word base record at blob +0x1CC4 (0f03a000 10717220 21a30100 38120000 4404500a ...) — an untested alternative for buf_addr that the plan does not anticipate.
- The reg 0x10 discriminator should note that 10717620 and 10717e20 also exist in ROM (the 26x3 variant array at 0xE1981A54) and belong to none of the four blocks. A buf_addr showing either means the camera is not using any of the four.

BOTTOM LINE ON THE IDENTIFICATION: not supported. Of the three offered points, one is arithmetically wrong, one is selection bias, and one points ambiguously or against. Blocks 0 and 1 are byte-identical for records 0-4. There is no ROM reference to any block in any addressing form. Treat the capture as an open four-way identification, not as confirmation of block 0 — but do run it, because it discriminates all four in a single capture at ISO 400.
