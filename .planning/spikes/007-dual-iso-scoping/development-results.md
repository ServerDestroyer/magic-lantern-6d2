# Spike 007 — Developing the 6D2's first dual-ISO photographs

**Date:** 2026-08-15 (session 6). Follows `session5-results.md`.

## Verdict in three lines

1. `cr2hdr` **works** on 6D2 dual-ISO CR2s. `_MG_2218` and `_MG_2217` merge to valid
   DNGs; the merged output has **no residual line-pair modulation** (+0.0005 to
   +0.0012 EV over 6.4 M pixel pairs per row class). Viewable previews are in
   `footage/previews/`.
2. The **6D2 CMOS ISO table is not defective**. I read it out of the ROM: it is exactly
   the 8-entry linear ladder `0x0d03a000, a110, a220 … a770` that `dual_iso.c` expects.
   The module's patch writes exactly the code the menu selected. **The camera did what
   it was told.**
3. The 1.71 EV is a **labelling** problem, not a table problem: on this sensor **one
   CMOS gain-code step is not one photographic stop**. Whichever index was selected,
   the code step delivered 1.715/index EV. The available evidence weakly favours menu
   index 2 (`100/400`) over the module default index 3 (`100/800`), but **I cannot
   settle which index was set from these files**. It is recoverable in one step — see
   §9.

---

## 1. Build

The binary is host-side and must be **32-bit** (`ml/src/raw.h:219` asserts
`SIZE_CHECK_STRUCT(raw_info, 0xa0)`; `struct raw_info` is 160 bytes only when `void*`
is 4 bytes). `nix-shell -p pkgsi686Linux.gcc` does not work — it leaves the native
x86_64 gcc first on `PATH`. Call the i686 compiler by store path instead. Verbatim,
reproduced from clean this session:

```sh
CC=$(nix-build '<nixpkgs>' -A pkgsi686Linux.stdenv.cc --no-out-link)/bin/gcc
# /nix/store/w05rbq6zskxgyzmk3drg8s7q8z6jm4jl-gcc-wrapper-15.2.0/bin/gcc
$CC -dumpmachine          # -> i686-unknown-linux-gnu

D="…/ml/modules/dual_iso"
$CC -mno-ms-bitfields -O2 -w -I"$D/../../src" -I"$D/build" -D_FILE_OFFSET_BITS=64 \
    -fno-strict-aliasing -msse -msse2 -std=gnu99 \
    "$D/cr2hdr.c" "$D/../../src/chdk-dng.c" "$D/dcraw-bridge.c" "$D/exiftool-bridge.c" \
    "$D/adobedng-bridge.c" "$D/amaze_demosaic_RT.c" "$D/dither.c" "$D/timing.c" \
    "$D/kelvin.c" -o "$W/cr2hdr" -lm
```

Notes:

- `-m32` is **dropped** — the compiler is already i686; passing it re-triggers the
  missing `gnu/stubs-32.h`.
- `-I$D/build` supplies the already-generated `module_strings.h`. Nothing is written
  into the repo: the single-invocation compile puts temporaries in `$TMPDIR` and `-o`
  points at scratch. `git status` was clean before and after.
- `Makefile.cr2hdr` was **not** used. It assumes a MinGW/`-m32` host setup and pulls in
  the module build system; the direct invocation above is smaller and does the same job.
- At runtime `cr2hdr` shells out to `dcraw` and `exiftool`
  (`exiftool-bridge.c:14,26` use `system()`/`popen()`), so both must be on `PATH`:
  `NIXPKGS_ALLOW_INSECURE=1 nix-shell -p dcraw exiftool` (dcraw 9.28, exiftool 13.59).

Binary: `…/scratchpad/dualiso-dev/cr2hdr` (149 560 B, ELF i686). CR2s were copied into
`…/scratchpad/dualiso-dev/run/` — disclosed scratch, nothing left in the repo.

---

## 2. cr2hdr output, verbatim

Run as `cr2hdr <file>.CR2` with no options, all five session-5 stills. Full log:
`…/scratchpad/dualiso-dev/cr2hdr_all.log`.

### `_MG_2218.CR2` — merged

```
cr2hdr: a post processing tool for Dual ISO images

Last update: (null)
Active options:
--amaze-edge    : use a temporary demosaic step (AMaZE) followed by edge-directed interpolation (default)
--cs2x2         : apply 2x2 chroma smoothing in noisy and aliased areas (default)
--wb=graymax    : set AsShotNeutral by maximizing the number of gray pixels (default)

Input file      : _MG_2218.CR2
Camera          : Canon EOS 6D Mark II (unknown, assuming 5D Mark III)
Full size       : 6384 x 4224
Active area     : 6264 x 4180
Black borders   : 120 left, 44 top
Black level     : 512
ISO pattern     : BBdd RGGB
White levels    : 16283 14883
Noise levels    : 8.94 9.03 7.60 7.69 (14-bit)
ISO difference  : 1.72 EV (329)
Black delta     : 1.86
Black adjust    : -36
Dynamic range   : 11.02 (+) 10.64 => 12.35 EV (in theory)
Looking for hot/cold pixels...
Cold pixels     : 113
AMaZE interpolation ...
Amaze took 1.23 s
Edge-directed interpolation...
Semi-overexposed: 3.11%
Deep shadows    : 92.79%
Horizontal stripe fix...
Full-res reconstruction...
ISO overlap     : 6.3 EV (approx)
Half-res blending...
Chroma smoothing...
Building alias map...
Filtering alias map...
Smoothing alias map...
Final blending...
Noise level     : 147.78 (20-bit), ideally 143.08
Dynamic range   : 12.74 EV (cooked)
Black adjust    : 0
AsShotNeutral   : 0.80 1 0.32, 2444K/g=0.85 (gray max)
Output file     : _MG_2218.DNG
_MG_2218.DNG    : copying EXIF from _MG_2218.CR2
```

### `_MG_2217.CR2` — merged

```
Input file      : _MG_2217.CR2
Camera          : Canon EOS 6D Mark II (unknown, assuming 5D Mark III)
Full size       : 6384 x 4224
Active area     : 6264 x 4180
Black borders   : 120 left, 44 top
Black level     : 512
ISO pattern     : BBdd RGGB
White levels    : 10000 5000
Noise levels    : 8.96 9.05 7.63 7.69 (14-bit)
ISO difference  : 1.71 EV (328)
Black delta     : 1.24
Black adjust    : -24
Dynamic range   : 10.28 (+) 8.95 => 10.67 EV (in theory)
Looking for hot/cold pixels...
Cold pixels     : 44
AMaZE interpolation ...
Amaze took 1.23 s
Edge-directed interpolation...
Semi-overexposed: 0.00%
Deep shadows    : 99.43%
Horizontal stripe fix...
Full-res reconstruction...
ISO overlap     : 5.6 EV (approx)
Half-res blending...
Chroma smoothing...
Building alias map...
Filtering alias map...
Smoothing alias map...
Final blending...
Noise level     : 147.70 (20-bit), ideally 143.58
Dynamic range   : 12.01 EV (cooked)
Black adjust    : 0
AsShotNeutral   : 0.58 1 0.43, 3579K/g=0.85 (gray max)
Output file     : _MG_2217.DNG
_MG_2217.DNG    : copying EXIF from _MG_2217.CR2
```

### `_MG_2216.CR2` — **rejected** (false negative)

```
Input file      : _MG_2216.CR2
Camera          : Canon EOS 6D Mark II (unknown, assuming 5D Mark III)
Full size       : 6384 x 4224
Active area     : 6264 x 4180
Doesn't look like interlaced ISO
```

This is a **cr2hdr detection-threshold failure, not a capture failure**. My own
regression on the same file finds slope 3.2592 / 3.2548 (+1.705 / +1.703 EV) over
151 362 and 109 577 pixel pairs, and its masked-region noise splits 8.98 / 7.66 exactly
like the other two (§5). The frame is simply too dark (`MeasuredEV` 0.12, the room
light was still off) for cr2hdr's content-based detector, which bails before it even
prints black level.

### `_MG_2215.CR2` / `_MG_2214.CR2` — controls, correctly rejected

```
Input file      : _MG_2215.CR2
Black level     : 2047
ISO pattern     : dBBd RGGB
White levels    : 16283 14883
Noise levels    : 52.47 53.78 52.58 53.56 (14-bit)
Doesn't look like interlaced ISO
ISO blending didn't work

Input file      : _MG_2214.CR2
Black level     : 2047
ISO pattern     : dddB RGGB
Bright/dark detection error
ISO blending didn't work
```

Note the four `Noise levels` for `_MG_2215` are all ≈53 — no row-class structure —
against `_MG_2218`'s clear `8.94 9.03 | 7.60 7.69` grouping.

**cr2hdr's `1.71–1.72 EV (328/329)` is an independent confirmation** of the separation:
different code path, different estimator, same answer as my regression (§5), and its
`Noise levels` match my masked-region sigmas to two decimals.

### Known cr2hdr limitation on this body

`Camera: Canon EOS 6D Mark II (unknown, assuming 5D Mark III)` — there is no 6D2 entry
in cr2hdr's camera table, so it falls back to 5D3 constants. Detection and blending are
unaffected (they are measured from the file), but the **DNG's colour matrix and white
level metadata are 5D3's**. The DNG's `UniqueCameraModel` is correctly
`Canon EOS 6D Mark II`, `BlackLevel 2050`, `WhiteLevel 65134`. Adding a 6D2 entry is a
small self-contained follow-up.

---

## 3. Previews

| Path | What it is |
|---|---|
| `footage/previews/MG_2218_dualiso.png` | `_MG_2218.DNG` (cr2hdr-merged), 2400x1602 |
| `footage/previews/MG_2218_normal.png` | `_MG_2218.CR2` developed normally, same scale |
| `footage/previews/MG_2218_crops_compare.png` | 1:1 crops, normal above / merged below |

Both were developed identically so the comparison means something:

```sh
dcraw -w -q 3 -4 -T -c _MG_2218.DNG > dual_lin.tiff   # 16-bit linear, no auto-brighten
dcraw -w -q 3 -4 -T -c _MG_2218.CR2 > norm_lin.tiff
```

The two linear renderings are not on the same scale — `dcraw -4` normalises each file's
own white to 65535. Measuring a shadow-only region (bottom-left quadrant, 3000x2000+0+2100,
contains no light source) gives means `0.00360334` (CR2) and `0.00147761` (DNG), i.e. the
merged DNG sits **2.4386x lower** = **1.286 EV of extra headroom above the CR2's clip
point**. Both were then put on one absolute scale and through one tone curve
(extended-Reinhard, `f(y)=y(1+y/W²)/(1+y)`, exposure `E=2`, `W=E·2.4386`), so **shadows
match exactly and only the highlight ceiling differs**:

```sh
magick norm_lin.tiff -set colorspace RGB -resize 2400x \
  -fx "((2*u)*(1+(2*u)/23.79))/(1+(2*u))"           -colorspace sRGB -depth 8 MG_2218_normal.png
magick dual_lin.tiff -set colorspace RGB -resize 2400x \
  -fx "((4.8772*u)*(1+(4.8772*u)/23.79))/(1+(4.8772*u))" -colorspace sRGB -depth 8 MG_2218_dualiso.png
```

**How to read them.** Because the curve is anchored on the merged file's white, the
normal development's clipped highlights top out at 221/255 — a flat grey plateau, which
is what "clipped" looks like when you stop pretending it is white. Two differences are
visible without pixel-peeping:

- **Fluorescent tube (highlight crop).** Normal: a blown, hue-shifted yellow slab with
  veiling glow — the R and G channels clip before B, so the highlight goes warm. Merged:
  neutral white, the tube's internal structure and a crisp fixture edge survive.
- **Lit cabinet surface (shadow crop).** Normal: blatant horizontal line-pair striping,
  the raw dual-ISO structure. Merged: clean, and the surface texture is resolved.

The normal development's frame mean is 26.7/255 and the merged 27.8/255 — matched
exposure, so the differences above are dynamic range, not brightness.

---

## 4. The merge is arithmetically correct

Residual line-pair modulation in `_MG_2218.DNG` (`dcraw -D -4`, row `r` against
`0.5·(row r−2 + row r+2)`, least squares through the origin):

```
row%4==0 vs ±2: n=6447384 slope=1.0007 (+0.0010 EV)
row%4==1 vs ±2: n=6473043 slope=1.0003 (+0.0005 EV)
row%4==2 vs ±2: n=6447189 slope=1.0004 (+0.0006 EV)
row%4==3 vs ±2: n=6473188 slope=1.0008 (+0.0012 EV)
```

The +1.71 EV that goes in comes out at +0.001 EV, over 6.4 M pixel pairs per class. The
merge inverted the exact structure that was measured going in. This is the strongest
single validation available and it is independent of anything cr2hdr printed.

---

## 5. Separation, re-measured from scratch

I did not take session 5's numbers on trust. Re-measured with my own script on
`dcraw -E -4` output (raw 14-bit values including the masked border — verified
unscaled: masked median 513.0 vs EXIF `AverageBlackLevel` 513):

```
_MG_2218  per-class black: 0:512.06 1:512.33 2:513.06 3:513.10
   class 0 vs 2: n=  1039921  slope=3.2573  (+1.704 EV)
   class 1 vs 3: n=   709980  slope=3.2823  (+1.715 EV)
   class 2 vs 0: n=  3565503  slope=0.3021  (-1.727 EV)
   class 3 vs 1: n=  2263254  slope=0.3029  (-1.723 EV)

_MG_2216  per-class black: 0:512.10 1:512.40 2:513.02 3:512.91
   class 0 vs 2: n=   151362  slope=3.2592  (+1.705 EV)
   class 1 vs 3: n=   109577  slope=3.2548  (+1.703 EV)
   class 2 vs 0: n=   331381  slope=0.3061  (-1.708 EV)
   class 3 vs 1: n=   260321  slope=0.3059  (-1.709 EV)

_MG_2214  per-class black: 0:2048.35 1:2048.28 2:2048.39 3:2048.48
   class 0 vs 2: n=  5613715  slope=0.9962  (-0.005 EV)
   class 1 vs 3: n=  4406653  slope=0.9957  (-0.006 EV)
   class 2 vs 0: n=  5613781  slope=0.9962  (-0.005 EV)
   class 3 vs 1: n=  4407680  slope=0.9960  (-0.006 EV)
```

Reproduces session 5 to the fourth decimal. The forward/reverse asymmetry
(3.257 vs 1/0.302 = 3.310) is ordinary errors-in-variables attenuation; the unbiased
estimate is the geometric mean, **3.28–3.29x = +1.714 to +1.719 EV**, which is exactly
what cr2hdr independently reports (`329` → 3.29x → 1.718 EV).

Masked-region read noise (left masked columns 8–110, 105 978 px per row class, 14-bit ADU):

```
_MG_2218  class 0: std=8.941  class 1: std=9.037  class 2: std=7.604  class 3: std=7.676
          grouped: rows{0,1}=8.9890  rows{2,3}=7.6403  ratio=1.1765
_MG_2216  grouped: rows{0,1}=8.9816  rows{2,3}=7.6573  ratio=1.1729
_MG_2214  grouped: rows{0,1}=52.8655 rows{2,3}=52.8409 ratio=1.0005   <- control, no split
```

Signal x3.29, read noise x1.18 → the amplification is **pre-ADC**, i.e. genuinely
analog. A post-ADC multiply would scale both by the same factor.

---

## 6. What the module actually programs

### 6.1 Code path

`ml/modules/dual_iso/dual_iso.c`:

- `dual_iso_init()` line **1298**, the 6D2 branch:
  ```c
  PHOTO_CMOS_ISO_START = get_photo_cmos_iso_start_6d2();
  PHOTO_CMOS_ISO_COUNT = 8;
  PHOTO_CMOS_ISO_SIZE  = 4;
  CMOS_ISO_BITS  = 4;   // bit size of *each* ISO field
  CMOS_FLAG_BITS = 4;
  CMOS_EXPECTED_FLAG = 0;
  ```
  `FRAME_CMOS_ISO_START` is never assigned → movie mode is off the table on this port
  (`dual_iso.c:876` warns "Dual ISO does not work in movie mode on your camera").
- `get_photo_cmos_iso_start_6d2()` line **1163** does *not* hardcode a heap address. It
  scans RAM `0x780000…0x880000` for a DMA descriptor whose source is `0xE1980000`,
  checks that four copies of that value sit at the expected offsets, then takes
  `probe[6] + 0xb30` as the table address. So the RAM table is a **DMA copy of ROM
  0xE1980000**, and `PHOTO_CMOS_ISO_START` is the RAM image of **ROM address
  0xE1980B30**.
- `patch_cmos_iso_values_6d2()` line **332** does the work:
  ```c
  uint32_t iso_mask = 0x000000f0;                       // low ISO nibble only
  uint32_t other_iso_i = get_alternate_iso_index();
  uint32_t other_iso_bits = *(uint32_t *)(old_values + item_size*other_iso_i) & iso_mask;
  // rejects anything not in {0x00,0x10,…,0x70}
  for (i = 0; i < count; i++) {
      uint32_t val = *(uint32_t *)(old_values + item_size*i);
      if ((val & 0xffff0000) == 0x0d030000) {           // sanity check
          val &= ~iso_mask;                             // clear low nibble
          val |= other_iso_bits;                        // write alternate nibble
      }
  }
  apply_patches(&patch, 1);
  ```
  Field layout, per the in-code comment: `0xURUUU AB F` — `A` and `B` are the two ISO
  nibbles (one per line group), `R` a CMOS register, `F` a flag. The patch **preserves
  `A` and overwrites `B`** with the `B` nibble of the table entry at the menu index.

### 6.2 The table itself, read out of ROM0

`ROM0.BIN` at file offset `0x01980B30` (= 0xE1980B30 − 0xE0000000):

```
[0] 0x0d03a000   iso field 0x000   A=0 B=0
[1] 0x0d03a110   iso field 0x110   A=1 B=1
[2] 0x0d03a220   iso field 0x220   A=2 B=2
[3] 0x0d03a330   iso field 0x330   A=3 B=3
[4] 0x0d03a440   iso field 0x440   A=4 B=4
[5] 0x0d03a550   iso field 0x550   A=5 B=5
[6] 0x0d03a660   iso field 0x660   A=6 B=6
[7] 0x0d03a770   iso field 0x770   A=7 B=7
--- table ends here ---
[8] 0x38120000  [9] 0x38120000  [10..15] 0x3c120000
```

**This is decisive for the "do the 6D2 tables under-deliver?" question.** The table is a
perfectly linear 8-entry ladder, `nibble == index`, `A == B` throughout, `0x0d03….0`
matching the module's `(val & 0xffff0000) == 0x0d030000` sanity check on all eight
entries, and it stops at exactly `PHOTO_CMOS_ISO_COUNT = 8`. It also matches the
in-code comment `0d03a000 == 100, 0d03a440 == 1600` (index 4 = ISO 1600 = 4 stops above
100). **There is no defect, no truncation, and no saturation in the table.**

### 6.3 What each menu index writes

`get_alternate_iso_index()` (line 180) returns a plain index 0…`max(FRAME,PHOTO)_COUNT-1`
= 0…7. Absolute mode when `dual_iso_alternate_iso >= 0`; relative mode adds a delta to
the Canon ISO index. The menu (`dual_iso_menu`, line ~945) is `Recovery ISO`,
`min=-12 max=6`, choices:

```
"-6 EV" … "-1 EV", "+1 EV" … "+6 EV", "100","200","400","800","1600","3200","6400"
   value -12…-7        value -6…-1      0     1     2     3     4      5      6
```

Default: `CONFIG_INT("dual_iso.iso", dual_iso_alternate_iso, 3)` (line 76) → **index 3,
displayed as `800`**, main menu line reading **`100/800`** (`dual_iso_update`, line 924,
prints `raw2iso(iso2)/raw2iso(iso1)`).

With the camera at ISO 100 (table entry 0 in use, `A = 0`), every menu index therefore
programs `0x0d03a0<i>0`:

| Menu index | Menu label | Register written | Nibbles A/B | **Nominal** separation | Separation at the **measured** 0.73 EV/code |
|---|---|---|---|---|---|
| 0 | `100` | `0x0d03a000` | 0 / 0 | 0 EV (module warns "nothing to do") | 0 |
| 1 | `200` | `0x0d03a010` | 0 / 1 | 1 EV | 0.73 EV |
| 2 | `400` | `0x0d03a020` | 0 / 2 | 2 EV | 1.46 EV |
| 3 | `800` (default) | `0x0d03a030` | 0 / 3 | 3 EV | 2.19 EV |
| 4 | `1600` | `0x0d03a040` | 0 / 4 | 4 EV | 2.92 EV |
| 5 | `3200` | `0x0d03a050` | 0 / 5 | 5 EV | 3.65 EV |
| 6 | `6400` | `0x0d03a060` | 0 / 6 | 6 EV | 4.38 EV |
| 7 | — | `0x0d03a070` | 0 / 7 | 7 EV | 5.11 EV |

Index 7 exists in the table but is **unreachable in absolute mode** (menu `.max = 6`);
it is only reachable in relative mode from a non-base Canon ISO. `dual_iso_check`
(line 864) nags "Consider using a less aggressive setting (e.g. 100/800)" above 4 stops,
i.e. at indices 5 and 6 — index 3 draws no warning.

---

## 7. EXIF cross-check

```
file       ISO   BaseISO  DigitalGain  AvgBlackLevel      NormalWhite  SpecularWhite  Exp     MeasuredEV
_MG_2214  12800   12800        0       2048 2048 2048 2048    13235        14558      1/15      0.50
_MG_2215  12800   12800        0       2048 2048 2048 2048    13235        14558      1/20      0.50
_MG_2216    100     100        0        513  513  513  513    13235        14558      1/100     0.12
_MG_2217    100     100        0        513  513  513  513    13235        14558      1/100     0.75
_MG_2218    100     100        0        513  513  513  513    13235        14558      1/100     7.50
```

- All three dual-ISO frames are `ISO 100 / BaseISO 100` → the camera was using **table
  entry 0**, so `A = 0` is confirmed, and the measured 1.715 EV is the gain of code `B`
  relative to code 0. This is the piece that makes the whole analysis well-posed.
- `DigitalGain = 0` on every file.
- EXIF can never show the alternate ISO. ML patches a CMOS gain table in RAM; Canon's
  metadata writer only records the menu ISO. (MLV has a dedicated `DISO` block —
  `dual_iso_mlv_rec_cbr`, line 389 — but stills have no equivalent.)
- `MeasuredEV` explains the exposure story: 2216/2217 were shot in a dark room
  (0.12 / 0.75), then the fluorescent fixture was switched on for 2218 (7.50). That is
  why 2216/2217 are near-black and why 2218 is the only usable frame. It also **rules
  out any cross-frame scene comparison** with the ISO-12800 controls (MeasuredEV 0.50,
  different framing and different light).

---

## 8. The 1.71 EV: verdict

### 8.1 What is certain

The measured 1.715 EV **is** the analog gain of CMOS code `B` relative to code 0. It is
model-free: both line groups are read through the same column ADC and the same
downstream chain in the same exposure, so their ratio is exactly the amplifier ratio.
The read-noise ratio (1.177 against a signal ratio of 3.29) proves the amplification
sits ahead of the dominant noise source, i.e. it is analog.

`2^1.715 = 3.28`, and 1.715 is not an integer. **No menu index produces a nominal 1.71 EV**
— the nominal grid is 1, 2, 3, 4, 5, 6 EV. So one of these is true:

- the sensor's gain step per CMOS code is **less than one stop**, or
- something other than the CMOS code carries the rest of Canon's ISO step, and ML only
  moves the CMOS part.

Both amount to the same operational statement: **ML's `index i ⇒ ISO 100·2^i` labelling
is inherited from Canon's ISO→code lookup, not from a measurement of the amplifier, and
on the 6D2 it over-promises.** The tables are correct data; the EV label attached to
them is what is wrong.

### 8.2 Which index — the honest answer

I cannot determine it from these files. Here is the one indirect argument available and
its exact assumptions.

Fit the standard two-source read-noise model to `_MG_2218`'s masked region, where
`σ_pre` is noise injected before the gain stage and `σ_post` after it, both in 14-bit ADU:

```
σ_hi² = (G·σ_pre)² + σ_post²      σ_hi  = 8.9890,  G = 3.29
σ_lo² =     σ_pre²  + σ_post²      σ_lo  = 7.6403
  ⇒ σ_pre = 1.511 ADU,  σ_post = 7.489 ADU
```

Apply it to `_MG_2214` (ISO 12800 = table entry 7 = **code 7**, σ = 52.8655):

```
52.8655² = (g₇·1.511)² + 7.489²   ⇒ g₇ = 34.6  ⇒ 5.11 EV of analog gain, code 0 → code 7
```

against a nominal 7.00 EV. Average **0.73 EV per code**. Now test each candidate index
for internal consistency — a CMOS column amplifier's gain per code either holds or
*falls* as the code rises (amplifiers compress at high gain; they do not expand):

| If B = | EV/code over codes 0→B | EV/code over the remaining codes B→7 | Monotone non-increasing? |
|---|---|---|---|
| 1 | 1.715 | 0.567 | yes, but 1.7 EV in one nominal stop is implausible |
| **2** | **0.858** | **0.680** | **yes** |
| 3 (default) | 0.572 | 0.850 | no — requires the amp to *gain efficiency* at high codes |
| 4 | 0.429 | 1.133 | no |
| 5 | 0.343 | 1.700 | no |
| 6 | 0.286 | 3.399 | no |

Only `B = 2` survives with a plausible gain curve, i.e. **menu `100/400`**.

**Do not treat this as established.** It rests on three assumptions I cannot test with
the files at hand:

1. `σ_post` is the same in ADU at ISO 100 and ISO 12800. If Canon scales the ADC
   reference with ISO (a common way to get gain without amplifying ADC noise), `σ_post`
   grows with ISO and `g₇ = 34.6` is an underestimate — which would push the answer
   toward index 3.
2. A single lumped `σ_pre` / `σ_post` pair describes a real multi-stage chain. It also
   absorbs fixed-pattern column noise, which inflates both terms.
3. Gain per code is monotone non-increasing.

### 8.3 Correction to `session5-results.md` §3

Session 5 argued that the black level rising 512 → 2048 between ISO 100 and ISO 12800
is "a factor of exactly 4.00x = 2.00 EV, which is what a post-ADC digital multiply does
to the offset", and used it to corroborate a ~1.9 EV digital component. **That inference
does not hold**, for a reason visible in the same EXIF block (§7):

- `NormalWhiteLevel` (13235) and `SpecularWhiteLevel` (14558) are **identical at ISO 100
  and ISO 12800**. A digital multiply of the form `out = g·adc` would scale black *and*
  white by `g`; white does not move.
- A digital multiply of the form `out = ped_out + g·(adc − ped_in)` leaves no trace in
  the black level at all — the observed black is just `ped_out`.

Either way the 4x black-level change carries no information about digital gain. The
parsimonious reading is a **pedestal change**: at ISO 12800 the read noise is σ ≈ 52.9
ADU, so a 513 pedestal would clip the noise distribution's left tail at 10σ, while 2048
gives 39σ of headroom. `DigitalGain = 0` on every file is consistent with this.

The rest of session 5's §3 — the `σ_pre`/`σ_post` fit and the ~5.1 EV analog estimate —
survives; only the black-level corroboration is withdrawn, which weakens (does not
overturn) the analog/digital-split hypothesis.

---

## 9. What could not be established, and the one step that fixes it

**Not established:** which `Recovery ISO` index was set. Neither EXIF nor the raw data
carries it, and the scene changed between the control frames and the dual-ISO frames
(§7), which closes off the one cross-frame calibration that would have settled it.

**Recoverable directly, no reshoot needed.** ML persists the setting. `MODULE_CONFIG`
values are written to `<config_dir><module>.cfg` (`ml/src/module.c:805,2239`, with
`get_config_dir()` → `ML/SETTINGS/`, `ml/src/config.c:626`). So the card that was in the
camera during session 5 holds:

```
ML/SETTINGS/dual_iso.cfg      containing:      dual_iso.iso = <index>
```

The card backup in this repo (`Backup SD card/ML/SETTINGS/`) is from 2025-09-29 and
predates dual-ISO ever being loaded — it holds only `magic.cfg` and `MENUS.CFG`. **Pull
`ML/SETTINGS/dual_iso.cfg` off the card currently in the body.** That is a file copy and
it answers §8.2 outright.

**Second-best:** the sweep already proposed in session 5 §7 — one static, correctly
exposed scene, indices 1 through 6, rerun the §5 regression. That does not just identify
the index, it *measures the 6D2's CMOS gain curve*, which is the number this port
actually needs and which no amount of analysis of these five files can produce.

**Also open:**

- Whether the 5D3 fallback constants in cr2hdr matter in practice for colour. Adding a
  6D2 entry to cr2hdr's camera table is a small self-contained change.
- cr2hdr's content-based detector rejects genuinely dual-ISO frames that are very
  underexposed (`_MG_2216`). Worth a note upstream, but the cheaper fix is to expose
  properly.
- Movie mode remains structurally unavailable (`FRAME_CMOS_ISO_START` never set on the
  6D2 branch).

---

## Artifacts

- Previews: `footage/previews/MG_2218_dualiso.png`, `MG_2218_normal.png`,
  `MG_2218_crops_compare.png`
- Merged DNGs (scratch, 54 MB each): `…/scratchpad/dualiso-dev/run/_MG_2218.DNG`,
  `_MG_2217.DNG`
- cr2hdr binary + full log: `…/scratchpad/dualiso-dev/cr2hdr`, `cr2hdr_all.log`
- Measurement scripts: `…/scratchpad/dualiso-dev/noise.py` (masked-region read noise),
  `gain.py` (line-pair gain regression), `dngres.py` (merged-DNG residual)
- Nothing was written into the repo except the three PNGs above; `footage/` is
  gitignored. `git status` clean.


---

## ADVERSARIAL VERIFICATION — cr2hdr result SURVIVES, EV direction REFUTED

An independent agent re-derived these claims from primary sources (HOLDS: False).
Act on the corrected version below, not on the text above where they conflict.

Two corrections to the deliverable, plus one addition.

1. HEADLINE, and claim 6's broader form. Replace "a 6D2 CMOS gain-code step is worth less than one stop" with "a 6D2 CMOS gain-code step is not worth exactly one stop; it is worth 1.71/B EV, where B is the menu index that was set and is unknown." The "less than" direction requires B >= 2 and is unsupported: if the menu was on index 1 ("100/200"), one code step is worth 1.71 EV — more than a stop. The narrow claim ("no menu index yields a nominal 1.71 EV, so a code step is not one stop") is correct and should be kept; only the direction must be dropped. The rest of the framing — table not defective, module wrote the selected code, the EV label rather than the table is what over-promises — survives.

2. CLAIM 9 (speculative, "probably index 2") should be withdrawn, not merely downgraded. (a) Its stated exclusion is arithmetically wrong: B=1 gives 1.687 EV for codes 0->1 then 0.567 EV/code for 1->7, which IS monotone non-increasing, so B=1 passes the same test B=2 passes. The criterion narrows the index to {1, 2}, not {2}. (b) Its premise is refuted by the ROM: at 0xE1980B50/B70/B90/BB0 four further 8-entry per-ISO register blocks each step discretely between index 1 and index 2 (0x38120000->0x3c120000, 0x72000001->0x72000000, 0x8000000c->0x80000008, 0x93210ba0->0x98210ba0), and a fifth at 0xE1980BD0 steps between index 5 and 6. A discrete conversion-gain/bias switch at the ISO 200/400 boundary makes gain-per-code non-monotone by design, so B=3 (the module default) cannot be excluded on monotonicity grounds either. The index is unconstrained over {1..6} and only the card's ML/SETTINGS/dual_iso.cfg or an index sweep will settle it.

3. ADDITION worth folding in, since it upgrades two claims from inference to proof. A raw code-lattice test settles "analog vs digital" without any noise modelling: over codes [700,8000) of _MG_2218's active area the high-gain rows leave 4 of 7300 codes empty (0.05%) and the low-gain rows leave 0, where a post-ADC multiply by 3.22 would empty ~68.9%. The same test on _MG_2214 leaves 0 of 6800 codes empty over [2200,9000), so there is no post-ADC digital gain >1 at ISO 12800 either — which independently confirms the withdrawal in claim 7. It does not exclude digital attenuation (<1x), so the "sigma_post ISO-invariant" caveat stands unchanged.

Also minor: "next words 0x38120000, 0x3c120000" is 0x38120000 x2 then 0x3c120000 x6; and "index 7 is unreachable" holds only in absolute mode — max_index is 7 (FRAME_CMOS_ISO_COUNT is 0 on the 6D2), so relative mode reaches index 7 from a Canon ISO of 200 or above.

Measured dynamic range, which the deliverable asserts but never quantifies: merged 12.42 EV vs plain ISO-100 development 11.08 EV at the same white point, +1.34 EV (+1.44 EV by the optical-black route). cr2hdr's printed "12.74 EV (cooked)" is optimistic by about 0.3 EV.
