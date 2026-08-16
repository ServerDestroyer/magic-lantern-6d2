# Spike 007 — Dual ISO on the 6D2: Session 5 stills results

**Verdict: DUAL-ISO ENGAGED.** `_MG_2216`, `_MG_2217` and `_MG_2218` carry a real,
per-line-pair **analog** gain split of **+1.71 EV (3.26x)**. `_MG_2214` and `_MG_2215`
are normal single-ISO frames and serve as the control.

These are, as far as this project can tell, the first dual-ISO exposures made on a
Canon EOS 6D Mark II. Two of the three (`2216`, `2217`) are too underexposed to be
useful; `_MG_2218` is a genuine, mergeable dual-ISO frame and has been merged to a
valid DNG.

**The file-size hypothesis in the task brief is refuted — it points the wrong way.**
The two *large* (36 MB) files are the normal ones; the dual-ISO files are the *small*
(26–28 MB) ones. See [Why the size split misleads](#why-the-size-split-misleads).

---

## 1. Per-file measurements

Gain ratio = signal in raw rows `%4 ∈ {0,1}` divided by signal in rows `%4 ∈ {2,3}`,
measured by least-squares regression over every usable pixel (method in §4).

| File | Size | EXIF ISO | Shutter | Black lvl | Gain ratio | EV | Masked-region noise σ (hi / lo) | Verdict |
|---|---|---|---|---|---|---|---|---|
| `_MG_2214.CR2` | 36 003 564 | 12800 | 1/15 | 2048 | 0.9961 | −0.006 | 52.914 / 52.912 (**1.0000**) | normal (control) |
| `_MG_2215.CR2` | 36 270 456 | 12800 | 1/20 | 2048 | 0.9948 | −0.007 | — | normal (control) |
| `_MG_2216.CR2` | 26 367 278 | 100 | 1/100 | 512 | **3.2600** | **+1.705** | 8.986 / 7.659 (1.1732) | **dual-ISO** |
| `_MG_2217.CR2` | 26 411 206 | 100 | 1/100 | 512 | **3.2609** | **+1.705** | 9.010 / 7.661 (1.1761) | **dual-ISO** |
| `_MG_2218.CR2` | 28 019 905 | 100 | 1/100 | 512 | **3.2698** | **+1.709** | 8.990 / 7.638 (1.1770) | **dual-ISO** |

All five: Canon EOS 6D Mark II, 6384x4224 raw / 6264x4180 active, 120 px left +
44 px top masked border, f/2.8, 24 mm, WB Auto, white level 14558.

Per-file regression detail (four measurements per file — two Bayer parities, each
measured in both directions; a genuine gain split must be **reciprocal**):

```
_MG_2214.CR2   class 0 vs 2: n=5618924  slope=0.9962 (-0.005 EV)
               class 1 vs 3: n=4382400  slope=0.9959 (-0.006 EV)
               class 2 vs 0: n=5618995  slope=0.9962 (-0.005 EV)      <- NOT reciprocal:
               class 3 vs 1: n=4411511  slope=0.9959 (-0.006 EV)         all four ≈ 1.0

_MG_2218.CR2   class 0 vs 2: n=1040291  slope=3.2572 (+1.704 EV)
               class 1 vs 3: n= 710198  slope=3.2823 (+1.715 EV)
               class 2 vs 0: n=3568226  slope=0.3021 (-1.727 EV)      <- reciprocal pair,
               class 3 vs 1: n=2264596  slope=0.3029 (-1.723 EV)         as dual-ISO requires
```

The phase is `BBdd` starting at the first active row: raw rows 44+0 and 44+1 are the
**bright** (amplified) lines, 44+2 and 44+3 the dark ones. `cr2hdr` independently
reports the same phase string.

---

## 2. Evidence that this is really dual-ISO

Four independent tests. The first is the important one because it does not depend on
scene content at all.

### 2.1 Masked-region (optical black) read noise — scene-independent

The 120-px masked border at the left of the sensor receives no light, so any
structure there cannot come from the subject. Analog gain still amplifies the
pre-amplifier read noise, so a per-line-pair gain change shows up as a per-line-pair
**noise sigma** change even at zero signal.

```
_MG_2218  rows%4:  0: σ=8.843   1: σ=8.927   2: σ=7.504   3: σ=7.595
_MG_2217  rows%4:  0: σ=8.848   1: σ=8.946   2: σ=7.556   3: σ=7.596
_MG_2216  rows%4:  0: σ=8.862   1: σ=8.908   2: σ=7.541   3: σ=7.611
_MG_2214  rows%4:  0: σ=51.880  1: σ=52.979  2: σ=52.044  3: σ=52.797
```

Rows `{0,1}` group together and rows `{2,3}` group together in all three dual-ISO
files — a 2-row period, which is exactly the ML dual_iso line-pair structure. The
control shows no such grouping (0≈2 and 1≈3; the small 0/1 vs 2/3 difference there is
the Bayer colour split, present in every file).

### 2.2 The gain is analog, not a digital multiply

A post-ADC digital multiply by `g` would scale signal *and* noise by the same `g`,
and would leave a comb in the histogram (only multiples of `g` reachable). Neither
happens:

- signal scales by **3.27x** but masked-region noise by only **1.177x**
- mid-tone histogram occupancy, `_MG_2218`, levels 1500–6000:
  bright lines **99.98 %** occupied, dark lines **99.98 %** occupied — gapless

So the amplification happens *ahead of* the dominant downstream noise source. That is
a genuine CMOS analog gain change, i.e. what `dual_iso.c` is designed to do.

### 2.3 Differential clipping

`_MG_2218`, fraction of active-area pixels at white level:

```
bright lines (rows%4 ∈ {0,1}):  3.2144 %
dark   lines (rows%4 ∈ {2,3}):  1.3132 %
```

The amplified lines saturate first, as they must. The control `_MG_2214` clips
identically on both groups (3.8848 % vs 3.8844 %) — a 4-decimal-place match.

### 2.4 cr2hdr agrees, and rejects the control

ML's own post-processor, built from this tree and run on the files (§5):

```
_MG_2218.CR2   ISO pattern    : BBdd RGGB
               Noise levels   : 8.94 9.03 7.60 7.69 (14-bit)
               ISO difference : 1.72 EV (329)
               Dynamic range  : 11.02 (+) 10.64 => 12.35 EV (in theory)
               Dynamic range  : 12.74 EV (cooked)
               Output file    : _MG_2218.DNG

_MG_2217.CR2   ISO pattern    : BBdd RGGB
               ISO difference : 1.71 EV (328)
               Output file    : _MG_2217.DNG

_MG_2214.CR2   ISO pattern    : dddB RGGB
               Bright/dark detection error
               ISO blending didn't work                     <- control correctly rejected
```

cr2hdr's `1.71–1.72 EV` was derived by a completely different code path from my
`1.705–1.709 EV`, and its noise levels match my masked-region sigmas to two decimals.

---

## 3. EXIF: what the camera recorded, and why it cannot show "100/800"

| File | `EXIF:ISO` | `MakerNotes:BaseISO` | `MakerNotes:AutoISO` | `CreateDate` |
|---|---|---|---|---|
| `_MG_2214` | 12800 | 12800 | 100 | 2026:08:15 21:06:34 |
| `_MG_2215` | 12800 | 12800 | 100 | 2026:08:15 21:06:46 |
| `_MG_2216` | 100 | 100 | 100 | 2026:08:15 21:08:02 |
| `_MG_2217` | 100 | 100 | 100 | 2026:08:15 21:08:30 |
| `_MG_2218` | 100 | 100 | 100 | 2026:08:15 21:09:36 |

**The EXIF pattern is consistent with a 100/800 dual-ISO setting, but it cannot
confirm it, and no EXIF field ever will.** ML's dual_iso does not change the ISO
Canon knows about; it patches the CMOS gain table in RAM
(`ml/modules/dual_iso/dual_iso.c:332` `patch_cmos_iso_values_6d2`, applied via
`apply_patches`). Canon's metadata writer therefore records only the ISO set in the
menu — 100. The alternate ISO is invisible to EXIF by construction. For MLV there
*is* a dedicated channel (a `DISO` block carrying `dualMode` and `isoValue`,
`dual_iso.c:389` `dual_iso_mlv_rec_cbr`), but stills have no equivalent.

So: the three dual-ISO frames were shot at camera ISO 100, and `_MG_2214`/`_MG_2215`
at ISO 12800 ~90 seconds earlier. Ordering by `CreateDate` (not mtime — the body
clock runs behind) confirms the two controls were shot first.

### The measured 1.71 EV is not the nominal 3 EV of a 100/800 pair

This needs stating plainly: **if the menu was set to 100/800, the sensor did not
deliver 3 EV of separation. It delivered 1.71.** Both `100/800` (3 EV) and `100/400`
(2 EV) are ruled out as *achieved* separations; the measurement is repeatable to
±0.005 EV across three files.

The likely reason — supported by two independent numbers, but not proven:

The 6D2 appears to split its ISO scaling between analog gain and a post-ADC digital
multiply, and ML patches only the analog half. Fitting a
`σ² = (g·σ_pre)² + σ_post²` read-noise model to the masked regions gives
`σ_pre = 1.52 ADU`, `σ_post = 7.49 ADU`, and implies the EXIF-ISO-12800 frame carries
only **5.10 EV of analog gain** against its nominal 7.00 EV ISO step — leaving
**1.90 EV** to be made up elsewhere. Independently, the black level rises from 512 at
ISO 100 to 2048 at ISO 12800, a factor of exactly 4.00x = **2.00 EV**, which is what a
post-ADC digital multiply does to the offset. 1.90 EV inferred from noise vs 2.00 EV
measured from the black level is close agreement from two unrelated observables.

At an average 0.73 EV of analog gain per nominal ISO stop, a nominal 3-stop request
(100→800) would land near 2.19 EV and a 2-stop request near 1.46 EV. The measured
1.71 EV sits between them, so **this reasoning cannot identify which menu index was
actually selected** — the analog gain per step is certainly not uniform. Treat the
analog/digital split as a well-supported hypothesis, not an established fact; the
`σ_pre`/`σ_post` fit also absorbs fixed-pattern column noise, which inflates it.

---

## 4. Method

`exiftool` 13.59 and `dcraw` 9.28 via `nix-shell`; pixel decode through
`rawpy` 0.26.1 (LibRaw) + `numpy` 2.4.4, which reads the 6D2 CR2 natively.

Scripts (scratchpad, session-local):
`/tmp/claude-1000/-home-chris-Vibe-Coding-6D-Mark-II-Magic-Lantern-6D2/d1809f97-1ab5-4672-8a2b-1ab8dcfa3d5e/scratchpad/`
→ `dualiso_probe.py` (first pass), `dualiso_gain.py` (gain regression),
`dualiso_confirm.py` (analog-vs-digital + clipping).

Three corrections mattered, and the first pass was wrong without them:

1. **Per-row-class black level.** A gain change shifts the offset too. Subtracting one
   global black gave 1.48x for `_MG_2216` and 3.18x for `_MG_2218` — apparently
   inconsistent. Taking each row class's own black from the masked columns collapsed
   all three files onto 3.26x. The black offsets differ by only ~0.9 ADU, but on
   near-black frames that dominates the ratio.
2. **Gradient cancellation.** The dark-line reference is `0.5·(row r−2 + row r+2)`,
   i.e. the two same-colour neighbours straddling the bright row. This cancels any
   linear vertical scene gradient exactly. Comparing row `r` against row `r+2` alone
   would fold the gradient into the gain.
3. **Same Bayer parity only.** Rows 0 and 2 are both RG rows, 1 and 3 both GB. The
   period-4 test must compare 0↔2 and 1↔3; comparing 0↔1 measures the colour
   difference, not gain.

Pixels were excluded when either row was within 200 ADU of white level, or when the
reference was under 40 ADU above black. Between 0.7 M and 5.6 M pixel pairs survived
per measurement.

### Why the size split misleads

The brief predicted the ~36 MB files would be dual-ISO because dual-ISO defeats the
lossless predictor. The opposite is true here, because a much larger confound is
present: `_MG_2214`/`_MG_2215` were shot at **ISO 12800**, where photon and read noise
alone destroy compressibility (their masked-region σ is 52.9 ADU against 7.6 at
ISO 100 — 7x the noise). That swamps any dual-ISO effect. Within the ISO-100 group the
predicted ordering does hold weakly — `_MG_2218` (28.0 MB, real content, 2.3 % clipped)
is larger than the near-black `_MG_2216`/`_MG_2217` (26.4 MB) — but that is scene
content, not dual-ISO. **File size is not a usable discriminator across different
ISOs.**

---

## 5. cr2hdr: built and run successfully

`ml/modules/dual_iso/` does contain the full host-side post-processor
(`cr2hdr.c`, 131 278 B, plus `Makefile.cr2hdr`, `dcraw-bridge.c`, `exiftool-bridge.c`,
`adobedng-bridge.c`, `amaze_demosaic_RT.c`, `dither.c`, `timing.c`, `kelvin.c`).

**Build.** It must be 32-bit: `ml/src/raw.h:219` asserts
`SIZE_CHECK_STRUCT(raw_info, 0xa0)`, and `struct raw_info` only measures 160 bytes when
`void*` is 4 bytes. On NixOS neither `gcc -m32` (no `gnu/stubs-32.h`), `gcc_multi`, nor
`nix-shell -p pkgsi686Linux.gcc` works — the last one puts the *native* x86_64 gcc first
on `PATH` (`gcc -dumpmachine` → `x86_64-unknown-linux-gnu`). What works is calling the
i686 compiler by store path:

```sh
CC=$(nix-build '<nixpkgs>' -A pkgsi686Linux.stdenv.cc --no-out-link)/bin/gcc
# $CC -dumpmachine -> i686-unknown-linux-gnu
cd ml/modules/dual_iso
$CC -mno-ms-bitfields -O2 -w -I../../src -Ibuild -D_FILE_OFFSET_BITS=64 \
    -fno-strict-aliasing -msse -msse2 -std=gnu99 \
    cr2hdr.c ../../src/chdk-dng.c dcraw-bridge.c exiftool-bridge.c \
    adobedng-bridge.c amaze_demosaic_RT.c dither.c timing.c kelvin.c \
    -o cr2hdr -lm
```

Note `-m32` is *dropped* (the compiler is already i686) and `-Ibuild` supplies the
existing `module_strings.h`. At runtime cr2hdr shells out to `dcraw` and `exiftool`
(`exiftool-bridge.c:14,26` use `system()`/`popen()`), so both must be on `PATH`;
`dcraw` needs `NIXPKGS_ALLOW_INSECURE=1` in current nixpkgs.

**Result.** Merged DNGs produced for `_MG_2218` (54 237 494 B) and `_MG_2217`
(54 237 726 B). Both validate:

| DNG | Decodes | Dimensions | Residual line-pair modulation |
|---|---|---|---|
| `_MG_2218.DNG` | yes, `postprocess()` OK | 6264x4180 visible, white 65134 | 1.0008 / 1.0004 (+0.001 EV) |
| `_MG_2217.DNG` | yes, `postprocess()` OK | 6264x4180 visible, white 40001 | 1.0001 / 1.0006 (+0.001 EV) |

The +1.71 EV modulation is gone from the merged output — down to +0.001 EV over
~6.5 M pixel pairs. That is the strongest single validation available: the merge
inverted exactly the structure I measured going in.

`_MG_2218` is the one worth looking at (`postprocess` mean 10.32/255 — dark but real).
`_MG_2217` merges to a near-black image (mean 0.61/255).

**Two caveats on the merged output:**

1. `cr2hdr` reports `Camera: Canon EOS 6D Mark II (unknown, assuming 5D Mark III)` —
   there is no 6D2 entry in its camera table, so it falls back to 5D3 constants
   (colour matrix, white level). Detection and blending are unaffected, but the DNG's
   **colour and white-level metadata are wrong**. Adding a 6D2 entry to `cr2hdr.c` is a
   small, self-contained follow-up.
2. `_MG_2216` is rejected by cr2hdr with `Doesn't look like interlaced ISO`, even
   though it *is* dual-ISO — my regression finds 3.2600x over 151 362 usable pixel
   pairs, and its masked-region noise split (8.986 / 7.659) is as clear as the others'.
   The frame is simply too dark for cr2hdr's content-based detector (mean signal
   ~3 ADU above black, zero saturated pixels). This is a cr2hdr detection-threshold
   limitation, not a capture failure.

---

## 6. What this establishes, and what it does not

**Established:**

- Dual-ISO engages on the 6D2 in stills. The CMOS gain-table patch in
  `patch_cmos_iso_values_6d2` reaches the sensor and produces a real analog gain split
  on alternating line pairs.
- The split is `BBdd`-phased, +1.705 to +1.709 EV, repeatable to ±0.005 EV across
  three frames, and confirmed independently by cr2hdr at 1.71–1.72 EV.
- The pipeline is end-to-end complete: capture → detect → merge → valid DNG.
- The 6D2 branch of `dual_iso_init` (`dual_iso.c:1298`) sets only `PHOTO_CMOS_ISO_*`
  and leaves `FRAME_CMOS_ISO_START` at 0 — verified by reading the whole block.

**Not established:**

- **Which alternate-ISO menu index was set.** The default is
  `CONFIG_INT("dual_iso.iso", dual_iso_alternate_iso, 3)` (`dual_iso.c:76`), which in
  absolute mode is index 3 = ISO 800 = 3 EV nominal. The achieved 1.71 EV does not
  match, and the analog-gain argument in §3 cannot separate index 2 from index 3.
  **Ask the owner what the Dual ISO menu line displayed** — it renders as `iso2/iso1`
  (`dual_iso.c:927`), which pins the setting directly.
- **Whether 1.71 EV is the ceiling on this body.** The analog/digital split hypothesis
  predicts it is, and predicts higher menu settings will not help much. Untested.
- Whether dual-ISO works in **movie/raw** mode on the 6D2. `FRAME_CMOS_ISO_START` is
  never assigned in the 6D2 branch of `dual_iso_init` (`dual_iso.c:1298`), and
  `dual_iso.c:876` warns "Dual ISO does not work in movie mode on your camera" when it
  is zero. Stills-only, by construction, on this port today.

## 7. Suggested next steps

1. Confirm the menu setting with the owner (one question, resolves §3 outright).
2. Re-shoot a **properly exposed** dual-ISO frame. All three attempts were 1–3 EV
   underexposed; only `_MG_2218` is usable and two were wasted. At ISO 100, 1/100,
   f/2.8 the scene was far too dark.
3. Sweep the alternate-ISO setting (index 1 through 5) over one static scene and
   measure achieved EV for each. That directly maps the 6D2's CMOS gain table and
   settles whether 1.71 EV is a ceiling — roughly 20 minutes of shooting and a rerun
   of `dualiso_gain.py`.
4. Add a 6D2 entry to `cr2hdr.c`'s camera table so merged DNGs get correct colour and
   white-level metadata.
