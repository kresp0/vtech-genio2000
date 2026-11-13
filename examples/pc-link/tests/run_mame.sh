#!/bin/sh
# Runs the cartridge in headless MAME with the virtual cable (tests/bridge.lua) and drives it with pclink.py.
#   tests/run_mame.sh [outdir] [-- pclink.py arguments...]     (default: the full check in tests/check.sh)
# GENIO_MAME = MAME binary with the genio2000 driver, GENIO_ROMPATH = your own ROMs, EN_INVERT=1 for the other
# BUSY polarity, EN_FALL_US=0 for an ideal line. Never opens a window: no display, dummy SDL drivers, no video, no sound.
# Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later
HERE=$(cd "$(dirname "$0")/.." && pwd)
MAME=${GENIO_MAME:-mame}
ROMPATH=$(realpath -m "${GENIO_ROMPATH:-roms}")
OUT=$(realpath -m "${1:-$HERE/mame/run}")
[ $# -gt 0 ] && shift
[ "$1" = "--" ] && shift
rm -rf "$OUT"; mkdir -p "$OUT"; : > "$OUT/ctl.txt"
unset DISPLAY WAYLAND_DISPLAY
export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy EN_DIR="$OUT"
export EN_FALL_US=${EN_FALL_US-1.9}     # BUSY as the scope saw it on the owner's unit: falling edges 1.9 us late
"$MAME" genio2000 -rompath "$ROMPATH" -cart "${EN_CART:-$HERE/pclink_gl2000_mirrored_AT28C256_32K.bin}" \
  -skip_gameinfo -video none -sound none -seconds_to_run "${EN_SECONDS:-600}" -snapshot_directory "$OUT" \
  -snapview native -cfg_directory "$OUT/cfg" -nvram_directory "$OUT/nvram" \
  -autoboot_script "${EN_BRIDGE:-$HERE/tests/bridge.lua}" > "$OUT/mame.out" 2>&1 &
PID=$!
sleep "${EN_BOOT:-3}"
if [ $# -gt 0 ]; then
  python3 "$HERE/pclink.py" --mame "$OUT" "$@"
else
  EN_PY="python3 $HERE/pclink.py --mame $OUT" sh "${EN_CHECK:-$HERE/tests/check.sh}"
fi
RC=$?
wait $PID
rm -rf "$OUT/cfg" "$OUT/nvram"
cat "$OUT/lua.log"
exit $RC
