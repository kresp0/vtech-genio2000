#!/bin/bash
set -e; cd "$(dirname "$0")"
sdasz80 -plosgff hello_api.s && sdldz80 -nmiu hello_api.rel
makebin -s 16384 -p hello_api.ihx hello_api_16k.bin 2>/dev/null || (sdobjcopy -I ihex -O binary hello_api.ihx hello_api_16k.bin)
ls -l hello_api_16k.bin; xxd hello_api_16k.bin | head -3
