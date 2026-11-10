#!/usr/bin/env python3
"""mk_image.py <ye|ga> <map> <cart8k> <out32k>: checks the memory discipline and builds the 32 KiB EEPROM image.
Every 8 KiB quarter is identical (so the cartridge boots whatever address lines the board really connects) EXCEPT 32 bytes at
0x1BE0..0x1BFF (CPU 0x9BE0 / 0xBBE0 in the window), which carry the quarter number: the program reports them, which tells which
cartridge address lines (A13, A14, page bits) reach the EEPROM."""
import re, sys, hashlib
var, mp, cart, out = sys.argv[1:5]
areas, syms = {}, {}
for line in open(mp):
    m = re.match(r'^(_\w+)\s+([0-9A-F]{8})\s+([0-9A-F]{8})\s*=', line)
    if m: areas[m.group(1)] = (int(m.group(2), 16), int(m.group(3), 16))
    m = re.match(r'^\s+([0-9A-F]{8})\s+(\S+)\s+\S+\s*$', line)
    if m: syms[m.group(2)] = int(m.group(1), 16)
bad = []
code = areas.get('_CODE')
if not code or code[0] != 0x8020 or code[0] + code[1] > 0x9BE0: bad.append('_CODE outside 0x8020..0x9BDF: %s' % (code,))
for a in ('_DATA', '_INITIALIZED', '_INITIALIZER', '_BSS', '_HEAP'):
    if a in areas and areas[a][1]:
        s, n = areas[a]
        if not (0xC000 <= s and s + n <= 0xC800): bad.append('%s outside 0xC000..0xC7FF: %04X+%d' % (a, s, n))
if syms.get('_crc_t0') != 0x9C00: bad.append('_crc_t0 != 0x9C00')
d = bytearray(open(cart, 'rb').read())
hdr = {'ye': bytes([0x55, 0xAA, 0x59, 0x45]), 'ga': bytes([0x55, 0xAA, 0x47, 0x41])}[var]
if len(d) != 8192 or d[:4] != hdr: bad.append('header / size')
if any(x != 0xFF for x in d[0x1BE0:0x1C00]): bad.append('marker area 0x1BE0..0x1BFF is not free')
for a, (s, n) in sorted(areas.items()):
    if n: print('  %-14s %04X-%04X (%d B)' % (a, s, s + n - 1, n))
print('mk_image: ' + ('FAILS: ' + '; '.join(bad) if bad else 'OK'))
if bad: sys.exit(1)
img = bytearray()
for q in range(4):
    qd = bytearray(d)
    qd[0x1BE0:0x1BE4] = b'MQ' + bytes([q, (~q) & 0xFF])
    for i in range(4, 32): qd[0x1BE0 + i] = (q << 4 | (i & 15)) & 0xFF
    img += qd
open(out, 'wb').write(img)
print('%s  %d bytes  code %d B' % (out, len(img), code[1]))
print(hashlib.sha256(img).hexdigest())
