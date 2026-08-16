# GUI-stage gap analysis — what MPU data QEMU still lacks, and do we already have it

Read-only investigation. Nothing in `qemu-eos/`, `ml/` or `6D2.h` was modified.

Fresh stock boot trace produced for this analysis (120 s, existing qemu binary, no rebuild):
`.planning/spikes/005-mpu-spell-capture/gui-stage-stock-boot-trace.log` (465 lines — the run
produced **zero** output after line 464; the remaining ~119 s were dead air).

**Bottom line: no new capture is needed. Both gaps are already in the captured logs.**
One is a wrong argument byte in `6D2.h`, the other is a reply the extractor commented out with a
heuristic that is wrong for this model. Both fixes are hand-edits to
`qemu-eos/hw/eos/mpu_spells/6D2.h`.

---

## 0. Why the extractor cuts — the actual rules

`qemu-eos/hw/eos/mpu_spells/extract_init_spells.py` has five suppression rules. Three matter here:

| line | rule | effect |
|---|---|---|
| 182-185 | `if description == "PROP_SHOOTING_TYPE": comment_block = True; comment_all_blocks = True` | hard stop — everything from that request onward is `//`-prefixed |
| 276-279 | `if description == "EVENTID_METERING_START_SW1ON": ... comment_all_blocks = True` | same, triggered by a half-shutter press |
| 269-271 | `if reply[6:11] in [ "02 00", "02 0e" ] and num > 1: cmt = "//"; warning = "mode switch?"` | comments out a **single reply**, not a block |

Corrections to `movie-spells-analysis.md` §1, which the numbers do not support:

* The **photo** capture is **not** truncated at all. `PROP_SHOOTING_TYPE` (`04 0c`) appears **zero
  times** in `tools/6D2-DEBUGMSG-body.txt`, and so does `EVENTID_METERING_START_SW1ON`. Neither
  hard-stop rule ever fires.
  `6D2.h` = 69 numbered spells + 2 commented blocks = **71**, which is exactly the log's 71
  `mpu_send` lines. Every request the body made is represented.
  The 2 commented blocks are `NotifyGUIEvent` (6D2.h:65) and `PROP_BATTERY_CHECK` (6D2.h:231) —
  both deliberate, both supplied instead by `NotifyGUIEvent.h`.
* The **movie** capture is the one that gets cut: `tools/6D2_spells_body_movie.h` = 69 numbered +
  84 commented = **153** = the movie log's 153 `mpu_send` lines. (The "128 entries / 44 active"
  figures in `movie-spells-analysis.md` §1 are wrong; the split is 69 active / 84 commented.)
* Inside `6D2.h`, exactly **one** reply is commented out inside an otherwise-active block:

      6D2.h:29:  // { 0x94, 0x93, 0x02, 0x0e, ... }   /* reply #5.1, Mode group, mode switch? */

  That one line is the boot blocker. See §1.

---

## 1. What the guest is waiting for at the stall

### The stall

```
gui-stage-stock-boot-trace.log:460  [ NFCMgr:e05d43f3 ] (3e:03)  nfcmgrstate_CeInitialize:ce_init 4194307
gui-stage-stock-boot-trace.log:461  [ NFCMgr:e05d934b ] (3e:03)  nfcmgrstate_Initialize ce_init
gui-stage-stock-boot-trace.log:463  [ DbgMgr:e05ead8f ] (00:01) [PM] Disable (ID = 10, cnt = 1/2)
gui-stage-stock-boot-trace.log:464  [ DbgMgr:e05eae1b ] (00:01) [PM] Enable (ID = 10, cnt = 0/1)
<nothing for the remaining 119 s>
```

### The last MPU exchange, and it *was* answered — except for one reply

The guest's last message to the emulated MPU:

```
gui-stage-stock-boot-trace.log:405  [MPU] Received: 06 04 02 14 00 00  (unnamed - spell #5)
```

QEMU answered with 15 replies (`6D2.h:30-45`), ending:

```
gui-stage-stock-boot-trace.log:443  [MPU] Sending : 08 06 01 a7 01 01 00 00
gui-stage-stock-boot-trace.log:446  [MPU] Sending : 08 06 01 a7 01 00 00 00
gui-stage-stock-boot-trace.log:449  [MPU] Sending : 0e 0d 04 30 00 00 00 00 00 00 00 00 00 00
gui-stage-stock-boot-trace.log:452  [MPU] Sending : 06 05 01 48 01 00  (PROP_LIVE_VIEW_MOVIE_SELECT)
gui-stage-stock-boot-trace.log:455  [MPU] Sending : 06 05 01 4b 01 00  (PROP_LIVE_VIEW_VIEWTYPE_SELECT)
```

The **first** reply of that block, `reply #5.1`, is the 148-byte **Mode group** `94 93 02 0e …`, and
it is commented out at `6D2.h:29` by the `num > 1` "mode switch?" rule.

On the body the exchange is identical *except* the Mode group is delivered, and the ICU
immediately acknowledges it:

```
tools/6D2-DEBUGMSG-body.txt:308  0.080117  mpu_send(06 04 02 14 00 00)            <- same request
tools/6D2-DEBUGMSG-body.txt:318  0.080797  mpu_recv(94 93 02 0e 03 03 03 00 02 02 03 00 …)   <- Mode group, 0.7 ms later
        …
tools/6D2-DEBUGMSG-body.txt:407           PropMgr:e044f427: Complete WaitID = 0x80000001, 0xE006442B(0)
tools/6D2-DEBUGMSG-body.txt:408  0.085958  mpu_send(08 06 00 00 02 0e 00 00)      <- "I finished handling 02 0e"
```

`known_spells.py:168` documents the `02 0e` Mode group as carrying properties
`80000000, 80000001, 80000002, …` — **0x80000001 is exactly the WaitID PropMgr completes** one line
before it sends the ack. No Mode group → PropMgr's WaitID 0x80000001 never completes → the ICU never
sends `08 06 00 00 02 0e 00 00`.

That ack is `6D2.h:46`, spell #6 — the gate for the next six init properties
(`01 49` PROP_LIVE_VIEW_AF_SYSTEM, `01 12`/`01 13` WBB, `01 8f`, `01 b1`, `01 03` PROP_DRIVE_MODE) and
transitively for spells #7 through #69. The whole downstream init chain is behind it. In the QEMU
trace `WaitID` appears **0 times**.

**This is a 6D2-specific extractor bug, not a data gap.** On the 6D and 70D the MPU sends the Mode
group as reply #1.1 (to the Init spell, `num == 1`), so the rule spares it — `6D.h:3` and `70D.h`
both have an active Mode group plus a commented later duplicate. On the 6D2 the MPU sends it only
once, at `num == 5`, so `num > 1` kills the only copy.

### The second gap — the known unknown

```
gui-stage-stock-boot-trace.log:374  [MPU] Received: 08 06 01 a7 00 01 00 00  (unknown - unnamed)
```

`6D2.h:7` holds `{ 0x08, 0x06, 0x01, 0xa7, 0x01, 0x01, 0x00, 0x00 }` as spell #2. `match_spell()`
(`hw/eos/mpu.c:185-216`) compares every byte from index 1 with no wildcard unless the entry uses
`ARG0..ARG2` (`mpu.h:6-8`), so **byte[4] `00` vs `01` is a miss**. `01 a7` is not in
`known_spells.py`, hence "unnamed".

Cost of that miss: **all 14 of spell #2's replies are silently dropped.** Only 3 of the 5 requests
QEMU received produced any output at all:

```
gui-stage-stock-boot-trace.log:348  Received: 06 04 02 00 00 00  (Init - spell #1)
gui-stage-stock-boot-trace.log:374  Received: 08 06 01 a7 00 01 00 00  (unknown - unnamed)   <- 14 replies lost
gui-stage-stock-boot-trace.log:396  Received: 22 20 0e 39 …          (unnamed - spell #3)
gui-stage-stock-boot-trace.log:402  Received: 06 05 03 8a 00 00      (unnamed - spell #4)
gui-stage-stock-boot-trace.log:405  Received: 06 04 02 14 00 00      (unnamed - spell #5)
```

Never sent, confirmed by grepping every `[MPU] Sending` line in the trace: `01 06` PROP_APERTURE,
`01 3f` PROP_FLASH_ENABLE, `01 4f` PROP_FIXED_MOVIE, `02 0d` **Card group**, `02 0f` **Movie group**,
`02 10` **AF group**, `02 11` **AF2 group**, `01 b6`, `01 b5`, `02 05` PROP_CFN_1, `02 08` PROP_CFN_4,
`01 95`, `01 21` PROP_CARD2_EXISTS. (`02 07` PROP_CFN_3 survives only because spell #3 repeats it.)

---

## 2. Do the captured logs contain the answer? — **Yes, verbatim, in the movie log**

The photo log never produces `a7 00 01`; its only `01 a7` request is the `01 01` variant
(`tools/6D2-DEBUGMSG-body.txt:211`). The **movie** log has both, and the second one is byte-for-byte
the message QEMU cannot answer:

```
tools/6D2-DEBUGMSG-body-movie.txt:227  0.419356  mpu_send(08 06 01 a7 01 01 00 00)
        … 20 replies (Card/Movie/AF groups, CFN_1/3/4, …) …
tools/6D2-DEBUGMSG-body-movie.txt:354  0.430241  mpu_send(08 06 01 a7 00 01 00 00)   <<< the unknown
tools/6D2-DEBUGMSG-body-movie.txt:397  0.433034  mpu_recv(08 06 01 a7 01 01 00 00)
tools/6D2-DEBUGMSG-body-movie.txt:406  0.433373  mpu_recv(08 06 01 a7 01 00 00 00)
tools/6D2-DEBUGMSG-body-movie.txt:410  0.433587  mpu_recv(08 06 01 a7 00 01 00 00)
tools/6D2-DEBUGMSG-body-movie.txt:414  0.433811  mpu_recv(08 06 01 a7 00 00 00 00)
tools/6D2-DEBUGMSG-body-movie.txt:433  0.435224  PropMgr: Complete WaitID = 0x80000001, 0xE006442B(0)
tools/6D2-DEBUGMSG-body-movie.txt:436  0.435361  mpu_send(08 06 00 00 02 0e 00 00)
```

The real MPU answers each ICU `01 a7` request by echoing it with the last argument stepped
`01 → 00`. The extractor already turned this into a valid, **uncommented** spell block —
`tools/6D2_spells_body_movie.h:35-39`:

```c
    { { 0x08, 0x06, 0x01, 0xa7, 0x00, 0x01, 0x00, 0x00 }, {     /* spell #6 */
        { 0x08, 0x06, 0x01, 0xa7, 0x01, 0x01, 0x00, 0x00 },     /* reply #6.1 */
        { 0x08, 0x06, 0x01, 0xa7, 0x01, 0x00, 0x00, 0x00 },     /* reply #6.2 */
        { 0x08, 0x06, 0x01, 0xa7, 0x00, 0x01, 0x00, 0x00 },     /* reply #6.3 */
        { 0x08, 0x06, 0x01, 0xa7, 0x00, 0x00, 0x00, 0x00 },     /* reply #6.4 */
```

### Recommended edits to `6D2.h` (two lines)

1. **`6D2.h:7`** — widen spell #2's byte[4] to a wildcard so the ICU's actual message matches and the
   14 init property replies are delivered:

   ```c
   -    { { 0x08, 0x06, 0x01, 0xa7, 0x01, 0x01, 0x00, 0x00 }, {     /* spell #2 */
   +    { { 0x08, 0x06, 0x01, 0xa7, ARG0, 0x01, 0x00, 0x00 }, {     /* spell #2 */
   ```

   `ARG0` = `0x0100` (`mpu.h:6`); `match_spell()` treats high-byte 1 as "matches anything"
   (`mpu.c:204-208`). None of spell #2's replies contain `ARG0`, so `copy_n_subst_spell()`
   (`mpu.c:113-137`) has nothing to substitute — no side effects.

2. **`6D2.h:29`** — un-comment the Mode group so PropMgr can complete WaitID 0x80000001 and emit the
   `08 06 00 00 02 0e 00 00` ack that spell #6 waits on:

   ```c
   -     // { 0x94, 0x93, 0x02, 0x0e, 0x03, 0x03, 0x03, 0x00, 0x02, 0x02, 0x03, … }, /* reply #5.1, Mode group, mode switch? */
   +        { 0x94, 0x93, 0x02, 0x0e, 0x03, 0x03, 0x03, 0x00, 0x02, 0x02, 0x03, … }, /* reply #5.1, Mode group */
   ```

   Keep the **photo** payload (`[8] = 0x02`, `[92] = 0x01`). The movie variant (`[8] = 0x03`) is the
   movie-mode selector, not a fix — see `movie-spells-analysis.md` §3a.

Optional, strictly additive: append the four `01 a7` echoes from
`tools/6D2_spells_body_movie.h:36-39` to spell #2's reply list. Spell #5 already emits the
`a7 01 01` / `a7 01 00` pair (`6D2.h:40-41`, seen at trace lines 443/446), so this is belt-and-braces
rather than required.

If the `ARG0` wildcard is judged too broad, the alternative is to paste
`tools/6D2_spells_body_movie.h:35-40` verbatim as a new entry between spells #2 and #3 — but note
that on its own it recovers **only** the four `a7` echoes, not the 14 lost property replies, because
the movie MPU attached those to the `a7 01 01` request instead. The wildcard is what recovers the
property payload.

Upstreaming note: rule `extract_init_spells.py:269-271` should become
`if reply[6:11] in ["02 00", "02 0e"] and num > 1 and <this class/id already emitted>` — it is meant
to suppress *duplicate* mode-group records (a user turning the dial mid-capture), not the first one.
The 6D2 is the counter-example where the first one arrives at `num == 5`.

---

## 3. Further spells needed to reach the GUI — already captured, already active

**Nothing is missing.** The photo capture reaches the GUI, and every request in it is an active
entry in `6D2.h`:

```
tools/6D2-DEBUGMSG-body.txt:3740  0.870647  GuiMainTas:e009a087:82:03: -> handleGuiInit
tools/6D2-DEBUGMSG-body.txt:3742  0.873962  GuiMainTas:e04959eb:41:03: GuiInitializeGraphics
tools/6D2-DEBUGMSG-body.txt:3821  0.905297  GuiMainTas:e009a063:84:03: AllocateVramCBR pAddress=426fe800
tools/6D2-DEBUGMSG-body.txt:3941  0.920961  GuiMainTas:e04d9263:04:03: refresh x=0 y=0 w=960 h=540
tools/6D2-DEBUGMSG-body.txt:3955  0.928947  GuiMainTas:e074517f:82:03: IDLEHandler INITIALIZE_CONTROLLER
tools/6D2-DEBUGMSG-body.txt:3956  0.929008  GuiMainTas:e0743fdd:82:03: IDLEHandler GOT_TOP_OF_CONTROL
tools/6D2-DEBUGMSG-body.txt:3958  0.929109  GuiMainTas:e0769333:82:03: GUI_RegisterPropertySlave, 306
```

`handleGuiInit` fires at **0.87 s**, around `mpu_send` index [43]; the full 960×540 OSD refresh at
0.92 s; `GOT_TOP_OF_CONTROL` at 0.93 s. The log continues to 18.83 s, by which point the ICU is
idle and only heartbeats `08 06 01 0b 00 00 00 00` every ~3 s
(`tools/6D2-DEBUGMSG-body.txt:6483, 6495, 6504, 6514, 6523`).

So the GUI-reaching sequence sits inside the **first second** of a capture window that runs to
18.8 s, is fully present as spells #1-#69 in `6D2.h`, and none of it lands in a commented region.
The commented tail in `tools/6D2_spells_body_movie.h` is post-init LiveView/OLC runtime traffic
(`09 xx` metering, `0e xx` display) — useful later for a 6D2 `LiveView.h` extension, irrelevant to
reaching the GUI.

Predicted sequence once the two edits land: spell #5 delivers the Mode group → ICU sends
`08 06 00 00 02 0e 00 00` → spell #6 → spell #7 (`08 07 03 6a 01 07 00 00`) → … → spell #69. Whether
anything *else* then blocks (NFC I2C, display hardware) is not visible from the MPU side and needs a
re-run to find out.

---

## 4. If a longer capture were ever needed (it is not, for the GUI)

For completeness, the two knobs and what the current capture actually cost:

* **Buffer size** — `ml/src/log-d678.c:334`, `buf_size = 2 * 1024 * 1024;`. The 6D2 takes the generic
  `#else` branch (no `CONFIG_6D2` override next to the `CONFIG_200D` / `CONFIG_80D` / `CONFIG_5D4`
  cases), allocated via `_AllocateMemory()` at `log-d678.c:347`.
* **Dump delay** — `ml/src/init.c:650`, `msleep(20000)` in `startup_log_dump_task()`
  (`init.c:646-652`), started from `boot_post_init_task()` at `init.c:660`. The build is gated by
  `CONFIG_STARTUP_LOG` in `ml/platform/6D2.111/Makefile:29-32`
  (`make CONFIG_STARTUP_LOG=y`), which pulls in `log-d678.o`.

Measured headroom, from the photo log's DIAG trailer:

```
[0] 20.007353  log_dump: Logging finished.
[0] 20.007383  log_dump: Free memory: 547484 bytes.
*** DIAG entered=6530 appended=6530 drop_nobuf=0 drop_full=0 lock_enter=6530 lock_exit=6530
    irq_enabled=0 len=521801 buf=7ba4c4 buf_size=2097152
```

`drop_full=0` and `len=521801` of `buf_size=2097152`: the photo capture used **25 %** of the buffer
and lost nothing across the full 20 s. Enlarging it would gain nothing, and there is only ~547 KB
free in that pool afterwards anyway, so 2 MiB → 4 MiB is not obviously safe.

The **movie** capture is the one that overflows: `tools/6D2-DEBUGMSG-body-movie.txt` is 2,097,090
bytes and ends mid-line at 3.01 s with no trailer, because LiveView emits DebugMsg at roughly 30×
the photo-mode rate. A movie-mode LiveView capture would need `buf_size` raised (and the free-memory
question answered first), or `msleep(20000)` cut to ~5000 so the dump happens before the buffer
fills, or DebugMsg class filtering in `my_DebugMsg()` (`log-d678.c:44-56`). **None of that is on the
path to the GUI** — do not ask the user to re-shoot anything for this.

**User action required: none.** Both fixes are hand-edits to `qemu-eos/hw/eos/mpu_spells/6D2.h`,
sourced from logs already on disk.
