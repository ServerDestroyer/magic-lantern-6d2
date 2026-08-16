# Spike 014 — UART crash console (the dead-camera exception)

**Date:** 2026-08-16
**Type:** execution
**Status:** DEFERRED — the one thing USB/peek-to-SD can't do; do only when a crash/freeze case actually needs it.
**Parent:** spike 011.

## Why it exists

The USB debugger (012) and peek-to-SD (013) are both **ML code** — if ML wedges or the camera hard-freezes, they die with it and the card log comes back blank. UART is **passive and firmware-independent**: it captures whatever the camera prints, including its last words before a lockup, and pre-DryOS bootloader output. It is the only channel that sees a dead camera.

Directly relevant to the CRASH00 / re-arm freeze investigations in `tools/`, where the on-card log is empty precisely because the camera died before the flush.

## Goal

Get read-only serial capture of the 6D2's ICU UART (DryOS DebugMsg + bootloader + drysh) with minimal hardware and no soldering to the SoC.

## Plan

1. **Locate access.** Peel the thumb-rest rubber first (2 min, reversible) and look for a hole/connector — 200D/R/RP precedent. If nothing, rear cover off per the 2025 teardown (screws-only, watch the LCD harness). The 6D2's FZC-8 access is undocumented — this step settles it.
2. **Identify pins.** Corrected family pinout: pins 2/3 = ICU RX/TX (1.8V), 4 = GND, 6/7 = MPU TX/RX (3.3V). Multimeter-verify before driving anything — never measured on a 6D2.
3. **Read-only, cheap.** A plain 3.3V FTDI reads the 1.8V ICU TX out of the box (confirmed on EOS M); 115200 8N1. Only *driving* the camera's RX needs a 2×470Ω divider. FZC-8 is 0.5mm pitch — needle probes, a trimmed 8-way FFC stub, or coon's flex breakout.
4. **Capture** the boot log / crash tail; compare against the QEMU serial console.

## What this unlocks

- **Output when the camera dies before the card flushes** — the CRASH00 / re-arm freeze tail.
- **Pre-boot / bootloader visibility** — the earliest debug surface; the unbrick channel.
- **Interactive drysh** (over the same line) — native Canon shell, demonstrated on family bodies.

## Why deferred

Needs opening the camera (not "no hardware"), and the project's current crashes are either already root-caused or reproducible in QEMU. Pull this off the shelf when a real freeze produces a blank card log and no other channel can see it. `uart_printf` is already stubbed at `platform/6D2.111/stubs.S:284` (`0xe04eb7a0`), so ML-side UART output needs no new stub.
