---
spike: 008
name: lossless-compression-scoping
type: scoping
validates: "Given mlv_lite records uncompressed 14-bit raw on the 6D2 in ~1s bursts, when the LJ92 lossless path used on DIGIC 5 is examined against the 6D2's DIGIC 7 ROM, then the per-body work required to reach sustained recording is enumerated with concrete addresses and a bounded effort estimate"
verdict: FEASIBLE-BUT-EXPENSIVE
related: [002, 006, 007]
tags: [rom, reversing, raw-video, lossless, jpcore, digic7]
---

# Spike 008 — Lossless (LJ92) raw compression on the 6D2: scoping

**Status:** research complete, read-only. No source modified, nothing built, nothing committed.
**Date:** 2026-08-15
**Tree:** `ml/` @ `dev` (3f24042a4), `qemu-eos/` @ working copy
**ROM:** `roms/6D2/ROM0.BIN` (32 MiB, base `0xE0000000`), `ROM1.BIN` (16 MiB)

---

## TL;DR

Three findings reframe the task.

1. **The `mlv_lite` side is already written.** `OUTPUT_14BIT_LOSSLESS`, `compress_task`,
   per-frame slot shrinking, the `MLV_VIDEO_CLASS_FLAG_LJ92` header flag and the
   compression-ratio estimator all exist and are exercised on DIGIC 5 today. The 6D2 is
   locked out by **one `if` at `mlv_lite.c:4633`**. Nothing needs to be designed there.

2. **The 6D2 has the hardware and the firmware for it.** ROM0 contains a complete
   `LosslessPath` subsystem plus the JPCORE encoder engine
   (`Src/Engine/EHD/Lossless/LosslessEncode.c`, `Src/Engine/ELD/JpCore/JpCore.c`,
   `Huffman.c`, `QTable.c`). Section 3 lists 30+ addresses.

3. **But the API was renamed and restructured between DIGIC 5 and DIGIC 7.** The string
   `TwoInTwoOut` appears **zero times** in either 6D2 ROM. Every one of the seven function
   pointers `lossless.c` needs is a DIGIC 4/5-era `ProcessTwoInTwoOut{Lossless,Jpeg}Path`
   entry point that **does not exist on this body**. This is not a "fill in seven addresses"
   port. It is a fresh reverse-engineering of a differently-shaped API with no sibling
   implementation to copy from.

**Verdict:** feasible, unblocked by any missing hardware, and worth roughly **8–14 sessions**.
The payoff is real: 1080p24/25 goes from a ~1-second burst to genuinely sustained recording.

---

## 1. How lossless raw works on supported bodies

### The files

| File | Role |
|---|---|
| [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/modules/silent/lossless.c](ml/modules/silent/lossless.c) | The whole encoder driver. 592 lines. **This is the `src/lossless.c` the brief asked about — it lives under `modules/silent/`, not `src/`.** |
| [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/modules/silent/lossless.h](ml/modules/silent/lossless.h) | 4-function public API (`lossless_init`, `lossless_compress_raw`, `lossless_compress_raw_rectangle`, `lossless_decompress_raw`) |
| [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/modules/raw_video/mlv_lite/mlv_lite.c](ml/modules/raw_video/mlv_lite/mlv_lite.c) | Consumer. `#include "../../silent/lossless.h"` at `:77` |
| [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/modules/silent/silent.c](ml/modules/silent/silent.c) | Other consumer — lossless DNG stills, `:514` `save_lossless_dng()` |

`mlv_lite` compiles the encoder into its own module via an explicit rule in
[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/modules/raw_video/mlv_lite/Makefile](ml/modules/raw_video/mlv_lite/Makefile)
(`$(BUILD_DIR)/lossless.o: ../../silent/lossless.c`), which is why
`modules/raw_video/mlv_lite/build/lossless.o` exists with no `lossless.c` beside it.

### The mechanism

ML does not implement LJ92 in software. It **borrows Canon's own still-image compression
pipeline** — the "two in, two out lossless path" that normally produces a CR2 — and points
its input EDMAC at an arbitrary memory rectangle instead of the sensor.

The seven ROM entry points, declared at `lossless.c:69-75`:

| Pointer | Canon name (D5) | Purpose |
|---|---|---|
| `TTL_SetArgs` | `PictureSize(Mem1ToRaw)` | fills the `TwoInTwoOutLosslessPath_args` struct |
| `TTL_Prepare` | `[TTL] GetPathResources` | locks engine resources, configures encoder for RAW/SRAW/MRAW |
| `TTL_RegisterCBR` | `RegisterTwoInTwoOutLosslessPathCompleteCBR` | completion callback |
| `TTL_SetFlags` | — | picture type |
| `TTL_Start` | — | starts the EDMAC transfers |
| `TTL_Stop` | after `sssStopMem1ToRawPath` | |
| `TTL_Finish` | — | unlocks resources, **returns the compressed output size** |

### The per-body pieces

Four, and only the first is a simple table lookup:

1. **Seven ROM addresses**, `lossless.c:82-186`. Present for 5D3 1.1.3/1.2.3, 700D, 650D,
   EOSM, 100D, 6D, 70D. Absent for everything else — `lossless_init()` returns
   `TTL_Start && lossless_sem && TTL_ResLock` at `:261`, so an unlisted body silently
   reports "not available" and the menu entry hides itself.

2. **A ResLock resource-ID list**, `lossless.c:189-255`. Three variants already
   (700D/650D/EOSM/100D, 5D3/6D, 70D). These are engine arbitration IDs — the EDMAC
   read/write channels plus read connection 1, write connection 45, and a set of
   `0x5xxxx`/`0x26000x` resources.

3. **Slice-geometry registers**, `lossless.c:325-374`. ML deliberately misconfigures the
   encoder: Canon uses `slice width = image width / 2, slice height = image height`, ML
   uses `slice width = image width, slice height = image height / 2`, which makes the
   two-slice output concatenate into a valid single-image LJ92 stream you can put a DNG
   header on. Per-family register writes: `0xC0F375B4` on most D5, `0xC0F37300`/`0xC0F373E8`
   on 70D, plus the `0xC0F376xx` block on 6D/650D and `0xC0F13068` for total image size.

4. **Output-size handling in `mlv_lite`** — already generic:
   - `max_frame_size` pre-sized at `mlv_lite.c:757-771` (85% of uncompressed above 10 MB,
     4096-byte aligned — the encoder has "unusual alignment requirements")
   - `compress_task` at `:2759`, calling `lossless_compress_raw_rectangle` at `:2829`
   - slots shrunk to the real compressed size on the fly after each frame
   - `get_estimated_compression_ratio()` at `:835` — defaults 60% for 14-bit lossless,
     52% for 12-bit, replaced by `measured_compression_ratio` once a frame has run
   - `MLV_VIDEO_CLASS_FLAG_LJ92` set in the header at `:3145`

### The 6D2's actual lockout — one `if`

`mlv_lite.c:4627-4640`:

```c
int version = get_digic_version();
...
if (version != 5)
{ // so far, only Digic 5 has working lossless compression, hide on other cams
    if (raw_video_menu->children[2].max > 2)
    {
        raw_video_menu->children[2].max = 2; // hide lossless options, which are 3, 4, 5
        output_format = 0; // plain 14-bit, no lossless support on D4, D678 (yet)
    }
}
```

That comment — "**no lossless support on D4, D678 (yet)**" — is the upstream statement of
exactly this gap. Note `lossless_init()` is still called unconditionally at `:4668` and
`compress_task` is still created at `:4674` on every body, including the 6D2. The
infrastructure is live; only the encoder backend and the menu gate are missing.

---

## 2. State of the art on DIGIC 6/7/8

### Nobody has driven the lossless engine on DIGIC 6, 7, or 8

Searched: the ML fork's issue and PR tracker, the ML forum's DIGIC 7 development thread,
and the `dev` branch source. Every body with a `lossless.c` entry is DIGIC 4 or 5. There is
no `lossless.c` block, no ResLock list, and no geometry register set for any D6/D7/D8 body —
including the ones with far more mature ports than the 6D2 (5D4, M50, R, R5, R6, 850D).

Corroborating evidence in-tree: `mlv_lite.c:4638`'s own comment, and the fact that the D678
raw-video work in this project (spike 006) is entirely about buffer physics for
*uncompressed* frames.

### The active precedent: PR #292, DIGIC 4

[reticulatedpines/magiclantern_simplified#292](https://github.com/reticulatedpines/magiclantern_simplified/pull/292) —
*"feat: enable LJ92 lossless compression on Digic 4 bodies"*, by **wavesoft**
(Ioannis Charalampidis), opened 2026-08-06, still open, targeting `dev`.
**+1388 / −86 across 7 files.** This is the single most useful reference for scoping, because
it is someone doing precisely this job on an adjacent architecture, right now.

What it took, from the PR body and diff:

- `modules/silent/lossless.c` **+522 / −31** — wire `ProcessTwoInTwoOutJpegPath`: split Start,
  geometry patch, stall-detector completion, LiveView save/restore, OBWB gain for reduced depths
- `modules/raw_video/mlv_lite/mlv_lite.c` **+425 / −52** — encodable width (`4 mod 8`),
  overread rows, RAWI level mapping, **6-frame encode warm-up**, clean compression-fault
  stop/drain
- `src/raw.c` +15, `src/state-object.c` +18 — DIGIC 4 digital-gain fix, and an
  "**Evf EngineError trim so borrowing JPCORE cannot ASSERT the camera**"
- a whole optional low-FPS soft-preview subsystem, because **JPCORE freezes LiveView while
  it encodes**

Two of those details are the important warnings for us and are covered in section 5:
borrowing JPCORE during LiveView can hard-ASSERT the camera, and the first frames of every
clip come out shredded until LiveView relocks (PR #292 notes VIDF 1–4 arrived in ~16-row
bands with vsync wobbling 37.8–45.1 ms, clean from VIDF 5).

Note that even *with* a same-family sibling implementation to copy (600D reuses the
`ProcessTwoInTwoOutJpegPath` API that 650D/700D/100D/EOSM already had), this was a
1388-line change. The 6D2 has no sibling.

### What changed in the JPEG engine architecture

From the ROM evidence in section 3, the DIGIC 5 → DIGIC 7 differences are structural, not cosmetic:

| | DIGIC 4/5 | DIGIC 7 (6D2) |
|---|---|---|
| Path name | `ProcessTwoInTwoOut{Lossless,Jpeg}Path` | `LosslessPath` / `MEM1TOLOSSLESS` |
| String `TwoInTwoOut` in ROM | present | **absent (0 occurrences, both ROMs)** |
| Args struct | `TwoInTwoOutLosslessPath_args`, RD1/RD2/WR1/WR2 channels | `LosslessPathRsc` + `LosslessPathParam`, with named `RdBayCh` / `WrRawCh` / **`WrThumbCh`** |
| Huffman table | implicit in the path setup | **explicit `pHuffmanTable` parameter** |
| Memory | single output memSuite | `PackMemNum`, `pMemList`, `SharememTbl`, `SharememNum` — a shared-memory table |
| Resource locking | `CreateResLockEntry` + `LockEngineResources` | `sssAsyncLockEngineResourcesLossless` — **asynchronous**, with a `CompLosslessPathResLockCB` callback |
| Allocation | caller-provided | firmware-managed with retry: `JudgeAllocLosslessMemory`, `RetryAllocLosslessMemory`, `Lossless Retry(%d)` |
| Geometry limits | ML-derived from register logs | **explicit `JPCORE_RESTRICTION_HORIZONTAL_MULTIPLE` / `_VERTICAL_MULTIPLE` asserts in firmware** |

The async resource lock and the firmware-managed retry allocator are the two that will most
change the shape of `lossless.c` — the current code is written as a synchronous
prepare/start/wait-semaphore/finish sequence (`lossless.c:267-460`).

**Sources:**
- [reticulatedpines/magiclantern_simplified#292 — enable LJ92 lossless compression on Digic 4 bodies](https://github.com/reticulatedpines/magiclantern_simplified/pull/292)
- [reticulatedpines/magiclantern_simplified#291 — SD overclocking for DIGIC 4 SD bodies](https://github.com/reticulatedpines/magiclantern_simplified/pull/291)
- [ML forum — DIGIC 7 development (200D/SL2, 800D/T7i, 77D, 6D2)](https://www.magiclantern.fm/forum/index.php?topic=19737.400)
- [ML forum — \[JPCORE\] Digic Quality](https://www.magiclantern.fm/forum/index.php?topic=5003.0)
- [ML forum — lossless compressed raw?](https://www.magiclantern.fm/forum/index.php?topic=7967.0)
- [ML wiki glossary — JPCORE](https://wiki.magiclantern.fm/glossary) ("dedicated hardware used by Canon to implement various types of image compression… we have little to no idea how to reprogram the code running on JPCORE")

---

## 3. 6D2 ROM evidence

All addresses from `strings -a -t x roms/6D2/ROM0.BIN`, offset + `0xE0000000`.
The encoder subsystem is unambiguously present.

### Engine source-file paths (Canon's own `__FILE__` strings)

| Address | String |
|---|---|
| `0xE0159520` | `../../Src/Engine/EHD/Lossless/LosslessEncode.c` |
| `0xE01D712C`, `0xE01D7A90` | `../../Src/Engine/EHD/Lossless/LosslessEncodeBase.c` |
| `0xE0158F64`, `0xE01592C8` | `../../Src/Engine/EHD/Lossless/LosslessDecode.c` |
| `0xE0246E34` | `../../Src/Engine/ELD/JpCore/JpCore.c` |
| `0xE00D90A0` | `../../Src/Engine/ELD/JpCore/JpCoreLoader.c` |
| `0xE06AC758` | `../../Src/Engine/ELD/JpCore/Huffman.c` |
| `0xE06AC7AC` | `../../Src/Engine/ELD/JpCore/QTable.c` (run at `6ac7a9` carries a 3-byte junk prefix) |

`JpCoreLoader.c` is notable: JPCORE is a loadable-microcode DSP, and this body has the loader.

### The `LosslessPath` API surface — the DIGIC 7 replacement for `TwoInTwoOut*`

| Address | String | Maps to |
|---|---|---|
| `0xE0329438` | `ReqLosslessStart(%d)` | job submission |
| `0xE0329848` | `CompAllocMemSuiteForLossless(%d)` | output buffer alloc complete |
| `0xE0329870` | `sssRequestAllocLosslessMemory(%d)Pict=%#x dcsPict=%#x` | |
| `0xE03298B0` | `JudgeAllocLosslessMemory Wait(%d)` | |
| `0xE03298D4` | `JudgeAllocLosslessMemory Ok(%d)` | |
| `0xE03298F4` | `CompLosslessPathResLockCB(%d)` | **async ResLock callback** |
| `0xE0329914` | `sssAsyncLockEngineResourcesLossless %x(%x)` | ≈ `TTL_Prepare` |
| `0xE0329944` | `LockEnginResLosslessPath(%d)` | |
| `0xE0329968` | `Wait LosslessPath(%d)` | |
| `0xE0329980` | `CompLosslessPathCB(%d)(%#x)(%d)` | ≈ `TTL_RegisterCBR` target |
| `0xE0329EC8` | `StartLosslessPath(%d)` | **≈ `TTL_Start`** |
| `0xE0329F28` | `CompLosslessPath(%d)` | ≈ `TTL_Finish` |
| `0xE0329EFC` | `sssUnLockEngineResourcesLossless %x(%x)` | |
| `0xE0328284` | `NotifyLosslessPathComp(%d)` | |
| `0xE0328254` | `LosslessPath Skip(%d)` | |
| `0xE0329F40` | `Lossless Retry(%d):%#x %#x` | |
| `0xE032A38C` | `CompReAllocMemSuiteForLossless(%d)` | |
| `0xE032A3B4` | `RetryAllocLosslessMemory(%d)` | |
| `0xE032A3F4` | `EV_LOCK_ENGRSC_LOSSLESSPATH(%d)(%d)` | |

### The args struct, field by field (the DIGIC 7 `TTL_Args` equivalent)

These are `DebugMsg` traces of struct members — a free field list for the struct we must rebuild.

| Address | String |
|---|---|
| `0xE03299C4` | `LosslessPathRsc pRscAry=%#x` |
| `0xE03299E0` | `LosslessPathRsc RscNum=%#x` |
| `0xE03299FC` | `LosslessPathRsc LosslessEncMode=%#x` |
| `0xE0329A20` | `LosslessPathRsc RdBayCh=%#x` |
| `0xE0329D80` | `LosslessPathRsc WrRawCh=%#x` |
| `0xE0329D9C` | `LosslessPathRsc WrThumbCh=%#x` |
| `0xE0329E6C` | `LosslessPathRsc SharememTbl=%#x` |
| `0xE0329E8C` | `LosslessPathRsc SharememNum=%#x` |
| `0xE0329DBC` | `LosslessPathParam PackMemNum=%d` |
| `0xE0329DDC` | `LosslessPathParam pHuffmanTable=%#x` |
| `0xE0329E00` | `LosslessPathParam pMemList=%#x` |
| `0xE0329E20` | `LosslessPathParam RdBayAddress=%#x` |
| `0xE0329E44` | `LosslessPathParam WrThumbAddress=%#x` |
| `0xE0329EAC` | `LosslessPath Sharemem` |

### Geometry constraints — firmware-enforced

| Address | String |
|---|---|
| `0xE0213E24` | `!( InputWidth % JPCORE_RESTRICTION_HORIZONTAL_MULTIPLE )` |
| `0xE0213E60` | `!( InputHeight % JPCORE_RESTRICTION_VERTICAL_MULTIPLE )` |

These are `ASSERT` condition strings. The multiples themselves are immediates in the
comparison — recoverable by disassembling the containing function. This is the DIGIC 7
analogue of PR #292's "encodable width `4 mod 8`" finding, and it must be honoured before the
first encode is attempted, or the camera asserts.

### Supporting / adjacent

| Address | String | Note |
|---|---|---|
| `0xE0F8F1A4` | `MEM1TOLOSSLESS` | **Engine path-name table entry, index 24** |
| `0xE0F8F244` | `MEM1TOSSRAW` | same table, index 11 |
| `0xE09420B0` | (pointer to `MEM1TOLOSSLESS`) | the table itself: idx 11 `MEM1TOSSRAW` … idx 22 `YUVTODCF`, idx 23 `YUVTODCFRAW`, **idx 24 `MEM1TOLOSSLESS`**, idx 25 `FACEPATH`, idx 26 `LENSCORRECT`, idx 27 `COLORREG` |
| `0xE051CC74` | `Degeen2Lossless` | de-Bayer/gain stage feeding the encoder |
| `0xE034247C` | `Degeen2GainRegForLossless` | — the digital-gain hook PR #292 needed on D4 |
| `0xE00C89E8` | `LuckyEnableFlag` | same `LuckyEnable` concept as `TTL_Args` field, `lossless.c:23` |
| `0xE013F3DC`, `0xE07EA740` | `fLuckyEnable(%d)` | |
| `0xE07F9A9C` | `pLuckyEnable = %d` | |
| `0xE02472F0` | `JpCoreIntrHandler` | encoder completion IRQ |
| `0xE038757C` | `devcLosslessEncodeRetry %d` | |
| `0xE0340E1C` … `0xE0341414` | `[MEM3NAVI]…Lossless…` | MEM3 allocator interaction |
| `0xE00D619C` … `0xE00D61D8` | `CORE_SetJpegPath`, `CORE_StartJpegPath Addr[%#x]`, `CORE_StopJpegPath` | **eventproc-shaped names** |
| `0xE00D6DDC` | `CORE_StartMem1ToRaw` | eventproc-shaped |
| `0xE0355DF0/E4C/E5C` | `SetJpegPath` / `StartJpegPath` / `StopJpegPath` | |
| `0xE051B7CC/7DC/7EC` | `SetMem1ToRaw` / `StartMem1ToRaw` / `StopMem1ToRaw` | |

### Does `stubs.S` or the veneer table hint at the entry points?

**No — and this is an effort input, not a footnote.**

[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/platform/6D2.111/stubs.S](ml/platform/6D2.111/stubs.S)
is 284 lines / 140 stubs and contains **nothing** encoder-related. It has `DryosDebugMsg`
(`:68`), EDMAC, MMU, FIO, and the generic `call` eventproc dispatcher at `:110`
(`THUMB_FN(0xe04e7432, call)`). No `Jpeg`, no `Lossless`, no `Encode`, no `TTJ`/`TTL`.
For comparison, `200D.101/stubs.S` is 512 lines and also has none. Across *all* platforms the
only encoder stubs that exist are `ENCODE_StartEncodeJpeg` and `GetJpegBufForLV`, and every
one of them is commented out (e.g. `5D3.113/stubs.S:310`, `6D.116/stubs.S:314`).

There is also **no usable veneer/xref shortcut**. Two scanning passes were run over ROM0:

- a 32-bit literal-pool scan (all 4-byte-aligned words in `0xE0000000..0xE2000000`)
- a Thumb-2 `MOVW`/`MOVT` immediate-pair reconstructor

Both returned **zero code references** to every `Lossless*`/`JpCore*` string above. The one
exception is `MEM1TOLOSSLESS`, referenced from the path-name table at `0xE09420B0` — proving
the scanners work, and that the misses are real. The referencing code therefore uses PC-relative
`ADR.W`, or interleaved/reordered `MOVW`/`MOVT` pairs that a linear scanner cannot pair up.

**Consequence:** naive string-xref stub-hunting — the method spike 002 used to audit the
existing stub table — will not find these entry points. This work requires a real disassembler
(Ghidra or IDA, ARMv7 Thumb-2, ROM0 loaded at `0xE0000000`). That is the single largest
methodology cost in the plan.

---

## 4. The bitrate math

### Baseline

1920 × 1080 × 14 bpp = **3,628,800 B/frame** (3.46 MiB), matching the 3,629,056 B measured
in spike 006 once the 512-aligned VIDF header is included.

| Mode | Uncompressed | 14-bit lossless @60% | @55% (clean) | @65% (noisy) | 12-bit lossless @52% |
|---|---|---|---|---|---|
| 1080p23.976 | 87.0 MB/s | **52.2** | 47.9 | 56.6 | 45.2 |
| 1080p25 | 90.7 MB/s | **54.4** | 49.9 | 59.0 | 47.2 |
| 1080p29.97 | 108.8 MB/s | **65.3** | 59.8 | 70.7 | 56.6 |
| 1080p59.94 | 217.5 MB/s | **130.5** | 119.6 | 141.4 | 113.1 |

The 60% / 52% figures are ML's own defaults from `get_estimated_compression_ratio()`
(`mlv_lite.c:852-856`), replaced at runtime by `measured_compression_ratio` after the first
encoded frame. The 55–65% spread is the realistic scene-dependent range for LJ92 on 14-bit
Bayer data.

### Against the card

**Caveat: no `bench.mo` result for this body exists in the project.** A grep across
`.planning/`, `docs/`, `FEATURE_MATRIX.md` and `PLAN_OF_ACTION.md` found only QEMU-emulated
`FileMgr` traces (12–24 MB/s), which are meaningless for real card throughput. The
~60–90 MB/s figure is an assumption. Spike 006 establishes the hard ceiling:
**≤104 MB/s UHS-I bus**
([/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/spikes/006-rawvideo-memory/README.md](.planning/spikes/006-rawvideo-memory/README.md), line 34).
Running `bench.mo` is a prerequisite for trusting any row below.

| Mode | Verdict with lossless |
|---|---|
| **1080p24** | **Sustained.** 52 MB/s clears even a pessimistic 60 MB/s card with margin. |
| **1080p25** | **Sustained.** 54 MB/s. The headline win. |
| **1080p30** | **Marginal → sustained at 12-bit.** 65 MB/s needs a ≥70 MB/s card; 12-bit lossless (57 MB/s) makes it safe on anything ≥60 MB/s. |
| **1080p50/60** | **Still a burst.** 130 MB/s exceeds the UHS-I bus ceiling outright — no card fixes this. |

### What 50/60p does gain

Burst length is `buffer / (demand − card_speed)`. With the 135 MB buffer measured in spike 006
and an 80 MB/s card:

- today, uncompressed: 135 / (217.5 − 80) = **0.98 s** — matches the observed ~1 s stop
- with lossless: 135 / (130.5 − 80) = **2.7 s**

So 60p goes from ~1 second to roughly **2.5–3 seconds**. Useful, not sustained.

**Summary: lossless compression converts the 6D2 from a burst-only raw camera into a
sustained-recording raw camera at 24/25p, and at 30p with 12-bit.** That is the deliverable
worth 8–14 sessions.

---

## 5. Effort estimate and plan

### Why this is not spike 007

Dual-ISO turned out to be a ~6-line diff plus three ROM table addresses. This is the opposite:
a new API to reverse, a new struct to rebuild, an async resource protocol the current code
does not model, and a real-time contention problem with LiveView.

### Phase 1 — static RE (3–5 sessions)

Ghidra, ROM0 at `0xE0000000`, ARMv7 Thumb-2 little-endian.

1. Locate the functions containing the anchors `LosslessPathRsc LosslessEncMode=%#x`
   (`0xE03299FC`) and `StartLosslessPath(%d)` (`0xE0329EC8`). These sit inside the setup and
   start functions respectively.
2. Recover the `LosslessPathRsc` / `LosslessPathParam` struct layouts from the `DebugMsg`
   argument order — the 14 field strings in section 3 give the names for free.
3. Recover `JPCORE_RESTRICTION_HORIZONTAL_MULTIPLE` and `_VERTICAL_MULTIPLE` from the
   compare immediates at `0xE0213E24` / `0xE0213E60`.
4. Map the async lock protocol: `sssAsyncLockEngineResourcesLossless` →
   `CompLosslessPathResLockCB` → `StartLosslessPath` → `CompLosslessPath`.
5. Identify the resource-ID array passed as `pRscAry`/`RscNum` — the D7 equivalent of
   `lossless.c:214-232`.

**Exit criterion:** seven addresses and a struct definition, written up. If the async protocol
cannot be untangled, stop here and report — that is a legitimate negative result.

### Phase 2 — minimal encode test, stills only (2–3 sessions)

**Do not start with `mlv_lite`.** Start with `silent.mo`'s lossless DNG path
(`silent.c:514 save_lossless_dng`), which calls the same `lossless_compress_raw()` but from a
still-capture context: engine idle, no LiveView contention, no real-time deadline, one frame,
and the output is a file verifiable byte-exactly on a PC.

This cleanly separates *"does the encoder work at all"* from *"can we steal it during movie
recording"* — the two risks that PR #292 shows are entirely different problems.

Add a `is_camera("6D2", "1.1.1")` block to `lossless_init()` and a D7 branch to the ResLock
list; leave `mlv_lite` untouched.

### Phase 3 — `mlv_lite` integration (3–6 sessions, high variance)

1. Flip `mlv_lite.c:4633` from `version != 5` to a capability test — ideally
   `if (!lossless_init())` rather than a DIGIC-version whitelist, which fixes D4 and D678
   with the same line.
2. Constrain `res_x`/`res_y` to the JPCORE multiples from phase 1.
3. Port PR #292's frame warm-up (skip/discard the first N encoded frames while LiveView
   relocks) and its clean compression-fault stop/drain.
4. Handle LiveView arbitration — see the unknown below.

### QEMU: useful for plumbing, useless for verification

`qemu-eos/hw/eos/engine.c:1163` `eos_handle_jpcore()` exists, mapped by
`qemu-eos/hw/eos/eos.c:651-653` as three windows:

```c
{ "JP51", 0xC0E00000, 0xC0E0FFFF, eos_handle_jpcore, 0 },  /* JPEG + old-style lossless (TTJ) */
{ "JP62", 0xC0E10000, 0xC0E1FFFF, eos_handle_jpcore, 1 },  /* H.264 */
{ "JP57", 0xC0E20000, 0xC0E2FFFF, eos_handle_jpcore, 2 },  /* new-style lossless (TTL) */
```

It is a **logging stub with no codec**. Writing bit 0 of `+0x0000` just fires interrupt `0x64`;
`+0x0024` is labelled `"output size"` and returns nothing; `+0x0030` returns a canned `0x1FF`.
There is no LJ92 implementation anywhere in the tree. The address map is also the DIGIC 4/5
layout, so the D7 register window is likely not even mapped for the 6D2 model.

**QEMU can therefore validate:** that stubs resolve, that the call sequence runs without
crashing, that ResLock ordering does not deadlock, and that `mlv_lite`'s menu/gating changes
behave. **QEMU cannot validate:** compressed output, geometry correctness, compression ratio,
or LiveView contention. All of those are body-only. Extending QEMU with a real LJ92 encoder is
possible (`mlv_rec/lj92.c` already contains one) but is its own multi-session project and is
**not** recommended as a prerequisite.

### Sessions

| Phase | Estimate |
|---|---|
| 1 — static RE | 3–5 |
| 2 — stills encode test | 2–3 |
| 3 — `mlv_lite` integration | 3–6 |
| **Total** | **8–14** |

Sanity check against PR #292: 1388 added lines *with* a same-family sibling to copy from.
We have no sibling, but we do have that PR as a structural template for phase 3.

### Biggest unknown

**Whether JPCORE is available while the 6D2 is in LiveView movie mode, and what happens to
Canon's own pipeline when ML takes it.**

PR #292 had to add an "Evf EngineError trim so borrowing JPCORE cannot ASSERT the camera",
and found that JPCORE freezes LiveView outright — enough that a whole soft-preview subsystem
was written to compensate. On the 6D2 this is sharper for three reasons:

1. `CONFIG_EVF_STATE_SYNC` is already set for this body
   ([/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/platform/6D2.111/internals.h](ml/platform/6D2.111/internals.h)),
   and raw video already routes through `raw_rec_vsync_cbr` via `vsync_func` — the encoder
   would be contending with a path ML is already hooked into.
2. DIGIC 7 has more concurrent engine consumers (DPAF, HDR movie, Dual Pixel) than DIGIC 4.
3. The 6D2's port has an unresolved dead-state/re-arm history (spike 006) — adding an async
   resource lock on top of that is a genuine risk of new hangs.

Second-order unknown: `LosslessEncMode` values. The 5D3 path takes a picture-quality argument
(`0=RAW, 1=MRAW, 2=SRAW, 14, 15`, `lossless.c:283`). The D7 field is named differently and its
valid values are unknown; a wrong one is a plausible ASSERT.

### First concrete action

**Load `roms/6D2/ROM0.BIN` into Ghidra at `0xE0000000` as ARMv7 Thumb-2 and report the
containing-function entry addresses for the two anchors `0xE03299FC`
(`LosslessPathRsc LosslessEncMode=%#x`) and `0xE0329EC8` (`StartLosslessPath(%d)`).**

Bounded, zero risk to the camera, needs no build and no body. It either yields the two
functions that everything else hangs off — or it shows the code is not statically reachable,
which kills the spike early and cheaply. Run `bench.mo` on the body in the same session to
replace the assumed 60–90 MB/s card figure with a measurement, since every sustainability
claim in section 4 depends on it.

---

## Appendix — reproduction

```bash
cd "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2"

# encoder subsystem strings, with addresses (add 0xE0000000 to the offset)
strings -a -t x roms/6D2/ROM0.BIN | grep -iE 'Lossless|JpCore|Mem1To|JpegPath'

# the negative result that reframes the port
strings -a roms/6D2/ROM0.BIN roms/6D2/ROM1.BIN | grep -c TwoInTwoOut   # => 0

# the one-line lockout
sed -n '4627,4640p' ml/modules/raw_video/mlv_lite/mlv_lite.c

# the per-body table that needs a 6D2 entry
sed -n '82,262p' ml/modules/silent/lossless.c

# QEMU's JPCORE stub
sed -n '1163,1240p' qemu-eos/hw/eos/engine.c
```

---

## Ghidra pass 1 — 2026-08-15

**Status:** phase 1 static RE substantially complete. Read-only, nothing built, nothing committed.
**Tools:** Ghidra 12.1.2 via `nix build nixpkgs#ghidra-bin` (950 MiB fetch, cached, ~35 min).
**Headline:** section 3's "no usable veneer/xref shortcut — this work requires a real disassembler"
was **wrong, and for a specific and correctable reason.** All 49 target strings resolve to exactly
one referencing site each. The API surface is now enumerated.

### 0. Why the earlier scan returned zero — the actual bug

The two passes run for section 3 (32-bit literal pool, `MOVW`/`MOVT` reconstruction) were both
looking for the wrong encoding. Canon's DryOS `DebugMsg` format strings are stored **inline in the
function body**, a few hundred bytes from the code that uses them, and are addressed with the
**16-bit Thumb `ADR` (T1)** form — `1010 0 Rd imm8`, opcode range `0xA000..0xA7FF`,
`Rd = Align(PC,4) + imm8*4`, reach 0..1020 bytes. That encoding appears in neither of the
original scans, and a literal pool is never involved because the string is close enough to
address directly.

Adding T1 `ADR` (and, secondarily, the 32-bit `ADR.W` `T3`/`T4` forms) resolved **49 of 49**
targets, 102 reference sites total:

| Encoding | Sites found | Notes |
|---|---|---|
| `ADR` T1 (16-bit) | 88 | the encoding that was missed; carries essentially the whole subsystem |
| `ADR.W` T3/T4 (32-bit) | 12 | used where the string is >1020 B away |
| literal pool word | 2 | `MEM1TOLOSSLESS`, `MEM1TOSSRAW` — the control case, unchanged |
| `MOVW`/`MOVT` pair | 0 | genuinely unused for these strings; the original scan was not wrong here |

The `MEM1TOLOSSLESS` control case still resolves to exactly the path table at `0xE09420B0`,
so the xref machinery is validated in both directions.

**Notably, Ghidra's own xref machinery also returns zero on this ROM** unless the ARM constant/
reference analyzer is run — a seeded-disassembly-only pass reports `n=0` for every anchor. The
spike's conclusion "Ghidra-class analysis required" was therefore not just unnecessary, it would
not have helped on its own. What was required was the right instruction encoding.

### 1. Resolved function entries

All addresses are Thumb (`entry|1` for a `THUMB_FN` stub). Sizes are Ghidra's, from seeded
disassembly + `CreateFunctionCmd`; they agree exactly with an independent prologue/BL-target
walk on all the small wrappers.

| Entry | Size | Evidence (string it emits) | Role — mapped to `lossless.c` |
|---|---|---|---|
| **`0xE032973C`** | 550 | all 13 `LosslessPathRsc`/`LosslessPathParam` field traces | **≈ `TTL_SetArgs`** — fills both structs |
| **`0xE0329B78`** | 54 | `StartLosslessPath(%d)` @`0xE0329EC8` | **≈ `TTL_Start`** (thin wrapper) |
| **`0xE032A27C`** | 100 | — (tail call of the above) | **the real starter** |
| **`0xE0329636`** | 42 | `sssAsyncLockEngineResourcesLossless %x(%x)` | **≈ `TTL_Prepare`**, async |
| **`0xE0329608`** | 46 | `CompLosslessPathResLockCB(%d)` | **the async ResLock callback** |
| `0xE0329660` | 138 | `LockEnginResLosslessPath(%d)`, `Wait LosslessPath(%d)` | lock driver; calls `0xE0329636` |
| `0xE03296EA` | 82 | `CompLosslessPathCB(%d)(%#x)(%d)` | ≈ `TTL_RegisterCBR` target |
| `0xE0329C74` | 88 | `sssUnLockEngineResourcesLossless %x(%x)` | ≈ `TTL_Finish` (unlock half) |
| `0xE0329C98` | 290 | `CompLosslessPath(%d)`, `Lossless Retry(%d)` | ≈ `TTL_Finish` (completion half) |
| `0xE0329268` | 78 | `ReqLosslessStart(%d)` | job submission |
| `0xE03294DE` | 200 | `sssRequestAllocLosslessMemory(...)` | output buffer alloc |
| `0xE032949E` | 64 | `CompAllocMemSuiteForLossless(%d)` | alloc-complete callback |
| `0xE03295A2` | 102 | `JudgeAllocLosslessMemory Wait/Ok(%d)` | alloc arbitration |
| `0xE0329F96` | 64 | `CompReAllocMemSuiteForLossless(%d)` | realloc callback |
| `0xE0329FD6` | 82 | `RetryAllocLosslessMemory(%d)` | retry allocator |
| `0xE032A028` | 144 | `EV_LOCK_ENGRSC_LOSSLESSPATH(%d)(%d)` | engine-resource event |
| `0xE0327E88` | 314 | `LosslessPath Skip(%d)` | skip path |
| `0xE032804E` | 72 | `NotifyLosslessPathComp(%d)` | completion notify |
| **`0xE0213AE4`** | 122 | both `JPCORE_RESTRICTION_*` asserts | **geometry validator** |
| `0xE0246A88` | 22 | `JpCore.c` | JPCORE register accessor |
| `0xE0246F2C` | 202 | `JpCoreIntrHandler` | encoder completion IRQ |
| `0xE015936A` | 184 | `LosslessEncode.c` | encode entry |
| `0xE01D6D46` | 136 | `LosslessEncodeBase.c` | encode base |
| `0xE051C874` | 192 | `Degeen2Lossless` | de-Bayer/gain stage |
| `0xE03420C6` | 180 | `Degeen2GainRegForLossless` | digital-gain hook (3 callers) |

Two shared helpers, worth naming because they appear in every trace above:
`0xE043B4F0` is an ARM veneer (`LDR PC,[PC,#-4]` → `0xDF006E6D`) to **`DryosDebugMsg`**, which
[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/platform/6D2.111/stubs.S](ml/platform/6D2.111/stubs.S)
already has at `:68` as `0xdf006e6c`. `0xE0617620` is `ASSERT(exprStr, fileStr, line)`.

### 2. Call tree

The subsystem is **not** a flat callable API. It is a DryOS **StateObject state machine** whose
handlers live in a transition table at **`0xE090EAF0..0xE090ED5C`** — pairs of
`{nextState, handlerFnPtr}`. Almost every function above has *zero* direct `BL` callers and is
reached only through that table. This is the structural reason `TwoInTwoOut`-style direct entry
points do not exist on D7.

```
 SsDevelopState StateObject  (file string "./SsDevelop/SsDevelopState.c" @0xE03281C4)
   table 0xE090EAF0 ─┬─[0xE090EC84]→ 0xE0329268  ReqLosslessStart
                     ├─[0xE090ECA4]→ 0xE03294DE  sssRequestAllocLosslessMemory
                     │                   └─→ 0xE032949E CompAllocMemSuiteForLossless
                     ├─[0xE090ECCC]→ 0xE03295A2  JudgeAllocLosslessMemory
                     ├─[0xE090ECEC]→ 0xE0329660  LockEnginResLosslessPath
                     │                   └─BL→ 0xE0329636 sssAsyncLockEngineResourcesLossless
                     │                            └─(async)→ 0xE0329608 CompLosslessPathResLockCB
                     │                                          └─→ 0xE03296EA CompLosslessPathCB
                     ├─[0xE090ED14]→ 0xE0329B78  StartLosslessPath
                     │                   └─BL→ 0xE032A27C  (real start)
                     ├─[0xE090ED3C]→ 0xE0329C98  CompLosslessPath / Lossless Retry
                     │                   └─→ 0xE0329C74 sssUnLockEngineResourcesLossless
                     ├─[0xE090ED44]→ 0xE0329FD6  RetryAllocLosslessMemory
                     └─[0xE090EAFC]→ 0xE032A028  EV_LOCK_ENGRSC_LOSSLESSPATH

 args setter 0xE032973C is called from 0xE032A2B2 (inside 0xE032A27C, the starter)
   └─→ 0xE0342246 / 0xE034226C / 0xE03422B0  →  0xE03420C6 Degeen2GainRegForLossless
```

Level-2 callers of the two externally-reachable entries:
`0xE0329268` ← `0xE0B20EF0` (in `0xE0B20744`) ← `0xE058F650`;
`0xE032A028` ← `0xE074651A` (in `0xE07459BC`) ← `0xE095DD54`.

### 3. The args structs — recovered field by field

`0xE032973C(ctx, argsPair, job)` where `argsPair[0] = LosslessPathRsc*`, `argsPair[1] =
LosslessPathParam*`. Offsets read directly off the `LDR Rn,[Rbase,#imm]` feeding each `DebugMsg`,
and confirmed against Ghidra's decompilation of the same function.

```c
struct LosslessPathRsc {          // argsPair[0]
    void *pRscAry;                // +0x00   resource-ID array   (cf. lossless.c:214-232)
    uint32_t RscNum;              // +0x04   entry count
    void *SharememTbl;            // +0x08
    uint32_t SharememNum;         // +0x0C   == 4 for mode 0, 9 for modes 1/2
    uint32_t LosslessEncMode;     // +0x10   0 / 1 / 2  — see below
    uint32_t RdBayCh;             // +0x14   read  EDMAC channel (Bayer in)
    uint32_t WrRawCh;             // +0x18   write EDMAC channel (raw out)   [inferred from spacing]
    uint32_t WrThumbCh;           // +0x1C   write EDMAC channel (thumbnail out)
};
struct LosslessPathParam {        // argsPair[1]
    void *pHuffmanTable;          // +0x00   explicit — the D5 path had this implicit
    uint32_t PackMemNum;          // +0x04
    void *pMemList;               // +0x08
    void *RdBayAddress;           // +0x0C
    void *WrThumbAddress;         // +0x10
};
```

**`LosslessEncMode` values — the spike's "second-order unknown" is answered.** `0xE032973C`
switches on a picture-quality code and asserts (`SsDevelopState.c:1616`) on anything else:

| quality code | `LosslessEncMode` | `SharememNum` | gain hook |
|---|---|---|---|
| `0x1000` (and `0x10000`) | **0** | 4 | `0xE0342246` |
| `0x8000` | **1** | 9 | `0xE034226C` |
| `0x4000` | **2** | 9 | `0xE03422B0` |

Three modes, same shape as D5's RAW / MRAW / SRAW. **Mode 0 is the one ML wants.**

### 4. JPCORE geometry restrictions — resolved to constants

`0xE0213AE4(InputWidth, InputHeight, ...)`, decompiled:

```c
if ((param_1 & 0xf) != 0) ASSERT("!( InputWidth  % JPCORE_RESTRICTION_HORIZONTAL_MULTIPLE )", …, 356);
if ((param_2 & 0x7) != 0) ASSERT("!( InputHeight % JPCORE_RESTRICTION_VERTICAL_MULTIPLE   )", …, 357);
```

> **`JPCORE_RESTRICTION_HORIZONTAL_MULTIPLE = 16`, `JPCORE_RESTRICTION_VERTICAL_MULTIPLE = 8`.**

`res_x` must be a multiple of 16 and `res_y` a multiple of 8 or the camera asserts. This is the
D7 analogue of PR #292's "encodable width `4 mod 8`" and is a hard gate on phase 3 step 2.

### 5. MMIO — the D7 JPCORE register window

Resolved by walking every `LDR`-literal and `MOVW`/`MOVT` inside the `JpCore.c` translation unit
(30 reference sites, code span `0xE0246A90..0xE0247560`):

| Address | Hits | Note |
|---|---|---|
| **`0xD0100000`** | 21 | **JPCORE base** — also used by `JpCoreIntrHandler` |
| `0xD0100200` | 2 | |
| `0xD0100400` | 4 | |
| `0xD0100500` | 1 | |
| `0xD0100600` | 1 | |
| `0xD0100928` | 1 | |
| `0xD0101000` | 2 | second bank |

> **The 6D2's JPCORE window is `0xD0100000..0xD0101FFF`.**

qemu-eos maps JPCORE at the D4/D5 addresses `0xC0E00000` / `0xC0E10000` / `0xC0E20000`
(`qemu-eos/hw/eos/eos.c:651-653`), which as section 5 predicted is **not mapped at all for this
model**. Adding a `{ "JP7", 0xD0100000, 0xD0101FFF, eos_handle_jpcore, 2 }` window is now a
one-line change and is the cheapest way to get the call sequence logged in emulation.

For orientation, the ROM-wide MMIO histogram is dominated by `0xDF000000` (82 `MOVW`/`MOVT`
pairs) — that is the RAM-resident DryOS core, not engine registers.

### 6. Veneer table and `stubs.S` — still nothing (question 3 answered: no)

ROM0 contains 1336 ARM long-branch veneers (`LDR PC,[PC,#-4]` = `0xE51FF004` + target word),
largest blocks at `0xE0CFBA44`, `0xE0CFBE50`, `0xE0CFC264`, `0xE0CFC670` and `0xE043B188..0xE043B4F8`.
The `0xE043Bxxx` block the brief pointed at is real and contains the `DryosDebugMsg` veneer, but:

- **no** LosslessPath candidate is the target of any veneer;
- **none** of the 25 entries matches any of the 133 addresses in `6D2.111/stubs.S`.

These veneers are long-branch thunks into the RAM-resident core (237 of them target `0xDF000000`),
not an export table. Section 3's conclusion stands — every address above has to be hard-coded.

### 7. What this pass did *not* resolve — honestly

1. **`pRscAry` contents.** The resource-ID array — the direct analogue of `lossless.c:214-232`,
   and a required input — is built elsewhere; `0xE032973C` only stores the pointer. Not traced.
   **This is the single biggest remaining phase-1 item.**
2. **`WrRawCh` at `+0x18` is inferred**, from `RdBayCh` at `+0x14` and `WrThumbCh` at `+0x1C`.
   The instruction window around its `DebugMsg` did not decode cleanly. Low risk, unconfirmed.
3. **The StateObject event/state numbering.** The table at `0xE090EAF0` was dumped and the
   handlers identified, but the input-event IDs and state indices that drive it were not decoded,
   so *how* ML would enter the machine (post an event vs. call a handler directly) is still open.
   This is the D7 replacement for "call `TTL_Prepare`, then `TTL_Start`" and it is not yet answered.
4. **`0xE032A27C`** (the real starter, 100 bytes) was located but not decompiled or traced into
   the EDMAC/register writes. The engine-start register poke itself is therefore *not* pinned to a
   specific offset within the `0xD0100000` window — only the window is known.
5. **Ghidra auto-analysis was deliberately not run.** The pass used `-noanalysis` plus seeded
   Thumb disassembly at 25 known entries, because full auto-analysis of a 32 MiB blob with no
   entry points was unnecessary once the reference sites were known from first principles. A full
   analysis run would likely improve items 1, 3 and 4 and is the obvious next Ghidra step.
6. Nothing here is validated against hardware. All of it is static.

### 8. Effect on the estimate

Phase 1 was budgeted at 3–5 sessions. Roughly 60–70% of it is now done in one pass: the seven
entry points exist and are named, both structs are recovered, `LosslessEncMode` is decoded, and
the geometry constraint is a concrete pair of integers. The async-lock protocol is *mapped* but
not *understood* — the StateObject entry mechanism (item 3) is the real remaining risk and is the
thing most likely to invalidate the "seven addresses" model that
[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/modules/silent/lossless.c](ml/modules/silent/lossless.c)
is built around. **Revised phase 1 remainder: 1–2 sessions.** Phases 2 and 3 are unchanged.

### 9. Reproduction

```bash
cd "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2"

# Ghidra 12.1.2, headless, seeded Thumb disassembly (no auto-analysis needed)
nix build --no-link --print-out-paths 'nixpkgs#ghidra-bin'
"$(nix build --no-link --print-out-paths 'nixpkgs#ghidra-bin')/bin/ghidra-analyzeHeadless" \
    /tmp/gproj p6d2 \
    -import roms/6D2/ROM0.BIN \
    -processor ARM:LE:32:Cortex -loader BinaryLoader -loader-baseAddr 0xE0000000 \
    -noanalysis -scriptPath /tmp/gs -postScript LosslessProbe.java
# LosslessProbe.java: set TMode=1 over the whole block FIRST (else every seed after the
# first throws ContextChangeException), then DisassembleCommand + CreateFunctionCmd per seed.

# the encoding the earlier passes missed — 16-bit Thumb ADR (T1)
#   halfword h in 0xA000..0xA7FF  =>  target = ((addr+4) & ~3) + (h & 0xFF)*4
```

No ROM copy was made; Ghidra read `roms/6D2/ROM0.BIN` in place and the scratch project lives
outside the repo.

---

## Ghidra pass 2 — 2026-08-15

**Status:** phase 1 static RE complete. Read-only, nothing built, nothing committed, no ROM copied
out of the project tree.
**Headline:** both gating questions are answered. `pRscAry` is **NULL on this path** — the real
resource-ID array lives in the SsDevelop task context and is dumped below (16 IDs for the mode ML
wants). The StateObject table decodes to a **7-input × 4-state** machine driven by
`StateTransition` at `0xE04E3280` with **global input IDs 20–26**, and the whole encode is a
self-driving chain: a caller posts **one** event (ID 20) and the machine runs to completion.

### 0. Method — Ghidra was fetched and then not needed

`nix build nixpkgs#ghidra-bin` resolved from cache to
`/nix/store/l7ijhav4ff3vmfkz99rqaigha3qwvf9g-ghidra-12.1.2` in seconds (pass 1 had already
populated the store). It was **not used**. Once pass 1 named the functions, both open questions
reduced to (a) decoding a static data table and (b) constant-propagation over <600 bytes of Thumb —
both of which `arm-none-eabi-objdump -b binary -m arm -M force-thumb --adjust-vma=<addr>` on a ROM
slice answers faster than auto-analysing a 32 MiB blob with no entry points. Literal-pool and
`ADR`-target scans were done in Python directly over `ROM0.BIN`.

This is worth recording as a methodology result, because it is now two passes in a row: **the
expensive-disassembler assumption in section 3 has been wrong both times.** What actually resolves
this ROM is knowing the encodings (pass 1: Thumb `ADR` T1) and reading Canon's data tables
(this pass).

### 1. `pRscAry` — resolved, and the answer is "not where the struct says"

#### 1.1 `LosslessPathRsc.pRscAry` is always NULL

`0xE032973C` does not merely *fail to build* the array — it explicitly **zeroes both fields** in
every one of the three mode branches. The quality code (returned by `0xE04EEA60(job)`) is compared
at `0xE0329786`–`0xE032979C` and dispatched:

| quality | branch | writes |
|---|---|---|
| `0x1000`, `0x10000` | `0xE0329ACA` | `Rsc+0x10 = 0` (EncMode 0), **`Rsc+0x00 = 0`**, **`Rsc+0x04 = 0`**, `Rsc+0x08 = 0xE0342596()`, `Rsc+0x0C = 4` |
| `0x8000` | `0xE0329B10` | `Rsc+0x10 = 1`, **`Rsc+0x00 = 0`**, **`Rsc+0x04 = 0`**, `Rsc+0x08 = 0xE03425A0()`, `Rsc+0x0C = 9` |
| `0x4000` | `0xE0329B44` | `Rsc+0x10 = 2`, **`Rsc+0x00 = 0`**, **`Rsc+0x04 = 0`**, `Rsc+0x08 = 0xE03425A0()`, `Rsc+0x0C = 9` |
| anything else | — | `ASSERT(SsDevelopState.c:1616)` |

(`r0` is set to 0 at `0xE0329784` and never reloaded before the branch targets, so the stores at
`0xE0329AD0`/`0xE0329AD4`, `0xE0329B18`/`0xE0329B1C`, `0xE0329B4C`/`0xE0329B50` are literal zeroes.)

The `pRscAry`/`RscNum` fields are part of the generic `sss*Path` argument shape — the sibling
`sssAsyncLockEngineResourcesRawToYuv` path uses the same struct — and the LosslessPath simply
declines to use them. Pass 1's "`0xE032973C` only stores the pointer" was one step too generous:
it stores a null pointer.

#### 1.2 Where the real array lives

Resource arbitration is delegated to the **SsDevelop task context**, and the async lock request is
a pointer *into* that context. From `0xE0329660` (`LockEnginResLosslessPath`):

```
e0329690  mov  r1, r6                 ; r6 = job
e0329694  bl   0xE032A202             ; "does this job need a lock?"
e032969c  beq  0xE03296CC             ; no -> "Wait LosslessPath(%d)", no lock
e032969e  bl   0xE04EEA60(job)        ; quality code
e03296a2  cmp  r0, #0x10000
e03296a6  beq  0xE03296C2             ;   -> ctx+0x1C
e03296aa  bl   0xE04EEA60(job)
e03296ae  cmp  r0, #0x1000
e03296b2  beq  0xE03296C2             ;   -> ctx+0x1C
e03296b6  ldr  r1, =0xE0329609        ; CompLosslessPathResLockCB
e03296b8  add.w r0, r4, #48           ;   -> ctx+0x30   (MRAW/SRAW)
e03296bc  bl   0xE0329636             ; sssAsyncLockEngineResourcesLossless
...
e03296c2  ldr  r1, =0xE0329609
e03296c6  add.w r0, r4, #28           ;   ctx+0x1C      (RAW — EncMode 0)
e03296ca  b    0xE03296BC
```

`r4 = 0xE036B19E(job)` is the SsDevelop path context. The two embedded lock requests are
initialised by the SsDevelop constructor at `0xE0327218`:

| ctx offset | source | value |
|---|---|---|
| `+0x1C` | `bl 0xE0342600` @`0xE032728E` | **`0xE09425A0`** — pRscAry |
| `+0x20` | `movs r0,#16` @`0xE0327298` | **16** — RscNum |
| `+0x24` | `str r6` @`0xE03272B6` | 0 |
| `+0x28` | `lsls r0,r4,#1` @`0xE03272A2` | lock-slot id `2*i` (byte) |
| `+0x2C` | `str r6` @`0xE03272B0` | 0 |
| `+0x30` | `bl 0xE0342608` @`0xE03272B8` | **`0xE09425E0`** — pRscAry |
| `+0x34` | `movs r0,#23` @`0xE03272C2` | **23** — RscNum |
| `+0x38` | `str r6` @`0xE03272E2` | 0 |
| `+0x3C` | `add.w r0,sl,r4,lsl #1` @`0xE03272CC` | lock-slot id `2*i+1` (byte) |
| `+0x40` | `str r6` @`0xE03272DE` | 0 |

So the lock-request record is 20 bytes:

```c
struct EngResLockReq {            /* 0x14 bytes */
    uint32_t *pRscAry;            /* +0x00 */
    uint32_t  RscNum;             /* +0x04 */
    void     *cbParam;            /* +0x08  written by 0xE0329636 (`str r5,[r4,#8]`)  */
    uint8_t   lockSlotId;         /* +0x0C */
    void    (*cb)(void *, int);   /* +0x10  written by 0xE0329636 (`str r6,[r4,#16]`) */
};
```

The getters are the usual Canon table/count pairs in `Degeen*`-adjacent code:

| Function | Returns |
|---|---|
| `0xE0342600` | `0xE09425A0` (pRscAry, RAW) |
| `0xE0342604` | `16` |
| `0xE0342608` | `0xE09425E0` (pRscAry, MRAW/SRAW) |
| `0xE032460E` | `23` |

`0xE09425A0` is referenced from exactly one place in the whole ROM — the literal pool at
`0xE0342630` that feeds these getters. There is no second consumer.

#### 1.3 The actual resource IDs

Encoding is identical to DIGIC 5: **`(class << 16) | id`**, the same shape as
[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/modules/silent/lossless.c](ml/modules/silent/lossless.c)
`:214-232`. Only the class numbering changed (D7 has more engine blocks).

> **`LosslessEncMode 0` (RAW — the mode ML wants), `pRscAry = 0xE09425A0`, `RscNum = 16`:**
>
> ```c
> /* 6D2 1.1.1, ROM0 @ 0xE09425A0 — LosslessPath RAW resource IDs */
> static const uint32_t lossless_res_6d2_raw[16] = {
>     0x00320022, 0x00320003, 0x0032000C, 0x0026000B,
>     0x00260084, 0x00260085, 0x00260029, 0x00260036,
>     0x000F0000, 0x000E0000, 0x001B0000, 0x0026003A,
>     0x00340000, 0x00340001, 0x0034000E, 0x0034000F,
> };
> ```

> **`LosslessEncMode 1/2` (MRAW/SRAW), `pRscAry = 0xE09425E0`, `RscNum = 23`:**
>
> ```
> 0x00320022 0x00320003 0x0032000C 0x0026000B 0x00260085 0x00260029 0x00260036
> 0x000F0000 0x000E0000 0x001B0000 0x0026003A 0x001A0000 0x00300000 0x00260088
> 0x00340000 0x00340001 0x0034000E 0x0034000F 0x00340008 0x00340009 0x0034000A
> 0x0034000B 0x0034000C
> ```

Note the RAW list is *not* a subset of the SRAW list — RAW has `0x00260084`, which appears
**exactly once in the entire 32 MiB ROM** (at `0xE09425B0`). That ID is the lossless-RAW path's
private resource.

#### 1.4 How the lock is actually taken (it never touches `CreateResLockEntry`)

`0xE0329636` is 42 bytes and does no locking itself:

```
e0329650  str  r6, [r4, #16]          ; req->cb     = CompLosslessPathResLockCB (0xE0329609)
e0329654  str  r5, [r4, #8]           ; req->cbParam = job
e032965a  ldr  r0, =0xE0328499        ; completion trampoline
e032965c  b.w  0xE051B5C2             ; tail call
```

`0xE051B5C2` lives in `./Shoot/ShtPath/ShtSsDevelopPath/ShtSsDevelopPath.c` and is a two-line
registration shim:

```
e051b5c2  ldr  r3, =<RAM globals>      ; 0xE051B738
e051b5c6  movs r1, #11                 ; event id 11 = ASYNC LOCK
e051b5c8  str  r0, [r3, #16]           ; stash the trampoline
e051b5ca  ldr  r0, =<hTaskClass>       ; 0xE051B774
e051b5cc  b.w  0xE042A6D4              ; post to the ShtSsDevelopPath task
```

The sibling at `0xE051B5D0` uses **event id 12** and slot `+0x14` — that is the async *unlock*,
reached from `0xE0329C74` (`sssUnLockEngineResourcesLossless`).

`0xE0328498` is the completion trampoline: it reads `req->cbParam` (`+0x08`) and `req->cb`
(`+0x10`) and tail-calls the callback, i.e. `CompLosslessPathResLockCB(job, 0)`.

**Consequence for ML:** the D5 model in `lossless.c` — build a resource array, call
`CreateResLockEntry`, hand the handle to `TTL_Prepare` — has no D7 counterpart on this path. ML
does not create a lock entry; it either (a) drives the state machine and lets the SsDevelop task do
the locking with `0xE09425A0`, or (b) replicates the lock by calling `0xE051B5C2` with its own
`EngResLockReq`. Option (a) is strictly less work and is what the call sequence in §4 assumes.

### 2. Fields pass 1 left inferred — now read directly

The three EDMAC channel numbers are written unconditionally in the common tail at `0xE03297AC`
(all three mode branches `b` back to it):

```
e03297ae  movs r0, #17   ; str r0,[Rsc,#0x18]   WrRawCh   = 17
e03297b2  movs r0, #48   ; str r0,[Rsc,#0x14]   RdBayCh   = 48
e03297b8  movs r0, #3    ; str r0,[Rsc,#0x1C]   WrThumbCh = 3
```

Pass 1's item 2 ("`WrRawCh` at `+0x18` is inferred") is confirmed correct — the trace at
`0xE0329A3C` uses format `0xE0329D80` `"LosslessPathRsc WrRawCh=%#x"` for `[Rsc+0x18]`, and
`0xE0329A44` uses `0xE0329D9C` `"...WrThumbCh"` for `[Rsc+0x1C]`.

> **`RdBayCh = 48`, `WrRawCh = 17`, `WrThumbCh = 3`.**

The `LosslessPathParam` offsets are confirmed the same way from the trace block at
`0xE0329A52`–`0xE0329A80`: `+0x00 pHuffmanTable`, `+0x04 PackMemNum`, `+0x08 pMemList`,
`+0x0C RdBayAddress`, `+0x10 WrThumbAddress`. `PackMemNum` and `pMemList` are filled from the
output memSuite by `0xE05EB19E(memsuite, &Param->PackMemNum, &Param->pMemList)` at `0xE03297C6`.

#### `SharememTbl` is a register script, not a resource list

`0xE0342596` returns `0xE0942208 + 0x88`, `0xE03425A0` returns `0xE0942208 + 0xA8`. The table is an
array of **`{MMIO address, value}` pairs**, and `SharememNum` is the pair count — the two tables
tile the region exactly (mode 0 ends where mode 1/2 begins):

| Mode 0 (`SharememNum = 4`, `0xE0942290`) | Modes 1/2 (`SharememNum = 9`, `0xE09422B0`) |
|---|---|
| `0xD0003200 <- 0x80180000` | `0xD0003200 <- 0x80180000` |
| `0xD0003204 <- 0x80180004` | `0xD0003204 <- 0x80180004` |
| `0xD0003238 <- 0x80180008` | `0xD0003238 <- 0x80180008` |
| `0xD000323C <- 0x8018000C` | `0xD000323C <- 0x8018000C` |
| | `0xD0003220 <- 0x80120000` |
| | `0xD0003224 <- 0x80130000` |
| | `0xD0003228 <- 0x80140000` |
| | `0xD000322C <- 0x80150000` |
| | `0xD0003230 <- 0x80160000` |

`0x8018xxxx` decodes as `ENABLE(bit31) | (0x18 << 16) | port`, and **`0x18` = 24 = the
`MEM1TOLOSSLESS` index** in the engine path-name table at `0xE09420B0` (section 3). That is an
independent confirmation that this table wires the shared-memory arbiter to the lossless path.

> **New MMIO window: `0xD0003000` (engine shared-memory/connection arbiter), distinct from the
> JPCORE window `0xD0100000..0xD0101FFF` found in pass 1.**

### 3. The StateObject — decoded

#### 3.1 The object

Name string is **`"SSSState"`** at `0xE0F822F8` (neighbours `SCSState`, `SBSState`, `SDSState`,
`SDCSState`, `SPSState`, `STSState`, `SFSState` — Canon's per-subsystem state machines).

Three `CreateStateObject` calls sit in the SsDevelop constructor at `0xE0327218`, through veneer
`0xE043B440` → `0xDF00A1FB`:

| Call site | `r0` name | `r1` | `r2` matrix | `r3` | `[sp]` |
|---|---|---|---|---|---|
| `0xE0327258` | `"SSSState"` | 0 | `0xE090EB18` | 13 | 2 |
| `0xE032726E` | `"SSSState"` | 0 | `0xE090EB68` | 20 | 5 |
| `0xE0327284` | `"SSSState"` | 0 | `0xE090EC80` | 27 | 4 |

Results are stored at `+0x00`, `+0x04`, `+0x08` of a 68-byte instance struct allocated at
`0xE0327242`; the instance pointer array is at **RAM `0x5784`** (`0x5738 + 0x4C`, indexed by
instance number), and the SsDevelop globals block is at RAM `0x5738`. A fourth matrix at
`0xE090EA58` (8 rows × 3 states) exists and is created elsewhere — the site at `0xE03274CC` also
loads `0xE090EA54` — but was not chased.

#### 3.2 Entry format

`struct state_transition { uint32_t next_state; void *handler; }`, exactly as
[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/src/state-object.h](ml/src/state-object.h)
`:40-44` describes; rows are inputs, columns are states. The decisive structural tell: **every
non-handler cell holds `{column_index, NULL}`** — "stay in this state, do nothing". That property
holds for all 4 matrices with no exceptions and fixes the row widths unambiguously:

| Matrix | Rows | States | Region | Ends at |
|---|---|---|---|---|
| `0xE090EA58` | 8 | 3 | `0xE090EA58..0xE090EB18` | — |
| `0xE090EB18` | 5 | 2 | `0xE090EB18..0xE090EB68` | — |
| `0xE090EB68` | 7 | 5 | `0xE090EB68..0xE090EC80` | — |
| **`0xE090EC80`** | **7** | **4** | **`0xE090EC80..0xE090ED60`** | `0xE090ED6C` starts `"SPSState"` |

They tile the region back-to-back with no gap and no overlap.

#### 3.3 The LosslessPath transition table, decoded

`0xE090EC80`, 7 inputs × 4 states, 28 entries, 224 bytes. Global input IDs are **20–26**
(derivation in §3.4). Cells shown as `next_state / handler`; blank = `{state, NULL}` no-op.

| input | state 0 | state 1 | state 2 | state 3 |
|---|---|---|---|---|
| **20** `ReqLosslessStart` | `0` / `0xE0329268` | — | — | — |
| **21** `sssRequestAllocLosslessMemory` | `1` / `0xE03294DE` | — | — | — |
| **22** `JudgeAllocLosslessMemory` | — | `1` / `0xE03295A2` | — | — |
| **23** `LockEnginResLosslessPath` | — | `2` / `0xE0329660` | `2` / `0xE032A0B8` | — |
| **24** `StartLosslessPath` | — | — | `3` / `0xE0329B78` | — |
| **25** `CompLosslessPath` | — | — | — | `0` / `0xE0329C98` |
| **26** `RetryAllocLosslessMemory` | `2` / `0xE0329FD6` | — | — | — |

Raw cell addresses for the seven handlers: `0xE090EC84`, `0xE090ECA4`, `0xE090ECCC`, `0xE090ECEC`,
`0xE090ECF4`, `0xE090ED14`, `0xE090ED3C`, `0xE090ED44`. Each of `0xE0329269`, `0xE0329B79`,
`0xE0329C99` occurs **exactly once** in the whole ROM, at those cells — there is no second copy of
this matrix.

State semantics fall straight out:

| state | meaning |
|---|---|
| **0** | idle / request accepted |
| **1** | output memory allocation in flight |
| **2** | engine resources locked, ready to start |
| **3** | JPCORE encoding in flight |

#### 3.4 The DryOS API, and why the input IDs are 20–26

> **`StateTransition` is at `0xE04E3280`**, called as
> `StateTransition(stateobj, ctx, inputId, job, 0)` — `r0` = state object (`ctx[+8]`), `r1` = ctx,
> `r2` = input ID, `r3` = job, one stack word = 0.

Thirty call sites exist in the `SsDevelopState.c` translation unit
(`0xE0327218..0xE032A400`). The input ID is a `movs r2,#imm` immediately before each. Four
independent chains fix the base at 20, because in every case the ID posted is exactly the ID whose
matrix cell holds the function that must run next:

| Posting site | inside | posts | matrix cell reached | handler |
|---|---|---|---|---|
| `0xE0327FB8` | handler of input 9 (`0xE0327E88`, a *different* matrix) | **20** | `0xE090EC84` | `ReqLosslessStart` — **the external entry point** |
| `0xE0329454` | `ReqLosslessStart` `0xE0329268` | **21** | `0xE090ECA4` | `sssRequestAllocLosslessMemory` |
| `0xE0329498`, `0xE03294D8` | `0xE032945E`, `CompAllocMemSuiteForLossless` `0xE032949E` | **22** | `0xE090ECCC` | `JudgeAllocLosslessMemory` |
| `0xE0329602` | `JudgeAllocLosslessMemory` `0xE03295A2` | **23** | `0xE090ECEC` | `LockEnginResLosslessPath` |
| `0xE0329630` | `CompLosslessPathResLockCB` `0xE0329608` | **24** | `0xE090ED14` | `StartLosslessPath` |
| `0xE0329736` | `CompLosslessPathCB` `0xE03296EA` | **25** | `0xE090ED3C` | `CompLosslessPath` |
| `0xE0329FD0` | `CompReAllocMemSuiteForLossless` `0xE0329F96` | **24** | `0xE090ED14` | `StartLosslessPath` (after realloc) |
| `0xE032A096` | `EV_LOCK_ENGRSC_LOSSLESSPATH` `0xE032A028` | **23** | `0xE090ECEC` | `LockEnginResLosslessPath` |

`stubs.S` has no stub for `0xE04E3280`; the nearest existing thing is `msg_queue_post` at
`0xdf00b337` ([/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/platform/6D2.111/stubs.S](ml/platform/6D2.111/stubs.S) `:204`),
which is a different API. `StateTransition` is a new stub ML would have to add.

### 4. Sketched call sequence for ML

The important structural finding: **this is not a seven-call API, it is a one-shot post.** Once
input 20 lands, the machine self-drives — every step posts its own successor from its completion
callback. ML supplies the input buffer and the output memSuite and waits.

```c
/* 6D2 1.1.1 — sketch, NOT verified on hardware */

/* ROM */
#define SSSTATE_INSTANCES      0x5784      /* RAM: array of SsDevelop instance ptrs */
#define StateTransition        0xE04E3280  /* (obj, ctx, input, job, 0)             */
#define SSS_EV_REQ_START       20          /* ReqLosslessStart                      */
#define SSS_EV_COMPLETE        25          /* CompLosslessPath -> state 0           */

/* 0. one-time: geometry gate from pass 1 §4 — hard ASSERT if violated */
if (width % 16 || height % 8) return -1;

/* 1. get the SsDevelop path context + its state object.
 *    ctx  = 0xE036B19E(job)       -> holds pRscAry at +0x1C / +0x30
 *    obj  = ctx[+8]               -> the SSSState object
 *    NOTE: obtaining a valid `job` is the unresolved step — see §6.1 */

/* 2. quality code must be 0x1000 or 0x10000 so that
 *      - 0xE032973C picks LosslessEncMode 0 (RAW),
 *      - 0xE0329660 picks pRscAry = 0xE09425A0 / RscNum = 16.
 *    Both read it via 0xE04EEA60(job), so it is a property of the job, not an argument. */

/* 3. fire the machine. Everything after this is Canon's. */
StateTransition(obj, ctx, SSS_EV_REQ_START, job, 0);

/*    20 ReqLosslessStart            -> posts 21
 *    21 sssRequestAllocLosslessMemory  (async alloc of the output memSuite)
 *         `-> CompAllocMemSuiteForLossless 0xE032949E posts 22
 *    22 JudgeAllocLosslessMemory    -> posts 23   ("Wait(%d)" / "Ok(%d)")
 *    23 LockEnginResLosslessPath    -> 0xE0329636 -> 0xE051B5C2 -> event 11
 *                                      to the ShtSsDevelopPath task, which locks
 *                                      the 16 IDs at 0xE09425A0
 *         `-> trampoline 0xE0328498 -> CompLosslessPathResLockCB 0xE0329608 posts 24
 *    24 StartLosslessPath 0xE0329B78 -> 0xE032A27C
 *           0xE032A2B2  0xE032973C(ctx, ctx[+0x18], job)   fills Rsc + Param
 *           0xE032A2BA  0xE051B560(argsPair, 0xE032A4F0)   hands them to the engine
 *         `-> JPCORE IRQ 0xE0246F2C -> CompLosslessPathCB 0xE03296EA posts 25
 *    25 CompLosslessPath 0xE0329C98  -> 0xE0329C74 sssUnLockEngineResourcesLossless
 *                                       (event 12) ; next_state = 0 (idle)
 *                                    -> "Lossless Retry(%d)" on failure, which posts 26
 */

/* 4. wait. The completion hook is CompLosslessPathCB (0xE03296EA); the compressed
 *    size is produced in CompLosslessPath (0xE0329C98) — the D7 equivalent of
 *    TTL_Finish's return value. Exact field not yet located (see §6.3). */
```

Mapped onto the seven D5 pointers in
[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/modules/silent/lossless.c](ml/modules/silent/lossless.c) `:69-75`:

| D5 pointer | D7 equivalent | Callable directly? |
|---|---|---|
| `TTL_SetArgs` | `0xE032973C` | no — called from inside `0xE032A27C` |
| `TTL_Prepare` | input **23** → `0xE0329660` | no — post the event |
| `TTL_RegisterCBR` | — | gone; the callback is wired by the state machine |
| `TTL_SetFlags` | — | gone; folded into the job's quality code |
| `TTL_Start` | input **24** → `0xE0329B78` | no — post the event |
| `TTL_Stop` | — | not found (see §6.4) |
| `TTL_Finish` | input **25** → `0xE0329C98` | no — posted by the JPCORE IRQ |
| `CreateResLockEntry` + array | **not used**; `pRscAry = 0xE09425A0` is Canon's, in the ctx | n/a |

### 5. LiveView / movie-mode contention — measured, not guessed

Section 5's "biggest unknown" can now be quantified. Intersecting the 16 RAW resource IDs against
every other resource array in ROM0 (whole-word match on `(class<<16)|id`, arrays attributed to a
translation unit by the nearest `__FILE__` string to their referencing code):

| Array | Owning TU | IDs shared with lossless-RAW |
|---|---|---|
| `0xE0E897AC`, `0xE0E89B70` | **`MotionJPEG/MovieRecorder/Fring.c`** | `0x320003`, `0x340000`, `0x340001`, `0x34000E`, `0x34000F` — **5 of 16** |
| `0xE09461A4` | **`ImgSeqCoop/ImgSeqCoopLv.c`**, `Epp/Vram/VramController.c` | `0x340000`, `0x340001`, `0x34000E`, `0x34000F` — **4 of 16** |
| `0xE08363B8` | `DevCommon/PathParam/Utility/DecodeLossless.c` | `0x0E0000`, `0x0F0000`, `0x320003`, `0x320022` |
| `0xE0836518` | `DevCommon/PathParam/Utility/{DecodeJpeg,Yuv2JpegEncode}.c` | `0x0E0000`, `0x0F0000`, `0x320003`, `0x320022` |
| `0xE0942310` region (other SsDevelop paths, incl. `LvCommon/LvCFilterCommon.c`, `Epp/Vram/VramStage.c`) | SsDevelop / DevCommon | `0x320022`, `0x320003`, `0x32000C`, `0x0F0000`, `0x0E0000` |

> **Verdict: the contention is real and specific.** The movie recorder claims resource class `0x34`
> ids `{0, 1, 0x0E, 0x0F}` — all four of which the lossless RAW path also locks — plus `0x320003`.
> While `Fring.c` holds those, `LockEnginResLosslessPath` cannot complete; it will sit in the async
> lock (input 23, state 1) rather than advance to state 2, and `"Wait LosslessPath(%d)"`
> (`0xE0329968`) is the trace that would fire.

This is the DIGIC 7 form of PR #292's finding, and it is *narrower* than feared: the collision is 4–5
IDs out of 16, and it is with the **movie recorder and the LV VRAM controller**, not with the whole
Evf pipeline. Three practical consequences:

1. The lock is **asynchronous and queued**, not a spin — so the failure mode is a stalled encode,
   not an immediate ASSERT. That is a materially better starting point than D4/D5.
2. Since ML's raw path already bypasses Canon's H.264 recorder, whether `Fring.c` actually holds
   those resources during ML raw recording is an empirical question — it may not, in which case the
   collision never materialises. **This is now a one-experiment question, not a research project.**
3. `0x00260084` is unique to the lossless RAW list ROM-wide, so at least one required resource has
   zero contention.

Phase 2's "stills first, engine idle" plan is unchanged and remains correct: it avoids all of the
above by construction.

### 6. What this pass did *not* resolve — honestly

1. **How ML obtains a valid `job`/`ctx` pair.** This is now the single biggest remaining item and it
   has replaced `pRscAry` at the top of the list. Every handler takes `(ctx, job, ...)`; the job
   carries the quality code (`0xE04EEA60`), the picture object (`0xE04EE98A`), and the output
   memSuite. ML must either synthesise one or hijack an existing SsDevelop job. Not traced.
2. **The `CreateStateObject` 4th argument (13 / 20 / 27) is not `max_inputs` as
   [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/src/state-object.h](ml/src/state-object.h) `:64`
   models it.** It is an *exclusive upper bound on the global input ID range*, and the matrices have
   5 / 7 / 7 rows respectively. Worse, handlers post IDs that cross matrix boundaries through a
   single `ctx[+8]` object (`0xE0327E88` posts 12, 13 **and** 20 via the same `ldr r0,[r4,#8]`),
   which the "four objects with disjoint ID ranges" reading does not explain. **The
   input-ID→matrix-row arithmetic inside `0xE04E3280` is not decoded.** This does not affect the
   operational answer — post ID 20, the chain is proven eight ways in §3.4 — but it does mean
   ML cannot safely reuse ML's existing `STATE_FUNC` macro or `stateobj_install_hook` on this
   machine without first reading `0xE04E3280`.
3. **Where the compressed output size is read.** `CompLosslessPath` (`0xE0329C98`, 290 bytes) was
   not decompiled. On D5 `TTL_Finish` returns it; here it must be a field the completion path
   writes. Required before `mlv_lite` can shrink slots.
4. **No `TTL_Stop` equivalent found.** There is no abort input in the 7×4 matrix. Whether an encode
   in state 3 can be cancelled at all is unknown — relevant to `mlv_lite`'s clean stop/drain.
5. **`0xE032A27C` still not traced into the engine registers.** The `0xD0100000` JPCORE poke and the
   `0xD0003000` shared-memory writes are known to exist (§2) but the write sequence at
   `0xE051B560` was not followed.
6. **`0xE032A202`** — the "does this job need a lock" predicate gating `LockEnginResLosslessPath` —
   was only skimmed. It reads a handle at globals `+0x48` and calls `0xE02E853C`/`0xE02E84DE`/
   `0xE02E865C`/`0xE02E8628`. If it returns 0 the path proceeds *without* locking
   (`"Wait LosslessPath(%d)"`), which may be the mechanism by which Canon runs lossless during
   LiveView — worth chasing before assuming §5's contention is fatal.
7. **Who posts input 26** (`RetryAllocLosslessMemory`) was not found; its `next_state = 2` from
   state 0 is anomalous and unexplained.
8. Nothing here is validated against hardware or QEMU. All static.

### 7. Effect on the estimate

Phase 1 was 3–5 sessions, revised after pass 1 to "1–2 remaining". Both nominated blockers are now
closed: the resource IDs are dumped, and the state machine is decoded with the entry event
identified. Item 6.1 (obtaining a job/ctx) is new and is genuinely phase-1 work, and items 6.3/6.4
(output size, abort) are prerequisites for phase 3 rather than phase 2.

**Revised phase 1 remainder: 1 session, focused on 6.1 + 6.3.** Phase 2 (stills, `silent.mo`)
unchanged at 2–3. Phase 3's variance is *reduced* by §5: the LiveView risk is now a bounded,
testable 4-ID collision with a named owner rather than an open-ended unknown. **Total 6–11**, down
from 8–14.

### 8. Reproduction

```bash
cd "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2"
export PATH="$(nix build --no-link --print-out-paths 'nixpkgs#gcc-arm-embedded')/bin:$PATH"

# disassemble any ROM range as Thumb (file offset = addr - 0xE0000000)
slice() {  # slice <addr> <len>
  python3 -c "
import sys,struct
a=int(sys.argv[1],16); n=int(sys.argv[2],0)
open('/tmp/s.bin','wb').write(open('roms/6D2/ROM0.BIN','rb').read()[a-0xE0000000:a-0xE0000000+n])" "$1" "$2"
  arm-none-eabi-objdump -D -b binary -m arm -M force-thumb --adjust-vma="$1" /tmp/s.bin
}

slice 0xE0329ACA 0x50     # pRscAry = 0 in the mode-0 branch
slice 0xE0329660 0x70     # resource-array selection by quality code
slice 0xE0327218 0x80     # CreateStateObject x3 + the two pRscAry getters

# the resource IDs, straight out of ROM0
python3 -c "
import struct; r=open('roms/6D2/ROM0.BIN','rb').read()
for n,a in (('RAW  ',0xE09425A0),('SRAW ',0xE09425E0)):
    c=16 if a==0xE09425A0 else 23
    print(n,' '.join('%08X'%w for w in struct.unpack_from('<%dI'%c,r,a-0xE0000000)))"

# the 7x4 LosslessPath transition table
python3 -c "
import struct; r=open('roms/6D2/ROM0.BIN','rb').read()
for i in range(7):
    b=0xE090EC80+i*32
    print('input %2d:'%(20+i), ' '.join('{%d,%08X}'%struct.unpack_from('<2I',r,b+j*8-0xE0000000) for j in range(4)))"
```

Ghidra 12.1.2 was fetched (`/nix/store/l7ijhav4ff3vmfkz99rqaigha3qwvf9g-ghidra-12.1.2`) but no
project was created and it was not run. Scratch files (ROM slices, the objdump helper, the
translation-unit dump) live in
`/tmp/claude-1000/-home-chris-Vibe-Coding-6D-Mark-II-Magic-Lantern-6D2/d1809f97-1ab5-4672-8a2b-1ab8dcfa3d5e/scratchpad/g2/`
and can be deleted. No ROM was copied outside the project tree except transient slices in that
scratch directory.
