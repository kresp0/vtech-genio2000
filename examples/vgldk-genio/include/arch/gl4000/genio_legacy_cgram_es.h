#ifndef __GENIO_LEGACY_CGRAM_ES_H
#define __GENIO_LEGACY_CGRAM_ES_H
/*
LEGACY initialisation (profile GENIO_ES without GENIO_NATIVE_CGROM): the boot code loads seven Spanish glyphs into CGRAM slots 1..7 and genio_putchar()
translates Latin-1 to them. Kept byte for byte (moved verbatim out of genio.h) so every existing program compiles to the same image.
The native-CGROM profile (genio_native.h) does not use any of this: the same characters exist in the physical CGROM.
*/

// ---------------------------------------------------------------- Spanish characters on the LCD
/*
CGRAM slots 1..7 (slot 0 can not be printed with lcd_putchar(), which treats code 0 as "no character"):
	1 N~  2 n~  3 U"  4 u"  5 (inverted ?)  6 (inverted !)  7 a'
Programs use Latin-1 codes: 0xD1 0xF1 0xDC 0xFC 0xBF 0xA1 0xE1.
Other accented Latin-1 letters degrade to the base letter. Everything else passes unchanged.
No assumption is made about the built-in CGROM; the glyphs are always loaded explicitly.
*/
#define CHAR_ES_NN 0xD1		// N tilde
#define CHAR_ES_nn 0xF1		// n tilde
#define CHAR_ES_UU 0xDC		// U dieresis
#define CHAR_ES_uu 0xFC		// u dieresis
#define CHAR_ES_QUEST 0xBF	// inverted ?
#define CHAR_ES_EXCL 0xA1	// inverted !
#define CHAR_ES_aa 0xE1		// a acute

const byte genio_glyphs[7 * 8] = {
	// 1: N tilde
	0x0D, 0x12, 0x11, 0x19, 0x15, 0x13, 0x11, 0x11,
	// 2: n tilde
	0x0D, 0x12, 0x00, 0x16, 0x19, 0x11, 0x11, 0x11,
	// 3: U dieresis
	0x0A, 0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E,
	// 4: u dieresis
	0x0A, 0x00, 0x11, 0x11, 0x11, 0x13, 0x0D, 0x00,
	// 5: inverted question mark
	0x04, 0x00, 0x04, 0x08, 0x10, 0x11, 0x0E, 0x00,
	// 6: inverted exclamation mark
	0x04, 0x00, 0x04, 0x04, 0x04, 0x04, 0x04, 0x00,
	// 7: a acute
	0x02, 0x04, 0x0E, 0x01, 0x0F, 0x11, 0x0F, 0x00,
};

void genio_lcd_load_glyphs(void) {
	byte i;
	lcd_writeControl(LCD_SETCGRAMADDR | 8);	// start of slot 1
	for (i = 0; i < 7 * 8; i++) lcd_writeData(genio_glyphs[i]);
	lcd_writeControl(LCD_SETDDRAMADDR);	// back to DDRAM
}

byte genio_lcd_translate(byte c) {
	switch (c) {
		case 0xD1: return 1;
		case 0xF1: return 2;
		case 0xDC: return 3;
		case 0xFC: return 4;
		case 0xBF: return 5;
		case 0xA1: return 6;
		case 0xE1: return 7;
		case 0xC1: case 0xC0: return 'A';
		case 0xC9: case 0xC8: return 'E';
		case 0xCD: case 0xCC: return 'I';
		case 0xD3: case 0xD2: return 'O';
		case 0xDA: case 0xD9: return 'U';
		case 0xE9: case 0xE8: return 'e';
		case 0xED: case 0xEC: return 'i';
		case 0xF3: case 0xF2: return 'o';
		case 0xFA: case 0xF9: return 'u';
	}
	return c;
}

void genio_putchar(byte c) {
	lcd_putchar(genio_lcd_translate(c));
}

#endif	// __GENIO_LEGACY_CGRAM_ES_H
