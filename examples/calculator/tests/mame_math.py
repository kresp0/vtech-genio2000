#!/usr/bin/env python3
# Runs the expression vectors of test_math.py through the cartridge in headless MAME (the Z80 assembly core and
# the microcode as built) and through tests/host (the C core), and checks that both give the same 16 digits,
# exponent and display text, or the same error.
# Usage: GENIO_MAME=... GENIO_ROMPATH=... python3 tests/mame_math.py [cases per function]
# Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
import test_math as tm

ERRMSG = {1: "Syntax error", 2: "Math error", 3: "Overflow", 4: "Too complex", 5: "Break", 6: "No root found",
          7: "Argument error"}
n = int(sys.argv[1]) if len(sys.argv) > 1 else 15

lines = [l.split("|")[0] for l in tm.FIXED]
for c in tm.CASES:
    tmpl, gen = c[:2]
    ang = c[3] if len(c) > 3 else 0
    lines.append("!ang %d" % ang)
    for _ in range(n):
        lines.append(tmpl.format(*[tm.lit(a) for a in gen()]))

host = [l for l in tm.run(["!fmt 0 0"] + lines) if l != "OK"]
exprs = [l for l in lines if not l.startswith("!")]
assert len(host) == len(exprs)

# angle mode changes become presses of REVOLTIJO DE LETRAS (DEG -> RAD -> GRA -> DEG)
vec, ang = [], 0
for l in lines:
    if l.startswith("!ang "):
        want = int(l[5:])
        while ang != want:
            vec.append("!press REVOLTIJO DE LETRAS"); ang = (ang + 1) % 3
    else:
        vec.append(l)
os.makedirs("mame", exist_ok=True)
open("mame/vectors.txt", "w").write("\n".join(vec) + "\n")
open("mame/vectors_script.txt", "w").write("wait 1.5\nevalfile mame/vectors.txt\nquit\n")
env = dict(os.environ, CT_OUT=os.path.abspath("mame/vectors_out.txt"))
subprocess.run(["tests/run.sh", "mame/vectors_script.txt", "mame/vectors", "3000"], env=env, check=True)
got = open("mame/vectors_out.txt").read().splitlines()

bad = 0
slow = []
for e, h, m in zip(exprs, host, got):
    mres, _, rest = m.partition("  [")
    secs = float(rest.split("s]")[0]) if rest else 0
    slow.append((secs, e))
    if h.startswith("ERR"):
        want = "ERR " + ERRMSG[int(h.split()[1])]
    else:
        want = h
    if mres != want:
        print("DIFF %-40s host %-40s mame %s" % (e, want, mres)); bad += 1
if len(got) != len(exprs):
    print("MAME gave %d results for %d expressions" % (len(got), len(exprs))); bad += 1
slow.sort(reverse=True)
print("slowest (MAME seconds, including the key press):")
for s, e in slow[:8]:
    print("  %6.2f  %s" % (s, e))
print("%d expressions, %d differences" % (len(exprs), bad))
sys.exit(1 if bad else 0)
