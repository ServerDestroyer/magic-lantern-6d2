#!/usr/bin/env python3
"""Extract MPU button codes for the 6D2 by statically decoding bindReceiveSwitch.

Upstream's qemu-eos/hw/eos/mpu_spells/extract_button_codes.py emulates DIGIC 4/5
ROM1 under Unicorn. That does not work here (6D2 firmware is Thumb-2 in ROM0),
but it does not need to: on DIGIC 7 bindReceiveSwitch is a plain two-level
tbb jump table, so the whole mapping can be read straight out of the ROM.

    switch (a) { ... r4 = <gui code> ... }   -> tbb [pc, sl], 44 entries
    if (b == 1) press else unpress           -> cmp r5,#1 / beq
    GUI_Control(r4, 0, arg)                  -> bl 0xE00DC458

MPU button code = (a << 8) | b.

Usage (inside nix-shell, needs arm-none-eabi-objdump):
    python3 decode_button_codes.py /path/to/ROM0.BIN
"""
import os, re, subprocess, sys, tempfile

BASE       = 0xE0000000
FUNC_START = 0xE00DA9F4   # bindReceiveSwitch (Thumb, entry 0xE00DA9F5)
SWITCH_TBB = 0xE00DAA32   # tbb table for arg a, 44 entries
DIS_LO, DIS_HI = 0xD8000, 0xDD800    # file offsets to disassemble
# every path that reaches these has left r4 == 0xFFFF -> no GUI event
NO_EVENT = {0xE00DAA88, 0xE00DAE8E, 0xE00DAE9E}
# r4 is live by the time control reaches the GUI_Control tail
TAIL = {0xE00DAA78, 0xE00DAA7E, 0xE00DAAA6}

# platform/6D2.111/gui.h -- camera GUI code -> ML name, restricted to the
# names that also exist in qemu-eos hw/eos/mpu.h `enum button_codes`.
GUI_H = {
    0x00: "BGMT_WHEEL_UP",      0x01: "BGMT_WHEEL_DOWN",
    0x02: "BGMT_WHEEL_LEFT",    0x03: "BGMT_WHEEL_RIGHT",
    0x04: "BGMT_PRESS_SET",     0x05: "BGMT_UNPRESS_SET",
    0x06: "BGMT_MENU",          0x07: "BGMT_INFO",
    0x0B: "BGMT_PLAY",          0x0D: "BGMT_TRASH",
    0x12: "BGMT_PRESS_ZOOM_IN", 0x13: "BGMT_UNPRESS_ZOOM_IN",
    0x1D: "BGMT_Q",             0x1E: "BGMT_LV",
    0x20: "BGMT_LIGHT",
    0x2E: "BGMT_UNPRESS_UDLR",  0x2F: "BGMT_PRESS_UP",
    0x30: "BGMT_PRESS_UP_RIGHT", 0x31: "BGMT_PRESS_UP_LEFT",
    0x32: "BGMT_PRESS_RIGHT",   0x33: "BGMT_PRESS_LEFT",
    0x34: "BGMT_PRESS_DOWN_RIGHT", 0x35: "BGMT_PRESS_DOWN_LEFT",
    0x36: "BGMT_PRESS_DOWN",
    0x4B: "GMT_GUICMD_PRESS_BUTTON_SOMETHING",
    0x55: "GMT_GUICMD_LOCK_ON",
    0x56: "GMT_GUICMD_OPEN_SLOT_COVER", 0x57: "GMT_GUICMD_CLOSE_SLOT_COVER",
}


def disassemble(rom_path):
    rom = open(rom_path, "rb").read()
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        f.write(rom[DIS_LO:DIS_HI])
        chunk = f.name
    out = subprocess.run(
        ["arm-none-eabi-objdump", "-D", "-b", "binary", "-m", "armv7",
         "-M", "force-thumb", "--adjust-vma=0x%X" % (BASE + DIS_LO), chunk],
        capture_output=True, text=True, check=True).stdout
    os.unlink(chunk)
    ins, order = {}, []
    for line in out.splitlines():
        m = re.match(r"^([0-9a-f]{8}):\t[0-9a-f ]+\t(.*)$", line)
        if m:
            a = int(m.group(1), 16)
            ins[a] = m.group(2).strip()
            order.append(a)
    return rom, ins, order, {a: i for i, a in enumerate(order)}


def walk(a, cond, depth, out, seen, ctx):
    """Follow control flow from `a` until r4 (the GUI code) is pinned down."""
    rom, ins, order, idx = ctx
    for _ in range(400):
        if depth > 6:
            return
        if a in NO_EVENT:
            out.append((cond, None))
            return
        if (a, cond) in seen:
            return
        seen.add((a, cond))
        i = ins.get(a)
        if i is None:
            return
        m = re.match(r"movs\s+r4, #(\d+)", i)
        if m:
            out.append((cond, int(m.group(1))))
            return
        m = re.match(r"cmp\s+r5, #(\d+)", i)
        if m:
            k, a2 = int(m.group(1)), order[idx[a] + 1]
            m2 = re.match(r"(beq|bne|bcs|bcc)(?:\.[nw])?\s+0x([0-9a-f]+)", ins.get(a2, ""))
            if m2:
                op, t = m2.group(1), int(m2.group(2), 16)
                lab = {"beq": ("b==%d" % k, "b!=%d" % k), "bne": ("b!=%d" % k, "b==%d" % k),
                       "bcs": ("b>=%d" % k, "b<%d" % k), "bcc": ("b<%d" % k, "b>=%d" % k)}[op]
                walk(t, cond + (lab[0],), depth + 1, out, set(seen), ctx)
                walk(order[idx[a2] + 1], cond + (lab[1],), depth + 1, out, set(seen), ctx)
                return
        if re.match(r"tbb\s+\[pc, r5\]", i):          # direction sub-switch
            tb = a + 4
            for b in range(10):
                walk(tb + 2 * rom[tb - BASE + b], cond + ("b=%d" % b,), depth + 1,
                     out, set(seen), ctx)
            return
        # sign test on sxtb(b): negative -> "... DIAL LEFT", positive -> RIGHT
        if re.match(r"movs\.w\s+r8, r0", i):
            a2 = order[idx[a] + 1]
            m2 = re.match(r"bpl(?:\.[nw])?\s+0x([0-9a-f]+)", ins.get(a2, ""))
            if m2:
                walk(int(m2.group(1), 16), cond + ("b>=0",), depth + 1, out, set(seen), ctx)
                walk(order[idx[a2] + 1], cond + ("b<0",), depth + 1, out, set(seen), ctx)
                return
        m = re.match(r"b(?:\.[nw])?\s+0x([0-9a-f]+)$", i)
        if m:
            a = int(m.group(1), 16)
            continue
        m = re.match(r"(beq|bne|bcs|bcc|bpl|bmi|bhi|bls)(?:\.[nw])?\s+0x([0-9a-f]+)", i)
        if m:
            walk(int(m.group(2), 16), cond + ("?",), depth + 1, out, set(seen), ctx)
            a = order[idx[a] + 1]
            continue
        m = re.match(r"cbn?z\s+r\d+, 0x([0-9a-f]+)", i)
        if m:
            walk(int(m.group(1), 16), cond + ("?",), depth + 1, out, set(seen), ctx)
            a = order[idx[a] + 1]
            continue
        a = order[idx[a] + 1]


def mpu_code(a, cond):
    """(switch id, path condition) -> the byte pair the MPU actually sends."""
    for c in cond:
        if c.startswith("b=="):
            return (a << 8) | int(c[3:])
        if c.startswith("b="):
            return (a << 8) | int(c[2:])
        if c == "b<0":
            return (a << 8) | 0xFF
        if c == "b>=0":
            return (a << 8) | 0x01
        if c == "b!=1" or c == "b!=0":
            return (a << 8) | (0x00 if c == "b!=1" else 0x01)
    return (a << 8) | 0x01          # unconditional handler: press byte by convention


def main():
    rom_path = sys.argv[1] if len(sys.argv) > 1 else "roms/6D2/ROM0.BIN"
    ctx = disassemble(rom_path)
    rom = ctx[0]
    table, trace = {}, []
    for i in range(0x2C):
        target = SWITCH_TBB + 2 * rom[SWITCH_TBB - BASE + i]
        out = []
        walk(target, (), 0, out, set(), ctx)
        for cond, gui in dict.fromkeys(out):
            code = mpu_code(i, cond)
            name = GUI_H.get(gui, "")
            trace.append("id 0x%02X -> 0x%08X  %-24s gui=%-5s %s"
                         % (i, target, ",".join(cond) or "always",
                            "--" if gui is None else "0x%02X" % gui, name))
            if name and name not in table:
                table[name] = code

    sys.stderr.write("\n".join(trace) + "\n")
    print("static int button_codes_6D2[] = {")
    for n, v in sorted(table.items(), key=lambda kv: kv[1]):
        print("    %-35s = 0x%04X," % ("[%s]" % n, v))
    print("    %-35s = 0x0000" % "[BGMT_END_OF_LIST]")
    print("};")

    # self-check: pairs read off the real body log, tools/6D2-DEBUGMSG-body.txt
    #   bindReceiveSwitch (17, 1) -> GUI_Control:85 (0x55) LOCK_ON
    #   bindReceiveSwitch (18, 0) -> GUI_Control:87 (0x57) CLOSE_SLOT_COVER
    #   bindReceiveSwitch (38, 1) -> GUI_Control:75 (0x4B) PRESS_BUTTON_SOMETHING (movie log)
    assert table.get("GMT_GUICMD_LOCK_ON") == 0x1101, table.get("GMT_GUICMD_LOCK_ON")
    assert table.get("GMT_GUICMD_CLOSE_SLOT_COVER") == 0x1200
    assert table.get("GMT_GUICMD_PRESS_BUTTON_SOMETHING") == 0x2601
    assert table.get("BGMT_PRESS_SET") == 0x0C01
    assert table.get("BGMT_WHEEL_LEFT") == 0x0DFF
    sys.stderr.write("self-check OK (5 pairs match the body log / 100D convention)\n")


if __name__ == "__main__":
    main()
