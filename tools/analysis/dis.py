#!/usr/bin/env python3
"""dis.py BANK START LEN [WINDOW_BASE_HEX]  -- linear disassembly of a bank with logical addresses."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import z80dis
ROM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rom", "genio2000_es_128k.bin")
rom = open(ROM, "rb").read()
bank = int(sys.argv[1]); start = int(sys.argv[2], 16); n = int(sys.argv[3], 0)
win = int(sys.argv[4], 16) if len(sys.argv) > 4 else (0 if bank == 0 else 0x4000)
b = rom[bank*0x4000:(bank+1)*0x4000]
pc = start
end = start + n
while pc < end:
    i = z80dis.decode(lambda a: b[(a - win) & 0x3FFF], win + pc if False else pc)
    off = pc
    print("%04X  %-11s %s" % (pc + win, i.bytes.hex(" "), i.text))
    pc += i.length
