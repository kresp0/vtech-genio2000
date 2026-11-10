#!/bin/bash
# run_cart.sh CART.bin SECONDS  -> OCR of the LCD at the end (EMU).  Example: tools/run_cart.sh examples/hello_api_16k.bin 8
M=${GENIO_MAME_DIR:?set GENIO_MAME_DIR to the MAME working tree}; D=$(mktemp -d /dev/shm/rc.XXXX); S=$(( ${2:-8} - 1 ))
GENIO_SCEN="$S:snap" timeout 200 $M/mame/genio genio2000 -rompath $M/roms_local -homepath $D/h -cfg_directory $D/c -nvram_directory $D/n -snapshot_directory $D/s -video none -sound none -seconds_to_run ${2:-8} -nothrottle -skip_gameinfo -cart "$1" -autoboot_script $M/tests/lua/scenario.lua >/dev/null 2>&1
python3 -I "$(dirname "$0")/snap_text.py" $D/s/*/*.png | grep -v "^/dev"; rm -rf $D
