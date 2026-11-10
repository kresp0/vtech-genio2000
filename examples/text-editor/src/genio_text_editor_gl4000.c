/*
	genio_text_editor_gl4000 - text editor for the Spanish VTech Genio 2000 (VGLDK gl4000 target, 4x20 LCD, native CGROM profile).

	Build with -DGENIO_ES -DGENIO_NATIVE_CGROM (see the Makefile). It does not modify the internal firmware. It writes no bank ports.
	Ports used: 0x0A/0x0B (LCD), 0x10/0x11 (matrix, DATA0..7 of the DB25), 0x12 (LED bit 5, strobe bit 2, power-off bit 0).

	STATUS: developed against a host test suite and a full Z80 simulation, then tested on a real Genio 2000 by the author. Already validated in earlier ROMs:
	  power-off (OUT 0x12,1), reading of OFF, T642 transmission.

	Modules (src/): ge_keymap.h (key -> interpretation), ge_matrix.h (physical state of every key), ge_buffer.h (document),
	ge_unicode.h (Unicode / LCD / UTF-8), ge_proto.h (tramas + CRC). Este fichero: hardware, pantalla, modos y bucle principal.
	No global has an initial value (cart_crt0 does not run gsinit): everything is initialised in main().
*/
#include <vgldk.h>

/* ----------------------------------------------------------------- parametros */
#define GE_TICK_ITERS   650	/* wait-loop turns per iteration: 26 T per turn (16900 T) + about 1570 scan/processing instructions, about 5 ms per iteration at about 6.16 MHz (clock deduced from T642; aproximado, ajustable) */
#define GE_REP_DELAY    100	/* ticks until the first repeat (about 0.5 s) */
#define GE_REP_RATE     20	/* ticks between repeats (about 0.1 s) */
#define GE_EXIT_HOLD    300	/* ticks of RESPUESTA held to leave the diagnostic (about 1.5 s) */
#ifndef GE_DOC_MAX
#define GE_DOC_MAX      6144	/* maximum capacity of the document in characters (the tests built a small variant with -DGE_DOC_MAX=n) */
#endif
#define GE_RAM_END_MAX  0xDC00	/* the program data cannot go beyond here (the rest is stack: 0xDFF0 downwards) */
#define GE_CHUNK        48	/* UTF-8 bytes per export frame */

#define GE_NCOLS 20
#define GE_NROWS 4

static void ge_tx_raw(byte b);		/* TX of a byte through the DB25, defined further down */

#include "ge_unicode.h"
#include "ge_keymap.h"
#include "ge_matrix.h"
#include "ge_buffer.h"
#include "ge_proto.h"

/* ----------------------------------------------------------------- global state */
static byte doc[GE_DOC_MAX];
static byte want[GE_NCOLS * GE_NROWS];		/* what we want on the screen */
static byte scr[GE_NCOLS * GE_NROWS];		/* what is on the LCD (to write only the differences) */
static byte cur_row, cur_col, cur_style;	/* hardware cursor: style 0 hidden, 1 underline (insert), 2 block (overwrite), 3 both (SYM) */
static byte applied_style;

static byte caps, sym, statusbar;
static byte mode;				/* GE_MODE_* */
static byte help_page, last_char;
static word tick;
static word ram_ok;				/* document characters verified by the RAM self-test */
static byte ram_err;
static byte rep_sc, rep_on;
static word rep_cnt;
static byte ans_hold_exit;
static word ans_hold;
static word ev_seq;				/* diagnostic event number */
static word diag_n;
static byte d_type, d_sc, d_mods, d_kind, d_lcdk, d_lcd;	/* last event shown in the diagnostic */
static word d_val;
static byte tx_ok;

#define GE_MODE_EDIT   0
#define GE_MODE_HELP   1
#define GE_MODE_STATUS 2
#define GE_MODE_MENU   3
#define GE_MODE_DIAG   4
#define GE_MODE_CONFIRM 5

/* ----------------------------------------------------------------- T642 serial TX (literal copy of the serial test cartridge, validated on the Genio) */
static byte serial_byte, serial_hc, serial_f;
#define TXFIX 110

// Sends serial_byte as start + 8 data bits (LSB first) + stop; 10 periods of TXFIX + 16*serial_hc + 13*serial_f T-states (T642: hc=30, f=4).
static void tx_send(void) __naked {
	__asm
		push	af
		push	bc
		push	de
		push	hl
		ld	a, (_serial_byte)
		ld	c, a
		ld	a, (_serial_hc)
		ld	d, a
		ld	a, (_serial_f)
		ld	l, a
		ld	e, #10
		or	a, a			; carry = 0 -> start bit (LOW)
	tx_loop:
		sbc	a, a			; 4   A = 0x00 (bit 0) or 0xff (bit 1)
		cpl				; 4   port value = ~A : bit 1 -> 0x00 (pins HIGH), bit 0 -> 0xff (pins LOW)
		out	(0x10), a		; 11  printer data
		ld	a, #0xff		; 7
		out	(0x11), a		; 11  latch / write enable (GL4000 documentation)
		in	a, (0x12)		; 11  read-modify-write: only bit 2 (STROBE) changes
		or	a, #0x04		; 7
		out	(0x12), a		; 11
		and	a, #0xfb		; 7
		out	(0x12), a		; 11
		ld	h, d			; 4
	tx_d1:
		dec	h			; 4
		jr	nz, tx_d1		; 12 / 7      => 16*H - 5
		ld	b, l			; 4
	tx_d2:
		djnz	tx_d2			; 13 / 8      => 13*F - 5  (+4 for ld b,l)
		scf				; 4   next bit comes from bit 0 of C, ones shifted in => stop bit = 1
		rr	c			; 8
		dec	e			; 4
		jr	nz, tx_loop		; 12 / 7
		pop	hl
		pop	de
		pop	bc
		pop	af
		ret
	__endasm;
}

// Static level on the data pins: serial_byte = 1 -> HIGH (UART idle). One latch + strobe cycle.
static void line_set(void) __naked {
	__asm
		push	af
		ld	a, (_serial_byte)
		and	a, #0x01
		neg				; 0 -> 0x00, 1 -> 0xff
		cpl
		out	(0x10), a
		ld	a, #0xff
		out	(0x11), a
		in	a, (0x12)
		or	a, #0x04
		out	(0x12), a
		and	a, #0xfb
		out	(0x12), a
		pop	af
		ret
	__endasm;
}

static void ge_tx_raw(byte b) { serial_byte = b; tx_send(); }
static void line_idle(void) { serial_byte = 1; line_set(); }

/* ----------------------------------------------------------------- CAPS LOCK LED (port 0x12 bit 5) */
// Read-modify-write as the original firmware does (0x01F2: IN A,(0x12); OR 0x20 ...) but with bit 0 ALWAYS at 0:
// OUT (0x12),n with bit 0 at 1 is the power-off request (poweroff() writes 0x01), so no LED write may carry it.
static byte ge_led_state, ge_p12_last;
static void ge_led_set(byte on) {
	byte v;
	v = led_port;				/* IN A,(0x12) */
	v = (byte)(v & (byte)~0x01);
	if (on) v = (byte)(v | LED_MASK); else v = (byte)(v & (byte)~LED_MASK);
	led_port = v;				/* OUT (0x12),A */
	ge_p12_last = v; ge_led_state = on;
}

/* ----------------------------------------------------------------- espera */
static void tick_delay(void) __naked {
	__asm
		push	af
		push	hl
		ld	hl, #GE_TICK_ITERS
	tdl_loop:
		dec	hl
		ld	a, h
		or	a, l
		jr	nz, tdl_loop
		pop	hl
		pop	af
		ret
	__endasm;
}
static void off_check(void) { if (genio_off_poll()) poweroff(); }	/* OFF verified on the Genio: confirmation by holding + OUT (0x12),1 */
static void wait_ticks(word n) { while (n--) { tick_delay(); off_check(); } }

/* ----------------------------------------------------------------- physical reading of the matrix */
static void mx_hw_read(word *cols) {
	byte ix, m, a, b;
	m = 0x01;
	for (ix = 0; ix < 8; ix++) {
		keyboard_port_matrix_col_out = m;
		a = keyboard_port_matrix1_row_in;
		b = keyboard_port_matrix2_row_in;
		keyboard_port_matrix_col_out = 0x00;
		cols[ix] = (word)((byte)~a) | ((word)((byte)~b & 0x1F) << 8);
		m = (byte)(m << 1);
	}
}

/* ----------------------------------------------------------------- screen (only the cells that change are written; RAW path: 0x00 is not interpreted) */
static byte cur_applied;			/* cell where the LCD address was left (0xFF: it has to be set again) */
static void lcd_flush(void) {
	byte i = 0, r, c, a, written = 0;
	for (r = 0; r < GE_NROWS; r++)
		for (c = 0; c < GE_NCOLS; c++, i++) {
			if (want[i] == scr[i]) continue;
			lcd_text_row = r; lcd_text_col = c;
			genio_lcd_putraw(want[i]);	/* RAW path of genio_native.h: the byte goes as it is to the data port (0x00 = Á is not a terminator, 0x08/0x0A/0x0D are not commands) */
			scr[i] = want[i]; written = 1;
		}
	if (written) cur_applied = 0xFF;
	a = (byte)((word)cur_row * GE_NCOLS + cur_col);
	if (cur_applied != a) { lcd_writeControl(LCD_SETDDRAMADDR | lcd_map[a]); cur_applied = a; }
	if (cur_style != applied_style) {
		lcd_writeControl(LCD_DISPLAYCONTROL | LCD_DISPLAYON | ((cur_style & 1) ? LCD_CURSORON : 0) | ((cur_style & 2) ? LCD_BLINKON : 0));
		applied_style = cur_style;
	}
}
static void scr_invalidate(void) { byte i; for (i = 0; i < GE_NCOLS * GE_NROWS; i++) scr[i] = 0xFE; cur_applied = 0xFF; applied_style = 0xFF; }
static void ui_blank(void) { byte i; for (i = 0; i < GE_NCOLS * GE_NROWS; i++) want[i] = ' '; cur_style = 0; cur_row = 0; cur_col = 0; }

static void ui_putc(byte row, byte col, byte lcdcode) { if (row < GE_NROWS && col < GE_NCOLS) want[(word)row * GE_NCOLS + col] = lcdcode; }
/* UTF-8 text (1 to 3 bytes per character) -> LCD codes; returns the next column */
static byte ui_puts(byte row, byte col, const char *s) {
	byte b;
	word u, v;
	while ((b = (byte)*s++) != 0) {
		if (b < 0x80) u = b;
		else if ((b & 0xE0) == 0xC0) { u = ((word)(b & 0x1F) << 6) | ((byte)*s++ & 0x3F); }
		else { u = (word)(b & 0x0F) << 12; u |= (word)((byte)*s++ & 0x3F) << 6; u |= ((byte)*s++ & 0x3F); }
		v = ge_uni_to_lcd(u);
		ui_putc(row, col++, v == GE_LCD_NONE ? '?' : (byte)v);
	}
	return col;
}
static const char ge_hx[17] = "0123456789ABCDEF";
static byte ui_hex(byte row, byte col, word v, byte digits) {
	while (digits--) ui_putc(row, col++, ge_hx[(v >> (digits * 4)) & 15]);
	return col;
}
static byte ui_dec(byte row, byte col, word v, byte width) {
	byte i;
	for (i = 0; i < width; i++) { ui_putc(row, (byte)(col + width - 1 - i), (v || !i) ? (byte)('0' + v % 10) : ' '); v /= 10; }
	return (byte)(col + width);
}

/* ----------------------------------------------------------------- short notice on the last row (non-blocking: the keyboard is still served) */
#define GE_FLASH_TICKS 150	/* ~0,75 s */
static const char *flash_msg;
static word flash_left;
static void ui_flash(const char *msg) { flash_msg = msg; flash_left = GE_FLASH_TICKS; }
static void flash_overlay(void) {
	byte i;
	if (!flash_left) return;
	for (i = 0; i < GE_NCOLS; i++) want[(GE_NROWS - 1) * GE_NCOLS + i] = ' ';
	ui_puts(GE_NROWS - 1, 0, flash_msg);
}

/* ----------------------------------------------------------------- CGRAM accents and LCD start-up */
static void accents_setup(void) {
	genio_native_install_accents(0, 0);	/* explicit: A I O U -> CGRAM 0..3, design 0 (2 px accent, row 7 empty); nothing foreign in CGRAM in this profile */
}

/* ----------------------------------------------------------------- RAM self-test of the document */
/* three fast passes over doc[]: writes (l xor h) of the address, verifies and writes the complement, verifies and leaves it at zero.
   Detects stuck bits (both levels of every bit appear) and overlapping addresses (the pattern depends on both address bytes). */
static word ram_fail;
static void ram_pass(void) __naked {
	__asm
		push	af
		push	bc
		push	de
		push	hl
		ld	hl, #_doc
		ld	bc, #GE_DOC_MAX
	rp0:
		ld	a, l
		xor	a, h
		ld	(hl), a
		inc	hl
		dec	bc
		ld	a, b
		or	a, c
		jr	nz, rp0
		ld	hl, #_doc
		ld	bc, #GE_DOC_MAX
	rp1:
		ld	a, l
		xor	a, h
		cp	a, (hl)
		jr	nz, rpfail
		cpl
		ld	(hl), a
		inc	hl
		dec	bc
		ld	a, b
		or	a, c
		jr	nz, rp1
		ld	hl, #_doc
		ld	bc, #GE_DOC_MAX
	rp2:
		ld	a, l
		xor	a, h
		cpl
		cp	a, (hl)
		jr	nz, rpfail
		xor	a, a
		ld	(hl), a
		inc	hl
		dec	bc
		ld	a, b
		or	a, c
		jr	nz, rp2
		ld	hl, #0xffff
		ld	(_ram_fail), hl
		jr	rpdone
	rpfail:
		ld	de, #_doc
		or	a, a
		sbc	hl, de
		ld	(_ram_fail), hl
	rpdone:
		pop	hl
		pop	de
		pop	bc
		pop	af
		ret
	__endasm;
}
static void ram_test(void) {
	ram_pass();
	ram_err = (byte)(ram_fail != 0xFFFF);
	ram_ok = ram_err ? ram_fail : GE_DOC_MAX;
}

/* ----------------------------------------------------------------- modificadores */
static byte cur_mods(void) {
	byte m = 0;
	if (ge_mx_sc_down(GE_SC_SHIFT)) m |= GE_MOD_SHIFT | GE_MOD_SHIFT_R;
	if (ge_mx_sc_down(GE_SC_ALT)) m |= GE_MOD_ALT;
	if (caps) m |= GE_MOD_CAPS;
	if (sym) m |= GE_MOD_SYM;
	if (ed_ins) m |= GE_MOD_INS;
	return m;
}

/* ----------------------------------------------------------------- screen composition */
static void compose_edit(void) {
	byte r, c, i;
	ed_rows = statusbar ? 3 : 4;
	ed_fix();
	ed_render(want);
	ed_curpos(&r, &c);
	cur_row = r; cur_col = c;
	cur_style = (byte)((ed_ins ? 1 : 2) | (sym ? 3 : 0));
	if (statusbar) {
		for (i = 0; i < GE_NCOLS; i++) want[3 * GE_NCOLS + i] = ' ';
		ui_putc(3, 0, 'L'); ui_dec(3, 1, ed_line_no(), 3);
		ui_putc(3, 5, 'C'); ui_dec(3, 6, ed_col_no(), 3);
		ui_puts(3, 10, ed_ins ? "INS" : "SOB");
		if (caps) ui_puts(3, 14, "MAY");
		if (sym) ui_puts(3, 18, "SY");
	}
	flash_overlay();
}

static void compose_help(void) {
	ui_blank();
	switch (help_page) {
	case 0:
		ui_puts(0, 0, "AYUDA 1/5 EDICION"); ui_puts(1, 0, "BORRAR: borra atrás"); ui_puts(2, 0, "DEL: borra delante"); ui_puts(3, 0, "INS: ins./sobrescr."); break;
	case 1:
		ui_puts(0, 0, "AYUDA 2/5 CURSOR"); ui_puts(1, 0, "RETROCESO/AVANCE: ←→"); ui_puts(2, 0, "ALT+Ü ↑  ALT+; ↓"); ui_puts(3, 0, "ALT+RETRO/AVANC: I/F"); break;
	case 2:
		ui_puts(0, 0, "AYUDA 3/5 LETRAS"); ui_puts(1, 0, "ALT+vocal: á é í ó ú"); ui_puts(2, 0, "SHIFT+ALT+vocal:Á É"); ui_puts(3, 0, "BLOQ.MAYUS: LED"); break;
	case 3:
		ui_puts(0, 0, "AYUDA 4/5 FUNCIONES"); ui_puts(1, 0, "SHIFT+PAUSA: estado"); ui_puts(2, 0, "RESPUESTA: menu"); ui_puts(3, 0, "IMPRIMIR TEXTO:envia"); break;
	default:
		ui_puts(0, 0, "AYUDA 5/5 SIMBOLOS"); ui_puts(1, 0, "ALT+Q √ S + D - F ×"); ui_puts(2, 0, "ALT+G ÷  π: ALT+BLOQ"); ui_puts(3, 0, "luego A ←→ otra:sale"); break;
	}
}

static void compose_status(void) {
	ui_blank();
	ui_puts(0, 0, "PAUSA  (otra: sigue)");
	ui_puts(1, 0, "Car"); ui_dec(1, 4, ED_LEN(), 4); ui_putc(1, 8, '/'); ui_dec(1, 9, ed_cap, 4); ui_puts(1, 14, "Lin"); ui_dec(1, 17, ed_lines(), 3);
	ui_puts(2, 0, "L"); ui_dec(2, 1, ed_line_no(), 3); ui_puts(2, 5, "C"); ui_dec(2, 6, ed_col_no(), 3); ui_puts(2, 10, ed_ins ? "INS" : "SOB");
	ui_puts(2, 14, caps ? "MAY1" : "MAY0"); ui_puts(2, 18, sym ? "S1" : "S0");
	ui_puts(3, 0, ram_err ? "RAM ERR " : "RAM OK  "); ui_dec(3, 8, ram_ok, 4); ui_puts(3, 13, "LED"); ui_putc(3, 16, ge_led_state ? '1' : '0');
}

static void compose_menu(void) {
	ui_blank();
	ui_puts(0, 0, "MENU (otra: salir)");
	ui_puts(1, 0, "1 Exportar 2 Diagn.");
	ui_puts(2, 0, statusbar ? "3 Barra:SI 4 Nuevo" : "3 Barra:NO 4 Nuevo");
	ui_puts(3, 0, "5 Redibuj. 6 Ayuda");
}

static void compose_confirm(void) {
	ui_blank();
	ui_puts(0, 0, "¿BORRAR TODO?"); ui_puts(1, 0, "INTRO = si"); ui_puts(2, 0, "otra tecla = no");
}

static void compose_diag(void) {
	byte col;
	ui_blank();
	ui_putc(0, 0, d_type == GE_EV_DOWN ? 'v' : d_type == GE_EV_UP ? '^' : 'G');
	ui_hex(0, 1, d_sc, 2); ui_puts(0, 4, "C"); ui_hex(0, 5, (byte)(d_sc < 64 ? (d_sc & 7) : (d_sc & 7)), 1);
	ui_puts(0, 7, "R"); ui_hex(0, 8, (byte)(d_sc < 64 ? (d_sc >> 3) : (8 + ((d_sc - 0x40) >> 3))), 1);
	if (d_sc >= 64) ui_puts(0, 10, "M2"); else ui_puts(0, 10, "M1");
	col = 13; { const char *n = ge_name_of(d_sc); byte k; for (k = 0; n[k] && k < 7; k++) ui_putc(0, col++, (byte)n[k]); }
	ui_puts(1, 0, "SL"); ui_putc(1, 2, (d_mods & GE_MOD_SHIFT) ? '1' : '0');
	ui_puts(1, 4, "SR"); ui_putc(1, 6, (d_mods & GE_MOD_SHIFT_R) ? '1' : '0');
	ui_puts(1, 8, "AL"); ui_putc(1, 10, (d_mods & GE_MOD_ALT) ? '1' : '0');
	ui_puts(1, 12, "CP"); ui_putc(1, 14, (d_mods & GE_MOD_CAPS) ? '1' : '0');
	ui_puts(1, 16, "SY"); ui_putc(1, 18, (d_mods & GE_MOD_SYM) ? '1' : '0');
	ui_puts(2, 0, "LG:"); ui_putc(2, 3, d_kind == GE_K_CHAR ? 'C' : d_kind == GE_K_FUNC ? 'F' : d_kind == GE_K_MOD ? 'M' : '-');
	if (d_kind != GE_K_NONE) ui_hex(2, 4, (byte)d_val, 2); else ui_puts(2, 4, "--");
	ui_puts(2, 7, "U+"); if (d_kind == GE_K_CHAR) ui_hex(2, 9, d_val, 4); else ui_puts(2, 9, "----");
	ui_puts(2, 14, "#"); ui_hex(2, 15, diag_n, 4);
	if (d_lcdk == 1) { ui_puts(3, 0, "CGROM "); ui_hex(3, 6, d_lcd, 2); ui_putc(3, 9, d_lcd); }
	else if (d_lcdk == 2) { ui_puts(3, 0, "CGRAM slot"); ui_hex(3, 10, d_lcd, 1); ui_putc(3, 12, d_lcd); }
	else ui_puts(3, 0, "LCD --");
	ui_puts(3, 14, "LED"); ui_putc(3, 17, ge_led_state ? '1' : '0');
	if (ge_ev_lost) ui_putc(3, 19, '!');
}

static void redraw(void) {
	switch (mode) {
	case GE_MODE_HELP: compose_help(); break;
	case GE_MODE_STATUS: compose_status(); break;
	case GE_MODE_MENU: compose_menu(); break;
	case GE_MODE_CONFIRM: compose_confirm(); break;
	case GE_MODE_DIAG: compose_diag(); break;
	default: compose_edit(); break;
	}
	lcd_flush();
}

/* ----------------------------------------------------------------- diagnostic events through the DB25 */
static void send_hello(void) {
	pr_begin(GE_T_HELLO, 8);
	pr_b(GE_PROTO_VER); pr_b(serial_hc); pr_b(serial_f); pr_b(0); pr_w(ram_ok); pr_w(GE_DOC_MAX);
	pr_end();
}
static void send_status(byte code, word arg) {
	pr_begin(GE_T_STATUS, 7);
	pr_w(ev_seq++); pr_w(tick); pr_b(code); pr_w(arg);
	pr_end();
}
static void send_key(byte type, byte sc, byte mods, byte kind, word val, byte lcdk, byte lcd) {
	pr_begin(GE_T_KEY, 14);
	pr_w(ev_seq++); pr_w(tick);
	pr_b(type);					/* 0 release, 1 press, 2 ghost discarded */
	pr_b(sc);
	pr_b((byte)(sc < 64 ? (sc & 7) : (sc & 7)));	/* columna_out */
	pr_b((byte)(sc < 64 ? (sc >> 3) : (8 + ((sc - 0x40) >> 3))));	/* fila_in: 0..7 matriz 1, 8..12 matriz 2 */
	pr_b(mods); pr_b(kind); pr_w(val); pr_b(lcdk); pr_b(lcd);
	pr_end();
}
static void send_led(void) {
	pr_begin(GE_T_LED, 6);
	pr_w(ev_seq++); pr_w(tick); pr_b(ge_led_state); pr_b(ge_p12_last);
	pr_end();
}

/* ----------------------------------------------------------------- export of the document as UTF-8 */
static byte ex_buf[GE_CHUNK + 4];
static byte ex_n;

/* next character of the document (index i) as UTF-8 bytes in u8[]; returns the length */
static byte ex_char(word i, byte *u8) { byte c = ed_at(i); return ge_utf8(c == ED_NL ? 0x0A : ge_lcd_to_uni(c), u8); }

static void ex_flush(word off) {
	byte k;
	pr_begin(GE_T_DOC_DATA, (word)(2 + ex_n));
	pr_w(off);
	for (k = 0; k < ex_n; k++) pr_b(ex_buf[k]);
	pr_end();
}

static void do_export(void) {
	word i, len, total, off, chunk_off;
	byte u8[3], n, k;
	len = ED_LEN();
	pr_stream_init(); total = 0;
	for (i = 0; i < len; i++) { n = ex_char(i, u8); total += n; for (k = 0; k < n; k++) pr_stream_add(u8[k]); }
	{ word crc = pr_stream_crc;
	ui_blank(); ui_puts(0, 0, "EXPORTANDO..."); ui_puts(1, 0, "Car"); ui_dec(1, 4, len, 4); ui_puts(2, 0, "UTF-8"); ui_dec(2, 6, total, 5); ui_puts(2, 12, "bytes"); lcd_flush();
	pr_begin(GE_T_DOC_BEGIN, 6); pr_w(total); pr_w(len); pr_w(ed_lines()); pr_end();
	ex_n = 0; off = 0; chunk_off = 0;
	for (i = 0; i < len; i++) {
		n = ex_char(i, u8);
		if (ex_n + n > GE_CHUNK) { ex_flush(chunk_off); chunk_off = off; ex_n = 0; off_check(); }
		for (k = 0; k < n; k++) ex_buf[ex_n++] = u8[k];
		off += n;
	}
	if (ex_n) ex_flush(chunk_off);
	pr_begin(GE_T_DOC_END, 4); pr_w(total); pr_w(crc); pr_end();
	}
	ui_puts(0, 0, "ENVIADO          "); ui_puts(3, 0, "CRC en tramas DOC"); lcd_flush();
	wait_ticks(200);
}

/* ----------------------------------------------------------------- editing actions */
static void edit_char(word u) {
	word v = ge_uni_to_lcd(u);
	if (v == GE_LCD_NONE) return;
	if (!ed_put((byte)v)) { rep_on = 0; ui_flash("MEMORIA LLENA"); return; }
	last_char = (byte)v; ed_setwant();
}

static byte repeatable(byte kind, word val) {
	if (kind == GE_K_CHAR) return 1;
	if (kind != GE_K_FUNC) return 0;
	switch (val) {
	case GE_F_LEFT: case GE_F_RIGHT: case GE_F_UP: case GE_F_DOWN: case GE_F_PGUP: case GE_F_PGDN:
	case GE_F_ENTER: case GE_F_BKSP: case GE_F_DEL: case GE_F_TAB: case GE_F_REPEAT: return 1;
	}
	return 0;
}

static void edit_func(word f) {
	byte i, n;
	switch (f) {
	case GE_F_LEFT:  ed_left(); ed_setwant(); break;
	case GE_F_RIGHT: ed_right(); ed_setwant(); break;
	case GE_F_UP:    ed_up(); break;
	case GE_F_DOWN:  ed_down(); break;
	case GE_F_HOME:  ed_home(); ed_setwant(); break;
	case GE_F_END:   ed_end(); ed_setwant(); break;
	case GE_F_PGUP:  for (i = 0; i < ed_rows; i++) ed_up(); break;
	case GE_F_PGDN:  for (i = 0; i < ed_rows; i++) ed_down(); break;
	case GE_F_ENTER: if (!ed_insert(ED_NL)) { rep_on = 0; ui_flash("MEMORIA LLENA"); } ed_setwant(); break;
	case GE_F_BKSP:  ed_bksp(); ed_setwant(); break;
	case GE_F_DEL:   ed_del(); ed_setwant(); break;
	case GE_F_INS:   ed_ins = (byte)!ed_ins; break;
	case GE_F_REPEAT: if (last_char) { if (!ed_put(last_char)) { rep_on = 0; ui_flash("MEMORIA LLENA"); } ed_setwant(); } break;
	case GE_F_TAB:
		n = (byte)(4 - (ed_col_of(ed_gs) & 3));
		for (i = 0; i < n; i++) if (!ed_put(' ')) { rep_on = 0; ui_flash("MEMORIA LLENA"); break; }
		ed_setwant(); break;
	case GE_F_HELP:   mode = GE_MODE_HELP; help_page = 0; break;
	case GE_F_PAUSE:  mode = GE_MODE_STATUS; break;
	case GE_F_ANSWER: mode = GE_MODE_MENU; break;
	case GE_F_CLEAR:  mode = GE_MODE_CONFIRM; break;
	case GE_F_EXPORT: do_export(); break;
	}
}

static void enter_diag(void) {
	mode = GE_MODE_DIAG; diag_n = 0; d_type = GE_EV_UP; d_sc = 0; d_mods = cur_mods(); d_kind = GE_K_NONE; d_val = 0; d_lcdk = 0; d_lcd = 0;
	ans_hold = 0; ans_hold_exit = 0;
	send_hello(); send_status(GE_ST_DIAG_ENTER, 0);
}

static void menu_key(word u) {
	mode = GE_MODE_EDIT;
	switch (u) {
	case '1': do_export(); scr_invalidate(); break;
	case '2': enter_diag(); break;
	case '3': statusbar = (byte)!statusbar; break;
	case '4': mode = GE_MODE_CONFIRM; break;
	case '5': lcd_init(); lcd_cursor = 0; accents_setup(); scr_invalidate(); break;
	case '6': mode = GE_MODE_HELP; help_page = 0; break;
	}
}

/* ----------------------------------------------------------------- one key press according to the mode */
static void on_press(byte sc) {
	byte mods = cur_mods();
	if (ge_is_modifier(sc)) {
		if (sc == GE_SC_CAPS) {
			if (mods & GE_MOD_ALT) { sym = 1; }		/* ALT+BLOQ.MAYUS: one-use symbol prefix; it does not change the lock */
			else { caps = (byte)!caps; ge_led_set(caps); if (mode == GE_MODE_DIAG) send_led(); }
		}
		return;
	}
	ge_interpret(sc, mods);
	if (mode == GE_MODE_EDIT) {
		rep_sc = sc; rep_cnt = 0; rep_on = repeatable(ge_kind, ge_val);		/* before acting: a failure (memory full) switches it off */
		if (ge_kind == GE_K_CHAR) edit_char(ge_val);
		else if (ge_kind == GE_K_FUNC) edit_func(ge_val);
		sym = 0;
	} else if (mode == GE_MODE_HELP) {
		if (ge_kind == GE_K_FUNC && ge_val == GE_F_RIGHT) { if (help_page < 4) help_page++; }
		else if (ge_kind == GE_K_FUNC && ge_val == GE_F_LEFT) { if (help_page > 0) help_page--; }
		else if (ge_kind != GE_K_NONE) mode = GE_MODE_EDIT;
		rep_on = 0;
	} else if (mode == GE_MODE_STATUS) {
		if (ge_kind != GE_K_NONE) mode = GE_MODE_EDIT;
	} else if (mode == GE_MODE_MENU) {
		if (ge_kind == GE_K_CHAR) menu_key(ge_val); else mode = GE_MODE_EDIT;
	} else if (mode == GE_MODE_CONFIRM) {
		if (ge_kind == GE_K_FUNC && ge_val == GE_F_ENTER) { ed_clear(); }
		mode = GE_MODE_EDIT;
	}
	sym = (byte)(mode == GE_MODE_EDIT ? sym : 0);
}

/* ---- diagnostic: every change is shown and sent (presses do not repeat: one frame per change) ---- */
static void diag_event(byte type, byte sc) {
	byte mods = cur_mods();
	d_type = type; d_sc = sc; d_mods = mods; d_kind = GE_K_NONE; d_val = 0; d_lcdk = 0; d_lcd = 0;
	if (type == GE_EV_DOWN || type == GE_EV_UP) {
		ge_interpret(sc, mods);
		d_kind = ge_kind; d_val = ge_val;
		if (ge_kind == GE_K_CHAR) {
			word v = ge_uni_to_lcd(ge_val);
			if (v != GE_LCD_NONE) { d_lcd = (byte)v; d_lcdk = (byte)(v < 8 ? 2 : 1); }
		}
	}
	diag_n++;
	send_key(type, sc, mods, d_kind, d_val, d_lcdk, d_lcd);
	if (type == GE_EV_GHOST) send_status(GE_ST_GHOST, sc);
}

static byte process_events(void) {
	word ev;
	byte type, sc, any = 0;
	/* modifiers are evaluated with the final stable state: SHIFT/ALT pressed at the same time as a key count for it */
	while (mx_pop(&ev)) {
		type = (byte)(ev >> 8); sc = (byte)ev;
		any = 1;
		if (mode == GE_MODE_DIAG) diag_event(type, sc);
		if (type == GE_EV_DOWN) on_press(sc);
		else if (type == GE_EV_UP && rep_on && sc == rep_sc) rep_on = 0;
	}
	if (ge_ev_lost && mode == GE_MODE_DIAG) { send_status(GE_ST_EVQ_LOST, ge_ev_lost); ge_ev_lost = 0; }
	return any;
}

/* ----------------------------------------------------------------- bucle principal */
void main() {
	word cols[8];
	byte i, dirty;

	serial_hc = 30; serial_f = 4;			/* T642 */
	ge_mx_init();
	pr_seq = 0; ev_seq = 0; tick = 0; tx_ok = 1;
	caps = 0; sym = 0; statusbar = 0; mode = GE_MODE_EDIT; help_page = 0; last_char = 0;
	rep_on = 0; rep_sc = 0xFF; rep_cnt = 0; ans_hold = 0; ans_hold_exit = 0; flash_left = 0; flash_msg = "";
	cur_applied = 0xFF; applied_style = 0xFF; cur_style = 0; cur_row = 0; cur_col = 0;
	lcd_cursor = 0;					/* genio_lcd_putraw() must not write DISPLAYCONTROL in every cell: the cursor is managed in lcd_flush() */
	for (i = 0; i < GE_NCOLS * GE_NROWS; i++) { want[i] = ' '; scr[i] = 0xFE; }

	accents_setup();
	ge_led_set(0);
	line_idle();
	ram_test();
	ed_init(doc, ram_ok < GE_DOC_MAX ? (word)ram_ok : (word)GE_DOC_MAX);
	ui_blank(); ui_puts(0, 0, "EDITOR GENIO 2000"); ui_puts(1, 0, "RAM doc"); ui_dec(1, 8, ed_cap, 4); ui_puts(1, 13, ram_err ? "ERR" : "OK"); ui_puts(3, 0, "AYUDA: ayuda");
	lcd_flush();
	send_hello();
	wait_ticks(200);
	dirty = 1;

	for (;;) {
		tick_delay();
		tick++;
		mx_hw_read(cols);
		ge_mx_feed(cols);
		if (process_events()) dirty = 1;
		if (mode == GE_MODE_EDIT) {
			if (rep_on && ge_mx_sc_down(rep_sc)) {
				rep_cnt++;
				if (rep_cnt >= GE_REP_DELAY && ((rep_cnt - GE_REP_DELAY) % GE_REP_RATE) == 0) {
					byte mods = cur_mods();
					ge_interpret(rep_sc, mods);
					if (ge_kind == GE_K_CHAR) edit_char(ge_val); else if (ge_kind == GE_K_FUNC) edit_func(ge_val);
					dirty = 1;
				}
			} else rep_on = 0;
		} else if (mode == GE_MODE_DIAG) {
			if (ge_mx_sc_down(GE_SC_ANSWER)) { ans_hold++; if (ans_hold >= GE_EXIT_HOLD && !ans_hold_exit) { ans_hold_exit = 1; send_status(GE_ST_DIAG_EXIT, 0); mode = GE_MODE_EDIT; scr_invalidate(); dirty = 1; } }
			else ans_hold = 0;
		}
		if (flash_left) { flash_left--; if (!flash_left || mode == GE_MODE_EDIT) dirty = 1; }
		if (dirty) { redraw(); dirty = 0; }
		off_check();
	}
}
