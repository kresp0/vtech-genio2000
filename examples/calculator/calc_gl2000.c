/*
	calc_gl2000 - scientific calculator cartridge for the VTech Genio 2000 / Genius LEADER 4000 family (Z80, HD44780 4x20)

	Algebraic entry with a two-row editor, 16-digit decimal arithmetic (dec.h), an evaluator that works on the text
	(eval.h), display formats (fmt.h), calculus, statistics, bases, constants and a help viewer. The activity panel keys
	carry the functions (tables from gen_ui.py). Interrupts stay disabled; keyboard and LCD are driven directly.
	RAM: globals from C000 (mkcart.py checks the end), the stack below DFF0; the evaluator stops with "Too complex"
	when the stack would reach STACK_MIN.
	cart_crt0.s does not run gsinit: globals are assigned before use.
	Copyright (c) 2026 Santiago Crespo. GPL-3.0-or-later (built against VGLDK)
*/
// Only VGLDK's crt0 is used (it jumps to vgldk_init, defined at the end); none of its drivers.
#include <string.h>

typedef unsigned char byte;
typedef unsigned int word;
typedef signed int i16;
typedef unsigned int u16;
typedef unsigned long u32;

#define STACK_MIN 0xD780

__sfr __at 0x0A lcd_cport;
__sfr __at 0x0B lcd_dport;
__sfr __at 0x12 port_sys;

void err(byte code);
void stack_check(void);
void poll_break(void);

#include "tables.h"
#include "dec.h"
#include "vm.h"
#include "fmt.h"
#include "eval.h"

// ---- globals
#define BUFN 120
#define HISTN 512
byte buf[BUFN + 1];
byte blen, cur, vs;
byte scr[80], shown[80];
byte curcell;			// 0xFF: no cursor
byte editing, have_res, ovr, hyp, rmode, working, led;
char rtext[40];
const char *msg;
byte hist[HISTN];
u16 hlen;
byte hidx;
num stat[6];			// n, sum x, sum x2, sum y, sum y2, sum xy
num stv[15];
num res;
byte kb_m1[8], kb_m2[8];
byte key, kmod, off_armed;
u16 idle;
word jb_sp, jb_ix, jb_pc;
byte psel, pn;

static const byte map4[80] = {
	0,	1,	2,	3,	8,	9,	10,	11,	12,	13,	14,	15,	24,	25,	26,	27,	28,	29,	30,	31,
	64,	65,	66,	67,	72,	73,	74,	75,	76,	77,	78,	79,	88,	89,	90,	91,	92,	93,	94,	95,
	4,	5,	6,	7,	16,	17,	18,	19,	20,	21,	22,	23,	32,	33,	34,	35,	36,	37,	38,	39,
	68,	69,	70,	71,	80,	81,	82,	83,	84,	85,	86,	87,	96,	97,	98,	99,	100,	101,	102,	103
};

// ================================================================ low level
// returns 0; err(code) comes back here with the code (only one catcher at a time)
byte catch_err(void) __naked { __asm
		pop hl
		ld (_jb_pc), hl
		ld (_jb_sp), sp
		ld (_jb_ix), ix
		xor a, a
		jp (hl)
__endasm; }

void err(byte code) __naked __sdcccall(1) { code; __asm
		ld sp, (_jb_sp)
		ld ix, (_jb_ix)
		ld hl, (_jb_pc)
		jp (hl)
__endasm; }

void stack_check(void) __naked { __asm
		ld hl, #0
		add hl, sp
		ld de, #STACK_MIN
		or a, a
		sbc hl, de
		ret nc
		ld a, #E_COMPLEX
		jp _err
__endasm; }

static void delay_ms(byte n) __naked __sdcccall(1) { n; __asm
		or a, a
		ret z
		ld c, a
	1$:	ld b, #120		; 120 * 51 T = 1 ms at 6.13 MHz
	2$:	ex (sp), hl
		ex (sp), hl
		djnz 2$
		dec c
		jr nz, 1$
		ret
__endasm; }

static void lcd_wait(void) __naked { __asm
		ld b, #24		; 341 T (56 us) between LCD writes
	1$:	djnz 1$
		ret
__endasm; }

// ---- page 2 (selector 0x83) holds the microcode and the texts; this copy runs from RAM while it is mapped
static const byte farcode[11] = { 0x3E, 0x83, 0xD3, 0x03, 0xED, 0xB0, 0x3E, 0x80, 0xD3, 0x03, 0xC9 };	// ldir there
byte ramfn[11];
void *f_dst;
u16 f_src, f_n;
char p2buf[88];

static void fetch_asm(void) __naked { __asm
		ld hl, (_f_src)
		ld de, (_f_dst)
		ld bc, (_f_n)
		jp _ramfn
__endasm; }

static void fetch(void *dst, u16 src, u16 n) { f_dst = dst; f_src = src; f_n = n; fetch_asm(); }

// string i of a page-2 table, in p2buf
static char *p2s(u16 table, byte i) {
	u16 a;
	fetch(&a, table + 2 * i, 2);
	fetch(p2buf, a, sizeof(p2buf));
	return p2buf;
}

static void lcd_cmd(byte v) { lcd_cport = v; lcd_wait(); }
static void lcd_dat(byte v) { lcd_dport = v; lcd_wait(); }

static void load_glyphs(void) {
	byte i;
	lcd_cmd(0x40);
	for (i = 0; i < 64; i++) lcd_dat(glyphs[i]);
}

static void refresh(void) {
	byte i, a, last = 0xF0;
	for (i = 0; i < 80; i++) {
		if (scr[i] == shown[i]) continue;
		a = map4[i];
		if (a != (byte)(last + 1)) lcd_cmd(0x80 | a);
		lcd_dat(scr[i]);
		shown[i] = scr[i];
		last = a;
	}
	if (curcell == 0xFF) lcd_cmd(0x0C);
	else { lcd_cmd(0x80 | map4[curcell]); lcd_cmd(ovr ? 0x0E : 0x0F); }
}

static void p12(void) { port_sys = led & 0x20; }	// LED only: bit 0 would power off

// switch the unit off: bit 0 of port 0x12, then halt (the firmware's own sequence; the only HALT in the program)
static void poweroff(void) __naked { __asm
		di
		ld a, #0x01
		out (0x12), a
	1$:	halt
		jr 1$
__endasm; }

static void beep(void) __naked { __asm
		ld a, (_led)
		and a, #0x20
		ld c, a
		ld e, #80		; 80 half periods of 250 us: 2 kHz for 40 ms
	1$:	ld a, c
		xor a, #0x08
		ld c, a
		out (0x12), a
		ld b, #117
	2$:	djnz 2$
		dec e
		jr nz, 1$
		ld a, c
		and a, #0x20
		out (0x12), a
		ret
__endasm; }

// one pass over the 8 columns: kb_m1[c] = rows 0-7 and kb_m2[c] = rows 8-12 of column c, 1 = pressed
static void kb_scan(void) __naked { __asm
		ld hl, #_kb_m1
		ld de, #_kb_m2
		ld c, #0x01
	1$:	ld a, c
		out (0x10), a
		ld b, #4
	2$:	djnz 2$
		in a, (0x10)
		cpl
		ld (hl), a
		inc hl
		in a, (0x11)
		cpl
		and a, #0x1F
		ld (de), a
		inc de
		sla c
		jr nc, 1$
		xor a, a
		out (0x10), a
		ret
__endasm; }

#define SC(col, row) ((row) * 8 + (col))
#define K_NONE  0xFF
#define K_SHIFT SC(6, 6)
#define K_ALT   SC(1, 5)
#define K_CAPS  SC(1, 0)
#define K_CLEAR SC(6, 1)
#define K_OFF   SC(7, 9)

static byte down(byte k) {
	byte r = k >> 3;
	return (r < 8 ? kb_m1[k & 7] >> r : kb_m2[k & 7] >> (r - 8)) & 1;
}

// lowest non-modifier key pressed in the last scan, or K_NONE
static byte kb_first(void) {
	byte k;
	for (k = 0; k < 104; k++)
		if (k != K_SHIFT && k != K_ALT && k != K_CAPS && down(k)) return k;
	return K_NONE;
}

static void off_check(void) {
	if (!down(K_OFF)) off_armed = 1;
	else if (off_armed) poweroff();
}

// waits for a key: two equal scans 6 ms apart; arrows and DEL repeat after 450 ms. Sets key and kmod.
static void getkey(void) {
	byte k, last = key, n = 0;
	idle = 0;
	for (;;) {
		kb_scan(); off_check();
		k = kb_first();
		rng += k + n;
		if (k != K_NONE) {
			if (k != last) {
				delay_ms(6); kb_scan();
				if (kb_first() == k) break;
			} else if (++n > 60 && (k == SC(7, 2) || k == SC(7, 3) || k == SC(7, 5))) { n = 52; break; }
		} else { last = K_NONE; n = 0; }
		delay_ms(7);
		if (++idle == 50000) poweroff();	// about 6 minutes without a key
	}
	key = k;
	kmod = down(K_SHIFT) | down(K_ALT) << 1;
	idle = 0;
}

// action of the key just read (0 = none), and activity panel index in pn (0xFF for the main keyboard)
static byte action(void) {
	byte r = key >> 3;
	pn = 0xFF;
	if (r < 8) return keymain[key][kmod & 2 ? 2 : kmod & 1];
	pn = (key & 7) * 5 + r - 8;
	return keyact[pn][kmod & 1];
}

// ================================================================ screen helpers
static void at(byte r, byte c) { wp = (char *)scr + r * 20 + c; }
static void w_str(const char *s) { while (*s) *wp++ = *s++; }
// s right-aligned on the row of wp
static void w_right(const char *s) {
	wp = (char *)scr + ((byte)(wp - (char *)scr) / 20) * 20 + 20 - strlen(s);
	w_str(s);
}

static void cls(void) { memset(scr, ' ', 80); curcell = 0xFF; }
static void blank(byte r) { memset(scr + r * 20, ' ', 20); }

// help text: rows separated by \n
static void w_rows(byte r, const char *s) {
	at(r, 0);
	for (; *s; s++) { if (*s == '\n') at(++r, 0); else *wp++ = *s; }
}

static byte ask(const char *q) {
	byte a;
	blank(3); at(3, 0); w_str(q); curcell = 0xFF; refresh();
	do { getkey(); a = action(); } while (a != CM_ENTER && key != SC(4, 5) && a != CM_CLEAR);
	return a == CM_ENTER;
}

// fmt_num into o, shortened to SCI when longer than w characters
static void fmt_fit(char *o, const num *x, byte w) {
	byte f = dispfmt, d = dispdig;
	char *sw = wp;	// fmt_num moves wp too
	fmt_num(o, x);
	if (strlen(o) > w) { dispfmt = FMT_SCI; dispdig = w - 7; fmt_num(o, x); dispfmt = f; dispdig = d; }
	wp = sw;
}

// ================================================================ list picker
// row(i) writes item i at wp (19 columns); top(i) writes row 0 for the selected item. Returns the action that
// ended it (CM_ENTER: psel is the item).
static byte pick(byte n, void (*row)(byte), void (*top)(byte)) {
	byte a, i, t;
	for (;;) {
		cls();
		at(0, 0); top(psel);
		t = psel - psel % 3;
		for (i = 0; i < 3 && t + i < n; i++) {
			at(i + 1, 0); *wp++ = t + i == psel ? '>' : ' ';
			row(t + i);
		}
		refresh();
		getkey(); a = action();
		if (a == CM_RIGHT || a == CM_DOWN) psel = psel + 1 < n ? psel + 1 : 0;
		else if (a == CM_LEFT || a == CM_UP) psel = psel ? psel - 1 : n - 1;
		else if (a == CM_ENTER || a == CM_CLEAR || a == CM_HELP || a == STR_ANS) return a;
	}
}

// ================================================================ editor
static byte isop(const byte *s) {
	byte c = s[0];
	if (c == C_CUBE) return s[1] != C_SQRT;
	return c == '+' || c == '-' || c == C_TIMES || c == C_DIV || c == '^' || c == C_SQ || c == C_INV || c == '!' ||
		c == '%' || c == C_STO || c == C_XRT;
}

static void start_edit(byte keep) {
	if (!keep) { blen = 0; buf[0] = 0; cur = 0; }
	editing = 1; have_res = 0; msg = 0; hidx = 0;
}

static void insert(const byte *s) {
	if (!editing) {
		start_edit(0);
		if (isop(s)) insert((const byte *)"Ans");
	}
	for (; *s; s++) {
		if (ovr && cur < blen) { buf[cur++] = *s; continue; }
		if (blen >= BUFN) { beep(); return; }
		memmove(buf + cur + 1, buf + cur, blen - cur + 1);
		buf[cur++] = *s; blen++;
	}
}

static byte is_low(byte c) { return c >= 'a' && c <= 'z'; }

// deletes the character before the cursor, or the whole name of a function, Ans, or symbol with its '('
static void backspace(void) {
	byte n = 1, c;
	if (!cur) return;
	c = buf[cur - 1];
	if (c == '(' && cur > 1) {
		c = buf[cur - 2];
		if (c == C_SQRT || c == C_INT || c == C_SUM) n = cur > 2 && c == C_SQRT && buf[cur - 3] == C_CUBE ? 3 : 2;
		else if (cur >= 5 && !memcmp(buf + cur - 5, "d/dx(", 5)) n = 5;
		else while (n < cur && is_low(buf[cur - n - 1])) n++;
	} else if (is_low(c)) { while (n < cur && is_low(buf[cur - n - 1])) n++; }
	else if (cur >= 3 && !memcmp(buf + cur - 3, "Ans", 3)) n = 3;
	memmove(buf + cur - n, buf + cur, blen - cur + 1);
	cur -= n; blen -= n;
}

static void hist_add(void) {
	byte n = blen + 1;
	u16 m;
	if (!blen) return;
	if (hlen >= n && !memcmp(hist + hlen - n, buf, n) && (hlen == n || !hist[hlen - n - 1])) return;	// same as the newest
	while (hlen + n > HISTN) {
		m = strlen((char *)hist) + 1;
		memmove(hist, hist + m, hlen - m); hlen -= m;
	}
	memcpy(hist + hlen, buf, n); hlen += n;
}

// k-th newest line (1 = newest) into buf; 0 when there are fewer
static byte hist_get(byte k) {
	u16 i;
	byte cnt = 0, j;
	for (i = 0; i < hlen; i++) if (!hist[i]) cnt++;
	if (k > cnt || !k) return 0;
	for (i = 0, j = cnt - k; j; i++) if (!hist[i]) j--;
	strcpy((char *)buf, (char *)hist + i);
	blen = strlen((char *)buf); cur = blen;
	return 1;
}

static const char * const errmsg[8] = { "", "Syntax error", "Math error", "Overflow", "Too complex", "Break",
	"No root found", "Argument error" };

static void status(void) {
	static const char * const ang[3] = { "DEG", "RAD", "GRA" };
	static const char * const fm[4] = { "NORM", "FIX", "SCI", "ENG" };
	static const char * const bs[4] = { "", "HEX", "BIN", "OCT" };
	at(0, 0); w_str(ang[angmode]);
	at(0, 4); w_str(fm[dispfmt]);
	if (dispfmt == FMT_FIX || dispfmt == FMT_SCI) put_int(dispfmt == FMT_SCI && !dispdig ? 10 : dispdig);
	at(0, 10); w_str(bs[basemode]);
	at(0, 14); if (hyp) w_str("HYP"); else if (ovr) w_str("OVR");
}

// result text for ans in the current mode; returns an error code from the formatting (base out of range)
static byte format_res(void) {
	byte e = catch_err();
	if (e) return e;
	vtop = vstk;
	if (rmode == 1 && fmt_frac(rtext, &ans)) return 0;
	if (rmode == 2 && fmt_dms(rtext, &ans)) return 0;
	if (rmode) { rmode = 0; beep(); }
	if (basemode) fmt_base(rtext, &ans); else fmt_num(rtext, &ans);
	return 0;
}

static void draw(void) {
	byte i, n;
	cls(); status();
	if (cur < vs) vs = cur - cur % 20;
	while (cur >= vs + 40) vs += 20;
	if (vs > 0) scr[18] = '<';
	if (blen > vs + 40) scr[19] = '>';
	for (i = 0; i < 40 && vs + i < blen; i++) scr[20 + i] = buf[vs + i];
	if (msg) { at(3, 0); w_str(msg); }
	else if (have_res) {
		n = strlen(rtext);
		memcpy(scr + 80 - n, rtext, n);
	}
	if (editing) curcell = 20 + cur - vs;
	refresh();
}

static void show_error(byte e) {
	msg = errmsg[e];
	if (e == E_SYNTAX && errpos) cur = errpos - buf;
	if (cur > blen) cur = blen;
	editing = 1; have_res = 0;
	beep();
}

static byte run(void) {
	byte e = catch_err();
	if (e) return e;
	evaluate(&res, buf);
	return 0;
}

static void enter(void) {
	byte e;
	if (!blen && !hist_get(1)) return;
	hist_add();
	working = 0; led = 0x20; p12();
	errpos = 0;
	e = run();
	led = 0; p12();
	if (e) { show_error(e); return; }
	dcopy(&ans, &res);
	rmode = 0;
	editing = 0; msg = 0; hidx = 0;
	e = format_res();
	if (e) { show_error(e); return; }
	have_res = 1;
}

// poll during long calculations: BORRAR stops, OFF switches off
void poll_break(void) {
	kb_scan(); off_check();
	if (down(K_CLEAR)) { key = K_CLEAR; err(E_BREAK); }	// the key still held is not a new press
	if (!working) { working = 1; blank(3); at(3, 0); w_str("Working..."); curcell = 0xFF; refresh(); }
}

// ================================================================ lists
static void top_text(const char *s) { w_str(s); }

static void cat_row(byte i) { w_str(p2s(P2_STR, cat_str[i] - 1)); }
static void cat_top(byte i) { top_text(p2s(P2_CATH, i)); }

static void cst_row(byte i) {
	const char *v;
	byte n, w = 13, e;
	w_str(p2s(P2_CSTN, i));
	v = p2s(P2_CSTV, i); n = strlen(v);
	at(1 + i % 3, 7);
	if (n > w) {	// shorten the mantissa, keep the exponent
		for (e = 0; v[e] && v[e] != C_EXP; e++) ;
		memcpy(wp, v, w - (n - e)); wp += w - (n - e);
		w_str(v + e);
	} else w_str(v);
}
static void cst_top(byte i) { top_text(p2s(P2_CSTH, i)); }

static void var_row(byte i) {
	char t[24];
	*wp++ = i < 26 ? 'A' + i : 'A';
	if (i == 26) w_str("ns");
	*wp++ = '=';
	fmt_fit(t, i < 26 ? &vars[i] : &ans, 15);
	w_right(t);
}
static void var_top(byte i) { (void)i; top_text("MEMORIES"); }

static const char * const st_lab[15] = { "n", "\x08", "sx", "\x0Bx", "\x0Dx", "\x0Dx\x09", "\x0A", "sy", "\x0By", "\x0Dy",
	"\x0Dy\x09", "\x0Dxy", "a", "b", "r" };
static void st_row(byte i) {
	char t[24];
	w_str(st_lab[i]);
	if (iszero(&stv[i]) && stv[i].s) { t[0] = '-'; t[1] = 0; }	// marks "not defined"
	else fmt_fit(t, &stv[i], 15);
	w_right(t);
}
static void st_top(byte i) { (void)i; top_text("STATISTICS y=a+bx"); }

static byte stat_add(void) {
	num x, y, t;
	byte e = catch_err();
	if (e) return e;
	vtop = vstk;
	pp = buf; expr(&x, 0);
	dzero(&y);
	if (*pp == ',') { pp++; expr(&y, 0); }
	if (*pp) syntax();
	dadd(&stat[0], &stat[0], &K_ONE);
	dadd(&stat[1], &stat[1], &x); dmul(&t, &x, &x); dadd(&stat[2], &stat[2], &t);
	dadd(&stat[3], &stat[3], &y); dmul(&t, &y, &y); dadd(&stat[4], &stat[4], &t);
	dmul(&t, &x, &y); dadd(&stat[5], &stat[5], &t);
	return 0;
}

// stv: n, mean x, s x, sigma x, sum x, sum x2, mean y, s y, sigma y, sum y, sum y2, sum xy, a, b, r (microcode stats)
static byte stat_view(void) {
	byte i, e = catch_err();
	if (e) return e;
	vtop = vstk;
	for (i = 0; i < 6; i++) vpush(&stat[i]);
	vm(VM_stats, vstk);
	memcpy(stv, vstk + 10, sizeof(stv));
	return 0;
}

// x mean, y mean and sigma for the statistics list, in CGRAM slots 0, 2, 3 (not needed there)
static const byte stat_gl[24] = {
	0x1F, 0x00, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x00,		// x bar
	0x1F, 0x00, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x00,		// y bar
	0x00, 0x00, 0x0F, 0x12, 0x11, 0x11, 0x0E, 0x00 };	// sigma

static const char * const fm_name[4] = { "NORM", "FIX", "SCI", "ENG" };
static const char * const fm_help[4] = { "Normal: 12 digits", "Fixed decimals", "Scientific", "Engineering" };
static void fm_row(byte i) { w_str(fm_name[i]); }
static void fm_top(byte i) { w_str(fm_help[i]); }

static void digits_prompt(byte f) {
	byte a, k;
	blank(3); at(3, 0); w_str("Digits? 0-9"); refresh();
	for (;;) {
		getkey(); a = action();
		if (a == CM_CLEAR || a == CM_ENTER) return;
		if (a && a < 0xC0) {
			k = *p2s(P2_STR, a - 1);
			if (k >= '0' && k <= '9' && !p2buf[1]) { dispfmt = f; dispdig = k - '0'; return; }
		}
	}
}

static void help_view(byte page, byte row) {
	byte a;
	for (;;) {
		cls();
		w_rows(0, p2s(P2_HELP, page));
		if (row < 4) curcell = row * 20;
		refresh();
		getkey(); a = action();
		row = 0xFF;
		if (pn != 0xFF && keyhelp[pn] != 0xFF) { page = keyhelp[pn] >> 2; row = keyhelp[pn] & 3; }
		else if (a == CM_RIGHT || a == CM_DOWN) page = page + 1 < NHELP ? page + 1 : 0;
		else if (a == CM_LEFT || a == CM_UP) page = page ? page - 1 : NHELP - 1;
		else if (a == CM_ENTER || a == CM_HELP || a == CM_CLEAR || a == STR_ANS) return;
	}
}

static void reset_all(void) {
	byte i;
	for (i = 0; i < 26; i++) dzero(&vars[i]);
	for (i = 0; i < 6; i++) dzero(&stat[i]);
	dzero(&ans); dzero(&res);
	angmode = 0; dispfmt = FMT_NORM; dispdig = 0; basemode = 0;
	hlen = 0; hidx = 0; ovr = 0; hyp = 0; rmode = 0;
	blen = 0; buf[0] = 0; cur = 0; vs = 0;
	editing = 1; have_res = 0; msg = 0;
}

// ================================================================ commands
static void insert_value(const char *v) {
	byte c = cur && editing ? buf[cur - 1] : 0;
	if ((c >= '0' && c <= '9') || c == '.' || c == C_EXP) insert((const byte *)"\xB7");
	insert((const byte *)v);
}

static void command(byte a) {
	byte e;
	switch (a) {
	case CM_ENTER: enter(); break;
	case CM_LEFT: if (!editing) { start_edit(1); cur = blen; } else if (cur) cur--; break;
	case CM_RIGHT: if (!editing) { start_edit(1); cur = 0; } else if (cur < blen) cur++; break;
	case CM_HOME: start_edit(1); cur = 0; break;
	case CM_END: start_edit(1); cur = blen; break;
	case CM_DEL: if (!editing) { start_edit(1); cur = blen; } backspace(); msg = 0; break;
	case CM_DELF: start_edit(1); if (cur < blen) { cur++; backspace(); } break;
	case CM_CLEAR: start_edit(0); break;
	case CM_INS: ovr ^= 1; hyp = 0; break;
	case CM_HELP: help_view(0, 0xFF); break;
	case CM_UP: if (hist_get(hidx + 1)) { e = hidx + 1; start_edit(1); hidx = e; } break;
	case CM_DOWN:
		if (hidx > 1 && hist_get(hidx - 1)) { e = hidx - 1; start_edit(1); hidx = e; }
		else start_edit(0);
		break;
	case CM_HYP: hyp ^= 1; break;
	case CM_DRG: angmode = angmode < 2 ? angmode + 1 : 0; break;
	case CM_BASE: basemode = (basemode + 1) & 3; rmode = 0; break;
	case CM_DEC: basemode = 0; break;
	case CM_FD: rmode = rmode == 1 ? 0 : 1; break;
	case CM_DMS: rmode = rmode == 2 ? 0 : 2; break;
	case CM_FORMAT:
		psel = dispfmt;
		if (pick(4, fm_row, fm_top) == CM_ENTER) {
			if (psel == FMT_FIX || psel == FMT_SCI) digits_prompt(psel); else { dispfmt = psel; dispdig = 0; }
		}
		break;
	case CM_CATALOG:
		psel = 0;
		if (pick(NCAT, cat_row, cat_top) == CM_ENTER) insert((const byte *)p2s(P2_STR, cat_str[psel] - 1));
		break;
	case CM_CONST:
		psel = 0;
		if (pick(NCST, cst_row, cst_top) == CM_ENTER) insert_value(p2s(P2_CSTV, psel));
		break;
	case CM_VARS:
		psel = 0;
		if (pick(27, var_row, var_top) == CM_ENTER) {
			char t[4];
			t[0] = 'A' + (psel < 26 ? psel : 0); t[1] = psel < 26 ? 0 : 'n'; t[2] = 's'; t[3] = 0;
			insert_value(t);
		}
		break;
	case CM_STATADD:
		if (!blen) break;
		e = stat_add();
		if (e) { show_error(e); break; }
		hist_add();
		start_edit(0);
		msg = rtext; strcpy(rtext, "Data n="); wp = rtext + 7; put_fixed(&stat[0], stat[0].e, 0, 0); *wp = 0;
		break;
	case CM_STATVIEW:
		e = stat_view();
		if (e) { show_error(e); break; }
		for (e = 0; e < 24; e++) {
			if (!(e & 7)) lcd_cmd(0x40 | (e ? e + 8 : 0));
			lcd_dat(stat_gl[e]);
		}
		psel = 0;
		e = pick(15, st_row, st_top);
		load_glyphs();
		if (e == CM_ENTER && !(iszero(&stv[psel]) && stv[psel].s)) {
			dcopy(&ans, &stv[psel]);
			start_edit(0); insert((const byte *)"Ans");
		} else if (e == CM_CLEAR && ask("Clear data? INTRO/N")) for (e = 0; e < 6; e++) dzero(&stat[e]);
		break;
	case CM_RESET:
		if (ask("Clear all? INTRO/N")) reset_all();
		break;
	case CM_POWER: poweroff();
	}
	if (have_res && (a == CM_BASE || a == CM_DEC || a == CM_FD || a == CM_DMS || a == CM_FORMAT)) {	// show it again
		e = format_res();
		if (e) show_error(e);
	}
}

// ================================================================ main
void main(void);

// entered from cart_crt0 (interrupts disabled, SP at DFF0); the LCD is not initialised yet
void vgldk_init(void) {
	static const byte init[7] = { 0x38, 0x38, 0x38, 0x38, 0x01, 0x06, 0x0C };
	byte i;
	for (i = 0; i < 7; i++) { lcd_cport = init[i]; delay_ms(5); }
	main();
}

void main(void) {
	byte a;
	char t[8];
	memcpy(ramfn, farcode, sizeof(farcode));
	led = 0; p12();
	off_armed = 0; key = K_NONE; rng = 0xACE1; idle = 0;
	memset(shown, 0xFE, 80);
	fetch(p2buf, 0x8000, 4);
	if (memcmp(p2buf, "CALC", 4)) {	// the second half of the EEPROM did not come up with selector 0x83
		cls(); at(0, 0); w_str("Page 2 (0x83) of the"); at(1, 0); w_str("cartridge is missing"); refresh();
		for (;;) { kb_scan(); off_check(); }
	}
	fetch(vmcode, P2_VM, VMLEN);
	reset_all();
	load_glyphs();
	msg = "AYUDA: help";
	for (;;) {
		draw();
		getkey(); a = action();
		if (!a) continue;
		if (a >= 0xC0) { command(a); if (a != CM_HYP) hyp = 0; continue; }
		if (hyp && a <= 6) {	// sin( -> sinh(
			strcpy(t, p2s(P2_STR, a - 1));
			strcpy(t + strlen(t) - 1, "h(");
			insert((const byte *)t);
		} else insert((const byte *)p2s(P2_STR, a - 1));
		hyp = 0; msg = 0;
	}
}
