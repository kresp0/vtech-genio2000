#!/bin/bash
# timing_run.sh <boot|off> <CLOCK idx> <IRQ idx> <outdir>   (experimental branch genio2000-dev only)
#   CLOCK: 0=6.13179 (driver default) 1=3.0 2=3.579545 3=4.194304 4=4.9152 5=5.0 6=6.0 7=6.144 8=8.0 9=4.0 MHz     IRQ: 0=50 1=40 2=45 3=55 4=60 5=75 6=100 Hz
# Headless, no throttle, same firmware + CGROM + scenario for every run; the only things that change are the two options.
# Writes <outdir>/{cfg/genio2000.cfg,timing.log,summary.json,cmd.txt}. Nothing outside <outdir> and work/ is touched.
set -e; SC=$1; CK=$2; IR=$3; OUT=$4
H=$(cd "$(dirname "$0")/.." && pwd); cd "$H"; mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd); rm -rf "$OUT/cfg" "$OUT/h"
python3 tools/set_cfg.py "$OUT/cfg" CLOCK=$CK IRQ=$IR
case $SC in boot) SCEN='14:quit'; SECS=16;; off) SCEN='20:press:OFF;27:quit'; SECS=30;; *) echo "scenario?"; exit 1;; esac
CMD="GENIO_LUADIR=$H/tests/lua GENIO_LOG=$OUT/timing.log GENIO_SCEN='$SCEN' GENIO_HOLD=0.4 mame/genio genio2000 -rompath roms_local -homepath $OUT/h -cfg_directory $OUT/cfg -nvram_directory $OUT/h/nvram -snapshot_directory $OUT/h/snap -video none -sound none -seconds_to_run $SECS -nothrottle -skip_gameinfo -autoboot_script tests/lua/timing_log.lua"
echo "$CMD" > "$OUT/cmd.txt"
GENIO_LUADIR=$H/tests/lua GENIO_LOG=$OUT/timing.log GENIO_SCEN="$SCEN" GENIO_HOLD=0.4 mame/genio genio2000 -rompath roms_local -homepath $OUT/h -cfg_directory $OUT/cfg -nvram_directory $OUT/h/nvram -snapshot_directory $OUT/h/snap -video none -sound none -seconds_to_run $SECS -nothrottle -skip_gameinfo -autoboot_script tests/lua/timing_log.lua > "$OUT/mame_stdout.txt" 2>&1 || true
rm -rf "$OUT/h"
python3 tools/timing_summary.py $SC "$OUT/timing.log" > "$OUT/summary.json"; cat "$OUT/summary.json"
