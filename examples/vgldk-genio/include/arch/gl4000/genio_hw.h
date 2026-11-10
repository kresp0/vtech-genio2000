#ifndef __GENIO_HW_H
#define __GENIO_HW_H
/*
Genio 2000 (Spanish Genius Leader 4000 Quadro) HARDWARE layer for the VGLDK "gl4000" target (power-off and OFF key). Moved verbatim out of genio.h; no language, CGROM or CGRAM content here.
Only compiled in when GENIO_ES is defined (see arch/gl4000/system.h); stock gl4000 is untouched otherwise.

Contents:
	* poweroff()            - the power-off sequence that was verified on real hardware (ROM poweroff_offkey_gl2000)
	* genio_off_*()         - OFF key detection (matrix port 0x10 column mask 0x80, port 0x11 bit 1, active low),
	                          with boot guard and hold-time confirmation (same scan and same hold as that ROM)
	* genio_putchar()       - LCD output with Latin-1 -> CGRAM translation for the Spanish characters
	* genio_lcd_load_glyphs - loads the Spanish glyphs into the HD44780 CGRAM

Three levels are kept apart (see reports/TECLADO_ES.md):
	1. physical key position in the matrix (scancode = row_in_bit * 8 + column_out_bit)
	2. logical key code returned by keyboard_inkey()
	3. what the program does with it
*/

// ---------------------------------------------------------------- ports (same names as stock keyboard.h)
#define KEYBOARD_PORT_ROW_OUT 0x10
#define KEYBOARD_PORT_COL_IN 0x10
#define KEYBOARD_PORT_COL_IN2 0x11
__sfr __at KEYBOARD_PORT_ROW_OUT keyboard_port_matrix_col_out;
__sfr __at KEYBOARD_PORT_COL_IN keyboard_port_matrix1_row_in;
__sfr __at KEYBOARD_PORT_COL_IN2 keyboard_port_matrix2_row_in;

#define KEY_OFF 0x0F	// logical code of the OFF event (only delivered when GENIO_OFF_EVENT_ONLY is defined)

// OFF key: matrix 2 (port 0x11), column mask 0x80 on port 0x10, bit 1 of port 0x11, active low.
// (experimentally: "row 7, column 1, index 0x79" in the old gl2000 driver's row*8+col notation)
#define GENIO_OFF_COLMASK 0x80
#define GENIO_OFF_ROWBIT 0x02

// Number of consecutive scans OFF must stay pressed before powering off.
// 0xFFFF == the value of the verified power-off ROM (BC=0xFFFF scan loop). Override with -DGENIO_OFF_HOLD=<n>.
#ifndef GENIO_OFF_HOLD
	#define GENIO_OFF_HOLD 0xFFFF
#endif


// ---------------------------------------------------------------- power off
// Electrical power-off, byte-identical to the sequence of the verified ROM:  F3 3E 01 D3 12 76 18 FD
//	DI ; LD A,1 ; OUT (0x12),A ; HALT ; JR $
// The mains-latch is released by the OUT; HALT only parks the CPU until the supply drops.
// ON restarts the machine from reset. NEVER call this during start-up.
void poweroff(void) __naked {
	__asm
		di
		ld	a, #0x01
		out	(0x12), a
	00001$:
		halt
		jr	00001$
	__endasm;
}


// ---------------------------------------------------------------- OFF key
byte genio_off_armed;	// 0 until OFF was seen released at least once (no spurious power-off at boot)

// OFF scan, instruction-for-instruction the routine of the verified power-off ROM (poweroff_offkey, 0x805D):
//	LD A,0x80 ; OUT (0x10),A ; NOP ; IN A,(0x11) ; AND 2 ; PUSH AF ; XOR A ; OUT (0x10),A ; POP AF ; RET
// Result in the Z flag: Z = OFF pressed (bit 1 of port 0x11 low), NZ = released. Not callable from C.
void genio_off_scan(void) __naked {
	__asm
		ld	a, #0x80
		out	(0x10), a
		nop
		in	a, (0x11)
		and	a, #0x02
		push	af
		xor	a, a
		out	(0x10), a
		pop	af
		ret
	__endasm;
}

// returns 1 while the OFF key is physically pressed (8-bit results are returned in A: SDCC __sdcccall(1))
byte genio_off_raw(void) __naked {
	__asm
		call	_genio_off_scan
		ld	a, #0
		ret	nz
		inc	a
		ret
	__endasm;
}

// returns 1 if OFF stays pressed for GENIO_OFF_HOLD consecutive scans, 0 as soon as it is released.
// Same loop as the ROM (BC = 0xFFFF scans, about 1.4 s at the ~6 MHz effective clock deduced from T642).
byte genio_off_confirm(void) __naked {
	__asm
		ld	bc, #GENIO_OFF_HOLD
	00010$:
		call	_genio_off_scan
		jr	nz, 00011$
		dec	bc
		ld	a, b
		or	a, c
		jr	nz, 00010$
		ld	a, #1
		ret
	00011$:
		ld	a, #0
		ret
	__endasm;
}

// returns 1 when a confirmed OFF press happened (the caller decides: poweroff() or deliver KEY_OFF)
byte genio_off_poll(void) {
	if (!genio_off_raw()) {
		genio_off_armed = 1;	// released: from now on a press counts
		return 0;
	}
	if (!genio_off_armed) return 0;	// OFF held since boot: ignore until released once
	if (!genio_off_confirm()) return 0;	// bounce / short tap
	genio_off_armed = 0;
	return 1;
}

#endif	// __GENIO_HW_H
