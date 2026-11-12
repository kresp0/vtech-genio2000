#!/bin/sh
# Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later
# Runs Sistema > IRQ period and Interrupt with the experimental CLOCK / IRQ switches of the MAME dev build.
# From Lua any nonzero value selects the first alternative (40 Hz, 3.000 MHz), so only 0 and 1 are used.
cd "$(dirname "$0")/.."
for irq in 0 1; do for clk in 0 1; do
  d=mame/irq_sel${irq}_clk${clk}
  DG_CFG="Periodic interrupt rate (experimental, real value unknown)=$irq;CPU clock (experimental)=$clk" \
    tests/run.sh tests/irq2.txt $d 25 >/dev/null
  echo "irq sel $irq clock sel $clk: $(grep -A3 '^--- periodo' $d/drive.log | sed -n 3,4p | tr '\n' ' ')"
done; done
