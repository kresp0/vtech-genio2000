#!/usr/bin/env python3
"""Cross-check z80dis against MAME unidasm over every bank, linear sweep, byte-length agreement + text agreement."""
import subprocess, sys, re, os
sys.path.insert(0, os.path.dirname(__file__))
import z80dis
ROM = os.path.join(os.path.dirname(__file__), "..", "rom", "genio2000_es_128k.bin")
d = open(ROM, "rb").read()
def norm(t):
    t = t.lower().strip()
    t = re.sub(r"\s+", " ", t)
    t = t.replace(", ", ",").replace("$", "")
    t = re.sub(r"\b0+([0-9a-f]+)\b", r"\1", t)
    return t
tot = bad = 0
skipdb = [0]
for bank in range(8):
    b = d[bank*0x4000:(bank+1)*0x4000]
    open("/dev/shm/_cb.bin", "wb").write(b)
    out = subprocess.run(["unidasm", "/dev/shm/_cb.bin", "-arch", "z80"], capture_output=True, text=True).stdout
    ref = {}
    for ln in out.splitlines():
        m = re.match(r"([0-9a-f]{4}):\s+((?:[0-9a-f]{2} )+)\s*(.*)", ln)
        if m: ref[int(m.group(1), 16)] = (len(m.group(2).split()), m.group(3))
    pc = 0
    while pc < 0x4000 - 4:
        i = z80dis.decode(lambda a: b[a & 0x3FFF], pc)
        if pc in ref:
            tot += 1
            rl, rt = ref[pc]
            if rt.startswith("db "): skipdb[0] += 1; pc += i.length; continue
            if rl != i.length or norm(rt) != norm(i.text).replace("rrd","rrd (hl)").replace("rld","rld (hl)") if norm(i.text) in ("rrd","rld") else rl != i.length or norm(rt) != norm(i.text):
                bad += 1
                if bad < 25: print("DIFF bank%d %04X mine=%r (%d) unidasm=%r (%d)" % (bank, pc, i.text, i.length, rt, rl))
        pc += i.length
print("compared", tot, "different", bad, "unidasm-db(undocumented prefix forms, skipped)", skipdb[0])
