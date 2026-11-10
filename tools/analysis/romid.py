#!/usr/bin/env python3
"""Phase 1: identify the ROM image (hashes, banks, entropy, fill, duplicates, vectors)."""
import sys, hashlib, zlib, math, collections, json
ROM = sys.argv[1] if len(sys.argv) > 1 else "rom/genio2000_es_128k.bin"
d = open(ROM, "rb").read()
def ent(b):
    c = collections.Counter(b); n = len(b)
    return -sum(v/n*math.log2(v/n) for v in c.values())
out = {"size": len(d), "sha256": hashlib.sha256(d).hexdigest(), "sha1": hashlib.sha1(d).hexdigest(),
       "md5": hashlib.md5(d).hexdigest(), "crc32": "%08X" % zlib.crc32(d), "banks": []}
for i in range(len(d)//0x4000):
    b = d[i*0x4000:(i+1)*0x4000]
    c = collections.Counter(b)
    # trailing fill run
    t = len(b)
    while t > 0 and b[t-1] == b[-1]: t -= 1
    out["banks"].append(dict(bank=i, sha256=hashlib.sha256(b).hexdigest(), crc32="%08X" % zlib.crc32(b),
        entropy=round(ent(b), 3), n00=c[0], nFF=c[0xFF], tail_fill=f"{b[-1]:02X}x{len(b)-t}",
        head=b[:8].hex(), has_55AA="yes" if b[:2] == b"\x55\xaa" else "no",
        ascii_pct=round(100*sum(32 <= x < 127 for x in b)/len(b), 1)))
# duplicate 16K / 256B blocks
seen = collections.defaultdict(list)
for o in range(0, len(d), 256):
    blk = d[o:o+256]
    if len(set(blk)) > 1: seen[blk].append(o)
out["dup_256B_blocks_nonconstant"] = sum(1 for v in seen.values() if len(v) > 1)
print(json.dumps(out, indent=1))
