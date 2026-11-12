/*
	Host build of the calculator's math and evaluator (dec.h, fmt.h, eval.h) for tests/test_math.py.
	Reads lines from stdin: an expression (ASCII, {tokens} for the LCD symbols, see tok[]) or a command:
	  !fmt <0-3> <digits>   !ang <0-2>   !base <0-3>   !frac   !dms   (the last two format the previous result)
	Prints one line per input: "R <sign><16 digits> <exp>" plus the display text, or "ERR <code> <position>".
	Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later
*/
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <setjmp.h>
typedef uint8_t byte;
typedef int16_t i16;
typedef uint16_t u16;
typedef uint32_t u32;

static jmp_buf jb;
void err(byte code) { longjmp(jb, code); }
void stack_check(void) {}
void poll_break(void) {}

#include "../tables.h"
#include "../dec.h"
#include "../vm.h"
#include "../fmt.h"
#include "../eval.h"
#include "page2.h"

static void fetch(void *dst, u16 src, u16 n) { memcpy(dst, page2 + src - 0x8000, n); }

static const struct { const char *t; byte c; } tok[] = {
	{"pi", C_PI}, {"sqrt", C_SQRT}, {"x", C_TIMES}, {"/", C_DIV}, {"-1", C_INV}, {"2", C_SQ}, {"3", C_CUBE},
	{"sto", C_STO}, {"int", C_INT}, {"sum", C_SUM}, {"E", C_EXP}, {"xrt", C_XRT}, {0, 0}};

static void show(const char *s) {	// LCD codes back to readable text
	for (; *s; s++) {
		byte c = *s, i;
		for (i = 0; tok[i].t; i++) if (tok[i].c == c) { printf("{%s}", tok[i].t); break; }
		if (!tok[i].t) { if (c == C_DEG) printf("{deg}"); else putchar(c); }
	}
}

int main(void) {
	char line[512], out[64];
	byte text[256];
	num r;
	int code;
	dzero(&ans);
	fetch(vmcode, P2_VM, VMLEN);
	while (fgets(line, sizeof line, stdin)) {
		char *p = line;
		byte *q = text;
		line[strcspn(line, "\r\n")] = 0;
		if (line[0] == '!') {
			int a = 0, b = 0;
			if (sscanf(line, "!fmt %d %d", &a, &b) == 2) { dispfmt = a; dispdig = b; }
			else if (sscanf(line, "!ang %d", &a) == 1) angmode = a;
			else if (sscanf(line, "!base %d", &a) == 1) basemode = a;
			else if (!strcmp(line, "!frac") || !strcmp(line, "!dms")) {
				byte ok = line[1] == 'f' ? fmt_frac(out, &ans) : fmt_dms(out, &ans);
				printf("F %d ", ok); if (ok) show(out); printf("\n");
				continue;
			}
			printf("OK\n");
			continue;
		}
		while (*p) {
			if (*p == '{') {
				byte i;
				char *e = strchr(p, '}');
				*e = 0;
				for (i = 0; tok[i].t && strcmp(tok[i].t, p + 1); i++) ;
				*q++ = tok[i].c;
				p = e + 1;
			} else *q++ = *p++;
		}
		*q = 0;
		errpos = 0;
		code = setjmp(jb);
		if (code) { printf("ERR %d %d\n", code, errpos ? (int)(errpos - text) : -1); continue; }
		evaluate(&r, text);
		dcopy(&ans, &r);
		printf("R %c", r.s ? '-' : '+');
		for (int i = 0; i < ND; i++) putchar('0' + r.d[i]);
		printf(" %d ", r.e);
		if (basemode) fmt_base(out, &r); else fmt_num(out, &r);
		show(out);
		printf("\n");
	}
	return 0;
}
