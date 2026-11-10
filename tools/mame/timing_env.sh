#!/bin/bash
# timing_env.sh  – records the exact environment of the timing evidence into logs/timing/environment.txt (hashes only, no ROM bytes).
H=$(cd "$(dirname "$0")/.." && pwd); cd "$H"; O=logs/timing/environment.txt
{
echo "date_utc: $(date -u +%FT%TZ)"
echo "mame_binary: mame/genio  sha256 $(sha256sum mame/genio | cut -d' ' -f1)"
echo "mame_version: $(mame/genio -version 2>&1 | head -1)"
echo "mame_branch: $(git -C mame rev-parse --abbrev-ref HEAD)   commit $(git -C mame rev-parse HEAD)"
echo "mame_branches: pr1=$(git -C mame rev-parse genio2000-pr1-system) pr2=$(git -C mame rev-parse genio2000-pr2-keyboard) pr3=$(git -C mame rev-parse genio2000-pr3-cgrom) dev=$(git -C mame rev-parse genio2000-dev) base=$(git -C mame merge-base origin/master genio2000-pr3-cgrom)"
echo "mame_tree_dirty: $(git -C mame status --porcelain | wc -l) modified files"
echo "firmware sha1 (27-5575-00): $(sha1sum roms_local/genio2000/27-5575-00 roms_local/genio2000/genio2000_cgrom_reconstructed.bin | sed 's#  roms_local/#  #' | tr '\n' ';')"
echo "cgrom sha1 (data/cgrom): $(sha1sum data/cgrom/genio2000_cgrom_reconstructed.bin | cut -d' ' -f1)  (BAD_DUMP, optical reconstruction)"
echo "emulated configuration: driver default CPU 6.13179 MHz (measured) and periodic interrupt 50 Hz; the experiments select CLOCK/IRQ with tools/set_cfg.py (genio2000-dev only): CLOCK index 0 = 6.13179, 9 = 4.0, 6 = 6.0, 7 = 6.144 MHz; IRQ 50 Hz (also 40 and 60 Hz). Runs preserved before 2026-11-09 17:00 used the old numbering (0 = 4 MHz default) but the same file names"
echo "refs: real unit videos on.mov / off.mov (not published); sha256 $(sha256sum ${GENIO_VIDEO_DIR:-.}/on.mov | cut -d' ' -f1) / $(sha256sum ${GENIO_VIDEO_DIR:-.}/off.mov | cut -d' ' -f1)"
echo "host: $(uname -srm); python $(python3 -V 2>&1); ffmpeg $(ffmpeg -version 2>&1 | head -1 | cut -d' ' -f3)"
} > $O; cat $O
