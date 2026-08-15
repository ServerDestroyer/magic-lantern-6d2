#!/usr/bin/env bash
# Deploy a 6D2 ML build to the SD card and VERIFY it — prevents the partial-sync
# trap (autoexec.bin updated but stale 6D2_111.sym/.mo/.hid left behind), which
# has silently broken two body tests already.
#
# Usage: sync_card.sh <card-mount-point> [build-zip-dir]
#   build-zip-dir defaults to ml/platform/6D2.111/build/zip (the live build).
#   For the spell-capture package: sync_card.sh /run/media/chris/EOS card_packages/capture
#
# Never format the card in-camera afterwards — that wipes the boot-sector flags.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CARD="${1:?usage: sync_card.sh <card-mount-point> [build-zip-dir]}"
BUILD="${2:-$ROOT/ml/platform/6D2.111/build/zip}"
[[ "$BUILD" = /* ]] || BUILD="$ROOT/$BUILD"

[[ -f "$BUILD/autoexec.bin" ]] || { echo "ERROR: no autoexec.bin in $BUILD" >&2; exit 1; }
[[ -f "$BUILD/ML/modules/6D2_111.sym" ]] || { echo "ERROR: no ML/modules/6D2_111.sym in $BUILD" >&2; exit 1; }
[[ -d "$CARD" && -w "$CARD" ]] || { echo "ERROR: card mount $CARD missing or read-only" >&2; exit 1; }

echo "== sync: $BUILD -> $CARD"
cp "$BUILD/autoexec.bin" "$CARD/autoexec.bin"
mkdir -p "$CARD/ML"
# Merge the whole tree. Build zip carries no SETTINGS/ or LOGS/, so the card's
# ML config and on-card logs survive untouched.
cp -r "$BUILD/ML/." "$CARD/ML/"

# Stale-.hid cleanup: a <name>.hid on the card hides module <name>.mo
# (src/module.c:132). Delete card-side .hid markers ONLY where the build ships
# the .mo but not the .hid (build-shipped .hid like dual_iso.hid stay).
for mo in "$BUILD"/ML/modules/*.mo; do
    base="$(basename "$mo" .mo)"
    if [[ -e "$CARD/ML/modules/$base.hid" && ! -e "$BUILD/ML/modules/$base.hid" ]]; then
        echo "   removing stale $base.hid (was hiding $base.mo)"
        rm "$CARD/ML/modules/$base.hid"
    fi
done

echo "== verify (md5 card vs build)"
fail=0
verify() { # verify <build-file> <card-file>
    local b c
    b="$(md5sum "$1" | cut -d' ' -f1)"
    c="$(md5sum "$2" | cut -d' ' -f1)"
    if [[ "$b" == "$c" ]]; then printf '   OK  %s\n' "${2#"$CARD"/}";
    else printf '   MISMATCH  %s\n' "${2#"$CARD"/}"; fail=1; fi
}
verify "$BUILD/autoexec.bin" "$CARD/autoexec.bin"
verify "$BUILD/ML/modules/6D2_111.sym" "$CARD/ML/modules/6D2_111.sym"
for mo in "$BUILD"/ML/modules/*.mo; do
    verify "$mo" "$CARD/ML/modules/$(basename "$mo")"
done

sync
if [[ $fail -ne 0 ]]; then echo "== FAILED: card does not match build — do NOT eject and test" >&2; exit 1; fi
echo "== done: card matches build. Do not format in camera."
