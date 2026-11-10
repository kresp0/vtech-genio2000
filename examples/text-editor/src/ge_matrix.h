#ifndef GE_MATRIX_H
#define GE_MATRIX_H
/*
 * ge_matrix.h - PHYSICAL keyboard layer: keeps the state of EACH key of the matrix (8 columns x 13 rows: 8 of matrix 1 on
 * port 0x10 and 5 of matrix 2 on port 0x11), not just an ASCII code. It knows nothing about characters (that is ge_keymap.h).
 *
 *   * One reading = 8 words of 16 bits (one per col_out): bit f (0..7) = row_in f of matrix 1 pressed,
 *     bit 8+f (0..4) = row_in f of matrix 2 pressed.
 *   * DEBOUNCE: a new state is only accepted after two consecutive identical readings (GE_DEBOUNCE).
 *   * Press / release events per key in a queue of GE_EVQ_N entries (if it fills up, ge_ev_lost is counted).
 *   * GHOSTS: the matrix has no known diodes; a new key that closes a rectangle with three others already pressed
 *     (columns a,b; rows r,r2) may be a ghost. It is not accepted (event GE_EV_GHOST) until the rectangle breaks.
 *   * The physical reading (ports) is done by the main program: ge_mx_feed(cols) is only logic.
 */
#include "ge_types.h"

#ifndef GE_DEBOUNCE
#define GE_DEBOUNCE 2		/* identical consecutive readings needed to accept a change (each reading about 5 ms: about 10 ms) */
#endif
#define GE_EVQ_N 16
#define GE_EV_UP    0
#define GE_EV_DOWN  1
#define GE_EV_GHOST 2

static word mx_prev[8], mx_stable[8];
static byte mx_same;			/* lecturas consecutivas iguales */
static word mx_evq[GE_EVQ_N];		/* byte alto = tipo, byte bajo = scancode */
static byte mx_evh, mx_evt;
static word mx_gmark[8];		/* rows whose ghost was already reported (once per press) */
static byte ge_ev_lost;
static word ge_ghosts;

static byte mx_sc(byte col, byte row) { return row < 8 ? (byte)(row * 8 + col) : (byte)(0x40 + (row - 8) * 8 + col); }

static void mx_push(byte type, byte sc) {
	byte n = (byte)((mx_evt + 1) % GE_EVQ_N);
	if (n == mx_evh) { if (ge_ev_lost < 255) ge_ev_lost++; return; }
	mx_evq[mx_evt] = ((word)type << 8) | sc; mx_evt = n;
}
static byte mx_pop(word *ev) {
	if (mx_evh == mx_evt) return 0;
	*ev = mx_evq[mx_evh]; mx_evh = (byte)((mx_evh + 1) % GE_EVQ_N);
	return 1;
}

static void ge_mx_init(void) {
	byte i;
	for (i = 0; i < 8; i++) { mx_prev[i] = 0; mx_stable[i] = 0; mx_gmark[i] = 0; }
	mx_same = 0; mx_evh = mx_evt = 0; ge_ev_lost = 0; ge_ghosts = 0;
}

/* stable state of a key (column, row 0..12) */
static byte ge_mx_down(byte col, byte row) { return (byte)((mx_stable[col] >> row) & 1); }
static byte ge_mx_sc_down(byte sc) {
	if (sc < 64) return ge_mx_down(sc & 7, sc >> 3);
	return ge_mx_down(sc & 7, (byte)(8 + ((sc - 0x40) >> 3)));
}
static byte ge_mx_any(void) { byte i; for (i = 0; i < 8; i++) if (mx_stable[i]) return 1; return 0; }

/* true if key (a, r) completes a rectangle with three keys already pressed in cand[] */
static byte mx_ghost(const word *cand, byte a, byte r) {
	byte b;
	word others = (word)(cand[a] & ~(1u << r));
	for (b = 0; b < 8; b++) {
		if (b == a) continue;
		if (((cand[b] >> r) & 1) && (cand[b] & others)) return 1;
	}
	return 0;
}

/* processes a raw reading (pressed = 1). Returns 1 if the stable state changed. */
static byte ge_mx_feed(const word *cols) {
	byte a, r, changed = 0, same = 1;
	word cand[8], diff;
	for (a = 0; a < 8; a++) if (cols[a] != mx_prev[a]) same = 0;
	for (a = 0; a < 8; a++) mx_prev[a] = cols[a];
	if (!same) { mx_same = 0; return 0; }
	if (mx_same < 255) mx_same++;
	if (mx_same < GE_DEBOUNCE - 1) return 0;
	/* stable: compare with the accepted state */
	for (a = 0; a < 8; a++) cand[a] = cols[a];
	/* releases first (they may break a rectangle) */
	for (a = 0; a < 8; a++) {
		diff = (word)(mx_stable[a] & ~cols[a]);
		for (r = 0; diff && r < 13; r++) if ((diff >> r) & 1) { mx_stable[a] &= ~(1u << r); mx_push(GE_EV_UP, mx_sc(a, r)); changed = 1; diff &= ~(1u << r); }
	}
	/* new presses: the ghost is evaluated against the state read (all physically pressed keys) */
	for (a = 0; a < 8; a++) {
		mx_gmark[a] &= cols[a];
		diff = (word)(cols[a] & ~mx_stable[a]);
		for (r = 0; diff && r < 13; r++) if ((diff >> r) & 1) {
			diff &= ~(1u << r);
			if (mx_ghost(cand, a, r)) {
				if (!((mx_gmark[a] >> r) & 1)) { mx_gmark[a] |= (word)(1u << r); ge_ghosts++; mx_push(GE_EV_GHOST, mx_sc(a, r)); changed = 1; }
				continue;
			}
			mx_stable[a] |= (word)(1u << r); mx_push(GE_EV_DOWN, mx_sc(a, r)); changed = 1;
		}
	}
	return changed;
}

#endif
