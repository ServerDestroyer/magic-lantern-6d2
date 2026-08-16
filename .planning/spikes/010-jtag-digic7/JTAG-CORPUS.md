# JTAG-scoped knowledge corpus (plan B4)

**Scope.** What the community already knows that is relevant to the 6D2
JTAG / hardware-in-the-loop effort: JTAG, DIGIC 6/7/8 debug, MPU/ERR80/
watchdog, UART, and PTP memory access. Each entry is a **finding + a
citation**, not copied bodies of text. Forum citations are ML/CHDK topic
numbers (live site is Cloudflare-blocked; retrieve via Wayback). In-repo
citations are workspace-relative paths.

Companion doc: kitor's DIGIC 8 method distilled in `KITOR-DIGIC8-METHOD.md`
(same folder). This corpus is the surrounding context; that doc is the
step-by-step.

---

## 1. JTAG / OpenOCD on DIGIC

- **DIGIC 8 IDCODE is the standard ARM CoreSight DAP `0x4ba00477`, single TAP,
  irlen 4, no ICEPICK.** kitor's working OpenOCD dual-A9 SMP config is
  reproduced in `KITOR-DIGIC8-METHOD.md`. — ML forum topic **27350** (kitor,
  2025-08/09), via Wayback `web/20260206101918/…topic=27350.0`.
- **DIGIC 5 IDCODE is a TI ICEPICK JRC `0x1b93a02f` (mfg TI), 2 bp/wp units,
  and needs an ICEPICK `tapenable` event to expose the DAP.** So the TAP
  topology is NOT constant across DIGIC generations — a DIGIC 7 scan must be
  read fresh, not assumed. — CHDK forum topic **13408** "DIGIC 5 JTAG"
  (Versaloon adapter, OpenOCD 0.10.0).
- **nTRST is active-low and tied/pulled low on both DIGIC 5 and 8; you pull it
  to VCC to bring the TAP up.** kitor didn't even cable it to the probe on the
  SX740. — topics 27350, 13408.
- **Resistance-signature pin-ID (the reusable discovery method):** TDI/TCK/
  TMS/TDO read 100–200 kΩ to GND (~128 kΩ EOS R, ~160 kΩ SX740); /TRST reads
  ~10 kΩ pull-down; while running /TRST+TDO are low, TDI/TCK/TMS high. — topic
  27350 (kitor).
- **No DIGIC 6 or 7 JTAG/SWD connection has ever been published** — no EOS
  IDCODE, no EOS pinout with a confirmed live session. nikfreak (2016) bought
  six older EOS bodies "to JTAG our EOS cams" and never reported a result;
  kitor's DIGIC 8 success is on a PowerShot. — `docs/jtag-research.html`
  (Open Leads / EOS attempts section), citing ML forum history.
- **Prior EOS-generation JTAG existed only up to DIGIC 4** (3.3 V, the single
  measured DIGIC I/O voltage in the public record). Do not carry 3.3 V forward
  — DIGIC 6–8 core logic is 1.8 V. — `docs/jtag-research.html` (Safety).
- **Adapter reality:** kitor used an Altera USB Blaster clone (OpenOCD:
  "adapter doesn't support configurable speed"). 1.8 V compatibility is the
  hard requirement. Reference dual-A9 OpenOCD configs: `zynq_7000.cfg`,
  `imx6.cfg` (bundled with OpenOCD). — topic 27350; OpenOCD distribution.
- **Tooling for pinout brute-force:** JTAGulator / JTAGenum; the nada-labs
  writeup "Finding JTAG on a Canon ELPH100HS (IXUS115)" (2014) is the closest
  Canon-specific worked example. — `docs/jtag-research.html` (References).

## 2. DIGIC 6/7/8 debug channels other than JTAG

- **UART is the cheapest firmware-cooperative channel and reads out of the box
  with a 3.3 V FTDI.** a1ex confirmed a plain 3.3 V receiver registers the EOS
  M's 1.8 V ICU TX highs; only *driving* the camera's RX needs a divider/
  shifter. 115200 8N1. — ML forum topic 7531; `docs/jtag-research.html`.
- **`drysh` / `Mon*` RPC shell exists in ROM** (interactive DryOS shell,
  demonstrated live over UART on family bodies) but its reachability on a
  stock 6D2 is unproven. — `.planning/spikes/011-hardware-in-the-loop/README.md`
  §5.
- **QEMU + GDB is the zero-risk debug surface today:** stock 6D2 firmware
  completes startup in qemu-eos (commit `85ad7df`); `pmemsave`/`xp`, `-d
  io/io_log/calls/tasks`, and `debugmsg.gdb` answer nearly all open
  `PU1_INVESTIGATION.md` / `ASSERT_INVESTIGATION.md` questions at the desk. The
  emulator cannot validate its own guessed model fields — that residue is what
  needs silicon. — `.planning/spikes/011-hardware-in-the-loop/README.md` §3.

## 3. MPU / ERR80 / watchdog

- **ICU vs MPU, the core distinction:** the **ICU** is the main CPU running
  DryOS; the **MPU** is a separate microcontroller handling buttons/power/
  mechanical control. On an **EOS** body, if the ICU stops answering, the MPU
  **throws ERR80 within seconds**. **PowerShots have no MPU**, so a locked ICU
  just stalls/reboots. — a1ex & g3gg0, ML forum topic **22030** "JTAG on DIGIC
  chips" (2018).
- **This is why kitor's PowerShot JTAG success does not guarantee a stable
  EOS session:** halting the ICU on a 6D2 will likely trip the MPU ERR80 fault.
  The halt works; *staying* halted is the open EOS-specific problem. —
  topic 22030; spike 010 README §2.
- **DIGIC 5 had a suppressible ICU-side watchdog at `0xC0410000`** (write zero
  via CHDK to disable). **No DIGIC 7 MPU-side fault/suppression address is
  published** — finding it statically in ROM0 is spike 010 Phase 0's one
  genuinely new research task. — CHDK lore / `docs/jtag-research.html`; spike
  010 README §2 & Phase 0.
- **Same failure mode reachable without JTAG:** an unguarded `GetMemory` read
  of the wrong MMIO (pop a FIFO, hang a bus) drives the ICU unresponsive → MPU
  ERR80 — identical symptom to a JTAG halt. Relevant discipline for the PTP
  debugger path. — `.planning/spikes/011-hardware-in-the-loop/README.md` §2.

## 4. UART / service-port connectors

- **The 6D2 external service connector is the FZC-8 family** (JST
  08FZC-SM1-GAN-TB, claimed), shared across 5D4/200D/R/RP/250D. Family pinout
  (topic 7531, posts 38–43): **pins 2/3 = ICU RX/TX at 1.8 V, pin 4 = GND,
  pins 6/7 = MPU TX/RX at 3.3 V.** **Never measured on an actual 6D2** —
  inherited from the family; multimeter-verify before driving. — ML forum
  topic **7531**; `.planning/spikes/011-hardware-in-the-loop/README.md` §4.
- **The port carries two independent UARTs at two different voltages** (ICU
  1.8 V + MPU 3.3 V); early probing of a 5D3 with an FTDI at 3.3 V/115200 read
  TXDICU / TXDFPU / TXDMPU on separate pins. — topic 7531 (coon/Alex).
- **Published adapter hardware exists:** `coon42/magic-lantern-dev-kit` on
  GitHub carries KiCad sources + orderable gerbers for 8-pin and 13-pin
  service-connector cables (coon's OSH Park design, ~$6/3). — GitHub
  `coon42/magic-lantern-dev-kit`; topic 7531.
- **kitor's own per-model UART/JTAG pad photos** live at `https://kitor.pl/eos/`
  (e.g. `eos/img/5d3_uart.jpg`, `eos/jtag/jtag_eosr.jpg`). — linked from
  topics 7531 and 27350.
- **6D2 physical access is undocumented:** FZC-8 is 0.5 mm pitch (no
  off-the-shelf mate); a 2025 teardown shows the rear cover is screws-only with
  no visible debug hole. `uart_printf` is already stubbed at
  `platform/6D2.111/stubs.S:284` (`0xe04eb7a0`). — spike 011 README §4.

## 5. PTP memory access (CHDK path)

- **The CHDK PTP memory path is generic and already ported into ML.**
  `PTP_CHDK_GetMemory` / `SetMemory` / `CallFunction` under custom opcode
  `0x9999`; `GetMemory` reads via a raw `*(uint32_t*)address` word loop. — in
  repo: `ml/src/ptp-chdk.c` (GetMemory ~line 115, SetMemory ~193, CallFunction
  ~297); upstream CHDK `chdkptp` / `ptpcam`.
- **It is dead on the 6D2 for exactly one reason: the `ptp_register_handler`
  firmware stub is missing.** Every DIGIC 6/7/8 body in the tree has zero live
  PTP stub; the 200D placeholder (`platform/200D.101/stubs.S:509`) is a
  byte-identical copy-paste of the DIGIC 4 `50D.109` scaffold, not a
  measurement. — `.planning/spikes/002-stub-verification/README.md`,
  `.planning/spikes/011-hardware-in-the-loop/README.md` §2.
- **6D2 candidate stub `0xE04BF152` (INFERENCE, not proof):** 3-arg
  `(id, handler, priv)` signature matching `ml/src/ptp.h:97-107`; calls
  `AddListOperationFunction` at `0xE04BF7A0`; the register site is called 175×
  across ROM0 in tight clusters — the shape of Canon registering all PTP
  opcodes at boot. Validate by GDB breakpoint during stock boot in QEMU before
  touching a body. — spike 011 README §2.
- **Brick discipline:** `GetMemory` has no address validation (MMIO reads can
  hang the bus → MPU ERR80); `CallFunction` is arbitrary code execution and
  the one unrecoverable-brick vector. Exercise on RAM only, in QEMU first;
  never `SetMemory` the vector table or page tables. — spike 011 README §2.
- **MPU init "spells" pipeline is fully tooled upstream** (relevant because the
  same dm-spy log capture underlies both memory work and emulator bring-up):
  `qemu-eos/hw/eos/mpu_spells/extract_init_spells.py` parses `mpu_send`/
  `mpu_recv` logs into an `mpu_init_spells_<MODEL>[]` C table;
  `annotate_mpu_log.py` decodes button codes. — in repo:
  `qemu-eos/hw/eos/mpu_spells/`.

---

## Re-derivation test — did the community already answer 3 things this project burned time on?

The direction docs flag "the project keeps re-deriving known answers" as
mostly-unmeasured. Three concrete checks:

### Q1 — The MPU-spell import method → **HIT (public + tooled)**
The whole method — enable DIGIC 6/7/8 startup DebugMsg logging, capture the
`mpu_send`/`mpu_recv` traffic, run it through `extract_init_spells.py` to emit
`mpu_spells/<MODEL>.h` — already ships in qemu-eos, documented in the tool's own
docstring ("Parse mpu_send/mpu_recv logs … generate MPU init spells code for
QEMU"). Spike 005 **used the existing tool**, it did not re-derive a method; the
only genuinely-new artifact was the 6D2 *data file* (no DIGIC 7 model had one
upstream). Caveat: the project *did* waste time on a phantom "log-buffering bug
in `log-d678.c`" that turned out to be `grep` treating a NUL-padded file as
binary (needed `grep -a`) plus reading a qcow2 while QEMU held it — but that is a
measurement mistake, not a missing-corpus problem. Source:
`qemu-eos/hw/eos/mpu_spells/extract_init_spells.py`,
`.planning/spikes/005-mpu-spell-capture/README.md`.

### Q2 — ICU vs MPU watchdog distinction → **HIT (public since 2018)**
a1ex spelled it out in ML forum topic 22030: EOS locks up and the MPU throws
ERR80 when the main CPU stops; PowerShots have no MPU. The DIGIC 5 suppressible
ICU watchdog (`0xC0410000`) is in CHDK lore. The project found and correctly
cited this (it's in spike 010 README), so it did **not** re-derive it. Source:
ML forum topic 22030. Residual gap (NOT publicly answered): the DIGIC-7
MPU-side suppression address.

### Q3 — CHDK-PTP memory path on modern DIGIC → **PARTIAL (general public, 6D2-specific not)**
The *mechanism* (GetMemory/SetMemory/CallFunction over a PTP opcode) is
documented in CHDK and already in-tree at `ml/src/ptp-chdk.c` — a clear hit for
"how does it work." But whether it works on a modern DIGIC 6/7 EOS body **out of
the box has no published answer**: it's gated by the `ptp_register_handler`
stub, which no DIGIC 6/7/8 body in the tree carries and which the community
never published for the 6D2. The project had to hunt it (candidate `0xE04BF152`,
still inference). So the specific enablement was genuinely un-answered. Source:
`ml/src/ptp-chdk.c`, `.planning/spikes/002` & `011`.

### Verdict on the premise: **mostly deflated.**
On all three probes, the project either (a) already found and used the public
answer (Q1 tool, Q2 watchdog), or (b) was blocked by a genuinely
**6D2-specific value that no corpus contains** (Q1 spell table, Q2 suppression
address, Q3 PTP stub). The one real time-sink (Q1's phantom log bug) was a
measurement error a knowledge corpus would not have prevented. The "keeps
re-deriving known answers" worry is **not strongly borne out** — this project
has been good at citing public sources; its actual costs are measurement
mistakes and unpublished DIGIC-7 specifics.

**Recommendation: enough for now — hold, do not invest further.** This file
plus `KITOR-DIGIC8-METHOD.md` capture the reusable general knowledge in one
place, which is worth having as a citation index. But the remaining unknowns are
all 6D2-specific (IDCODE, pad map, MPU-suppress address, PTP stub) and by
definition are produced by measurement/ROM work, not by growing a corpus of what
others already published. Spend the next hour on the QEMU breakpoint validation
of `0xE04BF152` or the ROM0 watchdog search, not on more corpus-building.
