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
| [.planning/spikes/](.planning/spikes/) | Open investigations (QEMU assert, stub verification, cheap-wins scoping, ML boot) |
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

ML builds for the 6D2 and qemu-eos boots stock firmware to
`K406 ICU Firmware Version 1.1.1` before halting on a Canon `RscMgr` assert.
See the roadmap for the current state.

[qemu-eos]: https://github.com/reticulatedpines/qemu-eos
