#!/bin/bash
# dis_quick.sh <bank> <start hex> <len dec> [base hex window]  -- quick unidasm view with logical addresses
B=$1; S=$((16#${2#0x})); L=$3; W=${4:-0}
dd if=$(dirname "$0")/../rom/genio2000_es_128k.bin bs=16384 skip=$B count=1 2>/dev/null > /dev/shm/_b.bin
unidasm /dev/shm/_b.bin -arch z80 -skip $S -count $L 2>&1 | awk -v base=$((S+16#${W#0x})) '{a=strtonum("0x" substr($1,1,4))+base; printf "%04X:%s\n", a, substr($0,5)}'
