#!/usr/bin/env python3
"""Replays the event streams of scenes.h the way the engine does and compares the LCD it predicts with MAME snapshots.

usage: check_snaps.py <snapshot dir> <segment>:<seconds into the segment>:<png> ...
The replay knows only the stream bytes and the frame lengths of gen_engine, not gen_scenes, so it checks the encoder too.
The CGROM is needed to draw ROM characters: set GENIO_CGROM to your own genio2000_cgrom_reconstructed.bin (not in this repository).
"""
import os, re, sys, struct, zlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from gen_engine import FRAME_ITERS, FIRE_ITERS, MQ_ITERS, T_ITER, CLOCK
from gen_scenes import MAP4

HERE = os.path.dirname(os.path.abspath(__file__))

def parse(path):
    """bytes of the scene_data block, label -> offset, and the 'cgdata' offset"""
    data, labels, fix = [], {}, []
    for line in open(path):
        line = line.strip()
        m = re.match(r'^(\w+):+$', line)
        if m:
            labels[m.group(1)] = len(data)
            continue
        if line.startswith('.db'):
            data += [int(v, 0) for v in line[3:].split(',')]
        elif line.startswith('.dw'):
            for v in line[3:].split(','):
                fix.append((len(data), v.strip()))
                data += [0, 0]
    return data, labels, fix

def segtable(path, labels):
    """ev label -> (cga, cgb, mqc0, mqper, marquee starts here) from the _segs table of scenes.h"""
    lines = open(path).read().split('_segs::')[1].split('\n')
    out = {}
    for i, l in enumerate(lines):
        m = re.search(r'(ev_\w+), _cgdata\+(\d+), _cgdata\+(\d+)', l)
        if m:
            q = re.search(r'\.dw (\d+), (\d+), (\w+)', lines[i + 2])
            out[m.group(1)] = (labels['_cgdata'] + int(m.group(2)), labels['_cgdata'] + int(m.group(3)),
                               int(q.group(1)), int(q.group(2)), q.group(3) != '0')
    return out

def play(data, labels, seg_label, seg, seconds, mqp=0):
    """DDRAM (dict addr -> code), CGRAM (64 bytes) and marquee position at `seconds` after the segment starts"""
    cga0, cgb0, mqc, mqper, mqstart = seg
    if mqstart:
        mqp = 0
    cg, mq = labels['_cgdata'], labels['_mq_str']
    limit = seconds * CLOCK / T_ITER
    ddram, p, it = {}, labels[seg_label], 0
    cgram_ptr = (cga0, cgb0)
    cgram = data[cga0:cga0 + 32] + data[cgb0:cgb0 + 32]
    evw = 1
    while it + FRAME_ITERS <= limit:
        # frame: CMD + 64 CGRAM data (from the pointers of the previous record) + EVCHK, then the marquee countdown
        cgram = data[cgram_ptr[0]:cgram_ptr[0] + 32] + data[cgram_ptr[1]:cgram_ptr[1] + 32]
        it += FRAME_ITERS
        evw = (evw - 1) & 255
        while evw == 0:
            n = data[p]; p += 1
            it += FIRE_ITERS
            for _ in range(n):
                cnt, cmd = data[p], data[p + 1]; p += 2
                for i in range(cnt):
                    ddram[(cmd & 0x7F) + i] = data[p + i]
                p += cnt
                it += 2 + cnt
            ia, ib, evw = data[p], data[p + 1], data[p + 2]; p += 3
            cgram_ptr = (cg + 32 * ia, cg + 32 * ib)
            if evw == 0:
                p = data[p] | data[p + 1] << 8          # jump (resolved offsets)
                it += 1
        mqc = (mqc - 1) & 0xFFFF
        if mqc == 0:
            for c in range(20):
                ddram[MAP4[60 + c]] = data[mq + mqp + c]
            mqp += 1
            mqc = mqper
            it += MQ_ITERS
    return ddram, cgram, mqp

def render(ddram, cgram, rom):
    """120 x 40 picture like MAME's native snapshot: 6 x 10 pixels per cell (5 x 8 dots)"""
    img = [[0] * 120 for _ in range(40)]
    for i in range(80):
        code = ddram.get(MAP4[i], 0x20)
        r, c = divmod(i, 20)
        for y in range(8):
            row = cgram[(code & 7) * 8 + y] if code < 16 else rom[code * 16 + y]
            for x in range(5):
                if row & (16 >> x):
                    img[r * 10 + y + (y == 7)][c * 6 + x] = 1       # MAME draws the detached eighth row one line lower
    return img

def read_png(path):
    raw = open(path, 'rb').read()
    pos, w, h, idat = 8, 0, 0, b''
    while pos < len(raw):
        ln, typ = struct.unpack('>I4s', raw[pos:pos + 8])
        body = raw[pos + 8:pos + 8 + ln]
        if typ == b'IHDR':
            w, h = struct.unpack('>II', body[:8])
        elif typ == b'IDAT':
            idat += body
        pos += 12 + ln
    px = zlib.decompress(idat)
    stride = w * 3 + 1
    rows, prev = [], bytearray(w * 3)
    for y in range(h):
        f, line = px[y * stride], bytearray(px[y * stride + 1:(y + 1) * stride])
        for i in range(len(line)):
            a = line[i - 3] if i >= 3 else 0
            b, c = prev[i], prev[i - 3] if i >= 3 else 0
            if f == 1: line[i] = (line[i] + a) & 255
            elif f == 2: line[i] = (line[i] + b) & 255
            elif f == 3: line[i] = (line[i] + (a + b) // 2) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append([sum(line[x * 3:x * 3 + 3]) for x in range(w)])
        prev = line
    return rows

def main():
    snapdir = sys.argv[1]
    data, labels, fix = parse(os.path.join(HERE, '..', 'scenes.h'))
    for off, name in fix:
        if name in labels:                      # stream jumps; the segment table is read separately
            v = labels[name]
            data[off], data[off + 1] = v & 255, v >> 8
    rom = open(os.environ['GENIO_CGROM'], 'rb').read()
    tab = segtable(os.path.join(HERE, '..', 'scenes.h'), labels)
    bad = 0
    for arg in sys.argv[2:]:
        seg, sec, png = arg.split(':')
        lab = 'ev_' + seg
        dd, cgr, _ = play(data, labels, lab, tab[lab], float(sec))
        want = render(dd, cgr, rom)
        got = read_png(os.path.join(snapdir, png))
        thr = 340                               # between MAME's dot (~263) and background (~420) shades
        diff = 0
        for y in range(40):
            for x in range(120):
                if (got[y][x] < thr) != bool(want[y][x]) and (x % 6) < 5:
                    diff += 1
        print('%-28s %5d differing dots' % (arg, diff))
        if diff:
            bad += 1
            for r in range(4):
                print('   want ' + ''.join('%02x ' % dd.get(MAP4[r * 20 + c], 0x20) for c in range(20)))
    return 1 if bad else 0

if __name__ == '__main__':
    sys.exit(main())
