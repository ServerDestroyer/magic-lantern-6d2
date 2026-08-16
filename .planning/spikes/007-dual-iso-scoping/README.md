# Spike 007 — Dual-ISO on the 6D2: scoping

**Status:** research complete, read-only. No source modified, nothing built.
**Date:** 2026-08-15
**Tree:** `ml/` @ `dev` (3f24042a4)

---

## TL;DR — the premise was wrong in our favour

The task was framed as "port dual-ISO to the 6D2". **It is already ported for stills and it
already works on the body.** Upstream commit `87f24974d` ("6d2: enable dual ISO",
stephen-e, 2024-12-19) says: *"Tested for stills. Doesn't mangle mov recording."*

What is actually missing is exactly one thing: **`FRAME_CMOS_ISO_START` is never set for the
6D2**, so dual-ISO is inert in movie/LiveView mode. The module is additionally marked hidden
in the GUI on this body.

This spike therefore reframes to: *what does it take to (a) unhide the working stills path and
(b) light up the movie path?* Answer to (b): three concrete, testable ROM table addresses
recovered below, and roughly a 6-line diff to try each.

---

## 1. dual_iso's exact per-model requirements

Source: [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/modules/dual_iso/dual_iso.c](ml/modules/dual_iso/dual_iso.c)

### The six constants (declared `dual_iso.c:113-119`)

| Constant | Meaning | Consumed at |
|---|---|---|
| `FRAME_CMOS_ISO_START` | address of the LiveView/movie ISO table (RAM or ROM) | `:665`, `:668`, `:876` |
| `FRAME_CMOS_ISO_COUNT` | number of ISO entries in that table | `:635`, `:668`, `:865` |
| `FRAME_CMOS_ISO_SIZE` | stride in bytes between consecutive ISO entries | `:647`, `:668` |
| `PHOTO_CMOS_ISO_START` | address of the stills ISO table | `:657`, `:661` |
| `PHOTO_CMOS_ISO_COUNT` | entries | `:636`, `:661`, `:865` |
| `PHOTO_CMOS_ISO_SIZE` | stride | `:653`, `:661` |

Plus three bitfield descriptors (`dual_iso.c:166-168`):

| Constant | Meaning |
|---|---|
| `CMOS_ISO_BITS` | width in bits of *each* of the two ISO fields |
| `CMOS_FLAG_BITS` | width of the flag field below them |
| `CMOS_EXPECTED_FLAG` | sanity value the flag field must equal |

Masks derived at `:170-171`. Generic decode at `:491-492`:
`iso1 = (raw >> CMOS_FLAG_BITS) & CMOS_ISO_MASK`,
`iso2 = (raw >> (CMOS_FLAG_BITS + CMOS_ISO_BITS)) & CMOS_ISO_MASK`.

### How they're consumed

`dual_iso_enable(start, size, count, backup)` (`:436`) walks `count` entries at
`start + i*size`, backs each up, sanity-checks the flag field, then rewrites the *second*
ISO field of every entry to the alternate ISO's gain bits and pushes the change through
`apply_patches()`. `dual_iso_disable()` reverts from the backup. Both are driven from
`dual_iso_refresh()` (`:625-690`), gated on `raw_ph` (stills RAW) or `raw_mv`
(`is_movie_mode() && lv && raw_lv_is_enabled()`).

**The 6D2 does not use the generic path.** `dual_iso.c:459-462` short-circuits:

```c
if (is_6d2)
    return patch_cmos_iso_values_6d2(start_addr, size, count);
```

with the in-tree rationale at `:445-458`: the generic code assumes 16-bit items at a fixed
offset, *"Neither of these things holds for 6d2."*

### The 6D2 branch as it stands (`dual_iso.c:1298-1315`)

```c
else if (is_camera("6D2", "1.1.1"))
{
    is_6d2 = 1;
    PHOTO_CMOS_ISO_START = get_photo_cmos_iso_start_6d2();
    PHOTO_CMOS_ISO_COUNT = 8;
    PHOTO_CMOS_ISO_SIZE  = 4;
    CMOS_ISO_BITS = 4;
    CMOS_FLAG_BITS = 4;
    CMOS_EXPECTED_FLAG = 0;
}
```

`FRAME_CMOS_ISO_START` is left at its file-scope initialiser `0`. **That single zero is the
whole of the missing movie feature.**

`patch_cmos_iso_values_6d2()` (`:332-410`) is 6D2-specific: item is a 32-bit CMOS command
word of shape `0x0d03aXY0`; `iso_mask = 0x000000f0` selects the second ISO nibble; entries
are validated with `(val & 0xffff0000) == 0x0d030000` and the extracted nibble must be one
of `0x00,0x10,…,0x70` (eight native ISOs — *"one more 'native' ISO than 200D"*).

`get_photo_cmos_iso_start_6d2()` (`:1163-1217`) does not hardcode a RAM address. Canon DMAs
the table from ROM `0xE1980000` into heap; the function scans `0x780000 → 0x880000` for the
DMA descriptor holding that source address, validates it (`probe[0]==probe[1]==probe[4]==probe[5]`),
takes `probe[6]` as the aligned destination base and returns **`probe[6] + 0xb30`**
(`dual_iso.c:1199`). Uncacheable-address check included. Returns `0` on failure, which safely
disables the feature.

> Care: there are three near-identical `get_photo_cmos_iso_start_*()` functions with different
> offsets — 650D `+0xde4` (`:1043`), 550D `+0x1244` (`:1120`), 6D2 `+0xb30` (`:1199`). Do not
> cross-wire them. The 6D2 value `0xb30` is independently corroborated by the ROM: the stills
> table sits at `0xE1980B30`, i.e. exactly `0xb30` into the `0xE1980000` blob that gets DMA'd.

**Precedent for deriving the movie table by fixed offset:** two other bodies already do exactly
what §4d proposes — `dual_iso.c:1428` (50D) `FRAME_CMOS_ISO_START = PHOTO_CMOS_ISO_START + 0x12b0`
and `:1549` (650D) `... + 0x124a`, both guarded by `if (PHOTO_CMOS_ISO_START != 0)`. The 6D2
change would follow this established shape, not invent one.

### is_camera gating and unsupported-body behaviour

`dual_iso_init()` is one long `if/else if` chain over `is_camera(model, fw)` with **no final
`else`**. An unrecognised body leaves all six constants at `0`. Consequences:

- `:657` `... && PHOTO_CMOS_ISO_START` — false, stills patching never runs.
- `:665` `... && FRAME_CMOS_ISO_START` — false, movie patching never runs.
- `:876` `if (mvi && !FRAME_CMOS_ISO_START)` → menu shows
  `"Dual ISO does not work in movie mode on your camera."`

So the module **loads and is harmless** on an unsupported body; it just does nothing.
This is exactly the 6D2's *current* movie-mode state — the "unsupported" warning is live
on this camera today.

### Closest structural analogues

**200D 1.0.1 (`dual_iso.c:1478-1520`) is the analogue, and it is very close.** Same DIGIC 7
generation, same MMU/`patch_mmu` world, same command-word format family, and it is the only
other body with a bespoke `patch_cmos_iso_values_XXXd()`. Its recorded table map is the
template for ours:

```
PHOTO_CMOS_ISO_START = 0xe0aaa2fc;  // +2fc changes stills, not video
FRAME_CMOS_ISO_START = 0xe0aaa53c;  // +53c changes x5 and x10 zoom modes
// +3bc changes video and video LV (but not photo LV)
// +47c changes photo LV (but not photos)
FRAME_CMOS_ISO_COUNT = 7;
FRAME_CMOS_ISO_SIZE  = 24;   // 0x18, 0x8 * 3
CMOS_ISO_BITS = 8; CMOS_FLAG_BITS = 4; CMOS_EXPECTED_FLAG = 0;
```

Two lessons carry over: (a) the stills and video tables are **separate arrays a few hundred
bytes apart in the same ROM blob**, and (b) `..._SIZE` is deliberately inflated to a multiple
of the real record size to skip 1/3-stop intermediates (`dual_iso.c:414-434` documents this
"we lie about size" idiom).

### Latent bug spotted in passing

`dual_iso.c:635-636` checks the wrong arrays against each other:

```c
if (FRAME_CMOS_ISO_COUNT > COUNT(backup_ph)) goto end;
if (PHOTO_CMOS_ISO_COUNT > COUNT(backup_lv)) goto end;
```

FRAME is bounds-checked against the *photo* backup and vice versa. Both arrays are `[20]`
and both counts are ≤9 today, so it is currently harmless — but it is wrong, and worth an
upstream one-liner.

---

## 2. How the constants were historically found

### The tooling is in this tree — under `dev_tools/`, not `modules/` directly

`ml/modules/adtg_gui/` does not exist (this is why a first-pass search misses it). The real
locations:

- [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/modules/dev_tools/adtg_gui/](ml/modules/dev_tools/adtg_gui/) — a1ex-era interactive register browser
- [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/modules/dev_tools/adtg_log/](ml/modules/dev_tools/adtg_log/) — g3gg0's original logger, 5D3-hardcoded
- [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/modules/dev_tools/adtglog2/](ml/modules/dev_tools/adtglog2/) — **the modern rewrite, and it already supports the 6D2**

### What adtg_gui hooks, and why it will not serve us

`adtg_gui.c:69-70` holds `ADTG_WRITE_FUNC` / `CMOS_WRITE_FUNC` (plus `CMOS2_`, `CMOS16_`),
filled per body in `adtg_gui_init()` (`adtg_gui.c:1000+`). It installs GDB-style watchpoints:

```c
if (ADTG_WRITE_FUNC)   bkpt1 = gdb_add_watchpoint(ADTG_WRITE_FUNC, 0, &adtg_log);   // :226
if (CMOS_WRITE_FUNC)   bkpt2 = gdb_add_watchpoint(CMOS_WRITE_FUNC, 0, &cmos_log);   // :227
```

The per-body addresses are annotated with **the exact marker strings used to find them**,
e.g. `adtg_gui.c:1023-1024` for the 500D:

```c
ADTG_WRITE_FUNC = 0xFF22F8F4; //"[REG] @@@@@@@@@@@@ Start ADTG[CS:%lx]"
CMOS_WRITE_FUNC = 0xFF22F9DC; //"[REG] ############ Start CMOS"
```

That is the historical method: find the `DebugMsg` format string in the ROM, find the
function that references it, that function *is* the register write path.

**adtg_gui is D45-only in practice.** Its `gdb_add_watchpoint` mechanism does not exist on
the MMU cams, and it carries no D7 entries. It does not need porting — `adtglog2` replaced it.

### adtglog2 — already ported to the 6D2

`README.rst`: *"Re-implementation of ADTG logging, supporting both MMU and older cams."*
Author `names_are_hard`. Instead of watchpoints it applies a **function-hook patch** via
`convert_f_patch_to_patch()` / `apply_patches()`. The 6D2 entry (`adtglog2.c` init):

```c
else if (is_camera("6D2", "1.1.1"))
{
    buf_item_size = 32;
    struct function_hook_patch f_patches[] = {
        {
            .patch_addr = 0xe053cdc4, // CMOS_write
            .orig_content = {0x2d, 0xe9, 0xfc, 0x5f, 0x04, 0x46, 0x94, 0x4f},
            .target_function_addr = (uint32_t)hook_CMOS_write_6D2,
            .description = "Log ADTG CMOS writes"
        },
    };
    ...
}
```

Added by commit `b65dbcc1b` ("adtglog2: add 6D2 support", 2024-11-11). The Thumb trampoline
lives in `modules/dev_tools/adtglog2/hooks_thumb_6D2.c`, built `-mthumb -march=armv7`.

That commit also contains the smoking gun for how the stills table was found — a hack left
commented out in the logger:

```c
// FIXME horrible hack, quickly test modifying command buffer for 6D2 inside the logger, yuck
// Tested and works.  Now to find out where these values come from.
// if (cmos_buf[cmos_i] == 0x0d03a110) { cmos_buf[cmos_i] = 0x0d03a140; } // hopefully ISO 200/1600
```

Log first, mutate in the hook to prove the effect, *then* go find the backing table. That is
the exact playbook to reuse for the movie path.

### Documented procedure

[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/developer_guide/02_01_hardware.md](ml/developer_guide/02_01_hardware.md), "ADTG" section (~line 133+), documents this
formally, and its worked example is **logged from a 6D2**:

```
CMOS_write, time: 24461,  LR: e0302d23, buf_addr: 415a7ae8
    data: 0d03a440 10717220 21a30100 3c120000 4476520a 50000010 60000021 72000000
          80000008 98210ba0 a0000000 d000e9f1 e00009f1 ffffffff
```

*"this commands CMOS register 0xd to sample the sensor at ISO 1600 … `0x0d03a110` would mean
ISO 200."* Recommended method: change ISO, take a picture, diff two logs.

Note `buf_addr: 415a7ae8` — this pins the runtime mapping **RAM `0x415A7000` ↔ ROM `0xE1980000`**,
which is what makes the ROM addresses in section 4 directly actionable.

---

## 3. DIGIC 7 prior art

Assessed from the tree itself, which is stronger evidence than forum recall.

**The ADTG/CMOS write path exists and is fully understood on DIGIC 7.** Two D7 bodies have
working CMOS-write hooks and working dual-ISO:

| Body | DIGIC | CMOS_write hook | Stills dual-ISO | Movie dual-ISO |
|---|---|---|---|---|
| 200D 1.0.1 | 7 | `0xE034256E` | yes (`d0f6fb328`) | partial — x5/x10 zoom only (`192b5c3f3`) |
| 6D2 1.1.1 | 7 | `0xE053CDC4` | yes (`87f24974d`) | **not implemented** |

So there is no D7 blocker of principle. What differs from D45:

- **Command width.** 6D2 uses 32-bit command words (`buf_item_size = 32`); 70D uses 16.
- **Command structure.** `dual_iso.c:450-455`: *"We also can't trivially adapt the 200D logic,
  because the protocol is quite different there. 4 apparent ISO channels and a different
  command structure."* 200D has four ISO channels; the 6D2 encodes both ISOs in one nibble
  pair of a single word.
- **Table location.** D45 tables sit at fixed RAM addresses. D7 tables are DMA'd from ROM to
  a heap address that moves, hence `get_photo_cmos_iso_start_6d2()`.
- **Hooking.** `gdb_add_watchpoint` (D45) → `patch_mmu` function-hook patches (D7/D8).
- **No ENGIO involvement.** `grep -c ENGIO` over ROM0 returns **0**, and 6D2's `consts.h` has
  no ENGIO defines. The CMOS/ADTG path here is the command-buffer protocol, not engio register
  pokes. Only `DSEngIo.c` (a filename string, `0x5EB2A0`) appears.

**Known D7 sensor register facts (6D2, from this ROM + tree):**

- CMOS register `0xd` is the ISO/gain register.
- Command word shape `0x0dRRaXY0`: `0d` = register 0xd, `X`/`Y` = the two ISO gain fields
  (4 bits each, values 0–7), low nibble a flag (always 0 observed).
- Eight native ISO gain steps: `0x0d03a000` (100) … `0x0d03a770` (12800).
- A **dual** value has X≠Y: the developer guide gives `0x0d03a040` = alternate lines at
  ISO 100 and 1600. This confirms `iso_mask = 0x000000f0` patches the `Y` field while `X`
  stays at the user's selected ISO — exactly what `patch_cmos_iso_values_6d2()` does.

**Hook mechanics on the 6D2** (`modules/dev_tools/adtglog2/hooks_thumb_6D2.c`): the command
buffer arrives in `r0`; the overwritten instructions are `push {r2-r12,lr}` / `mov r4, r0` /
`ldr r7, =0x91a38`; the trampoline returns via `ldr pc, =0xe053cdcd` (Thumb, +1).

**DIGIC 8 has nothing.** No `is_camera()` entry for M50, R, RP, 850D, R5, R6, M6II, SX70 or
SX740 exists in `dual_iso.c`, `adtglog2.c` or `adtg_gui.c`, and no D8 body has any known
ADTG/CMOS write address. Likewise no 77D or 800D work despite being D7 siblings of the 200D.
The 6D2 is one of only two D7 bodies with any of this — it is at the frontier, not behind it.

**The known D7 limitation, stated upstream** (`192b5c3f3`, 200D):

> *"Dual ISO in full frame is not yet useful, this mode uses line skipping, and the
> combination of that plus alternating dual ISO lines breaks cr2hdr and mlvapp code.
> It should be possible to get some dual ISO effect, but would require new post processing."*

This is a **post-processing** limitation, not a capture limitation — and it is the single
biggest risk to the 6D2 movie work (see §5).

### Survey caveat and outcome

A parallel forum/GitHub survey was run. Two results worth recording:

- **magiclantern.fm is entirely unreachable** — forum, wiki and builds all sit behind a
  Cloudflare bot challenge that defeated direct fetch, a browser UA, and a proxy. No
  forum-sourced quotes are available for this or any near-term spike. Plan research
  accordingly: the source tree and commit messages are the usable record.
- **No GitHub issue or PR exists on D7/D8 dual ISO or ADTG.** The nearest is
  [issue #73, "Fix cause of isoless err() on more cams"](https://github.com/reticulatedpines/magiclantern_simplified/issues/73)
  (open), which concerns older bodies.

The survey independently reproduced every load-bearing finding in this document from the same
primary sources. Our `ml/` checkout is at upstream `dev` HEAD (`3f24042a4`), so **this tree is
the state of the art** — there is no newer external work to catch up on.

Secondary confirmation that the 200D shipped these features:
[CineD](https://www.cined.com/magic-lantern-is-back-and-supports-new-cameras-such-as-eos-200d-6d-mark-ii-and-7d-mark-ii/) —
*"the EOS 200D has working RAW video, with DPAF, and Dual ISO"*.

---

## 4. 6D2 ROM reconnaissance

ROM0, 32 MiB, base `0xE0000000`; file offset = address − base.

### 4a. Marker strings (`strings -a -t x ROM0.BIN`)

All the classic adtg_gui-era markers are present, clustered in one driver blob:

| File offset | Address | String |
|---|---|---|
| `0x53C4A8` | `0xE053C4A8` | `Sio0DrvADTG` |
| `0x53CAF8` | `0xE053CAF8` | `Sio0DrvCMOS` |
| `0x53CB08` | `0xE053CB08` | `Sio0DrvIFE` |
| `0x53CB58` | `0xE053CB58` | `[REG] @@@@@@@@@@@@ Start ADTG[CS:%lx:%lx]` |
| `0x53CB88` | `0xE053CB88` | `[REG] ADTG:[0x%08x]` |
| `0x53D0E0` | `0xE053D0E0` | `[REG] @@@@@@@@@@@@ Start ADTGDMA[CS:%lx:%lx]size:%d` |
| **`0x53D124`** | **`0xE053D124`** | **`[REG] ############ Start CMOS`** |
| `0x53D14C` | `0xE053D14C` | `[REG] CMOS:[0x%08x]` |
| `0x53D578` | `0xE053D578` | `[REG] @@@@@@@@@@@@ Start CMOSDMA[%lx]size:%d` |
| `0x53D5C4` | `0xE053D5C4` | `[REG] ############ Start IFE` |
| `0x4C190` | `0xE004C190` | `[REG]---[%3ld]:[%#08lx]` |
| `0x55C04` | `0xE0055C04` | `FA_GetCmosGainAddr %ld 0x%lx` |
| `0x515524` | `0xE0515524` | `[DEBUG] RegisterSendCMOSGainCBR` |
| `0xF98C2C` / `0xF98C4C` | `0xE0F98C2C` / `0xE0F98C4C` | `SEQ_ADTG` / `SEQ_CMOS` |

Counts: 13 `adtg`, 36 `cmos`, **0 `ENGIO`**. ROM1 is barren — one bare `CMOS` string at
`0x34E46C`; all sensor driver code is in ROM0.

### 4b. The write functions are already identified and byte-verified

`CMOS_write` = **`0xE053CDC4`** (Thumb). Verified against the ROM:

```
bytes at 0xE053CDC4:  2d e9 fc 5f 04 46 94 4f
adtglog2 orig_content: 2d e9 fc 5f 04 46 94 4f   ← exact match
```

(`push.w {r2-r7,r9,r10,r11,r12,lr}; mov r4,r0; ldr r7,[pc,#…]`)

Note the locality: `CMOS_write` at `0xE053CDC4` sits **0x360 bytes before** its own log string
`[REG] ############ Start CMOS` at `0xE053D124`, in the same `Sio0DrvCMOS` blob. This is the
classic string→function adjacency, and it independently corroborates the address.

`ADTG_write` has **not** been extracted for the 6D2 and is not in any stub table. Its string
lives at `0xE053CB58`; by symmetry with `Sio0DrvCMOS` the function should lie a few hundred
bytes below it, around `0xE053C5xx–0xE053CBxx`. Not needed for dual-ISO — the ISO gain rides
on the CMOS path — so this is noted, not chased.

### 4c. Stub table / veneer table

[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/platform/6D2.111/stubs.S](ml/platform/6D2.111/stubs.S) holds 161 entries.
**None** relate to ADTG/CMOS/ENGIO. The only near-neighbour is
`stubs.S:82  THUMB_FN(0x30900, shamem_read)`, commented *"nearly always inlined, so very few refs."*

The Canon veneer table at `0xE043A000` therefore contributes nothing here: `CMOS_write` is
reached by direct call inside the Sio0Drv blob, not via a veneer, and adtglog2 already
patches it directly. **No new stub is required for this work.**

### 4d. The ISO tables — the actionable find

Scanning all 8 M words of ROM0 for the 6D2 ISO command shape `0x0d03aXY0` gives 133 words
matching `0x0d03____`, of which 91 are ISO-gain-shaped, **all inside `0xE1980000–0xE1982000`** —
one contiguous sensor-config blob, the one Canon DMAs to `0x415A7000`.

Searching that blob for constant-stride runs with monotonically increasing ISO index yields
**exactly three tables**:

| # | ROM start | `..._SIZE` | `..._COUNT` | Offset from stills base | RAM (per dev-guide mapping) |
|---|---|---|---|---|---|
| 1 | `0xE1980B30` | `0x4` (4) | 8 | `+0x000` | `0x415A7B30` |
| 2 | `0xE1980EF4` | `0x54` (84) | 8 | `+0x3C4` | `0x415A7EF4` |
| 3 | `0xE1980F10` | `0x54` (84) | 8 | `+0x3E0` | `0x415A7F10` |

**Table 1 is the known-good stills table.** It is a dense packed array, and it is precisely
what `get_photo_cmos_iso_start_6d2()` returns (`probe[6] + 0xb30`):

```
0xe1980b30:  0d03a000 0d03a110 0d03a220 0d03a330 0d03a440 0d03a550 0d03a660 0d03a770
```

Eight entries, stride 4, ISO 100→12800 — matching `PHOTO_CMOS_ISO_COUNT = 8`,
`PHOTO_CMOS_ISO_SIZE = 4` exactly. This confirms the whole method end to end.

**Tables 2 and 3 are the movie/LiveView candidates.** The region `0xE1980EF4–0xE19811C8` is an
array of 7-word (`0x1C`-byte) CMOS command records; the ISO index advances every **three**
records, so `0x54 = 3 × 0x1C` — the exact "1/3-stop, so lie about the size" idiom documented at
`dual_iso.c:414-434`. Record shape:

```
0xe1980ef4:  0d03a000 10717220 38120000 72000001 8000000c 93210ba0 d000e9f1
0xe1980f48:  0d03a110 10717220 38120000 72000001 8000000c 93210ba0 d000e9f1   (+0x54)
0xe1980f9c:  0d03a220 ...                                                      (+0xA8)
             ... through 0d03a770
```

Tables 2 and 3 are interleaved (`0xE1980F10 − 0xE1980EF4 = 0x1C`, i.e. adjacent records in the
same array), so they are two *phases* of one structure — very likely the 200D's "video / video LV"
pair. Two further arrays with the same `0x1C` record size but non-uniform ISO progression sit at
`0xE19811CC` (`+0x69C`) and `0xE198177C` (`+0xC4C`); these are the 1/3-stop-granular variants and
are the natural fallbacks if 2 and 3 turn out to drive the wrong mode.

**The offsets line up beautifully with the 200D map.** 200D: stills `+0x2FC`, video `+0x3BC`,
photo-LV `+0x47C`, zoom `+0x53C`. 6D2: stills `+0x000`, candidates `+0x3C4` / `+0x3E0`,
then `+0x69C`, `+0xC4C`. Same blob, same layout family, offsets within tens of bytes of the
200D's video table. This is strong prior-art corroboration that candidate 2 or 3 is the
video table.

**Crucially, no new address-finding is needed at runtime.** `get_photo_cmos_iso_start_6d2()`
already recovers the RAM base as `probe[6]`; a movie table is just a different constant offset
from that same base:

```c
uint32_t base = get_photo_cmos_iso_start_6d2();      // = ram_base + 0xb30
PHOTO_CMOS_ISO_START = base;
FRAME_CMOS_ISO_START = base ? base - 0xb30 + 0xef4 : 0;   // candidate 2
FRAME_CMOS_ISO_COUNT = 8;
FRAME_CMOS_ISO_SIZE  = 0x54;
```

That is the entire experiment.

---

## 5. Risk, plan, and effort

### Current packaging state (question: why is it `.hid`?)

Mechanism: `platform/Makefile:254` runs `platform/create_hid_files.py modules.hidden ZIP_MODULES_DIR`,
which touches an empty `<name>.hid` beside each module. `src/module.c:132` — *"Modules are
invisible if they have a .hid file of their name"* — hides them in the GUI unless the user
sets **Modules → Show hidden modules** (`src/module.c:2063-2066`, requires restart).

Per-platform survey of `modules.hidden` / `modules.included`:

- **6D2.111**: `dual_iso` is in **both** — it ships in the zip **and** is hidden in the GUI.
- **200D.101**: `hidden` has 16 entries, `dual_iso` is **not** among them → visible.
- All D45 bodies (5D3, 6D, 70D, 700D, …): empty `modules.hidden` → visible.
- Every other D7/D8 body (77D, 80D, M50, R, R5, R6, RP, 850D, SX70, 5D4, 7D2, 750D, 5DSR):
  `dual_iso` hidden.

So the `.hid` is the **generic new-port default** — "built, shipped, not blessed" — not a
6D2-specific verdict. The mechanism was introduced wholesale by commit `41ec65338`
(2025-03-28, "modules: limit modules in zip, allow hidden modules"):

> *"Hidden modules can still be manually enabled. This cleans up the spam of included modules
> for new cams that couldn't use them, and makes them safer; it was possible for a module to
> meet all symbols deps but be unsafe on new cams."*

**No commit message or issue anywhere gives a 6D2-dual_iso-specific reason for hiding it.**
The 200D was explicitly promoted out of it once stills worked. The 6D2 reached the same
milestone (`87f24974d`) but was never promoted — note it is the *only* body listed in both
`modules.included` and `modules.hidden`, which reads as "shipped but not signed off".
**Unhiding is a one-line deletion from `platform/6D2.111/modules.hidden`.**

### Plan

**Phase 0 — verify what already works (no code change).**
Show hidden modules → load `dual_iso` → shoot RAW stills at 100/1600 → run `cr2hdr`.
Confirms `87f24974d` on *this* body before building anything on top. If this passes,
`modules.hidden` loses a line and stills dual-ISO ships.

**Phase 1 — capture (adtglog2, already 6D2-capable).**
Build `adtglog2`, put it on the card, log CMOS writes while stepping ISO 100→12800 in:
(a) stills, (b) movie/LiveView 1x, (c) x5 zoom. Diff the logs. Goal: read the `buf_addr`
values in movie mode and confirm which of `ram_base+0xEF4` / `+0xF10` / `+0x11CC` / `+0x177C`
the movie path actually reads.

**Phase 2 — prove the effect before finding the table.**
Reuse stephen-e's own trick: re-enable the commented hack in `adtglog2.c` to rewrite
`0x0d03aXY0` in-flight during movie LiveView. If the image changes, the movie path is
patchable; if not, stop — no table hunt will help.

**Phase 3 — set the constants.**
Add `FRAME_CMOS_ISO_START/COUNT/SIZE` to the 6D2 branch using the offset arithmetic above.
Try candidate 2 (`+0xEF4`), then 3 (`+0xF10`), then the `+0x69C` / `+0xC4C` arrays.
Also required: `patch_cmos_iso_values_6d2()` currently assumes a packed 4-byte table; with
`SIZE = 0x54` it must patch the word at each record's offset 0 rather than a contiguous run.
Expect a modest rework there, mirroring how the 200D variant handles its stride.

**Phase 4 — capture and post-process.**
Record raw video with mlv_lite (already working on this body per the roadmap), then confirm
`cr2hdr` / MLVApp can actually demosaic it. **This is where 200D stalled.**

### What can brick vs. what is transient

**Transient — everything in this plan.** All changes are `apply_patches()` RAM patches to a
DMA'd heap copy of sensor config, reverted by `dual_iso_disable()` and unconditionally gone on
power cycle. Nothing writes ROM. Failure modes observed on other bodies: garbage/striped frames,
"isoless err", LiveView freeze, ERR70/ERR80 → pull the battery. `adtglog2` is a card-loaded
module; a bad build means ML does not load, not that the camera dies.

**Real but bounded risk:** writing an out-of-range ISO nibble to the CMOS gain register. The
existing sanity checks contain this — `patch_cmos_iso_values_6d2()` rejects anything outside
`0x00–0x70` and refuses to patch unless `(val & 0xffff0000) == 0x0d030000`. Keep both when
extending to `SIZE = 0x54`; do not relax them because a candidate table "looks close".

**Expect some ISO pairs simply not to work.** The 200D notes (`dual_iso.c:~300`) record that
*"'unusual' patterns aren't accepted, somehow. 4400 or 4040 both work. 4440 results in all
lines appearing the same brightness. 6420 seems to make two bright, two dark. So, this is not
fully understood."* If a 6D2 movie pairing produces a uniform-brightness frame, that is this
phenomenon, not a wrong table address — vary the ISO pair before abandoning a candidate.

Note also a1ex's standing warning in the `adtg_gui` README: *"this is not a toy; it can destroy
your sensor."* That applies to free-hand register poking in `adtg_gui`, which we are not doing —
`adtglog2` logs, and `dual_iso` writes only validated gain nibbles — but it is the reason for
keeping the sanity checks intact.

**The genuine brick risk is elsewhere and is not touched by this work:** anything writing the
FROM/ROM or the bootflag. Dual-ISO does none of that.

### Effort

| Phase | Sessions | Confidence |
|---|---|---|
| 0 — verify stills, unhide | 0.5 | high |
| 1 — adtglog2 capture + diff | 1 | high |
| 2 — in-flight mutation proof | 0.5–1 | high |
| 3 — set constants, rework stride | 1–2 | medium |
| 4 — raw video + post-processing | 1–3 | **low** |

**Realistic total: 4–7 sessions** to a working movie-mode capture, and that is the honest
number only if phases 0–2 go cleanly. Stills-only (phase 0) is genuinely half a session.

### Biggest unknown

**Not the register addresses — the post-processing.** The capture side is de-risked: the write
function is byte-verified, the tooling is 6D2-ported, the table layout is mapped, and the offset
arithmetic is a six-line diff. What is unknown is whether the 6D2's movie mode reads the sensor
in a way that survives alternating-line dual ISO. The 200D hit exactly this wall — full-frame
video uses line skipping, and line skipping *plus* dual-ISO line alternation *"breaks cr2hdr and
mlvapp code"* — which is why 200D movie dual-ISO shipped only for x5/x10 zoom, where there is no
skipping. Spike 006 evidence (`mlv-analysis-2.md:115`) shows the 6D2 reporting identical
binning/skipping across all tested modes, which does not yet tell us whether an unskipped mode
exists.

Concretely: **we may well succeed at making the sensor capture dual-ISO video on the 6D2 and
still have no tool that can develop the result.** Budget for x5/x10 zoom being the only usable
movie mode, exactly as on the 200D, and treat full-frame as a research item requiring new
post-processing rather than a port.

---

## First concrete next action

Build `adtglog2` for 6D2.111 and run Phase 0+1 together in one body session: enable
**Show hidden modules**, confirm stills dual-ISO actually works on this camera, then log CMOS
writes across ISO 100→12800 in stills, movie 1x, and x5 zoom. The `buf_addr` values in that log
decide which of the mapped candidate tables is the movie table — and that single answer converts
the rest of this from research into a six-line diff.

Practical note: `adtglog2` appears in **no** body's `modules.included`, so it is build-from-source
only — `make` it in `modules/dev_tools/adtglog2/` and copy `adtglog2.mo` to the card manually.
It writes `adtg.log` to the card, unlimited size.
