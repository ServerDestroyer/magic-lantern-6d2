---
spike: 003
name: cheap-wins-scoping
type: standard
validates: "Given the MOV time limit and focus-box/clean-HDMI asks, when the responsible code paths are traced in ML and the 6D2 ROM, then each has a concrete implementation route and effort estimate"
verdict: PENDING
related: [002]
tags: [features, scoping, upstream]
---

# Spike 003: Scoping the Two Cheap Wins

## What This Validates

**Given** the two targets the upstream maintainer already flagged as cheap and
high-value for DIGIC 7 bodies,
**when** the responsible code paths are traced through `ml/` and the 6D2 ROM,
**then** each target has a concrete implementation route, the specific Canon
function or property involved, and an honest effort estimate.

The two targets (Phase C step 9):

1. **MOV recording time limit extension** — reticulatedpines called this
   "fairly easy to add" on D7 cams.
2. **Focus-box hide → clean HDMI / clear overlays** — upstream issue #221, the
   community's top ask for the new cams, driven by WalterSchulz.

This is scoping, not implementation. The deliverable is knowing what the work
actually is before committing to it.

## Research

Both features exist and work on mature bodies, so the reference implementations
are in-tree — the question is what differs on DIGIC 7. Compare against a mature
platform such as `5D3.113`, and check which `CONFIG_*` gates gate each feature.

## How to Run

Static source analysis plus ROM string/symbol search. No emulator required, no
camera required.

## What to Expect

For each of the two features: the mature-body implementation, the 6D2 gap, the
specific blocker (missing stub / unported subsystem / different hardware path /
just never enabled), and an effort estimate.

## Investigation Trail

_Updated as the spike progresses._

## Results

_Pending._
