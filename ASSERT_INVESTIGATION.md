# 6D2 QEMU boot investigation — `ASSERT : Resource/./EstimatedSize.c, Task = RscMgr, Line 1521`

Date: 2026-08-15. Firmware 1.1.1, qemu-eos branch `qemu-eos-v4.2.1`, stock Canon boot (`boot=0`, no ML loaded).

Six investigation lenses (build, qemu SD model, ROM disassembly, DIGIC 7 sibling comparison, upstream git archaeology, live QEMU experiments), one hypothesis-ranking pass, one adversarial pass. All claims below are marked **observed** (a command was run, a log line exists) or **inferred**.

---

## 1. Summary

- **The root cause is not established.** What *is* established is the proximate trigger, at instruction level: the assert is the default arm of a switch on a movie frame-rate field, and the field holds 81, which is not one of the eight legal values. Why the field holds 81 has three candidate explanations and none has been tested by running anything.
- **The assert site is pinned exactly.** `EstimatedSize()` at ROM0 `0xE0202312`; the failing compare chain at `0xE0202372`–`0xE020247E`; the assert call at `0xE020248C`. Legal values are {2000, 2398, 2400, 2500, 2997, 5000, 5994, 11988} = fps × 100. **Observed** (disassembly of roms/6D2/ROM0.BIN).
- **The SD card is not the cause.** Eleven QEMU boots varied capacity 8 MiB → 32 GiB (crossing the SDHC threshold), FAT16 vs FAT32, and 4/16/32/64 KiB clusters. The assert fired identically in every one. Removing the filesystem entirely produced a *different, earlier* assert — so a mountable card is a **gate** on reaching EstimatedSize, not a cause of it. **Observed.**
- **This is a known upstream failure with a known band-aid, and 6D2 is the only DIGIC 7 body that never got it.** 77D, 80D, 750D and 760D all ship a GDB breakpoint forcing the value to `0x7D0` (= 2000 = the first legal case). 200D has the same patch, commented out and unvalidated. The 6D2 equivalent has now been written but **never run**.
- **ML step A2 succeeded.** `autoexec.bin` builds clean for 6D2.111 (243,136 bytes) once `ARM_BINPATH` is set. Two unrelated blockers stop the *emulator* ML path: the bundled `lua` module fails under GCC 15, and `zip` is missing from shell.nix, so no ML disk image can be produced.

---

## 2. ML build status (plan step A2)

**Result: builds.** `build/autoexec.bin`, 243,136 bytes, exit 0 from a clean tree. **Observed.**

Artifact: [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/platform/6D2.111/build/autoexec.bin](ml/platform/6D2.111/build/autoexec.bin) — md5 `0c159e7a5b917ad9ffc05816bff435a5`, embedded payload `magiclantern.bin` = 239,856 bytes, version string `Magic Lantern 2026-08-15.6D2.111 / Commit: 3f24042a4 dev`. The `xor_chk` footer checksum was applied (footer magic low word `13 ff 2f e1` intact at 0x3b5b0, high word replaced by `0x0a60e6c5`).

### The one undocumented requirement

[/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/Makefile.globals](ml/Makefile.globals) line 17: `ARM_BINPATH ?= /usr/bin`, consumed at line 20 as `CROSS_COMPILE = $(ARM_BINPATH)/arm-$(ARM_ABI)-`. On NixOS that path does not exist. Working incantation:

    export ARM_BINPATH=$(dirname $(which arm-none-eabi-gcc))

Worth folding into `shellHook` in [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/shell.nix](shell.nix).

### What broke

**(a) `make` with no target fails — bundled Lua, GCC 15 header collision.**

    make[2]: *** [../../modules/Makefile:134: build/lua/ldo.o] Error 1
    setjmp.h:15:48: error: expected declaration specifiers before '__dead2'

Chain: `modules/lua/lua/ldo.c:13` includes `<setjmp.h>`; `modules/lua/Makefile:34` puts `-Idietlibc/include/` ahead of the system includes; dietlibc has no `setjmp.h`, so newlib's is used; newlib 15's `setjmp.h:15-16` uses `__dead2` / `__returns_twice` from `<sys/cdefs.h>`; dietlibc *does* ship a `sys/cdefs.h` and it wins the search, and it defines neither macro. **Observed.** Proven out-of-tree without editing sources: re-running the exact failing gcc line with `-D__dead2=__attribute__((__noreturn__)) -D__returns_twice=__attribute__((__returns_twice__))` compiles `ldo.c` to a 7,492-byte object, exit 0.

Scope: cosmetic for this camera. 22 of 23 modules build; lua is the only failure and is not in [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml/platform/6D2.111/modules.included](ml/platform/6D2.111/modules.included) (which lists only bench, dual_iso, file_man, mlv_lite). But `platform/Makefile:251` requires the whole default module set before zipping, so plain `make` still dies.

**(b) `zip` is absent from the nix shell**, so `build/magiclantern.zip` and therefore `make disk_image` cannot run. `platform/Makefile:202-204` shells out to `zip`; `shell.nix` packages list contains only gcc-arm-embedded and python3(pillow, numpy). **Observed.** This is what currently prevents booting ML under QEMU at all.

**Note a disagreement with the task brief:** spaces in the project path do **not** break the ML build — every ML makefile path is relative (`TOP_DIR = ../..`). The symlink farm is required for qemu-eos's `configure` only. **Observed** (the successful build ran in the space-containing directory).

Other GCC 15 diagnostics across 104 compile invocations: one pre-existing upstream `#warning` in bundled TCC, and two `LOAD segment with RWX permissions` linker warnings that are expected for `-N` bare-metal links. Nothing load-bearing.

---

## 3. What the experiments actually showed

All runs are stock Canon firmware, `boot=0`. Logs in `/tmp/claude-1000/-home-chris-Vibe-Coding-6D-Mark-II-Magic-Lantern-6D2/97eb1d5b-2948-4584-a307-57ec6310a0cc/scratchpad/` (outside the workspace, so plain text — files `exp-*.log`).

| Run | Card | Firmware reported | Result | Max DryOS msg |
|---|---|---|---|---|
| exp-baseline | stock 247.5 MiB FAT16 | `Size: 247(7bc00)` | assert 1521 | 371 |
| exp-harness-ctl | stock, copied to scratch rundir | `Size: 247(7bc00)` | assert 1521 | 374 |
| exp-fat16-8m | 8 MiB FAT16 | `Size: 8(4000)` | assert 1521 | 376 |
| exp-fat16-64m | 64 MiB FAT16 | `Size: 64(20000)` | assert 1521 | 370 |
| exp-grow-orig-2g | 2 GiB, original FS grown | `Size: 2048(400000)` | assert 1521 | 368 |
| exp-fat32-2g | 2 GiB FAT32 | `Size: 2048(400000)` | assert 1521 | 373 |
| exp-fat32-8g | 8 GiB FAT32 | `Size: 8192(1000000)` | assert 1521 | 367 |
| exp-fat32-32g | 32 GiB FAT32 | `Size: 32768(4000000)` | assert 1521 | 369 |
| **exp-nofs-248m** | **248 MiB, no partition table** | `Size: 247(7bc00)` | **assert 1521 never fires** — instead `[FSU] ERROR fsuGetPart : not supported` then `ASSERT : SystemIF::KerRLock.c, Task = ShtCap, Line 205` | 378 |
| exp-sdcf-trace | stock, `-d sdcf` | — | assert 1521, plus full SD command trace | — |
| exp-dbgmsg | stock, `-d debugmsg` | — | assert 1521, plus full DryOS message log | — |

**Observed** in all of the above. Key derived facts:

- **Capacity is genuinely reaching the firmware and genuinely does not matter.** The `Size:` line tracks the qcow2 virtual size 1:1 across a 4096× range that crosses the 1 GiB SDHC threshold (`hw/sd/sd.c:307-311` only sets the OCR capacity bit above 1 GiB, so the small images enumerate as SDSC with CSD v1.0 and the large ones as SDHC). Both classes assert identically.
- **Cluster size reaches the speed-class code and changes its numbers, and still nothing moves.** `[FSU] Attach SC` fields tracked cluster size correctly: 16 KiB → `1 0 80 20 248`; 32 KiB → `1 0 40 10 8190`; 64 KiB → `1 0 20 8 32764`; 4 KiB → `1 0 200 80 10`.
- **The no-filesystem run is the decisive control** and also a caveat: it diverges at a *different* assert (`KerRLock.c:205`, task ShtCap, core 1) that appears nowhere in the normal boot, so it proves "no FS → never reaches EstimatedSize" but is not a clean single-variable control.
- **`[SDIO] Error` ×4 is benign noise.** exp-sdcf-trace.log:196-210 identifies them: CMD0 ×2, CMD52, CMD5 — SDIO-combo probes a plain SD card is supposed to reject. Constant across all 11 runs including the no-FS one. Emitted unconditionally from [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/qemu-eos/hw/eos/eos.c](qemu-eos/hw/eos/eos.c) lines 5060-5062 with no command number, which is why the bare log is uninformative.
- **`[TA10] ERROR Irregular TotalSheets 0 !!` is unrelated** — DryOS message ~229, ~70 messages *before* SD init (298), emitted by PropMgr (`e050d4e7`), and immediately followed by `ChangePropCBR ShotsPlan 2 / TotalSheets 2`, i.e. the value does get set. **Observed.**
- **Log line count is not a progress proxy.** Runs reaching the identical assert range from 198 to 2758 lines because QEMU aggregates repeated MMU traces differently. Use the DryOS message counter (all runs land at 367–378). **Observed.**

### Explicitly NOT tested, and why

| Not tested | Why |
|---|---|
| The `0x7D0` GDB workaround for 6D2 | The patch script was written but never executed. This is the single cheapest decisive test and it is still outstanding. |
| Populating QEMU's SD Status register (ACMD13) with a real SPEED_CLASS / AU_SIZE | Requires editing `hw/sd/sd.c:491` and rebuilding QEMU; source edits were out of scope for the agent that ran QEMU. |
| Adding a Movie-group MPU spell, or 6D2-specific spells generally | Same reason — requires editing `hw/eos/mpu_spells/`. Also, no 6D2 MPU spells have ever been captured by anyone. |
| exFAT card | The environment blocks filesystem-creation commands for agents. Prior is overwhelming that it behaves like FAT16/FAT32. |
| ML booted under QEMU (`boot=1`) | Blocked by the missing `zip` (section 2b) — no disk image can be built. |
| `dedicated_movie_mode = 1` for 6D2 | Requires a QEMU rebuild; refuted statically first (section 4). |
| 200D / 77D / 800D comparison boots | No ROM dumps for those bodies are present in `roms/`. |

---

## 4. Hypotheses, ranked, with adversarial verdicts

### H1 — Missing MPU "Movie group" spell leaves the frame-rate field at 81 → **SPLIT: mechanism confirmed, root-cause attribution refuted**

**Claim.** The generic MPU spell set never writes PROP_MOVIE_PARAM, so a movie-parameter struct keeps a bogus frame-rate field (81); RscMgr passes it to `GetEstimatedSizeOfMovie` when the card mounts; the switch matches nothing and asserts.

**Support (all independently re-verified by the skeptic, so this part stands):**

- Disassembly of ROM0 at `0xE0202312`. `0xE020231C mov r6,r0`; `0xE0202372 ldr r0,[r6,#8]`; compare chain against 2000/2400/2398/2500/2997/5000/5994/11988; `0xE0202480 movw r2,#1521`; `0xE0202484` → `0xE02023F0` `"Resource/./EstimatedSize.c"`; `0xE0202488` → `0xE0202464` `"FALSE"`; `0xE020248C bl 0xE0617620` (DryOS assert, r2 = line). **Observed.**
- The function is `GetEstimatedSize(struct*, DWORD *pdwSize, DWORD *pdwFrameRate, GopStruct *pdwGopStruct)` — proven by the assert strings at lines 1504/1505/1506: `"pdwSize != NULL"` (0xE0202424), `"pdwFrameRate != NULL"` (0xE0202434), `"pdwGopStruct != NULL"` (0xE020244C). So the field at +8 really is a frame rate, and the eight constants really are fps×100. **Observed.**
- The earlier switch (line 1511, on field +4 = resolution index) passes, which is why only 1521 fires — matching the log exactly. **Observed.**
- Exactly three callers, all passing the struct **by value**: `0xE0202532 / 0xE020257C / 0xE02025C2`, each doing `push {r0,r1,r2,r3}; push {lr}; sub sp,#20; add r0,sp,#24; bl 0xE0202312`. **Observed.**
- Cross-model: ml commit `39a7c8378` (`contrib/qemu/HACKING.rst:576`) records the 80D callstack for the same assert as `0xFE19B1A9(0, 1, 51, 8000003b)` — all four words identical to the 6D2's logged tuple. `0x51` = 81. **Observed.**
- `0x7D0` = 2000 = the first case of this switch. That closes upstream's own open question about why that magic number was chosen. **Inferred, but strongly.**

**Skeptic's verdict: refuted as a root cause.** The named cause is contradicted by its own citation. [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/qemu-eos/hw/eos/mpu_spells/known_spells.h](qemu-eos/hw/eos/mpu_spells/known_spells.h) line 174 records the `02 0f` "Movie group" with property ID `0xCCCCCCCC` — the file's placeholder for *unknown*. Nothing in the tree says the Movie group carries PROP_MOVIE_PARAM. The tree's only mapping to that property is [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/qemu-eos/hw/eos/mpu_spells/known_spells.py](qemu-eos/hw/eos/mpu_spells/known_spells.py) line 76, spell `01 4e`. And the models that *do* carry `01 4e` in their Init spells (550D/600D/60D/5D2) are exactly the DIGIC 4 bodies that boot fine under generic.h *without* it. The claimed correlation does not exist. Additionally `generic.h` omits ~30 other spells, so singling out one with no experiment is arbitrary; and the run was never done (the patch file says "UNVERIFIED AT TIME OF WRITING: not yet run").

**Reconciliation produced while assembling this report (new, my own commands):** the two skeptics disagreed about what the debugmsg line `PROP_MOVIE_PARAM 0 1 81 -2147483589` (exp-dbgmsg.log:1017) actually is. I resolved it by dumping ROM0 around `0xE091D348`. **Observed:**

    0xe091d350  0x4e        <- mpu_sub
    0xe091d354  0x80000039  <- prop id (known_spells.py:76, "01 4e")
    0xe091d358  0x0         <- default VALUE
    0xe091d35c  0x1         <- mpu class
    0xe091d360  0x51        <- next record's mpu_sub
    0xe091d364  0x8000003b  <- next record's prop id (known_spells.py:79)

Records are 16 bytes, `{mpu_sub, prop_id, default, mpu_class}`; across the table the class field only ever takes the values 1 and 9, matching known_spells.py's `01 xx` / `09 xx` prefixes (109 records scanned: 90 class-1, 19 class-9). The tuple `{0, 1, 0x51, 0x8000003b}` occurs exactly once in the whole 32 MiB ROM, at `0xE091D358`.

So the logged four words are **PROP_MOVIE_PARAM's one-word default (0) plus three words of over-read** into adjacent registry metadata — the DebugMsg format string at `0xE04EBCA0` is literally `"PROP_MOVIE_PARAM %d %d %d %d"`, and the copy at `0xE04EB99E` moves **32 bytes** out of a property whose registered default is 4 bytes. **Observed.**

That corrects both skeptics in opposite directions:
- Against the H2 skeptic: the log line is *not* an unrelated property's record. It starts precisely at PROP_MOVIE_PARAM's own default field, and the 80D callstack shows the same four words arriving as the by-value struct argument. So `struct+8 = 81` is real, not a coincidence of formatting.
- Against H1 as stated: 81 is not "the movie frame rate left at a stale default". It is the MPU sub-command byte of the *next* registry entry, read past the end of a 1-word property. The defect is a length mismatch — a 4-word consumer reading a 1-word property buffer — which on real hardware is masked because the MPU overwrites that buffer with a genuine multi-word payload (compare [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/qemu-eos/hw/eos/mpu_spells/100D.h](qemu-eos/hw/eos/mpu_spells/100D.h) line 33, a real captured PROP_MOVIE_PARAM spell: `{0, 2, 0x1E, 0xF, 0, 2, 0, 0}`).

**Net standing:** the proximate trigger is proven. "Which missing MPU spell would have filled that buffer" is still open — `01 4e` is now the better-evidenced candidate than `02 0f`, but neither has been tested. **Inferred.**

### H2 — 81 is a valid raw encoding that some init step should have converted → **REFUTED**

Killed on four grounds, all **observed**: (1) the consumer performs no conversion — the value is loaded from struct+8 and compared to raw fps×100 constants; (2) the eight legal values never appear as an adjacent table anywhere in ROM0 (only the pair 2400,2500 once, at `0xE19C10F4`), so there is no index→fps lookup and 81 cannot be an index; (3) there is no struct to initialise — the "struct on stack" is the compiler's argument spill block, materialised four instructions before the call, so no subsystem can be failing to init it; (4) the report I fold in above shows 81 is registry metadata, not any movie encoding.

Note the 200D comment that motivated this hypothesis was quoted at the wrong line and stripped of context: [/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/qemu-eos/magiclantern/cam_config/200D/patches.gdb](qemu-eos/magiclantern/cam_config/200D/patches.gdb) line 20, inside a block the file itself labels "experimental patches / they probably do more harm than good" (lines 8-9), entirely commented out.

### H3 — `dedicated_movie_mode = 0` for DIGIC 7 bodies → **REFUTED, and changing it would be wrong**

The two "runtime consumers" cited do not support the claim. `hw/eos/mpu.c:1314` gates on `== -1`, so 0 and 1 are indistinguishable there. The only site where 0 vs 1 differs, `mpu.c:1067`, sits inside `mpu_send_keypress`, whose only callers are the QEMU keyboard handler (`eos.c:1664-1667`) and `mpu_send_powerdown`. `run_qemu.py` sends no keystrokes, so the code is unreachable before the assert. **Observed.**

The supporting correlation is also false: ten of the twenty cameras in `ml_tests/cam.py`'s `gui_cams` have `dedicated_movie_mode = 0` (5D2, 5D3, 6D, 50D, 70D, 650D, 700D, 100D, EOSM, EOSM2), and every DIGIC 5+ entry in `model_list.c` is 0. The field tracks whether the mode dial has a dedicated Movie position, i.e. camera generation. Setting it to 1 for the 6D2 would assert something untrue about the hardware. **Observed.**

### H4 — Zeroed SD Status register (ACMD13): SPEED_CLASS = 0, AU_SIZE = 0 → **MOSTLY REFUTED**

The mechanism is real and was ranked first by three independent static lenses: `hw/sd/sd.c:491` `memset(sd->sd_status, 0, 64);`, only the bus-width nibble is ever written (`sd.c:1482-1483`), and the firmware really does issue ACMD13 (exp-sdcf-trace.log:249-253 — CMD55, CMD13, then a 64-byte read). **Observed.**

But the disassembly kills it as the cause of *this* assert: line 1521 tests one thing, a frame rate against eight constants, with no arithmetic involving allocation units or capacity anywhere in `0xE0202312`–`0xE0202530`. And the speed-class path demonstrably succeeded — `[FSU] AllocateMemoryStrictly For Speed Class!!!` is a post-allocation DebugMsg (alloc `0xE02AA4E4`, store `0xE02AA4EA`, message `0xE02AA4EC`), and its derived parameters tracked cluster size correctly across four experiments while the assert stayed identical. **Observed.** Caveat worth keeping: there is no test of `r0` between the allocator call and the message, so "successful allocation" is inferred from the absence of an error path, not from a check.

Speed class supplies the assert's *timing*, not its cause.

### H5 — Card capacity / filesystem type / cluster geometry → **DEAD**

Refuted empirically by eleven boots (section 3). Do not spend another run on card variation.

### H6 — Missing per-model memory region or unemulated ROM→RAM copy → **unlikely, cheap to close**

Precedent is real: qemu-eos `c1f0e49e86` "7D2: add required mem region to avoid assert", `6822bec04d` "60D: define rom0 size, prevents mem read assert", and 200D needs `patch_200D()` at `hw/eos/eos.c:1918-1929` to fake a ROM→RAM copy nobody has identified. 6D2 has no such hook. **Observed.**

Against it: the boot reaches DryOS message 371 with no memory-access aborts, the 6D2 already executes natively in the `0xDF00xxxx` region (its own debugmsg breakpoints sit at `0xDF006E6C` / `0xDF008CE6` / `0xDF008284` / `0xDF00A1FA`), and the same four bad words appear on the 80D, a DIGIC 6 body with a completely different memory map — a memory-mapping defect would not reproduce byte-for-byte across generations. **Inferred.**

---

## 5. Recommended next actions, cheapest decisive test first

1. **Run the workaround.** The script is already written: `/tmp/claude-1000/-home-chris-Vibe-Coding-6D-Mark-II-Magic-Lantern-6D2/97eb1d5b-2948-4584-a307-57ec6310a0cc/scratchpad/6D2-EstimatedSize.gdb`. Break at `0xE0202312`, `set *($r0 + 8) = 0x7d0`, continue. Cost: one boot, no rebuild. Pass = the boot walks past the assert; the target string to watch for is `[STARTUP] startupInitializeComplete`, which is what qemu-eos's own LogTest uses to define a successful boot ([/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/qemu-eos/magiclantern/ml_tests/log_test.py](qemu-eos/magiclantern/ml_tests/log_test.py) lines 26-74). Note `run_qemu.py --gdb` starts QEMU suspended on port 1234 and does **not** auto-source `cam_config` scripts (`run_qemu.py:114-117`), so drive it by hand — same as 77D. This also formally buries H4: if forcing the field clears the assert while SD Status is still all zeros, SD Status was never load-bearing.
2. **In the same session, print the field before patching** (`printf "%d\n", *($r0+8)`). If it prints 81, the whole chain from ROM registry → property buffer → by-value struct is confirmed end to end, which is currently the last inferred link. If it prints something else, the 81 evidence was a coincidence and H1's remaining support collapses.
3. **Record the next wall.** Expect boot to stop somewhere else. That is still progress; capture it the same way (`-d debugmsg`, DryOS message index, not line count).
4. **Unblock the ML-under-QEMU path** — two small independent fixes: add `zip` to `shell.nix`, and either reorder `-Idietlibc/include/` in `modules/lua/Makefile:34` or add the two missing macros to `modules/lua/dietlibc/include/sys/cdefs.h`. Then `make disk_image` and `run_qemu.py 6D2 --boot=1` becomes possible for the first time. Consider rebuilding with `CONFIG_QEMU=y` for that run (`platform/Makefile:36` defaults it to `n`).
5. **Only if steps 1-3 leave the root cause open:** test the `01 4e` MPU spell hypothesis by adding a PROP_MOVIE_PARAM reply to `generic.h` (payload shape from 100D.h:33) and rebuilding QEMU. This is the honest fix rather than the band-aid, but it costs a rebuild and is guesswork without captured 6D2 spells.
6. **Optional, cheap, unrelated to the assert:** add `known_cams["6D2"] = ["879cead703398cb4928cf6e9b5969504"]` (ROM0 md5, **observed**) plus a `qemu_expected_lines` entry, to turn this from an untracked failure into a tracked red test. Note the suite is currently unrunnable for *every* camera: `ml_tests/cam.py:93-101` looks for `platform/<CAM>/sd.qcow2` while `make disk_image` and `run_qemu.py` both use `platform/<CAM>/build/sd.qcow2` — a stale path left behind by qemu-eos commit `4b667a1d3c`.

**Do not do:** vary the card further (dead, section 3); set `dedicated_movie_mode = 1` (refuted and wrong, H3); attempt the 77D-style `set $r0 = 0x7D0` at function entry on 6D2 — `0xE0202372` reloads r0 from `[r6,#8]`, so an entry-time register write is overwritten. Use the 200D form (write through the pointer) or break at `0xE0202374` after the load.

---

## 6. Open questions and gaps

- **Why the property buffer contains what it contains.** Confirmed: PROP_MOVIE_PARAM's registered default is one word = 0, and a 32-byte copy over-reads adjacent registry records. Unknown: whether a real 6D2 MPU payload would land there (no 6D2 spells have ever been captured — `hw/eos/mpu.c` lists no DIGIC 7 model at all), and whether the over-read is a Canon bug masked on hardware or intended behaviour with a differently-sized real payload.
- **The runtime link from the property buffer to the struct is inferred, not traced.** The caller loads the struct from `ctx+0x180` (`0xE00E3A42 add.w r0,r5,#384`; `0xE00E3E32 ldr r0,[sp,#224]`; `ldmia r0,{r0,r1,r2,r3}` → `bl 0xE0202532`). PropMgr's cache is at RAM `0x6C024`, and a ROM-wide scan finds that constant referenced nowhere else. Nobody has watched the bytes move. Step 2 above closes this.
- **Whether 0x7D0 is a *correct* value or merely a value that gets past the check.** It is an 80D-derived magic number copied verbatim to 750D/760D/77D with no justification recorded in any commit message.
- **Whether 200D / 77D / 800D reach the identical assert in this build.** Strongly implied by their shipped workarounds, but no ROMs for those bodies exist here and none was run.
- **Whether the 6D2 needs an equivalent of `patch_200D()`.** It appears to perform that ROM→RAM copy natively, but this was not verified by execution.
- **The `[FSU] Attach SC` field semantics.** Only the trailing value is confidently identified (a cluster total). The helper functions `0xE0311852` / `0xE031176C` were never named, so the middle fields are inferred from the arithmetic (division by `sectors_per_cluster × bytes_per_sector`) rather than from symbols.
- **Whether the built `autoexec.bin` actually works.** It compiles, links and is checksummed. Nothing was flashed and nothing was run. `ml/platform/6D2.111/README.txt` still stands: "this code has never been tested on a real cam". Separately, GCC 15.2.1 compiling a 2010s codebase cleanly under `-Werror` is not evidence of correct codegen, and no older ARM toolchain is present to diff against.
- **Whether ML's boot path diverges before RscMgr reaches the assert.** Untestable until the `zip` and lua blockers are cleared.
- **exFAT**, and any indirect (function-pointer) callers of `0xE0202312` — the caller list of three is complete only for direct BL/B.W.
- **No network access this run**, so the Magic Lantern forum and the pre-git Bitbucket history (cited by `HACKING.rst` for the original 80D patches, and by `generic.h` for how MPU spells are captured) could not be consulted.
