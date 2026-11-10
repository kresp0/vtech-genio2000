#!/usr/bin/env python3
"""Analyse a port-0x12 log (tests/lua/port12_log.lua): group bit-3 edges into tones (gap > 20 ms ends a tone) and print f/duration."""
import sys
def tones(path, gap=0.02):
    ev = []
    for l in open(path):
        if l.startswith('#'): continue
        t, v, pc = l.split()
        if pc.upper() == '0FB5': continue          # the reset-time OUT (12),0DEh is not part of any tone
        ev.append((float(t), int(v, 16) >> 3 & 1))
    # keep only transitions of bit 3
    edges = []; last = None
    for t, b in ev:
        if b != last: edges.append((t, b)); last = b
    rises = [t for t, b in edges if b == 1]
    out = []; cur = []
    for t in rises:
        if cur and t - cur[-1] > gap: out.append(cur); cur = []
        cur.append(t)
    if cur: out.append(cur)
    res = []
    for c in out:
        if len(c) < 3: continue
        per = (c[-1] - c[0]) / (len(c) - 1)
        res.append((c[0], 1 / per, len(c), c[-1] - c[0] + per))
    return res
if __name__ == '__main__':
    for p in sys.argv[1:]:
        for t0, f, n, d in tones(p): print('%s start=%.4f f=%.2f Hz periods=%d dur=%.4f s' % (p, t0, f, n, d))
