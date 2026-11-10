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
ALT_PAD = [(4, 'nop'), (6, 'inc hl'), (7, 'ld a, #0'), (10, 'ld hl, #0'), (13, 'ld a, (0xC0F0)')]
def pad(a, n, opts):
    best = {0: []}
    for v in range(1, n + 1):
        for t, txt in opts:
            if v - t in best and v not in best: best[v] = best[v - t] + [(t, txt)]
    if n not in best: raise SystemExit('cannot pad %d T-states' % n)
    for t, txt in best[n]: a.i(txt, t)
def wrap40():
    return [('ld b, a', 4), ('cp a, #40', 7), ('sbc a, a', 4), ('and a, #40', 7), ('add a, b', 4), ('sub a, #40', 7)]
def iteration(a, w1=None, w2=None, main1=False, last=False):
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
    b2 = 47 - (10 if last else 0)
    if w2 is None: pad(a, b2, MAIN_PAD)
    else:
        a.i('exx', 4); used = 8
        for t, tt in w2: a.i(t, tt); used += tt
        pad(a, b2 - used, ALT_PAD); a.i('exx', 4)
    a.i('dec bc', 6); a.i('ld a, b', 4); a.i('or a, c', 4); a.i('call z, _fetch_note', 10)
    if last: a.i('jp kd_frame', 10)
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
    return a
def write_loop():
    a = gen_loop()
    frame_iters = sum(1 for l in a.lines if l.strip() == 'jp kd_frame') and (a.t // T_ITER)
    with open('loop.h', 'w') as f:
        f.write('// generated by gen_demo.py (do not edit): main loop, %d iterations/frame x %d T-states\n' % (frame_iters, T_ITER))
        f.write('void play_demo() __naked {\n__asm\n')
        f.write('\tdi\n\tpush ix\n\t.db 0xDD, 0x2E, 0\n\t.db 0xDD, 0x26, 0\n\tld hl, #0\n\tld de, #0\n\tld bc, #1\n\txor a, a\n\tld (_done), a\n\texx\n\tld c, #0\n\tld hl, #0\n\texx\n')
        for l in a.lines: f.write(l + '\n')
        f.write('kd_exit:\n\txor a, a\n\tout (0x12), a\n\tpop ix\n\tei\n\tret\n__endasm;\n}\n')
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
    tl = TL(6.0)
    for t, n in ((0.0, 'C6'), (0.35, 'G5'), (0.85, 'D#5'), (1.55, 'C5'), (2.5, 'G4')): tl.sweep(t, freq(n) * 1.03, freq(n), 0.09, 5)
    tl.sweep(3.4, 160, 32, 2.4, 8); return tl
def encode(steps):
    steps = steps[:]; steps[-14:] = [0] * 14       # silence at the end: the tables of the next scene are rebuilt here
    data = []; i = 0
    while i < len(steps):
        j = i
        while j < len(steps) and steps[j] == steps[i]: j += 1
        cnt = j - i; st = steps[i]
        while cnt > 0:
            c = min(cnt, 255); cnt -= c; data += [st & 255, st >> 8, c]
        i = j
    return data + [0xFF, 0xFF, 0]
def write_song():
    secs = [('song_warp', sec_warp()), ('song_scan', sec_scan()), ('song_contact', sec_contact()), ('song_jump', sec_jump()), ('song_outro', sec_outro())]
    tot = 0; size = 0
    with open('song.h', 'w') as f:
        f.write('// generated by gen_demo.py (do not edit): 3-byte entries: phase step (16 LE), duration (units of %.4f ms); step 0xFFFF = end\n' % (UNIT_S * 1000))
        for name, tl in secs:
            d = encode(tl.o); tot += len(tl.o) * UNIT_S; size += len(d)
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
    return dict(rows=rows, spf=[230]*8, spi=[0]*8, in0=[0]*8, wp=[y * 10 for y in range(8)], tcr=1, sh=3, gen=0)
def sc_text(txt, spf, wps, sh):
    return dict(rows=text_rows(txt), spf=[spf]*8, spi=[0]*8, in0=[0]*8, wp=[y * wps for y in range(8)], tcr=1, sh=sh, gen=0)
def sc_jump():
    rows = [''.join('1' if ((x + 2 * y) % 8) < 3 else '0' for x in range(40)) for y in range(8)]
    return dict(rows=rows, spf=[0]*8, spi=[0,0,1,1,0,0,1,1], in0=[0]*8, wp=[y * 20 for y in range(8)], tcr=1, sh=2, gen=1)
def write_scenes():
    scs = [sc_warp(), sc_scan(), sc_text('KEPLER', 100, 8, 3), sc_text('GENIO', 140, 10, 3), sc_jump(), sc_text('2000', 60, 6, 3)]
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
    n = write_loop(); size, secs = write_song(); write_scenes()
    print('frame: %d iterations x %d T = %d T (%.2f ms, %.1f CGRAM frames/s); audio fs = %.1f Hz; music %d bytes, %.1f s'
          % (n, T_ITER, n * T_ITER, n * T_ITER / CLOCK * 1000, CLOCK / (n * T_ITER), FS, size, secs))
