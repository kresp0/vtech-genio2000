#!/bin/sh
# Every check: host math against mpmath, the same vectors through the cartridge in MAME, and the key-press UI test.
# Needs GENIO_MAME and GENIO_ROMPATH (see tests/run.sh). Run from the project directory after make.
# Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later
set -e
make -s tests/host
python3 tests/test_math.py tests/host | grep -v worst
python3 tests/mame_math.py 15 | tail -1
tests/run.sh tests/ui.txt mame/ui 200
grep -q "fail=0" mame/ui/drive.log
tests/run.sh tests/break.txt mame/break 30
grep -q "fail=0" mame/break/drive.log && grep -q "1 with bit 0 set" mame/break/drive.log
python3 -c "d=open('calc_gl2000_AT28C256_32K.bin','rb').read(); open('mame/nopage2_64K.bin','wb').write((d[:16384]+bytes([255])*16384)*2)"
CT_CART=$(pwd)/mame/nopage2_64K.bin tests/run.sh tests/nopage2.txt mame/nopage2 10
grep -q "fail=0" mame/nopage2/drive.log && grep -q "1 with bit 0 set" mame/nopage2/drive.log
