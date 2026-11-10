#!/bin/bash
# record_sound.sh <out.wav> [CLOCK=n (0 = 6.13179 MHz default, 9 = 4 MHz)] [IRQ=n] [seconds]  – headless boot, WAV of the emulated speaker (CLOCK/IRQ need the genio2000-dev binary)
H=$(dirname "$0")/..; cd "$H"; OUT=$1; shift; SECS=8; CFG=$(mktemp -d work/rec_XXXX); ARGS=()
for a in "$@"; do case $a in CLOCK=*|IRQ=*) ARGS+=("$a");; *) SECS=$a;; esac; done
python3 tools/set_cfg.py $CFG/cfg "${ARGS[@]}"
mame/genio genio2000 -rompath roms_local -homepath $CFG/h -cfg_directory $CFG/cfg -nvram_directory $CFG/n -video none -sound none -wavwrite "$OUT" -seconds_to_run $SECS -nothrottle -skip_gameinfo > /dev/null 2>&1
echo "wrote $OUT ($(stat -c %s "$OUT") bytes)"; python3 tools/wav_notes.py "$OUT" | head -14
