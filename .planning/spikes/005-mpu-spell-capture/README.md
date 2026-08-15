---
spike: 005
name: mpu-spell-capture
type: standard
validates: "Given a startup-log ML build for the 6D2, when it runs and its DebugMsg log is converted by extract_init_spells.py, then a valid mpu_spells/6D2.h is produced — the artifact spike 001 says qemu-eos is missing"
verdict: PARTIAL
related: [001, 004]
tags: [qemu, mpu, logging, upstream, body-test]
---

# Spike 005: Capture 6D2 MPU Spells

## What This Validates

**Given** an ML build for `6D2.111` with the DIGIC 6/7/8 startup logger enabled,
**when** it boots and writes `DEBUGMSG.LOG`, and that log is fed to
`qemu-eos/hw/eos/mpu_spells/extract_init_spells.py`,
**then** a valid `mpu_init_spells_6D2[]` table is produced.

This is the artifact spike 001 identified as the root cause of the `RscMgr`
assert: qemu-eos has **no 6D2 MPU spells** — and in fact no DIGIC 7 camera has
one upstream. The 6D2 would be the first.

## Verdict: PARTIAL

The pipeline works end to end and produced a real spell table. It cannot yet
produce a *useful* one: the emulator's MPU traffic is synthetic, its boot stops
before most of it, and a build regression currently prevents capture entirely.

### What was validated

- **The pipeline runs end to end.** Startup-log build → boot → `DEBUGMSG.LOG` →
  extractor → `mpu_init_spells_6D2[]` with 23 spells; 16 carry a
  description, of which 8 are symbolic property names (`PROP_AVAIL_SHOT`,
  `PROP_BURST_COUNT`, `PROP_TFT_STATUS`, …), 6 are undecoded raw property IDs
  (e.g. "PROP 80030058") and 2 are protocol markers. Artifacts:
  `tools/6D2-startup-qemu.txt`, `tools/6D2-DEBUGMSG-card.txt`,
  `tools/6D2_spells_qemu.h`.
- **The logger is correct.** Measured from the host over the qemu monitor, not
  inferred: 1306 DebugMsg calls, **all** appended, `drop_nobuf=0`,
  `drop_full=0`, `lock_enter == lock_exit`, the patch at `0xdf006e6c` intact for
  the whole run, and a 2 MB buffer genuinely allocated from a 9 MB pool.
- **The card write is correct.** With qemu fully exited: 102744 bytes, **zero**
  NUL bytes, 1310 lines, 23 `mpu_send` + 3 `mpu_recv`, `Logging finished.` and
  the DIAG trailer both present.
- **Two independent capture paths agree** — scraping the qemu console and
  reading ML's own buffer out of guest RAM both yield the same 23 spells.

### What was not validated

**The QEMU-captured spells are worthless for fixing QEMU.** qemu-eos announces
`[MPU] FIXME: using generic MPU spells for 6D2` and then replays that generic
model; the 23 spells are the emulator talking to itself. Feeding them back in
would be circular. Only a real body produces a real 6D2 spell set.

**Both obstacles are real.** What 005 adds is narrow: the capture *mechanism*
survives the wedge — the `log_dump` task woke at t=19.5 s and wrote a complete
102744-byte file. But Canon's boot does stop early: the assert is at t=0.322816
and **22 of 23 `mpu_send` plus all 3 `mpu_recv` land in the 270 ms before it**,
with only PM/RTC housekeeping afterwards. So a body run is needed both because
emulated MPU traffic is synthetic *and* because boot truncates.

## How To Reproduce

```bash
cd "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2"
nix-shell --run 'cd ml/platform/6D2.111 && \
  make disk_image CONFIG_STARTUP_LOG=y \
    ARM_BINPATH="$(dirname $(which arm-none-eabi-gcc))" \
    ML_MODULES="raw_video/mlv_lite file_man bench dual_iso"'
```

`ML_MODULES` must be given explicitly: the default list includes `lua`, which
does not compile under gcc 15.

Then either boot in QEMU and read the card **after qemu has exited**, or use
`tools/grab_log.py`, which pulls the buffer straight from guest RAM via the
monitor's `pmemsave` and therefore works even when the guest wedges.

Convert:

```bash
cp <log> 6D2-startup.log      # extractor derives the model from the filename
ML_PLATFORM_DIR=/home/chris/ml6d2/magiclantern_simplified/platform/ \
  python3 qemu-eos/hw/eos/mpu_spells/extract_init_spells.py 6D2-startup.log > 6D2.h
```

## Code Changes Made (uncommitted, in gitignored `ml/`)

| File | Change |
|---|---|
| `platform/6D2.111/Makefile` | new `CONFIG_STARTUP_LOG=y` flag — adds `log-d678.o`, defines `-DCONFIG_STARTUP_LOG` |
| `src/init.c` | `log_start()` at the top of `boot_post_init_task`, plus a `log_dump` task that sleeps 20 s then `log_finish()` |
| `src/log-d678.c` | gcc-15 build fixes; DIAG counters; **safety fix** replacing upstream's `while (!buf);` |
| `qemu-eos/.../outils.py` | honour `ML_PLATFORM_DIR` (upstream hardcodes an old repo path) |

The `while (!buf);` fix matters: upstream spins forever inside
`boot_post_init_task` if the buffer allocation fails, which on a body is a camera
that looks bricked — and the blocker below proves that allocation really can
fail. It now sets `buf_size = 0` and returns.

Deliberately **not** changed: the adjacent `if (!(read_cpsr() & 80))` is dead
code (80 is decimal = 0x50, overlapping CPSR M[4], set in every AArch32 mode).
Only its `while(1)` became a return. Whether correcting it to `0x80` would drop
messages was never isolated, and is doubtful — `cli_spin_lock`
(arm-mcr.h:571-573) masks interrupts immediately before it, so a live check
should pass. The `diag_irq_enabled` counter would settle it.

## Blockers

1. **Allocation fails at `log_start()`.** Cause NOT established — the A/B is
   untried. Correlated with the feature set enabled around
   14:00 on 2026-08-15 (`FEATURE_SHOW_TASKS`, `FEATURE_SHOW_CPU_USAGE`,
   `FEATURE_SHOW_GUI_EVENTS`, `FEATURE_OVERRIDE_MOVIE_30_MIN_LIMIT`).
   `GetMemoryInformation()` returns **0 total / 0 free**, every
   `_AllocateMemory` fails from 2 MB down to 128 KB even with retry + `msleep`,
   so `buf` stays NULL and nothing is logged. Before those features, the same
   point reported 9 MB total / 5.9 MB free. Reproduced across four builds,
   including one reverted almost to the known-good logger — which rules out the
   logger edits, but does **not** isolate which of that session's four changed
   files (`features.h`, `consts.h`, `internals.h`, `stubs.S`) is responsible.

**Retracted — do not reinstate.** An earlier draft listed an ISR hook conflict
with `tskmon.c`. It is false: `src/tskmon.c:501` guards those assignments behind
`#ifdef CONFIG_ISR_HOOKS`, defined nowhere in the tree, so they never compile;
`tskmon.o` is unconditional (`platform/Makefile:364`), not gated by
`FEATURE_SHOW_TASKS`; and the captured DIAG trailer reads
`pre_isr_hook=103935 post_isr_hook=1039c9` — log-d678's own hooks, intact.

## Correction To Earlier Findings

`.planning/ROADMAP.md` records this thread's blocker as "a log-buffering bug in
`src/log-d678.c` (MPU lines reach the QEMU console but not the card-side
`DEBUGMSG.LOG`)". **That is wrong and has been corrected.** There is no
buffering bug. Two measurement mistakes produced it:

- `grep` on `DEBUGMSG.LOG` silently reports nothing because the file contains
  NUL padding and is treated as binary — use `grep -a`. The MPU lines were
  present all along.
- Reading `sd.qcow2` while qemu still held it returns a half-flushed image whose
  tail reads as NULs at a 16 KiB FAT-cluster boundary. This produced an apparent
  "32 KB truncation" that was briefly written up as a qemu-eos SD DMA bug. It is
  not real: stop the emulator, then read.
