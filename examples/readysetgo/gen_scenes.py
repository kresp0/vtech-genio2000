"""scenes.h: the pictures, as event streams for the engine.

A scene is a list of steps (time in song units, 80 cells). A cell is a ROM character code or ('A', bitmap) / ('B', bitmap):
a 5x8 picture that the encoder places in one of the CGRAM glyphs 0-3 (A) or 4-7 (B). Each step becomes one record:
[runs][count, DDRAM address command, characters...]...[index of glyphs 0-3][index of glyphs 4-7][frames to wait].
The wait is found by simulating the engine's frame lengths exactly (gen_engine constants).
"""
import math, random
from gen_engine import FRAME_ITERS, FIRE_ITERS, MQ_ITERS, UNIT_ITERS, CLOCK, T_ITER, UNIT_S
from gen_music import SIXT, BEAT, BAR

SP = 0x20
MAP4 = [0, 1, 2, 3, 8, 9, 10, 11, 12, 13, 14, 15, 24, 25, 26, 27, 28, 29, 30, 31,
        64, 65, 66, 67, 72, 73, 74, 75, 76, 77, 78, 79, 88, 89, 90, 91, 92, 93, 94, 95,
        4, 5, 6, 7, 16, 17, 18, 19, 20, 21, 22, 23, 32, 33, 34, 35, 36, 37, 38, 39,
        68, 69, 70, 71, 80, 81, 82, 83, 84, 85, 86, 87, 96, 97, 98, 99, 100, 101, 102, 103]
ADDR_CELL = {a: i for i, a in enumerate(MAP4)}
STEP = 40                                   # default step: 40 units = 53 ms (18.7 steps/s)

def blank():
    return [SP] * 80

def text(cells, r, c, s):
    for i, ch in enumerate(s):
        if 0 <= c + i < 20:
            cells[r * 20 + c + i] = ch if isinstance(ch, int) else ord(ch)

def bm(rows):
    """8 strings of 5 chars ('#' = dot on) -> tuple of 8 row bytes"""
    rows = list(rows) + ['.....'] * (8 - len(rows))
    return tuple(int(r.replace('#', '1').replace('.', '0'), 2) for r in rows)

FULL = (31,) * 8
EMPTY = (0,) * 8

# ---------------------------------------------------------------- big letters: 3 x 8 half-cells
BIG = {
    'R': ['##.', '#.#', '#.#', '##.', '##.', '#.#', '#.#', '#.#'],
    'E': ['###', '#..', '#..', '##.', '#..', '#..', '#..', '###'],
    'A': ['.#.', '#.#', '#.#', '#.#', '###', '#.#', '#.#', '#.#'],
    'D': ['##.', '#.#', '#.#', '#.#', '#.#', '#.#', '#.#', '##.'],
    'Y': ['#.#', '#.#', '#.#', '.#.', '.#.', '.#.', '.#.', '.#.'],
    'S': ['.##', '#..', '#..', '.#.', '.#.', '..#', '..#', '##.'],
    'T': ['###', '.#.', '.#.', '.#.', '.#.', '.#.', '.#.', '.#.'],
    'G': ['.##', '#..', '#..', '#..', '#.#', '#.#', '#.#', '.##'],
    'O': ['.#.', '#.#', '#.#', '#.#', '#.#', '#.#', '#.#', '.#.'],
    '!': ['#', '#', '#', '#', '#', '#', '.', '#'],
}

def big_canvas(word, x0=0, dy=None):
    """20 x 8 half-cell canvas; dy: per-letter vertical offset in half-cells (positive = down)"""
    cv = [[0] * 20 for _ in range(8)]
    x = x0
    for k, ch in enumerate(word):
        g = BIG[ch]
        oy = dy[k] if dy else 0
        for y in range(8):
            yy = y + oy
            if 0 <= yy < 8:
                for i, p in enumerate(g[y]):
                    if p == '#' and 0 <= x + i < 20:
                        cv[yy][x + i] = 1
        x += len(g[0]) + 1
    return cv

def big_style(kind, k=0):
    """bitmaps of the four half-cell glyphs (full, top, bottom, empty)"""
    top, bot = tuple(31 if y < 4 else 0 for y in range(8)), tuple(31 if y >= 4 else 0 for y in range(8))
    if kind == 'solid':
        return FULL, top, bot, EMPTY
    if kind == 'inverse':
        return EMPTY, bot, top, FULL
    if kind == 'scan':                      # one dark scan line at row k
        f = lambda g: tuple(0 if y == k else v for y, v in enumerate(g))
        return f(FULL), f(top), f(bot), EMPTY
    if kind == 'charge':                    # dotted, then filled from the bottom of every cell up to level k (0-8)
        f = lambda g: tuple(v if (y % 2 == 0 or y >= 8 - k) else 0 for y, v in enumerate(g))
        return f(FULL), f(top), f(bot), EMPTY
    raise ValueError(kind)

def big_cells(cells, cv, style, rows=range(4), bg=True):
    gf, gt, gb, ge = style
    for r in rows:
        for c in range(20):
            t, b = cv[2 * r][c], cv[2 * r + 1][c]
            key = 'F' if t and b else 'T' if t else 'B' if b else 'E'
            if key == 'E' and not bg:
                continue
            cells[r * 20 + c] = ('A', {'F': gf, 'T': gt, 'B': gb, 'E': ge}[key], key)

# ---------------------------------------------------------------- sprites on the B glyphs, pixel-smooth
SHIP = ['##....', '#####.', '.#####', '#####.', '##....']

def sprite(cells, spr, x, y, half='B', group=0):
    """draw a sprite with its top-left pixel at (x, y) of the 100 x 32 screen; sprites of one group share glyphs"""
    w = len(spr[0])
    for cy in range(y // 8, (y + len(spr) - 1) // 8 + 1):
        for cx in range(x // 5, (x + w - 1) // 5 + 1):
            if not (0 <= cx < 20 and 0 <= cy < 4):
                continue
            rows = []
            for py in range(8):
                v = 0
                for px in range(5):
                    sx, sy = cx * 5 + px - x, cy * 8 + py - y
                    if 0 <= sy < len(spr) and 0 <= sx < w and spr[sy][sx] == '#':
                        v |= 16 >> px
                rows.append(v)
            rows = tuple(rows)
            if any(rows):
                cells[cy * 20 + cx] = (half, rows, (group, cx - x // 5, cy - y // 8))

# ---------------------------------------------------------------- encoder
class Halves:
    def __init__(s):
        s.data = []
        s.index = {}
    def get(s, b32):
        b32 = tuple(b32)
        if b32 not in s.index:
            s.index[b32] = len(s.data)
            s.data.append(b32)
        assert len(s.data) <= 256
        return s.index[b32]

HALVES = Halves()

class Slots:
    """keeps glyph contents stable between steps, so unchanged halves stay identical"""
    def __init__(s):
        s.slots = {'A': [None] * 4, 'B': [None] * 4}
    def assign(s, half, need, where):
        """need: list of (key, bitmap, preferred slot or None); a key keeps its glyph while its picture changes"""
        cur = s.slots[half]
        pic = {}
        for key, g, _ in need:
            if pic.setdefault(key, g) != g:
                raise SystemExit('%s: key %r has two pictures' % (where, key))
        if len(pic) > 4:
            raise SystemExit('%s: %d glyphs needed in half %s' % (where, len(pic), half))
        keys = [c[0] if c else None for c in cur]
        free = [i for i in range(4) if keys[i] not in pic]
        for key, g, pref in need:
            if key in keys:
                continue
            k = pref if pref in free else free[0]
            free.remove(k)
            keys[k] = key
        for i in range(4):
            if keys[i] in pic:
                cur[i] = (keys[i], pic[keys[i]])
        return {key: keys.index(key) + (0 if half == 'A' else 4) for key in pic}
    def bytes(s, half):
        out = []
        for c in s.slots[half]:
            out += list(c[1] if c else EMPTY)
        return out

def runs_of(prev, cur):
    """DDRAM runs (address, [codes]) that turn prev into cur; prev None = write everything"""
    changed = sorted(MAP4[i] for i in range(80) if cur[i] is not None and (prev is None or prev[i] != cur[i]))
    runs = []
    for a in changed:
        if runs:
            ra, codes = runs[-1]
            last = ra + len(codes) - 1
            if a == last + 1:
                codes.append(cur[ADDR_CELL[a]])
                continue
            if a == last + 2 and (a // 64) == (last // 64) and (last + 1) in ADDR_CELL and cur[ADDR_CELL[last + 1]] is not None:
                codes += [cur[ADDR_CELL[last + 1]], cur[ADDR_CELL[a]]]
                continue
        runs.append((a, [cur[ADDR_CELL[a]]]))
    out = []
    for a, codes in runs:                      # a run holds at most 255 characters
        out.append((a, codes))
    return out

def iters_of_fire(runs):
    return FIRE_ITERS + sum(2 + len(c) for _, c in runs)

class Segment:
    """cells set to None belong to the marquee (bottom row) and are never written by the stream"""
    def __init__(s, name, steps, song_units, kmask=0, mqc0=0xFFFF, mqper=1, mq_start=False):
        s.name, s.steps, s.song_units, s.kmask = name, steps, song_units, kmask
        s.mqc0, s.mqper, s.mq_start = mqc0, mqper, mq_start

class Clock:
    """frame-by-frame timing of the engine: a frame is FRAME_ITERS iterations, plus a fired record, plus a marquee step"""
    def __init__(s, mqc0, mqper):
        s.it, s.mqc, s.mqper, s.mq_steps = 0, mqc0, mqper, 0
    def frame(s, fire=0):
        """runs one frame; returns the iteration index of its EVCHK"""
        e = s.it + FRAME_ITERS - 3
        s.it += FRAME_ITERS + fire
        s.mqc = (s.mqc - 1) & 0xFFFF
        if s.mqc == 0:
            s.it += MQ_ITERS
            s.mqc = s.mqper
            s.mq_steps += 1
        return e

def encode(seg):
    """-> list of records (runs, ia, ib, wait) plus a terminal hold; also the timing report"""
    slots = Slots()
    pend = []                                   # (t in iterations, runs, ia, ib)
    prev = None
    end_it = seg.song_units * UNIT_ITERS
    for k, (t, cells) in enumerate(seg.steps):
        t_it = t * UNIT_ITERS
        if t_it >= end_it:
            break
        need = {'A': [], 'B': []}
        for i, c in enumerate(cells):
            if isinstance(c, tuple):
                p = prev[i] if prev else None
                base = 0 if c[0] == 'A' else 4
                key = c[2] if len(c) > 2 else c[1]
                need[c[0]].append((key, c[1], p - base if p is not None and base <= p < base + 4 else None))
        codes = []
        maps = {h: slots.assign(h, need[h], '%s step %d' % (seg.name, k)) for h in 'AB'}
        for c in cells:
            codes.append(maps[c[0]][c[2] if len(c) > 2 else c[1]] if isinstance(c, tuple) else c)
        ia, ib = HALVES.get(slots.bytes('A')), HALVES.get(slots.bytes('B'))
        runs = runs_of(prev, codes)
        if pend and not runs and ia == pend[-1][2] and ib == pend[-1][3]:
            continue
        pend.append((t_it, runs, ia, ib))
        prev = [c if c is not None else (prev[i] if prev else None) for i, c in enumerate(codes)]
    # timing: record 0 fires in the first frame; each later one at the first EVCHK at or after its time
    clk = Clock(seg.mqc0, seg.mqper)
    recs, late = [], 0
    e = clk.frame(iters_of_fire(pend[0][1]))
    recs.append([pend[0][1], pend[0][2], pend[0][3], None, e])
    for t_it, runs, ia, ib in pend[1:]:
        w = 1                                   # the next record fires in the w-th frame from here
        while clk.it + FRAME_ITERS - 3 < t_it:
            if w == 255:                        # filler record: nothing changes
                recs[-1][3] = 255
                e = clk.frame(FIRE_ITERS)
                recs.append([[], recs[-1][1], recs[-1][2], None, e])
                w = 1
                continue
            clk.frame()
            w += 1
        recs[-1][3] = w
        e = clk.frame(iters_of_fire(runs))
        late = max(late, e - t_it)
        recs.append([runs, ia, ib, None, e])
    while clk.it < end_it:
        clk.frame()
    recs[-1][3] = 0                             # -> hold
    seg.mq_steps = clk.mq_steps
    return recs, late

def emit(seg, f):
    recs, late = encode(seg)
    size = 0
    lab = 'ev_' + seg.name
    f.write('%s:\n' % lab)
    for runs, ia, ib, w, e in recs:
        b = [len(runs)]
        for a, codes in runs:
            assert 1 <= len(codes) <= 255 and all(0 <= c <= 255 for c in codes)
            b += [len(codes), 0x80 | a] + codes
        assert len(runs) <= 255
        b += [ia, ib, w]
        f.write('\t.db %s\n' % ','.join(str(v) for v in b))
        size += len(b)
    # terminal hold: wait 255 frames, then jump back to that wait
    f.write('\t.dw %s_h\n%s_h:\n\t.db 0,%d,%d,255\n\t.db 0,%d,%d,0\n\t.dw %s_h\n' % (lab, lab, ia, ib, ia, ib, lab))
    size += 2 + 4 + 6
    first = recs[0]
    return dict(name=seg.name, ev=lab, cga=first[1], cgb=first[2], kmask=seg.kmask, size=size, recs=len(recs),
                late_ms=late * T_ITER / CLOCK * 1000)

# ---------------------------------------------------------------- scenes
U = lambda sec: int(round(sec / UNIT_S))

CURSOR_ON = FULL
CURSOR_OFF = bm(['.....'] * 7 + ['#####'])
TYPED = 'run'

def typing_times():
    """(unit, key) of the keystrokes of the BASIC scene"""
    rnd = random.Random(7)
    t = U(1.6)
    out = []
    for ch in TYPED:
        out.append((t, ch))
        t += U(0.17 + rnd.random() * 0.12)
    out.append((t + U(0.35), '\n'))
    return out

def scene_basic(song_units):
    steps = []
    keys = typing_times()
    blink = U(0.4)
    t = 0
    while t < song_units:
        typed = [k for u, k in keys if u <= t]
        last = max([u for u, k in keys if u <= t], default=-10 ** 6)
        cells = blank()
        text(cells, 0, 0, 'READY')
        line = ''.join(k for k in typed if k != '\n')
        text(cells, 1, 0, line)
        if '\n' in typed:
            cur = (2, 0)
        else:
            cur = (1, len(line))
        solid = t - last < U(0.5) or ((t // blink) % 2 == 0)
        cells[cur[0] * 20 + cur[1]] = ('A', CURSOR_ON if solid else CURSOR_OFF, 'cur')
        steps.append((t, cells))
        nexts = [u for u, k in keys if u > t] + [(t // blink + 1) * blink]
        t = min(nexts)
    return steps

READY_X = [0, 4, 8, 12, 16]

def scene_ready():
    steps = []
    hits = [k * 2 * SIXT for k in range(5)]
    for t in range(0, 2 * BAR, 20):
        dy = []
        for k, h in enumerate(hits):
            if t < h:
                dy.append(-99)
            else:
                dy.append(min(0, -8 + 2 * ((t - h) // 20)))   # drops in 4 steps of 2 half-cells
        cv = big_canvas('READY', 0, dy)
        if t < 6 * 2 * SIXT:
            st = big_style('solid')
        elif t < BAR + 4 * SIXT:
            st = big_style('scan', ((t - 6 * 2 * SIXT) // 10) % 8)
        else:
            beat = (t - BAR - 4 * SIXT) // SIXT
            st = big_style('inverse' if beat % 4 == 0 and (t // 20) % 2 == 0 else 'solid')
        cells = blank()
        big_cells(cells, cv, st)
        steps.append((t, cells))
    return steps

def gauge(level):
    """bitmaps for the 4 cells (top to bottom) of a 32-pixel gauge"""
    out = []
    for r in range(4):
        fill = max(0, min(8, level - (3 - r) * 8))
        out.append(tuple(31 if y >= 8 - fill else 17 for y in range(8)))
    return out

def scene_set():
    steps = []
    end = 4 * BAR
    charge_end = 3 * BAR
    for t in range(0, end, STEP):
        cv = big_canvas('SET', 0)
        cells = blank()
        lvl = min(8, t * 9 // charge_end)
        st = big_style('charge', lvl) if t < charge_end else (big_style('solid') if (t // STEP) % 2 else big_style('scan', (t // 10) % 8))
        big_cells(cells, cv, st)
        g = gauge(min(32, 2 * (t * 17 // charge_end)))
        for r in range(4):
            cells[r * 20 + 12] = ('B', g[r], r)
            cells[r * 20 + 13] = ('B', g[r], r)
        pct = min(100, t * 100 // charge_end)
        text(cells, 0, 15, 'POWER')
        text(cells, 1, 15, '%4d%%' % pct)
        if t >= charge_end:
            k = (t - charge_end) // BEAT
            text(cells, 3, 15, ['  T-3', '  T-2', '  T-1', ' SET!'][min(k, 3)])
        steps.append((t, cells))
    return steps

COMET = ['##', '##']

def scene_prompt():
    steps = []
    for t in range(0, 2 * BAR, STEP):
        cells = blank()
        text(cells, 0, 0, ' ALL SHIPS ARE SET! ')
        text(cells, 2, 0, 'PRESS ANY KEY TO GO!')
        text(cells, 3, 0, ' PRESS OFF TO QUIT')
        if (t // U(0.4)) % 2:
            text(cells, 2, 17, '   ')
        ph = (t * 2 * 98 // (2 * BAR))           # ping-pong comet on the rail of row 1
        x = ph if ph < 98 else 196 - ph
        for c in range(20):
            cells[20 + c] = 0x2D if c % 2 == 0 else SP
        sprite(cells, COMET, x, 11)
        steps.append((t, cells))
    return steps

def scene_go():
    steps = []
    for t in range(0, BAR, 20):
        if t < 2 * BEAT:
            st = big_style('inverse' if (t // 20) % 2 else 'solid')
            dy = [0, 0, 0]
        elif t < 3 * BEAT:
            st = big_style('solid')
            up = (t - 2 * BEAT) // 20
            dy = [-up * 2, -max(0, up * 2 - 2), -max(0, up * 2 - 4)]
        else:
            st = big_style('solid')
            dy = [-99] * 3
        cells = blank()
        big_cells(cells, big_canvas('GO!', 5, dy), st)
        steps.append((t, cells))
    return steps

def starfield(seed, n):
    rnd = random.Random(seed)
    return [(rnd.randrange(100), rnd.randrange(4), rnd.choice((1, 2, 3))) for _ in range(n)]

STAR_CH = {1: 0x2E, 2: 0xB0, 3: 0xB1}

def draw_stars(cells, stars, t, speed, skip=()):
    for x0, r, layer in stars:
        x = int(x0 - t * speed * layer) % 100
        c = x // 5
        if (r, c) in skip:
            continue
        if cells[r * 20 + c] == SP:
            cells[r * 20 + c] = STAR_CH[layer]

MQ_TEXT = 'RUNS ON:  Genio 2000 | Genius 4000 | Genius LEADER 4000 Quadro | Genius LEADER 4004 Quadro L | PreComputer Power Pad'
MQ_BLANK = 4 * BAR + 8 * 60                     # launch: the mothership has scrolled away, row 3 goes blank
MQ_FREE = MQ_BLANK + 150                        # from here the stream leaves row 3 to the marquee
MQ_FRAMES0 = (MQ_FREE + 150) * UNIT_ITERS // FRAME_ITERS     # the first marquee step comes at least this late
MQ_PER = 47                                     # frames per character, about 7.5 characters per second

FORMATION = [(0, 0), (10, 1), (0, 2)]           # (x offset, row): same phase, so all three share two glyphs

MOTHER = ['/####\\',
          '|##[  ',
          '|##[  ',
          '\\####/']

def door(k):
    """bay door cells (top, bottom) open by k of 8 rows"""
    top = tuple(0b00011 if y < 8 - k else 0 for y in range(8))
    bot = tuple(0b00011 if y >= k else 0 for y in range(8))
    return top, bot

def scene_launch():
    steps = []
    stars = starfield(11, 6)
    launches = [(BAR + 0, 1), (2 * BAR, 2), (3 * BAR, 1)]
    for t in range(0, 8 * BAR, STEP):
        cells = blank()
        pan = max(0, (t - 4 * BAR) // 60)                       # the mothership scrolls away
        if pan < 8:
            for r in range(4):
                text(cells, r, -pan, MOTHER[r])
            k = min(8, max(0, (t - BAR + 4 * SIXT) // 12))
            dt, db = door(k)
            if 5 - pan >= 0:
                cells[1 * 20 + 5 - pan] = ('A', dt, 'dt')
                cells[2 * 20 + 5 - pan] = ('A', db, 'db')
            # glowing engine lights at the back of the hull
            if pan == 0:
                for r in (1, 2):
                    cells[r * 20 + 0] = 0x7C if (t // BEAT) % 2 else 0x3C
            parked = [(1, 4), (2, 4)]
            for n, (lt, row) in enumerate(launches):
                if t < lt - 2 * BEAT and n != 2 and 4 - pan >= 0:
                    text(cells, row, 4 - pan, [0xF6])
                if n == 2 and BAR + BEAT * 2 <= t < lt and 4 - pan >= 0:
                    text(cells, 1, 4 - pan, [0xF6])
        draw_stars(cells, stars, t, 0.004 + (0.02 if t > 4 * BAR else 0), skip=[(r, c) for r in range(4) for c in range(7 - pan)])
        for n, (lt, row) in enumerate(launches):
            if lt <= t < lt + BAR:
                s = (t - lt) / BAR
                x = int(20 + 95 * s * s)
                if x < 100:
                    sprite(cells, SHIP, x, row * 8 + 1, group=n)
                    c = x // 5 - 1
                    if c >= 0 and cells[row * 20 + c] in (SP, 0x2E, 0xB0, 0xB1):
                        cells[row * 20 + c] = 0x2D
        if t >= 4 * BAR + BAR // 2:                            # formation enters from the left
            s = min(1.0, (t - 4 * BAR - BAR // 2) / (1.5 * BAR))
            xl = int(-10 + 50 * (1 - (1 - s) ** 2))
            bob = int(round(1 + math.sin(t / 60.0)))
            for dx, row in FORMATION:
                sprite(cells, SHIP, xl + dx, row * 8 + bob, group='f')
                c = (xl + dx) // 5 - 1
                r = row
                if 0 <= c < 20 and cells[r * 20 + c] in (SP, 0x2E, 0xB0, 0xB1):
                    cells[r * 20 + c] = 0x2D
        if t >= MQ_BLANK:
            for c in range(20):
                cells[60 + c] = None if t >= MQ_FREE else SP
        steps.append((t, cells))
    return steps

def streak_glyphs(t, speed=1):
    """4 background glyphs forming a 20-pixel ring per pixel row; each row slides at its own speed"""
    pat = ['11110000000000000000', '00000000111000000000', '11111100000000000000', '00000000000011000000',
           '00011111000000000000', '00000000000001111100', '01110000000000000000', '00000000011111110000']
    sp = [3, 1, 4, 2, 4, 1, 3, 2]
    rows = []
    for y in range(8):
        s = (t * sp[y] * speed) % 20
        rows.append(pat[y][s:] + pat[y][:s])
    return [tuple(int(rows[y][5 * g:5 * g + 5], 2) for y in range(8)) for g in range(4)]

def scene_warp():
    steps = []
    for t in range(0, 8 * BAR, STEP):
        k = t // STEP
        cells = blank()
        flash = 4 * BAR - 2 * SIXT <= t < 4 * BAR + 2 * SIXT
        if flash:
            for i in range(60):
                cells[i] = ('A', FULL if (t // 20) % 2 == 0 else EMPTY, (i % 20 + i // 20) % 4)
        else:
            g = streak_glyphs(k, 1 if t < 4 * BAR else 2)
            for r in range(3):
                for c in range(20):
                    cells[r * 20 + c] = ('A', g[(c + r) % 4], (c + r) % 4)
            bob = int(round(1 + math.sin(k / 3.0)))
            leave = max(0, t - 7 * BAR)
            x = 40 + int(leave * leave / 600)
            for dx, row in FORMATION:
                if x + dx < 100:
                    sprite(cells, SHIP, x + dx, row * 8 + bob, group='f')
        for c in range(20):
            cells[60 + c] = None
        steps.append((t, cells))
    return steps

PAGES = [
    ['READY, SET, GO!', '', 'a 1-bit demo for', 'the 4x20 LCD family'],
    ['3 ships, 8 glyphs,', '1 speaker bit,', '1 LED, 6.13 MHz,', 'all in 16 KiB.'],
    ['Press OFF at any', 'time to switch off.', '', 'Keys: any one.'],
    ['', 'Thanks for playing!'],
]

def scene_credits():
    steps = []
    page_len = 2 * BAR
    for p, page in enumerate(PAGES):
        t0 = p * page_len
        allc = [(r, c, ch) for r, line in enumerate(page) for c, ch in enumerate(line)]
        n = 0
        t = t0
        while t < t0 + page_len:
            cells = blank()
            shown = allc[:n]
            for r, c, ch in shown:
                text(cells, r, c, ch)
            if n < len(allc):
                r, c, _ = allc[n]
                cells[r * 20 + c] = ('A', FULL, 'cur')
            elif (t // U(0.4)) % 2 == 0:
                r, c, _ = allc[-1]
                if c + 1 < 20:
                    cells[r * 20 + c + 1] = ('A', FULL, 'cur')
            steps.append((t, cells))
            n = min(len(allc), n + 6)
            t += STEP
    t = len(PAGES) * page_len
    while t < 9 * BAR:
        cells = blank()
        text(cells, 1, 2, 'BREAK IN 10')
        steps.append((t, cells))
        t += BAR
    return steps

def scene_end():
    steps = []
    blink = U(0.4)
    for t in range(0, 2 * BAR, blink):
        cells = blank()
        text(cells, 0, 0, 'READY')
        cells[20] = ('A', CURSOR_ON if (t // blink) % 2 == 0 else CURSOR_OFF, 'cur')
        text(cells, 3, 0, 'KEY:AGAIN  OFF:BYE')
        steps.append((t, cells))
    return steps

def scene_bye():
    cells = blank()
    text(cells, 1, 3, 'SEE YOU LATER!')
    text(cells, 2, 2, 'POWERING OFF...')
    return [(0, cells)]

def write_scenes(songs, pats, path='scenes.h'):
    from gen_music import units
    su = {s.name: units(s, pats) for s in songs}
    segs = [
        Segment('basic', scene_basic(su['song_basic']), su['song_basic']),
        Segment('ready', scene_ready(), su['song_ready']),
        Segment('set', scene_set(), su['song_set']),
        Segment('prompt', scene_prompt(), su['song_prompt'], kmask=0xFF),
        Segment('go', scene_go(), su['song_go']),
        Segment('launch', scene_launch(), su['song_launch'], mqc0=MQ_FRAMES0, mqper=MQ_PER, mq_start=True),
        Segment('warp', scene_warp(), su['song_warp'], mqc0=MQ_PER, mqper=MQ_PER),
        Segment('credits', scene_credits(), su['song_credits']),
        Segment('end', scene_end(), su['song_end'], kmask=0xFF),
        Segment('bye', scene_bye(), su['song_bye']),
    ]
    infos = []
    with open(path, 'w') as f:
        f.write('// generated by gen_scenes.py (do not edit): event streams, glyph halves and the segment table\n')
        f.write('void scene_data(void) __naked {\n__asm\n')
        for s in segs:
            infos.append(emit(s, f))
        f.write('_cgdata::\n')
        for h in HALVES.data:
            f.write('\t.db %s\n' % ','.join(str(v) for v in h))
        # the marquee text: blank, the names, then blank for as many steps as launch + warp take
        steps = sum(s.mq_steps for s in segs)
        txt = MQ_TEXT.encode('ascii').replace(b'|', bytes([0xCD]))
        txt = b' ' * 20 + txt + b' ' * max(20, steps + 20 - 20 - len(txt))
        assert steps + 20 <= len(txt)
        f.write('_mq_str:\n')
        for i in range(0, len(txt), 32):
            f.write('\t.db %s\n' % ','.join(str(v) for v in txt[i:i + 32]))
        f.write('_segs::\n')
        for s, inf in zip(segs, infos):
            f.write('\t.dw _song_%s, %s, _cgdata+%d, _cgdata+%d\n\t.db %d\n\t.dw %d, %d, %s\n' % (s.name, inf['ev'], 32 * inf['cga'], 32 * inf['cgb'],
                    inf['kmask'], s.mqc0, s.mqper, '_mq_str' if s.mq_start else '0'))
        f.write('__endasm;\n}\n')
        f.write('#define N_SEGS %d\n' % len(segs))
        for k, s in enumerate(segs):
            f.write('#define SEG_%s %d\n' % (s.name.upper(), k))
    return infos, len(HALVES.data) * 32, su, steps, len(txt)
