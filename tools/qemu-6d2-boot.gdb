# Minimal, PROVEN gdb harness for booting the 6D2 in qemu-eos past the known walls.
#
# Deliberately does NOT source debug-logging.gdb. That chain installs 7 logging
# breakpoints and dies on a stray SIGTRAP at 0xdf00a5d4 during CreateStateObject,
# long before the interesting code. Under -batch gdb then DETACHES and QEMU runs
# on uninstrumented — producing a log that looks exactly like "the patch failed".
# That cost a full wasted run; use this file instead when testing a breakpoint.
#
# USAGE (both halves matter):
#   cd /home/chris/ml6d2/qemu-eos/magiclantern
#   nix-shell "<project>/shell.nix" --run '
#     timeout 240 python3 run_qemu.py 6D2 -q /home/chris/ml6d2/qemu-eos-build --gdb \
#         > qemu.log 2>&1 &
#     sleep 12
#     timeout 230 arm-none-eabi-gdb -nx -batch -x <project>/tools/qemu-6d2-boot.gdb \
#         > gdb.log 2>&1
#     wait
#   '
#
# READING THE LOGS — non-negotiable:
#   QEMU serial logs contain a NUL byte, so plain grep treats them as BINARY,
#   prints NOTHING and exits 1. That is indistinguishable from a genuine no-match
#   and has already produced one false conclusion. ALWAYS:
#       LC_ALL=C grep -a "pattern" qemu.log
#
# Success target: "[STARTUP] startupInitializeComplete" — this is qemu-eos's own
# definition of a booted camera (magiclantern/ml_tests/log_test.py). As of
# 2026-08-15 the 6D2 has NEVER reached it.

set pagination off
set confirm off
set architecture arm
set tcp connect-timeout 300
target remote localhost:1234

# ---------------------------------------------------------------- wall 1: SOLVED
# GetEstimatedSize() at 0xE0202312 loads a frame-rate field (fps x100) via
#   0xE0202372:  ldr r0, [r6, #8]
# then switches on it against exactly eight legal values:
#   2000 2398 2400 2500 2997 5000 5994 11988
# Under generic MPU spells the field holds 81 (0x51) -> no case matches -> the
# default arm runs ASSERT(FALSE) at 0xE0202480 = EstimatedSize.c:1521, task RscMgr.
# 200D's patches.gdb records the same value ("strange values passed in, 0x51").
#
# Break AFTER the load, not at function entry — an entry patch gets clobbered by it.
# Confirmed live: "rate=81" x14, boot 223 -> 2882 log lines.
b *0xE0202374
commands
  silent
  printf "ESTSIZE_HIT rate=%d -> forcing 2000\n", $r0
  set $r0 = 0x7D0
  c
end

# ------------------------------------------------- wall 2: symptom-fixed, unproven
# EngInit (0xE0060926) runs on Core 1 and blocks in `bl 0xE0091D04` at 0xE0060942,
# so `bl 0xE04AA690` (ResMng_Init — sole creator of the ENG_RES_MNG lock at 0x10BFC)
# never runs. ShtCap then takes a NULL handle and the kernel guard at 0xDF00B47A
# asserts: SystemIF::KerRLock.c line 205, Core 1. "WaitPU1 TimeOut" is the SAME bug.
#
# Stubbing with Thumb `bx lr` clears the assert (5 -> 0) and pushes DryOS messages
# 398 -> 557. It does NOT make the camera boot. Use 16-bit writes: the `set *(int*)`
# form was never validated here.
#
# UNCOMMENT to enable — it removes a symptom and may mask a real emulation gap:
# set *(unsigned short*)0xE0091D04 = 0x4770

# ------------------------------------------------------------ assert visibility
# The assert handler. Signature: assert(r0 = expr str, r1 = file str, r2 = line).
# NOTE qemu-eos's cam_config/6D2/debugmsg.gdb shipped 0xE06170EC for this, which is
# WRONG — that address is mid-instruction inside AES S-box lookup code, so no assert
# was ever logged for this cam. See patches/0004. $lr gives the calling function,
# which is the cheapest way to locate a new wall.
b *0xE0617620
commands
  silent
  printf "ASSERT_HIT line=%d caller_lr=0x%x\n", $r2, $lr
  c
end

cont
