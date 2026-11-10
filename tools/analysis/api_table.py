#!/usr/bin/env python3
"""Bank-0 API jump table (0x003B..0x0116, 3-byte JP entries) -> out/api_table.csv with target, first instructions and caller counts."""
import csv, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); import z80dis
ROM = open(os.path.join(ROOT, 'rom', 'genio2000_es_128k.bin'), 'rb').read()
callers = collections.Counter(); caller_banks = collections.defaultdict(set)
for r in csv.DictReader(open(os.path.join(ROOT, 'out', 'insns.csv'))):
    if r['kind'] in ('call', 'jp', 'rst') and r['target']:
        t = int(r['target'], 16)
        if 0x3B <= t < 0x119 and (t - 0x3B) % 3 == 0:
            callers[t] += 1; caller_banks[t].add(int(r['bank']))
rows = []
for a in range(0x3B, 0x119, 3):
    assert ROM[a] == 0xC3, hex(a)
    tgt = ROM[a + 1] | (ROM[a + 2] << 8)
    ins = []; pc = tgt
    for _ in range(4):
        i = z80dis.decode(lambda x: ROM[x & 0x3FFF], pc); ins.append(i.text); pc += i.length
        if i.kind in ('ret', 'jp'): break
    rows.append([('%04X' % a), ('%04X' % tgt), callers[a], ','.join(map(str, sorted(caller_banks[a]))), ' ; '.join(ins)])
with open(os.path.join(ROOT, 'out', 'api_table.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['entry', 'target', 'static_or_dyn_callers', 'caller_banks', 'first_insns']); w.writerows(rows)
for r in rows: print(*r, sep=' | ')
