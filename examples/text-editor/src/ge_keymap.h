#ifndef GE_KEYMAP_H
#define GE_KEYMAP_H
/*
 * ge_keymap.h - Spanish keyboard of the Genio 2000: matrix position -> interpretation.
 *
 * SOURCE: the four tables of the original firmware (verified dump, first 32 KiB, SHA256 14bc4b45...14fe):
 *   normal 0x0415, SHIFT 0x03AD, CAPS 0x04E5, CAPS+SHIFT 0x047D (13 bytes per column: 5 of matrix 2 and 8 of matrix 1) and the
 *   special ALT table at 0x054D (16 entries). The firmware reads SHIFT at (col 6, row 6), ALT at (col 1, row 5) and CAPS at (col 1, row 0).
 *   tools/extract_fw_keymap.py regenerates the firmware <-> this table comparison (test tests/test_keymap_vs_firmware.py in the original suite).
 *
 * Layers (do not confuse them):
 *   1. POSITION: scancode = row_in*8 + col_out (matrix 1, port 0x10);  0x40 + row_in*8 + col_out (matrix 2, port 0x11).
 *      col_out = bit written to port 0x10 (0..7), row_in = bit read (0..7 on P10, 0..4 on P11).
 *   2. MODIFIERS: SHIFT, ALT (held), BLOQ.MAYUS (lock), SYM (one-use prefix).
 *   3. INTERPRETATION: ge_interpret() -> (kind, val): GE_K_CHAR + Unicode, GE_K_FUNC + function.
 *   4. Unicode and 5. LCD code: ge_unicode.h.
 * STATUS: what is derived from the firmware is "firmware evidence"; only what docs/hardware/KEYBOARD.md marks as "confirmed" has been seen on the
 * unit. The own extensions (ALT+BLOQ, SHIFT+ALT+vowel, ALT+RETROCESO...) are "to be checked".
 */
#include "ge_types.h"

#define GE_SC(ix, iy)  ((byte)((iy) * 8 + (ix)))
#define GE_SC2(ix, iy) ((byte)(0x40 + (iy) * 8 + (ix)))
#define GE_M2_MAX 0x68			/* 0x40 + 5*8 + 8 */

/* base classes of the keys of matrix 1 (<0x80: lower-case ASCII character / base symbol) */
#define KB_NONE   0
#define KB_CAPS   0x80
#define KB_SHIFT  0x81
#define KB_ALT    0x82
#define KB_NTIL   0x83	/* physical key N~ */
#define KB_UDIA   0x84	/* physical key U" */
#define KB_HELP   0x85	/* AYUDA (icono tabulador) */
#define KB_PAUSA  0x86	/* '^' / PAUSA */
#define KB_BORRAR 0x87	/* REPETIR / BORRAR */
#define KB_LEFT   0x88	/* RETROCESO */
#define KB_RIGHT  0x89	/* AVANCE */
#define KB_ENTER  0x8A	/* INTRO */
#define KB_DEL    0x8B	/* JUGADOR DERECHA / DEL */
#define KB_ANSWER 0x8C	/* RESPUESTA */
#define KB_INS    0x8D	/* JUGADOR IZQUIERDA / INS */

/* indice = fila_in*8 + columna_out */
static GE_CONST byte ge_base[64] = {
	/* ix:   0         1        2    3    4    5    6         7          */
	KB_HELP,  KB_CAPS, '2', '4', '6', '8', '0',      KB_NONE,		/* iy 0 */
	KB_PAUSA, '1',     '3', '5', '7', '9', KB_BORRAR, KB_NONE,		/* iy 1 */
	KB_NONE,  'q',     'e', 't', 'u', 'o', KB_UDIA,  KB_LEFT,		/* iy 2 */
	KB_NONE,  'a',     's', 'f', 'h', 'k', KB_NTIL,  KB_RIGHT,		/* iy 3 */
	KB_NONE,  'z',     'd', 'g', 'j', 'l', ';',      KB_ENTER,		/* iy 4 */
	KB_NONE,  KB_ALT,  'x', 'v', 'n', ',', '\'',     KB_DEL,		/* iy 5 */
	KB_NONE,  ' ',     'c', 'b', 'm', '.', KB_SHIFT, KB_ANSWER,		/* iy 6 */
	KB_NONE,  KB_INS,  'w', 'r', 'y', 'i', 'p',      KB_NONE,		/* iy 7 */
};

#define GE_SC_CAPS  GE_SC(1, 0)
#define GE_SC_ALT   GE_SC(1, 5)
#define GE_SC_SHIFT GE_SC(6, 6)		/* the two physical SHIFT keys: a single intersection according to the firmware (SR duplicates SL) */
#define GE_SC_OFF   GE_SC2(7, 1)	/* 0x4F */
#define GE_SC_ANSWER GE_SC(7, 6)
#define GE_SC_PRINT GE_SC2(6, 2)	/* IMPRIMIR TEXTO (firmware code 0xB1) */

/* SHIFT for symbols (firmware, SHIFT table; red legends on the left of the photograph) */
#define GE_SHIFT_N 14
static GE_CONST byte ge_shift_from[GE_SHIFT_N] = { '1',  '2',  '3', '4', '5', '6', '7', '8', '9', '0', ',', '.', ';', '\'' };
static GE_CONST byte ge_shift_to  [GE_SHIFT_N] = { 0xA1, 0xBF, '#', '$', '%', '/', '&', '*', '(', ')', '?', '!', ':', '"' };	/* 0xA1 = U+00A1, 0xBF = U+00BF */

/* ALT for symbols (firmware, special table; red legends on the right) */
#define GE_ALT_N 8
static GE_CONST byte ge_alt_from[GE_ALT_N] = { '1', '2', '3', '4', '5', '6', '7', '8' };
static GE_CONST byte ge_alt_to  [GE_ALT_N] = { '\\', '@', '-', '_', '+', '[', ']', '=' };

/* SYM (one-use prefix, ALT+BLOQ.MAYUS): red calculator legends that are characters */
#define GE_SYM_N 6
static GE_CONST byte ge_sym_from[GE_SYM_N] = { 'q',    'a',    's', 'd', 'f',    'g' };
static GE_CONST word ge_sym_to  [GE_SYM_N] = { 0x221A, 0x03C0, '+', '-', 0x00D7, 0x00F7 };	/* root, pi, +, -, x, division */

/* functions (GE_K_FUNC interpretation) */
#define GE_F_NONE   0
#define GE_F_LEFT   1
#define GE_F_RIGHT  2
#define GE_F_UP     3
#define GE_F_DOWN   4
#define GE_F_HOME   5
#define GE_F_END    6
#define GE_F_PGUP   7
#define GE_F_PGDN   8
#define GE_F_ENTER  9
#define GE_F_BKSP   10
#define GE_F_DEL    11
#define GE_F_INS    12
#define GE_F_HELP   13
#define GE_F_PAUSE  14
#define GE_F_ANSWER 15
#define GE_F_REPEAT 16
#define GE_F_TAB    17
#define GE_F_CLEAR  18
#define GE_F_EXPORT 19
#define GE_F_SYM    20
#define GE_F_OFF    21	/* informative only: switching off is done by genio_off_poll()/poweroff() */
#define GE_F_COUNT  22

#define GE_K_NONE 0
#define GE_K_CHAR 1
#define GE_K_FUNC 2
#define GE_K_MOD  3

/* modifiers (bits of ge_mods) */
#define GE_MOD_SHIFT 0x01	/* left SHIFT (shared intersection) */
#define GE_MOD_SHIFT_R 0x02	/* right SHIFT: a copy of SL while it has no position of its own */
#define GE_MOD_ALT   0x04
#define GE_MOD_CAPS  0x08
#define GE_MOD_SYM   0x10
#define GE_MOD_INS   0x20	/* 1 = insert, 0 = overwrite (informative in the events) */

static byte ge_kind;
static word ge_val;

static byte ge_is_letter(byte b) { return b >= 'a' && b <= 'z'; }
static byte ge_is_vowel(byte b) { return b == 'a' || b == 'e' || b == 'i' || b == 'o' || b == 'u'; }

/* base class of a scancode (0 for positions without a known key and for matrix 2) */
static byte ge_base_of(byte sc) { return sc < 64 ? ge_base[sc] : KB_NONE; }

static byte ge_is_modifier(byte sc) { byte b = ge_base_of(sc); return b == KB_CAPS || b == KB_SHIFT || b == KB_ALT; }

/* Latin-1 of the accented vowel */
static word ge_accent_of(byte v, byte upper) {
	word u;
	u = v == 'a' ? 0xE1 : v == 'e' ? 0xE9 : v == 'i' ? 0xED : v == 'o' ? 0xF3 : 0xFA;
	return upper ? (word)(u - 0x20) : u;
}

/* Interpretation of a key press. Result in ge_kind / ge_val.
 *   mods: GE_MOD_* at the instant of the press.   sc: scancode (matrix 1: 0..63, matrix 2: 0x40..).
 * Rules (all "to be checked on the unit", except those the firmware already does):
 *   letter:   (SHIFT xor BLOQ) -> upper case; ALT+vowel -> lower-case accent, and with (SHIFT xor BLOQ) -> accented capital (improvement: the
 *             firmware ignores SHIFT with ALT).  ALT + other letters: nothing (they are calculator keys).
 *   N~ and U" : (SHIFT xor BLOQ) -> upper case.   Digits and signs: SHIFT -> left red legend; ALT -> right red legend; BLOQ has no effect.
 *   SYM:      Q A S D F G give root, pi, +, -, x, division (one use).
 */
static void ge_interpret(byte sc, byte mods) {
	byte b, k, up, shift, alt;
	ge_kind = GE_K_NONE; ge_val = 0;
	shift = (mods & GE_MOD_SHIFT) != 0; alt = (mods & GE_MOD_ALT) != 0;
	up = (byte)(shift ^ ((mods & GE_MOD_CAPS) != 0));
	if (sc >= 64) {
		if (sc == GE_SC_PRINT) { ge_kind = GE_K_FUNC; ge_val = GE_F_EXPORT; }
		else if (sc == GE_SC_OFF) { ge_kind = GE_K_FUNC; ge_val = GE_F_OFF; }
		return;
	}
	b = ge_base[sc];
	if (b == KB_NONE) return;
	if (b == KB_CAPS || b == KB_SHIFT || b == KB_ALT) { ge_kind = GE_K_MOD; ge_val = b; return; }
	/* ---- SYM (one use): it has priority over ALT, so it works even if ALT is still held after ALT+BLOQ ---- */
	if ((mods & GE_MOD_SYM) && ge_is_letter(b)) {
		for (k = 0; k < GE_SYM_N; k++) if (ge_sym_from[k] == b) { ge_kind = GE_K_CHAR; ge_val = ge_sym_to[k]; return; }
	}
	/* ---- ALT ---- */
	if (alt) {
		if (ge_is_vowel(b)) { ge_kind = GE_K_CHAR; ge_val = ge_accent_of(b, up); return; }
		if (b == KB_UDIA) { ge_kind = GE_K_FUNC; ge_val = shift ? GE_F_PGUP : GE_F_UP; return; }
		if (b == ';')     { ge_kind = GE_K_FUNC; ge_val = shift ? GE_F_PGDN : GE_F_DOWN; return; }
		if (b == KB_NTIL) { ge_kind = GE_K_FUNC; ge_val = GE_F_CLEAR; return; }
		if (b == KB_LEFT) { ge_kind = GE_K_FUNC; ge_val = GE_F_HOME; return; }
		if (b == KB_RIGHT){ ge_kind = GE_K_FUNC; ge_val = GE_F_END; return; }
		for (k = 0; k < GE_ALT_N; k++) if (ge_alt_from[k] == b) { ge_kind = GE_K_CHAR; ge_val = ge_alt_to[k]; return; }
		/* red calculator legends that are characters and do not clash with an accent: ALT+Q = root, ALT+S = +, ALT+D = -, ALT+F = x, ALT+G = division
		   (A is left for the accent: pi only with the SYM prefix = ALT+BLOQ and then A) */
		for (k = 0; k < GE_SYM_N; k++) if (ge_sym_from[k] == b && b != 'a') { ge_kind = GE_K_CHAR; ge_val = ge_sym_to[k]; return; }
		/* the rest with ALT: no function (other calculator letters, digits 9 and 0, signs) */
		return;
	}
	/* ---- function keys ---- */
	switch (b) {
	case KB_LEFT:   if (shift) { ge_kind = GE_K_CHAR; ge_val = '<'; } else { ge_kind = GE_K_FUNC; ge_val = GE_F_LEFT; } return;
	case KB_RIGHT:  if (shift) { ge_kind = GE_K_CHAR; ge_val = '>'; } else { ge_kind = GE_K_FUNC; ge_val = GE_F_RIGHT; } return;
	case KB_ENTER:  ge_kind = GE_K_FUNC; ge_val = GE_F_ENTER; return;
	case KB_DEL:    ge_kind = GE_K_FUNC; ge_val = GE_F_DEL; return;
	case KB_INS:    ge_kind = GE_K_FUNC; ge_val = GE_F_INS; return;
	case KB_ANSWER: ge_kind = GE_K_FUNC; ge_val = GE_F_ANSWER; return;
	case KB_HELP:   ge_kind = GE_K_FUNC; ge_val = shift ? GE_F_TAB : GE_F_HELP; return;
	case KB_PAUSA:  if (shift) { ge_kind = GE_K_FUNC; ge_val = GE_F_PAUSE; } else { ge_kind = GE_K_CHAR; ge_val = '^'; } return;
	case KB_BORRAR: ge_kind = GE_K_FUNC; ge_val = shift ? GE_F_REPEAT : GE_F_BKSP; return;
	case KB_NTIL:   ge_kind = GE_K_CHAR; ge_val = up ? 0xD1 : 0xF1; return;
	case KB_UDIA:   ge_kind = GE_K_CHAR; ge_val = up ? 0xDC : 0xFC; return;
	}
	/* ---- caracteres ---- */
	if (ge_is_letter(b)) { ge_kind = GE_K_CHAR; ge_val = up ? (word)(b - 0x20) : b; return; }
	ge_kind = GE_K_CHAR; ge_val = b;
	if (shift) for (k = 0; k < GE_SHIFT_N; k++) if (ge_shift_from[k] == b) { ge_val = ge_shift_to[k]; return; }
}

/* ---- short names (<= 7 characters, bytes = LCD codes) for the diagnostic ---- */
#define GE_NAME_LEN 8
/* keys that are not a symbol (base class >= 0x80); 0x9C = N~, 0x9A = U" on the LCD */
static GE_CONST char ge_names_k[14][GE_NAME_LEN] = {
	"BLOQMAY", "SHIFT", "ALT", "\x9C", "\x9A", "AYUDA", "PAUSA^", "BORRAR", "RETROC", "AVANCE", "INTRO", "DEL", "RESPUE", "INS",
};
/* matrix 2 (activity keys): index = col_out*5 + row_in. Names INFERRED from the order of the firmware codes (01..1F,B0..B7 from
 * left to right); only OFF (column 7, row 1) is physically confirmed. */
static GE_CONST char ge_names2[40][GE_NAME_LEN] = {
	"BUSCA",  "RECUERD","PLURAL","VERBOS", "REVOLT.",
	"PAL.MIS","DERIVAD","SINON.","ANTON.", "LET.LOC",
	"NUEVAPA","TRUEQUE","ALFAPUZ","REVOLTI","ACERTIJ",
	"SUMA",   "RESTA",  "MULT.", "DIVISIO","FRAC.DE",
	"FRAC/%", "RATIOS", "ALGEBRA","REPASO", "SIGNO",
	"CIENCIA","CINE",   "HIST/GE","GENERAL","QUE SOY",
	"RELAMPA","BASIC",  "IMPRIMI","CALCULA","CARTUCH",
	"ON",     "OFF",    "NIVEL", "1 JUG.", "2 JUG.",
};

static char ge_namebuf[GE_NAME_LEN];
static const char *ge_name_of(byte sc) {
	byte b;
	if (sc >= 64) { if (sc >= GE_M2_MAX) return "?"; return ge_names2[(sc & 7) * 5 + ((sc - 0x40) >> 3)]; }
	b = ge_base[sc];
	if (b >= 0x80) return ge_names_k[b - 0x80];
	if (b == KB_NONE) return "?";
	if (b == ' ') return "ESPACIO";
	ge_namebuf[0] = b >= 'a' && b <= 'z' ? (char)(b - 0x20) : (char)b; ge_namebuf[1] = 0;
	return ge_namebuf;
}

#endif
