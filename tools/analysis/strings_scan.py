#!/usr/bin/env python3
"""List printable ASCII runs per bank (min length N). Output: bank:offset(window addr) text.  Also tries high-bit-terminated strings."""
import sys, re
rom = open('rom/genio2000_es_128k.bin','rb').read()
N = int(sys.argv[1]) if len(sys.argv) > 1 else 5
sel = [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else range(8)
for b in sel:
    d = rom[b*0x4000:(b+1)*0x4000]
    for m in re.finditer(rb'[ -~\xa1-\xff]{%d,}' % N, d):
        print("%d:%04X %s" % (b, m.start(), m.group().decode('latin-1')))
