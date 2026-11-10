#ifndef __KEYBOARD_ES_H
#define __KEYBOARD_ES_H
/*
Spanish keyboard driver for the Genio 2000 on the VGLDK gl4000 target (included by arch/gl4000/system.h when GENIO_ES is defined).
Same public API as the stock gl4000 keyboard.h: keyboard_init/ispressed/update/inkey/getchar, KEY_* codes.

Differences from stock (documented in reports/TECLADO_ES.md):
	* Spanish (QWERTY) letter positions, N~ and U" keys, Spanish shifted symbols.
	* Distinct logical codes: cursor left/right are NOT the letters 'h'/'l' (define GENIO_LEGACY_CURSOR for the old vi codes),
	  ANSWER = ESC (0x1B), PAUSE = BREAK (0x03), REPEAT = BACKSPACE (0x08), DEL = 0x7F.
	* CAPS LOCK works (stock gl4000 stores 'C' in the buffer).
	* Unlabelled / unverified positions return KEY_UNK(n) (0x93..0x9B) instead of letters that collide with typing.
	* No KEYBOARD_LATCH write to port 0x11 (the verified gl2000 diagnostics never wrote it).
	* OFF key: detected through genio_off_poll(); powers off with poweroff() unless GENIO_OFF_EVENT_ONLY is defined,
	  in which case the logical code KEY_OFF is returned once.

Scancode = row_in_bit * 8 + column_out_bit (as in stock gl4000), i.e. the transpose of the old gl2000 "row*8+col" index.
*/

#define KEY_NONE	0

// ---- logical codes
#ifdef GENIO_LEGACY_CURSOR
	#define KEY_CURSOR_LEFT	'h'
	#define KEY_CURSOR_RIGHT	'l'
#else
	#define KEY_CURSOR_LEFT	0x1C
	#define KEY_CURSOR_RIGHT	0x1D
#endif
#define KEY_BACKSPACE	0x08	// physical "REPETIR/BORRAR"
#define KEY_REPEAT	KEY_BACKSPACE
#define KEY_TAB	'\t'	// physical "AYUDA/TAB"
#define KEY_BREAK	0x03	// physical "PAUSA" (distinct from ANSWER)
#define KEY_ESC	0x1B	// physical "RESPUESTA"
#define KEY_ESCAPE	KEY_ESC
#define KEY_ANSWER	KEY_ESC
#define KEY_ENTER	'\r'
#define KEY_DEL	0x7F	// physical "JUGADOR DERECHA / DEL"
#define KEY_PLAYER_RIGHT	KEY_DEL
#define KEY_PLAYER_LEFT	'\r'	// physical "JUGADOR IZQUIERDA / INS" (stock gl4000 behaviour: same as ENTER)
#define KEY_SPACE	' '
#define KEY_CAPS	0x90	// modifiers: internal codes, never delivered to the program
#define KEY_SHIFT	0x91
#define KEY_ALT	0x92
#define KEY_UNK(n)	((byte)(0x93 + (n)))	// unlabelled / unverified matrix positions
#define KEY_ON	KEY_NONE	// not pollable

#define KEY_CHARCODE_NONE 0
#define KEY_CHARCODE_ENTER '\r'

typedef byte keycode_t;
typedef byte scancode_t;

#define KEY_MATRIX1_ROWS 8
#define KEY_MATRIX1_COLS 8

// Scancode (iy*8+ix) -> keycode. iy = bit read on port 0x10 (0..7), ix = column mask bit written to port 0x10 (0..7).
const keycode_t KEY_CODES[KEY_MATRIX1_ROWS * KEY_MATRIX1_COLS] = {
	// ix:  0             1                 2     3     4     5     6                 7
	KEY_TAB,      KEY_CAPS,         '2',  '4',  '6',  '8',  '0',              KEY_UNK(6),            // iy 0
	KEY_BREAK,    '1',              '3',  '5',  '7',  '9',  KEY_BACKSPACE,    KEY_UNK(7),            // iy 1
	KEY_UNK(0),   'q',              'e',  't',  'u',  'o',  0xFC /*u"*/,      KEY_CURSOR_LEFT,       // iy 2
	KEY_UNK(1),   'a',              's',  'f',  'h',  'k',  0xF1 /*n~*/,      KEY_CURSOR_RIGHT,      // iy 3
	KEY_UNK(2),   'z',              'd',  'g',  'j',  'l',  '\'',             KEY_ENTER,             // iy 4
	KEY_UNK(3),   KEY_ALT,          'x',  'v',  'n',  ',',  '-',              KEY_DEL,               // iy 5
	KEY_UNK(4),   KEY_SPACE,        'c',  'b',  'm',  '.',  KEY_SHIFT,        KEY_ESC,               // iy 6
	KEY_UNK(5),   KEY_PLAYER_LEFT,  'w',  'r',  'y',  'i',  'p',              KEY_UNK(8),            // iy 7
};

// Shift translation (Spanish PC-style symbols; the exact legends of the Genio 2000 keys are NOT verified)
#define KEY_MAP_SHIFT_SIZE 17
const keycode_t KEY_MAP_SHIFT_FROM[KEY_MAP_SHIFT_SIZE] = {
	'1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
	',', '.', '-', '\'',
	KEY_CURSOR_LEFT, KEY_CURSOR_RIGHT, KEY_ENTER,
};
const byte KEY_MAP_SHIFT_TO[KEY_MAP_SHIFT_SIZE] = {
	'!', '"', '#', '$', '%', '&', '/', '(', ')', '=',
	';', ':', '_', '?',
	'<', '>', '\n',
};

#define KEYBOARD_PRESSED_MAX 6
#define KEYBOARD_BUFFER_MAX 8
#define KEYBOARD_SCANCODE_INVALID 0xff

#define KEYBOARD_MODIFIER_SHIFT 1
#define KEYBOARD_MODIFIER_ALT 2
#define KEYBOARD_MODIFIER_CAPS 4

byte keyboard_modifiers;	// SHIFT / ALT are held states, CAPS is a lock

byte keyboard_num_pressed;
scancode_t keyboard_pressed[KEYBOARD_PRESSED_MAX];

byte keyboard_buffer_in;
byte keyboard_buffer_out;
char keyboard_buffer[KEYBOARD_BUFFER_MAX];

byte keyboard_find(byte *haystack, byte needle, byte len) {
	while (len-- > 0) {
		if (*haystack++ == needle) return 1;
	}
	return 0;
}

void keyboard_push(byte charcode) {
	byte next = (keyboard_buffer_in + 1) % KEYBOARD_BUFFER_MAX;
	if (next == keyboard_buffer_out) return;	// buffer full: drop
	keyboard_buffer[keyboard_buffer_in] = charcode;
	keyboard_buffer_in = next;
}

void keyboard_init() {
	byte i;
	keyboard_buffer_in = 0;
	keyboard_buffer_out = 0;
	keyboard_num_pressed = 0;
	for (i = 0; i < KEYBOARD_PRESSED_MAX; i++) keyboard_pressed[i] = KEY_NONE;
	keyboard_modifiers = 0x00;
	genio_off_armed = 0;	// OFF is ignored until it was seen released once
}

// Return "true" if a key is pressed on matrix 1
byte keyboard_ispressed() {
	byte b1;
	keyboard_port_matrix_col_out = 0xff;	// all columns at once
	b1 = keyboard_port_matrix1_row_in;
	keyboard_port_matrix_col_out = 0x00;
	return (b1 < 0xff) ? 1 : 0;
}

void keyboard_update() {
	byte ix, iy, m;
	byte b1;
	char i, j;
	scancode_t scancode;
	keycode_t keycode;
	byte charcode;
	byte keyboard_num_pressed_new;
	scancode_t keyboard_pressed_new[KEYBOARD_PRESSED_MAX];

	keyboard_num_pressed_new = 0;

	if (keyboard_ispressed() != 0) {
		m = 0x01;
		for (ix = 0; ix < KEY_MATRIX1_COLS; ix++) {
			keyboard_port_matrix_col_out = m;
			b1 = keyboard_port_matrix1_row_in;
			keyboard_port_matrix_col_out = 0x00;
			if (b1 != 0xff) {
				for (iy = 0; iy < KEY_MATRIX1_ROWS; iy++) {
					if ((b1 & 1) == 0) {
						if (keyboard_num_pressed_new < KEYBOARD_PRESSED_MAX)
							keyboard_pressed_new[keyboard_num_pressed_new++] = iy * KEY_MATRIX1_ROWS + ix;
					}
					b1 >>= 1;
				}
			}
			m = m << 1;
		}
	}

	// Releases
	for (i = 0; i < keyboard_num_pressed; i++) {
		scancode = keyboard_pressed[i];
		if (keyboard_find(&keyboard_pressed_new[0], scancode, keyboard_num_pressed_new) != 0) continue;
		keycode = KEY_CODES[scancode];
		if (keycode == KEY_SHIFT) {
			// both physical SHIFT keys share this matrix position (see TECLADO_ES.md)
			keyboard_modifiers &= ~KEYBOARD_MODIFIER_SHIFT;
		} else if (keycode == KEY_ALT) {
			keyboard_modifiers &= ~KEYBOARD_MODIFIER_ALT;
		}
		keyboard_pressed[i] = keyboard_pressed[--keyboard_num_pressed];
		i--;
	}

	// Presses
	for (i = 0; i < keyboard_num_pressed_new; i++) {
		scancode = keyboard_pressed_new[i];
		if (keyboard_find(&keyboard_pressed[0], scancode, keyboard_num_pressed) != 0) continue;

		keycode = KEY_CODES[scancode];
		if (keycode == KEY_NONE) continue;

		if (keycode == KEY_SHIFT) keyboard_modifiers |= KEYBOARD_MODIFIER_SHIFT;
		else if (keycode == KEY_ALT) keyboard_modifiers |= KEYBOARD_MODIFIER_ALT;
		else if (keycode == KEY_CAPS) keyboard_modifiers ^= KEYBOARD_MODIFIER_CAPS;
		else {
			charcode = keycode;
			if ((keyboard_modifiers & KEYBOARD_MODIFIER_ALT) != 0) {
				// Alt + letter -> control code like Ctrl on a PC (a=1 .. z=26); other keys unchanged
				if (keycode >= 'a' && keycode <= 'z') charcode = 1 + (keycode - 'a');
			} else {
				byte shifted = (keyboard_modifiers & KEYBOARD_MODIFIER_SHIFT) != 0;
				if (keycode >= 'a' && keycode <= 'z') {
					byte caps = (keyboard_modifiers & KEYBOARD_MODIFIER_CAPS) != 0;
					if (shifted != caps) charcode = 'A' + (keycode - 'a');
				} else if (keycode == 0xF1) {
					// n~: Shift or CAPS -> N~
					byte caps = (keyboard_modifiers & KEYBOARD_MODIFIER_CAPS) != 0;
					if (shifted != caps) charcode = 0xD1;
				} else if (keycode == 0xFC) {
					byte caps = (keyboard_modifiers & KEYBOARD_MODIFIER_CAPS) != 0;
					if (shifted != caps) charcode = 0xDC;
				} else if (shifted) {
					for (j = 0; j < KEY_MAP_SHIFT_SIZE; j++) {
						if (keycode == KEY_MAP_SHIFT_FROM[j]) {
							charcode = KEY_MAP_SHIFT_TO[j];
							break;
						}
					}
				}
			}
			keyboard_push(charcode);
		}
		if (keyboard_num_pressed < KEYBOARD_PRESSED_MAX)
			keyboard_pressed[keyboard_num_pressed++] = scancode;
	}
}

byte keyboard_inkey() {
	byte charcode;

	// OFF is polled first and independently of matrix 1
	if (genio_off_poll() != 0) {
		#ifdef GENIO_OFF_EVENT_ONLY
			return KEY_OFF;
		#else
			poweroff();
		#endif
	}

	keyboard_update();

	if (keyboard_buffer_in == keyboard_buffer_out) return KEY_CHARCODE_NONE;
	charcode = keyboard_buffer[keyboard_buffer_out];
	keyboard_buffer_out = (keyboard_buffer_out + 1) % KEYBOARD_BUFFER_MAX;
	return charcode;
}

byte keyboard_getchar() {
	byte charcode;
	while ((charcode = keyboard_inkey()) == KEY_CHARCODE_NONE) {
		// block
	}
	return charcode;
}

#endif	// __KEYBOARD_ES_H
