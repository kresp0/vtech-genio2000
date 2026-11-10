#ifndef GE_BUFFER_H
#define GE_BUFFER_H
/*
 * ge_buffer.h - document in a GAP BUFFER and a 20-column view.
 *
 *   buf[0 .. gs)      text before the cursor
 *   buf[gs .. ge)     hueco (libre)
 *   buf[ge .. cap)    text after the cursor
 *   cursor = gs.  Length = cap - (ge - gs).  One byte per character = LCD code; 0x0A separates lines.
 * Inserting/deleting at the cursor is O(1); moving the cursor moves the gap (it copies only the bytes that cross).
 * No dynamic memory. None of this touches the LCD or the ports (it can be tested on a PC the same way).
 *
 * LINE WRAP: by characters, at 20 columns. A line of n characters takes n/20 + 1 visual rows (a line of exactly 20
 * characters shows an empty final row, where the cursor falls at the end). `top` = position of the first character of the first visible row.
 * Horizontal scrolling: not needed (line wrap replaces it).
 */
#include "ge_types.h"

#define ED_COLS 20
#define ED_NL   0x0A

static byte *ed_buf;
static word ed_cap, ed_gs, ed_ge, ed_top;
static byte ed_want;		/* wanted column for up/down (0..19) */
static byte ed_rows;		/* visible text rows (4, or 3 with the status bar) */
static byte ed_ins;		/* 1 = insert, 0 = overwrite */
static word ed_rn, ed_rnext;	/* result of ed_row() */

#define ED_LEN() ((word)(ed_cap - (ed_ge - ed_gs)))

/* ---- search for the end of a line in a contiguous stretch of memory ----
 * ge_nl_back(end, n): n bytes that end just before `end`; returns how many there are from the last 0x0A (excluded) to `end` (n if none).
 * ge_nl_fwd(p, n)   : n bytes from p; returns how many there are before the first 0x0A (n if none).
 * On the Z80 these are CPDR / CPIR (21 T per byte): a 6000-character line without breaks does not slow the screen down. On a PC, equivalent loops. */
#ifdef __SDCC
static word ge_as_n, ge_as_res;
static const byte *ge_as_p;
static void ge_as_rfind(void) __naked {
	__asm
		push	af
		push	bc
		push	hl
		ld	bc, (_ge_as_n)
		ld	a, b
		or	a, c
		jr	z, rf_none
		ld	hl, (_ge_as_p)
		dec	hl
		ld	a, #0x0a
		cpdr
		jr	nz, rf_none
		ld	hl, (_ge_as_n)
		or	a, a
		sbc	hl, bc
		dec	hl
		jr	rf_store
	rf_none:
		ld	hl, (_ge_as_n)
	rf_store:
		ld	(_ge_as_res), hl
		pop	hl
		pop	bc
		pop	af
		ret
	__endasm;
}
static void ge_as_ffind(void) __naked {
	__asm
		push	af
		push	bc
		push	hl
		ld	bc, (_ge_as_n)
		ld	a, b
		or	a, c
		jr	z, ff_none
		ld	hl, (_ge_as_p)
		ld	a, #0x0a
		cpir
		jr	nz, ff_none
		ld	hl, (_ge_as_n)
		or	a, a
		sbc	hl, bc
		dec	hl
		jr	ff_store
	ff_none:
		ld	hl, (_ge_as_n)
	ff_store:
		ld	(_ge_as_res), hl
		pop	hl
		pop	bc
		pop	af
		ret
	__endasm;
}
static word ge_nl_back(const byte *end, word n) { ge_as_p = end; ge_as_n = n; ge_as_rfind(); return ge_as_res; }
static word ge_nl_fwd(const byte *p, word n) { ge_as_p = p; ge_as_n = n; ge_as_ffind(); return ge_as_res; }
#else
static word ge_nl_back(const byte *end, word n) { word d = 0; while (d < n && end[-1 - (long)d] != 0x0A) d++; return d; }
static word ge_nl_fwd(const byte *p, word n) { word d = 0; while (d < n && p[d] != 0x0A) d++; return d; }
#endif

static void ed_init(byte *buf, word cap) {
	ed_buf = buf; ed_cap = cap; ed_gs = 0; ed_ge = cap; ed_top = 0; ed_want = 0; ed_rows = 4; ed_ins = 1;
}
static void ed_clear(void) { ed_gs = 0; ed_ge = ed_cap; ed_top = 0; ed_want = 0; }

static byte ed_at(word i) { return ed_buf[i < ed_gs ? i : (word)(i + (ed_ge - ed_gs))]; }

/* moves the cursor (and the gap) to position pos (0..length) */
static void ed_goto(word pos) {
	if (pos < ed_gs) {
		while (ed_gs > pos) { ed_ge--; ed_gs--; ed_buf[ed_ge] = ed_buf[ed_gs]; }
	} else {
		while (ed_gs < pos) { ed_buf[ed_gs] = ed_buf[ed_ge]; ed_gs++; ed_ge++; }
	}
}

/* start of the line that contains p (p <= cursor: the whole stretch is before the gap) */
static word ed_line_start(word p) {
	if (p > ed_gs) { while (p > 0 && ed_at((word)(p - 1)) != ED_NL) p--; return p; }
	return (word)(p - ge_nl_back(ed_buf + p, p));
}
/* length of the line that starts at ls (it may cross the gap) */
static word ed_line_len(word ls) {
	word d, n;
	if (ls < ed_gs) {
		n = (word)(ed_gs - ls);
		d = ge_nl_fwd(ed_buf + ls, n);
		if (d < n) return d;
		return (word)(n + ge_nl_fwd(ed_buf + ed_ge, (word)(ed_cap - ed_ge)));
	}
	return ge_nl_fwd(ed_buf + ls + (ed_ge - ed_gs), (word)(ED_LEN() - ls));
}

static word ed_row_start(word p) {
	word ls = ed_line_start(p);
	return (word)(ls + ((word)(p - ls) / ED_COLS) * ED_COLS);
}
static byte ed_col_of(word p) { word ls = ed_line_start(p); return (byte)((word)(p - ls) % ED_COLS); }
static void ed_setwant(void) { ed_want = ed_col_of(ed_gs); }

/* visual row that starts at p: ed_rn = characters of the row (0..20); returns 1 if there is another row after it (ed_rnext = its start) */
static byte ed_row(word p) {
	word len = ED_LEN();
	byte n = 0;
	while (n < ED_COLS && (word)(p + n) < len && ed_at((word)(p + n)) != ED_NL) n++;
	ed_rn = n;
	if (n == ED_COLS) { ed_rnext = (word)(p + ED_COLS); return 1; }
	if ((word)(p + n) < len) { ed_rnext = (word)(p + n + 1); return 1; }
	return 0;
}

/* row/column of the cursor relative to top (requires a previous ed_fix()) */
static void ed_curpos(byte *row, byte *col) {
	word p = ed_top;
	byte rr = 0, more;
	for (;;) {
		more = ed_row(p);
		if (ed_gs <= (word)(p + ed_rn) && (ed_rn < ED_COLS || ed_gs < (word)(p + ED_COLS))) { *row = rr; *col = (byte)(ed_gs - p); return; }
		if (!more || rr == 250) { *row = rr; *col = (byte)ed_rn; return; }
		p = ed_rnext; rr++;
	}
}

/* normalises top and guarantees that the cursor is inside the visible rows (it scrolls as little as possible) */
static void ed_fix(void) {
	byte r, c;
	if (ed_top > ed_gs) ed_top = ed_gs;
	ed_top = ed_row_start(ed_top);
	ed_curpos(&r, &c);
	while (r >= ed_rows) { ed_row(ed_top); ed_top = ed_rnext; r--; }
}

/* ---- editing ---- */
static byte ed_insert(byte c) {
	if (ed_gs == ed_ge) return 0;		/* lleno */
	ed_buf[ed_gs++] = c;
	return 1;
}
static byte ed_put(byte c) {			/* writes according to the INS / OVR mode */
	if (!ed_ins && ed_ge < ed_cap && ed_buf[ed_ge] != ED_NL) ed_ge++;	/* overwrites the character under the cursor */
	return ed_insert(c);
}
static byte ed_bksp(void) { if (ed_gs == 0) return 0; ed_gs--; return 1; }
static byte ed_del(void) { if (ed_ge >= ed_cap) return 0; ed_ge++; return 1; }
static void ed_left(void) { if (ed_gs > 0) { ed_ge--; ed_gs--; ed_buf[ed_ge] = ed_buf[ed_gs]; } }
static void ed_right(void) { if (ed_ge < ed_cap) { ed_buf[ed_gs] = ed_buf[ed_ge]; ed_gs++; ed_ge++; } }
static void ed_home(void) { ed_goto(ed_line_start(ed_gs)); }
static void ed_end(void) { word ls = ed_line_start(ed_gs); ed_goto((word)(ls + ed_line_len(ls))); }

static void ed_up(void) {
	word ls = ed_line_start(ed_gs), off = (word)(ed_gs - ls), pls, n;
	byte k = (byte)(off / ED_COLS), kk, rl, w = ed_want;
	if (k > 0) { if (w > ED_COLS - 1) w = ED_COLS - 1; ed_goto((word)(ls + (word)(k - 1) * ED_COLS + w)); return; }
	if (ls == 0) return;
	pls = ed_line_start((word)(ls - 1));
	n = (word)(ls - 1 - pls);
	kk = (byte)(n / ED_COLS); rl = (byte)(n - (word)kk * ED_COLS);
	if (w > rl) w = rl;
	ed_goto((word)(pls + (word)kk * ED_COLS + w));
}
static void ed_down(void) {
	word ls = ed_line_start(ed_gs), off = (word)(ed_gs - ls), n = ed_line_len(ls), nls, n2;
	byte k = (byte)(off / ED_COLS), K = (byte)(n / ED_COLS), nk, maxc, w = ed_want;
	if (k < K) {
		nk = (byte)(k + 1);
		maxc = (nk < K) ? ED_COLS - 1 : (byte)(n - (word)K * ED_COLS);
		if (w > maxc) w = maxc;
		ed_goto((word)(ls + (word)nk * ED_COLS + w));
		return;
	}
	nls = (word)(ls + n + 1);
	if (nls > ED_LEN()) return;		/* last line */
	n2 = ed_line_len(nls);
	maxc = (n2 >= ED_COLS) ? ED_COLS - 1 : (byte)n2;
	if (w > maxc) w = maxc;
	ed_goto((word)(nls + w));
}

/* ---- vista ---- */
/* fills rows*20 cells with the LCD codes of the window (spaces where there is no text) */
static void ed_render(byte *cells) {
	word p = ed_top;
	byte r, i, alive = 1, more;
	for (r = 0; r < ed_rows; r++) {
		byte *row = cells + (word)r * ED_COLS;
		if (!alive) { for (i = 0; i < ED_COLS; i++) row[i] = ' '; continue; }
		more = ed_row(p);
		for (i = 0; i < ed_rn; i++) row[i] = ed_at((word)(p + i));
		for (; i < ED_COLS; i++) row[i] = ' ';
		if (more) p = ed_rnext; else alive = 0;
	}
}

/* statistics: logical line (1..) and column (1..) of the cursor, number of lines */
static word ed_count_nl(const byte *p, word n) {		/* number of 0x0A in n bytes */
	word d, c = 0;
	while (n) { d = ge_nl_fwd(p, n); if (d >= n) break; c++; p += d + 1; n = (word)(n - d - 1); }
	return c;
}
static word ed_line_no(void) { return (word)(1 + ed_count_nl(ed_buf, ed_gs)); }
static word ed_lines(void) { return (word)(1 + ed_count_nl(ed_buf, ed_gs) + ed_count_nl(ed_buf + ed_ge, (word)(ed_cap - ed_ge))); }
static word ed_col_no(void) { return (word)(ed_gs - ed_line_start(ed_gs) + 1); }

#endif
