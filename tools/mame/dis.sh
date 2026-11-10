#!/bin/bash
# dis.sh <bank 0-7> <start hex> <count bytes> : Z80 disassembly of a 16 KiB bank of the (private) firmware with real offsets (uses MAME's unidasm)
D=${GENIO_FW_DIR:?set GENIO_FW_DIR to the directory with the verified bank_N.bin files}
unidasm "$D/bank_$1.bin" -arch z80 -skip $((16#${2#0x})) -count $3 2>&1 | awk -v base=$((16#${2#0x})) '{a=strtonum("0x" substr($1,1,4))+base; printf "%04X:%s\n", a, substr($0,5)}'
