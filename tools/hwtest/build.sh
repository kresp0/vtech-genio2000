#!/bin/bash
# build.sh [ye|ga|all] - builds ONLY inside hwtest/build/<variant>; reads VGLDK headers and gen_crc32tab.py from a clone of the dumper repository (GENIO_DUMPER_DIR, default ../dumper; see tools/README.md), read-only.
# Never programs any chip. Output: build/<variant>/hwtest_<variant>_AT28C256_32K.bin (4 x 8 KiB, each quarter has a different marker at 0x1BE0).
set -euo pipefail
cd "$(dirname "$0")"
FD=${GENIO_DUMPER_DIR:-../dumper}
V=$FD/third_party/vgldk
for T in ${1:-all}; do
  [ "$T" = all ] && { "$0" ye; "$0" ga; exit 0; }
  O=build/$T; mkdir -p "$O"
  python3 $FD/tools/gen_crc32tab.py "$O/crc32tab.s"
  sdasz80 -o "$O/crt0.rel" src/crt0_$T.s
  sdasz80 -o "$O/crc32tab.rel" "$O/crc32tab.s"
  sdcc -mz80 --no-std-crt0 -D VGLDK_SERIES=2000 --code-loc 0x8020 --data-loc 0xc000 \
    --lib-path $V/include -I $V/include -I $V/include/arch/gl2000 -I src \
    -o "$O/hwtest.ihx" "$O/crt0.rel" "$O/crc32tab.rel" src/hwtest.c 2>&1 | grep -v "warning 283\|warning 84\|warning 110\|warning 85\|warning 59" || true
  test -s "$O/hwtest.ihx"
  makebin -p -s 65536 "$O/hwtest.ihx" "$O/hwtest.ihx.bin" 2>/dev/null
  dd iflag=skip_bytes skip=32768 bs=1024 count=8 if="$O/hwtest.ihx.bin" of="$O/hwtest.cart.8kb.bin" status=none
  python3 tools/mk_image.py "$T" "$O/hwtest.map" "$O/hwtest.cart.8kb.bin" "$O/hwtest_${T}_AT28C256_32K.bin"
done
