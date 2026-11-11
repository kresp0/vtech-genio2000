#!/usr/bin/env python3
"""Checks every snapshot of a run_test.sh run against the replayed event streams.
usage: check_run.py <run dir> <segment order, comma separated; a trailing '*' repeats the last one>"""
import os, re, sys
import check_snaps as c

def main():
    run, order = sys.argv[1], sys.argv[2].split(',')
    log = open(os.path.join(run, 'summary.txt')).read()
    ends = [float(x) for x in re.findall(r'segment end at ([\d.]+)', log)]
    snaps = [(int(n), float(t)) for n, t in re.findall(r'snap (\d+) at ([\d.]+)', log)]
    data, labels, fix = c.parse(os.path.join(c.HERE, '..', 'scenes.h'))
    for off, name in fix:
        if name in labels:
            data[off], data[off + 1] = labels[name] & 255, labels[name] >> 8
    tab = c.segtable(os.path.join(c.HERE, '..', 'scenes.h'), labels)
    rom = open(os.environ['GENIO_CGROM'], 'rb').read()
    # marquee position at the start of each segment of the run: replay the ones before it to their real end
    names = [order[min(k, len(order) - 1)].rstrip('*') for k in range(len(ends) + 1)]
    mq_at = [0]
    for k in range(len(ends)):
        start = ends[k - 1] if k else 0.065
        lab = 'ev_' + names[k]
        if tab[lab][2] != 0xFFFF:
            _, _, p = c.play(data, labels, lab, tab[lab], ends[k] - start, mq_at[-1])
        else:
            p = mq_at[-1]
        mq_at.append(p)
    bad = 0
    for n, t in snaps:
        k = sum(1 for e in ends if e <= t)
        name = order[min(k, len(order) - 1)].rstrip('*')
        start = ends[k - 1] if k else 0.065                    # the cartridge starts about 65 ms after power-on
        got = c.read_png(os.path.join(run, 'genio2000', '%04d.png' % (n - 1)))
        thr = 340                                            # between MAME's dot (~263) and background (~420) shades
        best = None
        # MAME draws once per video frame (+-6 ms); the replay ignores the T-states of fetch_note, so the real show
        # runs up to about 1 % behind it
        el = t - start
        lag = [i * 0.003 for i in range(-int((0.01 * el + 0.006) / 0.003), 3)]
        for dt in sorted(lag, key=abs):
            dd, cg, p = c.play(data, labels, 'ev_' + name, tab['ev_' + name], t - start + dt, mq_at[k])
            # the replay does not count the T-states of fetch_note (about 0.2 %): allow the marquee one step either way
            shifts = (0, -1, 1) if p > 0 and tab['ev_' + name][2] != 0xFFFF or (p > 0 and k and mq_at[k]) else (0,)
            for sh in shifts:
                if sh or p:
                    for col in range(20):
                        if p + sh > 0 and tab['ev_' + name][2] != 0xFFFF:
                            dd[c.MAP4[60 + col]] = data[labels['_mq_str'] + p - 1 + sh + col]
                w = c.render(dd, cg, rom)
                d = sum((got[y][x] < thr) != bool(w[y][x]) for y in range(40) for x in range(120) if x % 6 < 5)
                if best is None or d < best[0]:
                    best = (d, sh, dt)
            if best[0] == 0:
                break
        print('snap %2d  %6.2f s  %-8s +%5.2f s  %4d differing dots  (replay %+3.0f ms%s)' % (n, t, name, t - start, best[0], best[2] * 1000,
              ', marquee %+d step' % best[1] if best[1] else ''))
        best = best[0]
        bad += best > 0
    print('%d of %d snapshots differ' % (bad, len(snaps)))
    return 1 if bad else 0

if __name__ == '__main__':
    sys.exit(main())
