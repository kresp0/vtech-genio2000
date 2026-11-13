#!/bin/sh
# Baud tolerance table, run by tests/run_mame.sh <dir> with EN_CHECK=tests/tolerance.sh: for each rate, packets
# sent with the PC clock off by -7 .. +7 % (the Genio's answers are decoded at the nominal rate).
# EN_BAUDS limits the rates; give MAME time with EN_SECONDS (the full table needs about 900 s).
# Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later
export PCLINK_MAME_QUIT=0
DIR=${EN_PY##* }
cur=76800
for b in ${EN_BAUDS:-2400 4800 9600 19200}; do
  $EN_PY --baud $cur baud $b > /dev/null; cur=$b
  line="$b:"
  for s in -7 -6 -5 -4 -3 -2 0 2 3 4 5 6 7; do
    f=$($EN_PY --baud $b --skew $s test -n ${EN_N:-6} --min 100 --max 240 | sed -n 's/.* \([0-9]*\) failed;.*/\1/p')
    line="$line $s%:${f:-?}"
  done
  echo "$line"
done
$EN_PY --baud $cur baud 76800 > /dev/null
echo quit >> "$DIR/ctl.txt"
