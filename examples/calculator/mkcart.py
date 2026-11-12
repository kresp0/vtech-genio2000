#!/usr/bin/env python3
# Checks the memory layout of the built cartridge and writes the 16 KiB image plus the 32 KiB AT28C256 image
# (the 16 KiB repeated).
# Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later
import re
import sys

name = sys.argv[1]
ihx = open("out/%s.ihx" % name).read().split()
top = 0
for rec in ihx:
    n, addr, typ = int(rec[1:3], 16), int(rec[3:7], 16), int(rec[7:9], 16)
    if typ == 0 and n and addr < 0xC000:      # VGLDK's 4 bytes of _INITIALIZER land in RAM and are never copied
        top = max(top, addr + n)
assert top <= 0xC000, "page 1 overflows: code reaches 0x%04X" % top

sym = {m.group(2): int(m.group(1), 16) for m in re.finditer(r"^\s+([0-9A-F]{8})\s+(\S+)", open("out/%s.map" % name).read(), re.M)}
# RAM areas follow each other from C000; library code in _HOME would land in RAM too
data_end = sym["s__INITIALIZED"] + sym["l__INITIALIZED"]
stack_min = int(re.search(r"#define STACK_MIN (0x[0-9A-Fa-f]+)", open("%s.c" % name).read()).group(1), 16)
assert sym["s__DATA"] == 0xC000 and sym.get("l__HOME", 0) == 0 and sym.get("l__BSS", 0) == 0
assert data_end + 0x180 <= stack_min, "globals end at 0x%04X, too close to STACK_MIN 0x%04X" % (data_end, stack_min)

# page 1 (selector 0x80) in the first half of the AT28C256, page 2 (0x83: bit 1 drives A14 on the RevD board) in
# the second. MAME maps selector 0x8n to offset n * 16 KiB without mirroring, so its copy repeats the 32 KiB.
img = bytearray(open("out/%s.cart.16kb.bin" % name, "rb").read())
img += b"\xff" * (0x4000 - len(img))	# makebin -p stops at the last byte used
p2 = open("page2.bin", "rb").read()
assert len(img) == 0x4000 and img[:4] == b"\x55\xAA\x59\x45" and len(p2) == 0x4000 and p2[:4] == b"CALC"
open("%s_AT28C256_32K.bin" % name, "wb").write(img + p2)
open("%s_mame_64K.bin" % name, "wb").write((img + p2) * 2)
print("page 1: code 8000-%04X (%d bytes, %d free); globals C000-%04X; stack DFF0-%04X (%d bytes)" %
      (top - 1, top - 0x8000, 0xC000 - top, data_end - 1, stack_min, 0xDFF0 - stack_min))
