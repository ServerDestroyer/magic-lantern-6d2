# Card benchmark — measured, session 5

**Status:** measurement complete. Replaces the assumed "~60–90 MB/s" card figure in
[README.md](.planning/spikes/008-lossless-compression-scoping/README.md) §4 "Against the card".

**Headline: the card writes 82.6 MB/s at large buffers.** The 60–90 MB/s assumption is
**CONFIRMED** — the true value sits in its upper-middle third. Every sustainability verdict in
spike 008 §4 survives, and **1080p29.97 upgrades from "marginal, needs 12-bit" to
"sustainable at 14-bit"**.

Source: `bench.mo` full card benchmark + memory benchmark + cache sweep, run on the body,
ML `2026-08-15.6D2.111` build `3f24042a4 dev` (the same tree spike 008 was written against).

---

## 1. Verbatim transcription

### 1.1 `tools/bench/bench0.bmp` — card read/write benchmark

Screen geometry from the BMP header: **720 × 480, 24 bpp, top-down** (`biHeight = -480`),
54-byte header, 3 distinct colours only (`#005200` background, `#000000` text box,
`#EBEBEB` text). Not palettised, and not 1024×768 — the ML screenshot buffer is the classic
720×480 BMP surface regardless of panel size.

```
Benchmark complete.
ML 2026-08-15.6D2.111, 3f24042a4 dev
Mode: PLAY-UNK LCD, Global Draw: ON

Write speed (buffer=16384k):     82.9 MB/s
Read speed  (buffer=16384k):     95.6 MB/s
Write speed (buffer=16384k):     82.6 MB/s
Read speed  (buffer=16384k):     95.7 MB/s
Write speed (buffer=15625k):     81.4 MB/s
Read speed  (buffer=15625k):     95.4 MB/s
Write speed (buffer=4096k):      71.8 MB/s
Read speed  (buffer=4096k):      89.1 MB/s
Write speed (buffer=3906k):      67.8 MB/s
Read speed  (buffer=3906k):      88.3 MB/s
Write speed (buffer=2048k):      65.3 MB/s
Read speed  (buffer=2048k):      84.2 MB/s
Write speed (buffer=1953k):      42.2 MB/s
Read speed  (buffer=1953k):      82.0 MB/s
Write speed (buffer=128k):       15.1 MB/s
Read speed  (buffer=128k):       33.4 MB/s
```

**The card is not identified.** `card_bench.c:130-135` prints `card->type/maker/model` at
y=80 when available; rows y=80..99 of `bench0.bmp` contain **zero** non-background pixels
(verified pixel-wise), so `get_shooting_card()` returned a NULL maker/model on this body.
We know the card's speed but not its make.

### 1.2 `tools/bench/bench1.bmp` — memory/DMA benchmark

```
Benchmark complete.
ML 2026-08-15.6D2.111, 3f24042a4 dev
Mode: PLAY-UNK LCD, Global Draw: ON

Test function:          Display on:      Display off:
memcpy cacheable         97.85 MB/s       99.14 MB/s      OK
memcpy uncacheable       15.60 MB/s       15.79 MB/s      OK
memcpy64 cacheable      108.36 MB/s      109.78 MB/s      OK
memcpy64 uncacheable     14.11 MB/s       14.22 MB/s      OK
dma_memcpy cacheable     50.54 MB/s       50.65 MB/s      OK
dma_memcpy uncacheab    126.71 MB/s      126.91 MB/s      OK
memset cacheable        411.57 MB/s      414.22 MB/s
memset uncacheable      494.33 MB/s      504.33 MB/s
memset64 cacheable      405.78 MB/s      414.62 MB/s
memset64 uncacheable    481.42 MB/s      502.03 MB/s
read32 cacheable        147.15 MB/s      150.70 MB/s
read32 uncacheable       21.91 MB/s       22.21 MB/s
read64 cacheable        147.14 MB/s      151.10 MB/s
read64 uncacheable       25.93 MB/s       26.31 MB/s
```

`dma_memcpy uncacheab` is truncated by the column width in ML's own format string; the row is
`dma_memcpy uncacheable`. The six `OK` markers (verified by cropping the right edge) are the
memcpy-family correctness checks — `mem_bench.c:21-42` runs `memcmp(src,dst,size)` after each
copy-like test and prints `OK` or a red `ERR!`. **All six passed; no `ERR!` anywhere.** The
memset/read rows are not copy-like (`is_memcpy` false at `mem_bench.c:194`) so they carry no
marker.

### 1.3 `tools/bench/cache0.bmp` — cache-size sweep

```
Benchmarking from address 0x100000 done.




                     (plot area — empty)




Now : 22784 bytes (525 MiB/s)
Peak:  2048 bytes (6291 MiB/s)
Drop: 16384 bytes (6234 MiB/s)
```

Only two bands of the 480 rows carry any non-background pixel: **rows 5–24** (the header) and
**rows 410–469** (the three result lines). The `plot_graph_t` XY plot that `mem_perf.c:320-350`
allocates at (5,35) rendered nothing into the screenshot. The numbers are still valid — they
are printed from scalars, not read off the plot.

---

## 2. The numbers that matter

### Card write speed — **82.6 MB/s**

`card_bench.c:136-137` runs the 16 MiB test **twice**, the first pass explicitly commented
`/* warm-up test */`. The post-warm-up figure is the honest one:

| | value | note |
|---|---|---|
| **Write, large buffer** | **82.6 MB/s** | 16 MiB, post-warm-up. Use this. |
| Write, large buffer (warm-up) | 82.9 MB/s | first pass, discard |
| Write, large buffer (16 MB decimal) | 81.4 MB/s | 15625k |
| **Read, large buffer** | **95.7 MB/s** | 16 MiB |
| Write, small buffer | 15.1 MB/s | 128k — irrelevant to raw video, see below |

Honest large-buffer spread: **81.4 – 82.9 MB/s**. Working figure **82.6**, conservative **81.4**.

### Units are decimal MB, and they are directly comparable to the demand figures

Verified in source rather than assumed, because the two benchmarks in this module use
*different* units under the same "MB/s" label:

- `card_bench.c:45` — `speed = (bufsize*times*10/1000)/(t1-t0)` with `t` from `get_ms_clock()`.
  Displayed value = `speed/10` = bytes / (1000 × ms) = **bytes / 10⁶ s → decimal MB/s.**
- `mem_bench.c:170-175` — `speed = bufsize*times*1e6/dt/1024` with `dt` from `get_us_clock()`,
  then `speeds = speed*100/1024`. That is **MiB/s**, mislabelled "MB/s" on screen.

So §1.1 (card) is decimal MB/s and §1.2 (memory) is really MiB/s. Spike 008's demand column is
decimal (3,629,056 B × 23.976 = 87.0 MB/s), so the card figures drop straight into the math
with no conversion. The memory figures do not, but nothing here depends on them.

### Which buffer row applies: the 16 MiB row

`mlv_lite` does not write frame-by-frame. It groups contiguous frames and issues one
`FIO_WriteFile` per group (`mlv_lite.c:3337`), with the group capped at `0xFFFE * 512` =
**33,553,408 B** (`mlv_lite.c:1495`, comment: *"split the group at 32M-512K … after this
number, write speed decreases"*). At 3,629,056 B/frame that is up to 9 frames = 32.7 MB per
call. Real raw-video writes are therefore **larger** than the largest buffer benchmarked, so
the 16 MiB row is the correct — and slightly conservative — proxy. The 15.1 MB/s at 128k is a
red herring for this workload.

### `cache0.bmp` — a different subsystem entirely

`mem_perf.c:110-170` sweeps block size from 128 B to 256 KiB in 128 B steps, timing a
copy from `0x00100000` (cached DRAM), and reports where throughput collapses:

| field | value | meaning (`mem_perf.c:161-164`) |
|---|---|---|
| `Peak` | 2048 B @ **6291 MiB/s** | `max_speed_size` — fastest block size seen |
| `Drop` | 16384 B @ **6234 MiB/s** | `drop_speed_size` — last size before speed fell >10% (`drop_speed < speed*1.1`) |
| `Now` | 22784 B @ **525 MiB/s** | `block_size` when the sweep aborted |

Read: throughput holds ~6.2–6.3 GiB/s up to a **16 KiB** working set, then falls **12×** to
525 MiB/s by 22.8 KiB. That is the **L1 data cache boundary at 16 KiB**, followed by the
sweep's own abort (`slower_count > 50`, `mem_perf.c:157`). This measures the CPU cache
hierarchy, not storage, and has **no bearing on the card-throughput math**. It is useful as
DIGIC 7 core characterisation — the 16 KiB L1D is a hardware fact about this body worth
recording — and nothing more.

---

## 3. Independent cross-check: the recordings agree with the benchmark

The benchmark ran in PLAY mode with no LiveView and no sensor DMA. That raises the obvious
objection — *does the card still do 82.6 MB/s while the sensor is streaming?* The MLVs already
on disk answer it, with no new test needed.

For a clip that auto-stops on buffer-full: frames arrive at demand rate `R`, the card drains at
`C`, recording ends when the buffer `B` fills. So

```
captured_bytes = B + C · T        (T = frames / fps)
```

Frame counts and fps below are **parsed from the MLV block streams**, not taken from prose —
VIDF block count and `MLVI.sourceFpsNom/Denom`. Every VIDF in every file is exactly
**3,629,056 B**, confirming the frame size the math rests on.

Solving pairs of buffer-full auto-stops:

| pair | solved C | solved B |
|---|---|---|
| M15-1924 (393 fr @ 25.000) × M15-2102 (57 fr @ 59.938) | **82.56 MB/s** | 128.3 MB |
| M15-1924 × M15-1934 / 1945 / 2103 / 2106 (57 fr @ ~59.94) | **82.56 MB/s** | 128.3–128.4 MB |
| M15-1924 × M15-2104 (63 fr @ 59.933) | 81.64 MB/s | 142.8 MB |
| M15-1924 × M15-2105 (64 fr @ 59.946) | 81.49 MB/s | 145.3 MB |

**Recording-derived: 81.5 – 82.6 MB/s. Benchmark: 81.4 – 82.9 MB/s.** The two agree to better
than 1%.

Two conclusions follow, and both matter:

1. **Sensor/LiveView contention costs the card essentially nothing.** The benchmark number is
   usable as-is for raw-video planning. This was not obvious a priori and is now measured.
2. **The buffer is not a fixed size.** Holding C = 82.56, the implied `B` across every
   auto-stopped clip is 128.3, 128.4, 141.8, 144.1, 147.8, 151.3 MB — it varies per take with
   whatever Canon's allocator left free. Spike 006's 135 MB sits in the middle of that range.
   Burst-length predictions therefore carry roughly ±10% from buffer variation alone, which is
   now the dominant uncertainty — larger than the uncertainty in the card speed.

Sanity check in the forward direction, C = 82.6, B = 128 MB:

| mode | predicted burst | observed |
|---|---|---|
| 1080p25 uncompressed | 15.75 s | **15.72 s** (M15-1924, 393 fr) |
| 1080p59.94 uncompressed | 0.95 s | **0.95 s** (M15-2102/2103/2106/1934/1945, 57 fr) |

And the negative control: **M15-1901 ran 558 frames over 25.87 s at 21.567 fps** — a demand of
78.27 MB/s — and did *not* auto-stop. A card slower than ~78 MB/s could not have done that.
Recording behaviour alone brackets C to 78.3–84.4 MB/s; the benchmark pins it at 82.6.

---

## 4. Recomputed sustainability

Frame = **3,629,056 B** (measured: every VIDF block in all 16 MLVs). Demand = frame × fps.
Card = **82.6 MB/s**. Compression ratios are spike 008's: 60% = ML's `get_estimated_compression_ratio()`
default for 14-bit lossless, 55%/65% the clean/noisy scene spread, 52% ML's 12-bit default.

### Demand, MB/s

| Mode | Uncompressed | 14-bit @60% | @55% clean | @65% noisy | 12-bit @52% |
|---|---|---|---|---|---|
| 1080p23.976 | 87.01 | **52.21** | 47.86 | 56.56 | 45.25 |
| 1080p25 | 90.73 | **54.44** | 49.90 | 58.97 | 47.18 |
| 1080p29.97 | 108.76 | **65.26** | 59.82 | 70.70 | 56.56 |
| 1080p59.94 | 217.53 | **130.52** | 119.64 | 141.39 | 113.11 |

### Verdict against the measured 82.6 MB/s

Sustained = demand below card speed, recording runs until the card fills. Percentages are duty
cycle (demand ÷ card). Bursts use B = 128 MB, the *smallest* observed buffer.

| Mode | Uncompressed | 14-bit lossless @60% | Worst case @65% | 12-bit @52% |
|---|---|---|---|---|
| **1080p23.976** | burst **29.0 s** | ✅ **sustained** (63% duty) | ✅ sustained (68%) | ✅ sustained (55%) |
| **1080p25** | burst **15.8 s** | ✅ **sustained** (66% duty) | ✅ sustained (71%) | ✅ sustained (57%) |
| **1080p29.97** | burst **4.9 s** | ✅ **sustained** (79% duty) | ✅ sustained (86%) | ✅ sustained (68%) |
| **1080p59.94** | burst **0.95 s** | ⛔ burst **2.7 s** | ⛔ burst 2.2 s | ⛔ burst 4.2 s |

### What changed versus spike 008 §4

| Claim in spike 008 | Now |
|---|---|
| "~60–90 MB/s is an assumption" | **CONFIRMED at 82.6 MB/s.** Assumption was correct and slightly pessimistic on average. |
| 1080p24 "sustained, clears even a pessimistic 60 MB/s card" | **Holds, with far more margin than claimed** — 52.2 vs 82.6 is a 37% headroom, not a squeak. |
| 1080p25 "sustained, the headline win" | **Holds.** 54.4 vs 82.6. |
| 1080p30 "marginal → sustained at 12-bit; 65 MB/s needs a ≥70 MB/s card" | **UPGRADED. Sustained at 14-bit.** 65.3 vs 82.6 = 79% duty; even the noisy-scene 70.7 fits at 86%. 12-bit is now a safety margin, not a requirement. |
| 1080p50/60 "exceeds the UHS-I bus ceiling outright — no card fixes this" | **Holds.** 130.5 MB/s vs 82.6 measured and ≤104 MB/s bus. |
| 60p burst "0.98 s today → 2.7 s with lossless" (assumed 80 MB/s, 135 MB buffer) | **Confirmed to two digits.** Measured 0.95 s observed → 2.7 s predicted at 82.6 MB/s, 128 MB. |

### The one genuinely new finding

**1080p23.976 uncompressed is only 4.4 MB/s short of sustained.** At 87.0 vs 82.6 the buffer
drains slowly enough to give a **~29-second** take today, with no compression work at all — not
the ~1-second burst the project has been describing. 1080p25 uncompressed gives ~16 s
(confirmed: M15-1924 ran 15.72 s). The "1 second" figure is specific to 59.94p.

This does not reduce the value of lossless — 29 s is not sustained, and 30p/60p still need it —
but it changes what to demo and what to tell users before the LJ92 work lands. It also means a
modest bitrate reduction, not the full 40% LJ92 gives, is enough to make 24p sustained:
**anything above a 95% compression ratio (i.e. ≥5% saving) tips 23.976p over the line.**

### Bus headroom

Measured write 82.6 and read 95.7 MB/s against spike 006's ≤104 MB/s UHS-I ceiling. Read is at
92% of the ceiling; write is at 79%. **The bus is not the write limiter — the card's own NAND
program rate is.** A faster card could plausibly reach ~100 MB/s write and push 30p @65%
(70.7) to a comfortable 71% duty, but it cannot approach the 130.5 MB/s that 60p lossless
needs. Spike 008's conclusion that no card fixes 60p stands.

---

## Appendix — reproduction

No ImageMagick or PIL on this machine; the BMPs were decoded with a stdlib-only script.

```bash
cd "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2"

# BMP geometry (720x480, 24bpp, top-down)
python3 -c "import struct;d=open('tools/bench/bench0.bmp','rb').read();\
print(struct.unpack_from('<iiHH',d,18))"

# colour census - 3 colours only, so no palette remapping was needed
# (#005200 bg, #000000 text box, #EBEBEB text)

# frame size and frame count, parsed from MLV block streams
python3 - <<'EOF'
import struct,os,glob
from collections import Counter
for p in sorted(glob.glob('footage/*.MLV')+glob.glob('footage/session5/*.MLV')):
    f=open(p,'rb'); sz=os.path.getsize(p); off=0; c=Counter(); v=Counter(); fps=None
    while off<sz:
        f.seek(off); h=f.read(16)
        if len(h)<16: break
        t=h[0:4]; n=struct.unpack_from('<I',h,4)[0]
        if n<16 or off+n>sz: break
        c[t]+=1
        if t==b'VIDF': v[n]+=1
        if t==b'MLVI':
            b=h+f.read(n-16); a,d=struct.unpack_from('<II',b,44); fps=a/d
        off+=n
    print(os.path.basename(p), c[b'VIDF'],'fr', round(fps,3),'fps', dict(v))
EOF
```

Source references for the unit and buffer-size claims:

- [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/modules/bench/card_bench.c](ml/modules/bench/card_bench.c) `:45` (decimal MB/s), `:136-146` (buffer sizes), `:130-135` (card model print)
- [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/modules/bench/mem_bench.c](ml/modules/bench/mem_bench.c) `:170-175` (MiB/s), `:21-42` (OK/ERR! check)
- [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/modules/bench/mem_perf.c](ml/modules/bench/mem_perf.c) `:110-170` (cache sweep, Now/Peak/Drop)
- [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/modules/raw_video/mlv_lite/mlv_lite.c](ml/modules/raw_video/mlv_lite/mlv_lite.c) `:1495` (32 MB write-group cap), `:3337` (the write call)
