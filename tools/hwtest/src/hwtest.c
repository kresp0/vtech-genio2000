/*
	hwtest - hardware test cartridge for the Spanish VTech Genio 2000. Genio -> PC only (printer-port soft UART, 9600 8N1),
	same transport, framing (protocol v2) and timing preset as the validated bank_diag / bank_dump (see firmware-dump/docs).

	Stages (each started with ENTER; S = skip the stage; power off at any time between stages):
	  A  entry state, NO writes: IFF/I at entry, shadows DFF0..DFF7, copy of C000-FFFF (RAM, and E000-FFFF probe)
	  B  IN of ports 00..FF (3 reads each); 0x0A/0x0B are skipped on purpose; no OUT
	  C  CPU clock (two bursts of 0x55 with a known extra delay) -- measured on the PC side
	  D  IRQ rate: EI + busy-wait (NO HALT) while the firmware ISR runs and calls our RAM hook (DFF5) that counts; progress frames at 1,5,20,100 IRQs, then 1000 IRQs timed on the PC side
	  E  LCD / LED questions (answer S or N):  CGRAM is read live?  codes 08-0F mirror 00-07?  LED toggles?
	  F  raw keyboard matrix logger (press ON, ALT, SHIFT, CAPS, the activity keys...; ENTER ends)
	  G  character-set pages 00-FF (photograph the 4 screens)
	  H  port 0x03 <- 00..07 (internal entries the firmware itself uses) + restore
	  I  port 0x03 <- 80..8F (cartridge pages) + restore
	  J  port 0x03 <- 08..1F + restore
	  K  cartridge /WR probe: ONE write of the value already stored at 0x9BF0 (see below)
	  L  port 0x03 <- 20,40,90,A0,C0 (single high bit) + restore
	Port 0x03 stages copy the window 8000-BFFF into RAM from a stub in RAM (the cartridge code is not visible while another
	entry is selected) and restore the entry before returning. Port 0x00/0x01/0x02/0x04/0x05/0x06 and 0x12 bit 0 are NEVER written.
	Memory writes are limited to RAM 0xC000-0xDFFF, with ONE exception, stage K: a single write to 0x9BF0 of the byte that is already
	there (idempotent even if /WR reaches the AT28C256 /WE), executed from RAM, followed by 16 polling reads and a 70 ms wait. A busy EEPROM
	(DQ6 toggling / DQ7 inverted) shows that /WR reaches the cartridge. The stage is skippable (S).
*/

#define LCD_MINIMAL
#include <vgldk.h>
#include "bank_common.h"

#define BUILD_ID    0x0100
#define TOOL_HW     4
#define TITLE       "HWTEST v1"

#define T_MEM    0x41
#define T_PORTS  0x42
#define T_WIN    0x43
#define T_CLK    0x44
#define T_IRQ    0x45
#define T_KEY    0x46
#define T_ANS    0x47
#define T_WRP    0x48

#define WINBUF   0xC800u	// 4 KiB bounce buffer (RAM)
#define STUB_WIN 0xD800u	// RAM stub: select entry, LDIR, restore
#define STUB_RD  0xD820u	// RAM stub: LD A,0 ; IN A,(n) ; RET   (n patched)
#define STUB_WR  0xD840u	// RAM stub: same-value write + polling reads (copied from wr_stub)
#define WR_ADDR  0x9BF0u	// inside the per-quarter marker area of the cartridge image: no code, no data used
#define HOOK_ADDR 0xD8A0u	// RAM hook called by the firmware ISR through DFF5/DFF6: counts interrupts
#define HOOK_CNT  0xD8B0u	// 16-bit interrupt counter (little endian)
#define SP_MIN   0xD900u
#define SP_MAX   0xE000u
#define CART_RESTORE 0x80	// port 0x03 value that maps cartridge page 0 (value the firmware itself writes before reading the cartridge)

#define IRQ_TARGET 1000u
#define CLK_N      1200u

__sfr __at 0x03 port_win2;
__sfr __at 0x12 port_sys;

static const byte stub_win[17] = { 0xD3, 0x03, 0, 0, 0, 0, 0xED, 0xB0, 0x3E, CART_RESTORE, 0xD3, 0x03, 0, 0, 0, 0, 0xC9 };
static const byte stub_rd[5] = { 0x3E, 0x00, 0xDB, 0x00, 0xC9 };
static const byte stub_hook[8] = { 0x2A, 0xB0, 0xD8, 0x23, 0x22, 0xB0, 0xD8, 0xC9 };	// LD HL,(D8B0) ; INC HL ; LD (D8B0),HL ; RET

static byte w_sel;
static word w_src, w_dst, w_len;
static byte rp_val, variant, e_i, e_f, cur_stage, sp_ok, qid;
static byte rec[96];

static void win_copy_call(void) __naked {
	__asm
		ld	a, (_w_sel)
		ld	hl, (_w_src)
		ld	de, (_w_dst)
		ld	bc, (_w_len)
		call	0xD800
		ret
	__endasm;
}
static void rd_call(void) __naked {
	__asm
		call	0xD820
		ld	(_rp_val), a
		ret
	__endasm;
}
static byte rd_port(byte n) { *(volatile byte *)(STUB_RD + 3) = n; rd_call(); return rp_val; }

// extra delay between bytes of the second clock burst: CALL 17 + body 6712 = 6729 T (EXTRA_T in hwtest_rx.py)
static void gap_dly(void) __naked {
	__asm
		push	af
		push	bc
		ld	b, #0
	gd1:
		djnz	gd1
		ld	b, #0
	gd2:
		djnz	gd2
		pop	bc
		pop	af
		ret
	__endasm;
}
// same-value write probe; copied to RAM and run there. HL = target (cartridge window), DE = result buffer (17 bytes)
static void wr_stub(void) __naked {
	__asm
		ld	a, (hl)
		ld	(hl), a
		ld	b, #16
	wr1:
		ld	a, (hl)
		ld	(de), a
		inc	de
		djnz	wr1
		ld	bc, #0x4000
	wr2:
		dec	bc
		ld	a, b
		or	a, c
		jr	nz, wr2
		ld	a, (hl)
		ld	(de), a
		ret
	__endasm;
}
static void wr_call(void) __naked {
	__asm
		ld	hl, (_w_src)
		ld	de, (_w_dst)
		call	0xD840
		ret
	__endasm;
}
static word irq_target;
// EI, busy-wait (no HALT: the firmware itself only ever HALTs when powering off) until the hook counter reaches irq_target, DI.
static void irq_wait(void) __naked {
	__asm
		ei
	iw1:
		ld	hl, (0xD8B0)
		ld	de, (0xD8B0)
		or	a, a
		sbc	hl, de
		jr	nz, iw1			; torn read (interrupt between the two bytes): retry
		ld	hl, (0xD8B0)
		ld	de, (_irq_target)
		or	a, a
		sbc	hl, de
		jr	c, iw1
		di
		ret
	__endasm;
}

static void screen(const char *a, const char *b, const char *c) {
	blank();
	put(0, 0, TITLE); wn[0][10] = 'A' + cur_stage;
	put(1, 0, a); put(2, 0, b); put(3, 0, c);
	draw();
}

// ---- stage control ----
static byte wait_stage(const char *l1, const char *l2) {	// 1 = run (ENTER), 0 = skip (S)
	byte c;
	blank();
	put(0, 0, TITLE); wn[0][11] = 'A' + cur_stage;
	put(1, 0, l1); put(2, 0, l2); put(3, 0, "ENTER=run  S=skip");
	draw();
	while (1) {
		c = kb_event();
		if (c == '\r') { kb_last = kb_scan(); return 1; }
		if (c == 'S') { kb_last = kb_scan(); return 0; }
		if (cur_stage == 0) session++;
		wb_n = 96; wait_bits();
	}
}
static void send_stage(byte skipped) {
	frame_begin(T_STAGE, SEL_NONE, 0, 0, 3);
	tx_crc(cur_stage); tx_crc(skipped); tx_crc(1);
	frame_end();
	serial_byte = 1; line_set();
}

static byte ask(byte id, const char *q) {	// question on row 3 only (rows 0-2 keep the pattern); returns S / N / \r
	byte c;
	for (c = 0; c < NCOLS; c++) wn[3][c] = ' ';
	put(3, 0, q);
	draw();
	while (1) {
		c = kb_event();
		if (c == 'S' || c == 'N' || c == '\r') break;
		wb_n = 96; wait_bits();
	}
	kb_last = kb_scan();
	frame_begin(T_ANS, SEL_NONE, 0, 0, 2);
	tx_crc(id); tx_crc(c);
	frame_end();
	serial_byte = 1; line_set();
	return c;
}

// ---- stage A ----
static void st_entry(void) {
	word a;
	byte i;
	frame_begin(T_START, SEL_NONE, 0, 0, 16);
	tx_crc(TOOL_HW); tx_w16(BUILD_ID); tx_w16(sp_main);
	tx_crc(variant); tx_crc(e_f); tx_crc(e_i);
	for (i = 0; i < 8; i++) tx_crc(*(volatile byte *)(0xDFF0 + i));
	frame_end();
	for (a = 0xC000; ; a += 0x80) {
		blank(); put(0, 0, "A: copy C000-FFFF"); put(1, 0, "addr "); put_hex4(1, 5, a); draw();
		frame_begin(T_MEM, SEL_NONE, a, 0, 128);
		for (i = 0; i < 128; i++) tx_crc(*(volatile byte *)(a + i));
		frame_end();
		if (a == 0xFF80) break;
	}
}

// ---- stage B ----
static void st_ports(void) {
	word n;
	byte k;
	screen("B: reading ports", "", "");
	frame_begin(T_PORTS, SEL_NONE, 0, 0, 768);
	for (n = 0; n < 256; n++) {
		for (k = 0; k < 3; k++) {
			if (n == 0x0A || n == 0x0B) tx_crc(0xEE);	// skipped: an IN on the LCD ports could clock garbage into the controller
			else tx_crc(rd_port((byte)n));
		}
	}
	frame_end();
}

// ---- stage C ----
static void tx_burst(word n, byte gap) {
	while (n--) { serial_byte = 0x55; tx_send(); if (gap) gap_dly(); }
}
static void st_clock(void) {
	screen("C: clock bursts", "burst 1/2", "");
	serial_byte = 1; line_set();
	frame_begin(T_CLK, SEL_NONE, 0, 0, 5);
	tx_crc(0); tx_w16(CLK_N); tx_w16(CLK_N);
	frame_end();
	serial_byte = 1; line_set(); wb_n = 3840; wait_bits();
	tx_burst(CLK_N, 0);
	serial_byte = 1; line_set(); wb_n = 3840; wait_bits();
	screen("C: clock bursts", "burst 2/2", "");
	tx_burst(CLK_N, 1);
	serial_byte = 1; line_set(); wb_n = 3840; wait_bits();
	frame_begin(T_CLK, SEL_NONE, 0, 0, 5);
	tx_crc(1); tx_w16(CLK_N); tx_w16(CLK_N);
	frame_end();
	serial_byte = 1; line_set();
}

// ---- stage D ----
static word hook_count(void) { return *(volatile word *)HOOK_CNT; }
static void irq_frame(byte phase) {
	byte i;
	frame_begin(T_IRQ, SEL_NONE, 0, 0, 13);
	tx_crc(phase); tx_w16(hook_count());
	for (i = 0; i < 8; i++) tx_crc(*(volatile byte *)(0xDB24 + i));
	tx_crc(*(volatile byte *)0xDB00); tx_crc(*(volatile byte *)0xDB01);
	frame_end();
	serial_byte = 1; line_set();
}
static const word irq_marks[4] = { 1, 5, 20, 100 };
static void st_irq(void) {
	byte i, o4, o5, o6;
	word c0;
	screen("D: IRQ rate", "NO key presses", "off if it stops");
	o4 = *(volatile byte *)0xDFF4; o5 = *(volatile byte *)0xDFF5; o6 = *(volatile byte *)0xDFF6;
	*(volatile word *)HOOK_CNT = 0;
	*(volatile byte *)0xDFF5 = (byte)HOOK_ADDR; *(volatile byte *)0xDFF6 = (byte)(HOOK_ADDR >> 8);
	irq_frame(0);						// phase 0: before the first EI (count 0)
	for (i = 0; i < 4; i++) {					// phase 2: progress frames, tell how far the unit gets
		irq_target = irq_marks[i]; irq_wait();
		irq_frame(2);
	}
	c0 = hook_count();
	irq_frame(3);						// phase 3: start of the timed window (count c0)
	irq_target = c0 + IRQ_TARGET; irq_wait();
	irq_frame(1);						// phase 1: end of the timed window
	*(volatile byte *)0xDFF4 = o4; *(volatile byte *)0xDFF5 = o5; *(volatile byte *)0xDFF6 = o6;
	port_win2 = CART_RESTORE;
	lcd_reset_screen();
}

// ---- stage E ----
static void lcd_cg(byte glyph, byte v0, byte v1) {	// 8 rows of two alternating values
	byte r;
	lcd_writeControl(0x40 | (glyph << 3));
	for (r = 0; r < 8; r++) lcd_writeData((r & 1) ? v1 : v0);
}
static void fill_codes(byte first, byte mask) {
	byte r, c;
	for (r = 0; r < 3; r++) for (c = 0; c < NCOLS; c++) { wn[r][c] = first + ((c + r) & mask); sh[r][c] = ~wn[r][c]; }	// rows 0-2; force a rewrite
	draw();
}
static void st_lcd(void) {
	byte g, t;
	for (g = 0; g < 8; g++) lcd_cg(g, 0x1F, 0x1F);
	fill_codes(0, 0);
	ask(1, "solid blocks? S/N");
	for (g = 0; g < 8; g++) lcd_cg(g, 0x15, 0x0A);
	ask(2, "all changed? S/N");
	for (g = 0; g < 8; g++) lcd_cg(g, (byte)(1 << g) | 1, (byte)(0x10 >> (g & 3)));
	fill_codes(0, 7);
	ask(3, "8 shapes? S/N");
	for (g = 0; g < 8; g++) lcd_cg(g, (byte)(0x1F >> g), 0x04);
	ask(4, "all changed? S/N");
	fill_codes(8, 7);
	ask(5, "08-0F = 00-07? S/N");
	lcd_reset_screen();
	// LED (port 0x12 bit 5, read-modify-write as the firmware does; bit 0 = power off is never touched)
	t = port_sys;
	for (g = 0; g < 6; g++) {
		port_sys = (g & 1) ? (byte)(t & 0xDB) : (byte)((t | 0x20) & 0xFB);
		wb_n = 4800; wait_bits();
	}
	port_sys = t & 0xFB;
	screen("LED blinked 3x?", "", "");
	ask(6, "LED blinked? S/N");
}

// ---- stage F ----
#define NEV 120
static void raw_scan(byte *d) {
	byte m, i;
	keyboard_port_matrixColIn2 = 0xFF;
	m = 0x80;
	for (i = 0; i < 8; i++) {
		keyboard_port_matrixRowOut = m;
		d[i << 1] = keyboard_port_matrixColIn2;
		d[(i << 1) + 1] = keyboard_port_matrixColIn;
		keyboard_port_matrixRowOut = 0;
		m >>= 1;
	}
}
static void st_keys(void) {
	byte *ev = (byte *)WINBUF;
	byte cur[16], i, same, n, e;
	n = 0;
	raw_scan(ev);					// baseline = the matrix as it is when the stage starts
	screen("F: press keys", "ALT SHIFT CAPS...", "ENTER ends");
	while (n < NEV) {
		raw_scan(cur);
		same = 1;
		for (i = 0; i < 16; i++) if (cur[i] != ev[(n << 4) + i]) same = 0;
		if (!same) {
			n++;
			for (i = 0; i < 16; i++) ev[(n << 4) + i] = cur[i];
			blank(); put(0, 0, "F: events "); put_hex2(0, 10, n);
			put(1, 0, "last:"); for (i = 0; i < 8; i++) put_hex2(2 + (i >> 2), (i & 3) * 5, cur[i << 1]);
			draw();
		}
		e = kb_event();
		if (e == '\r') break;
	}
	frame_begin(T_KEY, SEL_NONE, 0, 0, (word)(n + 1) << 4);
	for (i = 0; i < 16; i++) tx_crc(ev[i]);
	for (e = 1; e <= n; e++) for (i = 0; i < 16; i++) tx_crc(ev[(e << 4) + i]);
	frame_end();
	serial_byte = 1; line_set();
}

// ---- stage G ----
static void st_chars(void) {
	byte page, r, c;
	word v;
	for (page = 0; page < 4; page++) {
		for (r = 0; r < 4; r++) for (c = 0; c < NCOLS; c++) {
			v = ((word)page * 80) + (r * 20) + c;
			wn[r][c] = (v < 256) ? (byte)v : ' ';
			sh[r][c] = ~wn[r][c];
		}
		draw();
		while (kb_event() != '\r') { wb_n = 96; wait_bits(); }
		kb_last = kb_scan();
	}
	lcd_reset_screen();
}

// ---- stages H-K: port 0x03 selectors ----
static void do_win(byte sel) {
	byte q, i, pass;
	byte *b = (byte *)WINBUF;
	blank(); put(0, 0, "port03 <- "); put_hex2(0, 10, sel); put(1, 0, "reading 2x16 KiB"); draw();
	rec[0] = sel;
	for (pass = 0; pass < 2; pass++) {
		if (pass) crc_begin();
		for (q = 0; q < 4; q++) {
			w_sel = sel; w_src = 0x8000u + ((word)q << 12); w_dst = WINBUF; w_len = 0x1000; win_copy_call();
			if (pass == 0) {
				crc_begin(); crc_run(WINBUF, 0x1000); crc_out(&rec[1 + (q << 2)]);
				if (q == 0) for (i = 0; i < 16; i++) rec[17 + i] = b[i];
				if (q == 1) for (i = 0; i < 16; i++) rec[33 + i] = b[0xBE0 + i];
				if (q == 3) { for (i = 0; i < 16; i++) { rec[49 + i] = b[0xBE0 + i]; rec[65 + i] = b[0xFF0 + i]; } }
			} else crc_run(WINBUF, 0x1000);
		}
	}
	crc_out(&rec[81]);
	frame_begin(T_WIN, sel, 0x8000, 0, 85);
	for (i = 0; i < 85; i++) tx_crc(rec[i]);
	frame_end();
	serial_byte = 1; line_set();
}
static void st_wr(void) {
	byte i, orig;
	byte *b = (byte *)WINBUF;
	screen("K: /WR probe", "1 same-value write", "wait 1 s");
	orig = *(volatile byte *)WR_ADDR;
	w_src = WR_ADDR; w_dst = WINBUF; wr_call();
	frame_begin(T_WRP, SEL_NONE, WR_ADDR, 0, 19);
	tx_crc(orig);
	for (i = 0; i < 17; i++) tx_crc(b[i]);
	tx_crc(*(volatile byte *)WR_ADDR);
	frame_end();
	serial_byte = 1; line_set();
}
static byte cart_ok(void) { return *(volatile byte *)0x8000 == 0x55 && *(volatile byte *)0x8001 == 0xAA; }
static void win_list(const byte *l, byte n) {
	byte i;
	for (i = 0; i < n; i++) {
		do_win(l[i]);
		if (!cart_ok()) {
			blank(); put(0, 0, "STOP: cart window"); put(1, 0, "lost after sel"); put_hex2(1, 15, l[i]); put(3, 0, "power off"); draw();
			while (1) { wb_n = 960; wait_bits(); }
		}
	}
}
static byte lst[32];

void main() {
	byte i;
	__asm
		ld	a, i
		ld	(_e_i), a
		push	af
		pop	hl
		ld	a, l
		ld	(_e_f), a
		di
	__endasm;
	preset = 1; serial_byte = 1; wb_n = 96;
	kb_cnt = 0; kb_cand = 0xff; session = 0; seq = 0; crc = 0; cur_stage = 0;
	get_sp();
	sp_ok = (sp_main >= SP_MIN && sp_main <= SP_MAX) ? 1 : 0;
	variant = *(volatile byte *)0x8002;
	apply_preset();
	lcd_reset_screen();
	kb_last = kb_scan();

	if (!sp_ok) {
		blank(); put(0, 0, "STOP: SP out of RAM"); put(1, 0, "SP="); put_hex4(1, 3, sp_main); put(3, 0, "power off"); draw();
		while (1) { wb_n = 960; wait_bits(); }
	}

	// ---- A: no writes (RAM stubs are installed only after the snapshot) ----
	cur_stage = 0;
	if (wait_stage("entry state", "RAM C000-FFFF copy")) { serial_byte = 1; line_set(); wb_n = 2880; wait_bits(); st_entry(); send_stage(0); } else send_stage(1);
	for (i = 0; i < 17; i++) *(volatile byte *)(STUB_WIN + i) = stub_win[i];
	for (i = 0; i < 5; i++) *(volatile byte *)(STUB_RD + i) = stub_rd[i];
	for (i = 0; i < 40; i++) *(volatile byte *)(STUB_WR + i) = ((const byte *)wr_stub)[i];
	for (i = 0; i < 8; i++) *(volatile byte *)(HOOK_ADDR + i) = stub_hook[i];

	cur_stage = 1;
	if (wait_stage("IN ports 00..FF", "no OUT at all")) { st_ports(); send_stage(0); } else send_stage(1);
	cur_stage = 2;
	if (wait_stage("CPU clock bursts", "2 x 1200 bytes")) { st_clock(); send_stage(0); } else send_stage(1);
	cur_stage = 3;
	if (wait_stage("IRQ rate (no HALT)", "do not press keys")) { st_irq(); send_stage(0); } else send_stage(1);
	cur_stage = 4;
	if (wait_stage("LCD + LED questions", "answer S or N")) { st_lcd(); send_stage(0); } else send_stage(1);
	cur_stage = 5;
	if (wait_stage("keyboard matrix log", "press keys, ENTER end")) { st_keys(); send_stage(0); } else send_stage(1);
	cur_stage = 6;
	if (wait_stage("charset 00-FF", "4 screens, photo")) { st_chars(); send_stage(0); } else send_stage(1);

	cur_stage = 7;
	if (wait_stage("port 03 <- 00..07", "internal entries")) {
		lst[0] = CART_RESTORE; for (i = 0; i < 8; i++) lst[1 + i] = i;
		if (!cart_ok()) { blank(); put(0, 0, "STOP: cart not seen"); draw(); while (1) { wb_n = 960; wait_bits(); } }
		win_list(lst, 9); send_stage(0);
	} else send_stage(1);
	cur_stage = 8;
	if (wait_stage("port 03 <- 80..8F", "cartridge pages")) { for (i = 0; i < 16; i++) lst[i] = 0x80 + i; win_list(lst, 16); send_stage(0); } else send_stage(1);
	cur_stage = 9;
	if (wait_stage("port 03 <- 08..1F", "more internal entries")) { for (i = 0; i < 24; i++) lst[i] = 8 + i; win_list(lst, 24); send_stage(0); } else send_stage(1);
	cur_stage = 10;
	if (wait_stage("cart /WR probe", "same-value write")) { st_wr(); send_stage(0); } else send_stage(1);
	cur_stage = 11;
	if (wait_stage("port 03 <- 20 40 90", "A0 C0 (untested)")) { lst[0] = 0x20; lst[1] = 0x40; lst[2] = 0x90; lst[3] = 0xA0; lst[4] = 0xC0; win_list(lst, 5); send_stage(0); } else send_stage(1);

	frame_begin(T_END, SEL_NONE, 0, 0, 3);
	tx_w16(0); tx_crc(sp_ok);
	frame_end();
	serial_byte = 1; line_set();
	port_win2 = CART_RESTORE;
	blank();
	put(0, 0, "HWTEST DONE");
	put(1, 0, "tell Claude: done");
	put(3, 0, "power off now");
	draw();
	while (1) { wb_n = 960; wait_bits(); }
}
