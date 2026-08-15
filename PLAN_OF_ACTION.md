# 6D Mark II — Magic Lantern Plan of Action

## Status (2026-08-15)

**Live status ledger is now `.planning/ROADMAP.md`** — this file keeps the
narrative, the build traps, and the reasoning. Update both when state changes;
this header block has already gone stale twice in one day.

- Done: `ml/` and `qemu-eos/` cloned; `discord-bot/` read-only logger built
  and verified (see `discord-bot/README.md`); ROM dumps recovered and verified;
  toolchain via `shell.nix`; **ML built for 6D2** (Phase A step 2); qemu-eos
  built and booting stock firmware as far as a Canon assert (step 4, partial).
- Waiting on Chris: Discord dev-portal setup + admin invite ask per the
  `discord-bot/README.md`. Nothing else is blocked on the camera.
- Work in flight: spikes 001-004 in `.planning/spikes/` (QEMU assert, stub
  verification, cheap-wins scoping, ML boot in QEMU) plus Phase B's
  `FEATURE_MATRIX.md`.

Goal: get ML features working on the Canon EOS 6D Mark II (DIGIC 7), using QEMU
emulation for the loop that doesn't need the camera, and the real body for the
loop that does.

## 0. Ground truth (as of research on 2026-08-15)

- Active codebase is **git**, not the old Mercurial tree:
  `https://github.com/reticulatedpines/magiclantern_simplified` (branch `dev`).
- Emulator is a patched QEMU: `https://github.com/reticulatedpines/qemu-eos`,
  supported branch **`qemu-eos-v4.2.1`**.
- 6D2 is on the official release list (issue #151, closed Dec 2025), i.e. it
  boots and ships nightlies — it is *not* feature-complete.
- Maintainer's own statement (issue thread): feature parity between old and new
  cams is not feasible soon; raw video works on 200D and is "experimental
  quality", porting to other DIGIC 6/7 cams is possible but time-consuming.
  Increased MOV time limit is "fairly easy to add" on D7 cams.
- Open 6D2 request already filed: #221 — hide focus box → clean HDMI / clear
  overlays. That is the community's top ask for the new cams.

## 1. What we have downloaded

| Item | Path | Notes |
|---|---|---|
| ML source | `ml/` (+ `magiclantern_simplified` symlink) | branch `dev` |
| Patched QEMU | `qemu-eos/` | branch `qemu-eos-v4.2.1` |
| ARM toolchain | system | `arm-none-eabi-gcc` — must be added to NixOS config |
| **6D2 ROM dumps** | `roms/6D2/` | **DONE** — dumped 2025-09-29, verified |

**Blocker cleared (2026-08-15).** `ROM0.BIN` (32 MiB) + `ROM1.BIN` (16 MiB) were
dumped from the body on 2025-09-29 and are now in `roms/6D2/`. Verified genuine:
`akashimorino` DryOS marker, version string `1.1.1` (matches `platform/6D2.111`),
`FIRMWARE_ID 0x80000406`, valid Thumb-2 code at offset `0x40000` (= the Makefile's
`MAIN_FIRMWARE_ADDR 0xE0040000`). md5: ROM0 `879cead703398cb4928cf6e9b5969504`,
ROM1 `355ef058ff64b2a52f700aaacd2e5a3a`. Source card also mirrored to
`Backup SD card/`. Canon firmware is copyrighted — never commit these or fetch
them from mirrors.

### Camera state — ML is already installed on the SD card

Established 2026-08-15 from file timestamps on the card. Two date clusters tell
the history:

| When | What | Evidence |
|---|---|---|
| 2025-06-20 | Nightly `magiclantern.2025-06-20.6D2.111` copied to card; `ML-SETUP.FIR` run from Canon's firmware-update menu (sets the camera bootflag) | `autoexec.bin`, `ML-SETUP.FIR`, `ML/{cropmks,data,doc,fonts,modules,scripts}` all dated 2025-06-20 |
| 2025-09-29 | Camera booted with ML; Debug → "Dump ROM and RAM" run | `ML/SETTINGS/{magic.cfg,MENUS.CFG}` and `ML/LOGS/{ROM0,ROM1}.BIN` dated 2025-09-29 — neither dir ships with the nightly, ML creates them at runtime |

Consequences for the rest of the plan:

- **The camera is already ML-capable.** Bootflag is set, nightly is installed.
  Phase C body testing (step 10) needs no reinstall — just drop our built
  `autoexec.bin` onto the card.
- **Do not format that card in the camera.** The card-side boot flags
  (`EOS_DEVELOP` + `BOOTDISK` in the boot sector) are wiped by an in-camera
  format and ML then silently stops loading. Recovery is
  `ml/tools/card-flags/edit_card_flags.py` (supports exFAT, which this 256 GB
  card uses; needs `numpy`).
- **Camera bootflag vs card flags are separate.** `ML-SETUP.FIR` sets the
  camera one (persists in the body); the card ones are per-card.

**Process note:** this was recorded as a blocker for ~45 min of work today purely
because nobody ran `ls` on the card. Check the artifact before planning around
its absence.

**`SFDATA.BIN` is NOT required for the 6D2.** The `sf_dump` module
(`ml/modules/dev_tools/sf_dump/sf_dump.c`) only has stubs for DIGIC 4/5 bodies,
and qemu-eos's `magiclantern/ml_tests/cam.py:68` still reads `# TODO handle
SFDATA`. ROM0 + ROM1 are sufficient.

## 2. Ordered steps

### Phase A — build the loop (no camera needed except the ROM dump)
1. ~~Add deps to `/etc/nixos/configuration.nix`.~~ **DONE differently** — see
   `shell.nix` at the project root; enter with `nix-shell`. Deliberately NOT in
   the system config: these deps are project-only, and `shell.nix` is undone by
   deleting one file instead of a system rebuild + push. Verified in-shell:
   `arm-none-eabi-gcc` 15.2.1, `cc` 13.4.0, PIL 12.3.0, numpy 2.4.4,
   glib 2.88.1, pixman 0.46.4, gtk+3 3.24.52.
2. ~~Build ML for 6D2: `cd ml/platform/6D2.111` → `make`.~~ **DONE
   (2026-08-15 12:11).** Firmware version is confirmed 1.1.1 from the ROM
   itself, so `6D2.111` was the correct platform dir. Artifacts:
   `build/autoexec.bin` (243 KB), unstripped ELF `build/autoexec`, symbol table
   `build/6D2_111.sym` (1296 symbols), and a staged `build/zip/` containing
   `autoexec.bin` + `ML-SETUP.FIR`. The ELF and `.sym` are what make source-level
   gdb debugging possible in step 5.
3. ~~Dump ROMs from the camera.~~ **DONE** — see section 1. Files live in
   `roms/6D2/`, which is where the tooling's default `--rom-dir` resolves to.
4. **PARTIAL (2026-08-15).** qemu-eos builds and boots 6D2 stock firmware, but
   halts on a Canon assert before reaching the GUI — so the "reaches Canon menus"
   gate is *not* met. Details in §2a below. Command that works:

       cd /home/chris/ml6d2/qemu-eos/magiclantern
       python3 run_qemu.py 6D2 -q /home/chris/ml6d2/qemu-eos-build

   `-q` is required: `get_default_dirs` resolves via `realpath`, which follows the
   symlink farm back to the space-containing project path and finds no build dir.
   (Note: `run_canon_fw.sh` does not exist on the `qemu-eos-v4.2.1` branch —
   the entry point is `magiclantern/run_qemu.py`.)
5. Boot our own ML build inside QEMU (`-s -S` + gdb) — this is the debug rig.

### Build environment — three non-obvious traps (all hit and solved 2026-08-15)

**1. This project path cannot build QEMU.** `qemu-eos/configure:283` hard-rejects
any source or build path containing whitespace or a colon:

    if printf %s\\n "$source_path" "$PWD" | grep -q "[[:space:]:]"; then
      error_exit "main directory cannot contain spaces nor colons"

`/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/` fails on both counts.
Workaround in place: a space-free symlink farm at `/home/chris/ml6d2/`, which is
also exactly the sibling layout `ml_qemu/run.py: get_default_dirs` expects:

    /home/chris/ml6d2/
      qemu-eos                -> <project>/qemu-eos     (symlink)
      magiclantern_simplified -> <project>/ml           (symlink)
      roms                    -> <project>/roms         (symlink)
      qemu-eos-build/                                   (real dir)

This works because `configure` derives `source_path` via `pwd`, which returns the
*logical* path and so never resolves back through the spaces. Build and run qemu
from `/home/chris/ml6d2/`, not from the project dir. Undo with `rm -rf ~/ml6d2`.
The proper fix, if this ever gets fragile, is relocating the project to a
space-free path — which the global CLAUDE.md rule already asks for anyway.

**2. Default GCC is too new.** qemu-eos is forked from QEMU 4.2.1 (2019); this
system defaults to GCC 15.2, and GCC 14 made implicit-function-declaration and
int-conversion hard errors. `shell.nix` pins `gcc13Stdenv` (13.4.0) — the oldest
still in nixpkgs 26.05, since `gcc11Stdenv`/`gcc12Stdenv` were removed as
unmaintained. If 13 proves insufficient, pin an older nixpkgs via `fetchTarball`
rather than patching QEMU sources.

**3. `--disable-werror` is required.** Configure's `clock_adjtime` probe compiles
`return clock_adjtime(0, 0);`, but modern glibc declares that function
`__nonnull((2))`, so `-Wnonnull` fires and `-Werror` turns it fatal. The probe is
only testing whether the symbol exists — the flag is not masking a real defect.
Full working line:

**4. `--disable-sdl` is required on nixpkgs.** nixpkgs ships `sdl2-compat` as its
SDL2, which is a shim that `dlopen`s `libSDL3.so` at runtime. QEMU 4.2's configure
auto-detects it (`CONFIG_SDL=m`) and links it even though we asked for GTK; with
no SDL3 in the closure the binary aborts at startup with
`Failed loading SDL3 library.` before parsing any argument — note that string is
*not* in QEMU's source, it comes from the shim. SDL is never needed here:
`ml_qemu/run.py:160-165` only ever emits `-display gtk` or `-display none` and
raises on anything else. Disable it rather than adding SDL3 to the shell.

Full working configure line:

    ../qemu-eos/configure --target-list=arm-softmmu --enable-plugins \
        --disable-docs --enable-vnc --enable-gtk --disable-vte \
        --disable-werror --disable-sdl

Then: `make -j$(nproc) && make plugins && cp tests/plugin/libmagiclantern.so
arm-softmmu/plugins/`. Note the QEMU binary only runs *inside* `nix-shell` — its
libraries live in the shell closure.

**Do not flash our own build to the body yet.** `ml/platform/6D2.111/README.txt`
states this code "has never been tested on a real cam" and "boots in qemu, but
qemu doesn't get far for 6D2." QEMU first; the body only after step 4 passes.

## 2a. First boot result (2026-08-15) — how far QEMU gets

Stock 6D2 firmware, no ML. The rig works; the firmware stops at a Canon assert.

**Reached, in order:**

    [EOS] loading ROM0.BIN to 0xE0000000-0xE1FFFFFF   <- ROMs map correctly
    [EOS] loading ROM1.BIN to 0xF0000000-0xF0FFFFFF
    <<<<< Musa(PU0) Boot Ver 0.19 >>>>>               <- bootloader
    Loader
    K406 READY                                        <- K406 = 6D2 internal model code
    K406 ICU Firmware Version 1.1.1 ( 6.4.9 )         <- main firmware live, version matches
    [MPU] Received/Sending ... PROP_CARD2_EXISTS ...  <- MPU property exchange working
    [SD] Name: QEMU! Size: 247(7bc00)                 <- emulated card enumerated
    [FSU] efat_map_filesys / Attach SC 1 0 80 20 248

Both Cortex-A9 cores come up (SGI exchange between CPU0/CPU1 is present).

**Stops here:**

    [FSU] AllocateMemoryStrictly For Speed Class!!!
    ASSERT : Resource/./EstimatedSize.c, Task = RscMgr, Line 1521
    [STARTUP] ERROR ASSERT : Resource/./EstimatedSize.c, Task = RscMgr
    [STARTUP] ERROR ASSERT : Line 1521 / FALSE

This matches `platform/6D2.111/README.txt` ("boots in qemu, but qemu doesn't get
far for 6D2") — but now with an exact failure point instead of folklore.

**Leads, in priority order:**

1. The assert is in the resource manager's size estimation, immediately after the
   filesystem unit does a **speed-class** allocation for the emulated SD card.
   Suspect the emulated card geometry: 247 MB is small and QEMU-synthesised.
   Cheapest experiment: vary the card image size/geometry and see if the assert
   moves or clears.
2. Earlier warnings likely related, worth ruling in/out first:
   `[SDIO] Error` (x4), `[TA10] ERROR Irregular TotalSheets 0 !!`.
3. qemu-eos prints two known gaps for this model at startup —
   `[MPU] FIXME: using generic MPU spells for 6D2.` and
   `[MPU] FIXME: no MPU button codes for 6D2.` The missing button codes will
   block GUI navigation later even once boot completes, so they need doing
   regardless.

### Phase B — establish what is missing and why
6. Enumerate current 6D2 feature state from source, not from forum folklore:
   grep `platform/6D2.*/` for `CONFIG_*` flags, compare against a mature cam
   (e.g. `5D3.113`) and against `FEATURES.txt`/`Makefile.setup` gates.
7. For each missing feature, classify the reason:
   - **stub missing** (address not found in this ROM) — solvable by reversing,
   - **subsystem unported** (raw video / mlv_lite on D67) — large work,
   - **hardware/firmware differs** (new LiveView path, new EDMAC layout),
   - **just never enabled/tested** — cheapest wins, do these first.
8. Produce `FEATURE_MATRIX.md`: feature × status × reason × est. effort ×
   who upstream already touched it.

### Phase C — pick targets and ship
9. Start with the cheap high-value items the maintainer already flagged:
   MOV recording time limit, then focus-box hide / clean HDMI (issue #221).
10. Work each one as: reproduce in QEMU → find the Canon function/property →
    patch → test in QEMU → test on body → PR to `magiclantern_simplified`.
11. Only after those, evaluate porting 200D raw video to 6D2 (biggest prize,
    biggest cost, known "experimental quality" upstream).

## 3. Knowing what others have and are doing

Do this before writing any code, and keep it refreshed:
- `git log --since=1.year --stat` filtered to 6D2/D7 paths — tells you exactly
  who is active and on what.
- GitHub issues/PRs mentioning 6D2 / D7 / D678 (8 issues today; #221 open).
- `forum.magiclantern.fm` — public, fetchable, and the real technical record.
- ML wiki DIGIC pages for the D7 reversing state.

### Discord — the honest answer
There is no compliant way for me to "scan" the ML Discord on my own:
- Reading a server requires a **bot** account, and a bot only sees servers its
  admins invited it to. We can't invite one to someone else's server.
- Driving *your* user account/token programmatically (self-bot, chat exporters
  using a user token) is a Discord ToS violation and can get your account
  banned. Not doing that.

What actually works, in order of effort:
1. **Use the public sources instead** (forum + GitHub). Nearly everything
   technical on Discord is restated there.
2. **You paste, I index.** Copy the relevant `#digic678` / `#dev` channel
   scrollback into `discord/` as plain `.md` files; I index and search them
   locally and extract "who knows what".
3. **Your own server, official bot.** If you create a Discord server and a bot
   (or use an existing Discord MCP server with your bot token), I can read and
   post there — useful as a workspace, not as a window into ML's server.
4. **Ask directly, as yourself.** I draft the message, you send it.

Who to ask — **corrected 2026-08-15 from `git log`, not from guessing.** The
earlier list in this section was wrong on two counts:

- **`reticulatedpines` = `stephen-e`.** Same person: `git log --format='%an <%ae>'`
  shows both names sharing one GitHub noreply address. He authored 34 of the 37
  commits touching `platform/6D2.*`. He is the correct and essentially only
  contact for the D67 port.
- **`WalterSchulz` has touched nothing 6D2-specific.** His only commits in three
  years are DXO dynamic-range data in `src/raw.c` for the R5 and 80D. He is a
  testing/support voice on the forum, not a code owner here — do not route
  technical 6D2 questions to him.
- **Issue #221 was opened by `evgeniimv`** (2025-08-31), not WalterSchulz.
  WalterSchulz's "clean HDMI is the top wish" remark is in issue **#155**, which
  motivated #221.
- For the MOV time limit specifically, the reference implementation is the
  **200D** (`platform/200D.101`), authored by the same maintainer.

## 4. Definition of done for this plan's first milestone
- QEMU boots stock 6D2 firmware **and** our ML build.
- `FEATURE_MATRIX.md` exists with a reason attached to every missing feature.
- One upstream-quality patch opened for a cheap target.
