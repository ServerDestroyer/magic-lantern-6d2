# 6D2 startup-log capture card package (spike 005, body run)

Copy `autoexec.bin` to the card root (overwrite the existing one), and merge the
`ML/` directory here over the card's existing `ML/` (overwrite matching files —
`ML/modules/6D2_111.sym` and the four `.mo` files must all come from this build,
a mismatched sym/module set is a known failure mode). Do NOT touch the card's
`ML/SETTINGS` or `ML/LOGS`, and do NOT format the card in camera (formatting
wipes the boot-sector flags). Verify with `md5sum -c md5sums.txt` from the card
root if in doubt. Then: power on, wait ~25 s, pull the battery, copy
`DEBUGMSG.LOG` off the card. `grep -a` when inspecting it (NUL padding). A
missing file or missing `*** DIAG` trailer means the capture failed, not that
there was nothing to log.

Build: `magiclantern_simplified` @ 3f24042a4 + patches 0001 (SHOW features
commented out — they break the allocator pool, see spike 005) + 0002 + 0004,
`CONFIG_STARTUP_LOG=y`, `ML_MODULES="raw_video/mlv_lite file_man bench dual_iso"`.
Verified in QEMU 2026-08-15: pool 9437184/5970756 at log_start(), 2 MB
allocated, DIAG trailer present, 23 mpu_send + 3 mpu_recv captured.
autoexec.bin md5 969d407d01fc2b140cdfd3b20a9f9f34.
