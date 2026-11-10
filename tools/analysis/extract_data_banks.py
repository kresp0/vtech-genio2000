#!/usr/bin/env python3
"""Extract the word database of a data bank by running the REAL firmware routine B0:0C13 in a Z80 interpreter
(tools/z80core.py, read-only copy of firmware-dump/tests/z80core.py) with the bank mapped at 0x8000 (OUT 03 emulated).
Routine contract (derived from the code and checked against MAME, SINONIMOS 'abrasar quemar'):
  A = group, D = subgroup, E = index; returns A != 0xFF on success; result string at D401.. (length at D400).
Hierarchy counts come from the header: word at 8008 -> P: P[0]=n_groups, P[1..n]=n_subgroups per group, then per-(group,subgroup) counts.
Output: out/data_banks/bank<k>.tsv  (group, sub, index, text)  -- text bytes are firmware codes (CP437/850-like), decoded to Unicode with cp850.
Evidence: EMU-independent (ROM bytes + firmware code); correctness of the harness verified by reproducing MAME's output."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from textdec_probe import mk, ROM
from wordlist_probe import word
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(ROOT, 'out', 'data_banks'), exist_ok=True)
def counts(bank):
    """(group, sub) -> number of entries, from the header table P (word at +8): P[0]=n_groups, P[1..n]=subgroups per group, then one count byte per (group,sub)."""
    b = ROM[bank*0x4000:(bank+1)*0x4000]
    P = (b[8] | (b[9] << 8)) - 0x8000
    ng = b[P]; nsub = list(b[P+1:P+1+ng]); q = P + 1 + ng; out = {}
    for A in range(ng):
        for D in range(nsub[A]):
            out[(A, D)] = b[q]; q += 1
    return out
def dump(bank):
    z = mk(bank); rows = []
    for (A, D), n in sorted(counts(bank).items()):
        for E in range(n):
            r = word(z, bank, A, D, E)
            rows.append((A, D, E, r[1] if r and r[0] != 0xFF else None))
    return rows
if __name__ == '__main__':
    for b in [int(x) for x in sys.argv[1:]] or [4]:
        rows = dump(b)
        with open(os.path.join(ROOT, 'out', 'data_banks', 'bank%d%s.tsv' % (b, os.environ.get('GENIO_TAG', ''))), 'w', encoding='utf-8') as f:
            for A, D, E, t in rows:
                f.write('%d\t%d\t%d\t%s\n' % (A, D, E, (t.decode('cp850', 'replace').strip() if t is not None else '<FAIL>')))
        print('bank', b, len(rows), 'entries', rows[:2])
