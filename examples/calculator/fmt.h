/*
	fmt.h - number to text in the display formats (NORM, FIX n, SCI n, ENG), fractions, degrees-minutes-seconds and
	the integer bases. Output uses LCD codes (C_EXP for the exponent mark, C_DEG for degrees); at most 20 characters
	except BIN (up to 32 digits).
	Copyright (c) 2026 Santiago Crespo. GPL-3.0-or-later (built against VGLDK)
*/
#define C_INV   0x08	// CGRAM glyphs 0-7 at their 0x08-0x0F aliases (0x00 would end the string)
#define C_SQ    0x09
#define C_CUBE  0x0A
#define C_STO   0x0B
#define C_INT   0x0C
#define C_SUM   0x0D
#define C_EXP   0x0E
#define C_XRT   0x0F
#define C_DEG   0xB2
#define C_TIMES 0xB7
#define C_DIV   0xB8
#define C_SQRT  0xBE
#define C_PI    0xED

#define FMT_NORM 0
#define FMT_FIX  1
#define FMT_SCI  2
#define FMT_ENG  3
#define NORM_SIG 12

static byte dispfmt, dispdig;
static byte basemode;		// 0 DEC, 1 HEX, 2 BIN, 3 OCT
static char *wp;

typedef union { u32 v; byte b[4]; } u32b;	// both the Z80 and the test host are little endian

// integer part as 32 bits (two's complement below zero); Overflow outside -2^31 .. 2^32-1
static u32 dtou32(const num *a) {
	num t, q, k;
	u32b u;
	byte i;
	dtrunc(&t, a);
	if (t.s) { if (cmpabs(&t, &K_2P31) > 0) err(E_OVER); dadd(&t, &t, &K_2P32); }
	if (dcmp(&t, &K_2P32) >= 0) err(E_OVER);
	for (i = 0; i < 4; i++) {
		ddivn(&q, &t, 256); dtrunc(&q, &q);
		dfromint(&k, 256); dmul(&k, &k, &q); dsub(&k, &t, &k);
		u.b[i] = dtoi(&k);
		dcopy(&t, &q);
	}
	return u.v;
}

// r = v as a signed 32-bit value
static void dfromu32(num *r, u32 v) {
	num k;
	u32b u;
	byte i = 4;
	u.v = v;
	dzero(r);
	dfromint(&k, 256);
	while (i--) { dmul(r, r, &k); dfromint(vtop, u.b[i]); dadd(r, r, vtop); }
	if (u.b[3] & 0x80) dsub(r, r, &K_2P32);
}

// r = r and/or/xor b (op 0-2), or not r (op 3)
static void dbit(num *r, const num *b, byte op) {
	u32 x = dtou32(r), y = op < 3 ? dtou32(b) : 0;
	dfromu32(r, op == 0 ? x & y : op == 1 ? x | y : op == 2 ? x ^ y : ~x);
}

// round to n decimals
static void ddec(num *r, const num *a, byte n) {
	dcopy(r, a);
	if (iszero(r)) return;
	r->e += n; dround(r, r);
	if (!iszero(r)) r->e -= n;
}

static void dround_disp(num *r, const num *a) {
	if (dispfmt == FMT_FIX) ddec(r, a, dispdig);
	else dsig(r, a, dispfmt == FMT_SCI ? (dispdig ? dispdig : 10) : NORM_SIG);
}

static byte dig(const num *y, i16 i) { return i >= 0 && i < ND ? y->d[i] : 0; }

// digits of y with the point after k digits; dec decimals, or as many as needed (strip)
static void put_fixed(const num *y, i16 k, i16 dec, byte strip) {
	i16 i, last;
	if (strip) {
		for (last = ND - 1; last >= 0 && !y->d[last]; last--) ;
		dec = last + 1 - k;
		if (dec < 0) dec = 0;
	}
	if (k <= 0) *wp++ = '0';
	for (i = 0; i < k; i++) *wp++ = '0' + dig(y, i);
	if (dec > 0) {
		*wp++ = '.';
		for (i = k; i < k + dec; i++) *wp++ = '0' + dig(y, i);
	}
}

static void put_int(i16 v) {
	char b[6];
	byte n = 0;
	if (v < 0) { *wp++ = '-'; v = -v; }
	do { b[n++] = '0' + v % 10; v /= 10; } while (v);
	while (n) *wp++ = b[--n];
}

// mantissa with k integer digits, then the exponent mark and E
static void put_sci(const num *y, byte k, i16 dec, byte strip, i16 E) {
	put_fixed(y, k, dec, strip);
	*wp++ = C_EXP;
	put_int(E);
}

static void fmt_num(char *o, const num *x) {
	num y;
	i16 E;
	byte n;
	wp = o;
	if (x->s) *wp++ = '-';
	n = dispdig;
	if (dispfmt == FMT_FIX) {
		ddec(&y, x, n);
		if (iszero(&y)) { wp = o; put_fixed(&y, 0, n, 0); goto done; }
		if (y.e <= 12 && y.e + n <= ND) { put_fixed(&y, y.e, n, 0); if (wp - o <= 20) goto done; }
		wp = o + x->s;
		n = 0;
	}
	if (iszero(x)) { *wp++ = '0'; goto done; }
	if (dispfmt == FMT_SCI && n) {	// SCI 0 = 10 digits
		dsig(&y, x, n);
		put_sci(&y, 1, n - 1, 0, y.e - 1);
		goto done;
	}
	dsig(&y, x, dispfmt == FMT_SCI ? 10 : NORM_SIG);
	E = y.e - 1;
	if (dispfmt == FMT_ENG) {
		n = (E + 600) % 3;
		if (E == n) put_fixed(&y, n + 1, 0, 1); else put_sci(&y, n + 1, 0, 1, E - n);
	} else if (dispfmt == FMT_SCI) put_sci(&y, 1, 9, 0, E);
	else if (E >= NORM_SIG || E < -6) put_sci(&y, 1, 0, 1, E);
	else put_fixed(&y, y.e, 0, 1);
done:
	*wp = 0;
}

static byte fmt_ok(char *o) { byte n = 0; while (*o++) n++; return n <= 20; }

// h/k by continued fractions (microcode tofrac) when it matches x to 14 digits with k < 10^6; returns 0 otherwise
static byte fmt_frac(char *o, const num *x) {
	num *fb = vtop;
	byte ok = 0;
	if (iszero(x) || x->e > 10 || isint(x)) return 0;
	vpush(x);
	vm(VM_tofrac, fb);
	if (!iszero(fb + 4)) {
		wp = o;
		if (x->s) *wp++ = '-';
		put_fixed(fb + 2, fb[2].e, 0, 0);
		*wp++ = '/';
		put_fixed(fb + 4, fb[4].e, 0, 0);
		*wp = 0;
		ok = fmt_ok(o);
	}
	vtop = fb;
	return ok;
}

// d°m's.ss" of x degrees (microcode todms)
static byte fmt_dms(char *o, const num *x) {
	num *fb = vtop;
	if (x->e > 7) return 0;
	vpush(x);
	vm(VM_todms, fb);
	wp = o;
	if (x->s) *wp++ = '-';
	put_fixed(fb + 1, fb[1].e, 0, 0); *wp++ = C_DEG;
	put_fixed(fb + 2, fb[2].e, 0, 0); *wp++ = '\'';
	put_fixed(fb + 3, fb[3].e, 0, 1); *wp++ = '"';
	*wp = 0;
	vtop = fb;
	return fmt_ok(o);
}

// integer part in base 16, 2 or 8 (basemode 1..3), two's complement below zero
static void fmt_base(char *o, const num *x) {
	u32 v = dtou32(x);
	byte sh = basemode == 1 ? 4 : basemode == 2 ? 1 : 3, n = 0, d;
	char b[33];
	do { d = v & ((1 << sh) - 1); b[n++] = d < 10 ? '0' + d : 'A' - 10 + d; v >>= sh; } while (v);
	while (n) *o++ = b[--n];
	*o = 0;
}
