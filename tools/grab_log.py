#!/usr/bin/env python3
"""Boot the 6D2 startup-log build and pull ML's complete log buffer straight out of
guest RAM with the qemu monitor's pmemsave.

The card copy (DEBUGMSG.LOG) is equally valid — but ONLY read it after qemu has
exited. Reading sd.qcow2 while qemu still holds it returns a half-flushed image
whose tail reads as NULs at a 16 KiB FAT-cluster boundary, which looks exactly
like a truncated write and is not one. This route avoids the question entirely
and also works when the guest wedges before the dump task runs.

Requires the CONFIG_STARTUP_LOG build:
  make disk_image CONFIG_STARTUP_LOG=y ARM_BINPATH=... ML_MODULES=...
Run inside nix-shell."""
import os, re, sys, subprocess, time

sys.path.insert(0, "/home/chris/ml6d2/qemu-eos/magiclantern")
os.chdir("/home/chris/ml6d2/qemu-eos/magiclantern")
from ml_qemu.run import QemuRunner

BASE = "/home/chris/ml6d2"
PLAT = f"{BASE}/magiclantern_simplified/platform/6D2.111/build"
OUT = os.environ.get("OUTDIR", "/tmp")
DEST = os.environ.get("DEST", f"{OUT}/6D2-startup-full.log")
MAX_WAIT = int(os.environ.get("MAX_WAIT", "240"))
ELF = f"{PLAT}/magiclantern"


def bss_addrs():
    """Resolve buf/len out of the ELF. These are static ints whose addresses move
    on every rebuild, so hardcoding them silently yields garbage — look them up."""
    nm = os.environ.get("NM", "arm-none-eabi-nm")
    try:
        out = subprocess.run([nm, ELF], capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        sys.exit(f"could not run {nm} on {ELF}: {e}\n(are you inside nix-shell?)")
    syms = {}
    for line in out.splitlines():
        m = re.match(r"^([0-9a-f]{8}) [bBdD] (\w+)$", line.strip())
        if m:
            syms.setdefault(m.group(2), int(m.group(1), 16))
    missing = [s for s in ("buf", "len") if s not in syms]
    if missing:
        sys.exit(f"{ELF} has no {missing} symbols — is this a CONFIG_STARTUP_LOG build?")
    return syms["buf"], syms["len"]


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


BUF_ADDR, LEN_ADDR = bss_addrs()
print(f"symbols from {ELF}: buf@0x{BUF_ADDR:x} len@0x{LEN_ADDR:x}")

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
    # wait until the log stops growing (guest stops progressing after the assert)
    while time.time() - t0 < MAX_WAIT:
        time.sleep(15)
        b = words(mon(q, "xp/1xw 0x%x" % BUF_ADDR))
        l = words(mon(q, "xp/1xw 0x%x" % LEN_ADDR))
        if not b or not l:
            continue
        buf, ln = b[0], l[0]
        print(f"t={int(time.time()-t0):4d}s buf=0x{buf:x} len={ln}", flush=True)
        if buf == 0:
            # log_start() bailed: Canon's allocator gave it nothing. See spike 005.
            print("  buf is NULL — log_start() got no buffer; nothing will be captured",
                  flush=True)
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
