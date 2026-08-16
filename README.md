# Magic Lantern on the Canon EOS 6D Mark II

Working notes, planning, and local tooling for getting more Magic Lantern
features running on the 6D2 (DIGIC 7) — using [qemu-eos] for the loop that
doesn't need the camera, and the real body for the loop that does.

This repo is **not** a fork of Magic Lantern. Upstream code lives in its own
repos and is cloned locally (see below); patches go upstream as PRs.

## What's here

| Path | What |
|---|---|
| [PLAN_OF_ACTION.md](PLAN_OF_ACTION.md) | Narrative: research, build traps, reasoning |
| [.planning/ROADMAP.md](.planning/ROADMAP.md) | Status ledger — done / in flight / next |
| [.planning/spikes/](.planning/spikes/) | Investigations: QEMU boot, stub verification, MPU capture, raw-video memory, dual-ISO, lossless compression, button codes |
| [docs/6D2_CONTROLS.md](docs/6D2_CONTROLS.md) | 6D2 control map + how ML is driven on this body |
| [patches/](patches/) | The canonical record of every change (the ML and qemu-eos clones are gitignored) |
| [shell.nix](shell.nix) | ARM toolchain + build deps, project-local |
| [discord-bot/](discord-bot/) | Read-only logger for the ML Discord (research aid) |

## What's deliberately not here

Cloned separately, ignored by git:

```sh
git clone -b dev  https://github.com/reticulatedpines/magiclantern_simplified ml
ln -s ml magiclantern_simplified
git clone -b qemu-eos-v4.2.1 https://github.com/reticulatedpines/qemu-eos
```

`roms/` and `Backup SD card/` are gitignored and stay that way — Canon firmware
is copyrighted. Dump your own ROMs from your own body; don't fetch them from
mirrors.

## Build

```sh
nix-shell            # ARM toolchain
cd ml/platform/6D2.111 && make
```

## Status

Everything below is hardware-confirmed on a real 6D2 running firmware 1.1.1,
unless noted. See [.planning/ROADMAP.md](.planning/ROADMAP.md) and the spikes
for the evidence behind each line.

**Working on the camera**

- **Raw video** — 14-bit 1920×1080 MLV, pixel-valid and properly finalized.
  Recording length is buffer-bound (see *Known limits*).
- **Dual-ISO stills** — measured +1.71 EV analog line-pair separation. The
  module ships hidden on new DIGIC 7/8 ports by default; unhiding it is all
  that was needed here.
- **MOV/MP4 recording limit override** — the 29:59 cap lifted, auto-stop
  verified at a custom limit.
- **Debug displays** — task list, CPU usage, GUI events.

**Fixes found and sent upstream**

| PR | What |
|---|---|
| [#294](https://github.com/reticulatedpines/magiclantern_simplified/pull/294) | 6D2: override the 29:59 MOV/MP4 recording limit |
| [#295](https://github.com/reticulatedpines/magiclantern_simplified/pull/295) | D678: don't wait out the timeout on writes denied by the whitelist |
| [#296](https://github.com/reticulatedpines/magiclantern_simplified/pull/296) | log-d678: don't spin forever when the log buffer allocation fails |
| [#297](https://github.com/reticulatedpines/magiclantern_simplified/pull/297) | mlv_lite: stamp the *measured* frame rate into the MLVI header |
| [#298](https://github.com/reticulatedpines/magiclantern_simplified/pull/298) | mlv_lite: reallocate buffers after a recording stops on its own |

Three of those (#295, #297, #298) are body-agnostic — they fix behaviour that
affects other ports too, not just this one.

**Emulation (qemu-eos)**

Stock 6D2 firmware now **completes startup** in qemu-eos, reaching
`GIS_Initialize : End` and Canon's own `NotifyComplete (Startup)`. Getting
there needed the first DIGIC 7 MPU spell set (captured from the body), 6D2
button codes (decoded statically from ROM), and a per-core interrupt fix —
qemu-eos modelled only one of the 6D2's two CPUs' interrupt banks. Patches
live in [patches/](patches/); upstreaming is in progress.

The old `RscMgr` assert that stopped boot was never an SD-card problem: it was
a frame-rate switch receiving garbage because the emulator had no 6D2 property
data.

**Known limits**

- Raw video is write-bound: the card measures 82.6 MB/s, while uncompressed
  1080p needs 87 MB/s at 24p and 218 MB/s at 59.94p — so takes end when the
  135 MB buffer fills. Lossless compression is scoped
  ([spike 008](.planning/spikes/008-lossless-compression-scoping/)) and would
  make 24/25/29.97p sustained; the encoder hardware is present in the ROM but
  DIGIC 7 restructured its API.
- Dual-ISO in *movie* mode is not enabled yet — it needs one CMOS register
  table ([spike 007](.planning/spikes/007-dual-iso-scoping/)).
- Magic Lantern itself does not yet run fully under emulation.

## Method note

Findings here are checked by independent re-derivation before they are written
down — several confident-but-wrong conclusions have been caught that way,
including a proposed code fix that turned out to rest on a mis-traced call
path. Where something is unproven, the docs say so.

[qemu-eos]: https://github.com/reticulatedpines/qemu-eos
