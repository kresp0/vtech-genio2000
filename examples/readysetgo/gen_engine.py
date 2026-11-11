"""engine.h: the player loop (256 T-states per iteration, exact count checked here) and fetch_note.

Iteration = [audio A][W1][audio B][W2][note check][tail]. W1 ends with the LCD write (if any), so every LCD write
sits at the same offset of its iteration and consecutive writes are always >= 252 T-states (41 us) apart.
"""
CLOCK = 6131790.0
T_ITER = 256
FS = 2 * CLOCK / T_ITER                     # audio samples per second
UNIT_ITERS = 32                             # one duration unit of the song = 32 iterations
UNIT_S = UNIT_ITERS * T_ITER / CLOCK

AUDIO_T = 68                                # add/ld/rrca x4/and/or (ix+d)/out
W1_T = 60                                   # chosen so that the two samples are exactly 128 T apart
NOTE_T = 24                                 # dec bc / ld a,b / or c / call z (not taken)
W2_T = T_ITER - 2 * AUDIO_T - W1_T - NOTE_T  # W2 + tail
assert AUDIO_T + W1_T == 128 and W2_T == 36

# Frame structure, mirrored by the timing simulation in gen_scenes.py
FRAME_ITERS = 68                            # CMD + 64 CGRAM data + EVCHK + 2 marquee countdown
MQ_ITERS = 25                               # one marquee step: 3 address commands, 20 characters, 2 to advance
OFF_STEP = 17                               # OFF must be seen down in 255 / OFF_STEP consecutive frames (42 ms)
FIRE_ITERS = 7                              # TXTLOAD + TEND1..6 (+ 2 + count per run, + 1 for a jump)
N_SPECIAL = 12                              # unrolled CGRAM data iterations that also scan the keys

# pads: none of them touches A, the main registers, HL', DE' or BC'
PADS = [(4, 'nop'), (7, 'cp a, #0'), (9, 'ld r, a'), (10, 'inc iy'), (12, 'jr .+2'), (13, 'ld (_pad_sink), a')]

def padlist(n):
    best = {0: []}
    for v in range(1, n + 1):
        for t, txt in PADS:
            if v - t in best and v not in best:
                best[v] = best[v - t] + [(txt, t)]
    if n not in best:
        raise SystemExit('cannot pad %d T-states' % n)
    return best[n]

def audio(off):
    return [('add hl, de', 11), ('ld a, h', 4), ('rrca', 4), ('rrca', 4), ('rrca', 4), ('rrca', 4),
            ('and a, #0x08', 7), ('or a, %d (ix)' % off, 19), ('out (0x12), a', 11)]

class Asm:
    def __init__(s):
        s.lines = []
        s.t = 0
    def i(s, text, t):
        s.lines.append('\t' + text)
        s.t += t
    def raw(s, text):
        s.lines.append(text)
    def block(s, ops):
        for txt, t in ops:
            s.i(txt, t)

def ops_t(ops):
    return sum(t for _, t in ops)

def iteration(a, w1=(), out=None, w1alt=True, w2=(), w2alt=True, tail=()):
    """w1: ops before the LCD write, out: the write instruction (or None), w2: free work, tail: branch at the end."""
    start = a.t
    a.block(audio(0))
    w1 = list(w1)
    outop = [out] if out else []
    if w1alt:
        if w1 or out:
            body = w1 + padlist(W1_T - 8 - ops_t(w1) - ops_t(outop)) + outop
            a.block([('exx', 4)] + body + [('exx', 4)])
        else:
            a.block(padlist(W1_T))
    else:
        a.block(w1 + padlist(W1_T - ops_t(w1) - ops_t(outop)) + outop)
    a.block(audio(1))
    w2 = list(w2)
    budget = W2_T - ops_t(tail)
    if w2 and w2alt:
        a.block([('exx', 4)] + w2 + padlist(budget - 8 - ops_t(w2)) + [('exx', 4)])
    else:
        a.block(w2 + padlist(budget - ops_t(w2)))
    a.block([('dec bc', 6), ('ld a, b', 4), ('or a, c', 4), ('call z, fetch_note', 10)])
    a.block(tail)
    assert a.t - start == T_ITER, (a.t - start)

DATA = [('ld a, (hl)', 7), ('inc hl', 6)]
OUT_DATA = ('out (0x0b), a', 11)

def gen_loop():
    a = Asm()
    a.raw('kd_frame:')
    # CMD: CGRAM address 0, HL' = first half of the glyphs
    iteration(a, [('ld a, #0x40', 7)], ('out (0x0a), a', 11), w1alt=False, w2=[('ld hl, (_cga)', 16)])
    # 12 unrolled data iterations: one key column, the OFF key, the exit checks
    sp = [
        dict(w2=[('ld a, (_kcol)', 13), ('out (0x10), a', 11)], w2alt=False),                 # select one key column
        dict(w2=[('in a, (0x10)', 11), ('ld (_krow), a', 13)], w2alt=False),
        dict(pre=[('xor a, a', 4), ('out (0x10), a', 11)],                                     # then the OFF column
             w2=[('ld a, #0x80', 7), ('out (0x10), a', 11)], w2alt=False),
        dict(w2=[('in a, (0x11)', 11), ('ld (_offr), a', 13)], w2alt=False),
        dict(pre=[('ld a, (_kcol)', 13), ('rlca', 4), ('ld c, a', 4)],
             w2=[('xor a, a', 4), ('out (0x10), a', 11)], w2alt=False),
        dict(pre=[('ld a, (_offm)', 13), ('ld b, a', 4)], w2=[('ld a, c', 4), ('ld (_kcol), a', 13)]),
        dict(pre=[('ld a, (_offr)', 13), ('or a, b', 4), ('and a, #0x02', 7), ('ld b, a', 4)],  # B' = 0 if OFF is down (offm = 2 hides it)
             w2=[('ld a, b', 4), ('sub a, #1', 7), ('sbc a, a', 4), ('ld b, a', 4)]),
        dict(pre=[('ld a, (_offc)', 13), ('add a, #%d' % OFF_STEP, 7), ('and a, b', 4), ('ld c, a', 4)],  # OFF debounce
             w2=[('ld a, c', 4), ('ld (_offc), a', 13)]),
        dict(tail=[('ld a, (_offc)', 13), ('inc a', 4), ('jp z, kd_off', 10)]),
        dict(pre=[('ld a, (_krow)', 13), ('cpl', 4), ('ld b, a', 4)],
             w2=[('ld a, (_kmask)', 13), ('and a, b', 4), ('ld c, a', 4)]),
        dict(tail=[('exx', 4), ('ld a, c', 4), ('exx', 4), ('or a, a', 4), ('jp nz, kd_key', 10)]),
        dict(pre=[('ld b, #%d' % (32 - N_SPECIAL), 7)], tail=[('ld a, (_done)', 13), ('or a, a', 4), ('jp nz, kd_exit', 10)]),
    ]
    assert len(sp) == N_SPECIAL
    for s in sp:
        iteration(a, s.get('pre', []) + DATA, OUT_DATA, w2=s.get('w2', []), w2alt=s.get('w2alt', True), tail=s.get('tail', []))
    a.raw('kd_data1:')
    iteration(a, DATA, OUT_DATA, tail=[('exx', 4), ('dec b', 4), ('exx', 4), ('jp nz, kd_data1', 10)])
    # second half of the glyphs from its own pointer
    iteration(a, [('ld hl, (_cgb)', 16)] + DATA, OUT_DATA, w2=[('ld b, #31', 7)])
    a.raw('kd_data2:')
    iteration(a, DATA, OUT_DATA, tail=[('exx', 4), ('dec b', 4), ('exx', 4), ('jp nz, kd_data2', 10)])
    # EVCHK: count down to the next event record
    iteration(a, [('ld a, (_evw)', 13), ('dec a', 4), ('ld (_evw), a', 13)], tail=[('ld a, (_evw)', 13), ('or a, a', 4), ('jp nz, kd_mq', 10)])
    a.raw('kd_tload:')
    iteration(a, [('ld de, (_evp)', 20), ('ld a, (de)', 7), ('inc de', 6), ('ld b, a', 4)],
              tail=[('exx', 4), ('ld a, b', 4), ('or a, a', 4), ('exx', 4), ('jp z, kd_tend', 10)])
    # one run of consecutive DDRAM cells: count, address command, then count characters
    a.raw('kd_run:')
    iteration(a, [('ld a, (de)', 7), ('ld c, a', 4), ('inc de', 6), ('ld a, (de)', 7), ('inc de', 6)], ('out (0x0a), a', 11))
    a.raw('kd_tdat:')
    iteration(a, [('ld a, (de)', 7), ('inc de', 6)], ('out (0x0b), a', 11), tail=[('exx', 4), ('dec c', 4), ('exx', 4), ('jp nz, kd_tdat', 10)])
    iteration(a, tail=[('exx', 4), ('dec b', 4), ('exx', 4), ('jp nz, kd_run', 10)])
    # glyph halves: one index byte each, pointer = cgdata + 32 * index (B' is 0 here). The audio between W1 and W2
    # changes the flags, so no carry may pass from one block to the other: add hl,hl only.
    a.raw('kd_tend:')
    x2 = ('add hl, hl', 11)
    iteration(a, [('ld a, (de)', 7), ('inc de', 6), ('ld l, a', 4), ('ld h, b', 4), x2, x2], w2=[x2])
    iteration(a, [x2, x2, ('ld bc, #_cgdata', 10), ('add hl, bc', 11)], w2=[('ld (_cga), hl', 16)])
    iteration(a, [('ld a, (de)', 7), ('inc de', 6), ('ld l, a', 4), ('ld h, #0', 7), x2], w2=[x2, x2, ('inc bc', 6)])    # inc bc: a pad, BC' is reloaded next
    iteration(a, [x2, x2, ('ld bc, #_cgdata', 10), ('add hl, bc', 11)], w2=[('ld (_cgb), hl', 16)])
    iteration(a, [('ld a, (de)', 7), ('ld c, a', 4), ('inc de', 6), ('ld (_evp), de', 20)], w2=[('ld a, c', 4), ('ld (_evw), a', 13)])
    iteration(a, tail=[('ld a, (_evw)', 13), ('or a, a', 4), ('jp nz, kd_mq', 10)])
    # wait 0 = jump: the record continues with the address of the next record, which fires at once
    iteration(a, [('ex de, hl', 4), ('ld e, (hl)', 7), ('inc hl', 6), ('ld d, (hl)', 7), ('ld (_evp), de', 20)],
              tail=[('jp kd_tload', 10)])
    # marquee: when its 16-bit countdown ends, the bottom row is rewritten from mqp onwards and mqp moves one character
    a.raw('kd_mq:')
    iteration(a, [('ld hl, (_mqc)', 16), ('dec hl', 6), ('ld (_mqc), hl', 16)], w2=[('ld a, h', 4), ('or a, l', 4), ('ld c, a', 4)])
    iteration(a, tail=[('exx', 4), ('ld a, c', 4), ('or a, a', 4), ('exx', 4), ('jp nz, kd_frame', 10)])
    first = True
    for cmd, n in ((0xC4, 4), (0xD0, 8), (0xE0, 8)):          # DDRAM 68-71, 80-87, 96-103 = row 3, columns 0-19
        iteration(a, ([('ld de, (_mqp)', 20)] if first else []) + [('ld a, #0x%02X' % cmd, 7)], ('out (0x0a), a', 11), w2=[('ld b, #%d' % n, 7)])
        a.raw('kd_mq%02x:' % cmd)
        iteration(a, [('ld a, (de)', 7), ('inc de', 6)], ('out (0x0b), a', 11), tail=[('exx', 4), ('dec b', 4), ('exx', 4), ('jp nz, kd_mq%02x' % cmd, 10)])
        first = False
    iteration(a, [('ld hl, (_mqp)', 16), ('inc hl', 6), ('ld (_mqp), hl', 16)], w2=[('ld hl, (_mqper)', 16)])
    iteration(a, [('ld (_mqc), hl', 16)], tail=[('jp kd_frame', 10)])
    return a

FETCH = '''fetch_note:
	push hl
fn_next:
	ld hl, (_song_ptr)
	ld e, (hl)
	inc hl
	ld d, (hl)
	inc hl
	ld c, (hl)
	inc hl
	ld (_song_ptr), hl
	ld a, d
	cp a, #0xFC
	jr nc, fn_op
	and a, #0xC0
	ld hl, #0
	jr z, fn_led
	ld l, #0x20
	cp a, #0x40
	jr z, fn_led
	ld h, #0x20
fn_led:
	ld (_ledv), hl
	ld a, d
	and a, #0x3F
	ld d, a
	ld l, c
	ld h, #0
	add hl, hl
	add hl, hl
	add hl, hl
	add hl, hl
	add hl, hl
	ld b, h
	ld c, l
	pop hl
	ret
fn_op:
	jr z, fn_loop
	cp a, #0xFD
	jr z, fn_ret
	cp a, #0xFE
	jr z, fn_call
	ld a, #1
	ld (_done), a
	ld hl, #0
	ld (_ledv), hl
	ld de, #0
	ld bc, #0xFFFF
	pop hl
	ret
fn_call:
	ld hl, (_song_ptr)
	ld (_sret), hl
	ld h, c
	ld l, e
	ld (_song_ptr), hl
	jp fn_next
fn_ret:
	ld hl, (_sret)
	ld (_song_ptr), hl
	jp fn_next
fn_loop:
	ld a, (_lcnt)
	or a, a
	jr nz, fn_l1
	ld a, c
fn_l1:
	dec a
	ld (_lcnt), a
	jp z, fn_next
	ld a, e
	inc a
	ld l, a
	add a, a
	add a, l
	ld e, a
	ld d, #0
	ld hl, (_song_ptr)
	or a, a
	sbc hl, de
	ld (_song_ptr), hl
	jp fn_next
'''

def write_engine(path='engine.h'):
    a = gen_loop()
    with open(path, 'w') as f:
        f.write('// generated by gen_engine.py (do not edit): the player loop, %d T-states per iteration\n' % T_ITER)
        f.write('void engine(void) __naked {\n__asm\n')
        f.write('\tdi\n\tpush ix\n\tpush iy\n\tld ix, #_ledv\n\tld hl, #0\n\tld (_ledv), hl\n\tld de, #0\n\tld bc, #1\n\tjp kd_frame\n')
        for l in a.lines:
            f.write(l + '\n')
        f.write('kd_key:\n\tld a, #2\n\tld (_done), a\n\tjr kd_exit\nkd_off:\n\tld a, #4\n\tld (_done), a\n')
        f.write('kd_exit:\n\txor a, a\n\tout (0x10), a\n\tout (0x12), a\n\tpop iy\n\tpop ix\n\tret\n')
        f.write(FETCH)
        f.write('__endasm;\n}\n')
    return len(a.lines)

if __name__ == '__main__':
    print(write_engine())
