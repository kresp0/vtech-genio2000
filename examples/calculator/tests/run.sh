#!/bin/sh
# Headless MAME run of one driver script: tests/run.sh <script> <outdir> <seconds> [extra MAME args]
# CT_CART = another image. GENIO_MAME = MAME binary with the genio2000 driver (default: mame), GENIO_ROMPATH = your own ROMs (default: roms).
# Never opens a window: no display, dummy SDL drivers, no video; sound only when the extra args ask for -wavwrite.
# Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later
set -e
HERE=$(cd "$(dirname "$0")/.." && pwd)
MAME=${GENIO_MAME:-mame}
ROMPATH=$(realpath -m "${GENIO_ROMPATH:-roms}")
SCRIPT=$(realpath "$1"); OUT=$(realpath -m "$2"); SECS=$3; shift 3
rm -rf "$OUT"; mkdir -p "$OUT"
unset DISPLAY WAYLAND_DISPLAY
export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
export CT_SCRIPT="$SCRIPT" CT_LOG="$OUT/drive.log" CT_MAP="$HERE/out/calc_gl2000.map" CT_OUT="${CT_OUT:-}"
SOUND="-sound none"
case " $* " in *" -wavwrite "*) SOUND="-sound sdl";; esac
cd "$HERE"
"$MAME" genio2000 -rompath "$ROMPATH" -cart "${CT_CART:-$HERE/calc_gl2000_mame_64K.bin}" \
  -skip_gameinfo -nothrottle -video none $SOUND -seconds_to_run "$SECS" -snapshot_directory "$OUT" -snapview native \
  -cfg_directory "$OUT/cfg" -nvram_directory "$OUT/nvram" -autoboot_script "$HERE/tests/drive.lua" "$@" \
  > "$OUT/mame.out" 2>&1 || true
rm -rf "$OUT/cfg" "$OUT/nvram"
tail -1 "$OUT/drive.log"
