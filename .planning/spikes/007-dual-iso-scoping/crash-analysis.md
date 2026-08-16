# Session 5 crash analysis — `ASSERT: m_VSize` @ ImgSeqCoopStore.c:194

**Date:** 2026-08-15 · **Build:** `2026-08-15.6D2.111`, git `3f24042a4` dev, built 2026-08-16 02:39:10 UTC
**Inputs:** `tools/CRASH00-session5.txt`, `tools/RAWDIAG-session5.txt`, `footage/session5/`, `tools/bench/`, `roms/6D2/ROM0.BIN`
**Method:** ROM disassembly + BL-target scan, MLV/CR2 content parsing, source trace. No inference where a measurement was available.

---

## TL;DR

**The crash is ours, not Canon's, and it has nothing to do with dual-ISO.**

`shoot_task` is a Magic Lantern task (`ml/src/shoot.c:6203`); the string does not exist anywhere in
ROM0. The function that asserted — ROM `0xE04471DE` — is stubbed in our own tree as
`_get_fps_register_b` (`ml/platform/6D2.111/stubs.S:279`). It is Canon's
`ImgSeqCoopStore::GetVSize()`, and on the 6D2 it is **ML's only way to read FPS timer B**.

We called it while Canon's image-sequence store still held `m_VSize == 0` — i.e. during a
LiveView reconfiguration, before the timing generator had published a frame height. The assert
is a null-check, not a range check: nothing was mis-configured, we simply read a field too early.

The occasion was the movie → stills-with-LiveView switch that the dual-ISO test required
(`lv:1 mode:0`, and RAWDIAG's `raw inactive: lv=1 movie=0 gui=0` records that exact transition).
Dual-ISO was the *reason the user was in that state*, not the mechanism.

**Verdict: benign, caught, and safe to repeat.** The bug is a missing guard in ML.

---

## 1. ROM findings

### 1.1 The asserting function — byte-exact

Disassembly of ROM0 at file offset `0x4471C8` (`--adjust-vma=0xE0447000`, `-m armv7 -M force-thumb`):

```
; ImgSeqCoopStore::SetVSize(int)
e04471c8:  b510        push  {r4, lr}
e04471ca:  0004        movs  r4, r0                    ; sets Z if arg == 0
e04471cc:  d104        bne.n 0xe04471d8
e04471ce:  22bc        movs  r2, #188      @ 0xbc      ; line 188
e04471d0:  a1c7        add   r1, pc, #796  @ 0xe04474f0 ; "./ImgSeqCoop/ImgSeqCoopStore.c"
e04471d2:  a0ec        add   r0, pc, #944  @ 0xe0447584 ; "VSize"
e04471d4:  f1d0 fa24   bl    0xe0617620                ; debug_assert()
e04471d8:  48d7        ldr   r0, [pc, #860] @ 0xe0447538
e04471da:  61c4        str   r4, [r0, #28]             ; store->m_VSize = arg
e04471dc:  bd10        pop   {r4, pc}

; ImgSeqCoopStore::GetVSize(void)   <-- ML stub `_get_fps_register_b`
e04471de:  b510        push  {r4, lr}
e04471e0:  4cd5        ldr   r4, [pc, #852] @ 0xe0447538
e04471e2:  69e0        ldr   r0, [r4, #28]             ; r0 = store->m_VSize
e04471e4:  b920        cbnz  r0, 0xe04471f0            ; non-zero -> skip assert
e04471e6:  22c2        movs  r2, #194      @ 0xc2      ; line 194
e04471e8:  a1c1        add   r1, pc, #772  @ 0xe04474f0 ; "./ImgSeqCoop/ImgSeqCoopStore.c"
e04471ea:  a0e8        add   r0, pc, #928  @ 0xe044758c ; "m_VSize"
e04471ec:  f1d0 fa18   bl    0xe0617620                ; debug_assert()
e04471f0:  69e0        ldr   r0, [r4, #28]             ; <-- LR == 0xE04471F1 (Thumb)
e04471f2:  bd10        pop   {r4, pc}
```

Every field of the crash log is reproduced exactly:

| Crash log field | ROM evidence |
|---|---|
| `m_VSize` | string at `0xE044758C` (file offset `0x44758C`), loaded into `r0` at `e04471ea` |
| `./ImgSeqCoop/ImgSeqCoopStore.c` | string at `0xE04474F0`, loaded into `r1` at `e04471e8` |
| `:194` | `movs r2, #194` at `e04471e6` |
| `:e04471f1` | ML captures `read_lr()` in `my_assert_handler` (`ml/src/init.c:558`); the return address after the `bl` at `e04471ec` is `0xE04471F0`, `|1` for Thumb → **`0xE04471F1`** |

`0xE0617620` is `debug_assert()`. It loads the handler pointer from a RAM slot and tail-calls it
(`ldr r3,[r0,#0]; cbz r3; bx r3` at `e0617632`–`e061763c`) — that slot is
`DRYOS_ASSERT_HANDLER 0x4000` in `ml/platform/6D2.111/consts.h:11`, which ML overwrites at
`ml/src/init.c:669`. This is why the assert produced a log instead of a silent ERR70.

### 1.2 What `m_VSize` is, and why zero is the failure

`ImgSeqCoopStore.c` is a plain singleton property bag — "image sequence cooperation" state shared
between the capture and LiveView sequencers. Its instance lives at **RAM `0x0001C928`** (literal at
`0xE0447538`); `m_VSize` is the word at **`0x0001C944`** (`+0x1C`). Neighbouring fields, read off the
same disassembly, show the uniform shape:

| Offset | Field | Setter asserts (line) | Getter asserts (line) |
|---|---|---|---|
| `+0x14` | `SensorMode` | `< IMGSEQCOOP_SENSOR_MODE_MAX` (165) | same (170) |
| `+0x18` | `pMemoryData` | non-NULL (176) | non-NULL (182) |
| **`+0x1C`** | **`VSize`** | **non-zero (188)** | **non-zero (194)** |
| `+0x24/+0x28` | `PSaveTiming`, `ResetPSaveTiming` | non-zero (211/212) | non-zero (219/220) |
| `+0x2C` | `ShutterSpeed` | non-zero (227) | non-zero (232) |
| `+0x30` | `AfShutterSpeed` | — | non-zero (252) |

So the assert means **"nobody has called `SetVSize()` yet"** — the field is at its BSS zero. It does
*not* mean a size was out of range, and it carries no information about sensor geometry being wrong.
This is the single most important correction to the working hypothesis: a vertical-size *mismatch*
was never in evidence.

### 1.3 Who sets it — the timing generator

A full BL-target scan of ROM0 (Thumb-2 BL decode over all 32 MiB) gives every caller:

```
SetVSize (0xE04471C8) callers:
  0xE0301690 E03016BE E0301716 E0301752 E03017A0 E0301840 E0301BA4 E0301BEA
  0xE0301E56 E0301EAE E0302302 E030235A E0302510 E0302560 E03025A8 E03025BE
  0xE03025E6 E03025FC          -> inside ./ImgSeqCoop/ImgSeqCoopCap.c  (file string 0xE0303060)
  0xE0514382 E05143E6          -> inside ./Device/TG/TGdriver.c        (file string 0xE051403C)

GetVSize (0xE04471DE) callers:
  0xE03029C8 E0302A40 E0303032 E0303140 E03034F0 E03036D4 E0303766 E0303828
  0xE030388A E0303D16 E0303E68 -> ./ImgSeqCoop/ImgSeqCoopCap.c
  0xE052465C E05246A6 E0524F8A E052515E E052542A E0525BE6 E0525FBC
                                -> ./ImgSeqCoop/ImgSeqCoopLv.c         (file string 0xE05247B4)
```

`VSize` is published by **`Device/TG/TGdriver.c`** — the sensor timing generator — and consumed by
the capture and LiveView sequencers. That is precisely the semantics ML already documents:

> `ml/src/fps-engio.c:62` — *"FPS_REGISTER_B is known as VSize. Sometimes this is the actual row
> count, but not always."*

So `VSize` = the TG's frame height in lines, i.e. FPS timer B. It exists only while a timing mode is
programmed. Between modes it is zero.

**Canon never trips this assert on its own**: every Canon caller of `GetVSize` sits inside the
Cap/Lv sequencers, which run after the TG has published the value.

---

## 2. The ML call chain

### 2.1 `shoot_task` is ours

```
$ grep -a -c "shoot_task" roms/6D2/ROM0.BIN
0
```

Zero occurrences in the firmware. Canon's equivalent is `ShootCapture` (`0xE053C680`,
`0xE0F7F2A8`). `shoot_task` is created at `ml/src/shoot.c:6203`:

```c
TASK_CREATE( "shoot_task", shoot_task, 0, 0x1a, 0x2000 );
```

`get_current_task_name()` is read live at assert time, so the attribution is exact. **ML code called
Canon's getter.**

### 2.2 The only route from `shoot_task` to `GetVSize` on this body

```
ml/platform/6D2.111/stubs.S:279     THUMB_FN(0xe04471de, _get_fps_register_b)
ml/platform/6D2.111/fps-engio_per_cam.c:29-33
        int get_fps_register_b(void) { return _get_fps_register_b(); }
```

Call sites of `get_fps_register_b()` are all in `ml/src/fps-engio.c`. Eliminating them:

- lines 817–818 — inside a commented-out `fps_was_changed_by_canon()`. Dead.
- lines 1716–1717, 1747, 1771, 1775 — `fps_read_current_timer_values()` /
  `fps_read_default_timer_values()` / override apply, all driven from **`fps_task`**
  (`fps-engio.c:1986`). Wrong task name.
- line 580 — `get_current_shutter_reciprocal_x1000()`, guarded by `#ifdef FRAME_SHUTTER_BLANKING_READ`.
  **The 6D2 defines neither `FRAME_SHUTTER_BLANKING_READ` nor `FRAME_SHUTTER_TIMER`** (verified: no
  hits in `ml/platform/6D2.111/*.h`), so this function falls through to the APEX-units branch and
  never touches the register. Eliminated.
- **line 916 — `fps_get_current_x1000()`. The only survivor.**

```c
int fps_get_current_x1000()          // ml/src/fps-engio.c:912
{
    if (!lv)                          // <-- the ONLY guard
        return 0;
    int fps_timer = (get_fps_register_b() & 0xFFFF) + 1;
    ...
}
```

Its guard is `lv`. The crash log says `lv:1`. The guard passed.

### 2.3 The immediate caller (high confidence, not proven)

The 6D2 ships four modules only (`ml/platform/6D2.111/modules.included`: `bench`, `dual_iso`,
`file_man`, `mlv_lite`), so the `CBR_SHOOT_TASK` set is small. Of the direct callers of
`fps_get_current_x1000()` in that build, all but one are eliminated:

| Call site | Why it is not this crash |
|---|---|
| `ml/src/shoot.c:1710` | `MENU_UPDATE_FUNC(shutter_display)` — menu task, and gated on `is_movie_mode()` (false) |
| `ml/src/lens.c:2957` | `LVINFO_UPDATE_FUNC(fps_update)` — gated on `is_movie_mode()` (false) |
| `ml/src/state-object.c:54,62` | Canon state-object hooks — different task |
| `mlv_lite.c:869,920,1293` | `update_status()` (recording only) and menu update funcs |
| **`ml/src/raw.c:1234`** | **survives** |

`raw.c:1234` sits inside `raw_update_params_work()` (`raw.c:871`), on this branch:

```c
if (lv)
{
    if (width != raw_info.width || height != raw_info.height)
    {
        /* raw dimensions changed in LiveView? ... */
        int fps = fps_get_current_x1000();      // <-- raw.c:1234
```

It is reached **only when the LiveView raw geometry has just changed** — which is exactly the moment
the TG is being reprogrammed and `m_VSize` is transiently zero. The shoot-task path into it:

```
shoot_task                                   ml/src/shoot.c:6203
 └ module_exec_cbr(CBR_SHOOT_TASK)           ml/src/shoot.c:5497
    └ raw_rec_polling_cbr()  REQUIRES(ShootTask)
                                             mlv_lite.c:2067  (registered at :4693)
       └ raw_lv_request_update()             mlv_lite.c:2071 → :1829
          └ raw_video_enable() → raw_lv_request()
                                             mlv_lite.c / ml/src/raw.c:2579
             └ raw_lv_update()               ml/src/raw.c:2527 (called at :2594)
                └ raw_update_params_work()   ml/src/raw.c:2536 → :871
                   └ fps_get_current_x1000() ml/src/raw.c:1234
                      └ get_fps_register_b() ml/src/fps-engio.c:916
                         └ _get_fps_register_b()  → ROM 0xE04471DE
                            └ ASSERT(m_VSize)     ImgSeqCoopStore.c:194
```

`raw_lv_update()` loops `raw_update_params_work()` up to 5 times with `wait_lv_frames(1)` between
attempts — tens to a couple hundred milliseconds of blocking. That window comfortably straddles the
mode change, which is how `is_movie_mode()` can have been true on entry while `shooting_mode` reads
`0` (`SHOOTMODE_P`, `ml/src/property.h:233`) by the time the assert fires.

> **Confidence:** the leaf (`_get_fps_register_b` → `GetVSize`), the task, and the elimination down to
> `fps_get_current_x1000()` are *certain* — each is a byte match or an exhaustive source search.
> The specific caller `raw.c:1234` is *likely*: it is the only survivor of the elimination and its
> trigger condition (LiveView geometry change) matches the recorded state transition, but ML's
> backtrace is disabled on DIGIC 6/7/8 (`ml/src/init.c:576-580`, `backtrace_getstr` is `#else`-only),
> so there is no stack to confirm it.

---

## 3. Session correlation

### 3.1 Timeline, reconstructed from file *content* (never mtime)

MLV names encode capture time (`mlv_lite.c:3077`: `"M%02d-%02d%02d.MLV"` = day, hour, minute, with the
minute bumped on collision), and each file carries an `RTCI` block with the real clock. CR2s carry
EXIF `DateTimeOriginal`.

| Camera clock | Artifact | Evidence | Test |
|---|---|---|---|
| 21:02:45 | `M15-2102.MLV` 206,857,216 B | RTCI | **Double-REC take 1** |
| 21:02:50 | `M15-2103.MLV` 206,857,216 B | RTCI (+5 s, name bumped to `2103`) | **Double-REC take 2 — PASS** |
| 21:03:00 | `M15-2104.MLV` 228,631,552 B | RTCI | extra take |
| 21:03:45 | `M15-2105.MLV` 232,260,608 B | RTCI, **`WBAL` mode = 1** (all others 0) | **Custom-WB discriminator** |
| ~21:04:03 | — | RAWDIAG boot A `[137.538] raw inactive: lv=0 movie=0 gui=0` | left movie mode |
| — | *power cycle* | RAWDIAG timestamps restart | dual_iso module enable → "restart camera" |
| 21:05:57 | `M15-2106.MLV` 206,857,216 B | RTCI, **`DISO` block present** | dual_iso now loaded |
| ~21:06:15–21 | — | RAWDIAG boot B `[44.598] raw inactive: lv=1 movie=0 gui=0` | **movie → stills, LiveView still up** |
| 21:06:34 | `_MG_2214.CR2` ISO 12800 1/15 | EXIF | stills setup |
| 21:06:46 | `_MG_2215.CR2` ISO 12800 1/20 | EXIF | stills setup |
| 21:08:02 | `_MG_2216.CR2` ISO 100 1/100 | EXIF | no stripes |
| 21:08:30 | `_MG_2217.CR2` ISO 100 1/100 | EXIF | no stripes |
| 21:09:36 | `_MG_2218.CR2` ISO 100 1/100 | EXIF | **dual-ISO fired** |

Boot A maps 1:1 onto the first four MLVs, by inter-probe spacing alone:

```
RAWDIAG boot A probes : 59.511  64.194  75.196  119.865   (Δ = 4.68, 11.00, 44.67 s)
MLV RTCI              : 21:02:45 21:02:50 21:03:00 21:03:45 (Δ = 5, 10, 45 s, 1 s resolution)
```

That fixes ML boot A at ≈ 21:01:45 wall clock. `[2.013]` in both boots is the startup probe.

### 3.2 Dual-ISO did fire — on exactly one frame

Each CR2 embeds a **full-resolution 6240×4160 JPEG preview** (IFD0 `StripOffsets`/`StripByteCounts`).
Dual-ISO alternates the analog gain every 2 sensor rows, giving a **period-4 row modulation**.
Fourier power of the de-trended row means (central 512-px band, 9-row moving average removed):

| File | row-dev RMS | P(2 rows) | **P(4 rows)** | P(8 rows) | P4/RMS |
|---|---|---|---|---|---|
| `_MG_2214.CR2` | 0.124 | 0.002 | 0.004 | 0.014 | 0.03 |
| `_MG_2215.CR2` | 0.224 | 0.002 | 0.001 | 0.021 | 0.01 |
| `_MG_2216.CR2` | 0.024 | 0.000 | 0.000 | 0.001 | 0.00 |
| `_MG_2217.CR2` | 0.027 | 0.001 | 0.002 | 0.005 | 0.09 |
| **`_MG_2218.CR2`** | **8.597** | 0.238 | **5.750** | 0.003 | **0.67** |

`_MG_2218` shows a 5.75-grey-level period-4 modulation carrying 67 % of its row variance, with
period-2 and period-8 near zero. That is an unambiguous dual-ISO signature and it is absent from
every other frame. Corroboration: its preview JPEG is 1,960,800 B against 705,660 / 734,666 B for
`_MG_2216` / `_MG_2217` at the *same* ISO 100 and *same* 1/100 shutter — the stripes are what inflate it.

**Stills dual-ISO works on this body.** Spike 007's claim is now hardware-confirmed.

The `DISO` block in `M15-2106.MLV` (offset `0x2DC`, 24 bytes) reads:

```
44 49 53 4f 18 00 00 00 | a1 90 48 01 00 00 00 00 | 00 00 00 00 | 03 00 00 00
   "DISO"     size=0x18       timestamp                dualMode=0    isoValue=3
```

`dualMode = dual_iso_is_active() = 0` — expected, because `FRAME_CMOS_ISO_START` is `0` on the 6D2,
so movie-mode dual-ISO is inert by construction (spike 007 §1). `isoValue = dual_iso_alternate_iso = 3`
→ `iso1 = 72 + 3*8 = 96` → **ISO 800**, exactly the 100/800 pairing the test plan asked for. The
companion `VERS` block confirms the module was loaded: `dual_iso built 2026-08-15 18:50:44 UTC`.

### 3.3 Which test caused it — and which did not

**Not dual-ISO.** `dual_iso.c` contains **zero** references to `fps_get_current_x1000`,
`get_current_shutter_reciprocal_x1000` or `get_fps_register_*` (grep returns nothing). Its two
shoot-task CBRs (`dual_iso_refresh`, `dual_iso_playback_fix`, `dual_iso.c:1638-1639`) cannot reach
the asserting function by any path. Its writes go to a DMA'd **RAM** copy of the CMOS gain table via
`apply_patches()` (`dual_iso.c:387-397`) and cannot zero a field in `ImgSeqCoopStore` at `0x1C944`.

**Not the benchmark.** `bench` runs from PLAY/menu — both benchmark screens are stamped
`Mode: PLAY-UNK LCD`. The crash has `lv:1`.

**Not movie-mode raw video.** `mode:0` is `SHOOTMODE_P`, not `SHOOTMODE_MOVIE`; RAWDIAG's own
`movie=0` at the matching moment agrees.

**It was the movie → stills transition that the dual-ISO test required.** RAWDIAG boot B
`[44.598] raw inactive: lv=1 movie=0 gui=0` is mlv_lite's shoot-task CBR observing exactly the
crash state — LiveView alive, movie mode gone — one tick after the collar switch, ~13–19 s before the
first still at 21:06:34. Same task, same instant, same condition.

Dual-ISO is the *occasion*, not the *mechanism*.

---

## 4. Severity verdict

**Benign. Repeat the test.**

1. **ML caught it and the camera kept running.** `my_assert_handler` (`init.c:554`) formatted the
   message, called `request_crash_log(1)`, then chained to Canon's original handler. Five stills and
   the whole benchmark suite were produced after the transition; the owner reports no freeze and no
   battery pull. Contrast session 1, which needed one.
2. **`CRASH00.LOG` means it happened once.** `save_crash_log()` (`debug.c:548-555`) scans
   `CRASH00…CRASH99` for the first free/zero-length slot, so `00` is the only crash log on the card.
3. **Nothing was written anywhere persistent.** The assert is a *read* of a Canon RAM field. It
   changed no state at all.
4. **Dual-ISO's writes are transient and validated.** `patch_cmos_iso_values_6d2()` targets the
   heap copy of the CMOS table (`dual_iso.c:332`), rejects any word failing
   `(val & 0xffff0000) == 0x0d030000`, and only accepts gain nibbles `0x00`–`0x70`. Nothing touches
   ROM, FROM or the bootflag. `_MG_2218.CR2` is the proof it did the right thing.
5. **The failure is a missing guard on our side, and it is one line.** No sensor risk, no register
   risk.

### Sibling bug, same shape — flag it now

`ml/platform/6D2.111/stubs.S:278` maps `_get_fps_register_a` to **`0xE044726A`**, which the same
disassembly shows to be `ImgSeqCoopStore::GetShutterSpeed()`:

```
e044726a: push {r4,lr}
e044726c: ldr  r4, [pc,#712]  @ 0xe0447538
e044726e: ldr  r0, [r4,#44]   @ 0x2c        ; store->m_ShutterSpeed
e0447270: cbnz r0, 0xe044727c
e0447272: movs r2, #232       @ 0xe8        ; line 232
e0447276: adr  r0, 0xe04475e8               ; "m_ShutterSpeed"
e0447278: bl   0xe0617620
```

Identical failure mode. Expect `ASSERT: m_ShutterSpeed at ./ImgSeqCoop/ImgSeqCoopStore.c:232` from
`fps_task` under the same race — `fps_read_current_timer_values()` (`fps-engio.c:1716`) reads *both*
registers behind the same bare `if (!lv)`.

### Suggested fix (not applied — read-only spike)

`lv` is a cached property and stays `1` across a LiveView reconfiguration, so it is the wrong guard.
The lazy fix is one place, in `fps-engio_per_cam.c`, covering every caller at once: read the store
field directly instead of through the getter, and return `0` when it is zero.

```c
/* ml/platform/6D2.111/fps-engio_per_cam.c */
/* ImgSeqCoopStore singleton; m_VSize +0x1C, m_ShutterSpeed +0x2C.
 * Canon's getters ASSERT when the field is 0, which happens whenever the TG
 * is mid-reconfiguration (mode switches). Read the field, skip the assert. */
#define IMGSEQCOOP_STORE 0x1C928       /* literal at ROM 0xE0447538 */

int get_fps_register_b(void) { return MEM(IMGSEQCOOP_STORE + 0x1C); }
int get_fps_register_a(void) { return MEM(IMGSEQCOOP_STORE + 0x2C); }
```

Callers already handle `0`: `fps_get_current_x1000()` returns a timer of `1`, and both
`raw.c:1235` and `lens.c:2957` explicitly test `if (fps == 0)`. Verify the two offsets against a
live `_get_fps_register_*` return before trusting the address; keeping the stubs as a cross-check in
a debug build would settle it in one session.

> `ponytail:` reads the singleton by hardcoded address rather than calling Canon. Upgrade path if
> the address proves unstable across boots: keep the stub call but wrap it in a
> `is_lv_reconfiguring()` gate — more code, needs a state hook we do not have yet.

---

## 5. Diag-log reading

Full contents of `tools/RAWDIAG-session5.txt` (11 lines, two boots — timestamps restart at line 7):

```
boot A  [  2.013] [probe] max 135MB steps 34 slowest 101ms@136MB last TIMEOUT
        [ 59.511] [probe] max 135MB steps 34 slowest  91ms@136MB last TIMEOUT
        [ 64.194] [probe] max 135MB steps 34 slowest 102ms@136MB last TIMEOUT
        [ 75.196] [probe] max 135MB steps 34 slowest 100ms@136MB last TIMEOUT
        [119.865] [probe] max 135MB steps 34 slowest  92ms@136MB last TIMEOUT
        [137.538] raw inactive: lv=0 movie=0 gui=0
boot B  [  1.912] [probe] max 135MB steps 34 slowest 104ms@136MB last TIMEOUT
        [ 13.153] raw inactive: lv=0 movie=0 gui=9
        [ 20.300] [probe] max 135MB steps 34 slowest  99ms@136MB last TIMEOUT
        [ 25.970] [probe] max 135MB steps 34 slowest 100ms@136MB last TIMEOUT
        [ 44.598] raw inactive: lv=1 movie=0 gui=0
```

### 5.1 `[probe]` — the memory pool is rock stable

`shoot_malloc_autodetect()` (`ml/src/exmem.c:234-289`) allocates a 4 MB backup, then probes
**linearly from 4 MB in 4 MB steps** until an allocation fails.

- **34 steps** → the last attempt was `4 + 33*4 = 136 MB`, and it failed.
- **`last TIMEOUT`** is `probe_last_ok == 0`, i.e. the loop's normal terminator. It is **not an
  error** — every successful autodetect ends this way. The 91–104 ms "slowest" is always the failing
  136 MB attempt, i.e. the allocator's own timeout.
- **`max 135MB`** = last success (132 MB) + backup (4 MB) − 1 MB safety margin (`exmem.c:271`).

All eight probes across both boots return **identical** figures, and they are identical to sessions 1
and 2 (`135MB / 34 steps / 93–100 ms`). The **135 MB baseline is confirmed stable across a full
session including five raw takes, a power cycle, dual-ISO stills and a benchmark run.**

Specifically: spike 006's third open bug — the *92 MB shoot-pool shrink between alloc cycles* — **did
not reproduce**. Boot A probed the pool four times over 118 seconds of recording with zero decay.

### 5.2 `gui=9` — the Q / quick-control screen

`GUISTATE_QMENU 9` (`ml/src/gui-common.h:223`). The 6D2 uses the DryOS block (`#else` branch, the
`CONFIG_5DC` block does not apply), where the annotated map is:

```
0 IDLE   1 PLAYMENU   2 MENUDISP   3 QR   ...   9 QMENU ("unavi?")   12 QR_ZOOM
```

`[13.153] raw inactive: lv=0 movie=0 gui=9` therefore reads: 13 s after the boot-B restart, with
LiveView off and out of movie mode, the user was on the **Q / quick-control screen** — consistent
with setting up Dual ISO / ISO before going back to LiveView. `raw inactive` fires from
`raw_rec_polling_cbr` (`mlv_lite.c:2107`) when raw video is no longer active and any allocated suite
is being freed — a clean teardown, exactly what it is meant to log.

The last line, `[44.598] raw inactive: lv=1 movie=0 gui=0`, is the important one: **LiveView on,
movie mode off, idle GUI** — the crash state, recorded by our own instrumentation.

### 5.3 Zero `No memory suites.` — the re-arm fix works

`diag_log("No memory suites. ...")` fires at up to 1 Hz from `setup_buffers()` (`mlv_lite.c:1610`)
whenever both `shoot_mem_suite` and `srm_mem_suite` are NULL. Session 1 recorded **7 consecutive
seconds** of it with `rawact=1 rec=0 → rec=1`, ending in the hard freeze that needed a battery pull.

**Session 5: not one line, across both boots.** Combined with `M15-2102` → `M15-2103` five seconds
apart and byte-identical in size (206,857,216 B each — the same buffer-full stop), this is the
**double-REC re-arm fix confirmed on hardware**. The patch is `mlv_lite.c:2117-2124`:

```c
/* Both suites NULL while raw video active and idle -> realloc. */
if (!shoot_mem_suite && !srm_mem_suite && raw_video_active && RAW_IS_IDLE)
    realloc = 1;
```

The dead state it was written for no longer occurs.

### 5.4 Card and memory benchmarks (`tools/bench/`)

Screens are 720×480 24-bpp BMPs, all stamped `ML 2026-08-15.6D2.111, 3f24042a4 dev` /
`Mode: PLAY-UNK LCD, Global Draw: ON`.

`bench0.bmp` — card:

| Buffer | Write | Read |
|---|---|---|
| 16384k | **82.9 / 82.6 MB/s** | **95.6 / 95.7 MB/s** |
| 15625k | 81.4 MB/s | 95.4 MB/s |
| 4096k | 71.8 MB/s | 89.1 MB/s |
| 3906k | 67.8 MB/s | 88.3 MB/s |
| 2048k | 65.3 MB/s | 84.2 MB/s |
| 1953k | 42.2 MB/s | 82.0 MB/s |
| 128k | 15.1 MB/s | 33.4 MB/s |

**The 60–90 MB/s assumption underpinning the compression math is confirmed: ~83 MB/s write at large
buffers.** Note the sharp cliff below 2 MB — buffer size matters more than the card does.

`bench1.bmp` — memory (display on / off): `memcpy` cacheable 97.9/99.1, uncacheable 15.6/15.8;
`memcpy64` cacheable 108.4/109.8; `dma_memcpy` **uncacheable 126.7/126.9** (faster than cacheable
50.5 — DMA prefers uncacheable); `memset` uncacheable 494/504 MB/s; `read32` cacheable 147/151 vs
uncacheable 21.9/22.2. Display state is worth ~1–3 %, i.e. nothing.

`cache0.bmp` — cache benchmark from `0x100000`: peak 6291 MiB/s @ 2048 B, drop-off at 16384 B
(6234 MiB/s), 525 MiB/s at 22784 B.

---

## 6. What could not be established

- **The exact immediate caller of `fps_get_current_x1000()`.** `raw.c:1234` is the only survivor of
  an exhaustive elimination and its trigger condition matches, but `backtrace_getstr` is compiled out
  on DIGIC 6/7/8 (`ml/src/init.c:576-580`) so there is no stack. To settle it, add a
  `diag_log("fps_reg_b read: lv=%d movie=%d gui=%d\n", ...)` immediately before the
  `_get_fps_register_b()` call in `fps-engio_per_cam.c` and repeat the movie→stills switch.
- **Whether `m_VSize` was zero because the store was never populated in boot B, or because the TG
  cleared it during the mode change.** Distinguishing these needs a runtime read of `0x1C944`
  across the transition. It does not change the fix.
- **Boot B has three `[probe]` lines but only one MLV** (`1.912` startup, then `20.300` and
  `25.970`). Boot A's probes map 1:1 to its four MLVs, so one boot-B allocation cycle produced no
  file. Most likely an arm that was cancelled before recording, but only five MLVs were recovered and
  the card is unmounted — not verifiable from here.
- **Why `_MG_2214`/`_MG_2215` are ISO 12800.** They predate the striped frame and show no dual-ISO
  signature; presumably scene/exposure setup. Not load-bearing.

---

## 7. Actions

1. **Fix the guard** in `ml/platform/6D2.111/fps-engio_per_cam.c` (§4). Covers `GetVSize` and
   `GetShutterSpeed`, every caller, one file. Verify the two offsets against the stub returns first.
2. **Repeat the dual-ISO test as written — it is safe.** Add: run `cr2hdr` on `_MG_2218.CR2` to close
   spike 007 Phase 0, then delete `dual_iso` from `ml/platform/6D2.111/modules.hidden`.
3. **Close two spike-006 bugs as fixed on hardware:** the post-record dead state (§5.3) and the
   92 MB shoot-pool shrink (§5.1).
4. **Record the ROM findings in the stub table** — `_get_fps_register_a/b` are
   `ImgSeqCoopStore::GetShutterSpeed` / `GetVSize` at `+0x2C` / `+0x1C` of the singleton at
   `0x1C928`, and they assert when unset. That comment belongs next to `stubs.S:278-279` so the next
   person does not re-derive it.

---

## ADVERSARIAL VERIFICATION VERDICT (same session): DIAGNOSIS PARTLY REFUTED — DO NOT APPLY THE PROPOSED FIX

An independent verifier re-derived every claim. Results:

**SURVIVES (byte-verified):** the asserting function IS at `0xE04471DE` — bytes at
ROM0 offset 0x4471DE decode to `PUSH{r4,lr}; LDR r4,[pc,#0x354]; LDR r0,[r4,#28];
CBNZ r0,0xE04471F0; MOVS r2,#194; ADR r1,<"./ImgSeqCoop/ImgSeqCoopStore.c">; ...`
— i.e. it asserts a zero field at struct+0x1C and the `#194` matches the log's
line number. It is also genuinely the function ML's own FPS-register stub calls.

**REFUTED — the immediate caller.** The claim that `raw.c:1234` triggered it does
not hold. `wait_lv_frames()` (src/state-object.c:50-62) is itself a direct caller
of `fps_get_current_x1000()`, and in `raw_lv_update()`'s enable branch
`raw_lv_enable()` → `wait_lv_frames(2)` runs FIRST and unconditionally
(raw.c:2453-2456), before raw.c:1234 is reachable. Worse for the stated story:
with `mode:0` (photo), `is_movie_mode()` is false, so mlv_lite.c:1829-1848 takes
the DISABLE branch, which reads no FPS register at all. The only surviving path
is `raw_lv_release()` decrementing the request count while another subsystem still
holds a request. **The caller is UNPROVEN.** Best candidate is raw.c:2456.

**Also corrected:** `fps_get_current_x1000()` touches BOTH asserting registers
(B at 0xE04471DE then A at 0xE044726A) on essentially every call, not just B.

**CONSEQUENCE — the recommended one-line guard in `fps-engio_per_cam.c` must NOT
be applied**: it was justified by the refuted call-site attribution, and would
paper over a condition we have not localised. Backtrace is compiled out on D678
(init.c:576-580), so the way to settle it is a `diag_log` probe INSIDE
`fps_get_current_x1000()` logging `get_current_task_name()` and the return
address — a probe in fps-engio_per_cam.c alone cannot distinguish the three call
sites.

**Unchanged:** the assert is benign (caught and logged, recording unaffected,
dual_iso writes only transient per-frame registers) and the test is safe to repeat.
