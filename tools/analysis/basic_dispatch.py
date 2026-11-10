#!/usr/bin/env python3
"""Statement dispatch table of the BASIC interpreter: bank 7 @0x5822, 60 words, index = token-0x80 (code at 7:5D60-5D75: SUB $80; CP $3C; RLCA; LD HL,$5822; ADD HL,BC).
Cross-checks each handler against the MAME-executed address set (out/mame/*.exec, bank 7 window 0x4000)."""
import sys, json, glob, os
sys.path.insert(0, 'tools'); import basic_tokens as bt
rom = open('rom/genio2000_es_128k.bin', 'rb').read(); b7 = rom[7*0x4000:8*0x4000]
dyn = set()
for f in glob.glob('out/mame/*.exec'):
    for ln in open(f):
        pc, e1, e2, n = ln.split()
        if int(e1) == 7 and 0x4000 <= int(pc, 16) < 0x8000: dyn.add(int(pc, 16))
names = {0x80 + i: bt.name(raw) for i, (_, raw) in enumerate(bt.entries())}
rows = []
for i in range(60):
    a = 0x5822 + 2*i
    h = b7[a-0x4000] | (b7[a-0x4000+1] << 8)
    tok = 0x80 + i
    rows.append(dict(token='0x%02X' % tok, keyword=names.get(tok), handler='0x%04X' % h,
                     kind='ram_stub' if h >= 0xC000 else 'rom', executed_in_mame='yes' if h in dyn else 'no'))
if '--json' in sys.argv: print(json.dumps(rows, indent=0))
else:
    for r in rows: print(r['token'], str(r['keyword']).ljust(8), r['handler'], r['kind'], r['executed_in_mame'])
