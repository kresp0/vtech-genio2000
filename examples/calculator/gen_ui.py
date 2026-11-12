#!/usr/bin/env python3
# User interface tables for the calculator (imported by gen_tables.py): key maps, CGRAM glyphs, help pages,
# function catalog and constants list. All text is in LCD codes; {name} stands for a special glyph (SYM below).
# Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later

SYM = {"inv": 0x08, "sq": 0x09, "cube": 0x0A, "sto": 0x0B, "int": 0x0C, "sum": 0x0D, "E": 0x0E, "xrt": 0x0F,
       "deg": 0xB2, "x": 0xB7, "/": 0xB8, "sqrt": 0xBE, "pi": 0xED, "U": 0x9A, "?": 0x9F}

# CGRAM slots 0-7 (shown at codes 0x08-0x0F)
GLYPHS = [
    ["...#.", "...#.", "##.#.", "...#.", "...#.", ".....", ".....", "....."],    # -1 superscript
    [".##..", "#..#.", "..#..", ".#...", "####.", ".....", ".....", "....."],    # squared
    ["###..", "...#.", ".##..", "...#.", "###..", ".....", ".....", "....."],    # cubed
    [".....", "..#..", "...#.", "#####", "...#.", "..#..", ".....", "....."],    # store arrow
    ["...##", "..#..", "..#..", "..#..", "..#..", "..#..", "##...", "....."],    # integral
    ["#####", "#....", ".#...", "..#..", ".#...", "#....", "#####", "....."],    # sigma
    [".....", ".....", "####.", "#....", "###..", "#....", "####.", "....."],    # exponent mark
    ["#.#..", ".#...", "#.#.#", "....#", "#..#.", ".#.#.", "..#..", "....."],    # x-th root
]


def lcd(s):
    """text with {sym} escapes -> list of LCD codes"""
    out, i = [], 0
    while i < len(s):
        if s[i] == "{":
            j = s.index("}", i)
            out.append(SYM[s[i + 1:j]])
            i = j + 1
        else:
            assert 32 <= ord(s[i]) < 127, s
            out.append(ord(s[i]))
            i += 1
    return out


def cstr(codes):
    return '"' + "".join("\\x%02X" % c if c < 32 or c > 126 or chr(c) in '"\\?' else chr(c) for c in codes) + '"'


# commands (key table values >= 0xC0)
CMDS = "ENTER LEFT RIGHT HOME END DEL DELF CLEAR INS HELP UP DOWN HYP DRG DMS FD CONST FORMAT STATADD STATVIEW " \
       "CATALOG VARS BASE DEC RESET POWER".split()
CMD = {c: 0xC0 + i for i, c in enumerate(CMDS)}

STRINGS = []


def act(v):
    """a key action: a command name in capitals, or text to insert"""
    if v is None:
        return 0
    if v in CMD:
        return CMD[v]
    codes = tuple(lcd(v))
    if codes not in STRINGS:
        STRINGS.append(codes)
    return STRINGS.index(codes) + 1


# trig strings first, so HYP can recognise them by index (1..6)
for t in ["sin(", "cos(", "tan(", "asin(", "acos(", "atan("]:
    act(t)

# matrix 1: (col, row) -> normal, MAYUSCULAS, ALT
MAIN = {
    (1, 1): ("1", None, None), (2, 0): ("2", None, None), (2, 1): ("3", None, "-"), (3, 0): ("4", None, None),
    (3, 1): ("5", "%", "+"), (4, 0): ("6", "{/}", None), (4, 1): ("7", None, None), (5, 0): ("8", "{x}", "="),
    (5, 1): ("9", "(", None), (6, 0): ("0", ")", None),
    (5, 6): (".", "!", None), (5, 5): (",", None, None), (6, 5): ("^", None, None), (1, 6): (" ", " ", " "),
    (7, 4): ("ENTER", "ENTER", "ENTER"), (7, 2): ("LEFT", "HOME", "HOME"), (7, 3): ("RIGHT", "END", "END"),
    (7, 5): ("DEL", "DELF", "DELF"), (1, 7): ("INS", "INS", "INS"), (6, 1): ("CLEAR", "CLEAR", "CLEAR"),
    (7, 6): ("Ans", "Ans", "Ans"), (0, 0): ("HELP", "HELP", "HELP"),
    (6, 2): (None, None, "UP"), (6, 4): (None, None, "DOWN"),
}
LETTERS = {"Q": (1, 2), "W": (2, 7), "E": (2, 2), "R": (3, 7), "T": (3, 2), "Y": (4, 7), "U": (4, 2), "I": (5, 7),
           "O": (5, 2), "P": (6, 7), "A": (1, 3), "S": (2, 3), "D": (2, 4), "F": (3, 3), "G": (3, 4), "H": (4, 3),
           "J": (4, 4), "K": (5, 3), "L": (5, 4), "Z": (1, 4), "X": (2, 5), "C": (2, 6), "V": (3, 5), "B": (3, 6),
           "N": (4, 5), "M": (4, 6)}
for ch, pos in LETTERS.items():
    MAIN[pos] = (ch, ch.lower(), None)

# activity panel, in firmware code order (index = col * 5 + row - 8): label for help, normal, MAYUSCULAS, help text
ACT = [
    ("BUSCA LETRA", "sin(", "asin(", "sin asin"), ("RECUERDA", "cos(", "acos(", "cos acos"),
    ("PLURALES", "tan(", "atan(", "tan atan"), ("VERBOS", "HYP", "HYP", "hyperbol"),
    ("REVOLT.LETR", "DRG", "DMS", "DRG {deg}'\""),
    ("MISTERIOSA", "ln(", "e^(", "ln e^x"), ("DERIVADOS", "log(", "10^(", "log 10^x"),
    ("SINONIMOS", "{sqrt}(", "{cube}{sqrt}(", "{sqrt} {cube}{sqrt}"), ("ANTONIMOS", "{inv}", "!", "x{inv} x!"),
    ("LETRA LOCA", "{sq}", "{cube}", "x{sq} x{cube}"),
    ("NUEVA PALAB", "^", "{xrt}", "^ {xrt}"), ("TRUEQUE", "(", ",", "(  ,"), ("ALFAPUZZLE", ")", "{sto}", ")  {sto}"),
    ("REVOLTIJO", "{pi}", "e", "{pi}  e"), ("ACERTIJO", "{E}", "rnd(", "{E} rnd"),
    ("SUMA", "+", "+", "+"), ("RESTA", "-", "-", "-"), ("MULTIPLIC.", "{x}", "{x}", "{x}"),
    ("DIVISION", "{/}", "{/}", "{/}"), ("FRAC/DECIM", "FD", "FD", "a/b<>dec"),
    ("FRAC/PORC", "%", "mod(", "%  mod"), ("RATIOS", "ncr(", "npr(", "nCr nPr"),
    ("ALGEBRA", "solve(", "d/dx(", "solve d/dx"), ("REPASO", "UP", "DOWN", "history"),
    ("SIGNO PERD.", "abs(", "int(", "abs int"),
    ("CIENCIAS", "CONST", "CONST", "constants"), ("CINE Y TV", "FORMAT", "FORMAT", "fix/sci"),
    ("HISTORIA", "STATADD", "STATVIEW", "stat data"), ("GENERAL", "CATALOG", "CATALOG", "functions"),
    ("{?}QUE SOY?", "VARS", "VARS", "memories"),
    ("RELAMPAGO", "rand", "ranint(", "random"), ("BASIC", "BASE", "DEC", "hex bin.."),
    ("IMPRIMIR", "{int}(", "{sum}(", "{int}  {sum}"), ("CALCULADORA", "X", "=", "X  ="),
    ("CARTUCHOS", "gcd(", "lcm(", "gcd lcm"),
    (None, None, None, None), ("OFF", "POWER", "POWER", None), ("NIVEL", "RESET", "RESET", "reset all"),
    ("1 JUGADOR", "max(", "min(", "max min"), ("2 JUGADORES", "and(", "or(", "and or"),
]
assert len(ACT) == 40

HELP = """
SCIENTIFIC CALC
Type a formula, then
INTRO. AVANCE/RETRO-
CESO turn the pages.

Press a key of the
activity panel here
to see what it does.
AYUDA/INTRO: exit.

EDITING
RETROCESO AVANCE:
move. MAY+them: to
the start / the end.

DEL: erase left.
MAY+DEL: erase here.
INS: insert/replace.
BORRAR: clear line.

INTRO on an empty
line repeats the
last one. ALT+{U} and
ALT+; : history.

After a result, an
operator key starts
with Ans: {x}2 gives
Ans{x}2.

TYPING RESPUESTA:Ans
A-Z: 26 memories.
MAY+letter: small
letter (functions).

MAY+5 %   MAY+6 {/}
MAY+8 {x}   MAY+9 (
MAY+0 )   MAY+. !
ALT+3 -  ALT+5 +

ALT+8 =   ' : ^
The panel keys give
the rest. MAYUSCULAS
+key: 2nd function.

PANEL KEYS
(key, then with
MAYUSCULAS held)

@1

@2

@3

@4

@5

@6

@7

@8

@9

@10

ORDER
2+3{x}4=14, -2{sq}=-4
1{/}2{pi} = 1{/}(2{pi})
2^3^2 = 2^9

Missing ) at the end
are added. Errors
put the cursor where
the problem is.

MEMORIES
5{sto}A stores 5 in A.
2A{sq} = 2{x}A{sq}
Ans: last result.

SOLVE (ALGEBRA)
solve(X{sq}-2,1)
solve(X{cube}=8,1)
root near 1, into X

CALCULUS
{int}(X{sq},0,3) = 9
d/dx(sin(X),0)
{sum}(X,1,100) = 5050

These use X. BORRAR
stops a long one.
Integrals: Gauss
5 points, adaptive.

MODES
REVOLT.LETRAS: DEG
RAD GRA. CINE Y TV:
NORM FIX SCI ENG.

FRAC/DECIM: result
as a fraction. MAY+
REVOLT.LETRAS: as
degrees {deg} ' ".

BASES (BASIC)
DEC HEX BIN OCT.
Numbers are typed in
that base: 0FF, 101.

Results show the
32-bit integer part.
and( or( xor( not(
work on 32 bits.

STATISTICS
Type x or x,y and
press HISTORIA.
MAY+HISTORIA: n,

means, deviations,
sums, y=a+bx and r.
BORRAR there clears
the data.

LISTS
CIENCIAS constants,
GENERAL functions,
{?}QUE SOY? memories.

AVANCE/RETROCESO
move; INTRO puts the
value or name in the
formula.

NIVEL clears all the
memories and modes.
Numbers: 16 digits,
12 shown, to 9{E}499

FUNCTIONS
Panel keys type them
or MAY+letters: the
names in small type.

sin cos tan: angle
in the mode (DEG RAD
GRA). asin acos atan
answer in that mode.

sinh cosh tanh and
asinh acosh atanh:
hyperbolic (VERBOS
then the trig key).

ln(x) base e, log(x)
base 10. e^( 10^( :
powers. x^y: ^ key,
y can be any number.

{sqrt}x square root,
{cube}{sqrt}x cube root,
3{xrt}8 = 2 any root,
(-8)^(1{/}3) = -2.

x{sq} x{cube} x{inv} : the
panel keys. x! and
gamma(x) work for
non-integers too.

abs int frac floor
rnd(x): rounds as
the display shows
it (FIX/SCI digits).

ncr(n,r) npr(n,r)
gcd(a,b) lcm(a,b)
mod(a,b) max(a,b)
min(a,b)

rand: 0 to 1.
ranint(a,b): integer
a to b. Seeded by
your key timing.

and or xor (a,b),
not(a): 32 bits,
two's complement:
not(0) = -1.

5% = 0.05, so
200{x}15% = 30.

EXAMPLES
2{pi}{x}3 = 18.8495..
1{E}3 = 1000 ({E} is
the ACERTIJO key).

2A = 2{x}A, and AB is
A{x}B: one letter is
one memory.

solve(X{sq}=2): with no
guess it starts at
the X stored. The
root stays in X.

{int}(f,a,b) uses X:
{int}(1{/}X,1,e) = 1
{sum}(f,a,b): a..b in
steps of 1.

d/dx(f,x): slope at
x. d/dx(X{cube},2) = 12
Done with central
differences.

ERRORS
Syntax: cursor shows
where. Math: outside
the domain (ln 0).

Overflow: from 1{E}500
(or base range).
Too complex: deeper
than the memory.

No root found: try
another guess.
Argument: a function
needs whole numbers.

SPEED  + - {x} {/}: fast
sin ln e^x: 0.5 s.
253!: 4 s. Integrals
take seconds.

BORRAR stops a long
calculation. OFF
switches off; idle 6
minutes: it does too
"""


def help_pages():
    pages = []
    for block in HELP.strip().split("\n\n"):
        rows = block.split("\n")
        if rows[0].startswith("@"):
            g = int(rows[0][1:]) - 1
            rows = []
            for i in range(4 * g, 4 * g + 4):
                a = ACT[i]
                if a[0] and a[3]:
                    n, d = len(lcd(a[0])), len(lcd(a[3]))
                    pad = min(max(11, n + 1), 20 - d)
                    assert pad > n, a
                    rows.append(a[0] + " " * (pad - n) + a[3])
                else:
                    rows.append("")
            pages.append(rows)
            continue
        pages.append(rows)
    return pages


CATALOG = [  # text inserted, help line
    ("sin(", "sine"), ("cos(", "cosine"), ("tan(", "tangent"), ("asin(", "arc sine"), ("acos(", "arc cosine"),
    ("atan(", "arc tangent"), ("sinh(", "hyperbolic sine"), ("cosh(", "hyperbolic cosine"),
    ("tanh(", "hyperbolic tangent"), ("asinh(", "inverse sinh"), ("acosh(", "inverse cosh"),
    ("atanh(", "inverse tanh"), ("ln(", "natural logarithm"), ("log(", "logarithm base 10"),
    ("e^(", "e to the power"), ("10^(", "10 to the power"), ("{sqrt}(", "square root"), ("{cube}{sqrt}(", "cube root"),
    ("{xrt}", "root: 3{xrt}8 = 2"), ("{inv}", "reciprocal 1/x"), ("!", "factorial (x!)"),
    ("gamma(", "gamma function"), ("abs(", "absolute value"), ("int(", "integer part"),
    ("frac(", "fractional part"), ("floor(", "round down"), ("rnd(", "round as displayed"),
    ("ncr(", "combinations n,r"), ("npr(", "permutations n,r"), ("gcd(", "greatest common div."),
    ("lcm(", "least common mult."), ("mod(", "remainder a,b"), ("max(", "larger of a,b"),
    ("min(", "smaller of a,b"), ("rand", "random 0 to 1"), ("ranint(", "random integer a..b"),
    ("and(", "bitwise and (32 bit)"), ("or(", "bitwise or"), ("xor(", "bitwise xor"), ("not(", "bitwise not"),
    ("solve(", "solve(f,guess): f=0"), ("{int}(", "integral: f,a,b"), ("d/dx(", "derivative: f,x"),
    ("{sum}(", "sum: f,a,b"), ("{sto}", "store: 5{sto}A"), ("%", "percent: x/100"), ("e", "e = 2.71828..."),
    ("{pi}", "pi = 3.14159..."),
]

CONSTS = [  # name, value (as typed), help line. CODATA 2018 and exact definitions
    ("c", "299792458", "light speed m/s"), ("h", "6.62607015{E}-34", "Planck J s"),
    ("hbar", "1.054571817{E}-34", "reduced Planck J s"), ("qe", "1.602176634{E}-19", "elementary charge C"),
    ("me", "9.1093837015{E}-31", "electron mass kg"), ("mp", "1.67262192369{E}-27", "proton mass kg"),
    ("mn", "1.67492749804{E}-27", "neutron mass kg"), ("u", "1.6605390666{E}-27", "atomic mass unit kg"),
    ("NA", "6.02214076{E}23", "Avogadro 1/mol"), ("k", "1.380649{E}-23", "Boltzmann J/K"),
    ("R", "8.314462618", "gas constant J/molK"), ("F", "96485.33212", "Faraday C/mol"),
    ("G", "6.6743{E}-11", "gravitation m3/kgs2"), ("g", "9.80665", "std gravity m/s2"),
    ("eps0", "8.8541878128{E}-12", "permittivity F/m"), ("mu0", "1.25663706212{E}-6", "permeability N/A2"),
    ("sigma", "5.670374419{E}-8", "Stefan-Boltzmann"), ("a0", "5.29177210903{E}-11", "Bohr radius m"),
    ("Rinf", "10973731.56816", "Rydberg 1/m"), ("Vm", "0.02241396954", "molar vol. m3/mol"),
    ("atm", "101325", "standard atm. Pa"), ("T0", "273.15", "0 Celsius in K"),
    ("inch", "0.0254", "inch in m"), ("foot", "0.3048", "foot in m"), ("mile", "1609.344", "mile in m"),
    ("nmi", "1852", "nautical mile in m"), ("lb", "0.45359237", "pound in kg"),
    ("oz", "0.028349523125", "ounce in kg"), ("gal", "3.785411784", "US gallon in L"),
    ("cal", "4.184", "calorie in J"), ("eV", "1.602176634{E}-19", "electronvolt in J"),
    ("ly", "9.4607304725808{E}15", "light year in m"), ("au", "149597870700", "astronomical unit m"),
    ("hp", "745.69987158227", "horsepower in W"),
]


def gen():
    o = ["// generated by gen_tables.py (gen_ui.py)"]
    o.append("static const byte glyphs[64] = {%s};" % ",".join(
        "0x%02X" % int(r.replace(".", "0").replace("#", "1"), 2) for g in GLYPHS for r in g))
    main = [[0, 0, 0] for _ in range(64)]
    for (c, r), v in MAIN.items():
        main[r * 8 + c] = [act(x) for x in v]
    actt = []
    for a in ACT:
        actt.append([act(a[1]), act(a[2])])
    o.append("static const byte keymain[64][3] = {%s};" % ",".join("{%d,%d,%d}" % tuple(m) for m in main))
    o.append("static const byte keyact[40][2] = {%s};" % ",".join("{%d,%d}" % tuple(m) for m in actt))
    for c, v in CMD.items():
        o.append("#define CM_%s 0x%02X" % (c, v))
    for c in CATALOG:
        act(c[0])
    # page 2: help pages, catalog help, constants (tables of addresses, see gen_tables.py)
    pages = help_pages()
    for p in pages:
        assert len(p) <= 4, p
        for r in p:
            assert len(lcd(r)) <= 20, r
    p2 = {"HELP": [sum((lcd(r) + [10] for r in p), [])[:-1] for p in pages]}
    o.append("#define NHELP %d" % len(pages))
    first = next(i for i, p in enumerate(HELP.strip().split("\n\n")) if p.startswith("@"))
    kp = []
    for i, a in enumerate(ACT):
        kp.append((first + i // 4) * 4 + i % 4 if a[0] and a[3] else 0xFF)
    o.append("static const byte keyhelp[40] = {%s};	// page * 4 + row" % ",".join(map(str, kp)))
    for c in CATALOG + CONSTS:
        assert len(lcd(c[-1])) <= 20, c
    o.append("#define NCAT %d\n#define NCST %d" % (len(CATALOG), len(CONSTS)))
    p2["CATH"] = [lcd(c[1]) for c in CATALOG]
    p2["CSTN"] = [lcd(c[0]) for c in CONSTS]
    p2["CSTV"] = [lcd(c[1]) for c in CONSTS]
    p2["CSTH"] = [lcd(c[2]) for c in CONSTS]
    o.append("static const byte cat_str[NCAT] = {%s};" % ",".join(str(act(c[0])) for c in CATALOG))
    o.append("#define NSTR %d" % len(STRINGS))
    p2["STR"] = [list(s) for s in STRINGS]
    o.append('#define STR_ANS %d' % (STRINGS.index(tuple(lcd("Ans"))) + 1))
    assert len(STRINGS) < 0xC0
    return "\n".join(o) + "\n", p2


if __name__ == "__main__":
    print(gen())
