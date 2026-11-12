/*
	core_z80.h - the decimal arithmetic of dec.h in Z80 assembly (the cartridge build; the host tests use the C
	versions in dec.h, and tests/mame_math.sh runs the same vectors through this code in MAME).
	Pointers come in HL, DE and on the stack (sdcccall 1, the callee drops stack arguments); they are kept in
	pr/pa/pb. Every routine ends in pack, which rounds W into *pr.
	Copyright (c) 2026 Santiago Crespo. GPL-3.0-or-later (built against VGLDK)
*/
static num *pr, *pa, *pb;
static byte pk_n, pk_s, subf, R[ND + 1], D[ND + 1], mt[10];
static i16 pk_e;

void pack(void);
void dadd(num *r, const num *a, const num *b);
void dsub(num *r, const num *a, const num *b);
void dmul(num *r, const num *a, const num *b);
void ddiv(num *r, const num *a, const num *b);
void ddivn(num *r, const num *a, u16 n);
signed char cmpabs(const num *a, const num *b);
byte isint(const num *a);
void dtrunc(num *r, const num *a);
i16 dtoi(const num *a);

static void dpack(num *r, byte n, i16 e, byte s) { pr = r; pk_n = n; pk_e = e; pk_s = s; pack(); }

static void core_z80(void) __naked { __asm
; ---- pack: *pr = sign pk_s, 0.W[0..pk_n-1] * 10^pk_e rounded half up to 16 digits
_pack::
		ld hl, #_W
		ld a, (_pk_n)
		or a, a
		jp z, _zero_r
		ld b, a
		ld de, (_pk_e)
	1$:	ld a, (hl)
		or a, a
		jr nz, 2$
		inc hl
		dec de
		djnz 1$
		jp _zero_r
	2$:	ld a, b
		cp a, #ND + 1
		jr c, 5$
		push hl
		ld bc, #ND
		add hl, bc
		ld a, (hl)
		cp a, #5
		jr c, 4$
		ld b, #ND
	3$:	dec hl
		inc (hl)
		ld a, (hl)
		cp a, #10
		jr c, 4$
		ld (hl), #0
		djnz 3$
		ld (hl), #1
		inc de
	4$:	pop hl
		ld b, #ND
	5$:	bit 7, d
		jr nz, 6$
		push hl
		ld hl, #EMAX
		or a, a
		sbc hl, de
		pop hl
		jp c, _e_over
		jr 7$
	6$:	push hl
		ld hl, #-EMIN
		add hl, de
		bit 7, h
		pop hl
		jp nz, _zero_r
	7$:	push hl
		ld hl, (_pr)
		ld a, (_pk_s)
		ld (hl), a
		inc hl
		ld (hl), e
		inc hl
		ld (hl), d
		inc hl
		ex de, hl
		pop hl
		ld a, #ND
		sub a, b
		ld c, b
		ld b, #0
		ldir
		or a, a
		ret z
		ld b, a
		xor a, a
	8$:	ld (de), a
		inc de
		djnz 8$
		ret

_zero_r::
		ld hl, (_pr)
		ld b, #19
		xor a, a
	1$:	ld (hl), a
		inc hl
		djnz 1$
		ret

; *pr = *hl
_copy_r::
		ld de, (_pr)
		ld bc, #19
		ldir
		ret

_e_over::
		ld a, #E_OVER
		jp _err
_e_math::
		ld a, #E_MATH
		jp _err

; ---- cmpabs(a = HL, b = DE) -> A = -1, 0, 1
_cmpabs::
		ld bc, #3
		add hl, bc
		ex de, hl
		add hl, bc
		ld a, (de)
		or a, a
		jr nz, 1$
		ld a, (hl)
		or a, a
		ret z
		ld a, #0xFF
		ret
	1$:	ld a, (hl)
		or a, a
		ld a, #1
		ret z
		push hl
		push de
		dec hl
		ld b, (hl)
		dec hl
		ld c, (hl)
		ex de, hl
		dec hl
		ld d, (hl)
		dec hl
		ld e, (hl)
		ex de, hl
		or a, a
		sbc hl, bc
		pop de
		pop hl
		jr z, 3$
		ld a, #1
		ret p
		ld a, #0xFF
		ret
	3$:	ld b, #ND
	4$:	ld a, (de)
		cp a, (hl)
		jr nz, 5$
		inc hl
		inc de
		djnz 4$
		xor a, a
		ret
	5$:	ld a, #1
		ret nc
		ld a, #0xFF
		ret

; ---- dadd / dsub (r = HL, a = DE, b on the stack)
_dsub::
		ld a, #1
		jr _dadd_c
_dadd::
		xor a, a
_dadd_c::
		ld (_subf), a
		ld (_pr), hl
		pop bc
		pop hl
		push bc
		push hl
		inc hl
		inc hl
		inc hl
		ld a, (hl)
		pop hl
		or a, a
		jr nz, 1$
		ex de, hl
		jp _copy_r		; b is zero: a
	1$:	push de
		inc de
		inc de
		inc de
		ld a, (de)
		pop de
		or a, a
		jr nz, 2$
		call _copy_r		; a is zero: -+b
		ld a, (_subf)
		or a, a
		ret z
		ld hl, (_pr)
		ld a, (hl)
		xor a, #1
		ld (hl), a
		ret
	2$:	ld a, (_subf)		; sign of b as it is used
		xor a, (hl)
		ld c, a
		ld a, (de)
		ld b, a			; B = sign of a, C = sign of b
		push bc
		push hl
		push de
		ex de, hl
		call _cmpabs
		pop de
		pop hl
		pop bc
		bit 7, a
		jr z, 3$
		ex de, hl		; the larger one first
		ld a, b
		ld b, c
		ld c, a
	3$:	ld (_pa), de
		ld (_pb), hl
		ld a, b
		ld (_pk_s), a
		xor a, c
		ld (_subf), a		; now: 1 = subtract magnitudes
		ld hl, #_W
		ld b, #ND + 3
		xor a, a
	4$:	ld (hl), a
		inc hl
		djnz 4$
		ld hl, (_pa)
		ld bc, #3
		add hl, bc
		ld de, #_W + 1
		ld bc, #ND
		ldir
		ld hl, (_pa)
		inc hl
		ld e, (hl)
		inc hl
		ld d, (hl)
		ld (_pk_e), de
		ld hl, (_pb)
		inc hl
		ld c, (hl)
		inc hl
		ld b, (hl)
		ex de, hl
		or a, a
		sbc hl, bc		; k = a.e - b.e >= 0
		ld a, h
		or a, a
		jr nz, 9$
		ld a, l
		cp a, #ND + 2
		jr nc, 9$
		ld c, a
		ld a, #ND + 2
		sub a, c
		cp a, #ND + 1
		jr c, 5$
		ld a, #ND
	5$:	ld b, a			; digits of b that fit
		ld hl, #_W + 1
		ld e, c
		ld d, #0
		add hl, de
		ld de, (_pb)
		inc de
		inc de
		inc de
		ld a, (_subf)
		or a, a
		jr nz, 7$
	6$:	ld a, (de)
		add a, (hl)
		ld (hl), a
		inc hl
		inc de
		djnz 6$
		jr 8$
	7$:	ld a, (hl)
		ex de, hl
		sub a, (hl)
		ex de, hl
		ld (hl), a
		inc hl
		inc de
		djnz 7$
	8$:	ld hl, #_W + ND + 2	; carries and borrows, right to left
		ld b, #ND + 2
	10$:	ld a, (hl)
		dec hl
		bit 7, a
		jr z, 11$
		add a, #10
		dec (hl)
		jr 12$
	11$:	cp a, #10
		jr c, 13$
		sub a, #10
		inc (hl)
	12$:	inc hl
		ld (hl), a
		dec hl
	13$:	djnz 10$
	9$:	ld hl, (_pk_e)
		inc hl
		ld (_pk_e), hl
		ld a, #ND + 3
		ld (_pk_n), a
		jp _pack

; ---- dmul (r = HL, a = DE, b on the stack): rows from the last digit of a, mt = x * 0..9
_dmul::
		ld (_pr), hl
		ld (_pa), de
		pop bc
		pop hl
		push bc
		ld (_pb), hl
		inc hl
		inc hl
		inc hl
		ld a, (hl)
		or a, a
		jp z, _zero_r
		inc de
		inc de
		inc de
		ld a, (de)
		or a, a
		jp z, _zero_r
		ld hl, (_pa)
		ld de, (_pb)
		ld a, (de)
		xor a, (hl)
		ld (_pk_s), a
		inc hl
		inc de
		ld c, (hl)
		inc hl
		ld b, (hl)
		ex de, hl
		ld e, (hl)
		inc hl
		ld d, (hl)
		ex de, hl
		add hl, bc
		ld (_pk_e), hl
		ld hl, #_W
		ld b, #2 * ND + 1
		xor a, a
	1$:	ld (hl), a
		inc hl
		djnz 1$
		ld b, #ND		; row i = b - 1
	2$:	push bc
		ld hl, (_pa)
		ld de, #2
		add hl, de
		ld e, b
		add hl, de
		ld a, (hl)		; x = a.d[i]
		or a, a
		jr z, 9$
		ld c, a
		ld hl, #_mt
		xor a, a
		ld e, #10
	3$:	ld (hl), a
		inc hl
		add a, c
		dec e
		jr nz, 3$
		ld hl, #_W + ND - 1
		ld e, b
		ld d, #0
		add hl, de		; W + i + ND
		push hl
		ld hl, (_pb)
		ld de, #2 + ND
		add hl, de
		ex de, hl		; DE = &b.d[ND - 1]
		pop hl
		ld b, #ND
		ld c, #0		; carry
	4$:	ld a, (de)
		push hl
		ld hl, #_mt
		add a, l
		ld l, a
		jr nc, 5$
		inc h
	5$:	ld a, (hl)
		pop hl
		add a, (hl)
		add a, c
		ld c, #0
	6$:	cp a, #10
		jr c, 7$
		sub a, #10
		inc c
		jr 6$
	7$:	ld (hl), a
		dec hl
		dec de
		djnz 4$
		ld (hl), c
	9$:	pop bc
		djnz 2$
		ld a, #2 * ND
		ld (_pk_n), a
		jp _pack

; ---- ddiv (r = HL, a = DE, b on the stack): ND + 2 quotient digits by repeated subtraction
_ddiv::
		ld (_pr), hl
		ld (_pa), de
		pop bc
		pop hl
		push bc
		ld (_pb), hl
		inc hl
		inc hl
		inc hl
		ld a, (hl)
		or a, a
		jp z, _e_math
		inc de
		inc de
		inc de
		ld a, (de)
		or a, a
		jp z, _zero_r
		ld hl, (_pa)
		ld de, (_pb)
		ld a, (de)
		xor a, (hl)
		ld (_pk_s), a
		inc hl
		inc de
		ld c, (hl)
		inc hl
		ld b, (hl)		; BC = a.e
		ex de, hl
		ld e, (hl)
		inc hl
		ld d, (hl)		; DE = b.e
		ld h, b
		ld l, c
		or a, a
		sbc hl, de
		inc hl
		ld (_pk_e), hl
		xor a, a
		ld (_R), a
		ld (_D), a
		ld hl, (_pa)
		ld bc, #3
		add hl, bc
		ld de, #_R + 1
		ld bc, #ND
		ldir
		ld hl, (_pb)
		ld bc, #3
		add hl, bc
		ld de, #_D + 1
		ld bc, #ND
		ldir
		ld hl, #_W
		ld b, #ND + 2
	1$:	push bc
		push hl
		ld c, #0
	2$:	ld hl, #_R		; R >= D ?
		ld de, #_D
		ld b, #ND + 1
	3$:	ld a, (de)
		cp a, (hl)
		jr nz, 4$
		inc hl
		inc de
		djnz 3$
		jr 5$
	4$:	jr nc, 7$
	5$:	ld hl, #_R + ND		; R -= D
		ld de, #_D + ND
		ld b, #ND + 1
		or a, a
	6$:	ld a, (hl)
		ex de, hl
		sbc a, (hl)
		ex de, hl
		jr nc, 8$
		add a, #10
	8$:	ld (hl), a
		dec hl
		dec de
		djnz 6$
		inc c
		jr 2$
	7$:	pop hl
		ld (hl), c
		inc hl
		push hl
		ld hl, #_R + 1
		ld de, #_R
		ld bc, #ND
		ldir
		xor a, a
		ld (de), a
		pop hl
		pop bc
		djnz 1$
		ld a, #ND + 2
		ld (_pk_n), a
		jp _pack

; ---- ddivn (r = HL, a = DE, n on the stack, 1..6553)
_ddivn::
		ld (_pr), hl
		ex de, hl
		ld a, (hl)
		ld (_pk_s), a
		inc hl
		ld e, (hl)
		inc hl
		ld d, (hl)
		inc hl
		ld (_pk_e), de
		pop bc
		pop de			; n
		push bc
		push hl
		pop iy			; digits of a
		ld hl, #_W
		ld (_pb), hl
		ld hl, #0		; remainder
		ld b, #ND + 6
	1$:	push bc
		add hl, hl		; hl * 10 + digit
		ld b, h
		ld c, l
		add hl, hl
		add hl, hl
		add hl, bc
		ld a, b
		pop bc
		push bc
		ld a, b
		cp a, #7
		ld a, #0
		jr c, 2$
		ld a, 0 (iy)
		inc iy
	2$:	ld c, a
		ld b, #0
		add hl, bc
		ld c, #0
	3$:	or a, a
		sbc hl, de
		jr c, 4$
		inc c
		jr 3$
	4$:	add hl, de
		push hl
		ld hl, (_pb)
		ld (hl), c
		inc hl
		ld (_pb), hl
		pop hl
		pop bc
		djnz 1$
		ld a, #ND + 6
		ld (_pk_n), a
		jp _pack

; ---- isint(a = HL) -> A = 1 when no digit after the point is set
_isint::
		inc hl
		ld e, (hl)
		inc hl
		ld d, (hl)
		inc hl
		ld b, #ND
	1$:	bit 7, d		; index ND - b >= e ?
		jr nz, 2$
		ld a, d
		or a, a
		jr nz, 3$
		ld a, #ND
		sub a, b
		cp a, e
		jr c, 3$
	2$:	ld a, (hl)
		or a, a
		ld a, #0
		ret nz
	3$:	inc hl
		djnz 1$
		ld a, #1
		ret

; ---- dtrunc(r = HL, a = DE): digits from index e on are cleared (all when e <= 0)
_dtrunc::
		ld (_pr), hl
		ex de, hl
		push hl
		call _copy_r
		pop hl
		inc hl
		ld e, (hl)
		inc hl
		ld d, (hl)
		bit 7, d
		jp nz, _zero_r
		ld a, d
		or a, e
		jp z, _zero_r
		ld a, d
		or a, a
		ret nz
		ld a, e
		cp a, #ND
		ret nc
		ld hl, (_pr)
		ld bc, #3
		add hl, bc
		ld c, e
		add hl, bc
		ld a, #ND
		sub a, e
		ld b, a
		xor a, a
	1$:	ld (hl), a
		inc hl
		djnz 1$
		ret

; ---- dtoi(a = HL) -> DE; Argument error outside -32767..32767
_dtoi::
		ld a, (hl)
		push af
		inc hl
		ld c, (hl)
		inc hl
		ld b, (hl)
		inc hl
		ex de, hl		; DE -> digits
		ld hl, #0
		bit 7, b
		jr nz, 3$
		ld a, b
		or a, a
		jr nz, 9$
		ld a, c
		cp a, #6
		jr nc, 9$
		or a, a
		jr z, 3$
		ld b, a
	1$:	add hl, hl		; hl = hl * 10 + digit
		jr c, 9$
		push de
		ld d, h
		ld e, l
		add hl, hl
		jr c, 8$
		add hl, hl
		jr c, 8$
		add hl, de
		jr c, 8$
		pop de
		ld a, (de)
		inc de
		add a, l
		ld l, a
		jr nc, 2$
		inc h
		jr z, 9$
	2$:	bit 7, h
		jr nz, 9$
		djnz 1$
	3$:	pop af
		ex de, hl
		or a, a
		ret z
		xor a, a
		sub a, e
		ld e, a
		sbc a, a
		sub a, d
		ld d, a
		ret
	8$:	pop de
	9$:	pop af
		ld a, #E_ARG
		jp _err
__endasm; }
