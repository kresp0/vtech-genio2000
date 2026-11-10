"""Regression tests: each assertion pins a documented conclusion to ROM bytes (they fail if the ROM image or the conclusion changes).
Run: python3 -I -m pytest -q tests   (or python3 -I tests/test_findings.py)"""
import hashlib, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
ROM = open(os.path.join(ROOT, 'rom', 'genio2000_es_128k.bin'), 'rb').read()
B = [ROM[i*0x4000:(i+1)*0x4000] for i in range(8)]

def w(b, a): return b[a] | (b[a+1] << 8)

def test_identity():
    assert len(ROM) == 131072
    assert hashlib.sha256(ROM).hexdigest() == 'f66f4d51d7152a8264ff9d99cbeb38dbbb5cc2d6f087e3fffb4e067f42e5ea48'
    assert len(set(hashlib.sha256(x).hexdigest() for x in B)) == 8     # 8 distinct banks

def test_reset_and_vectors():
    assert B[0][0:6] == bytes([0xF3, 0xED, 0x56, 0xC3, 0xAA, 0x0F])           # DI; IM 1; JP 0FAA
    assert B[0][0x38:0x3B] == bytes([0xC3, 0x19, 0x01])                         # IM1 vector -> ISR 0119
    assert B[0][0x08:0x0B] == bytes([0xC3, 0x00, 0xD0])                         # RST 08 -> RAM
    assert B[0][0x10:0x13] == bytes([0xC3, 0x10, 0x40])                         # RST 10 -> 4010 (system bank)
    assert B[0][0x30:0x33] == bytes([0xC3, 0xE6, 0x11])                         # RST 30 -> warm restart 11E6

def test_boot_cartridge_probe():
    code = B[0][0x100A:0x1033]
    assert bytes([0x3E, 0x80, 0xD3, 0x03]) in code                              # LD A,80; OUT (03),A  -> cartridge page 0
    assert bytes([0xFE, 0x55]) in code and bytes([0xFE, 0xAA]) in code and bytes([0xFE, 0x59]) in code and bytes([0xFE, 0x45]) in code
    assert B[0][0x1030:0x1033] == bytes([0xC3, 0x04, 0x80])                     # JP 8004
    # menu path (CARTUCHOS ADICIONALES): 55 AA 11 -> JP 27BD ; 55 AA 'G' 'A' -> JP 8004
    assert B[0][0x11A9:0x11AB] == bytes([0xFE, 0x11]) and B[0][0x11B3:0x11B6] == bytes([0xC3, 0xBD, 0x27])
    assert B[0][0x11B6:0x11B8] == bytes([0xFE, 0x47]) and B[0][0x11BC:0x11BE] == bytes([0xFE, 0x41])
    assert B[0][0x11C6:0x11C9] == bytes([0xC3, 0x04, 0x80])

def test_api_jump_table():
    for a in range(0x3B, 0x119, 3):
        assert B[0][a] == 0xC3, hex(a)
    assert w(B[0], 0x3C) == 0x36EE and w(B[0], 0x7B) == 0x35AE

def test_lcd_translation_and_ddram_table():
    code = B[0][0x07A8:0x07CA]
    for a, b in ((0xAD, 0xA9), (0xA8, 0x9F), (0xA4, 0x9B), (0xA5, 0x9C)):
        assert bytes([0xFE, a, 0x20, 0x03, 0x3E, b, 0xC9]) in code, hex(a)
    assert bytes([0xFE, 0xA7, 0xC0, 0x3E, 0x9E, 0xC9]) in code                  # last case falls through with RET NZ
    t = B[0][0x7EE:0x7EE+80]
    assert list(t[0:4]) == [0x80, 0x81, 0x82, 0x83] and t[20] == 0xA8 and list(t[40:44]) == [0x84, 0x85, 0x86, 0x87] and t[60] == 0xC4
    assert sorted(t) == sorted(set(t)) or len(set(t)) == 80                     # 80 distinct DDRAM addresses

def test_basic_keyword_table():
    import basic_tokens as bt
    n = {0x80 + i: bt.name(r) for i, (_, r) in enumerate(bt.entries())}
    assert n[0x80] == 'END' and n[0x82] == 'FOR' and n[0xB2] == 'PRINT' and n[0xBB] == 'NEW' and n[0xD7] == 'SGN' and n[0xFA] == 'MID$'
    assert n[0x85] is None and n[0xA2] is None                                  # emptied entries
    names = [v for v in n.values() if v]
    for absent in ('PEEK', 'POKE', 'CALL', 'USR', 'OUT', 'INP', 'WAIT', 'DEF', 'FRE', 'POS', 'ON'):
        assert absent not in names, absent
    assert len(names) == 68 and len(n) == 123

def test_basic_dispatch_and_syntax_error_stub():
    assert w(B[7], 0x5822 - 0x4000) == 0x5DAE                                   # END
    assert w(B[7], 0x5822 - 0x4000 + 2 * 0x32) == 0x606F                        # PRINT
    assert B[7][0x012D:0x0132] == bytes([0x1E, 0x02, 0xC3, 0xA2, 0x59])         # LD E,2; JP 59A2 (error 2)

def test_keyboard_scan_and_buffer_geometry():
    assert B[0][0x01B2:0x01B5] == bytes([0x21, 0x07, 0xDB])                     # LD HL,DB07 matrix buffer
    assert B[0][0x01BF:0x01C5] == bytes([0x0E, 0x80, 0x06, 0x08, 0x79, 0xD3]) and B[0][0x01C5] == 0x10   # C=80, B=8 columns, OUT (10),C
    assert B[0][0x0689+0:0x0689+1] == b'\xe5'
    assert B[0][0x064B:0x064F] == bytes([0xFD, 0x21, 0xA0, 0xDC])               # row 0 buffer DCA0
    assert B[0][0x0653:0x0657] == bytes([0xFD, 0x21, 0xB4, 0xDC])               # row 1 buffer DCB4

def test_word_database_extractor():
    """Real firmware routine B0:0C13 run in a Z80 interpreter reproduces what MAME shows (SINONIMOS 'abrasar quemar') and the bank-1 quiz format."""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    from textdec_probe import mk
    from wordlist_probe import word
    z = mk(4)
    assert word(z, 4, 1, 0, 1)[1].strip() == b'abrasar quemar'
    z1 = mk(1)
    assert word(z1, 1, 0, 0, 0)[1].decode('cp850').strip().startswith('\u00bfQUIEN ERA LA PAREJA DE STARSKY')

def test_duplicate_tails_and_zero_run():
    def tail(a, b):
        n = 0
        while n < 0x4000 and B[a][0x3FFF - n] == B[b][0x3FFF - n]: n += 1
        return n
    assert tail(2, 5) == 1095 and tail(0, 1) == 401           # identical tails of different banks (cause unknown)
    assert B[3][0x1439:0x1800] == bytes(967) and B[3][0x1438] != 0

def test_data_bank_statistics():
    import collections
    def load(n):
        d = collections.defaultdict(list)
        for l in open(os.path.join(ROOT, 'out', 'data_banks', n), encoding='utf-8'):
            g, s_, i, t = l.rstrip('\n').split('\t', 3); d[int(g)].append(t)
        return d
    b4, b1 = load('bank4.tsv'), load('bank1.tsv')
    assert [len(b4[g]) for g in range(14)] == [136, 133, 414, 213, 133, 135, 136, 102, 282, 126, 31, 200, 400, 160]
    assert b4[0][1] == 'abierto cerrado' and b4[1][1] == 'abrasar quemar' and b4[4][0] == 'abierto abiertos'   # antonyms / synonyms / plurals
    assert [len(b1[g]) for g in range(5)] == [213, 219, 220, 200, 214]
    assert dict(collections.Counter(len(t.split('\\')) for g in b1 for t in b1[g])) == {4: 785, 5: 253, 6: 25, 7: 3}   # question + 3..6 answer fragments

def test_bank_selects_in_mame_traces():
    import glob
    sel = {'01': set(), '03': set()}
    for f in glob.glob(os.path.join(ROOT, 'out', 'mame', '*.io')):
        for l in open(f):
            p = l.split()
            if p[0] == 'W' and p[1] in sel: sel[p[1]].add(int(p[2], 16))
    assert sel['03'] == {0x00, 0x03, 0x04, 0x06, 0x80} and sel['01'] == {0x00, 0x05, 0x06, 0x07}    # EMU: entries 1 and 2 never selected in the 51 scenarios

def test_second_unit_revision():
    U2 = open(os.path.join(ROOT, 'rom', 'genio2000_es_128k_unit2.bin'), 'rb').read()
    assert hashlib.sha256(U2).hexdigest() == '5e41fdabf73f87f9761502bce85db6de36d9c9db705a7887922b8e8ed56cc771'
    N = [U2[i*0x4000:(i+1)*0x4000] for i in range(8)]
    assert all(N[i] == B[i] for i in (0, 4, 5, 6))                       # core, words, activities, editor: common to both units
    d7 = [j for j in range(0x4000) if N[7][j] != B[7][j]]
    assert d7 == [0x39AC] and B[7][0x39AB:0x39AD] == bytes([0x38, 0x9C]) and N[7][0x39AB:0x39AD] == bytes([0x38, 0x99])   # JR C 7949 -> 7946 (stack fix)
    assert B[7][0x3949:0x394B] == bytes([0xAF, 0xC9]) and N[7][0x3946:0x394B] == bytes([0xC1, 0xE1, 0xF1, 0xAF, 0xC9])
    assert all(N[i] != B[i] for i in (1, 2, 3)) and N[1][:8] == B[1][:8] and N[3][0x144A:] == B[3][0x144A:]

def test_basic_file_code_uses_ram_cartridge():
    b = B[7]
    code = b[0x39BA:0x39BA + 0x20]                                       # 79BA: CALL 7D3D; LD HL,8000; LD A,55; CP (HL) ... CPL; CP (HL) ... LD A,EE
    assert code[3:6] == bytes([0x21, 0x00, 0x80]) and code[6:8] == bytes([0x3E, 0x55]) and bytes([0x3E, 0xEE]) in code
    # format path writes the signature back and verifies it: LD A,55 ; LD (HL),A ; CP (HL) ; RET NZ
    assert bytes([0x77, 0xBE, 0xC0]) in b[0x3A2E:0x3A40]

if __name__ == '__main__':
    import traceback
    ok = 0
    for k, v in sorted(globals().items()):
        if k.startswith('test_'):
            try: v(); print('PASS', k); ok += 1
            except Exception: print('FAIL', k); traceback.print_exc()
    print(ok, 'passed')
