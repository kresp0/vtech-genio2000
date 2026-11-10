#ifndef __GENIO_NATIVE_H
#define __GENIO_NATIVE_H
/*
NATIVE-CGROM profile glue for the VGLDK gl4000 target (select with -DGENIO_ES -DGENIO_NATIVE_CGROM; see arch/gl4000/system.h).

What it does differently from the legacy GENIO_ES initialisation (genio_legacy_cgram_es.h):
	* NOTHING is written to CGRAM at boot. The characters N~ n~ U" u" inverted-? inverted-! a' and all the others that the legacy code
	  drew as CGRAM glyphs exist in the physical CGROM of the LCD, so text is mapped to their native codes.
	* Output is RAW-SAFE: a translated byte is written to the LCD data port as it is. lcd_putchar() cannot be used for that: it swallows
	  0x00 (the CGRAM slot 0, where A-acute lives by default) and turns 0x08, 0x0A and 0x0D into cursor commands.

Layers (all independent, none of them knows about the others' contents):
	cgrom_profile_vtech_gl4000_v1.h   which glyph the physical CGROM has at each code (generated; verified on one unit, see CGROM_PROFILES.md)
	cgram_accents.h                   CGRAM glyph library (A-acute I-acute O-acute U-acute, default slots 0..3; those slots are the
	                                  library default, NOT a system reservation: accents_install() refuses slots the caller declares foreign)
	genio_hw.h                        GL4000 hardware (OFF key, poweroff)
	keyboard_es.h                     keyboard distribution
	this file                         glue: Latin-1 / UTF-8 text -> LCD bytes -> LCD

TEXT ENCODINGS: genio_native_putchar() takes ONE Latin-1 byte; genio_native_puts()/genio_native_putn() take UTF-8 (1- and 2-byte sequences, i.e. U+0000-U+07FF;
only the Latin-1 range has glyphs here, anything else prints '?').  Characters without glyph print '?'.
VGLDK's printf()/stdout goes through genio_native_putchar(), i.e. ONE Latin-1 byte per character: UTF-8 string literals must be printed with genio_native_puts(), not printf().
A-acute I-acute O-acute U-acute are printed from CGRAM only after genio_native_install_accents() succeeded; before that they print '?'.
Bytes that are LCD codes (CGRAM 0x00-0x07...) are never part of a C string (0x00 would end it): use genio_lcd_putraw(), or genio_native_puts()
with the letters.
No global has an initial value (cart_crt0 has no gsinit): genio_native_init() runs from vgldk_init().
*/
#include "cgrom_profile_vtech_gl4000_v1.h"
#include "cgram_accents.h"

#define GENIO_NATIVE_NONE 0xFFFFu		// no glyph (neither CGROM nor an installed CGRAM glyph)
#define GENIO_NATIVE_ACCENT_DESIGN 0		// accent design 0 = 01 02 (2 px), chosen by inspecting the real LCD

void genio_native_init(void) {
	accents_init();			// state only: no LCD access, CGRAM untouched
}

// CGRAM glyphs of the accent library. foreign = slots another user of this CGRAM owns, allow = those the caller explicitly lets us overwrite.
// Returns ACC_OK, or the mask of conflicting slots (nothing written).
byte genio_native_install_accents(byte foreign, byte allow) {
	return accents_install(GENIO_NATIVE_ACCENT_DESIGN, foreign, allow);
}

byte genio_native_restore_accents(void) {
	return accents_restore();		// after lcd_init() or any loss of CGRAM; same masks as the install
}

// Writes ONE byte to the LCD data port at the text cursor and advances it. c is never interpreted (0x00-0x1F are LCD codes here).
// Cursor wrap, scrolling and the screen buffer behave exactly like lcd_putchar().
void genio_lcd_putraw(byte c) {
	byte o;

	if (lcd_text_col >= LCD_COLS) {
		lcd_text_col = 0;
		lcd_text_row++;
	}
	if (lcd_text_row >= LCD_ROWS) {
		#ifndef LCD_MINIMAL
		if (lcd_scroll_cb != 0)
			(*lcd_scroll_cb)();
		else
			while (lcd_text_row >= LCD_ROWS) {
				lcd_text_row--;
				lcd_scroll();
			}
		#else
			lcd_text_row = 0;
		#endif
	}
	o = lcd_text_col + (lcd_text_row * LCD_COLS);
	lcd_writeControl(LCD_SETDDRAMADDR | lcd_map[o]);
	lcd_writeData(c);
	lcd_text_col++;
	#ifndef LCD_MINIMAL
	lcd_buffer[o] = c;
	lcd_set_cursor();
	#endif
}

// LCD code of a Latin-1 character, or GENIO_NATIVE_NONE.
word genio_native_encode(byte l1) {
	byte g;
	if (l1 >= 0x20 && l1 <= 0x7E) return l1;
	if (l1 == 0xA0) return 0x20;			// no-break space
	if (l1 >= 0xA0) {
		word v = cgrom_latin1_hi[l1 - 0xA0];
		if (v != CGROM_NONE) return v;		// physical CGROM
		g = accents_glyph_for_codepoint(l1);	// capital accents: CGRAM, only while installed
		if (g != 0xFF && accent_state == 2) return accents_code(g);
	}
	return GENIO_NATIVE_NONE;
}

// One Latin-1 character. \r \n and backspace move the cursor like lcd_putchar(); other control bytes are ignored (they are not text).
void genio_native_putchar(byte c) {
	word e;
	if (c == '\r' || c == '\n' || c == 8) { lcd_putchar(c); return; }
	if (c < 0x20 || c == 0x7F) return;
	e = genio_native_encode(c);
	genio_lcd_putraw(e == GENIO_NATIVE_NONE ? '?' : (byte)e);
}

// UTF-8 text of n bytes (the length is explicit so the text may be built at run time)
void genio_native_putn(const char *s, word n) {
	byte b, b2;
	word cp;
	while (n > 0) {
		b = (byte)*s++; n--;
		if (b < 0x80) { genio_native_putchar(b); continue; }
		if ((b & 0xE0) == 0xC0 && n > 0 && (((byte)*s) & 0xC0) == 0x80) {
			b2 = (byte)*s++; n--;
			cp = ((word)(b & 0x1F) << 6) | (b2 & 0x3F);
			if (cp < 0x100) genio_native_putchar((byte)cp); else genio_lcd_putraw('?');
		} else genio_lcd_putraw('?');
	}
}

// zero-terminated UTF-8 string
void genio_native_puts(const char *s) {
	word n = 0;
	while (s[n]) n++;
	genio_native_putn(s, n);
}

#endif	// __GENIO_NATIVE_H
