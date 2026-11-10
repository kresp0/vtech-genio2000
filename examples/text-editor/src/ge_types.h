#ifndef GE_TYPES_H
#define GE_TYPES_H
/* Common types and utilities of the editor. On the Z80 (SDCC) byte/word come from vgldk.h; in PC tests they are defined here. */
#ifdef GE_HOSTTEST
	#include <stdint.h>
	#include <string.h>
	typedef uint8_t byte;
	typedef uint16_t word;
	#define GE_CONST const
#else
	#define GE_CONST const
#endif
#endif
