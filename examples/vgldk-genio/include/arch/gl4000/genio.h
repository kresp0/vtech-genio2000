#ifndef __GENIO_H
#define __GENIO_H
/*
Genio 2000 support layer for the VGLDK "gl4000" target. Only compiled in when GENIO_ES is defined (see arch/gl4000/system.h);
stock gl4000 is untouched otherwise. This file only ties the layers together (they are independent of each other):

	genio_hw.h                 GL4000 hardware: poweroff(), OFF key (verified on the real machine)
	genio_legacy_cgram_es.h    LEGACY Spanish CGRAM glyphs (slots 1..7 loaded at boot) + genio_putchar(); skipped with GENIO_NATIVE_CGROM
	genio_native.h             NATIVE-CGROM profile (GENIO_NATIVE_CGROM): no CGRAM at boot, text through the verified CGROM profile, raw-safe output
	keyboard_es.h              keyboard distribution (separate; included by system.h)
*/
#include "genio_hw.h"
#ifndef GENIO_NATIVE_CGROM
	#include "genio_legacy_cgram_es.h"
#endif

#endif	// __GENIO_H
