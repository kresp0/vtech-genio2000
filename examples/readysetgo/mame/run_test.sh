#!/bin/sh
# usage: run_test.sh <outdir> <seconds> <scenario> [extra MAME options]   (headless; needs the genio2000 MAME build)
# env: MAME = the MAME binary with the genio2000 driver, ROMPATH = the folder that holds your own genio2000 ROM set
MAME=$(realpath "${MAME:?set MAME to the MAME binary with the genio2000 driver}")
ROMPATH=$(realpath "${ROMPATH:?set ROMPATH to the folder with your own genio2000 ROMs}")
H=$(cd "$(dirname "$0")" && pwd)
OUT=$(mkdir -p "$1" && cd "$1" && pwd); SECS=$2; SCEN=$3; shift 3
# address of the engine's exit write to port 0x12, to log where each segment ends
B=$(awk '/DEF _engine /{print $3}' "$H/../out/readysetgo_gl2000.noi")
E=$(awk '/ _engine::/{print $1}' "$H/../out/readysetgo_gl2000.lst")
X=$(awk '/kd_exit:/{f=1} f&&/out\t\(0x12\)/{print $1; exit}' "$H/../out/readysetgo_gl2000.lst")
export RSG_EXITPC=$(( B - 0x$E + 0x$X ))
unset DISPLAY WAYLAND_DISPLAY
export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
RSG_SCEN="$SCEN" RSG_LOG="$OUT/summary.txt" "$MAME" genio2000 -rompath "$ROMPATH" \
	-cart "$H/../readysetgo_gl2000_mirrored_AT28C256_32K.bin" -video none -sound none -skip_gameinfo -nothrottle \
	-cfg_directory "$OUT/cfg" -nvram_directory "$OUT/nvram" -snapshot_directory "$OUT" \
	-seconds_to_run "$SECS" -script "$H/rsg_test.lua" "$@" > "$OUT/stdout.txt" 2>&1
echo "exit $?"
