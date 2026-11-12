/*
	eval.h - expression evaluator: precedence climbing straight over the text (no tokens, no tree), so the calculus
	functions can evaluate their first argument again and again by moving the text pointer back.
	Precedence, low to high: + -, x /, implicit multiplication (1/2pi = 1/(2pi)), unary -, ^ and x-root (right to left),
	postfix ! sq cube inv %. Missing ')' at the end of the text are closed automatically.
	Functions run as microcode (vm.h). The platform provides stack_check() and poll_break().
	Copyright (c) 2026 Santiago Crespo. GPL-3.0-or-later (built against VGLDK)
*/
static const byte *pp;		// parse position
static const byte *errpos;	// where a syntax error was found
static u16 rng;

static void syntax(void) { errpos = pp; err(E_SYNTAX); }

static void expr(num *r, byte minp);
static void unary(num *r);

static byte isdig(byte c) { return c >= '0' && c <= '9'; }
static byte isup(byte c) { return c >= 'A' && c <= 'Z'; }
static byte islow(byte c) { return c >= 'a' && c <= 'z'; }
static void skipsp(void) { while (*pp == ' ') pp++; }

static void number(num *r) {
	byte n = 0, any = 0, dot = 0, d, neg;
	i16 e = 0, x;
	static const byte radix[4] = { 10, 16, 2, 8 };
	if (basemode && *pp != C_EXP) {	// an integer in the base, as a signed 32-bit value
		num b;
		dzero(r);
		dfromint(&b, radix[basemode]);
		for (;; pp++) {
			d = *pp;
			if (isdig(d)) d -= '0'; else if (d >= 'A' && d <= 'F') d -= 'A' - 10; else break;
			if (d >= radix[basemode]) break;
			dmul(r, r, &b); dfromint(vtop, d); dadd(r, r, vtop);
			if (dcmp(r, &K_2P32) >= 0) err(E_OVER);
		}
		if (dcmp(r, &K_2P31) >= 0) dsub(r, r, &K_2P32);
		return;
	}
	for (;; pp++) {
		d = *pp;
		if (d == '.') { if (dot) syntax(); dot = 1; continue; }
		if (!isdig(d)) break;
		d -= '0'; any = 1;
		if (!n && !d) { if (dot) e--; continue; }
		if (n < ND + 1) W[n++] = d;
		if (!dot) e++;
	}
	if (*pp == C_EXP) {
		if (!any) { W[0] = 1; n = 1; e = 1; any = 1; }
		pp++; neg = 0; x = 0;
		if (*pp == '-') { neg = 1; pp++; }
		if (!isdig(*pp)) syntax();
		while (isdig(*pp)) { if (x < 1000) x = x * 10 + *pp - '0'; pp++; }
		e += neg ? -x : x;
	}
	if (!any) syntax();
	dpack(r, n, e, 0);
}

// a primary can start here (implicit multiplication follows)
static byte starts_primary(void) {
	byte c = *pp;
	return isdig(c) || c == '.' || isup(c) || islow(c) || c == '(' || c == C_PI || c == C_SQRT || c == C_INT ||
		c == C_SUM || c == C_EXP || (c == C_CUBE && pp[1] == C_SQRT);
}

static void close_paren(void) {
	skipsp();
	if (*pp == ')') pp++;
	else if (*pp && *pp != C_STO) syntax();
}

static void comma(void) { skipsp(); if (*pp != ',') syntax(); pp++; }

// f(x) of the formula at cf; "lhs = rhs" gives lhs - rhs
static void feval(num *r, const num *x) {
	const byte *save = pp;
	poll_break();
	dcopy(&vars[V_X], x);
	pp = cf;
	expr(r, 0);
	if (*pp == '=') { num *t = vnew(); pp++; expr(t, 0); dsub(r, r, t); vtop--; }
	if (*pp != ',' && *pp != ')' && *pp) syntax();
	pp = save;
}

// solve, integral, sum, derivative: the first argument is text, skipped here and evaluated by the microcode
static void calculus(num *r, byte which) {
	static const u16 entry[4] = { VM_solve, VM_integ, VM_sigma, VM_deriv };
	num xs, *fb = vtop;
	const byte *f = pp, *save = cf;
	byte depth = 0;
	dcopy(&xs, &vars[V_X]);
	for (;; pp++) {
		if (!*pp) syntax();
		if (*pp == '(') depth++;
		else if (*pp == ')') { if (!depth) break; depth--; }
		else if (*pp == ',' && !depth) break;
	}
	if (which == F_SOLVE && *pp == ')') vpush(&xs);
	else { comma(); expr(vnew(), 0); }
	if (which == F_INTEG || which == F_SIGMA) { comma(); expr(vnew(), 0); }
	close_paren();
	cf = f;
	vm(entry[which - F_SOLVE], fb);
	cf = save;
	dcopy(r, vtop - 1);
	vtop = fb;
	if (which != F_SOLVE) dcopy(&vars[V_X], &xs);
}

static u16 rnd16(void) {
	if (!rng) rng = 1;
	rng ^= rng << 7; rng ^= rng >> 9; rng ^= rng << 8;
	return rng;
}

static void drand(num *r) {
	byte i;
	for (i = 0; i < ND; i++) W[i] = rnd16() % 10;
	dpack(r, ND, 0, 0);
}

// longest function name that starts at pp
static byte lookup(void) {
	const char *s = fn_names;
	byte id = 0, best = 0xFF, bl = 0, l;
	while (*s) {
		for (l = 0; s[l] && s[l] == pp[l]; l++) ;
		if (!s[l] && l > bl) { bl = l; best = id; }
		while (*s++) ;
		id++;
	}
	if (best == 0xFF) syntax();
	pp += bl;
	return best;
}

static void call(num *r, byte id) {
	num *fb = vtop;
	if (id != F_E && id != F_RAND) {
		if (*pp != '(') syntax();
		pp++;
		if (id >= F_SOLVE) { calculus(r, id); return; }
		expr(vnew(), 0);
		if (id >= F_TWO) { comma(); expr(vnew(), 0); }
		close_paren();
	}
	vm(fn_entry[id], fb);
	dcopy(r, vtop - 1);
	vtop = fb;
}

static void primary(num *r) {
	byte c;
	skipsp();
	c = *pp;
	if (isdig(c) || c == '.' || c == C_EXP) { number(r); return; }
	pp++;
	if (c == '(') { expr(r, 0); close_paren(); return; }
	if (c == C_PI) { dcopy(r, &K_PI); return; }
	if (c == C_SQRT) { unary(r); vcall(r, 0, VM_sqrt); return; }
	if (c == C_CUBE && *pp == C_SQRT) { pp++; unary(r); vcall(r, 0, VM_cbrt); return; }
	if (c == C_INT || c == C_SUM) { if (*pp != '(') syntax(); pp++; calculus(r, c == C_INT ? F_INTEG : F_SIGMA); return; }
	if (isup(c)) {
		if (c == 'A' && pp[0] == 'n' && pp[1] == 's') { pp += 2; dcopy(r, &ans); return; }
		dcopy(r, &vars[c - 'A']);
		return;
	}
	pp--;
	if (islow(c)) {
		if (c == 'd' && pp[1] == '/' && pp[2] == 'd' && pp[3] == 'x') { pp += 4; call(r, F_DERIV); return; }
		call(r, lookup());
		return;
	}
	syntax();
}

static void unary(num *r) {
	byte c;
	skipsp();
	c = *pp;
	if (c == '-' || c == '+') {
		pp++;
		expr(r, 4);
		if (c == '-') dneg(r);
		return;
	}
	primary(r);
	for (;;) {
		c = *pp;
		if (c == '!') vcall(r, 0, VM_fact);
		else if (c == C_SQ) dmul(r, r, r);
		else if (c == C_CUBE && pp[1] != C_SQRT) { dmul(vtop, r, r); dmul(r, r, vtop); }
		else if (c == C_INV) ddiv(r, &K_ONE, r);
		else if (c == '%') ddivn(r, r, 100);
		else return;
		pp++;
	}
}

static void expr(num *r, byte minp) {
	num b;
	byte op, p;
	stack_check();
	unary(r);
	for (;;) {
		skipsp();
		op = *pp;
		if (op == '+' || op == '-') p = 1;
		else if (op == C_TIMES || op == '*' || op == C_DIV || op == '/') p = 2;
		else if (op == '^' || op == C_XRT) p = 5;
		else if (starts_primary()) { p = 3; op = 0; }
		else return;
		if (p < minp) return;
		if (op) pp++;
		expr(&b, p == 5 ? 5 : p + 1);
		if (op == '+') dadd(r, r, &b);
		else if (op == '-') dsub(r, r, &b);
		else if (op == '/' || op == C_DIV) ddiv(r, r, &b);
		else if (op == '^') vcall(r, &b, VM_pow);
		else if (op == C_XRT) vcall(r, &b, VM_xrt);
		else dmul(r, r, &b);
	}
}

// the whole line: expression, optionally followed by -> and a letter
static void evaluate(num *r, const byte *text) {
	vtop = vstk; cf = 0;
	pp = text;
	expr(r, 0);
	skipsp();
	if (*pp == C_STO) {
		pp++;
		if (!isup(*pp)) syntax();
		dcopy(&vars[*pp - 'A'], r);
		pp++;
		skipsp();
	}
	if (*pp) syntax();
}
