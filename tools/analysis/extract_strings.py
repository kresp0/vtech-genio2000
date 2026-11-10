#!/usr/bin/env python3
"""Extract text-like runs from every bank into out/strings.csv (bank, offset, window-addr, length, text, decoded_as_code_pct).
A run is >=6 bytes of [0x20-0x7E] or LCD accent codes {0xA9,0xAD,0xB0-0xFF excluded} with >=70% letters/space/digits.
Heuristic: runs fully inside statically/dynamically decoded code are flagged but kept (inline strings after CALL exist)."""
import re, csv, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ROM = open(os.path.join(ROOT, 'rom', 'genio2000_es_128k.bin'), 'rb').read()
code = {}
for r in csv.DictReader(open(os.path.join(ROOT, 'out', 'insns.csv'))):
    k = int(r['bank']); a = int(r['addr'], 16); w = int(r['window'], 16)
    off = a if (k == 0 and w == 0) else a - w
    code.setdefault(k, set()).update(range(off, off + len(r['bytes']) // 2))
PRIM = {0: 0, 1: 0x8000, 2: 0x8000, 3: 0x8000, 4: 0x8000, 5: 0x4000, 6: 0x8000, 7: 0x4000}
rows = []
for k in range(8):
    d = ROM[k * 0x4000:(k + 1) * 0x4000]
    for m in re.finditer(rb'[\x20-\x7e\xa9\xad]{6,}', d):
        s = m.group()
        good = sum(chr(c).isalnum() or c in b' .,:;!?()-\xa9\xad' for c in s)
        if good / len(s) < 0.8: continue
        if sum(chr(c).isalpha() for c in s) < len(s) * 0.5: continue
        inc = sum((m.start() + i) in code.get(k, ()) for i in range(len(s)))
        rows.append((k, m.start(), PRIM[k] + m.start(), len(s), s.decode('latin-1'), round(100 * inc / len(s))))
with open(os.path.join(ROOT, 'out', 'strings.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['bank', 'offset', 'win_addr', 'len', 'text', 'pct_in_decoded_code']); w.writerows(rows)
print(len(rows), 'strings;', {k: sum(1 for r in rows if r[0] == k) for k in range(8)})
