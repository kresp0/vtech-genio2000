#!/bin/bash
# run_genio.sh [mame args...]  – interactive genio2000 with the private ROMs and the photo artwork (artwork/genio2000: clickable keys; ON, CONTRASTE and the LED need the dev-branch binary), all state kept inside work/interactive
H=$(dirname "$0")/..; cd "$H"; mkdir -p work/interactive/cfg
exec mame/genio genio2000 -rompath roms_local -homepath work/interactive -cfg_directory work/interactive/cfg -nvram_directory work/interactive/nvram \
     -snapshot_directory work/interactive/snap -skip_gameinfo -artpath "$PWD/artwork" -window -nomax "$@"
