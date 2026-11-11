"""song.h: the music, one single 1-bit voice.

Entry = 3 bytes: phase step (14 bits) | LED level << 14 (0 off, 1 dim, 2 on), duration in units of 32 iterations.
Ops (high byte >= 0xFC): [K, FC, R] plays the K entries before it R times in all; [lo, FE, hi] calls a pattern;
[0, FD, 0] returns; [FF, FF, 0] ends the song.
"""
import random
from gen_engine import FS, UNIT_S

BPM = 144
SIXT = 78                                   # units per 16th note (104.2 ms: 144 BPM)
BEAT = 4 * SIXT
BAR = 16 * SIXT

NOTE = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}

def freq(n):
    m = NOTE[n[:-1]] + 12 * (int(n[-1]) + 1)
    return 440.0 * 2 ** ((m - 69) / 12)

def step(f):
    s = int(round(f * 65536 / FS)) if f else 0
    assert 0 <= s < 0x4000, f
    return s

class Song:
    def __init__(s, name):
        s.name = name
        s.items = []                        # ('n', step, led, dur) | ('loop', k, r) | ('call', label) | ('ret',) | ('end',)
    def n(s, f, dur, led=0):
        f = freq(f) if isinstance(f, str) else f
        while dur > 0:
            d = min(dur, 255)
            s.items.append(('n', step(f), led, d))
            dur -= d
        return s
    def rest(s, dur, led=0):
        return s.n(0, dur, led)
    def loop(s, k, r):
        assert 1 <= k <= 80 and 2 <= r <= 255
        s.items.append(('loop', k, r))
        return s
    def call(s, pat):
        s.items.append(('call', pat.name))
        return s
    def entries(s):
        return len(s.items)

def expand(song, pats):
    """the notes as played: list of (step, led, dur)"""
    out = []
    def run(items, top):
        i = 0
        while i < len(items):
            it = items[i]
            if it[0] == 'n':
                out.append(it[1:])
            elif it[0] == 'loop':
                k, r = it[1], it[2]
                block = items[i - k:i]
                assert all(b[0] == 'n' for b in block), 'loops hold notes only'
                for _ in range(r - 1):
                    out.extend(b[1:] for b in block)
            elif it[0] == 'call':
                assert top, 'patterns do not call patterns'
                run(pats[it[1]].items, False)
            i += 1
    run(song.items, True)
    return out

def units(song, pats):
    return sum(d for _, _, d in expand(song, pats))

# ---------------------------------------------------------------- instruments
rnd = random.Random(2000)

def kick(s, total=SIXT * 2, led=2):
    for f, d in ((190, 7), (130, 7), (90, 8), (62, 10)):
        s.n(f, d, led)
    s.rest(total - 32)

def snare(s, total=SIXT * 2, led=1):
    for k in range(6):
        s.n(rnd.randrange(2500, 7000), 4, led)
    s.n(rnd.randrange(900, 1500), 6, led)
    s.rest(total - 30)

def hat(s, total=SIXT):
    s.n(9000, 2).n(6500, 2).rest(total - 4)

def blip(s, f, on, total, led=0):
    s.n(f, on, led).rest(total - on)

def trill(s, lead, other, dur, led=0):
    """lead and a second voice alternated every 18 + 9 units; dur is a multiple of 27 units after trimming"""
    k = max(1, dur // 27)
    s.n(lead, 18, led).n(other, 9, led)
    if k > 1:
        s.loop(2, k)
    rem = dur - 27 * k
    if rem:
        s.n(lead, rem, led)

# ---------------------------------------------------------------- sections
def song_basic(typing):
    """typing: list of (time in units, key) from gen_scenes; one click per key"""
    s = Song('song_basic')
    t = 0
    for at, key in typing:
        s.rest(at - t)
        if key == '\n':
            s.n(1700, 6).n(1250, 6)
            t = at + 12
        else:
            s.n(2600 + rnd.randrange(-150, 150), 3)
            t = at + 3
    s.rest(int(0.45 / UNIT_S))
    return s

def song_ready():
    s = Song('song_ready')
    for k, f in enumerate((330, 370, 415, 494, 554)):         # one thunk per letter, on 8ths
        s.n(f, 6, 2).n(f * 0.7, 6, 2).n(f * 0.5, 8, 2).n(f * 0.35, 10, 2).rest(2 * SIXT - 30, 0)
    s.rest(2 * SIXT)
    trill(s, 'A5', 'E5', 4 * SIXT, 1)                          # chord stab: A minor
    trill(s, 'C6', 'A5', 4 * SIXT, 2)
    trill(s, 'E6', 'A5', 4 * SIXT, 1)
    s.rest(BAR * 2 - units(s, {}))
    return s

def song_set():
    """engines charging: bass pulse on 8ths and a rising tone in between, then the countdown"""
    s = Song('song_set')
    n8 = 24
    for k in range(n8):
        f = 140 * (1700 / 140) ** (k / (n8 - 1))
        s.n('E2', 26, 2).n(f, 2 * SIXT - 32, 1 if k % 2 else 0).rest(6)
    for f in ('E5', 'E5', 'E5'):                               # 3, 2, 1
        s.n(f, 40, 2).n(freq(f) / 2, 20, 2).rest(BEAT - 60)
    s.n(220, 30, 2)
    for k in range(20):
        s.n(220 * 2 ** (k / 6), 12, 2)
    s.rest(BAR * 4 - units(s, {}))
    return s

def song_prompt():
    """heartbeat and a sonar ping, two bars, played again while waiting for a key"""
    s = Song('song_prompt')
    s.n('A5', 10, 0).n('A4', 6, 0).rest(BEAT - 16)
    for b in range(7):
        s.n(70, 22, 2).rest(30, 0).n(58, 26, 1).rest(BEAT - 78, 0)
    s.rest(BAR * 2 - units(s, {}))
    return s

def song_go():
    s = Song('song_go')
    for k in range(10):
        s.n(rnd.randrange(1500, 8000), 5, 2)
    for k in range(36):
        s.n(1900 * (55 / 1900) ** (k / 35), 12, 2)
    s.rest(BAR - units(s, {}))
    return s

CHORDS = {'Am': ('A3', 'C4', 'E4'), 'F': ('F3', 'A3', 'C4'), 'C': ('C4', 'E4', 'G4'), 'G': ('G3', 'B3', 'D4'),
          'E': ('E3', 'G#3', 'B3'), 'Dm': ('D4', 'F4', 'A4')}
BASS = {'Am': 'A2', 'F': 'F2', 'C': 'C3', 'G': 'G2', 'E': 'E2', 'Dm': 'D3'}
PROG = ['Am', 'F', 'C', 'G', 'Am', 'F', 'G', 'E']

def groove_bar(name, chord, fill=False):
    """kick on 1 and 3, snare on 2 and 4, bass and arpeggio on the other 16ths; the half bar is played twice"""
    p = Song(name)
    b = BASS[chord]
    bo = b[:-1] + str(int(b[-1]) + 1)
    c = CHORDS[chord]
    kick(p, SIXT, 2)
    blip(p, bo, 26, SIXT)
    blip(p, c[2] if not fill else c[0], 22, SIXT, 0)
    blip(p, b, 30, SIXT, 1)
    snare(p, SIXT, 1)
    blip(p, c[1], 22, SIXT)
    blip(p, bo, 26, SIXT, 1)
    blip(p, c[0], 22, SIXT)
    p.loop(p.entries(), 2)
    p.items.append(('ret',))
    return p

MELODY = [   # (note or None, 16ths), one bar per line, 16 sixteenths each
    [('E5', 3), ('A5', 3), ('G5', 2), ('E5', 2), ('D5', 2), ('C5', 4)],
    [('C5', 3), ('F5', 3), ('E5', 2), ('C5', 2), ('A4', 2), ('C5', 4)],
    [('G4', 2), ('C5', 2), ('E5', 2), ('G5', 2), ('E5', 2), ('C5', 2), ('E5', 4)],
    [('D5', 3), ('G5', 3), ('F5', 2), ('D5', 2), ('B4', 2), ('G4', 4)],
    [('E5', 3), ('A5', 3), ('B5', 2), ('C6', 2), ('B5', 2), ('A5', 4)],
    [('A5', 3), ('C6', 3), ('A5', 2), ('F5', 2), ('A5', 2), ('C6', 4)],
    [('B5', 3), ('D6', 3), ('B5', 2), ('G5', 2), ('D5', 2), ('G5', 4)],
    [('G#5', 3), ('B5', 3), ('E6', 2), ('D6', 2), ('B5', 2), ('G#5', 2), ('E5', 2)],
]

def lead_bar(name, chord, notes):
    """melody against the chord's root (fast alternation), a kick at the start of the bar"""
    p = Song(name)
    low = CHORDS[chord][0]
    first = True
    for n, d in notes:
        dur = d * SIXT - 8
        if first:
            p.n(140, 6, 2).n(80, 8, 2)
            dur -= 14
            first = False
        trill(p, n, low, dur, 1)
        p.rest(8)
    assert sum(d for _, d in notes) == 16, name
    p.items.append(('ret',))
    return p

def song_launch(pats):
    s = Song('song_launch')
    for b in range(8):
        s.call(pats['g_' + PROG[b]] if b != 7 else pats['gf_E'])
    return s

def song_warp(pats):
    s = Song('song_warp')
    for b in range(8):
        s.call(pats['l%d' % b])
    return s

def song_credits(pats):
    """the groove again, then a slow arpeggio coda that ends on A"""
    s = Song('song_credits')
    for b in range(6):
        s.call(pats['g_' + PROG[b]])
    for ch, led in (('F', 1), ('G', 1)):
        for n in CHORDS[ch] + (CHORDS[ch][0][:-1] + str(int(CHORDS[ch][0][-1]) + 1),):
            blip(s, n, SIXT * 3, SIXT * 4, led)
    for n in ('A3', 'C4', 'E4', 'A4'):
        blip(s, n, 60, SIXT, 2)
    trill(s, 'A5', 'E5', BAR - 4 * SIXT, 1)
    s.rest(BAR * 9 - units(s, pats))
    return s

def song_end():
    s = Song('song_end')
    s.rest(BAR * 2)
    return s

def song_bye():
    s = Song('song_bye')
    for n in ('E5', 'C5', 'A4', 'E4'):
        s.n(n, 70, 1).rest(20)
    for k in range(30):
        s.n(330 * (40 / 330) ** (k / 29), 10, 0)
    s.rest(80)
    return s

# ---------------------------------------------------------------- output
def asm_song(song, f, is_pat=False):
    f.write('%s:\n' % ('_' + song.name))
    for it in song.items:
        if it[0] == 'n':
            st, led, d = it[1:]
            assert 1 <= d <= 255 and led in (0, 1, 2)
            v = st | (led << 14)
            f.write('\t.db 0x%02x, 0x%02x, %d\n' % (v & 255, v >> 8, d))
        elif it[0] == 'loop':
            f.write('\t.db %d, 0xFC, %d\n' % (it[1], it[2]))
        elif it[0] == 'call':
            f.write('\t.db <(_%s), 0xFE, >(_%s)\n' % (it[1], it[1]))
        elif it[0] == 'ret':
            f.write('\t.db 0, 0xFD, 0\n')
    if not is_pat:
        f.write('\t.db 0xFF, 0xFF, 0\n')
    return 3 * (len(song.items) + (0 if is_pat else 1))

def build(typing):
    pats = {}
    for ch in sorted(set(PROG)):
        pats['g_' + ch] = groove_bar('g_' + ch, ch)
    pats['gf_E'] = groove_bar('gf_E', 'E', fill=True)
    for b in range(8):
        pats['l%d' % b] = lead_bar('l%d' % b, PROG[b], MELODY[b])
    songs = [song_basic(typing), song_ready(), song_set(), song_prompt(), song_go(), song_launch(pats),
             song_warp(pats), song_credits(pats), song_end(), song_bye()]
    return songs, pats

def write_song(songs, pats, path='song.h'):
    size = 0
    with open(path, 'w') as f:
        f.write('// generated by gen_music.py (do not edit)\nvoid song_data(void) __naked {\n__asm\n')
        for p in pats.values():
            size += asm_song(p, f, True)
        for s in songs:
            size += asm_song(s, f)
        f.write('__endasm;\n}\n')
    return size
