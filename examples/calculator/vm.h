/*
	vm.h - interpreter for the math microcode (gen_vm.py describes the machine and holds the programs).
	The number stack is shared by nested runs: the evaluator pushes arguments, runs a program, takes the top and
	drops the frame; FEVAL re-enters the evaluator, which may run more programs above the current frame.
	Copyright (c) 2026 Santiago Crespo. GPL-3.0-or-later (built against VGLDK)
*/
#define VSTK 40
static byte vmcode[VMLEN];	// copied from page 2 at start
static num vstk[VSTK + 1];	// one spare slot for SWAP
static num *vtop;
static const byte *cf;		// formula text for FEVAL
static byte angmode;		// 0 DEG, 1 RAD, 2 GRA
num vars[26], ans;		// A-Z, last result (not static: the MAME tests find them in the map)
#define V_X ('X' - 'A')

static void feval(num *r, const num *x);
static void dfloor(num *r, const num *a);
static void fetch(void *dst, u16 src, u16 n);
static void dround_disp(num *r, const num *a);
static void dbit(num *r, const num *b, byte op);
static void drand(num *r);

static num *vnew(void) {
	if (vtop >= vstk + VSTK) err(E_COMPLEX);
	return vtop++;
}

static void vpush(const num *a) { dcopy(vnew(), a); }

static void dneg2(num *r, const num *a) { (void)a; dneg(r); }
static void dabs(num *r, const num *a) { (void)a; r->s = 0; }
static void dinv(num *r, const num *a) { ddiv(r, &K_ONE, a); }

typedef void (*fn3)(num *, const num *, const num *);
typedef void (*fn2)(num *, const num *);
static const fn3 vbin[OP_NBIN] = { dadd, dsub, dmul, ddiv };
static const fn2 vun[OP_NUN - OP_NBIN] = { dneg2, dabs, dinv, dtrunc, dfloor, dround, dround_disp, feval };
static const byte jmask[7] = { 7, 2, 5, 1, 6, 4, 3 };	// JMP .. JLE: bit f+1 set = jump

// runs the program at entry; its frame starts at fb (the arguments already pushed). The result is vtop[-1].
static void vm(u16 entry, num *fb) {
	const byte *pc = vmcode + entry;
	const byte *rpc[8];
	num *rfb[8], *t, *u;
	byte rd = 0, op, a = 0, b = 0, c = 0;
	u16 vn = 0;
	i16 e;
	signed char f = 0;
	stack_check();
	for (;;) {
		op = *pc++;
		t = vtop - 1; u = vtop - 2;
		if (op < OP_NBIN) { vbin[op](u, u, t); vtop--; continue; }
		if (op < OP_NUN) { vun[op - OP_NBIN](t, t); continue; }
		if (op >= OP_FIRST1) {
			a = *pc++;
			if (op < OP_FIRST1 + 7) { if (jmask[op - OP_FIRST1] >> (f + 1) & 1) pc += (signed char)a; continue; }
			if (op >= OP_FIRST2) { b = *pc++; if (op >= OP_FIRST3) c = *pc++; }
		}
		switch (op) {
		case OP_RET:
			if (!rd) return;
			dcopy(fb, t); vtop = fb + 1;
			rd--; pc = rpc[rd]; fb = rfb[rd];
			break;
		case OP_CALL:
			if (rd == 8) err(E_COMPLEX);
			rpc[rd] = pc; rfb[rd] = fb; rd++;
			fb = vtop - c; pc = vmcode + (a | (u16)b << 8);
			break;
		case OP_DUP: vpush(t); break;
		case OP_DROP: vtop--; break;
		case OP_SWAP: dcopy(vtop, t); dcopy(t, u); dcopy(u, vtop); break;
		case OP_NINC: vn++; break;
		case OP_DIVN: ddivn(t, t, vn); break;
		case OP_PUSHN: dfromint(vnew(), vn); break;
		case OP_TOVN: vn = dtoi(t); vtop--; break;
		case OP_SCALE: dscale(u, t); vtop--; break;
		case OP_MANT:
			e = t->e - 1;
			if (!iszero(t)) t->e = 1;
			dfromint(vnew(), e);
			break;
		case OP_TST: f = dsign(t); vtop--; break;
		case OP_CMP: f = dcmp(u, t); vtop -= 2; break;
		case OP_ISINT: f = !isint(t); vtop--; break;
		case OP_STX: dcopy(&vars[V_X], t); break;
		case OP_ANG: vn = angmode; break;
		case OP_QUAD: vn = dmod4(t); vtop--; break;
		case OP_HALVN: f = vn & 1; vn >>= 1; break;
		case OP_RAND: drand(vnew()); break;
		case OP_UNDEF: t = vnew(); dzero(t); t->s = 1; break;
		case OP_LD: vpush(fb + a); break;
		case OP_ST: vtop--; dcopy(fb + a, vtop); break;
		case OP_KN: a += vn;	// fall through
		case OP_K: fetch(vnew(), P2_KT + a * sizeof(num), sizeof(num)); break;
		case OP_I: dfromint(vnew(), a); break;
		case OP_NSET: vn = a; break;
		case OP_ALLOC: while (a--) dzero(vnew()); break;
		case OP_SMALL: f = !small(t, fb + a); vtop--; break;
		case OP_ERR: err(a);
		case OP_BIT:
			if (a == 3) dbit(t, t, 3);
			else { dbit(u, t, a); vtop--; }
			break;
		case OP_JVN: if (vn == a) pc += (signed char)b; break;
		}
	}
}

// r = program(r) or program(r, b)
static void vcall(num *r, const num *b, u16 entry) {
	num *fb = vtop;
	vpush(r);
	if (b) vpush(b);
	vm(entry, fb);
	dcopy(r, vtop - 1);
	vtop = fb;
}
