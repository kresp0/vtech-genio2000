#!/bin/sh
# The MAME check run by tests/run_mame.sh: every pclink.py command against the cartridge through the virtual cable.
# EN_PY = "python3 pclink.py --mame DIR"; prints PASS/FAIL per step and exits with the number of failures.
# Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later
FAIL=0
export PCLINK_MAME_QUIT=0
DIR=${EN_PY##* }
step() {   # step <grep pattern or -> <pclink.py args...>
  pat=$1; shift
  echo "== $*"
  out=$($EN_PY "$@" 2>&1); rc=$?
  echo "$out" | sed 's/^/   /'
  if [ $rc -ne 0 ] || { [ "$pat" != "-" ] && ! echo "$out" | grep -q -- "$pat"; }; then
    echo "   FAIL"; FAIL=$((FAIL + 1))
  else
    echo "   PASS"
  fi
}
key() { echo "press $1" >> "$DIR/ctl.txt"; sleep 1; }

if [ "$EN_INVERT" = "1" ]; then
  echo "== ping --tries 2   (must get no answer: the cartridge starts with polarity A)"
  if $EN_PY ping --tries 2 > /dev/null 2>&1; then echo "   FAIL"; FAIL=$((FAIL + 1)); else echo "   PASS"; fi
  key P
  step "pol B" ping
else
  step "76800 baud pol A" ping                                       # the default rate
  for i in 1 2 3 4 5 6 7 8 9 10; do step "pol A" ping --tries 1; done    # first packet after an idle period
  step - send "Hello Genio 2000!"
  step "0 failed" test -n 40
  step "now at 9600" baud 9600
  step "0 failed" --baud 9600 --skew 3 test -n 20
  step "0 failed" --baud 9600 --skew -3 test -n 20
  step - --baud 9600 line --period 0.3 --count 3
  step "breaks 3" --baud 9600 ping
  step "now at 19200" --baud 9600 baud 19200
  step "0 failed" --baud 19200 --skew 2 test -n 20
  step "0 failed" --baud 19200 --skew -2 test -n 20
  step "now at 76800" --baud 19200 baud 76800
  step " 76800: 0/12 failed" sweep -n 12
  step "128000: 0/12 failed" sweep --experimental -n 12
  step "rising edges" scope 128000
  step "works from" margin -n 4
  step "76800 baud" ping
  step "now at 57600" baud 57600
  step "goes back to 76800" --baud 57600 reset          # a 3 s break brings the Genio back to the default rate
  step "76800 baud" ping
  key 4                                   # baud keys on the Genio
  step "19200 baud" --baud 19200 ping
  key 8
  step "115200 baud" --baud 115200 ping
  key 9
  step "128000 baud" --baud 128000 ping
  key 3
  step "9600 baud" --baud 9600 ping
  key 7
  step "76800 baud" ping
  key E                                   # echo off: raw text is shown but not sent back
  step "echo off" ping
  step - send --no-echo "no echo"
  key E
  key S                                   # statistics page
  step "echo on" ping
  key H
fi
echo "quit" >> "$DIR/ctl.txt"
echo "check: $FAIL failure(s)"
exit $FAIL
