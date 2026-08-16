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
