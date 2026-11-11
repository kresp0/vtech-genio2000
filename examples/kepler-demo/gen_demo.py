#!/usr/bin/env python3
"""kepler_demo_gl2000: generates song.h (Kepler 2000 music, 3 bytes/entry), scenes.h (bitmaps/tables of the CGRAM scenes)
and loop.h (the unrolled main loop, with the exact T-state count of every iteration).

Architecture (everything with interrupts disabled, a single loop of 256 T-states per iteration = 41.7 us):
  * 2 audio samples per iteration (16-bit phase accumulator, square wave on bit 3 of port 0x12): fs = 2*CLOCK/256
  * 1 LCD write per iteration (>= 37 us between writes, as the HD44780 requires): rewrites the 64 bytes of CGRAM
    (8 characters of 5x8) about 347 times per second; the 64 bytes are computed in real time with tables
  * 5 iterations per frame update, one row per frame, the positions of the 8 pixel strips (speed, sine waviness)
One frame = CMD, H, 64 DATA, S1, S2a, S2b, S3, S4 = 71 iterations.
"""
import math, random
CLOCK = 6131790.0
T_ITER = 256
FS = 2 * CLOCK / T_ITER                 # audio samples per second
UNIT_ITERS = 24                         # 1 duration unit of the song entries = 24 iterations
UNIT_S = UNIT_ITERS * T_ITER / CLOCK    # = 1,0021 ms
# ---- RAM (aligned pages, the firmware uses 0xDC00+) ----
FR, SPF, SPI, SPI0, IN, WP, PA, WOB, TAB0 = 0xC200, 0xC300, 0xC400, 0xC500, 0xC600, 0xC700, 0xC800, 0xC900, 0xCA00
BITS = 0xD200                           # scratch of the table builder (128 bytes)
# ======================= loop =======================
class Asm:
    def __init__(s): s.lines = []; s.t = 0
    def i(s, text, t): s.lines.append('\t' + text); s.t += t
    def raw(s, text): s.lines.append(text)
def audio(led):
    return [('add hl, de', 11), ('ld a, h', 4), ('rrca', 4), ('rrca', 4), ('rrca', 4), ('rrca', 4), ('and a, #0x08', 7), ('.db 0xDD, %s' % ('0xB5' if led == 'ixl' else '0xB4'), 8), ('out (0x12), a', 11)]
MAIN_PAD = [(4, 'nop'), (7, 'ld a, #0'), (12, 'jr .+2'), (13, 'ld a, (0xC0F0)')]
ALT_PAD = [(4, 'nop'), (6, 'inc hl'), (7, 'ld a, #0'), (10, 'ld hl, #0'), (13, 'ld a, (0xC0F0)'), (9, 'ld a, i')]
def padlist(n, opts):
    best = {0: []}
    for v in range(1, n + 1):
        for t, txt in opts:
            if v - t in best and v not in best: best[v] = best[v - t] + [(txt, t)]
    if n not in best: raise SystemExit('cannot pad %d T-states' % n)
    return best[n]
def pad(a, n, opts):
    best = {0: []}
    for v in range(1, n + 1):
        for t, txt in opts:
            if v - t in best and v not in best: best[v] = best[v - t] + [(t, txt)]
    if n not in best: raise SystemExit('cannot pad %d T-states' % n)
    for t, txt in best[n]: a.i(txt, t)
def wrap40():
    return [('ld b, a', 4), ('cp a, #40', 7), ('sbc a, a', 4), ('and a, #40', 7), ('add a, b', 4), ('sub a, #40', 7)]
def iteration(a, w1=None, w2=None, main1=False, last=False, tail=None):
    """w1/w2: list of (text, T) in the alternate context (between exx), except main1=True (main context, no exx)."""
    start = a.t
    for t, tt in audio('ixl'): a.i(t, tt)
    b1 = 71
    if w1 is None: pad(a, b1, MAIN_PAD)
    elif main1:
        used = 0
        for t, tt in w1: a.i(t, tt); used += tt
        pad(a, b1 - used, MAIN_PAD)
    else:
        a.i('exx', 4); used = 8
        for t, tt in w1: a.i(t, tt); used += tt
        pad(a, b1 - used, ALT_PAD); a.i('exx', 4)
    for t, tt in audio('ixh'): a.i(t, tt)
    if last: tail = [('jp (iy)', 8)]
    tail = tail or []
    b2 = 47 - sum(tt for t, tt in tail)
    if w2 is None: pad(a, b2, MAIN_PAD)
    else:
        a.i('exx', 4); used = 8
        for t, tt in w2: a.i(t, tt); used += tt
        pad(a, b2 - used, ALT_PAD); a.i('exx', 4)
    a.i('dec bc', 6); a.i('ld a, b', 4); a.i('or a, c', 4); a.i('call z, _fetch_note', 10)
    for t, tt in tail: a.i(t, tt)
    assert a.t - start == T_ITER, (a.t - start)
def gen_loop():
    a = Asm(); a.raw('kd_frame:')
    # CMD: CGRAM address 0 + end-of-section check
    iteration(a, [('ld a, #0x40', 7), ('out (0x0a), a', 11), ('ld a, (_done)', 13), ('or a, a', 4), ('jp nz, kd_exit', 10)], main1=True)
    # H: time counter (TC += TCR) and row to update (C' = 0..7)
    iteration(a, [('ld hl, #_tcr', 10), ('ld a, (_tc)', 13), ('add a, (hl)', 7), ('ld (_tc), a', 13), ('inc c', 4), ('res 3, c', 8)])
    for t in range(8):
        for y in range(8):
            iteration(a, [('ld a, (0x%04X)' % (PA + y), 13), ('add a, #%d' % (5 * t), 7), ('ld l, a', 4),
                          ('ld h, #0x%02X' % ((TAB0 >> 8) + y), 7), ('ld a, (hl)', 7), ('out (0x0b), a', 11)])
    # S1: position fraction; D' = new fraction, E' = carry
    iteration(a, [('ld l, c', 4), ('ld h, #0x%02X' % (FR >> 8), 7), ('ld a, (hl)', 7), ('ld b, a', 4), ('ld h, #0x%02X' % (SPF >> 8), 7),
                  ('ld a, (hl)', 7), ('add a, b', 4), ('ld d, a', 4), ('ld e, #0', 7), ('rl e', 8)],
              [('ld h, #0x%02X' % (FR >> 8), 7), ('ld l, c', 4), ('ld a, d', 4), ('ld (hl), a', 7)])
    # S2a: E' += integer speed
    iteration(a, [('ld l, c', 4), ('ld h, #0x%02X' % (SPI >> 8), 7), ('ld a, (hl)', 7), ('add a, e', 4), ('ld e, a', 4)])
    # S2b: IN = (IN + E') mod 40
    iteration(a, [('ld l, c', 4), ('ld h, #0x%02X' % (IN >> 8), 7), ('ld a, (hl)', 7), ('add a, e', 4)] + wrap40() + [('ld e, a', 4)],
              [('ld h, #0x%02X' % (IN >> 8), 7), ('ld l, c', 4), ('ld a, e', 4), ('ld (hl), a', 7)])
    # S3: E' = waviness = WOB[TC + WP[y]]
    iteration(a, [('ld l, c', 4), ('ld h, #0x%02X' % (WP >> 8), 7), ('ld a, (hl)', 7), ('ld d, a', 4), ('ld a, (_tc)', 13), ('add a, d', 4),
                  ('ld l, a', 4), ('ld h, #0x%02X' % (WOB >> 8), 7)],
              [('ld a, (hl)', 7), ('ld e, a', 4)])
    # S4: P[y] = (IN[y] + waviness) mod 40
    iteration(a, [('ld l, c', 4), ('ld h, #0x%02X' % (IN >> 8), 7), ('ld a, (hl)', 7), ('add a, e', 4)] + wrap40() + [('ld e, a', 4)],
              [('ld h, #0x%02X' % (PA >> 8), 7), ('ld l, c', 4), ('ld a, e', 4), ('ld (hl), a', 7)], last=True)
    # Finale extension (reached through iy): when the countdown _fw reaches 0 it sends the next record of
    # cell writes (3 cells: address, char x3) to the LCD in 6 iterations, otherwise it only counts down.
    a.raw('kd_ext:')
    iteration(a, tail=[('ld a, (_fw)', 13), ('or a, a', 4), ('jp z, kd_fire', 10)])
    iteration(a, [('ld hl, #_fw', 10), ('dec (hl)', 11)], tail=[('jp kd_frame', 10)])
    a.raw('kd_fire:')
    iteration(a, [('ld de, (_fe_ptr)', 20)])
    for k in range(6):
        iteration(a, padlist(25, ALT_PAD) + [('ld a, (de)', 7), ('inc de', 6), ('out (0x%02x), a' % (0x0a if k % 2 == 0 else 0x0b), 11)])
    iteration(a, [('ld a, (de)', 7), ('ld (_fw), a', 13), ('inc de', 6), ('ld (_fe_ptr), de', 20)], tail=[('jp kd_frame', 10)])
    return a
# ======================= names: four text lines scrolling left, 80 cells rewritten per step =======================
NAMES = ["Genio 2000", "Genius LEADER 4000 Quadro", "Genius LEADER 4004 Quadro L", "Genius 4000", "PreComputer Power Pad"]   # the 4 x 20 family
FIRST_ROW_NAMES = [0, 2, 3, 4]                                 # the name each row starts at: Genio 2000 first
MQ_PAGE = 128                                                  # cells prepared per row (the scroll never gets past n = MQ_PAGE - 21)
MQ_STEP_S, MQ_HOLD_S = 0.05, 1.0
MQ_RATES = [51, 68, 84, 102]                                  # cells per step x 256: 4, 5.3, 6.6 and 8 cells/s
RUNS = [(0, 4), (8, 8), (24, 8), (64, 4), (72, 8), (88, 8), (4, 4), (16, 8), (32, 8), (68, 4), (80, 8), (96, 8)]
def gen_names():
    global ALT_PAD
    saved = ALT_PAD
    ALT_PAD = [(4, 'nop'), (7, 'ld a, #0'), (13, 'ld a, (0xC0F0)'), (9, 'ld a, i')]   # pads must not touch hl', de' or bc'
    a = Asm()
    a.raw('mq_s0:')
    iteration(a, [('ld h, #0xCA', 7), ('ld l, #0xFF', 7), ('ld a, (hl)', 7), ('ld l, a', 4), ('ld de, #mq_tab', 10), ('ld c, #3', 7)])
    a.raw('mq_ctrl:')
    iteration(a, padlist(25, ALT_PAD) + [('ld a, (de)', 7), ('inc de', 6), ('out (0x0a), a', 11)],
              [('ld a, (de)', 7), ('inc de', 6), ('ld b, a', 4)])
    a.raw('mq_data:')
    iteration(a, padlist(25, ALT_PAD) + [('ld a, (hl)', 7), ('inc hl', 6), ('out (0x0b), a', 11)],
              tail=[('exx', 4), ('dec b', 4), ('exx', 4), ('jp nz, mq_data', 10)])
    iteration(a, tail=[('exx', 4), ('dec c', 4), ('exx', 4), ('jp nz, mq_ctrl', 10)])
    iteration(a, [('inc h', 4), ('ld l, #0xFF', 7), ('ld a, (hl)', 7), ('ld l, a', 4), ('ld c, #3', 7)],
              tail=[('exx', 4), ('ld a, h', 4), ('cp a, #0xCE', 7), ('exx', 4), ('jp nz, mq_ctrl', 10)])
    for r in range(4):                                         # every row has its own speed: a fractional accumulator (page byte 254) carries into its offset (byte 255)
        iteration(a, [('ld hl, #0x%02XFE' % (0xCA + r), 10), ('ld a, (hl)', 7), ('add a, #%d' % MQ_RATES[r], 7), ('ld (hl), a', 7),
                      ('inc l', 4), ('ld a, (hl)', 7), ('adc a, #0', 7), ('ld (hl), a', 7)])
    iteration(a, [('ld de, (_mq_cur)', 20), ('ld hl, (_mq_wait)', 16), ('ld (_mq_cur), hl', 16)],
              tail=[('ld a, (_done)', 13), ('or a, a', 4), ('jp nz, mq_exit', 10)])
    a.raw('mq_wait:')
    iteration(a, [('dec de', 6)], tail=[('exx', 4), ('ld a, d', 4), ('or a, e', 4), ('exx', 4), ('jp nz, mq_wait', 10)])
    a.raw('\tjp mq_s0')
    ALT_PAD = saved
    return a
NAMES_STR = bytes([0x20, 0xCD, 0x20]).join(n.encode('ascii') for n in NAMES) + bytes([0x20, 0xCD, 0x20])
NAME_POS = [sum(len(n) + 3 for n in NAMES[:k]) for k in range(len(NAMES))]
def write_names():
    a = gen_names()
    iters = lambda sec: int(round(sec * CLOCK / T_ITER))
    step_wait = iters(MQ_STEP_S) - 115; hold_wait = iters(MQ_HOLD_S) - 115
    with open('names.h', 'w') as f:
        f.write('// generated by gen_demo.py (do not edit): the names scroller. Every row shows the same circular string, starting at a different name\n')
        f.write('#define MQ_STEP %d\n#define MQ_HOLD %d\n#define MQ_PAGE %d\n#define MQ_LEN %d\n' % (step_wait, hold_wait, MQ_PAGE, len(NAMES_STR)))
        f.write('static const byte mq_start[4] = {%s};\n' % ','.join(str(NAME_POS[k]) for k in FIRST_ROW_NAMES))
        f.write('static const byte mq_str[%d] = {\n\t%s\n};\n' % (len(NAMES_STR), ','.join(str(v) for v in NAMES_STR)))
        f.write('void play_names_loop() __naked {\n__asm\n')
        f.write('\tdi\n\tpush ix\n\t.db 0xDD, 0x2E, 0\n\t.db 0xDD, 0x26, 0\n\tld hl, #0\n\tld de, #0\n\tld bc, #1\n\txor a, a\n\tld (_done), a\n\texx\n\tld c, #0\n\tld hl, #0\n\tld de, #0\n\texx\n')
        f.write('\tld de, (_mq_cur)\n\texx\n\tld de, (_mq_cur)\n\texx\n') if False else None
        for l in a.lines: f.write(l + '\n')
        f.write('mq_exit:\n\txor a, a\n\tout (0x12), a\n\tpop ix\n\tei\n\tret\nmq_tab:\n')
        for addr, ln in RUNS: f.write('\t.db 0x%02x, %d\n' % (0x80 | addr, ln))
        f.write('__endasm;\n}\n')
    return len(a.lines)
def write_loop():
    a = gen_loop()
    frame_iters = 2 + 64 + 5
    with open('loop.h', 'w') as f:
        f.write('// generated by gen_demo.py (do not edit): main loop, %d iterations/frame x %d T-states\n' % (frame_iters, T_ITER))
        f.write('void play_demo() __naked {\n__asm\n')
        f.write('\tdi\n\tpush ix\n\tpush iy\n\tld iy, #kd_frame\n\tld a, (_fe_on)\n\tor a, a\n\tjr z, kd_noext\n\tld iy, #kd_ext\nkd_noext:\n\t.db 0xDD, 0x2E, 0\n\t.db 0xDD, 0x26, 0\n\tld hl, #0\n\tld de, #0\n\tld bc, #1\n\txor a, a\n\tld (_done), a\n\texx\n\tld c, #0\n\tld hl, #0\n\texx\n')
        for l in a.lines: f.write(l + '\n')
        f.write('kd_exit:\n\txor a, a\n\tout (0x12), a\n\tpop iy\n\tpop ix\n\tei\n\tret\n__endasm;\n}\n')
    return frame_iters
# ======================= music =======================
def freq(n):
    NAMES = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
    m = NAMES[n[:-1]] + 12 * (int(n[-1]) + 1); return 440.0 * 2 ** ((m - 69) / 12)
def stp(f): return max(1, int(round(f * 65536 / FS)))
BPM = 108; S = 60.0 / BPM / 4
K = 1.0 / UNIT_S
class TL:
    def __init__(s, secs): s.o = [0] * int(round(secs * K))
    def tone(s, t, f, dur, gap=0.0):
        a, e = int(round(t * K)), int(round((t + dur - gap) * K))
        for i in range(a, min(e, len(s.o))): s.o[i] = stp(f) if f else 0
    def sweep(s, t, f0, f1, dur, blk=4):
        n = max(1, int(dur * 1000 / blk))
        for k in range(n):
            f = f0 * (f1 / f0) ** (k / max(1, n - 1)); a = int(round(t * K)) + k * blk
            for i in range(a, a + blk):
                if i < len(s.o): s.o[i] = stp(f)
    def noise(s, t, dur, rnd, blk=3):
        a = int(round(t * K))
        for k in range(0, int(dur * 1000), blk):
            st = rnd.randrange(3500, 9000)
            for i in range(a + k, a + k + blk):
                if i < len(s.o): s.o[i] = st
    def kick(s, t): s.sweep(t, 190, 45, 0.07, 4)
rnd = random.Random(2000)
CH = [['C4','D#4','G4','C5'], ['G#3','C4','D#4','G#4'], ['F3','G#3','C4','F4'], ['G3','B3','D4','G4']]
BASS = ['C3', 'G#2', 'F2', 'G2']
PAT = [0,1,2,3,2,1,2,3, 0,1,2,3,2,1,2,1, 0,1,2,3,2,1,2,3, 0,1,2,3,3,2,1,2]
def drums(tl, t0, bars, bass=True):
    for b in range(bars):
        for beat in range(4):
            t = t0 + (b * 16 + beat * 4) * S
            if beat % 2 == 0: tl.kick(t)
            elif bass: tl.tone(t, freq(BASS[b % 4]), 0.055)
            tl.noise(t + 2 * S, 0.012, rnd)
def arp(tl, t0, bars, chords, step=S / 2):
    for b in range(bars):
        for k in range(32):
            t = t0 + b * 16 * S + k * step
            tl.tone(t, freq(CH[chords[b % len(chords)]][PAT[k]]), step, gap=step * 0.18)
def sec_warp():
    tl = TL(5.6); tl.sweep(0.0, 40, 900, 2.6, 6); tl.sweep(2.6, 900, 1500, 0.15, 3)
    for t in (3.1, 3.9, 4.5, 4.9, 5.2): tl.sweep(t, 1760, 1500, 0.07, 5)
    return tl
def sec_scan():
    tl = TL(4 * 16 * S); arp(tl, 0, 4, [0, 1, 2, 3]); drums(tl, 0, 4); return tl
LEAD = [[('G4',8),('D#5',4),('D5',4)], [('C5',8),('D#5',4),('C5',4)], [('F5',6),('D#5',2),('C5',4),('G#4',4)], [('B4',6),('D5',2),('G5',8)]]
def sec_contact(bars=4, lead=LEAD):
    tl = TL(bars * 16 * S); t = 0.0; g = 0
    for b, bar in enumerate(lead):
        for n, d in bar:
            a, e = t, t + d * S - 0.03; tt = a
            while tt < e - 0.001:
                tl.tone(tt, freq(n), 0.014); tl.tone(tt + 0.014, freq(CH[b][g % 4]), 0.009); g += 1; tt += 0.023
            t += d * S
    drums(tl, 0, bars, bass=False); return tl
def sec_jump():
    tl = TL(2 * 16 * S); up = ['C4','D#4','G4','C5','D#5','G5','C6','D#6']; k = 0; t = 0.0
    while t < 16 * S - 0.04: tl.tone(t, freq(up[k % 8]), 0.034, gap=0.006); k += 1; t += 0.04
    for j in range(3): tl.sweep(16 * S + j * 4 * S, 3200, 260, 0.30, 4)
    tl.tone(16 * S + 12 * S, freq('G3'), 0.30, 0.0); tl.kick(0); tl.kick(8 * S); return tl
def sec_outro():
    tl = TL(7.5)
    for t, n in ((0.0, 'C6'), (0.35, 'G5'), (0.85, 'D#5'), (1.55, 'C5'), (2.5, 'G4')): tl.sweep(t, freq(n) * 1.03, freq(n), 0.09, 5)
    tl.sweep(3.4, 160, 32, 2.4, 8); tl.sweep(6.45, 1200, 1100, 0.08, 5); return tl
def encode(steps, split=()):
    steps = steps[:]; steps[-14:] = [0] * 14       # silence at the end: the tables of the next scene are rebuilt here
    data = []; i = 0
    while i < len(steps):
        if i in split: data += [0xFF, 0xFF, 0]     # end marker in the middle: play_demo returns and is called again
        j = i + 1
        while j < len(steps) and steps[j] == steps[i] and j not in split: j += 1
        cnt = j - i; st = steps[i]
        while cnt > 0:
            c = min(cnt, 255); cnt -= c; data += [st & 255, st >> 8, c]
        i = j
    return data + [0xFF, 0xFF, 0]
def write_song():
    secs = [('song_warp', sec_warp(), ()), ('song_scan', sec_scan(), [int(round(n * S * K)) for n in (16, 28, 40, 52)]), ('song_contact', sec_contact(), ()), ('song_jump', sec_jump(), ()), ('song_outro', sec_outro(), ())]
    tot = 0; size = 0
    with open('song.h', 'w') as f:
        f.write('// generated by gen_demo.py (do not edit): 3-byte entries: phase step (16 LE), duration (units of %.4f ms); step 0xFFFF = end\n' % (UNIT_S * 1000))
        for name, tl, split in secs:
            d = encode(tl.o, split); tot += len(tl.o) * UNIT_S; size += len(d)
            f.write('static const byte %s[%d] = {\n' % (name, len(d)))
            for i in range(0, len(d), 16): f.write('\t' + ','.join('0x%02x' % b for b in d[i:i+16]) + ',\n')
            f.write('};\n')
    return size, tot
# ======================= scenes (bitmaps of 8 rows x 40 pixels, periodic) =======================
FONT = {'K':['10001','10010','10100','11000','10100','10010','10001'], 'E':['11111','10000','10000','11110','10000','10000','11111'],
        'P':['11110','10001','10001','11110','10000','10000','10000'], 'L':['10000']*6 + ['11111'],
        'R':['11110','10001','10001','11110','10100','10010','10001'], 'G':['01110','10001','10000','10111','10001','10001','01110'],
        'N':['10001','11001','10101','10011','10001','10001','10001'], 'I':['01110','00100','00100','00100','00100','00100','01110'],
        'O':['01110','10001','10001','10001','10001','10001','01110'], '2':['01110','10001','00001','00110','01000','10000','11111'],
        '0':['01110','10001','10011','10101','11001','10001','01110'], ' ':['00000'] * 7}
FONT3 = {'G':['.##','#..','#..','#.#','#.#','#.#','.##'], 'E':['###','#..','#..','##.','#..','#..','###'],
         'N':['#..#','##.#','##.#','#.##','#.##','#..#','#..#'], 'I':['#']*7,
         'O':['.#.','#.#','#.#','#.#','#.#','#.#','.#.'], '2':['###','..#','..#','###','#..','#..','###'],
         '0':['###','#.#','#.#','#.#','#.#','#.#','###'], ' ':['.'] * 7}
def text_rows3(txt):
    rows = [''] * 8
    for ch in txt:
        g = FONT3[ch]
        for y in range(7): rows[y] += g[y].replace('.', '0').replace('#', '1') + '0'
        rows[7] += '0' * (len(g[0]) + 1)
    assert len(rows[0]) <= 40, len(rows[0])
    return [(r + '0' * 40)[:40] for r in rows]
def text_rows(txt, gap=1):
    rows = [''] * 8
    for ch in txt:
        g = FONT[ch]
        for y in range(7): rows[y] += g[y] + '0' * gap
        rows[7] += '0' * (5 + gap)
    return [(r + '0' * 40)[:40] for r in rows]
def rows_to_bytes(rows):
    out = []
    for r in rows:
        for b in range(5): out.append(int(r[b*8:b*8+8], 2))
    return out
def sc_warp():
    L = [3, 9, 4, 14, 6, 11, 5, 16]; O = [0, 17, 9, 28, 3, 22, 13, 33]; rows = []
    for y in range(8):
        r = ['0'] * 40
        for k in range(L[y]): r[(O[y] + k) % 40] = '1'
        r[(O[y] + 23) % 40] = '1'; rows.append(''.join(r))
    return dict(rows=rows, spf=[0,128,64,192,32,160,96,224], spi=[1,1,1,2,2,2,3,3], in0=[0]*8, wp=[0]*8, tcr=0, sh=7, gen=1)
def sc_scan():
    rows = []
    for y in range(8):
        r = ['0'] * 40
        for x in range(40):
            if round(3.5 + 3.2 * math.sin(2 * math.pi * x / 40)) == y: r[x] = '1'
        rows.append(''.join(r))
    return dict(rows=rows, spf=[102]*8, spi=[1]*8, in0=[0]*8, wp=[y * 10 for y in range(8)], tcr=2, sh=3, gen=0)
def sc_text(txt, spf, wps, sh):
    return dict(rows=text_rows(txt), spf=[spf]*8, spi=[0]*8, in0=[0]*8, wp=[y * wps for y in range(8)], tcr=1, sh=sh, gen=0)
def sc_text3(txt, spf, wps, sh):
    rows = text_rows3(txt)
    rows[7] = ('11111100' * 5)                                  # the cursor row: dashes that run the other way under the text
    spf = [spf] * 7 + [102]; spi = [0] * 7 + [38]
    return dict(rows=rows, spf=spf, spi=spi, in0=[0]*8, wp=[y * wps for y in range(7)] + [0], tcr=1, sh=sh, gen=0)
def sc_jump():
    rows = [''.join('1' if ((x + 2 * y) % 8) < 3 else '0' for x in range(40)) for y in range(8)]
    return dict(rows=rows, spf=[0]*8, spi=[0,0,1,1,0,0,1,1], in0=[0]*8, wp=[y * 20 for y in range(8)], tcr=1, sh=2, gen=1)
def sc_finale():
    L = [2, 5, 1, 7, 3, 6, 2, 4]; O = [0, 17, 9, 28, 3, 22, 13, 33]; rows = []        # sparse streaks, so the ships and the blast stand out
    for y in range(8):
        r = ['0'] * 40
        for k in range(L[y]): r[(O[y] + k) % 40] = '1'
        rows.append(''.join(r))
    return dict(rows=rows, spf=[0,128,64,192,32,160,96,224], spi=[1,1,1,2,2,2,3,3], in0=[0]*8, wp=[0]*8, tcr=0, sh=7, gen=0)
# ======================= finale: ships and an explosion drawn over the CGRAM streaks with ROM characters =======================
MAP4 = [0,1,2,3,8,9,10,11,12,13,14,15,24,25,26,27,28,29,30,31, 64,65,66,67,72,73,74,75,76,77,78,79,88,89,90,91,92,93,94,95,
        4,5,6,7,16,17,18,19,20,21,22,23,32,33,34,35,36,37,38,39, 68,69,70,71,80,81,82,83,84,85,86,87,96,97,98,99,100,101,102,103]
def bg(r, c): return (c + 2 * r) & 7
def cell(r, c, ch): return (0x80 | MAP4[r * 20 + c], ch)
def finale_events():
    ev = []                                                    # (time s, [(row, col, char)])
    sparks = [0xB0, 0xB1, 0xB2, 0xB3, 0xB4]                    # small dots of the ROM
    rg = random.Random(5)
    # two ships fly together to the right on different rows, the one on row 1 three cells ahead
    NOSE = 0xF6
    for k in range(25):
        ups = []
        for row, lag in ((1, 0), (2, 3)):
            h = k - lag
            for col, ch in ((h, NOSE), (h - 1, 0xB2), (h - 2, None)):
                if 0 <= col < 20: ups.append((row, col, bg(row, col) if ch is None else ch))
        if ups: ev.append((0.1 + 0.125 * k, ups))
    cr, cc = 1.5, 9.5
    cells = [(r, c, math.hypot((c - cc) * 0.55, r - cr)) for r in range(4) for c in range(20)]
    # the explosion: a flash, then rings of star, plus, circle and flying sparks
    t0 = 3.4
    ev.append((t0, [(r, c, 0xFF) for r, c, d in cells if d < 1.0]))
    for dt, lo, hi, ch in ((0.12, 0.0, 1.0, '*'), (0.12, 1.0, 1.9, '+'), (0.4, 1.9, 2.8, 'o'), (0.72, 2.8, 4.0, None), (1.05, 4.0, 5.4, None)):
        grp = [(r, c, ord(ch) if ch else rg.choice(sparks)) for r, c, d in cells if lo <= d < hi]
        for i in range(0, len(grp), 6): ev.append((t0 + dt, grp[i:i+6]))
    # the screen collapses like a switched-off tube: rows go blank, the last row becomes a bar, the bar shrinks to a "+" and a dot
    r0, c0 = 2, 10
    for t, row in ((4.7, 0), (4.85, 3), (5.0, 1)):
        ev.append((t, [(row, c, 0x20) for c in range(20)]))
    ev.append((5.15, [(r0, c, 0xFD) for c in range(20)]))
    ev.append((5.30, [(r0, c, 0x2D) for c in range(20)]))        # the bar gets thinner
    for k in range(9):
        ev.append((5.42 + 0.05 * k, [(r0, k, 0x20), (r0, 19 - k, 0x20)]))
    ev.append((5.42 + 0.05 * 9, [(r0, 9, 0x20)]))
    ev.append((5.95, [(r0, c0, ord('+'))]))
    ev.append((6.45, [(r0, c0, 0xCD)]))
    global FE_DOT; FE_DOT = 6.45
    ev.sort(key=lambda e: e[0]); return ev
T_IDLE = 73 * T_ITER / CLOCK; T_FIRE = 80 * T_ITER / CLOCK
def write_finale():
    recs = []                                                  # (time, [bytes x6])
    for t, ups in finale_events():
        for i in range(0, len(ups), 3):
            g = ups[i:i+3]; g = g + [g[-1]] * (3 - len(g)); b = []
            for r, c, ch in g: b += list(cell(r, c, ch))
            recs.append((t, b))
    cur = 0.0; waits = []; data = []
    for t, b in recs:
        n = max(0, int(round((t - cur) / T_IDLE)))
        while n > 254 and data:                                 # long pause: repeat the previous record while waiting
            waits.append(254); cur += 254 * T_IDLE + T_FIRE; data.append(data[-1]); n -= 255
        assert n < 255, n
        waits.append(max(n, 0)); cur += n * T_IDLE + T_FIRE; data.append(b)
    data += [data[-1]] * 3                                      # the last record again: keeps the point on until the music ends
    waits += [255] * 3
    out = []
    for i, b in enumerate(data): out += b + [waits[i + 1] if i + 1 < len(data) else 255]
    with open('finale.h', 'w') as f:
        f.write('// generated by gen_demo.py (do not edit): finale cell writes, 6 bytes (3 x address, char) + frames to wait\n')
        f.write('#define FE_WAIT0 %d\nstatic const byte fe_stream[%d] = {\n' % (waits[0], len(out)))
        for i in range(0, len(out), 14): f.write('\t' + ','.join(str(v) for v in out[i:i+14]) + ',\n')
        f.write('};\n')
    return len(out), cur
def write_scenes():
    scs = [sc_warp(), sc_scan(), sc_text('KEPLER', 100, 8, 3), sc_jump(), sc_finale()]
    sine = [int(round(31.5 + 31.5 * math.sin(2 * math.pi * i / 256))) for i in range(256)]
    with open('scenes.h', 'w') as f:
        f.write('// generated by gen_demo.py (do not edit). Per scene (75 bytes): bitmap 8x5, spf[8], spi[8], in0[8], wp[8], tcr, waviness shift, gen\n')
        f.write('static const byte scene_data[%d][75] = {\n' % len(scs))
        for s in scs:
            d = rows_to_bytes(s['rows']) + s['spf'] + s['spi'] + s['in0'] + s['wp'] + [s['tcr'], s['sh'], s['gen']]
            assert len(d) == 75
            f.write('\t{' + ','.join(str(v) for v in d) + '},\n')
        f.write('};\nstatic const byte sine_tab[256] = {\n')
        for i in range(0, 256, 16): f.write('\t' + ','.join(str(v) for v in sine[i:i+16]) + ',\n')
        f.write('};\n')
if __name__ == '__main__':
    import gen_helpers; gen_helpers.write_helpers(SPI0, SPI, TAB0, BITS, WOB)
    n = write_loop(); size, secs = write_song(); write_scenes(); write_names(); fsize, fend = write_finale(); print('finale: %d bytes, last record at %.2f s' % (fsize, fend))
    print('frame: %d iterations x %d T = %d T (%.2f ms, %.1f CGRAM frames/s); audio fs = %.1f Hz; music %d bytes, %.1f s'
          % (n, T_ITER, n * T_ITER, n * T_ITER / CLOCK * 1000, CLOCK / (n * T_ITER), FS, size, secs))
