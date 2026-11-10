#!/bin/bash
# video_events.sh <video.mov> <outdir> <name> <crop W:H:X:Y> t1 t2 ...  -> <outdir>/<name>.jpg  contact sheet (5 per row) of the cropped frames at the given
# video times, labelled with the time.  Frame times are the container timestamps (60 fps).  Event times in logs/timing/video/events.csv were read by eye from these sheets.
V=$1; O=$2; N=$3; CROP=$4; shift 4; mkdir -p "$O"; T=$(mktemp -d); i=0
for t in "$@"; do ffmpeg -v error -ss $t -i "$V" -frames:v 1 -vf "crop=$CROP,scale=480:-1,drawtext=text='$t':x=10:y=8:fontsize=30:fontcolor=yellow" $T/f$(printf %03d $i).png -y; i=$((i+1)); done
ffmpeg -v error -pattern_type glob -i "$T/f*.png" -vf "tile=5x$(( (i+4)/5 ))" -frames:v 1 -q:v 4 "$O/$N.jpg" -y; rm -rf $T
