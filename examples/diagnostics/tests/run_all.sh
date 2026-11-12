#!/bin/sh
# Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later
# Every MAME check of the diagnostic cartridge, headless. Output in mame/<name>/drive.log; summary on stdout.
cd "$(dirname "$0")/.." && mkdir -p mame
python3 -c "
d=bytearray(open('diag_gl2000_mirrored_AT28C256_32K.bin','rb').read())
i=d.index(b'ACERTIJO GRAMATICAL'); d[i]^=1
open('mame/corrupt_32K.bin','wb').write(d)"
for t in auto all menus sound; do
  extra=""; [ $t = sound ] && extra="-wavwrite $PWD/diag_sonido_mame.wav"
  echo "$t: $(tests/run.sh tests/$t.txt mame/$t 110 $extra)"
done
echo "faults (expects FAIL in RAM address, RAM march 8K, ROM cartridge, ROM page 81, Keys at rest):"
DG_STUCK0="D234:10" DG_CART="$PWD/mame/corrupt_32K.bin" tests/run.sh tests/faults.txt mame/faults 60 >/dev/null
grep "FAIL" mame/faults/drive.log
tests/irq_matrix.sh
