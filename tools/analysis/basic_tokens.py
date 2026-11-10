#!/usr/bin/env python3
"""Parse the BASIC keyword table (bank 7 @ 0x5650, window 0x4000) into token numbers.
Evidence: detokenizer at 0x6B94-0x6BC4 (LIST): token t >= 0x80 -> E = t-0x7F; walk from 0x5650 skipping bytes while bit7=0;
the E-th byte with bit 7 set starts the E-th entry; the entry text continues until the next byte with bit 7 set (first char = byte & 0x7F).
Entries that are '81 00 00 ...' are never matched by the tokenizer: reported as <unused>.
"""
import sys, json
rom = open('rom/genio2000_es_128k.bin', 'rb').read()
B7 = rom[7*0x4000:8*0x4000]
START = 0x5650
def entries(start=START, end=0x5820):
    i = start - 0x4000
    out = []
    while i < end - 0x4000:
        assert B7[i] & 0x80, hex(i + 0x4000)
        j = i + 1
        while j < len(B7) and not (B7[j] & 0x80):
            j += 1
        raw = B7[i:j]
        out.append((0x4000 + i, raw))
        i = j
    return out
def name(raw):
    s = bytes([raw[0] & 0x7F]) + raw[1:]
    if raw[0] == 0x81 and all(b == 0 for b in raw[1:]):
        return None
    return s.decode('latin-1')
if __name__ == '__main__':
    ents = entries()
    res = []
    for n, (addr, raw) in enumerate(ents):
        tok = 0x80 + n
        res.append(dict(token="0x%02X" % tok, addr="0x%04X" % addr, name=name(raw), raw=raw.hex()))
    print(json.dumps(res, indent=0) if '--json' in sys.argv else '')
    if '--json' not in sys.argv:
        for r in res:
            print("%s  %s  %-10s  %s" % (r['token'], r['addr'], r['name'], r['raw']))
