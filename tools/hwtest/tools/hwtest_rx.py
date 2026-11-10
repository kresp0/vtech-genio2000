#!/usr/bin/env python3
"""hwtest_rx - receiver and report generator for the Genio 2000 hardware test cartridge (hwtest). Genio -> PC only.

Live (9600 8N1, RX only; same wiring as the dumper: DB25 pin 2 -> CP2102 RXD, GND common, TXD not connected):
    python3 tools/hwtest_rx.py --port /dev/ttyUSB0
Offline (a capture saved by a previous run; the .tlog next to it carries the read timestamps used for clock / IRQ rate):
    python3 tools/hwtest_rx.py --analyze results/<stamp>/capture.bin

Output (never overwrites): results/<stamp>/  capture.bin  capture.tlog  results.json  REPORT.md  mem_C000_FFFF.bin
REPORT.md is rewritten after every stage, so cutting the power between stages loses nothing. Send that file (or its text) back.
Evidence class of everything in the report: HW (measured on the unit) unless a line says otherwise.
"""
import argparse, json, os, struct, sys, time, zlib
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(os.environ.get('GENIO_DUMPER_DIR', os.path.join(os.path.dirname(ROOT), 'dumper')), 'tools'))      # gframe.py lives in the dumper repository
import gframe as g

T_MEM, T_PORTS, T_WIN, T_CLK, T_IRQ, T_KEY, T_ANS, T_WRP = 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48
STAGES = 'ABCDEFGHIJKL'
STAGE_NAMES = {'A': 'entry state + RAM copy', 'B': 'IN ports 00..FF', 'C': 'CPU clock bursts', 'D': 'IRQ rate', 'E': 'LCD + LED questions',
               'F': 'keyboard matrix log', 'G': 'charset pages (photos)', 'H': 'port 03 <- 00..07', 'I': 'port 03 <- 80..8F',
               'J': 'port 03 <- 08..1F', 'K': 'cartridge /WR probe', 'L': 'port 03 <- 20 40 90 A0 C0'}
EXTRA_T = 6729            # T-states added per byte in clock burst 2 (CALL + gap_dly body), see hwtest.c
BAUD = 9600
ANSWERS = {1: ('all cells = code 00 show a solid block', 'S'), 2: ('rewriting CGRAM 0 changes ALL cells at once (live read)', 'S'),
           3: ('codes 0-7 show 8 different shapes', 'S'), 4: ('rewriting CGRAM changes everything at once', 'S'),
           5: ('codes 08-0F look the same as 00-07 (mirror)', 'S'), 6: ('a LED blinked 3 times (port 0x12 bit 5)', 'S')}
# vgl_key_map of the VGLDK (row = column-select bit position r, k = bit read on port 0x10; idx = r*8+k). Names are the US/DE layout labels used by VGLDK;
# the Spanish keyboard has the same matrix but other legends.
KEYMAP = ['TAB/AYUDA', 'BREAK/*', 'e', 'f', 'g', 'i', 'j', 'k', 'CAPS', '1', 'Q', 'A', 'Z', 'ALT', 'ESPACIO', 'INS',
          '2', '3', 'E', 'S', 'D', 'X', 'C', 'W', '4', '5', 'T', 'F', 'G', 'V', 'B', 'R', '6', '7', 'U', 'H', 'J', 'N', 'M', 'Y',
          '8', '9', 'O', 'K', 'L', ',', '.', 'I', '0', 'BORRAR', '=', ':', "'", '/', 'SHIFT', 'P', 'x', 'y', '<-', '->', 'ENTER', 'DEL', 'ESC', 'z']


def load_internal_crcs():
    """CRC-32 of the internal banks of every known ROM image -> label (unit 1 = reference ROM, unit 2 = second dumped unit)."""
    out = {}
    for fn, tag in (('genio2000_es_128k.bin', ''), ('genio2000_es_128k_unit2.bin', ' (unit 2)')):
        p = os.path.join(os.path.dirname(ROOT), 'rom', fn)
        if not os.path.exists(p): continue
        d = open(p, 'rb').read()
        for i in range(8): out.setdefault(g.crc32(d[i * 0x4000:(i + 1) * 0x4000]), (i, tag))
    return out


class Run:
    def __init__(self):
        self.frames = []          # (index_of_read, t, Frame)
        self.reads = []           # (t, bytes)
        self.rejects = 0
        self.start = None
        self.mem = {}
        self.ports = None
        self.win = {}
        self.clk = []             # (phase, read_index)
        self.irq = []             # (phase, count, db24[8], read_index, t, frame_bytes)
        self.keys = None
        self.wrp = None
        self.ans = {}
        self.stages = {}
        self.ended = False
        self.dec = g.ParmrkDecoder()

    def feed(self, t, data):
        self.reads.append((t, data))
        ri = len(self.reads) - 1
        for item in self.dec.feed(data):
            if item[0] == 'reject':
                if not (len(item[2]) > 100 and set(item[2]) == {0x55}): self.rejects += 1     # the clock bursts are deliberately unframed
                continue
            self.add(ri, t, item[1])

    def add(self, ri, t, f):
        self.frames.append((ri, t, f))
        p = f.payload
        if f.type == g.T_START and p and p[0] == 4:
            tool, build, sp, variant, flags, ireg = struct.unpack('<BHHBBB', p[:8])
            self.start = dict(tool=tool, build=build, sp=sp, variant=chr(variant), flags_at_entry=flags, i_reg=ireg, shadows=list(p[8:16]), session=f.session)
        elif f.type == T_MEM: self.mem[f.src] = p
        elif f.type == T_PORTS and len(p) == 768: self.ports = p
        elif f.type == T_WIN and len(p) == 85: self.win[p[0]] = p
        elif f.type == T_CLK: self.clk.append((p[0], ri, struct.unpack('<HH', p[1:5])))
        elif f.type == T_IRQ and len(p) == 13: self.irq.append((p[0], struct.unpack('<H', p[1:3])[0], list(p[3:11]), ri, t, len(f.raw) + 2, p[11], p[12]))
        elif f.type == T_KEY: self.keys = p
        elif f.type == T_WRP and len(p) == 19: self.wrp = p
        elif f.type == T_ANS: self.ans[p[0]] = chr(p[1]) if p[1] in (0x53, 0x4E, 0x0D) else '?'
        elif f.type == g.T_STAGE:
            k = STAGES[p[0]]
            if not p[1] or self.stages.get(k) != 'done': self.stages[k] = 'SKIPPED' if p[1] else 'done'     # a later boot that skips a stage does not erase an earlier result
        elif f.type == g.T_END: self.ended = True


def fit_rate(chunks):
    """least squares of cumulative byte count vs time -> (bytes/s, n). chunks = [(t, n)]"""
    if len(chunks) < 3: return None
    cum, xs, ys = 0, [], []
    for t, n in chunks:
        cum += n; xs.append(t); ys.append(cum)
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    return (sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx, cum) if sxx else None


def analyze_clock(r):
    out = {}
    begin = [c for c in r.clk if c[0] == 0]; end = [c for c in r.clk if c[0] == 1]
    if not begin or not end: return None
    a, b = begin[0][1], end[0][1]
    ch = [(t, len(d)) for (t, d) in r.reads[a + 1:b] if d and all(x == 0x55 for x in d)]
    bursts, cur = [], []
    for t, n in ch:
        if cur and t - cur[-1][0] > 0.2: bursts.append(cur); cur = []
        cur.append((t, n))
    if cur: bursts.append(cur)
    out['bursts_found'] = len(bursts)
    rates = [fit_rate(bu) for bu in bursts]
    out['bytes_per_burst'] = [sum(n for _, n in bu) for bu in bursts]
    out['byte_period_s'] = [None if x is None else 1.0 / x[0] for x in rates]
    if len(bursts) >= 2 and rates[0] and rates[1]:
        p1, p2 = 1.0 / rates[0][0], 1.0 / rates[1][0]
        if p2 > p1:
            f = EXTRA_T / (p2 - p1)
            out['cpu_clock_hz'] = f
            out['t_per_byte_burst1'] = p1 * f
            out['note'] = 'f = %d T / (period2 - period1); burst 1 byte = 10 bits x 642 T + C gap => expect ~6650 T' % EXTRA_T
    return out


def analyze_irq(r):
    """phases: 0 before the first EI, 2 progress marks (1,5,20,100 IRQs), 3 start of the timed window, 1 end of it."""
    if not r.irq: return None
    out = dict(frames=[dict(phase=x[0], count=x[1], db26=x[2][2] | (x[2][3] << 8), db00=x[6], db01=x[7]) for x in r.irq])
    out['max_count'] = max(x[1] for x in r.irq)
    out['reached_end'] = any(x[0] == 1 for x in r.irq)
    b = [x for x in r.irq if x[0] == 3]; e = [x for x in r.irq if x[0] == 1]
    if b and e:
        tb, te = b[0][4], e[0][4] - e[0][5] * 10.0 / BAUD
        dt = te - tb; n = e[0][1] - b[0][1]
        out.update(count=n, seconds=dt)
        if dt > 1: out['hz'] = n / dt
    return out


def decode_keys(p):
    ev = [p[i:i + 16] for i in range(0, len(p), 16)]
    rows, prev = [], ev[0]
    for n, cur in enumerate(ev[1:], 1):
        pr, rl = [], []
        for i in range(8):
            for port, off in ((0x10, 1), (0x11, 0)):
                a, b = prev[2 * i + off], cur[2 * i + off]
                for bit in range(8):
                    was, now = not (a >> bit) & 1, not (b >> bit) & 1
                    if was == now: continue
                    r_ = 7 - i
                    name = KEYMAP[r_ * 8 + bit] if port == 0x10 else 'P11.col%d.bit%d' % (r_, bit)
                    (pr if now else rl).append('%s [col%d,port%02X.b%d]' % (name, r_, port, bit))
        rows.append(dict(n=n, pressed=pr, released=rl, raw=cur.hex()))
        prev = cur
    return rows


def window_report(r, internal):
    rows = []
    for sel in sorted(r.win):
        p = r.win[sel]
        q = [struct.unpack('<I', p[1 + 4 * k:5 + 4 * k])[0] for k in range(4)]
        whole = q[0]
        for k in range(1, 4): whole = g.crc32_combine(whole, q[k], 0x1000)
        again = struct.unpack('<I', p[81:85])[0]
        head, mk1, mk2, tail = p[17:33], p[33:49], p[49:65], p[65:81]
        def qid(m): return m[2] if m[:2] == b'MQ' and m[3] == (~m[2] & 0xFF) else None
        kind = 'internal bank %d%s' % internal[whole] if whole in internal else ('FF' if set(head + mk1 + mk2 + tail) == {0xFF} else 'cartridge/other')
        rows.append(dict(sel='%02X' % sel, crc32='%08X' % whole, stable=(whole == again), kind=kind, quarter_8K_lo=qid(mk1), quarter_8K_hi=qid(mk2),
                         head=head.hex(), chunk_crc=['%08X' % x for x in q]))
    groups = {}
    for x in rows: groups.setdefault(x['crc32'], []).append(x['sel'])
    return rows, [v for v in groups.values() if len(v) > 1]


def report(r, outdir):
    internal = load_internal_crcs()
    res = dict(rejected_frames=r.rejects, line_errors=r.dec.line_errors, ended=r.ended, stages=r.stages, start=r.start)
    L = ['# HWTEST results (HW, measured on the unit; none of this is MAME)', '',
         'Captured: %s. Rejected frames: %d, line errors: %d. End of program received: %s.' % (time.strftime('%Y-%m-%d %H:%M:%S'), r.rejects, r.dec.line_errors, 'yes' if r.ended else 'NO (cut off or incomplete?)'), '']
    L.append('## Stages'); L += ['- %s (%s): %s' % (s, STAGE_NAMES[s], r.stages.get(s, 'not received')) for s in STAGES]; L.append('')
    if r.start:
        s = r.start
        L += ['## A. Entry state', '- cartridge `%s`  SP=%04X  build %04X  session %04X' % ('YE (autostart)' if s['variant'] == 'Y' else ('GA (menu)' if s['variant'] == 'G' else s['variant']), s['sp'], s['build'], s['session']),
              '- `LD A,I`: F=%02X (bit 2 = IFF2 -> interrupts %s) I=%02X' % (s['flags_at_entry'], 'ENABLED' if s['flags_at_entry'] & 4 else 'disabled', s['i_reg']),
              '- DFF0..DFF7 = ' + ' '.join('%02X' % x for x in s['shadows']) + '  (DFF1/DFF3 = shadows of ports 01/03, DFF4/DFF5 = bank and hook of the ISR)']
        if r.mem:
            img = bytearray(b'\xff' * 0x4000); have = 0
            for a, d in r.mem.items():
                img[a - 0xC000:a - 0xC000 + 128] = d; have += 1
            open(os.path.join(outdir, 'mem_C000_FFFF.bin'), 'wb').write(bytes(img))
            same = sum(1 for a in range(0xE000, 0x10000, 128) if a in r.mem and (a - 0x2000) in r.mem and r.mem[a] == r.mem[a - 0x2000])
            blocks_ff = sum(1 for a in range(0xE000, 0x10000, 128) if a in r.mem and set(r.mem[a]) == {0xFF})
            blocks_00 = sum(1 for a in range(0xE000, 0x10000, 128) if a in r.mem and set(r.mem[a]) == {0})
            L += ['- copy of C000-FFFF: %d/128 blocks received (`mem_C000_FFFF.bin`)' % have,
                  '- E000-FFFF: %d/64 blocks identical to their pair at C000-DFFF (mirror), %d all FF, %d all 00' % (same, blocks_ff, blocks_00)]
            res['e000_mirror_blocks'] = same; res['e000_ff_blocks'] = blocks_ff; res['e000_00_blocks'] = blocks_00
        L.append('')
    if r.ports:
        L += ['## B. Port reads (3 reads per port; 0A/0B deliberately not read)', '', '| port | reads |', '|---|---|']
        res['ports'] = {}
        for n in range(256):
            v = list(r.ports[3 * n:3 * n + 3])
            res['ports']['%02X' % n] = v
            if v != [0xFF] * 3 or n < 0x20: L.append('| %02X | %s |' % (n, ' '.join('%02X' % x for x in v)))
        L += ['', 'Ports that do not appear returned FF FF FF.', '']
    c = analyze_clock(r)
    if c:
        res['clock'] = c
        L += ['## C. CPU clock', '- bursts found: %s  bytes: %s' % (c['bursts_found'], c['bytes_per_burst']),
              '- period per byte (s): %s' % c['byte_period_s']]
        if 'cpu_clock_hz' in c: L.append('- **estimated CPU clock: %.3f MHz** (T per byte in burst 1: %.0f)' % (c['cpu_clock_hz'] / 1e6, c['t_per_byte_burst1']))
        L.append('')
    i = analyze_irq(r)
    if i:
        res['irq'] = i
        L += ['## D. Interrupts (firmware ISR + DFF5 hook that counts; no HALT)',
              '- marks received: ' + ', '.join('phase %d: %d IRQ (DB26/27=%04X DB00=%02X DB01=%02X)' % (f['phase'], f['count'], f['db26'], f['db00'], f['db01']) for f in i['frames'])]
        if 'hz' in i: L.append('- measured window: %d interrupts in %.2f s -> **%.2f Hz**' % (i['count'], i['seconds'], i['hz']))
        elif not i['reached_end']: L.append('- **the test did not finish** (the unit switched off or stopped after %d counted interrupts)' % i['max_count'])
        L.append('')
    if r.ans:
        res['answers'] = {}
        L += ['## E. LCD/LED questions', '', '| # | question | answer | expected (MAME/datasheet) |', '|---|---|---|---|']
        for k, (q, exp) in sorted(ANSWERS.items()):
            a = r.ans.get(k, '—'); res['answers'][k] = a
            L.append('| %d | %s | %s | %s |' % (k, q, a, exp))
        L.append('')
    if r.keys:
        ev = decode_keys(r.keys); res['key_events'] = ev
        L += ['## F. Keyboard matrix (change events, in order)', '', '| n | pressed | released |', '|---|---|---|']
        for e in ev: L.append('| %d | %s | %s |' % (e['n'], ', '.join(e['pressed']) or '—', ', '.join(e['released']) or '—'))
        L.append('')
    if r.wrp:
        o, polls, fin, after = r.wrp[0], list(r.wrp[1:17]), r.wrp[17], r.wrp[18]
        busy = any(x != o for x in polls) or fin != o
        res['wr_probe'] = dict(original=o, polls=polls, final=fin, after=after, eeprom_busy=busy, content_changed=(after != o))
        L += ['## K. /WR probe of the cartridge (one write of the same value at 9BF0 from RAM)',
              '- original value %02X; 16 immediate reads: %s; read after 70 ms: %02X; final read from the code: %02X' % (o, ' '.join('%02X' % x for x in polls), fin, after),
              ('- **the EEPROM answered as busy (DQ6/DQ7): /WR REACHES the cartridge** (and cartridge RAM can be expected if it is decoded that way)' if busy else
               '- no write-cycle signals: /WR does **not** seem to reach the EEPROM (or there is no effective write); it does NOT prove that the connector has no /WR'),
              ('- **WARNING: the content changed** (%02X -> %02X): check/reprogram the EEPROM' % (o, after)) if after != o else '- content intact', '']
    if r.win:
        rows, groups = window_report(r, internal); res['window'] = rows; res['window_mirror_groups'] = groups
        L += ['## H-K. Port 03: window 8000-BFFF per selector', '', '| sel | CRC-32 16 KiB | stable | content | 8K quarter low/high (mark) |', '|---|---|---|---|---|']
        for x in rows: L.append('| %s | %s | %s | %s | %s / %s |' % (x['sel'], x['crc32'], 'yes' if x['stable'] else '**NO**', x['kind'], x['quarter_8K_lo'], x['quarter_8K_hi']))
        L += ['', 'Selectors that give the same content (mirrors): ' + ('; '.join(' = '.join(gp) for gp in groups) if groups else 'none'), '']
    L += ['---', 'Generated by tools/hwtest_rx.py. The quarter marks (0..3) come from the 32 bytes at 0x1BE0 of each 8 KiB of the EEPROM image.']
    open(os.path.join(outdir, 'REPORT.md'), 'w').write('\n'.join(L) + '\n')
    json.dump(res, open(os.path.join(outdir, 'results.json'), 'w'), indent=1, default=str)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--port', default='/dev/ttyUSB0'); ap.add_argument('--baud', type=int, default=BAUD)
    ap.add_argument('--analyze', metavar='CAPTURE'); ap.add_argument('--outdir')
    a = ap.parse_args()
    r = Run()
    if a.analyze:
        outdir = a.outdir or os.path.join(os.path.dirname(os.path.abspath(a.analyze)), 'analysis'); os.makedirs(outdir, exist_ok=True)     # never overwrite the report written live
        data = open(a.analyze, 'rb').read(); tl = a.analyze[:-4] + '.tlog'
        if os.path.exists(tl):
            pos = 0
            for line in open(tl):
                t, n = line.split(); n = int(n); r.feed(float(t), data[pos:pos + n]); pos += n
        else:
            print('warning: no .tlog: clock and IRQ rate cannot be computed'); r.feed(0.0, data)
        report(r, outdir); print(open(os.path.join(outdir, 'REPORT.md')).read()); return 0
    import serial, termios
    stamp = time.strftime('%Y%m%d_%H%M%S')
    outdir = a.outdir or os.path.join(ROOT, 'results', stamp); os.makedirs(outdir)
    ser = serial.Serial(a.port, a.baud, bytesize=8, parity='N', stopbits=1, timeout=0.2, exclusive=True)
    try:
        at = termios.tcgetattr(ser.fileno())
        at[0] = (at[0] | termios.PARMRK | termios.INPCK) & ~(termios.IGNPAR | termios.ISTRIP | termios.IGNBRK | termios.BRKINT)
        termios.tcsetattr(ser.fileno(), termios.TCSANOW, at)
    except Exception as e: print('warning: PARMRK not enabled (%s)' % e, file=sys.stderr)
    print('port %s %d 8N1 (RX only). Results in %s\nPower on the Genio with the HWTEST cartridge. Ctrl-C to finish.\n' % (a.port, a.baud, outdir), flush=True)
    t0 = time.monotonic(); last_report = 0
    try:
        with open(os.path.join(outdir, 'capture.bin'), 'xb') as raw, open(os.path.join(outdir, 'capture.tlog'), 'x') as tl:
            while not r.ended:
                d = ser.read(max(1, ser.in_waiting))      # returns as soon as a byte arrives: fine timestamps for the clock / IRQ analysis
                if not d: continue
                t = time.monotonic() - t0
                raw.write(d); raw.flush(); tl.write('%.4f %d\n' % (t, len(d))); tl.flush()
                n0, st0 = len(r.frames), dict(r.stages)
                r.feed(t, d)
                for _, _, f in r.frames[n0:]:
                    if f.type == g.T_STAGE: print('stage %s (%s): %s' % (STAGES[f.payload[0]], STAGE_NAMES[STAGES[f.payload[0]]], 'skipped' if f.payload[1] else 'done'), flush=True)
                if r.stages != st0 or time.monotonic() - last_report > 20: report(r, outdir); last_report = time.monotonic()
    except KeyboardInterrupt: print('\ninterrupted')
    finally: ser.close()
    report(r, outdir)
    print(open(os.path.join(outdir, 'REPORT.md')).read())
    print('\nThe report is in %s/REPORT.md' % outdir)
    return 0 if r.ended else 2


if __name__ == '__main__': sys.exit(main())
