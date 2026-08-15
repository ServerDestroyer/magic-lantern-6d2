#!/usr/bin/env python3
"""Boot the 6D2 startup-log build and pull ML's complete log buffer straight out of
guest RAM with the qemu monitor's pmemsave.

Why not just read DEBUGMSG.LOG off the card: qemu-eos's SD model commits only the
first 32 KB of a multi-burst DMA write (hw/eos/eos.c sdio_write_data), so the card
copy is truncated even though the buffer in RAM is complete. On a real camera the
card file is the right source; in the emulator this is."""
import os, sys, subprocess, time

sys.path.insert(0, "/home/chris/ml6d2/qemu-eos/magiclantern")
os.chdir("/home/chris/ml6d2/qemu-eos/magiclantern")
from ml_qemu.run import QemuRunner

BASE = "/home/chris/ml6d2"
PLAT = f"{BASE}/magiclantern_simplified/platform/6D2.111/build"
OUT = os.environ.get("OUTDIR", "/tmp")
DEST = os.environ.get("DEST", f"{OUT}/6D2-startup-full.log")
MAX_WAIT = int(os.environ.get("MAX_WAIT", "240"))
STATE = 0x0015daa8          # diag_entered; buf/buf_size/len follow (see nm output)


def mon(q, cmd, wait=0.5):
    q.monitor_socket.send(cmd.encode() + b"\n")
    time.sleep(wait)
    out = b""
    q.monitor_socket.setblocking(False)
    try:
        while True:
            c = q.monitor_socket.recv(65536)
            if not c:
                break
            out += c
    except BlockingIOError:
        pass
    finally:
        q.monitor_socket.setblocking(True)
    return out.decode(errors="replace")


def words(text):
    ws = []
    for line in text.splitlines():
        if ":" not in line:
            continue
        for tok in line.split(":", 1)[1].split():
            if tok.startswith("0x"):
                try:
                    ws.append(int(tok, 16))
                except ValueError:
                    pass
    return ws


with QemuRunner(f"{BASE}/qemu-eos-build", f"{BASE}/roms",
                f"{BASE}/magiclantern_simplified", "6D2",
                sd_file=f"{PLAT}/sd.qcow2", cf_file=f"{PLAT}/cf.qcow2",
                stdout=f"{OUT}/grab_stdout.log", stderr=f"{OUT}/grab_stderr.log",
                serial_out=f"{OUT}/grab_serial.log",
                display=None, d_args=["debugmsg"], boot=True) as q:
    mon(q, "")
    buf = ln = 0
    stable = 0
    prev = -1
    t0 = time.time()
    # wait until the log stops growing (guest wedges on the known RscMgr assert)
    while time.time() - t0 < MAX_WAIT:
        time.sleep(15)
        st = words(mon(q, "xp/10xw 0x%x" % STATE))
        if len(st) < 5:
            continue
        buf, ln = st[1], st[4]
        entered, appended = st[0], st[6]
        print(f"t={int(time.time()-t0):4d}s buf=0x{buf:x} len={ln} "
              f"entered={entered} appended={appended}", flush=True)
        stable = stable + 1 if ln == prev else 0
        prev = ln
        if stable >= 2 and ln > 0:
            print("log stopped growing", flush=True)
            break

    if buf and ln:
        print(mon(q, "pmemsave 0x%x %d \"%s\"" % (buf, ln, DEST), wait=2.0).strip()[:200])
    q.shutdown(force=True)
    try:
        q.qemu_process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        q.qemu_process.kill()

if os.path.exists(DEST):
    raw = open(DEST, "rb").read()
    txt = raw.split(b"\x00")[0] if b"\x00" in raw else raw
    open(DEST, "wb").write(txt)
    print(f"\nsaved {DEST}: {len(txt)} bytes, {txt.count(chr(10).encode())} lines")
