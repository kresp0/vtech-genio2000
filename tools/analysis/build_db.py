#!/usr/bin/env python3
"""Build the code database: recursive tracing seeded by (a) architectural vectors, (b) the bank-0 API jump table,
(c) every opcode address executed in MAME (out/mame/*.exec, with bank context) and (d) word tables of code pointers
validated by (a)-(c).  Outputs (all under out/):
  insns.csv      image,addr,bytes,text,kind,target,dyn
  functions.csv  image,addr,callers,ncalls_dyn,seed_reasons
  xrefs.csv      src_image,src_pc,kind,dst_image,dst_addr
  coverage.json  per-bank code bytes (static / dynamic / union)
Image naming: 'B<k>@<window>'.
Evidence classes: static trace = derived from ROM bytes; dyn = also executed in MAME (emulation, NOT hardware).
"""
import os, sys, glob, json, csv, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import trace as T
import z80dis

ROM = open(os.path.join(ROOT, 'rom', 'genio2000_es_128k.bin'), 'rb').read()
OUT = os.path.join(ROOT, 'out'); os.makedirs(OUT, exist_ok=True)


def img_of(pc, e1, e2):
    if pc < 0x4000:
        return (0, 0)
    if pc < 0x8000:
        return (e1, 0x4000)
    if pc < 0xC000 and e2 < 8:
        return (e2, 0x8000)
    return None  # cartridge window (e2>=0x80) or RAM


def load_dynamic():
    dyn = collections.defaultdict(int)   # (bank,win,pc) -> count
    ctx = collections.defaultdict(set)   # window -> banks seen
    for f in sorted(glob.glob(os.path.join(OUT, 'mame', '*.exec'))):
        for ln in open(f):
            pc, e1, e2, n = ln.split()
            pc = int(pc, 16); e1 = int(e1); e2 = int(e2); n = int(n)
            im = img_of(pc, e1, e2)
            if im is None:
                continue
            dyn[(im[0], im[1], pc)] += n
    return dyn


def main():
    dyn = load_dynamic()
    seeds = [(0, 0, a, 'vector') for a in (0x0000, 0x0008, 0x0010, 0x0018, 0x0020, 0x0028, 0x0030, 0x0038, 0x0066)]
    seeds += [(0, 0, a, 'api_jump_table') for a in range(0x3B, 0x119, 3)]
    # bank-7 RST stubs (RST 10h..28h land at 0x4010..0x4028 in system bank 7)
    seeds += [(7, 0x4000, a, 'rst_stub') for a in (0x4000, 0x4010, 0x4018, 0x4020, 0x4028)]
    # cartridge-style headers in banks 1 and 4 (55 AA): entry 0x8004? (jump target seen in bank 0 at 0x1019-0x1030)
    for (b, w, pc), n in dyn.items():
        seeds.append((b, w, pc, 'dynamic'))
    t = T.Tracer(ROM)
    t.run(seeds)
    # pass 2: far references that can be resolved from the dynamic contexts of the target window
    unresolved = collections.Counter()
    for (sb, sw, spc, kind, tgt) in list(t.far):
        cands = sorted({(b, w) for (b, w, pc) in dyn if pc == tgt})
        if cands:
            for (b, w) in cands:
                t.add_seed(b, w, tgt, 'far_%s_dyn' % kind, (sb, sw, spc, kind))
        else:
            unresolved[(sb, sw, kind, tgt)] += 1
    t.run([])
    # pass 3: word tables of code pointers (>=4 consecutive words, each landing on a decoded instruction start in the same bank image)
    ptr_seeds = []
    for im, code in t.code.items():
        pass
    cov = {}
    for k in range(8):
        for w in (0x0000, 0x4000, 0x8000):
            code = t.code.get((k, w))
            if code:
                cov["B%d@%04X" % (k, w)] = sum(i.length for i in code.values())
    # per-bank union (a byte decoded in any window)
    union = {}
    for k in range(8):
        m = bytearray(0x4000)
        for w in (0x0000, 0x4000, 0x8000):
            code = t.code.get((k, w), {})
            for a, i in code.items():
                for j in range(i.length):
                    off = (a - w + j) & 0x3FFF if not (k == 0 and w == 0) else (a + j)
                    if off < 0x4000:
                        m[off] = 1
        union[k] = sum(m)
    with open(os.path.join(OUT, 'insns.csv'), 'w', newline='') as f:
        wr = csv.writer(f)
        wr.writerow(['bank', 'window', 'addr', 'bytes', 'text', 'kind', 'target', 'dyn'])
        for (k, w), code in sorted(t.code.items()):
            for a in sorted(code):
                i = code[a]
                wr.writerow([k, '%04X' % w, '%04X' % a, i.bytes.hex(), i.text, i.kind, '' if i.target is None else '%04X' % i.target, dyn.get((k, w, a), 0)])
    funcs = collections.defaultdict(lambda: {'callers': [], 'why': set()})
    for (b, w, a), why in t.labels.items():
        if 'call_target' in why or 'vector' in why or 'api_jump_table' in why or 'rst_stub' in why or any(x.startswith('far_call') for x in why):
            f = funcs[(0, 0, a) if a < 0x4000 else (b, w, a)]
            f['why'] |= why
    for key, lst in t.callers.items():
        b, w, a = key
        if (b, w, a) in funcs or (0, 0, a) in funcs:
            funcs[(b, w, a)]['callers'] += lst
    with open(os.path.join(OUT, 'functions.csv'), 'w', newline='') as f:
        wr = csv.writer(f)
        wr.writerow(['bank', 'window', 'addr', 'n_callers', 'dyn_hits', 'why'])
        for (b, w, a), v in sorted(funcs.items()):
            wr.writerow([b, '%04X' % w, '%04X' % a, len(v['callers']), dyn.get((b, w, a), 0), '|'.join(sorted(v['why']))])
    with open(os.path.join(OUT, 'xrefs.csv'), 'w', newline='') as f:
        wr = csv.writer(f)
        wr.writerow(['src_bank', 'src_window', 'src_pc', 'kind', 'dst_bank', 'dst_window', 'dst_addr'])
        for (b, w, a), lst in sorted(t.callers.items()):
            for (sb, sw, spc, kind) in lst:
                wr.writerow([sb, '%04X' % sw, '%04X' % spc, kind, b, '%04X' % w, '%04X' % a])
    json.dump({'per_image_bytes': cov, 'per_bank_union_bytes': union, 'bank_size': 0x4000,
               'dyn_unique_addresses': len(dyn), 'unresolved_far': [list(map(str, k)) + [n] for k, n in unresolved.items()],
               'jpind': [[b, '%04X' % w, '%04X' % p, x] for b, w, p, x in t.jpind]},
              open(os.path.join(OUT, 'coverage.json'), 'w'), indent=1)
    print(json.dumps({'union_bytes': union, 'percent': {k: round(100 * v / 0x4000, 1) for k, v in union.items()}}, indent=1))
    print('images:', sorted(cov.items()))
    print('unresolved far:', len(unresolved), ' jpind:', len(t.jpind))
    return t, dyn


if __name__ == '__main__':
    main()
