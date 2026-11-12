/*
	diag_gl2000 - diagnostic cartridge for the VTech Genio 2000 / Genius LEADER 2000-4000 family (Z80, HD44780 4x20)

	A menu of automatic tests (CPU, RAM, ROM, interrupt, ports, idle keyboard) and interactive ones (LCD, keyboard,
	sound, LED). Interrupts stay disabled except inside the interrupt test, which borrows the firmware ISR.
	RAM use: C000-C3FF globals, C400-DAFF scratch (tests are free to destroy it), DB00-DFFF firmware variables and
	stack. The full RAM test copies C000-C3FF and DB00-DFFF into the already tested scratch area, tests them, and
	copies them back.
	cart_crt0.s does not run gsinit: globals are assigned before use.
	Copyright (c) 2026 Santiago Crespo. GPL-3.0-or-later (built against VGLDK)
*/
// Trimmed VGLDK: no keyboard, sound or stdio code; vgl_sound_off would write port 0x12 without masking bit 0
#define __KEYBOARD_H
#define __VGL_SOUND_H
#define keyboard_init()
#define vgl_sound_off()
#define LCD_MINIMAL
#include <vgldk.h>

#define SCRATCH   0xC400
#define SCRATCH_N 0x1700
#define IRQ_SNAPS 18		// the first interval is dropped: an interrupt may be pending before EI

__sfr __at 0x0A lcd_cport;
__sfr __at 0x0B lcd_dport;
__sfr __at 0x10 port_kb1;
__sfr __at 0x11 port_kb2;
__sfr __at 0x12 port_sys;

// ---- globals (all inside C000-C3FF; checked by mkcart.py against the map file)
byte scr[80];
char det[21];
byte res_st[32];
char res_det[32][20];
byte t_buf[64];
byte t_res, t_step;
word t_sp;
word ms_n, tone_n, tone_cnt;
byte p12_led;
word irq_cnt, irq_snap[IRQ_SNAPS];
byte irq_n, irq_iff0, irq_iff1;
byte crc32v[4];
word crc_ptr, crc_len;
void (*alu_fn)(void);
byte alu_mask, alu_left;
word alu_crc, alu_ptr;
word ram_fail_addr;
byte ram_fail_val;
byte page_sel, page_x;
word page_s;
byte kb_m1[8], kb_m2[8];
byte kb_testing;
word boot_pat, boot_zero;
char *wp;

#include "tables.h"

static const byte map4[80] = {
	0,	1,	2,	3,	8,	9,	10,	11,	12,	13,	14,	15,	24,	25,	26,	27,	28,	29,	30,	31,
	64,	65,	66,	67,	72,	73,	74,	75,	76,	77,	78,	79,	88,	89,	90,	91,	92,	93,	94,	95,
	4,	5,	6,	7,	16,	17,	18,	19,	20,	21,	22,	23,	32,	33,	34,	35,	36,	37,	38,	39,
	68,	69,	70,	71,	80,	81,	82,	83,	84,	85,	86,	87,	96,	97,	98,	99,	100,	101,	102,	103
};

// ================================================================ low level: LCD, delays, keyboard, port 0x12
static void lcd_wait(void) __naked { __asm
		ld b, #LCD_N
	1$:	djnz 1$
		ret
__endasm; }

static void lcd_cmd(byte v) { lcd_cport = v; lcd_wait(); }
static void lcd_dat(byte v) { lcd_dport = v; lcd_wait(); }

static void show(void) {
	byte i, a, last = 0xF0;	// never adjacent to map4[0]: the first cell always sets the address
	for (i = 0; i < 80; i++) {
		a = map4[i];
		if (a != (byte)(last + 1)) lcd_cmd(0x80 | a);
		lcd_dat(scr[i]);
		last = a;
	}
}

static void cg(byte slot, const byte *rows) {
	byte i;
	lcd_cmd(0x40 | (slot << 3));
	for (i = 0; i < 8; i++) lcd_dat(rows[i]);
}

// switch the unit off: bit 0 of port 0x12, then halt (the firmware's own sequence; the only HALT in the program)
static void diag_poweroff(void) __naked { __asm
		di
		ld a, #0x01
		out (0x12), a
	1$:	halt
		jr 1$
__endasm; }

static void wait_ms(word n) { ms_n = n; delay_ms(); }

static void p12_out(byte v) { port_sys = v & 0x28; }	// speaker (bit 3) and LED (bit 5) only: bit 0 would power off

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
#define K_INTRO SC(7, 4)
#define K_RESP  SC(7, 6)
#define K_AVAN  SC(7, 3)
#define K_RETRO SC(7, 2)
#define K_SPACE SC(1, 6)
#define K_REP   SC(6, 1)		// REPETIR / BORRAR
#define K_N     SC(4, 5)
#define K_OFF   SC(7, 9)

static byte kb_first(void) {	// lowest scancode pressed in the last scan, or K_NONE
	byte c, r, m;
	for (r = 0; r < 13; r++)
		for (c = 0; c < 8; c++) {
			m = r < 8 ? (kb_m1[c] >> r) : (kb_m2[c] >> (r - 8));
			if (m & 1) return SC(c, r);
		}
	return K_NONE;
}

static byte kb_count(void) {
	byte c, n = 0, m;
	for (c = 0; c < 8; c++) {
		for (m = kb_m1[c]; m; m >>= 1) n += m & 1;
		for (m = kb_m2[c]; m; m >>= 1) n += m & 1;
	}
	return n;
}

static void wait_release(void) {
	byte n = 0;
	while (n < 3) { kb_scan(); n = kb_first() == K_NONE ? n + 1 : 0; wait_ms(5); }
}

// waits for a new key press (two equal scans 10 ms apart); OFF switches the unit off
static byte get_key(void) {
	byte k;
	wait_release();
	for (;;) {
		kb_scan(); k = kb_first();
		if (k != K_NONE) {
			wait_ms(10); kb_scan();
			if (kb_first() == k) {
				if (k == K_OFF && !kb_testing) diag_poweroff();
				return k;
			}
		}
		wait_ms(5);
	}
}

static byte key_digit(byte k) {	// menu index of a digit key (1..9 -> 0..8, 0 -> 9), or K_NONE
	static const byte dig[10] = { SC(6, 0), SC(1, 1), SC(2, 0), SC(2, 1), SC(3, 0), SC(3, 1), SC(4, 0), SC(4, 1), SC(5, 0), SC(5, 1) };
	byte i;
	for (i = 0; i < 10; i++) if (dig[i] == k) return i ? i - 1 : 9;
	return K_NONE;
}

// ================================================================ text output into scr / det
static void at(byte r, byte c) { wp = (char *)scr + r * 20 + c; }
static void w_str(const char *s) { while (*s) *wp++ = *s++; }
static void w_hex(word v, byte n) { while (n--) { byte d = (v >> (n * 4)) & 15; *wp++ = d < 10 ? '0' + d : 'A' - 10 + d; } }
static void w_dec(word v) {
	char b[5]; byte n = 0;
	do { b[n++] = '0' + v % 10; v /= 10; } while (v);
	while (n) *wp++ = b[--n];
}
static void w_hex32(const byte *p) { w_hex(p[3], 2); w_hex(p[2], 2); w_hex(p[1], 2); w_hex(p[0], 2); }
static void cls(void) { byte i; for (i = 0; i < 80; i++) scr[i] = ' '; }
static void line(byte r, const char *s) { at(r, 0); w_str(s); }
static void d_start(void) { byte i; for (i = 0; i < 20; i++) det[i] = ' '; det[20] = 0; wp = det; }

static void screen(const char *a, const char *b, const char *c, const char *d) {
	cls(); line(0, a); line(1, b); line(2, c); line(3, d); show();
}

#define R_NONE  0
#define R_OK    1
#define R_FAIL  2
#define R_INFO  3
#define R_AGAIN 4	// only from ask(): run_test runs the test again
static const char * const st_name[4] = { "--", "OK", "FAIL", "INFO" };

// question after an interactive test: INTRO = yes, N = no, REPETIR = run the test again
static byte ask(const char *title, const char *q) {
	byte k;
	screen(title, q, "INTRO=yes  N=no", "REPETIR=run again");
	for (;;) {
		k = get_key();
		if (k == K_INTRO || k == K_N || k == K_REP) {
			wait_release();
			return k == K_INTRO ? R_OK : k == K_N ? R_FAIL : R_AGAIN;
		}
	}
}

// waits up to ms milliseconds; returns early when a key is pressed (after releasing it)
static byte pause_key(word ms) {
	while (ms >= 10) {
		kb_scan();
		if (kb_first() != K_NONE) { wait_release(); return 1; }
		wait_ms(10); ms -= 10;
	}
	return 0;
}


// ================================================================ CPU tests
static void crc16_a(void) __naked { __asm	; alu_crc = CRC-16/CCITT step with A; keeps BC and HL
		push bc
		ld de, (_alu_crc)
		xor a, d
		ld d, a
		ld b, #8
	1$:	sla e
		rl d
		jr nc, 2$
		ld a, d
		xor a, #0x10
		ld d, a
		ld a, e
		xor a, #0x21
		ld e, a
	2$:	djnz 1$
		ld (_alu_crc), de
		pop bc
		ret
__endasm; }

// runs alu_fn on every vector with A=a F=f B=b C=5A D=b E=a H=a L=b; CRCs A, F & alu_mask, H, L
static void alu_run(void) __naked { __asm
		push ix
		push iy
		ld hl, #0xFFFF
		ld (_alu_crc), hl
		ld hl, #_alu_vec
		ld (_alu_ptr), hl
		ld a, #ALU_NVEC
		ld (_alu_left), a
	1$:	ld hl, (_alu_ptr)
		ld d, (hl)
		inc hl
		ld b, (hl)
		inc hl
		ld e, (hl)
		inc hl
		ld (_alu_ptr), hl
		push de
		pop af
		ld h, d
		ld l, b
		ld e, d
		ld d, b
		ld c, #0x5A
		ld iy, (_alu_fn)
		call 9$
		push hl
		push af
		pop bc
		ld a, (_alu_mask)
		and a, c
		ld c, a
		ld a, b
		call _crc16_a
		ld a, c
		call _crc16_a
		pop hl
		ld a, h
		call _crc16_a
		ld a, l
		call _crc16_a
		ld hl, #_alu_left
		dec (hl)
		jr nz, 1$
		pop iy
		pop ix
		ret
	9$:	jp (iy)
__endasm; }

// stores every register after loading distinct values, swapping the alternate set and passing through the stack
static void cpu_regs_asm(void) __naked { __asm
		push ix
		push iy
		ld a, i
		push af
		ld bc, #0x1234
		ld de, #0x5678
		ld hl, #0x9ABC
		ld a, #0xDE
		exx
		.db 0x08		; ex af, af (alternate)
		ld bc, #0x8765
		ld de, #0x4321
		ld hl, #0xCBA9
		ld a, #0x0F
		ld ix, #0xA55A
		ld iy, #0x5AA5
		exx
		.db 0x08
		ld (_t_buf + 0), bc
		ld (_t_buf + 2), de
		ld (_t_buf + 4), hl
		ld (_t_buf + 6), a
		exx
		.db 0x08
		ld (_t_buf + 8), bc
		ld (_t_buf + 10), de
		ld (_t_buf + 12), hl
		ld (_t_buf + 14), a
		ld (_t_buf + 16), ix
		ld (_t_buf + 18), iy
		ld a, #0x96		; 8-bit moves through every register
		ld b, a
		ld c, b
		ld d, c
		ld e, d
		ld h, e
		ld l, h
		ld a, l
		inc a
		ld (_t_buf + 20), a
		ld a, #0xA5
		ld i, a
		xor a, a
		ld a, i
		ld (_t_buf + 21), a
		ld hl, #0
		add hl, sp
		ld (_t_buf + 22), hl
		ld bc, #0x1122
		ld de, #0x3344
		ld hl, #0x5566
		ld ix, #0x7788
		ld iy, #0x99AA
		push bc
		push de
		push hl
		push ix
		push iy
		pop bc
		pop de
		pop hl
		pop ix
		pop iy
		ld (_t_buf + 24), bc
		ld (_t_buf + 26), de
		ld (_t_buf + 28), hl
		ld (_t_buf + 30), ix
		ld (_t_buf + 32), iy
		ld hl, #0
		add hl, sp
		ld (_t_buf + 34), hl
		pop af
		ld i, a
		pop iy
		pop ix
		ret
__endasm; }

static const byte exp_regs[22] = {
	0x34, 0x12, 0x78, 0x56, 0xBC, 0x9A, 0xDE, 0,	0x65, 0x87, 0x21, 0x43, 0xA9, 0xCB, 0x0F, 0,
	0x5A, 0xA5, 0xA5, 0x5A, 0x97, 0xA5 };
static const byte exp_regs2[10] = { 0xAA, 0x99, 0x88, 0x77, 0x66, 0x55, 0x44, 0x33, 0x22, 0x11 };

static byte cmp_buf(const byte *exp, byte off, byte n, byte skip_mask_7) {	// index+1 of the first difference, 0 if equal
	byte i;
	for (i = 0; i < n; i++) {
		if (skip_mask_7 && (i & 7) == 7) continue;
		if (t_buf[off + i] != exp[i]) return off + i + 1;
	}
	return 0;
}

static byte t_cpu_regs(void) {
	byte e;
	cpu_regs_asm();
	e = cmp_buf(exp_regs, 0, 22, 1);
	if (!e) e = cmp_buf(exp_regs2, 24, 10, 0);
	if (!e && (t_buf[22] != t_buf[34] || t_buf[23] != t_buf[35])) e = 35;
	if (!e) { w_str("16 pairs, I, EXX"); return R_OK; }
	w_str("byte "); w_dec(e - 1); w_str(" = "); w_hex(t_buf[e - 1], 2);
	return R_FAIL;
}

static byte t_cpu_alu(void) {
	byte i;
	for (i = 0; i < ALU_NOPS; i++) {
		alu_fn = alu_ops[i].fn; alu_mask = alu_ops[i].mask;
		alu_run();
		if (alu_crc != alu_ops[i].crc) { w_str(alu_ops[i].name); w_str(" "); w_hex(alu_crc, 4); return R_FAIL; }
	}
	w_dec(ALU_NOPS); w_str(" ops x "); w_dec(ALU_NVEC);
	return R_OK;
}

// jumps, calls, returns on every condition, DJNZ, JP (HL/IX/IY), EX, the stack; t_res = 0 or the failing step
static void cpu_flow_asm(void) __naked { __asm
		push ix
		push iy
		ld hl, #0
		add hl, sp
		ld (_t_sp), hl
		ld a, #1
		ld (_t_step), a
		xor a, a
		jp nz, 90$
		jp c, 90$
		jr nz, 7$
		jr c, 7$
		jr z, 1$
	7$:	jp 90$
	1$:	ld a, #2
		ld (_t_step), a
		scf
		jp nc, 90$
		jr nc, 8$
		jp c, 2$
	8$:	jp 90$
	2$:	ld a, #3
		ld (_t_step), a
		xor a, a
		call nz, 90$
		call c, 90$
		call z, 80$
		cp a, #0x77
		jp nz, 90$
		or a, a
		call c, 90$
		call nc, 81$
		cp a, #0x33
		jp nz, 90$
		ld a, #4
		ld (_t_step), a
		ld a, #0x80
		or a, a
		jp p, 90$
		call m, 82$
		cp a, #0x44
		jp nz, 90$
		ld a, #0x03
		or a, a
		jp po, 90$
		ld a, #0x07
		or a, a
		jp pe, 90$
		ld a, #5
		ld (_t_step), a
		ld b, #200
		ld c, #0
	3$:	inc c
		djnz 3$
		ld a, c
		cp a, #200
		jp nz, 90$
		ld a, #6
		ld (_t_step), a
		ld hl, #4$
		jp (hl)
	4$:	ld ix, #5$
		jp (ix)
		jp 90$
	5$:	ld iy, #6$
		jp (iy)
		jp 90$
	6$:	ld a, #7
		ld (_t_step), a
		ld hl, #0x1234
		ld de, #0x5678
		ex de, hl
		ld a, h
		cp a, #0x56
		jp nz, 90$
		ld a, d
		cp a, #0x12
		jp nz, 90$
		ld bc, #0xBEEF
		push bc
		ld hl, #0xCAFE
		ex (sp), hl
		pop bc
		ld a, b
		cp a, #0xCA
		jp nz, 90$
		ld a, h
		cp a, #0xBE
		jp nz, 90$
		ld a, #8
		ld (_t_step), a
		ld bc, #0x12D7
		push bc
		pop af
		push af
		pop de
		ld a, e
		cp a, #0xD7
		jp nz, 90$
		ld a, d
		cp a, #0x12
		jp nz, 90$
		ld hl, #0
		add hl, sp
		ld de, (_t_sp)
		or a, a
		sbc hl, de
		jp nz, 90$
		xor a, a
		ld (_t_res), a
		pop iy
		pop ix
		ret
	80$:	ld a, #0x77
		ret
	81$:	scf
		ret nc
		ld a, #0x33
		ret c
		ld a, #0
		ret
	82$:	ret p
		ld a, #0x44
		ret m
		ld a, #0
		ret
	90$:	ld sp, (_t_sp)
		ld a, (_t_step)
		ld (_t_res), a
		pop iy
		pop ix
		ret
__endasm; }

static byte t_cpu_flow(void) {
	cpu_flow_asm();
	if (!t_res) { w_str("JP JR CALL RET DJNZ"); return R_OK; }
	w_str("step "); w_dec(t_res);
	return R_FAIL;
}

// LDIR, LDDR, CPIR (found, not found), CPDR, LDI, RLD, RRD on the scratch area; registers and flags to t_buf
static void cpu_block_asm(void) __naked { __asm
		ld hl, #0xC400
	1$:	ld a, l
		xor a, #0x5A
		ld (hl), a
		inc l
		jr nz, 1$
		ld hl, #0xC400
		ld de, #0xC500
		ld bc, #0x0100
		ldir
		push af
		ld (_t_buf + 0), hl
		ld (_t_buf + 2), de
		ld (_t_buf + 4), bc
		ld hl, #0xC5FF
		ld de, #0xC6FF
		ld bc, #0x0100
		lddr
		push af
		ld (_t_buf + 6), hl
		ld (_t_buf + 8), de
		ld (_t_buf + 10), bc
		ld hl, #0xC700
		ld (hl), #0xA7
		ld de, #0xC701
		ld bc, #0x00FF
		ldir
		ld hl, #0xC400
		ld bc, #0x0100
		ld a, #0x6D
		cpir
		push af
		ld (_t_buf + 12), hl
		ld (_t_buf + 14), bc
		ld hl, #0xC700
		ld bc, #0x0010
		xor a, a
		cpir
		push af
		ld (_t_buf + 16), hl
		ld (_t_buf + 18), bc
		ld hl, #0xC4FF
		ld bc, #0x0100
		ld a, #0xDA
		cpdr
		push af
		ld (_t_buf + 20), hl
		ld (_t_buf + 22), bc
		ld hl, #0xC400
		ld de, #0xC800
		ld bc, #0x0001
		ldi
		push af
		ld (_t_buf + 24), hl
		ld (_t_buf + 26), de
		ld (_t_buf + 28), bc
		ld hl, #0xC801
		ld (hl), #0x34
		ld a, #0x12
		rld
		push af
		ld a, (hl)
		ld (_t_buf + 30), a
		ld (hl), #0x34
		ld a, #0x12
		rrd
		push af
		ld a, (hl)
		ld (_t_buf + 31), a
		ld hl, #_t_buf + 48
		ld b, #8
	2$:	pop de
		dec hl
		ld (hl), d
		dec hl
		ld (hl), e
		djnz 2$
		ret
__endasm; }

static const byte exp_block[32] = {
	0x00, 0xC5, 0x00, 0xC6, 0x00, 0x00,	0xFF, 0xC4, 0xFF, 0xC5, 0x00, 0x00,	0x38, 0xC4, 0xC8, 0x00,
	0x10, 0xC7, 0x00, 0x00,	0x7F, 0xC4, 0x80, 0x00,	0x01, 0xC4, 0x01, 0xC8, 0x00, 0x00,	0x42, 0x23 };
// per pushed AF: { flag mask, expected flags, expected A (0xFF = do not check) }
static const byte exp_block_af[8][3] = {
	{ 0x16, 0x00, 0xFF }, { 0x16, 0x00, 0xFF }, { 0xD6, 0x46, 0x6D }, { 0xD6, 0x12, 0x00 },
	{ 0xD6, 0x46, 0xDA }, { 0x16, 0x00, 0xFF }, { 0xD6, 0x00, 0x13 }, { 0xD6, 0x04, 0x14 } };
static const char * const block_name[8] = { "LDIR", "LDDR", "CPIR", "CPIR-", "CPDR", "LDI", "RLD", "RRD" };

static byte t_cpu_block(void) {
	byte i, e;
	volatile byte *p = (volatile byte *)0xC400;
	cpu_block_asm();
	e = cmp_buf(exp_block, 0, 32, 0);
	if (e) { w_str("byte "); w_dec(e - 1); w_str(" = "); w_hex(t_buf[e - 1], 2); return R_FAIL; }
	for (i = 0; i < 8; i++) {
		if ((t_buf[32 + 2 * i] & exp_block_af[i][0]) != exp_block_af[i][1] ||
		    (exp_block_af[i][2] != 0xFF && t_buf[33 + 2 * i] != exp_block_af[i][2])) {
			w_str(block_name[i]); w_str(" AF="); w_hex(t_buf[33 + 2 * i], 2); w_hex(t_buf[32 + 2 * i], 2);
			return R_FAIL;
		}
	}
	i = 0;
	do {
		if (p[0x100 + i] != p[i] || p[0x200 + i] != p[i] || p[0x300 + i] != 0xA7) { w_str("copy "); w_hex(i, 2); return R_FAIL; }
	} while (++i);
	if (p[0x400] != 0x5A) { w_str("LDI data"); return R_FAIL; }
	w_str("LDIR LDDR CPIR RLD");
	return R_OK;
}

// (IX+d) and (IY+d) with extreme displacements, INC/DEC/SET/RES/BIT on them, ADD IX/IY, EX (SP),IX
static void cpu_index_asm(void) __naked { __asm
		push ix
		push iy
		ld ix, #0xC980
		ld iy, #0xCA80
		ld 127 (ix), #0x11
		ld -128 (ix), #0x22
		ld a, #0x33
		ld 5 (iy), a
		ld b, 127 (ix)
		ld c, -128 (ix)
		ld (_t_buf + 0), bc
		inc 127 (ix)
		dec -128 (ix)
		set 7, 5 (iy)
		res 0, 5 (iy)
		bit 7, 5 (iy)
		push af
		bit 6, 5 (iy)
		push af
		ld de, #0x0100
		add ix, de
		ld (_t_buf + 2), ix
		ld a, 5 (ix)
		ld (_t_buf + 4), a
		ld hl, #0x7777
		push hl
		ex (sp), ix
		pop hl
		ld (_t_buf + 5), hl
		ld (_t_buf + 7), ix
		add iy, iy
		push af
		ld (_t_buf + 9), iy
		ld a, (0xC9FF)
		ld (_t_buf + 11), a
		ld a, (0xC900)
		ld (_t_buf + 12), a
		ld hl, #_t_buf + 22
		ld b, #3
	1$:	pop de
		dec hl
		ld (hl), d
		dec hl
		ld (hl), e
		djnz 1$
		pop iy
		pop ix
		ret
__endasm; }

static const byte exp_index[13] = { 0x22, 0x11, 0x80, 0xCA, 0xB2, 0x80, 0xCA, 0x77, 0x77, 0x00, 0x95, 0x12, 0x21 };
static const byte exp_index_f[3][2] = { { 0x52, 0x10 }, { 0x52, 0x50 }, { 0x13, 0x11 } };

static byte t_cpu_index(void) {
	byte e, i;
	cpu_index_asm();
	e = cmp_buf(exp_index, 0, 13, 0);
	if (e) { w_str("byte "); w_dec(e - 1); w_str(" = "); w_hex(t_buf[e - 1], 2); return R_FAIL; }
	for (i = 0; i < 3; i++)
		if ((t_buf[16 + 2 * i] & exp_index_f[i][0]) != exp_index_f[i][1]) { w_str("flags "); w_dec(i); w_str(" = "); w_hex(t_buf[16 + 2 * i], 2); return R_FAIL; }
	w_str("IX IY +127 -128");
	return R_OK;
}

// refresh register R (7-bit counter, bit 7 kept) and interrupt vector register I
static void cpu_ri_asm(void) __naked { __asm
		ld a, r
		ld b, a
		nop
		nop
		ld a, r
		sub a, b
		and a, #0x7F
		ld (_t_buf + 0), a
		ld a, #0x80
		ld r, a
		nop
		ld a, r
		and a, #0x80
		ld (_t_buf + 1), a
		ld a, #0x7F
		ld r, a
		nop
		nop
		ld a, r
		ld (_t_buf + 2), a
		ld a, i
		ld c, a
		ld a, #0x5A
		ld i, a
		xor a, a
		ld a, i
		ld (_t_buf + 3), a
		push af
		ld a, c
		ld i, a
		pop bc
		ld a, c
		ld (_t_buf + 4), a
		ret
__endasm; }

static byte t_cpu_ri(void) {
	cpu_ri_asm();
	if (t_buf[0] != 5 || t_buf[1] != 0x80 || t_buf[2] != 0x03 || t_buf[3] != 0x5A || (t_buf[4] & 0xD6) != 0) {
		w_str("R "); w_hex(t_buf[0], 2); w_hex(t_buf[1], 2); w_hex(t_buf[2], 2); w_str(" I "); w_hex(t_buf[3], 2); w_hex(t_buf[4], 2);
		return R_FAIL;
	}
	w_str("R +5, bit 7, I");
	return R_OK;
}

// ================================================================ RAM tests
// Walking 1 and walking 0 at four addresses. t_res = 0, or 1 with ram_fail_addr, t_step = written, ram_fail_val = read
static const word bus_adr[4] = { 0xC400, 0xCAAA, 0xD555, 0xDAFF };
static void ram_bus_asm(void) __naked { __asm
		ld hl, #_bus_adr
		ld b, #4
	1$:	ld e, (hl)
		inc hl
		ld d, (hl)
		inc hl
		ld c, #0x01
	2$:	ld a, c
		call 5$
		jr nz, 8$
		ld a, c
		cpl
		call 5$
		jr nz, 8$
		sla c
		jr nc, 2$
		djnz 1$
		xor a, a
		ld (_t_res), a
		ret
	5$:	ld (de), a
		ld (_t_step), a
		ld a, (de)
		push hl
		ld hl, #_t_step
		cp a, (hl)
		pop hl
		ret
	8$:	ld (_ram_fail_val), a
		ld (_ram_fail_addr), de
		ld a, #1
		ld (_t_res), a
		ret
__endasm; }

// every scratch byte holds the XOR of its address bytes, then the inverse; same result variables as ram_bus_asm
static void ram_addr_asm(void) __naked { __asm
		ld b, #2
		ld c, #0
	1$:	ld hl, #0xC400
	2$:	ld a, h
		xor a, l
		xor a, c
		ld (hl), a
		inc hl
		ld a, h
		cp a, #0xDB
		jr nz, 2$
		ld hl, #0xC400
	3$:	ld a, h
		xor a, l
		xor a, c
		cp a, (hl)
		jr nz, 8$
		inc hl
		ld a, h
		cp a, #0xDB
		jr nz, 3$
		ld c, #0xFF
		djnz 1$
		xor a, a
		ld (_t_res), a
		ret
	8$:	ld (_t_step), a
		ld a, (hl)
		ld (_ram_fail_val), a
		ld (_ram_fail_addr), hl
		ld a, #1
		ld (_t_res), a
		ret
__endasm; }

static byte ram_report(const char *ok) {
	if (!t_res) { w_str(ok); return R_OK; }
	w_hex(ram_fail_addr, 4); w_str(" w"); w_hex(t_step, 2); w_str(" r"); w_hex(ram_fail_val, 2);
	return R_FAIL;
}
static byte t_ram_bus(void) { ram_bus_asm(); return ram_report("D0-D7 4 addresses"); }
static byte t_ram_addr(void) { ram_addr_asm(); return ram_report("A0-A12 C400-DAFF"); }

// March C- with backgrounds 00/FF, 55/AA, 33/CC, 0F/F0 over HL..HL+BC-1. Z = pass; NZ: HL = address, A = value read
static void march_pat(void) __naked { __asm	; D = background, E = its inverse
		push hl
		push bc
	1$:	ld (hl), d
		inc hl
		dec bc
		ld a, b
		or a, c
		jr nz, 1$
		pop bc
		pop hl
		push hl
		push bc
	2$:	ld a, (hl)
		cp a, d
		jp nz, 90$
		ld (hl), e
		inc hl
		dec bc
		ld a, b
		or a, c
		jr nz, 2$
		pop bc
		pop hl
		push hl
		push bc
	3$:	ld a, (hl)
		cp a, e
		jp nz, 90$
		ld (hl), d
		inc hl
		dec bc
		ld a, b
		or a, c
		jr nz, 3$
		pop bc
		pop hl
		push hl
		push bc
		add hl, bc
		dec hl
	4$:	ld a, (hl)
		cp a, d
		jp nz, 90$
		ld (hl), e
		dec hl
		dec bc
		ld a, b
		or a, c
		jr nz, 4$
		pop bc
		pop hl
		push hl
		push bc
		add hl, bc
		dec hl
	5$:	ld a, (hl)
		cp a, e
		jp nz, 90$
		ld (hl), d
		dec hl
		dec bc
		ld a, b
		or a, c
		jr nz, 5$
		pop bc
		pop hl
		push hl
		push bc
	6$:	ld a, (hl)
		cp a, d
		jp nz, 90$
		inc hl
		dec bc
		ld a, b
		or a, c
		jr nz, 6$
		pop bc
		pop hl
		xor a, a
		ret
	90$:	pop bc
		pop bc
		ret
__endasm; }

static void march_all(void) __naked { __asm
		ld de, #0x00FF
		call 10$
		ret nz
		ld de, #0x55AA
		call 10$
		ret nz
		ld de, #0x33CC
		call 10$
		ret nz
		ld de, #0x0FF0
	10$:	push hl
		push bc
		call _march_pat
		pop bc
		jr nz, 11$
		pop hl
		ret
	11$:	pop de
		ret
__endasm; }

// all 8 KiB: scratch first, then the globals and the firmware/stack area from copies kept in the tested scratch
static void ram_full(void) __naked { __asm
		ld hl, #0xC400
		ld bc, #0x1700
		call _march_all
		jr nz, 8$
		ld hl, #0xDB00
		ld de, #0xC400
		ld bc, #0x0500
		ldir
		ld hl, #0xC000
		ld de, #0xC900
		ld bc, #0x0400
		ldir
		ld (0xCE00), sp
		ld sp, #0xCF00
		ld hl, #0xDB00
		ld bc, #0x0500
		call _march_all
		jr nz, 5$
		ld hl, #0xC000
		ld bc, #0x0400
		call _march_all
	5$:	ld (0xCE02), hl
		ld (0xCE04), a
		ld a, #0
		jr z, 6$
		inc a
	6$:	ld (0xCE05), a
		ld hl, #0xC900
		ld de, #0xC000
		ld bc, #0x0400
		ldir
		ld hl, #0xC400
		ld de, #0xDB00
		ld bc, #0x0500
		ldir
		ld sp, (0xCE00)
		ld a, (0xCE05)
		or a, a
		ld hl, (0xCE02)
		ld a, (0xCE04)
		jr z, 9$
	8$:	ld (_ram_fail_addr), hl
		ld (_ram_fail_val), a
		ld a, #1
		ld (_t_res), a
		ret
	9$:	xor a, a
		ld (_t_res), a
		ret
__endasm; }

static byte t_ram_march(void) {
	ram_full();
	if (t_res) { w_hex(ram_fail_addr, 4); w_str(" read "); w_hex(ram_fail_val, 2); return R_FAIL; }
	w_str("C000-DFFF 4 backgr.");
	return R_OK;
}

static byte t_ram_mirror(void) {	// read-only look at E000-FFFF: on the unit it mirrors the RAM (HW), MAME leaves it unmapped
	byte i = 0, same = 1;
	volatile byte *p = (volatile byte *)0xC400;
	do { p[i] = i ^ 0xC3; } while (++i);
	do { if (p[0x2000 + i] != p[i]) same = 0; } while (++i);
	w_str(same ? "E000 = C000 (mirror)" : "E000 no mirror");
	return R_INFO;
}

static void boot_ram_scan(void) {	// before anything writes the scratch area: what did power-on leave there?
	volatile byte *p = (volatile byte *)SCRATCH;
	word i;
	boot_pat = 0; boot_zero = 0;
	for (i = 0; i < SCRATCH_N / 4; i++, p += 4) {
		if (p[0] == 0x70 && p[1] == 0xC1 && p[2] == 0x07 && p[3] == 0x1C) boot_pat++;
		if (!(p[0] | p[1] | p[2] | p[3])) boot_zero++;
	}
}

static byte t_ram_boot(void) {	// SCRATCH_N / 4 = 1472 words: percent = n * 25 / 368
	w_str("70C1071C "); w_dec(boot_pat * 25 / 368); w_str("% 0:"); w_dec(boot_zero * 25 / 368); w_str("%");
	return R_INFO;
}

// ================================================================ ROM tests
static void crc32_run(void) __naked { __asm	; crc32v = CRC-32 of crc_len bytes at crc_ptr
		push ix
		ld ix, (_crc_ptr)
		ld bc, (_crc_len)
		ld hl, #0xFFFF
		ld (_crc32v), hl
		ld (_crc32v + 2), hl
	1$:	ld a, 0 (ix)
		inc ix
		ld hl, #_crc32v
		xor a, (hl)
		ld e, a
		ld d, #0
		ld hl, #_crc32_t0
		add hl, de
		ld a, (hl)
		ld hl, #_crc32v + 1
		xor a, (hl)
		ld (_crc32v), a
		ld hl, #_crc32_t1
		add hl, de
		ld a, (hl)
		ld hl, #_crc32v + 2
		xor a, (hl)
		ld (_crc32v + 1), a
		ld hl, #_crc32_t2
		add hl, de
		ld a, (hl)
		ld hl, #_crc32v + 3
		xor a, (hl)
		ld (_crc32v + 2), a
		ld hl, #_crc32_t3
		add hl, de
		ld a, (hl)
		ld (_crc32v + 3), a
		dec bc
		ld a, b
		or a, c
		jr nz, 1$
		ld hl, #_crc32v
		ld b, #4
	2$:	ld a, (hl)
		cpl
		ld (hl), a
		inc hl
		djnz 2$
		pop ix
		ret
__endasm; }

static void crc32_of(word p, word n) { crc_ptr = p; crc_len = n; crc32_run(); }
static byte crc_is(const byte *p) { byte i; for (i = 0; i < 4; i++) if (crc32v[i] != p[i]) return 0; return 1; }

static byte t_rom_cart(void) {	// mkcart.py stores the CRC-32 of 8000-BFFB at BFFC
	const byte *h = (const byte *)0x8000;
	crc32_of(0x8000, 0x3FFC);
	if (h[0] != 0x55 || h[1] != 0xAA || h[2] != 0x59 || h[3] != 0x45) { w_str("bad header"); return R_FAIL; }
	w_str("CRC "); w_hex32(crc32v);
	return crc_is((const byte *)0xBFFC) ? R_OK : R_FAIL;
}

// copied to RAM and run there: maps cartridge page A, sums 8000-BFFF (HL = sum, C = xor), maps page 0x80 back
static void page_sum_code(void) __naked { __asm
	_page_sum_rom::
		out (0x03), a
		ld hl, #0
		ld de, #0x8000
		ld c, #0
	1$:	ld a, (de)
		add a, l
		ld l, a
		jr nc, 2$
		inc h
	2$:	ld a, (de)
		xor a, c
		ld c, a
		inc de
		ld a, d
		cp a, #0xC0
		jr nz, 1$
		ld a, #0x80
		out (0x03), a
		ret
	_page_sum_end::
__endasm; }
extern const byte page_sum_rom[], page_sum_end[];

static void page_sum(void) __naked { __asm
		ld a, (_page_sel)
		call 0xC400
		ld (_page_s), hl
		ld a, c
		ld (_page_x), a
		ret
__endasm; }

static byte t_rom_page(void) {	// only pages 0x80 and 0x81 of port 0x03 are known to be safe on the unit
	word s80; byte x80, i;
	for (i = 0; i < (byte)(page_sum_end - page_sum_rom); i++) ((byte *)SCRATCH)[i] = page_sum_rom[i];
	page_sel = 0x80; page_sum(); s80 = page_s; x80 = page_x;
	page_sel = 0x81; page_sum();
	w_str("80:"); w_hex(s80, 4); w_hex(x80, 2); w_str(" 81:"); w_hex(page_s, 4); w_hex(page_x, 2);
	return (page_s == s80 && page_x == x80) ? R_OK : R_FAIL;
}

static byte t_rom_int(void) {	// bank 0 is fixed at 0000 and is the same in both known firmware revisions
	crc32_of(0x0000, 0x4000);
	w_str("bank 0 "); w_hex32(crc32v);
	return crc_is(bank_crc[0]) ? R_OK : R_FAIL;
}

static byte t_rom_win(void) {	// which bank the firmware left at 4000-7FFF (the ISR maps it from the DFF1 shadow)
	byte i;
	crc32_of(0x4000, 0x4000);
	for (i = 0; i < NBANKS; i++) if (crc_is(bank_crc[i])) { w_str("4000: "); w_str(bank_name[i]); return R_INFO; }
	w_str("4000: ? "); w_hex32(crc32v);
	return R_INFO;
}

// ================================================================ system tests
static byte t_keys_idle(void) {	// nobody touches the keyboard: no key may read as pressed
	byte i, k = K_NONE;
	screen("Keys at rest", "Do not touch the", "keyboard...", "");
	for (i = 0; i < 100; i++) { kb_scan(); if (kb_first() == K_NONE) break; wait_ms(30); }
	wait_ms(400);
	for (i = 0; i < 40 && k == K_NONE; i++) { kb_scan(); k = kb_first(); wait_ms(10); }
	d_start();
	if (k == K_NONE) { w_str("94 keys released"); return R_OK; }
	w_str("pressed c"); w_dec(k & 7); w_str(" r"); w_dec(k >> 3);
	return R_FAIL;
}

static void irq_hook(void) __naked { __asm	; called by the firmware ISR through DFF5: snapshot of the loop counter
		push af
		push de
		push hl
		ld a, (_irq_n)
		cp a, #IRQ_SNAPS
		jr nc, 1$
		ld e, a
		ld d, #0
		ld hl, #_irq_snap
		add hl, de
		add hl, de
		ld de, (_irq_cnt)
		ld (hl), e
		inc hl
		ld (hl), d
		inc a
		ld (_irq_n), a
	1$:	pop hl
		pop de
		pop af
		ret
__endasm; }

static byte irq_jitter(void) {	// spread of the intervals between snapshots 1..IRQ_SNAPS-1, in loop passes
	byte i;
	word d, dmin = 0xFFFF, dmax = 0;
	for (i = 1; i + 1 < IRQ_SNAPS; i++) {
		d = irq_snap[i + 1] - irq_snap[i];
		if (d < dmin) dmin = d;
		if (d > dmax) dmax = d;
	}
	return dmax - dmin > 99 ? 99 : dmax - dmin;
}

static unsigned long irq_cycles(word extra) {	// T-states of 16 periods: loop passes plus extra per interrupt
	unsigned long tt = 0;
	word d = irq_snap[IRQ_SNAPS - 1] - irq_snap[1];
	byte i;
	for (i = 0; i < IRQ_LOOP_T; i++) tt += d;
	for (i = 0; i < 16; i++) tt += extra;
	return tt;
}

static word div32(unsigned long num, unsigned long den) {	// small quotients only; avoids the library division
	word q = 0;
	while (num >= den) { num -= den; q++; }
	return q;
}

static byte irq_check(void) {
	if (irq_n < IRQ_SNAPS) { w_str("only "); w_dec(irq_n); w_str(" interrupts"); return 0; }
	if (irq_iff0 || !irq_iff1) { w_str("IFF2 "); w_dec(irq_iff0); w_dec(irq_iff1); return 0; }
	return 1;
}

#define RB(a) (*(volatile byte *)(a))
static byte t_irq(void) {
	// Settings that make the firmware ISR safe (hwtest stage D on the unit, plus the LCD flags): DB00 = D0 skips
	// the keyboard scan and the idle switch-off, DB01 must not be B4 (switch-off path), DCF0-DCF3 = 0 (no dirty
	// LCD rows), DCF7 = 0 (no cursor service), DFF5/6 = our hook.
	static const word saved_at[9] = { 0xDB00, 0xDB01, 0xDCF0, 0xDCF1, 0xDCF2, 0xDCF3, 0xDCF7, 0xDFF5, 0xDFF6 };
	byte sv[9], i, jit;
	word fw, hz10;
	for (i = 0; i < 9; i++) sv[i] = RB(saved_at[i]);
	RB(0xDB00) = 0xD0; RB(0xDB01) = 0xF9;
	for (i = 2; i < 7; i++) RB(saved_at[i]) = 0;
	RB(0xDFF5) = (byte)(word)irq_hook; RB(0xDFF6) = (byte)((word)irq_hook >> 8);
	fw = *(volatile word *)0xDB28;
	irq_n = 0; irq_cnt = 0;
	irq_count();
	fw = *(volatile word *)0xDB28 - fw;
	for (i = 0; i < 9; i++) RB(saved_at[i]) = sv[i];
	if (!irq_check()) return R_FAIL;
	jit = irq_jitter();
	hz10 = div32(CLOCK_HZ * 160UL, irq_cycles(0));	// the firmware ISR's time is not counted: reads high
	*wp++ = '~'; w_dec(hz10 / 10); *wp++ = '.'; w_dec(hz10 % 10); w_str("Hz j"); w_dec(jit); w_str(" fw"); w_dec(fw);
	return (jit <= 3 && fw == IRQ_SNAPS && hz10 >= 400 && hz10 <= 560) ? R_OK : R_FAIL;
}

// vector table C500-C600 (all C6, whatever byte the bus gives) -> JP irq2_isr at C6C6; IM 2 only for irq_count
static void im2_count(void) __naked { __asm
		ld hl, #0xC500
		ld de, #0xC501
		ld bc, #0x0100
		ld (hl), #0xC6
		ldir
		ld a, #0xC3
		ld (0xC6C6), a
		ld hl, #_irq2_isr
		ld (0xC6C7), hl
		ld a, i
		ld (_t_step), a
		ld a, #0xC5
		ld i, a
		im 2
		call _irq_count
		im 1
		ld a, (_t_step)
		ld i, a
		ret
__endasm; }

static void w_dec32(unsigned long v) {
	static const unsigned long p10[6] = { 100000UL, 10000UL, 1000UL, 100UL, 10UL, 1UL };
	byte i, d, started = 0;
	for (i = 0; i < 6; i++) {
		d = 0;
		while (v >= p10[i]) { v -= p10[i]; d++; }
		if (d || started || i == 5) { *wp++ = '0' + d; started = 1; }
	}
}

static byte t_irq_period(void) {	// exact period in T-states: every cycle of the loop and of irq2_isr is counted
	unsigned long p;
	word hz100;
	byte jit;
	irq_n = 0; irq_cnt = 0;
	im2_count();
	if (!irq_check()) return R_FAIL;
	jit = irq_jitter();
	p = irq_cycles(IRQ2_T) >> 4;
	hz100 = div32(CLOCK_HZ * 100UL + (p >> 1), p);	// rounded
	w_dec32(p); w_str("T "); w_dec(hz100 / 100); *wp++ = '.'; w_dec((hz100 / 10) % 10); w_dec(hz100 % 10);
	w_str("Hz j"); w_dec(jit);
	return (jit <= 2 && hz100 >= 4000 && hz100 <= 5600) ? R_OK : R_FAIL;
}

static byte t_ports(void) {	// at rest the unit reads 10=FF 11=5F 12=16 (HW); MAME gives 11=1F
	byte a, b, c;
	port_kb1 = 0;
	a = port_kb1; b = port_kb2; c = port_sys;
	w_str("10="); w_hex(a, 2); w_str(" 11="); w_hex(b, 2); w_str(" 12="); w_hex(c, 2);
	return R_INFO;
}

// ================================================================ LCD tests (the user judges)
static const byte g_full[8] = { 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F };
static const byte g_chk_a[8] = { 0x15, 0x0A, 0x15, 0x0A, 0x15, 0x0A, 0x15, 0x0A };
static const byte g_chk_b[8] = { 0x0A, 0x15, 0x0A, 0x15, 0x0A, 0x15, 0x0A, 0x15 };

static void fill(byte v) { byte i; for (i = 0; i < 80; i++) scr[i] = v; }

static byte t_lcd_full(void) {
	cg(0, g_full); fill(0); show();
	pause_key(3000);
	return ask("LCD dots", "Every dot lit?");
}

static byte t_lcd_check(void) {
	byte i, k;
	for (i = 0; i < 80; i++) scr[i] = i & 1;
	cg(0, g_chk_a); cg(1, g_chk_b); show();
	for (k = 0; k < 8; k++) {
		cg(k & 1, g_chk_a); cg((k & 1) ^ 1, g_chk_b);
		if (pause_key(500)) break;
	}
	return ask("LCD checker", "Even and inverting?");
}

static byte t_lcd_order(void) {
	byte r, c;
	for (r = 0; r < 4; r++) { scr[r * 20] = '1' + r; for (c = 1; c < 20; c++) scr[r * 20 + c] = 'A' + c - 1; }
	show();
	pause_key(4000);
	return ask("LCD order", "Rows 1-4, A to S?");
}

static byte t_lcd_chars(void) {
	byte p, i;
	for (p = 0; p < 3; p++) {
		for (i = 0; i < 80; i++) scr[i] = (p == 2 && i >= 64) ? ' ' : 0x20 + p * 80 + i;
		show();
		get_key();
	}
	return ask("LCD charset", "3 pages 20-FF right?");
}

static byte t_lcd_cgram(void) {	// glyph k = bar k+1 rows high; codes 08-0F must show the same as 00-07
	byte g[8], k, r, n;
	for (k = 0; k < 8; k++) {
		for (r = 0; r < 8; r++) g[r] = r >= 7 - k ? 0x1F : 0;
		cg(k, g);
	}
	fill(0);
	for (k = 0; k < 8; k++) { scr[k] = k; scr[10 + k] = 8 + k; }
	scr[8] = scr[9] = scr[18] = scr[19] = ' ';
	show();
	for (n = 0; n < 24; n++) {
		for (r = 0; r < 8; r++) g[r] = r >= 7 - (n & 7) ? 0x1F : 0;
		cg(0, g);
		if (pause_key(150)) break;
	}
	return ask("LCD CGRAM", "08-0F=00-07, moving?");
}

static byte t_lcd_cursor(void) {
	static const byte mode[3] = { 0x0E, 0x0D, 0x0F };
	byte m, c;
	screen("Cursor:", "", "underline, block", "and both");
	for (m = 0; m < 3; m++)
		for (c = 0; c < 20; c += 4) {
			lcd_cmd(0x80 | map4[20 + c]);
			lcd_cmd(mode[m]);
			wait_ms(400);
		}
	lcd_cmd(0x0C);
	return ask("LCD cursor", "Line, block, both?");
}

// ================================================================ keyboard, sound, LED
static byte t_keyboard(void) {
	byte seen[13], i, n = 0, k, hold = 0, cnt, c, r, m;
	for (i = 0; i < 13; i++) seen[i] = 0;
	kb_testing = 1;
	wait_release();
	for (;;) {
		kb_scan(); k = kb_first(); cnt = kb_count();
		for (c = 0; c < 8; c++)
			for (r = 0; r < 13; r++) {
				m = r < 8 ? kb_m1[c] >> r : kb_m2[c] >> (r - 8);
				if ((m & 1) && !(seen[r] & (1 << c))) { seen[r] |= 1 << c; n++; }
			}
		cls();
		at(0, 0); w_str("KEYBOARD  "); w_dec(n); w_str("/94");
		if (k != K_NONE) {
			for (i = 0; i < NKEYS; i++) if (key_sc[i] == k) { at(1, 0); w_str(key_name[i]); }
			at(2, 0); w_str("col "); w_dec(k & 7); w_str(" row "); w_dec(k >> 3);
			if (cnt > 1) { w_str("  +"); w_dec(cnt - 1); }
		}
		line(3, "Hold RESPUESTA: exit");
		show();
		hold = (k == K_RESP && cnt == 1) ? hold + 1 : 0;
		if (hold > 40) break;
		wait_ms(20);
	}
	kb_testing = 0;
	wait_release();
	d_start();
	w_str("seen "); w_dec(n); w_str("/94");
	return n == NKEYS ? R_OK : R_INFO;
}

static byte t_sound(void) {
	byte i;
	screen("Sound", "5 rising notes", "C4 C5 C6 C7 G7", "");
	p12_led = 0;
	for (i = 0; i < NTONES; i++) {
		tone_n = tone_tab[i][0]; tone_cnt = tone_tab[i][1];
		tone_play();
		wait_ms(150);
	}
	return ask("Sound", "5 rising notes?");
}

static byte t_led(void) {
	byte i;
	screen("LED", "On for 1 s, off,", "then 5 blinks", "");
	p12_out(0x20); wait_ms(1000);
	p12_out(0x00); wait_ms(700);
	for (i = 0; i < 5; i++) { p12_out(0x20); wait_ms(200); p12_out(0x00); wait_ms(300); }
	return ask("LED", "On, then 5 blinks?");
}

// ================================================================ test table and runner
typedef byte (*tfn_t)(void);
typedef struct { const char *name; tfn_t fn; } test_t;
#define NTESTS 28
#define N_AUTO 19
const test_t tests[NTESTS] = {	// not static: tests/drive.lua reads the names through the map file
	{ "CPU registers", t_cpu_regs }, { "CPU ALU", t_cpu_alu }, { "CPU jumps", t_cpu_flow },
	{ "CPU block ops", t_cpu_block }, { "CPU indexed", t_cpu_index }, { "CPU R and I", t_cpu_ri },
	{ "RAM data bus", t_ram_bus }, { "RAM address", t_ram_addr }, { "RAM march 8K", t_ram_march },
	{ "RAM mirror", t_ram_mirror }, { "RAM at boot", t_ram_boot },
	{ "ROM cartridge", t_rom_cart }, { "ROM page 81", t_rom_page }, { "ROM internal", t_rom_int },
	{ "ROM window 1", t_rom_win },
	{ "Keys at rest", t_keys_idle }, { "Interrupt", t_irq }, { "IRQ period", t_irq_period },
	{ "I/O ports", t_ports },
	{ "LCD dots", t_lcd_full }, { "LCD checker", t_lcd_check }, { "LCD order", t_lcd_order },
	{ "LCD charset", t_lcd_chars }, { "LCD CGRAM", t_lcd_cgram }, { "LCD cursor", t_lcd_cursor },
	{ "Keyboard", t_keyboard }, { "Sound", t_sound }, { "LED", t_led },
};
#define T_KEYS_IDLE 15

static byte run_test(byte id) {
	byte i, r;
	if (id < N_AUTO && id != T_KEYS_IDLE) screen("Testing...", tests[id].name, "", "");
	do { d_start(); r = tests[id].fn(); } while (r == R_AGAIN);
	res_st[id] = r;
	for (i = 0; i < 20; i++) res_det[id][i] = det[i];
	return r;
}

static void show_result(byte id) {
	byte i;
	cls(); line(0, tests[id].name); line(1, st_name[res_st[id]]);
	at(2, 0); for (i = 0; i < 20; i++) *wp++ = res_det[id][i];
	line(3, "INTRO: continue");
	show();
	get_key();
}

static void results(void);

static void run_range(byte from, byte to) {	// to is exclusive
	byte id, n[4] = { 0, 0, 0, 0 };
	for (id = from; id < to; id++) n[run_test(id)]++;
	cls();
	line(0, "Done");
	at(1, 0); w_dec(n[R_OK]); w_str(" OK  "); w_dec(n[R_FAIL]); w_str(" FAIL");
	at(2, 0); w_dec(n[R_INFO]); w_str(" INFO");
	line(3, "INTRO: results");
	show();
	if (get_key() == K_INTRO) results();
}

static void burn_in(void) {	// repeats the automatic tests (except the two that need an idle keyboard or boot data)
	word pass = 0, fails = 0;
	byte id, i, last = 0xFF;
	wait_release();
	for (;;) {
		for (id = 0; id < N_AUTO; id++) {
			if (id == T_KEYS_IDLE || id == 10) continue;
			cls(); at(0, 0); w_str("LOOP pass "); w_dec(pass);
			at(1, 0); w_str("failures "); w_dec(fails);
			if (last != 0xFF) { w_str(" "); w_str(tests[last].name); }
			line(2, tests[id].name); line(3, "Hold a key: stop");	// checked only between tests
			show();
			d_start();
			res_st[id] = tests[id].fn();
			for (i = 0; i < 20; i++) res_det[id][i] = det[i];
			if (res_st[id] == R_FAIL) { fails++; last = id; }
			kb_scan();
			if (kb_first() != K_NONE) { wait_release(); results(); return; }
		}
		pass++;
	}
}

// ================================================================ menus
typedef const char *(*label_fn_t)(byte i);

// returns the chosen item or K_NONE for RESPUESTA
static byte menu(const char *title, byte n, label_fn_t label, byte sel, byte numbered) {
	byte k, top, i, r, d;
	for (;;) {
		top = sel == 0 ? 0 : sel - 1;
		if (n >= 3 && top > n - 3) top = n - 3;
		cls(); line(0, title);
		for (r = 0; r < 3 && top + r < n; r++) {
			i = top + r;
			at(r + 1, 0);
			*wp++ = i == sel ? '>' : ' ';
			*wp++ = (numbered && i < 10) ? (i == 9 ? '0' : '1' + i) : ' ';
			*wp++ = ' ';
			w_str(label(i));
		}
		show();
		k = get_key();
		if (k == K_INTRO) return sel;
		if (k == K_RESP) return K_NONE;
		if (k == K_AVAN || k == K_SPACE) sel = sel + 1 < n ? sel + 1 : 0;
		else if (k == K_RETRO) sel = sel ? sel - 1 : n - 1;
		else if (numbered && (d = key_digit(k)) < n) return d;
	}
}

static void results(void) {
	byte sel = 0, k, top, r, i;
	for (;;) {
		top = sel == 0 ? 0 : sel - 1;
		if (top > NTESTS - 3) top = NTESTS - 3;
		cls(); line(0, "RESULTS");
		for (r = 0; r < 3; r++) {
			i = top + r;
			at(r + 1, 0); *wp++ = i == sel ? '>' : ' ';
			w_str(tests[i].name);
			at(r + 1, 15); w_str(st_name[res_st[i]]);
		}
		show();
		k = get_key();
		if (k == K_RESP) return;
		if (k == K_INTRO) show_result(sel);
		else if (k == K_AVAN || k == K_SPACE) sel = sel + 1 < NTESTS ? sel + 1 : 0;
		else if (k == K_RETRO) sel = sel ? sel - 1 : NTESTS - 1;
	}
}

static const byte grp_first[5] = { 0, 6, 11, 15, 19 };
static const byte grp_last[5] = { 6, 11, 15, 19, 25 };
static const char * const grp_name[5] = { "CPU", "RAM", "ROM", "SYSTEM", "LCD SCREEN" };
static byte cur_grp;

static const char *grp_label(byte i) { return i ? tests[grp_first[cur_grp] + i - 1].name : "All"; }

static void group_menu(byte g) {
	byte sel = 0, n;
	cur_grp = g;
	n = grp_last[g] - grp_first[g] + 1;
	for (;;) {
		cur_grp = g;
		sel = menu(grp_name[g], n, grp_label, sel, 1);
		if (sel == K_NONE) return;
		if (sel == 0) run_range(grp_first[g], grp_last[g]);
		else { run_test(grp_first[g] + sel - 1); show_result(grp_first[g] + sel - 1); }
	}
}

#define M_ALL 0
#define M_AUTO 1
#define M_RES 2
#define M_GRP 3		// 3..7 = groups 0..4
#define M_KEYB 8
#define M_SOUND 9
#define M_LED 10
#define M_LOOP 11
#define M_OFF 12
#define N_MAIN 13
static const char * const main_items[N_MAIN] = {
	"All tests", "Automatic tests", "Results", "CPU >", "RAM >", "ROM >", "System >",
	"LCD screen >", "Keyboard", "Sound", "LED", "Burn-in loop", "Power off" };
static const char *main_label(byte i) { return main_items[i]; }

void main() {
	byte i, sel = 0;
	boot_ram_scan();
	kb_testing = 0; p12_led = 0;
	p12_out(0);
	for (i = 0; i < 32; i++) res_st[i] = R_NONE;
	lcd_cmd(0x0C);
	screen("DIAGNOSTICS", "Genio 2000 / GL4000", "v1.1", "INTRO: menu");
	get_key();
	for (;;) {
		sel = menu("DIAGNOSTICS", N_MAIN, main_label, sel, 1);
		if (sel == K_NONE) { sel = 0; continue; }
		if (sel == M_ALL) run_range(0, NTESTS);
		else if (sel == M_AUTO) run_range(0, N_AUTO);
		else if (sel == M_RES) results();
		else if (sel < M_GRP + 5) group_menu(sel - M_GRP);
		else if (sel <= M_LED) { i = 25 + sel - M_KEYB; run_test(i); show_result(i); }
		else if (sel == M_LOOP) burn_in();
		else diag_poweroff();
	}
}
