#!/bin/bash
# record_t1.sh [label] [seconds]  – T1: record the boot music of the REAL unit with the default microphone.
#   label   free text for the file name, e.g. pilas, adaptador (default: toma)
#   seconds recording length (default 15)
# Output: work/recordings/t1_<label>_<date>.wav (48 kHz, mono, 16 bit). Never overwrites.
# Procedure: unit OFF, phone/mic 5-10 cm from the speaker, quiet room. Run this, wait for the countdown, press ON.
# Then compare:  tools/wav_notes.py work/wav/<emulator>.wav work/recordings/t1_*.wav
set -e
LABEL=${1:-toma}; SECS=${2:-15}
cd "$(dirname "$0")/.."; mkdir -p work/recordings
OUT=work/recordings/t1_${LABEL}_$(date +%Y%m%d_%H%M%S).wav
[ -e "$OUT" ] && { echo "exists: $OUT"; exit 1; }
if command -v pw-record >/dev/null; then
  REC=(pw-record --rate 48000 --channels 1 --format s16 "$OUT")
elif command -v parecord >/dev/null; then
  REC=(parecord --rate=48000 --channels=1 --format=s16le --file-format=wav "$OUT")
else
  REC=(arecord -q -f S16_LE -r 48000 -c 1 -t wav "$OUT")
fi
echo "Mic: default input. Unit must be OFF. Recording $SECS s after the prompt -> $OUT"
# Start the recorder FIRST: pw-record/parecord take a moment to open the stream, so the prompt only appears once it is running.
"${REC[@]}" &
RPID=$!
# pw-record needs ~2 s before it really captures (a 15 s run gave a 13 s file): wait until the file actually grows.
for i in $(seq 1 100); do
  kill -0 "$RPID" 2>/dev/null || { echo "recorder failed to start"; exit 1; }
  [ "$(stat -c %s "$OUT" 2>/dev/null || echo 0)" -gt 20000 ] && break
  sleep 0.1
done
sleep 1
echo ">>> REC running. Press ON now"
sleep "$SECS"
kill -INT "$RPID" 2>/dev/null || true
wait "$RPID" 2>/dev/null || true
echo "Done."
ffprobe -v error -show_entries stream=sample_rate,channels,duration -of default=nw=1 "$OUT" 2>/dev/null || ls -l "$OUT"
ffmpeg -v error -i "$OUT" -af volumedetect -f null - 2>&1 | grep -E "max_volume|mean_volume" || true
echo "If max_volume is 0 dB the signal clipped: move the mic away or lower the input gain, and repeat."
