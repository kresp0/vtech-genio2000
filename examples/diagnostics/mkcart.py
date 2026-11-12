#!/usr/bin/env python3
# Checks the memory layout of the built cartridge, stores the CRC-32 of 8000-BFFB at BFFC (little endian),
# and writes the 16 KiB image plus the 32 KiB AT28C256 image (the 16 KiB repeated).
# Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later
import re
import sys
import zlib

name = sys.argv[1]
ihx = open("out/%s.ihx" % name).read().split()
top = 0
for rec in ihx:
    n, addr, typ = int(rec[1:3], 16), int(rec[3:7], 16), int(rec[7:9], 16)
    if typ == 0 and n and addr < 0xC000:      # VGLDK's 4 bytes of _INITIALIZER land in RAM and are never copied
        top = max(top, addr + n)
assert top <= 0xBFFC, "code reaches 0x%04X: no room for the CRC at BFFC" % top

sym = {m.group(2): int(m.group(1), 16) for m in re.finditer(r"^\s+([0-9A-F]{8})\s+(\S+)", open("out/%s.map" % name).read(), re.M)}
# RAM areas follow each other from C000; library code in _HOME would land in RAM too
data_end = sym["s__INITIALIZED"] + sym["l__INITIALIZED"]
assert sym["s__DATA"] == 0xC000 and sym.get("l__HOME", 0) == 0 and sym.get("l__BSS", 0) == 0
assert data_end <= 0xC400, "globals end at 0x%04X, beyond C3FF (the scratch area starts at C400)" % data_end

img = bytearray(open("out/%s.cart.16kb.bin" % name, "rb").read())
assert len(img) == 0x4000 and img[:4] == b"\x55\xAA\x59\x45"
img[0x3FFC:0x4000] = (zlib.crc32(bytes(img[:0x3FFC])) & 0xFFFFFFFF).to_bytes(4, "little")
open("%s_16K.bin" % name, "wb").write(img)
open("%s_mirrored_AT28C256_32K.bin" % name, "wb").write(img * 2)
print("code 8000-%04X (%d bytes, %d free), globals C000-%04X, CRC-32 %08X" %
      (top - 1, top - 0x8000, 0xBFFC - top, data_end - 1, int.from_bytes(img[0x3FFC:], "little")))
