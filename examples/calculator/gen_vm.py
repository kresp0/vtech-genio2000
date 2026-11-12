#!/usr/bin/env python3
# Assembler for the calculator's math microcode (run by vm.h) and the programs themselves: every function above
# the four operations is written here, at one or two bytes per step instead of a C call each.
# Machine: a stack of 16-digit numbers; a frame (arguments, then ALLOC'd locals) addressed by LD/ST n; a 16-bit
# counter vn; a flag f (-1, 0, 1) set by TST/CMP/ISINT/SMALL/HALVN and tested by the jumps. CALL label n makes the
# top n values the callee's frame; RET leaves the callee's top value in place of its frame (at the outer level RET
# just stops, leaving the stack for the C caller). vn and f are shared with callees.
# Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later

# grouped so that vm.h can dispatch through tables: binary, unary, the rest; then the jumps lead the 1-operand ops
BINARY = "ADD SUB MUL DIV".split()
UNARY = "NEG ABS INV TRUNC FLOOR ROUND RNDD FEVAL".split()
OPS0 = BINARY + UNARY + ("RET DUP DROP SWAP NINC DIVN PUSHN TOVN SCALE MANT TST CMP ISINT STX ANG QUAD HALVN RAND "
                         "UNDEF").split()
OPS1 = "JMP JEQ JNE JLT JGE JGT JLE LD ST K I NSET ALLOC SMALL ERR KN BIT".split()
OPS2 = ["JVN"]          # value, jump
OPS3 = ["CALL"]         # address (2 bytes), number of arguments
OPCODE = {}
for i, o in enumerate(OPS0 + OPS1 + OPS2 + OPS3):
    OPCODE[o] = i
FIRST1, FIRST2, FIRST3 = len(OPS0), len(OPS0) + len(OPS1), len(OPS0) + len(OPS1) + len(OPS2)
JUMPS = {"JMP", "JEQ", "JNE", "JLT", "JGE", "JGT", "JLE"}
ERRS = {"SYNTAX": 1, "MATH": 2, "OVER": 3, "COMPLEX": 4, "BREAK": 5, "NOROOT": 6, "ARG": 7}

PROGRAMS = r"""
# ---- parser entry points: f_<name>, arguments in slots 0 (and 1)
sinr:    I 0; ALLOC 3; NSET 1; JMP trg2     # sine in radians whatever the mode
f_sin:   I 0; JMP trg
f_cos:   I 1; JMP trg
f_tan:   I 2
trg:     ALLOC 3; ANG                       # 1 which, 2 q, 3 s, 4 c (quarter turn while reducing)
trg2:    JVN 1 tr
         I 90; JVN 0 td; DROP; I 100
td:      DUP; ST 4; LD 0; SWAP; DIV; ROUND; ST 2
         LD 2; ABS; K 1E15; CMP; JGT terr
         LD 0; LD 2; LD 4; MUL; SUB
         K PI180; JVN 0 td2; DROP; K PI200
td2:     MUL; ST 3; JMP tq
tr:      LD 0; K PI2; DIV; ROUND; ST 2
         LD 2; ABS; K 1E9; CMP; JGT terr
         LD 0; LD 2; K PI2A; MUL; SUB; LD 2; K PI2B; MUL; SUB; ST 3
tq:      LD 3; I 0; I 1; CALL tsc 3; LD 3; I 1; I 1; CALL tsc 3; ST 4; ST 3
         LD 2; QUAD
         HALVN; JEQ tq1
         LD 4; LD 3; NEG; ST 4; ST 3       # quadrant 1, 3: (s, c) = (c, -s)
tq1:     HALVN; JEQ tq2
         LD 3; NEG; ST 3; LD 4; NEG; ST 4
tq2:     LD 1; TOVN; JVN 0 ts; JVN 1 tc
         LD 3; LD 4; DIV; RET
ts:      LD 3; RET
tc:      LD 4; RET
terr:    ERR MATH

# sum of x^(2k+1)/(2k+1)! (or x^2k/(2k)! when cos), alternating when alt: tsc(x, cos, alt)
tsc:     ALLOC 3                            # 3 x2, 4 term, 5 sum
         LD 0; DUP; MUL; ST 3; NSET 2; LD 0
         LD 1; TST; JEQ s1; DROP; I 1; NSET 1
s1:      DUP; ST 4; ST 5
s2:      LD 4; LD 3; MUL; DIVN; NINC; DIVN; NINC
         LD 2; TST; JEQ s3; NEG
s3:      DUP; ST 4; DUP; SMALL 5; JEQ s4
         LD 5; ADD; ST 5; JMP s2
s4:      DROP; LD 5; RET

# sum of z^(2k+1)/(2k+1), alternating when alt: atanh (alt 0) or atan (alt 1); tat(z, alt)
tat:     ALLOC 2                            # slot 0 is the sum; 2 z2, 3 power
         LD 0; DUP; MUL; ST 2; LD 0; ST 3; NSET 3
ta1:     LD 3; LD 2; MUL; LD 1; TST; JEQ ta2; NEG
ta2:     DUP; ST 3; DIVN; NINC; NINC; DUP; SMALL 0; JEQ ta3
         LD 0; ADD; ST 0; JMP ta1
ta3:     DROP; LD 0; RET

# radians to the angle mode
frad:    ANG; JVN 1 fr1
         LD 0; K 180PI; JVN 0 fr2; DROP; K 200PI
fr2:     MUL; RET
fr1:     LD 0; RET

f_atan:  LD 0; CALL atr 1; CALL frad 1; RET
atr:     ALLOC 3                            # 1 inverted, 2 plus pi/6, 3 x; slot 0 becomes |x|
         LD 0; ST 3; LD 0; ABS; ST 0
         LD 0; I 1; CMP; JLE a1
         LD 0; INV; ST 0; I 1; ST 1
a1:      LD 0; K TAN15; CMP; JLE a2
         LD 0; K SQRT3; MUL; I 1; SUB; LD 0; K SQRT3; ADD; DIV; ST 0; I 1; ST 2
a2:      LD 0; I 1; CALL tat 2
         LD 2; TST; JEQ a3; K PI2; NSET 3; DIVN; ADD
a3:      LD 1; TST; JEQ a4; K PI2; SWAP; SUB
a4:      LD 3; TST; JGE a5; NEG
a5:      RET

f_asin:  LD 0; ABS; I 1; CMP; JGT merr; JLT as1
         K PI2; LD 0; TST; JGE as0; NEG
as0:     CALL frad 1; RET
as1:     I 1; LD 0; SUB; I 1; LD 0; ADD; MUL; CALL f_sqrt 1; LD 0; SWAP; DIV; CALL f_atan 1; RET
merr:    ERR MATH
f_acos:  LD 0; ABS; I 1; CMP; JGT merr
         I 1; LD 0; ADD; DUP; TST; JNE ac1
         DROP; K PI; CALL frad 1; RET
ac1:     I 1; LD 0; SUB; SWAP; DIV; CALL f_sqrt 1; CALL atr 1; DUP; ADD; CALL frad 1; RET

f_sinh:  LD 0; ABS; I 1; CMP; JGE sh1
         LD 0; I 0; I 0; CALL tsc 3; RET
sh1:     LD 0; CALL f_exp 1; DUP; INV; SUB; NSET 2; DIVN; RET
f_cosh:  LD 0; CALL f_exp 1; DUP; INV; ADD; NSET 2; DIVN; RET
f_tanh:  LD 0; ABS; I 100; CMP; JLE th1
         I 1; LD 0; TST; JGE th0; NEG
th0:     RET
th1:     LD 0; CALL f_sinh 1; LD 0; CALL f_cosh 1; DIV; RET
f_asinh: LD 0; DUP; MUL; I 1; ADD; CALL f_sqrt 1
         LD 0; ABS; I 1; CMP; JGE ash1
         LD 0; SWAP; DIV; CALL f_atanh 1; RET
ash1:    LD 0; ABS; ADD; CALL f_ln 1; LD 0; TST; JGE ash2; NEG
ash2:    RET
f_acosh: LD 0; I 1; CMP; JLT herr
         LD 0; DUP; MUL; I 1; SUB; CALL f_sqrt 1; LD 0; ADD; CALL f_ln 1; RET
f_atanh: LD 0; ABS; I 1; CMP; JGE herr
         LD 0; ABS; K TAN15; CMP; JGE ath1
         LD 0; I 0; CALL tat 2; RET
ath1:    I 1; LD 0; ADD; I 1; LD 0; SUB; DIV; CALL f_ln 1; NSET 2; DIVN; RET
herr:    ERR MATH

# e^x = 10^k e^s, s = x - k ln10 (ln10 split in two so k*A is exact)
f_exp:   ALLOC 4                            # 1 k, 2 s, 3 sum, 4 term
         LD 0; ABS; K 1E4; CMP; JLT e1
         LD 0; TST; JLT ez
         ERR OVER
ez:      I 0; RET
e1:      LD 0; K LN10; DIV; ROUND; ST 1
         LD 0; LD 1; K LN10A; MUL; SUB; LD 1; K LN10B; MUL; SUB; ST 2
         I 1; DUP; ST 3; ST 4; NSET 1
el:      LD 4; LD 2; MUL; DIVN; NINC; DUP; ST 4; DUP; SMALL 3; JEQ ed
         LD 3; ADD; ST 3; JMP el
ed:      DROP; LD 3; LD 1; SCALE; RET

# ln x = E ln10 + ln m; log x = E + ln m / ln10 (exact for powers of ten)
f_ln:    NSET 0; JMP lnc
f_log:   NSET 1
lnc:     PUSHN; ALLOC 1                     # 1 log?, 2 E
         LD 0; TST; JGT ln1
         ERR MATH
ln1:     LD 0; MANT; ST 2; ST 0
         LD 2; I 1; NEG; CMP; JNE ln2       # [0.5, 1): keep it, no cancellation near 1
         LD 0; I 5; CMP; JLT ln2
         LD 0; I 1; NEG; SCALE; ST 0; I 0; ST 2
ln2:     LD 0; CALL lnm 1; LD 1; TOVN; JVN 1 ln3
         LD 2; K LN10; MUL; ADD; RET
ln3:     K LN10; DIV; LD 2; ADD; RET
# ln m for m in [0.5, 10): halve below 1.5, then 2 atanh((m-1)/(m+1))
lnm:     ALLOC 1
lm1:     LD 0; K 1_5; CMP; JLT lm2
         LD 0; NSET 2; DIVN; ST 0; LD 1; I 1; ADD; ST 1; JMP lm1
lm2:     LD 0; I 1; SUB; LD 0; I 1; ADD; DIV; I 0; CALL tat 2
         DUP; ADD; LD 1; K LN2; MUL; ADD; RET

# Newton from m/4 + 1 (always above the root) until it stops falling
f_sqrt:  ALLOC 2                            # 1 E/2, 2 y
         LD 0; TST; JGT q1; JEQ qz
         ERR MATH
qz:      I 0; RET
q1:      LD 0; MANT; I 2; DIV; ST 1; ST 0
         LD 1; ISINT; JEQ q2
         LD 0; I 1; SCALE; ST 0; LD 1; K HALF; SUB; ST 1
q2:      LD 0; NSET 4; DIVN; I 1; ADD; ST 2
q3:      LD 0; LD 2; DIV; LD 2; ADD; NSET 2; DIVN
         DUP; LD 2; CMP; JGE q4
         ST 2; JMP q3
q4:      DROP; LD 2; LD 1; SCALE; RET

f_cbrt:  ALLOC 1
         LD 0; TST; JNE cb1
         I 0; RET
cb1:     LD 0; ABS; CALL f_ln 1; NSET 3; DIVN; CALL f_exp 1; ST 1
         LD 0; ABS; LD 1; DUP; MUL; DIV; LD 1; SUB; NSET 3; DIVN; LD 1; ADD     # one Newton step
         LD 0; TST; JGE cb2; NEG
cb2:     RET

# x^y: integer y by squaring, 10^y and e^y exactly split, else 10^(y log x)
f_pow:   ALLOC 2                            # 2 base, 3 product
         LD 1; TST; JNE p1
         LD 0; TST; JNE p0
         ERR MATH
p0:      I 1; RET
p1:      LD 0; TST; JNE p2
         LD 1; TST; JGT pz
         ERR MATH
pz:      I 0; RET
p2:      LD 0; I 10; CMP; JNE p3
         LD 1; CALL p10 1; RET
p3:      LD 0; K E; CMP; JNE p4
         LD 1; CALL f_exp 1; RET
p4:      LD 1; ISINT; JNE p6
         LD 1; ABS; K 1E3; CMP; JGT p6
         LD 0; LD 1; TST; JGE p5; INV
p5:      ST 2; I 1; ST 3; LD 1; ABS; TOVN
pl:      HALVN; JEQ pe
         LD 3; LD 2; MUL; ST 3
pe:      JVN 0 pd
         LD 2; DUP; MUL; ST 2; JMP pl
pd:      LD 3; RET
perr:    ERR MATH
p6:      LD 0; TST; JGT p7
         LD 1; INV; DUP; ISINT; JNE perr; NSET 2; DIVN; ISINT; JEQ perr   # needs y = 1/odd
         LD 0; ABS; LD 1; CALL pg 2; NEG; RET
p7:      LD 0; LD 1; CALL pg 2; RET
pg:      LD 0; CALL f_log 1; LD 1; MUL; CALL p10 1; RET
p10:     ALLOC 1
         LD 0; FLOOR; ST 1
         LD 0; LD 1; SUB; K LN10; MUL; CALL f_exp 1; LD 1; SCALE; RET
# x-th root of y (the operator): (x, y)
f_xrt:   LD 1; TST; JGE xr1
         LD 0; ISINT; JNE xr1
         LD 0; NSET 2; DIVN; ISINT; JEQ xr1
         LD 1; ABS; LD 0; INV; CALL f_pow 2; NEG; RET
xr1:     LD 1; LD 0; INV; CALL f_pow 2; RET

# gamma: Stirling at w in [15, 16), the recurrence to z, reflection below 0.5
gerr:    ERR MATH
goer:    ERR OVER
f_gamma: ALLOC 5                            # 1 w, 2 divisor, 3 multiplier, 4 t, 5 t^2
         LD 0; ISINT; JNE g1
         LD 0; TST; JLE gerr
g1:      LD 0; K HALF; CMP; JGE g2
         K PI; LD 0; K PI; MUL; CALL sinr 1; I 1; LD 0; SUB; CALL f_gamma 1; MUL; DIV; RET
g2:      LD 0; K 1E3; CMP; JGT goer
         LD 0; ST 1; I 1; DUP; ST 2; ST 3
g3:      LD 1; I 15; CMP; JGE g4
         LD 2; LD 1; MUL; ST 2; LD 1; I 1; ADD; ST 1; JMP g3
g4:      LD 1; I 16; CMP; JLT g5
         LD 1; I 1; SUB; DUP; ST 1; LD 3; MUL; ST 3; JMP g4
g5:      LD 1; INV; DUP; ST 4; DUP; MUL; ST 5
         K ST7; LD 5; MUL; K ST6; ADD; LD 5; MUL; K ST5; ADD; LD 5; MUL; K ST4; ADD; LD 5; MUL
         K ST3; ADD; LD 5; MUL; K ST2; ADD; LD 5; MUL; K ST1; ADD; LD 5; MUL; K ST0; ADD; LD 4; MUL
         LD 1; CALL f_ln 1; LD 1; K HALF; SUB; MUL; ADD; LD 1; SUB; K HLN2PI; ADD
         CALL f_exp 1; LD 3; MUL; LD 2; DIV; RET
oerr:    ERR OVER
f_fact:  ALLOC 1
         LD 0; ISINT; JEQ fa1
         LD 0; I 1; ADD; CALL f_gamma 1; RET
fa1:     LD 0; TST; JLT ferr
         LD 0; K 1E3; CMP; JGT oerr
         I 1; ST 1
fa2:     LD 0; I 2; CMP; JLT fa3
         LD 1; LD 0; MUL; ST 1; LD 0; I 1; SUB; ST 0; JMP fa2
fa3:     LD 1; RET
ferr:    ERR MATH

f_ncr:   I 0; JMP cmb
f_npr:   I 1
cmb:     ALLOC 3                            # 2 perm, 3 m, 4 product, 5 count
         LD 0; ISINT; JNE aerr; LD 1; ISINT; JNE aerr
         LD 0; TST; JLT aerr; LD 1; TST; JLT aerr
         LD 1; LD 0; CMP; JGT aerr
         LD 1; LD 2; TST; JNE c1
         LD 0; LD 1; SUB; DUP; LD 1; CMP; JGE c0
         SWAP
c0:      DROP
c1:      DUP; K 1E3; CMP; JGT oerr
         ST 5; LD 0; ST 3; I 1; ST 4; NSET 1
c2:      PUSHN; LD 5; CMP; JGT c4
         LD 4; LD 3; MUL; LD 2; TST; JNE c3; DIVN
c3:      ST 4; LD 3; I 1; SUB; ST 3; NINC; JMP c2
c4:      LD 4; RET
aerr:    ERR ARG

f_gcd:   LD 0; ISINT; JNE aerr; LD 1; ISINT; JNE aerr
         LD 0; ABS; ST 0; LD 1; ABS; ST 1
gc1:     LD 1; TST; JEQ gc2
         LD 0; LD 1; CALL f_mod 2; LD 1; ST 0; ST 1; JMP gc1
gc2:     LD 0; RET
f_lcm:   LD 0; LD 1; CALL f_gcd 2; DUP; TST; JEQ lc1
         LD 0; SWAP; DIV; LD 1; MUL; ABS
lc1:     RET
f_mod:   LD 0; LD 0; LD 1; DIV; FLOOR; LD 1; MUL; SUB; RET
f_max:   LD 0; LD 1; CMP; JGT mx0
         LD 1; RET
mx0:     LD 0; RET
f_min:   LD 0; LD 1; CMP; JLT mx0
         LD 1; RET
f_abs:   LD 0; ABS; RET
f_int:   LD 0; TRUNC; RET
f_frac:  LD 0; LD 0; TRUNC; SUB; RET
f_floor: LD 0; FLOOR; RET
f_rnd:   LD 0; RNDD; RET
f_not:   LD 0; BIT 3; RET
f_and:   LD 0; LD 1; BIT 0; RET
f_or:    LD 0; LD 1; BIT 1; RET
f_xor:   LD 0; LD 1; BIT 2; RET
f_e:     K E; RET
f_rand:  RAND; RET
f_ranint: LD 1; LD 0; SUB; I 1; ADD; RAND; MUL; FLOOR; LD 0; ADD; RET

# ---- calculus: the formula is evaluated by FEVAL (X = top)
# secant method from the guess; the root is left in X
f_solve: ALLOC 6                            # 0 x0, 1 x1, 2 f0, 3 f1, 4 |f(guess)|, 5 step, 6 df
         LD 0; FEVAL; DUP; ST 2; ABS; ST 4
         LD 0; DUP; TST; JNE sv0
         DROP; K 1EM4; JMP sv1
sv0:     K 1EM4; MUL; ABS
sv1:     LD 0; ADD; ST 1; NSET 0
sv2:     JVN 100 nor; NINC
         LD 2; TST; JNE sv3
         LD 0; ST 1; JMP svd
sv3:     LD 1; FEVAL; DUP; ST 3; TST; JEQ svd
         LD 3; ABS; LD 4; K 1EM24; MUL; CMP; JLE svd     # tiny next to f(guess): also done (double roots)
         LD 1; LD 0; SUB; DUP; ST 5; TST; JEQ svc
         LD 5; ABS; LD 1; ABS; K 1EM14; MUL; K 1EM60; ADD; CMP; JLT svc
         LD 3; LD 2; SUB; DUP; ST 6; TST; JEQ nor
         LD 5; LD 3; MUL; LD 6; DIV; ST 5
         LD 1; ST 0; LD 3; ST 2; LD 1; LD 5; SUB; ST 1; JMP sv2
svc:     LD 3; ABS; LD 4; K 1EM8; MUL; K 1EM12; ADD; CMP; JLE svd
nor:     ERR NOROOT
svd:     LD 1; STX; RET

# Gauss-Legendre with 5 points per panel; the panels double until two sums agree to 10 digits (the error of
# the finer one is then about 2^-10 of that)
f_integ: ALLOC 6                            # 2 h, 3 odd 2i+1, 4 sum, 5 previous, 6 n, 7 rounds
         I 1; ST 6; I 0; ST 7
ig1:     LD 6; DUP; ADD; ST 6
         LD 1; LD 0; SUB; LD 6; DUP; ADD; DIV; ST 2
         I 0; ST 4; I 1; ST 3
ig2:     LD 3; LD 6; DUP; ADD; CMP; JGT ig4
         NSET 0
ig3:     LD 2; LD 3; MUL; LD 0; ADD; LD 2; KN GLX0; MUL; ADD
         FEVAL; KN GLW0; MUL; LD 4; ADD; ST 4
         NINC; JVN 5 ig3b; JMP ig3
ig3b:    LD 3; I 2; ADD; ST 3; JMP ig2
ig4:     LD 4; LD 2; MUL; ST 4
         LD 7; TST; JEQ ig5
         LD 4; LD 5; SUB; ABS; LD 4; ABS; K 1EM10; MUL; K 1EM40; ADD; CMP; JLT igd
ig5:     LD 4; ST 5; LD 7; I 1; ADD; DUP; ST 7; I 7; CMP; JLT ig1
igd:     LD 4; RET

# Richardson on central differences: (4 D(h/2) - D(h)) / 3, h = 0.001 max(1, |x|)
f_deriv: ALLOC 2                            # 1 h, 2 D(h)
         LD 0; ABS; I 1; CMP; JGE dv0
         I 1; JMP dv1
dv0:     LD 0; ABS
dv1:     K 1EM3; MUL; ST 1
         LD 0; LD 1; CALL dq 2; ST 2
         LD 0; LD 1; NSET 2; DIVN; CALL dq 2
         I 4; MUL; LD 2; SUB; NSET 3; DIVN; RET
dq:      LD 0; LD 1; ADD; FEVAL; LD 0; LD 1; SUB; FEVAL; SUB; LD 1; DIV; NSET 2; DIVN; RET

f_sigma: ALLOC 1                            # 2 sum
         LD 0; ISINT; JNE serr; LD 1; ISINT; JNE serr
         I 0; ST 2
sg1:     LD 0; LD 1; CMP; JGT sg2
         LD 0; FEVAL; LD 2; ADD; ST 2; LD 0; I 1; ADD; ST 0; JMP sg1
sg2:     LD 2; RET
serr:    ERR ARG

# ---- for the C side: results stay in the frame (see fmt.h, calc_gl2000.c)
# statistics (n, sx, sxx, sy, syy, sxy) -> slots 10-24: n, mean x, sx, sigma x, sums x x2, mean y, sy, sigma y,
# sums y y2 xy, a, b, r (UNDEF where not defined)
stats:   ALLOC 4                            # 6 Sxx, 7 Syy, 8 Sxy, 9 n-1
         LD 0; TST; JNE st1
         LD 0; UNDEF; UNDEF; UNDEF; LD 1; LD 2; UNDEF; UNDEF; UNDEF; LD 3; LD 4; LD 5; UNDEF; UNDEF; UNDEF; RET
st1:     LD 2; LD 1; DUP; MUL; LD 0; DIV; SUB; CALL pos 1; ST 6
         LD 4; LD 3; DUP; MUL; LD 0; DIV; SUB; CALL pos 1; ST 7
         LD 5; LD 1; LD 3; MUL; LD 0; DIV; SUB; ST 8
         LD 0; I 1; SUB; ST 9
         LD 0; LD 1; LD 0; DIV; LD 6; LD 9; CALL sd 2; LD 6; LD 0; CALL sd 2; LD 1; LD 2
         LD 3; LD 0; DIV; LD 7; LD 9; CALL sd 2; LD 7; LD 0; CALL sd 2; LD 3; LD 4; LD 5
         LD 6; TST; JNE st2
         UNDEF; UNDEF; UNDEF; RET
st2:     LD 3; LD 8; LD 6; DIV; DUP; ST 9; LD 1; MUL; SUB; LD 0; DIV; LD 9
         LD 6; LD 7; MUL; DUP; TST; JNE st3
         DROP; UNDEF; RET
st3:     CALL f_sqrt 1; LD 8; SWAP; DIV; RET
sd:      LD 1; TST; JNE sd1
         UNDEF; RET
sd1:     LD 0; LD 1; DIV; CALL f_sqrt 1; RET
pos:     LD 0; TST; JGE ps1
         I 0; RET
ps1:     LD 0; RET

# x -> slot 2 h, slot 4 k with h/k = |x| to 14 digits and k < 10^6, or k = 0
tofrac:  ALLOC 6                            # 1 y, 2 h, 3 h', 4 k, 5 k', 6 a
         LD 0; ABS; ST 1; I 1; ST 2; I 0; ST 3; I 0; ST 4; I 1; ST 5; NSET 0
qfr1:     JVN 40 qfrf; NINC
         LD 1; TRUNC; ST 6
         LD 6; LD 2; MUL; LD 3; ADD; LD 2; ST 3; ST 2
         LD 6; LD 4; MUL; LD 5; ADD; LD 4; ST 5; ST 4
         LD 4; K 1E6; CMP; JGE qfrf
         LD 2; LD 4; DIV; LD 0; ABS; SUB; ABS; LD 0; ABS; K 1EM14; MUL; CMP; JLE qfrd
         LD 1; LD 6; SUB; DUP; TST; JEQ qfrd
         INV; ST 1; JMP qfr1
qfrf:     I 0; ST 4
qfrd:     RET
# x degrees -> slots 1, 2, 3: degrees, minutes, seconds rounded to 2 decimals (of |x|)
todms:   ALLOC 3
         LD 0; ABS; DUP; TRUNC; DUP; ST 1; SUB; I 60; MUL; DUP; TRUNC; DUP; ST 2; SUB; I 60; MUL
         I 2; SCALE; ROUND; I 2; NEG; SCALE; ST 3
         LD 3; I 60; CMP; JLT dm1
         LD 3; I 60; SUB; ST 3; LD 2; I 1; ADD; ST 2
dm1:     LD 2; I 60; CMP; JLT dm2
         LD 2; I 60; SUB; ST 2; LD 1; I 1; ADD; ST 1
dm2:     RET
"""


def assemble(text, kindex):
    """-> (bytes, labels)"""
    items = []      # (label or None, op, args)
    for line in text.splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        if ":" in line.split()[0]:
            lab, _, line = line.partition(":")
            items.append((lab.strip(), None, None))
            line = line.strip()
        for ins in line.split(";"):
            p = ins.split()
            if p:
                assert p[0] in OPCODE, p
                items.append((None, p[0], p[1:]))

    def size(op):
        o = OPCODE[op]
        return 1 if o < FIRST1 else 2 if o < FIRST2 else 3 if o < FIRST3 else 4

    for _ in range(2):
        labels, pc = {}, 0
        for lab, op, args in items:
            if lab:
                assert lab not in labels, lab
                labels[lab] = pc
            else:
                pc += size(op)
    code = []
    where = "start"
    for lab, op, args in items:
        if lab:
            where = lab
            continue
        o = OPCODE[op]
        end = len(code) + size(op)

        def rel(name):
            d = labels[name] - end
            assert -128 <= d < 128, "jump to %s out of range (after label %s)" % (name, where)
            return d & 0xFF

        if op in JUMPS:
            code += [o, rel(args[0])]
        elif op == "JVN":
            code += [o, int(args[0]), rel(args[1])]
        elif op == "CALL":
            a = labels[args[0]]
            code += [o, a & 0xFF, a >> 8, int(args[1])]
        elif op in ("K", "KN"):
            code += [o, kindex[args[0]]]
        elif op == "ERR":
            code += [o, ERRS[args[0]]]
        elif o >= FIRST1:
            v = int(args[0])
            assert 0 <= v < 256
            code += [o, v]
        else:
            code.append(o)
    return code, labels


def gen(kindex, fnames):
    code, labels = assemble(PROGRAMS, kindex)
    o = ["// generated by gen_tables.py (gen_vm.py)"]
    for i, n in enumerate(OPS0 + OPS1 + OPS2 + OPS3):
        o.append("#define OP_%s %d" % (n, i))
    o.append("#define OP_FIRST1 %d\n#define OP_FIRST2 %d\n#define OP_FIRST3 %d" % (FIRST1, FIRST2, FIRST3))
    o.append("#define OP_NBIN %d\n#define OP_NUN %d" % (len(BINARY), len(BINARY) + len(UNARY)))
    o.append("#define VMLEN %d" % len(code))
    for lab in ("stats", "tofrac", "todms", "f_pow", "f_xrt", "f_fact", "f_sqrt", "f_cbrt", "f_solve", "f_integ",
                "f_deriv", "f_sigma"):
        o.append("#define VM_%s %d" % (lab[2:] if lab.startswith("f_") else lab, labels[lab]))
    o.append("static const u16 fn_entry[%d] = {%s};" % (len(fnames), ",".join(str(labels["f_" + n]) for n in fnames)))
    return "\n".join(o) + "\n", code
