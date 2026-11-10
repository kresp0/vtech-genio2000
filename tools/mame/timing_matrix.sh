#!/bin/bash
# timing_matrix.sh [outdir]   default logs/timing/emulation – boot and power-off scenarios for the reference runs and the IRQ-rate sweep.
set -e; H=$(cd "$(dirname "$0")/.." && pwd); cd "$H"; O=${1:-logs/timing/emulation}; mkdir -p "$O"
CSV=$O/summary.csv; echo "scenario,clock_MHz,irq_Hz,summary_json" > $CSV
clk=(6.13179 3.0 3.579545 4.194304 4.9152 5.0 6.0 6.144 8.0 4.0); irq=(50 40 45 55 60 75 100)
for sc in boot off; do for pair in "9 0" "6 0" "6 1" "6 4" "9 1" "9 4" "7 0" "0 0"; do set -- $pair
  n=${sc}_clk${clk[$1]}MHz_irq${irq[$2]}Hz; j=$(tools/timing_run.sh $sc $1 $2 "$O/$n"); echo "$sc,${clk[$1]},${irq[$2]},\"${j//\"/\"\"}\"" >> $CSV; echo "$n $j"; done; done
