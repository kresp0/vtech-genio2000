#ifndef __GENIO_COMPAT_GL2000_H
#define __GENIO_COMPAT_GL2000_H
/*
Compatibility shim so that the diagnostic programs written against the gl2000 target
(keyboard_test, poweroff_probe, serial_test, firmware_dump, lcd_test) build unchanged on gl4000.
They scan the matrix with their own port code and index vgl_key_map[] with the old gl2000 index
idx = column_out_bit * 8 + row_in_bit ("row*8+col" in their notation).
vgl_key_map[] below is a verbatim copy of that gl2000 table (include/arch/gl2000/keyboard.h) so the diagnostics
print exactly what they printed before. It is a legacy label table, NOT the Spanish logical key map.
*/
#ifndef __sfr
#endif
#ifndef GENIO_ES
	// stock gl4000 keyboard.h uses new sfr names; keyboardmin.h uses the old ones
	#define keyboard_port_matrixRowOut keyboard_port_matrix_col_out
	#define keyboard_port_matrixColIn keyboard_port_matrix1_row_in
	#define keyboard_port_matrixColIn2 keyboard_port_matrix2_row_in
#else
	#define keyboard_port_matrixRowOut keyboard_port_matrix_col_out
	#define keyboard_port_matrixColIn keyboard_port_matrix1_row_in
	#define keyboard_port_matrixColIn2 keyboard_port_matrix2_row_in
#endif
#define vgl_sound_off sound_off

const char vgl_key_map[8 * 8] = {
	'\t', 27, 'e', 'f', 'g', 'i', 'j', 'k',
	'c', '1', 'Q', 'A', 'Z', 'a', ' ', '\r',
	'2', '3', 'E', 'S', 'D', 'X', 'C', 'W',
	'4', '5', 'T', 'F', 'G', 'V', 'B', 'R',
	'6', '7', 'U', 'H', 'J', 'N', 'M', 'Y',
	'8', '9', 'O', 'K', 'L', ',', '.', 'I',
	'0', 8, '=', ':', '\'', '/', 's', 'P',
	'x', 'y', 'h', 'l', '\r', 127, 27, 'z',
};
#endif
