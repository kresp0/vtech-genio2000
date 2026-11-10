/*
 * cgram_accents.h - custom CGRAM glyphs for the capital accented vowels that the CGROM of the Spanish Genio 2000 does NOT have:
 *     A-acute U+00C1   I-acute U+00CD   O-acute U+00D3   U-acute U+00DA
 * (E-acute U+00C9 exists natively as CGROM 0x90 and is NEVER redefined; lower-case accents use their CGROM codes 0xA0 0x82 0xA1 0xA2 0xA3.)
 *
 * These glyphs live in CGRAM. They are NOT part of the CGROM and must never be listed in CGROM_FULL_TABLE.csv as if they were built in.
 *
 * GLYPH RULES (enforced here and by tests/test_accents.py): 5 columns x 8 rows; ONLY rows 0-6 are used, row 7 (the eighth, cursor row)
 * is ALWAYS 00000; bits above bit 4 are never set.  The acute accent occupies rows 0-1 and the letter rows 2-6 (5 rows), the same
 * construction as the native E-acute (photographed and confirmed on the real unit).
 *
 * LOGICAL GLYPH ORDER IS FIXED (ACC_A, ACC_I, ACC_O, ACC_U).  The CGRAM slot of each glyph is a RUNTIME map (accent_slot[]), default
 * slots 0..3, changeable with accents_set_slots() without touching any application code that prints through accents_code().
 *
 * CONFLICTS (audited, see CGROM_CUSTOM_ACCENTS.md): stock VGLDK never writes CGRAM; the GENIO_ES layer (overlay genio.h) loads slots 1..7
 * at every boot (N~ n~ U" u" inverted-? inverted-! a'), and lcd_putchar() cannot print code 0.  So the default slots 0-3 overlap
 * genio.h slots 1-3.  accents_install() therefore NEVER writes a slot that is in the caller's `foreign` mask unless the caller also
 * lists it in `allow` (an explicit, documented decision); otherwise it writes nothing and returns the conflicting slots.
 *
 * LCD access goes through two macros so the file works in the Z80 build and in host tests:
 *     ACCENTS_LCD_CTRL(v)   default lcd_writeControl(v)      ACCENTS_LCD_DATA(v)   default lcd_writeData(v)
 * No global has an initial value (cart_crt0 has no gsinit): call accents_init() first.
 */
#ifndef CGRAM_ACCENTS_H
#define CGRAM_ACCENTS_H

#ifndef ACCENTS_LCD_CTRL
	#define ACCENTS_LCD_CTRL(v) lcd_writeControl(v)
	#define ACCENTS_LCD_DATA(v) lcd_writeData(v)
#endif
#define ACCENTS_SETCGRAMADDR 0x40
#define ACCENTS_SETDDRAMADDR 0x80

#define ACCENT_COUNT   4
#define ACC_A 0
#define ACC_I 1
#define ACC_O 2
#define ACC_U 3
#define ACCENT_DESIGNS 3
#define ACCENT_FOREIGN_GENIO_ES 0xFE		/* slots 1..7 are loaded by the GENIO_ES boot code (overlay genio.h) */

/* return codes */
#define ACC_OK          0
#define ACC_ERR_SLOT    0x80			/* slot >= 8 or two glyphs on the same slot */
#define ACC_ERR_DESIGN  0x81
#define ACC_ERR_NOTINIT 0x82
/* any value 1..0x7F returned by accents_install()/accents_restore() is the MASK of conflicting slots (nothing was written) */

static const unsigned short accent_codepoint[ACCENT_COUNT] = { 0x00C1, 0x00CD, 0x00D3, 0x00DA };

/* The acute accent is ALWAYS exactly 2 pixels (one on row 0, one on row 1): the user rejected the 4-pixel bold accent as too heavy.
 * design 0 (DEFAULT, chosen by the user): columns 4-3, one column right of design 1   design 1: columns 3-2 (the accent of the 'a acute' of genio.h)
 * design 2: columns 2-1 */
static const unsigned char accent_glyphs[ACCENT_DESIGNS][ACCENT_COUNT][8] = {
	{	/* design 0 */
		{ 0x01, 0x02, 0x0E, 0x11, 0x1F, 0x11, 0x11, 0x00 },	/* A-acute */
		{ 0x01, 0x02, 0x0E, 0x04, 0x04, 0x04, 0x0E, 0x00 },	/* I-acute */
		{ 0x01, 0x02, 0x0E, 0x11, 0x11, 0x11, 0x0E, 0x00 },	/* O-acute */
		{ 0x01, 0x02, 0x11, 0x11, 0x11, 0x11, 0x0E, 0x00 },	/* U-acute */
	},
	{	/* design 1 */
		{ 0x02, 0x04, 0x0E, 0x11, 0x1F, 0x11, 0x11, 0x00 },	/* A-acute */
		{ 0x02, 0x04, 0x0E, 0x04, 0x04, 0x04, 0x0E, 0x00 },	/* I-acute */
		{ 0x02, 0x04, 0x0E, 0x11, 0x11, 0x11, 0x0E, 0x00 },	/* O-acute */
		{ 0x02, 0x04, 0x11, 0x11, 0x11, 0x11, 0x0E, 0x00 },	/* U-acute */
	},
	{	/* design 2 */
		{ 0x04, 0x08, 0x0E, 0x11, 0x1F, 0x11, 0x11, 0x00 },	/* A-acute */
		{ 0x04, 0x08, 0x0E, 0x04, 0x04, 0x04, 0x0E, 0x00 },	/* I-acute */
		{ 0x04, 0x08, 0x0E, 0x11, 0x11, 0x11, 0x0E, 0x00 },	/* O-acute */
		{ 0x04, 0x08, 0x11, 0x11, 0x11, 0x11, 0x0E, 0x00 },	/* U-acute */
	},
};
/* ---- runtime state (all set by accents_init) ---- */
static unsigned char accent_slot[ACCENT_COUNT];	/* CGRAM slot (0..7) of each logical glyph */
static unsigned char accent_design;		/* design currently in CGRAM */
static unsigned char accent_state;		/* 0 = not initialised, 1 = initialised, not installed, 2 = installed */
static unsigned char accent_foreign;		/* masks given to the last accents_install(), reused by accents_restore() */
static unsigned char accent_allow;

static void accents_init(void) {
	accent_slot[ACC_A] = 0; accent_slot[ACC_I] = 1; accent_slot[ACC_O] = 2; accent_slot[ACC_U] = 3;
	accent_design = 0; accent_state = 1; accent_foreign = 0; accent_allow = 0;
}

static unsigned char accents_slot_mask(void) {
	unsigned char i, m = 0;
	for (i = 0; i < ACCENT_COUNT; i++) m |= (unsigned char)(1 << accent_slot[i]);
	return m;
}

/* change the slot assignment (does not touch the LCD; call accents_install() afterwards). ACC_OK or ACC_ERR_SLOT. */
static unsigned char accents_set_slots(unsigned char a, unsigned char i, unsigned char o, unsigned char u) {
	unsigned char s[ACCENT_COUNT], k, m = 0;
	s[0] = a; s[1] = i; s[2] = o; s[3] = u;
	for (k = 0; k < ACCENT_COUNT; k++) {
		if (s[k] > 7 || (m & (1 << s[k]))) return ACC_ERR_SLOT;
		m |= (unsigned char)(1 << s[k]);
	}
	for (k = 0; k < ACCENT_COUNT; k++) accent_slot[k] = s[k];
	return ACC_OK;
}

/* slots that would be overwritten although another user owns them: (used & foreign) & ~allow */
static unsigned char accents_conflicts(unsigned char foreign, unsigned char allow) {
	return (unsigned char)(accents_slot_mask() & foreign & (unsigned char)~allow);
}

/* write one glyph into a CGRAM slot. Rows 0-6 from the table, row 7 forced to 0, bits above bit 4 masked. */
static void accents_write_glyph(unsigned char slot, const unsigned char *rows) {
	unsigned char r;
	ACCENTS_LCD_CTRL(ACCENTS_SETCGRAMADDR | (unsigned char)(slot << 3));
	for (r = 0; r < 8; r++) ACCENTS_LCD_DATA(r < 7 ? (unsigned char)(rows[r] & 0x1F) : 0);
}

/* explicit install: writes the four glyphs of `design` into accent_slot[]. Nothing is written if a slot conflicts. */
static unsigned char accents_install(unsigned char design, unsigned char foreign, unsigned char allow) {
	unsigned char k, c;
	if (accent_state == 0) return ACC_ERR_NOTINIT;
	if (design >= ACCENT_DESIGNS) return ACC_ERR_DESIGN;
	c = accents_conflicts(foreign, allow);
	if (c) return c;
	for (k = 0; k < ACCENT_COUNT; k++) accents_write_glyph(accent_slot[k], accent_glyphs[design][k]);
	ACCENTS_LCD_CTRL(ACCENTS_SETDDRAMADDR);		/* back to DDRAM */
	accent_design = design; accent_foreign = foreign; accent_allow = allow; accent_state = 2;
	return ACC_OK;
}

/* explicit restore after the LCD was re-initialised or CGRAM lost: reinstalls the current design with the masks of the last install */
static unsigned char accents_restore(void) {
	if (accent_state != 2) return ACC_ERR_NOTINIT;
	return accents_install(accent_design, accent_foreign, accent_allow);
}

/* LCD byte to print for a logical glyph (a CGRAM code 0..7: print it with lcd_putchar_at(), NOT lcd_putchar(): code 0 is "no character") */
static unsigned char accents_code(unsigned char idx) { return accent_slot[idx]; }

/* Unicode -> logical glyph index, 0xFF if the code point is not one of the four */
static unsigned char accents_glyph_for_codepoint(unsigned short cp) {
	unsigned char k;
	for (k = 0; k < ACCENT_COUNT; k++) if (accent_codepoint[k] == cp) return k;
	return 0xFF;
}

#endif /* CGRAM_ACCENTS_H */
