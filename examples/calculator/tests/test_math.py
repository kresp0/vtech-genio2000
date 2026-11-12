#!/usr/bin/env python3
# Compares the calculator's math (tests/host, the same C code the cartridge runs) against mpmath, and checks the
# display formats and the parser on fixed cases. Usage: python3 tests/test_math.py [path to host binary]
# Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later
import os
import random
import subprocess
import sys

import mpmath as mp

mp.mp.dps = 40
HOST = os.environ.get("CT_HOST") or (sys.argv[1] if len(sys.argv) > 1 and __name__ == "__main__" else "tests/host")
TOL = mp.mpf("3e-14")       # relative; the display shows 12 digits


def run(lines):
    out = subprocess.run([HOST], input="\n".join(lines) + "\n", capture_output=True, text=True, check=True).stdout
    return out.splitlines()


def value(line):
    p = line.split(" ", 3)
    if p[0] != "R":
        return None
    return mp.mpf(p[1][0] + "0." + p[1][1:]) * mp.power(10, int(p[2]))


def lit(x):
    s = mp.nstr(x, 16, min_fixed=-30, max_fixed=30).replace("e", "{E}").replace("+", "")
    return "(" + s + ")" if s.startswith("-") else s


rnd = random.Random(2026)
deg = mp.pi / 180


def u(a, b):
    return mp.mpf(rnd.uniform(a, b))


def lu(a, b):      # log-uniform magnitude
    return mp.power(10, u(a, b))


# (template, generator of args, reference, angle mode 0 deg / 1 rad)
CASES = [
    ("{}+{}", lambda: (u(-1e6, 1e6), lu(-20, 20)), lambda a, b: a + b),
    ("{}-{}", lambda: (lu(-5, 5), lu(-5, 5)), lambda a, b: a - b),
    ("{}{{x}}{}", lambda: (u(-1e3, 1e3), lu(-100, 100)), lambda a, b: a * b),
    ("{}{{/}}{}", lambda: (u(-1e3, 1e3), lu(-100, 100)), lambda a, b: a / b),
    ("{{sqrt}}({})", lambda: (lu(-300, 300),), mp.sqrt),
    ("{{3}}{{sqrt}}({})", lambda: (u(-1e6, 1e6),), lambda a: mp.sign(a) * mp.cbrt(abs(a))),
    ("ln({})", lambda: (lu(-400, 400),), mp.log),
    ("ln({})", lambda: (u(0.5, 1.5),), mp.log),
    ("log({})", lambda: (lu(-400, 400),), mp.log10),
    ("e^({})", lambda: (u(-1100, 1100),), mp.exp),
    ("e^({})", lambda: (u(-2, 2),), mp.exp),
    ("10^({})", lambda: (u(-300, 300),), lambda a: mp.power(10, a)),
    ("{}^{}", lambda: (lu(-3, 3), u(-30, 30)), mp.power),
    ("{}^{}", lambda: (u(-9, 9), mp.mpf(rnd.randint(-12, 12))), mp.power),
    ("sin({})", lambda: (u(-1000, 1000),), lambda a: mp.sin(a * deg)),
    ("cos({})", lambda: (u(-1000, 1000),), lambda a: mp.cos(a * deg)),
    ("tan({})", lambda: (u(-89, 89),), lambda a: mp.tan(a * deg)),
    ("asin({})", lambda: (u(-1, 1),), lambda a: mp.asin(a) / deg),
    ("acos({})", lambda: (u(-1, 1),), lambda a: mp.acos(a) / deg),
    ("atan({})", lambda: (u(-50, 50),), lambda a: mp.atan(a) / deg),
    ("sin({})", lambda: (u(-100, 100),), mp.sin, 1),
    ("cos({})", lambda: (u(-100, 100),), mp.cos, 1),
    ("tan({})", lambda: (u(-1.5, 1.5),), mp.tan, 1),
    ("atan({})", lambda: (lu(-10, 10),), mp.atan, 1),
    ("sinh({})", lambda: (u(-20, 20),), mp.sinh),
    ("sinh({})", lambda: (lu(-12, 0),), mp.sinh),
    ("cosh({})", lambda: (u(-20, 20),), mp.cosh),
    ("tanh({})", lambda: (u(-5, 5),), mp.tanh),
    ("asinh({})", lambda: (u(-1e4, 1e4),), mp.asinh),
    ("asinh({})", lambda: (lu(-12, 0),), mp.asinh),
    ("acosh({})", lambda: (u(1, 1e4),), mp.acosh),
    ("atanh({})", lambda: (u(-0.999, 0.999),), mp.atanh),
    ("gamma({})", lambda: (u(-20, 60),), mp.gamma),
    ("{}!", lambda: (u(0, 100),), mp.factorial),
    ("{}!", lambda: (mp.mpf(rnd.randint(0, 250)),), mp.factorial),
]


def math_cases(n=40):
    lines, refs = [], []
    for c in CASES:
        tmpl, gen, ref = c[:3]
        ang = c[3] if len(c) > 3 else 0
        lines.append("!ang %d" % ang); refs.append(None)
        for _ in range(n):
            args = gen()
            args = [mp.mpf(lit(a).strip("()").replace("{E}", "e")) for a in args]   # what the calculator reads
            lines.append(tmpl.format(*[lit(a) for a in args]))
            refs.append((tmpl, args, ref(*args)))
    out = run(lines)
    bad = 0
    worst = {}
    for line, ref, res in zip(lines, refs, out):
        if ref is None:
            continue
        v = value(res)
        exact = ref[2]
        if v is None:
            if abs(exact) < mp.mpf("1e499"):
                print("FAIL", line, res); bad += 1
            continue
        err = abs(v - exact) / abs(exact) if exact else abs(v)
        if exact and abs(exact) < mp.mpf("1e-490"):
            continue
        # near the zeros of sin/cos/tan the absolute error is what counts
        if ref[0].split("(")[0] in ("sin", "cos", "tan", "sinh", "atan") and abs(exact) < 1e-3:
            err = abs(v - exact)
        worst[ref[0]] = max(worst.get(ref[0], 0), err)
        if err > (TOL * 4 if ref[0] in ("{}^{}", "gamma({})", "{}!") else TOL):
            print("FAIL %s -> %s (exact %s, rel %s)" % (line, res, mp.nstr(exact, 18), mp.nstr(err, 3))); bad += 1
    for k, v in worst.items():
        print("  %-22s worst %s" % (k, mp.nstr(v, 2)))
    return bad


# exact cases: input, expected display (or ERR n)
FIXED = """
1+2|3
0.1+0.2|0.3
1-0.9-0.1|0
1{/}3{x}3|1
2{x}3+4{x}5|26
2+3{x}4^2|50
2^3^2|512
-2^2|-4
2^-1|0.5
-2{2}|-4
(-2){2}|4
1{/}2{pi}|0.159154943092
2{pi}|6.28318530718
3(4+5)|27
(1+2)(3+4)|21
2(3|6
5%|0.05
200{x}15%|30
3!|6
0!|1
2{-1}|0.5
3{3}|27
2{3}{sqrt}8|4
3{xrt}27|3
3{xrt}-8|-2
{sqrt}16|4
{sqrt}(2){2}|2
sin(30)|0.5
cos(60)|0.5
tan(45)|1
sin(180)|0
cos(90)|0
tan(90)|ERR 2
asin(1)|90
acos(-1)|180
atan(1)|45
ln(e)|1
log(1000)|3
log(0.001)|-3
e^(ln(7))|7
10^(log(5))|5
ln(0)|ERR 2
ln(-1)|ERR 2
{sqrt}(-1)|ERR 2
1{/}0|ERR 2
0^0|ERR 2
(-8)^(1{/}3)|-2
(-8)^0.5|ERR 2
10^500|ERR 3
10^-600|0
1{E}499{x}10|ERR 3
69!|1.71122452428{E}98
253!|5.17346099264{E}499
254!|ERR 3
ncr(10,3)|120
npr(10,3)|720
ncr(52,5)|2598960
gcd(84,36)|12
lcm(4,6)|12
mod(17,5)|2
mod(-17,5)|3
max(3,7)|7
min(3,-7)|-7
abs(-2.5)|2.5
int(-2.5)|-2
frac(-2.5)|-0.5
floor(-2.5)|-3
gamma(0.5){2}|3.14159265359
and(12,10)|8
or(12,10)|14
xor(12,10)|6
not(0)|-1
5{sto}A|5
A{2}|25
2A|10
AA|25
Ans+1|26
X|0
solve(X{2}-2,1)|1.41421356237
solve(X{2}=2,-1)|-1.41421356237
solve(cos(X)=X{x}0+0.5,10)|60
solve(e^(X)+1,0)|ERR 6
solve(X{2},1)|ERR 0
solve(X{3}-X,0.4)|ERR 0
{int}(X{2},0,3)|9
{int}(sin(X),0,180)|ERR 0
d/dx(X{3},2)|12
{sum}(X,1,100)|5050
{sum}(X{2},1,10)|385
sin(|ERR 1
2++|ERR 1
)|ERR 1
3,4|ERR 1
foo(2)|ERR 1
1.2.3|ERR 1
""".strip().splitlines()

FMT = [  # (setup, input, expected display)
    ("!fmt 1 2", "1{/}3", "0.33"),
    ("!fmt 1 2", "2{/}3", "0.67"),
    ("!fmt 1 0", "2.5", "3"),
    ("!fmt 1 4", "0", "0.0000"),
    ("!fmt 1 2", "1{E}20", "1{E}20"),
    ("!fmt 1 2", "0.001", "0.00"),
    ("!fmt 1 2", "0.005", "0.01"),
    ("!fmt 2 3", "123456", "1.23{E}5"),
    ("!fmt 2 3", "-0.00012345", "-1.23{E}-4"),
    ("!fmt 3 0", "123456", "123.456{E}3"),
    ("!fmt 3 0", "0.0012", "1.2{E}-3"),
    ("!fmt 3 0", "12", "12"),
    ("!fmt 0 0", "1{E}12", "1{E}12"),
    ("!fmt 0 0", "999999999999", "999999999999"),
    ("!fmt 0 0", "-0.0000012345", "-0.0000012345"),
    ("!fmt 0 0", "1{E}-7", "1{E}-7"),
    ("!fmt 0 0", "2{/}3{x}1{E}-200", "6.66666666667{E}-201"),
]


def fixed_cases():
    bad = 0
    lines = ["!fmt 0 0", "!ang 0", "!base 0"] + [l.split("|")[0] for l in FIXED]
    out = run(lines)[3:]
    for l, res in zip(FIXED, out):
        inp, exp = l.split("|")
        if exp.startswith("ERR"):
            got = " ".join(res.split()[:2]) if res.startswith("ERR") else res
            ok = got == exp if exp != "ERR 0" else not res.startswith("ERR")   # ERR 0 = "no error, any value"
        else:
            got = res.split(" ", 3)[3] if res.startswith("R") else res
            ok = got == exp
        if not ok:
            print("FAIL %-28s want %-20s got %s" % (inp, exp, res)); bad += 1
    lines = []
    for setup, inp, exp in FMT:
        lines += [setup, inp]
    out = run(lines)
    for i, (setup, inp, exp) in enumerate(FMT):
        res = out[2 * i + 1]
        got = res.split(" ", 3)[3] if res.startswith("R") else res
        if got != exp:
            print("FAIL %s %-20s want %-16s got %s" % (setup, inp, exp, res)); bad += 1
    # fractions, DMS, bases
    extra = [
        (["!fmt 0 0", "1{/}3", "!frac"], "F 1 1/3"), (["0.75", "!frac"], "F 1 3/4"),
        (["-355{/}113", "!frac"], "F 1 -355/113"), (["{pi}", "!frac"], "F 0 "), (["2", "!frac"], "F 0 "),
        (["12.5042", "!dms"], "F 1 12{deg}30'15.12\""), (["-0.5", "!dms"], "F 1 -0{deg}30'0\""),
        (["29.99999999", "!dms"], "F 1 30{deg}0'0\""),
        (["!base 1", "0FF+1", "!base 0"], "R +2560000000000000 3 100"),
        (["!base 1", "0FFFFFFFF", "!base 0"], "R -1000000000000000 1 FFFFFFFF"),
        (["!base 2", "1010{x}11", "!base 0"], "R +3000000000000000 2 11110"),
        (["!base 3", "777+1", "!base 0"], "R +5120000000000000 3 1000"),
        (["!base 1", "2{x}10{E}9", "!base 0"], "R +3200000000000000 11 ERR 3 -1"),
    ]
    for cmds, exp in extra:
        out = run(cmds)
        got = [o for o in out if o != "OK"][-1]
        if got.strip() != exp.strip():
            print("FAIL %s want %s got %s" % (cmds, exp, got)); bad += 1
    return bad


if __name__ == "__main__":
    bad = fixed_cases()
    print("fixed cases: %d failures" % bad)
    b2 = math_cases()
    print("random cases: %d failures" % b2)
    sys.exit(1 if bad + b2 else 0)
