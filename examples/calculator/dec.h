/*
	dec.h - decimal floating point for the calculator: 16 significant digits, exponent range 1E-499 .. 9.99E499.
	A number is s (1 = negative), e and d[16] (one digit per byte): value = (-1)^s * 0.d0d1..d15 * 10^e.
	Zero has d[0] == 0. Every result is rounded half-up to 16 digits. Only the arithmetic is here; the functions are
	microcode (gen_vm.py, run by vm.h).
	Portable C: the same file is compiled by SDCC for the Z80 and by gcc for the host tests (tests/host.c).
	Copyright (c) 2026 Santiago Crespo. GPL-3.0-or-later (built against VGLDK)
*/
#define ND 16
#define EMAX 500
#define EMIN (-498)

#ifdef __SDCC
typedef struct { byte s; i16 e; byte d[ND]; } num;
#else
typedef struct __attribute__((packed)) { byte s; i16 e; byte d[ND]; } num;	// 19 bytes, as in page 2
#endif

#define E_SYNTAX  1
#define E_MATH    2
#define E_OVER    3
#define E_COMPLEX 4
#define E_BREAK   5
#define E_NOROOT  6
#define E_ARG     7

void err(byte code);

#include "consts.h"

static byte W[2 * ND + 2];

#define dcopy(r, a) memcpy((r), (a), sizeof(num))
#define iszero(a) (!(a)->d[0])

static void dzero(num *r) { memset(r, 0, sizeof(num)); }

#ifdef __SDCC
#include "core_z80.h"
#else
// r = +-0.W[0..n-1] * 10^e, rounded to ND digits; W is modified
static void dpack(num *r, byte n, i16 e, byte s) {
	byte *w = W, *p;
	while (n && !*w) { w++; n--; e--; }
	if (!n) { dzero(r); return; }
	if (n > ND) {
		if (w[ND] >= 5) {
			p = w + ND;
			do { if (p == w) { *p = 1; e++; break; } *--p += 1; if (*p < 10) break; *p = 0; } while (1);
		}
		n = ND;
	}
	r->s = s; r->e = e;
	memset(r->d, 0, ND);
	memcpy(r->d, w, n);
	if (e > EMAX) err(E_OVER);
	if (e < EMIN) dzero(r);
}

static signed char cmpabs(const num *a, const num *b) {
	const byte *p = a->d, *q = b->d;
	byte n = ND;
	if (!*p) return *q ? -1 : 0;
	if (!*q) return 1;
	if (a->e != b->e) return a->e > b->e ? 1 : -1;
	do { if (*p != *q) return *p > *q ? 1 : -1; p++; q++; } while (--n);
	return 0;
}

#endif

static signed char dcmp(const num *a, const num *b) {
	signed char c;
	if (iszero(a)) return iszero(b) ? 0 : b->s ? 1 : -1;
	if (iszero(b) || a->s != b->s) return a->s ? -1 : 1;
	c = cmpabs(a, b);
	return a->s ? -c : c;
}

#ifndef __SDCC
// W[1..ND+2] = |a| -+ |b| aligned (|a| >= |b|); W[0] takes the carry
static void dadd(num *r, const num *a, const num *b) {
	const num *t;
	const byte *p;
	byte *w, n;
	i16 k;
	if (iszero(b)) { dcopy(r, a); return; }
	if (iszero(a)) { dcopy(r, b); return; }
	if (cmpabs(a, b) < 0) { t = a; a = b; b = t; }
	memset(W, 0, ND + 3);
	memcpy(W + 1, a->d, ND);
	k = a->e - b->e;
	if (k <= ND + 1) {
		w = W + 1 + k; p = b->d;
		n = ND + 2 - k; if (n > ND) n = ND;
		if (a->s == b->s) do *w++ += *p++; while (--n);
		else do *w++ -= *p++; while (--n);
		w = W + ND + 2; n = ND + 2;
		do {
			if ((signed char)*w < 0) { *w += 10; w[-1]--; }
			else if (*w >= 10) { *w -= 10; w[-1]++; }
			w--;
		} while (--n);
	}
	dpack(r, ND + 3, a->e + 1, a->s);
}

#endif

static void dneg(num *r) { if (!iszero(r)) r->s ^= 1; }

#ifndef __SDCC
static void dsub(num *r, const num *a, const num *b) {
	num t;
	dcopy(&t, b); dneg(&t);
	dadd(r, a, &t);
}

// schoolbook, accumulating each column in a byte: W[i + j + 1] += a[i] b[j], carries after every row
static void dmul(num *r, const num *a, const num *b) {
	const byte *p, *q;
	byte *w, *v, i, j, x, c;
	if (iszero(a) || iszero(b)) { dzero(r); return; }
	memset(W, 0, 2 * ND + 1);
	p = a->d + ND;
	for (i = ND; i; i--) {
		x = *--p;
		if (!x) continue;
		w = W + i + ND; q = b->d + ND; c = 0;
		for (j = ND; j; j--) {
			v = --w;
			c += *v + x * *--q;
			*v = c % 10; c /= 10;
		}
		w[-1] += c;
	}
	dpack(r, 2 * ND, a->e + b->e, a->s ^ b->s);
}

// long division by repeated subtraction, ND + 2 quotient digits
static void ddiv(num *r, const num *a, const num *b) {
	static byte R[ND + 1], D[ND + 1];
	byte q, c, n, *x, *y;
	signed char t;
	if (iszero(b)) err(E_MATH);
	if (iszero(a)) { dzero(r); return; }
	R[0] = 0; D[0] = 0;
	memcpy(R + 1, a->d, ND); memcpy(D + 1, b->d, ND);
	for (q = 0; q < ND + 2; q++) {
		c = 0;
		for (;;) {
			x = R; y = D; n = ND + 1;
			while (n && *x == *y) { x++; y++; n--; }
			if (n && *x < *y) break;
			x = R + ND + 1; y = D + ND + 1; n = ND + 1;
			do {
				t = *--x - *--y;
				if (t < 0) { t += 10; x[-1]--; }
				*x = t;
			} while (--n);
			c++;
		}
		W[q] = c;
		memmove(R, R + 1, ND); R[ND] = 0;
	}
	dpack(r, ND + 2, a->e - b->e + 1, a->s ^ b->s);
}

static void ddivn(num *r, const num *a, u16 n) {
	byte i;
	u16 v, rem = 0;
	for (i = 0; i < ND + 6; i++) {
		v = rem * 10 + (i < ND ? a->d[i] : 0);
		W[i] = v / n; rem = v % n;
	}
	dpack(r, ND + 6, a->e, a->s);
}

#endif

static void dfromint(num *r, i16 v) {
	byte n = 6, s = 0;
	u16 u = v;
	if (v < 0) { s = 1; u = -v; }
	do { W[--n] = u % 10; u /= 10; } while (n);
	dpack(r, 6, 6, s);
}

#ifndef __SDCC
// integer part as i16; Math error when it does not fit
static i16 dtoi(const num *a) {
	byte i;
	u16 v = 0;
	if (a->e > 5) err(E_ARG);
	for (i = 0; (i16)i < a->e; i++) {
		if (v > 3276 || (v == 3276 && a->d[i] > 7)) err(E_ARG);
		v = v * 10 + a->d[i];
	}
	return a->s ? -(i16)v : (i16)v;
}

static byte isint(const num *a) {
	byte i;
	for (i = 0; i < ND; i++) if (a->d[i] && (i16)i >= a->e) return 0;
	return 1;
}

static void dtrunc(num *r, const num *a) {
	byte i;
	dcopy(r, a);
	if (a->e <= 0) { dzero(r); return; }
	for (i = 0; i < ND; i++) if ((i16)i >= a->e) r->d[i] = 0;
}

#endif

static void dfloor(num *r, const num *a) {
	byte n = !isint(a) && a->s;
	dtrunc(r, a);
	if (n) dsub(r, r, &K_ONE);
}

// round half away from zero to an integer
static void dround(num *r, const num *a) {
	num h;
	dcopy(&h, &K_HALF); h.s = a->s;
	dadd(r, a, &h);
	dtrunc(r, r);
}

// round to n significant digits (1..ND-1)
static void dsig(num *r, const num *a, byte n) {
	byte i;
	if (iszero(a) || n >= ND) { dcopy(r, a); return; }
	W[0] = 0;
	memcpy(W + 1, a->d, n);
	if (a->d[n] >= 5) for (i = n; ++W[i] == 10; i--) W[i] = 0;
	dpack(r, n + 1, a->e + 1, a->s);
}

static byte small(const num *t, const num *sum) { return iszero(t) || t->e < sum->e - ND - 1; }

static signed char dsign(const num *a) { return iszero(a) ? 0 : a->s ? -1 : 1; }

// r *= 10^k (k an integer number); underflow gives zero
static void dscale(num *r, const num *k) {
	i16 n;
	if (iszero(r)) return;
	if (k->e > 4) { if (k->s) { dzero(r); return; } err(E_OVER); }
	n = r->e + dtoi(k);
	if (n > EMAX) err(E_OVER);
	if (n < EMIN) { dzero(r); return; }
	r->e = n;
}

// n mod 4 of an integer
static byte dmod4(const num *q) {
	byte v = 0;
	if (q->e > 0) v = q->d[q->e - 1];
	if (q->e > 1) v += q->d[q->e - 2] * 10;
	v &= 3;
	if (q->s) v = (4 - v) & 3;
	return v;
}
