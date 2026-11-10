#!/bin/bash
# check_pr_series.sh – builds each branch of the small PR series (stacked on origin/master) and checks it: warnings in pc2000.cpp, -validate, ROM listing; the last one (the full
# candidate) also gets the tests that do not need the experimental options and a check that it carries none; then returns to genio2000-dev and rebuilds mame/genio.
# Aborts if the MAME tree has local changes.  Branches: genio2000-pr1-system, -pr2-keyboard, -pr3-cgrom, -pr4-lcd, -pr5-power, -pr6-led, -pr7-speaker, -pr8-contrast.
set -e; H=$(cd "$(dirname "$0")/.." && pwd); cd "$H/mame"
[ -z "$(git status --porcelain)" ] || { echo "mame/ has uncommitted changes: commit or stash first"; exit 1; }
START=$(git rev-parse --abbrev-ref HEAD); export CPATH=$H/deps/inc LIBRARY_PATH=$H/deps/lib
MK="make SUBTARGET=genio SOURCES=src/mame/vtech/pc2000.cpp USE_QTDEBUG=0 NOWERROR=1 TOOLS=0 -j20"
BRANCHES='genio2000-pr1-system genio2000-pr2-keyboard genio2000-pr3-cgrom genio2000-pr4-lcd genio2000-pr5-power genio2000-pr6-led genio2000-pr7-speaker genio2000-pr8-contrast'; LAST=genio2000-pr8-contrast
BASE=$(git merge-base origin/master $LAST); echo "base: $(git log --oneline -1 $BASE)"
for b in $BRANCHES; do
  git checkout -q $b; touch src/mame/vtech/pc2000.cpp; $MK > ../logs/build_$b.log 2>&1
  echo "== $b: $(git log --oneline $BASE..$b | wc -l) commit(s) on the base, files: $(git diff --name-only $BASE $b | tr '\n' ' '), warnings in pc2000.cpp: $(grep -c 'pc2000.cpp.*warning' ../logs/build_$b.log)"
  ./genio -validate && echo "   -validate OK"; ./genio -listroms genio2000 | sed -n 3,5p
  cp genio genio_$b
done
cp genio_$LAST genio_candidate
! strings genio_candidate | grep -q -E "experimental|Sound model|CPU clock \(" && echo "no experimental option strings in the candidate binary"
git checkout -q "$START"; $MK > ../logs/build_dev_final.log 2>&1
cd "$H"; GENIO_MAME=$H/mame/genio_candidate GENIO_CANDIDATE=1 python3 -m pytest -q tests -p no:cacheprovider | tail -3
