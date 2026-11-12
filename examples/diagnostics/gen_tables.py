#!/usr/bin/env python3
# Generates tables.h for the diagnostic cartridge: ALU test vectors and their expected CRCs (from a Python model
# of the documented Z80 flags), CRC-32 tables, known firmware bank CRCs, key names, and the T-state counted
# routines (tone, millisecond delay, interrupt counting loop) with assertions on their cycle counts.
# Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later

CLOCK = 6131790          # Hz, measured on the CPU CLK pin of the unit (docs/hardware/CLOCK_AND_SOUND.md)
OUT = "tables.h"

SF, ZF, YF, HF, XF, PF, NF, CF = 0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01
DOC = SF | ZF | HF | PF | NF | CF        # 0xD7: documented flags only


def parity(v):
    return 0 if bin(v & 0xFF).count("1") & 1 else PF


def szp(v):
    v &= 0xFF
    return (v & SF) | (ZF if v == 0 else 0) | parity(v)


# ---------------------------------------------------------------- 8/16-bit ALU model (documented behaviour)
def add8(a, b, c):
    r = a + b + c
    f = (r & 0x80) | (ZF if r & 0xFF == 0 else 0) | (HF if (a & 0xF) + (b & 0xF) + c > 0xF else 0)
    f |= PF if ((a ^ ~b) & (a ^ r) & 0x80) else 0
    f |= CF if r > 0xFF else 0
    return r & 0xFF, f


def sub8(a, b, c):
    r = a - b - c
    f = (r & 0x80) | (ZF if r & 0xFF == 0 else 0) | (HF if (a & 0xF) - (b & 0xF) - c < 0 else 0) | NF
    f |= PF if ((a ^ b) & (a ^ r) & 0x80) else 0
    f |= CF if r < 0 else 0
    return r & 0xFF, f


def daa(a, f):
    c, h, n = f & CF, f & HF, f & NF
    diff, nc = 0, 0
    if h or (a & 0xF) > 9:
        diff |= 0x06
    if c or a > 0x99:
        diff |= 0x60
        nc = CF
    r = (a - diff) & 0xFF if n else (a + diff) & 0xFF
    nh = (HF if (h and (a & 0xF) < 6) else 0) if n else (HF if (a & 0xF) > 9 else 0)
    return r, szp(r) | nh | n | nc


def rot_cb(kind, a, f):
    c = f & CF
    if kind == "RLC":
        co = a >> 7; r = ((a << 1) | co) & 0xFF
    elif kind == "RRC":
        co = a & 1; r = (a >> 1) | (co << 7)
    elif kind == "RL":
        co = a >> 7; r = ((a << 1) | c) & 0xFF
    elif kind == "RR":
        co = a & 1; r = (a >> 1) | (c << 7)
    elif kind == "SLA":
        co = a >> 7; r = (a << 1) & 0xFF
    elif kind == "SRA":
        co = a & 1; r = (a >> 1) | (a & 0x80)
    else:  # SRL
        co = a & 1; r = a >> 1
    return r, co


def model(op, a, f, b, h, l, d, e):
    """Returns (A, F, H, L) after the routine for op."""
    hl, de = (h << 8) | l, (d << 8) | e
    c = f & CF
    keep = f & (SF | ZF | PF)
    if op in ("ADD A,B", "ADC A,B"):
        a, f = add8(a, b, c if op == "ADC A,B" else 0)
    elif op in ("SUB B", "SBC A,B"):
        a, f = sub8(a, b, c if op == "SBC A,B" else 0)
    elif op == "CP B":
        _, f = sub8(a, b, 0)
    elif op == "AND B":
        a &= b; f = szp(a) | HF
    elif op == "XOR B":
        a ^= b; f = szp(a)
    elif op == "OR B":
        a |= b; f = szp(a)
    elif op == "INC A":
        r = (a + 1) & 0xFF
        f = (r & SF) | (ZF if r == 0 else 0) | (HF if a & 0xF == 0xF else 0) | (PF if a == 0x7F else 0) | c
        a = r
    elif op == "DEC A":
        r = (a - 1) & 0xFF
        f = (r & SF) | (ZF if r == 0 else 0) | (HF if a & 0xF == 0 else 0) | (PF if a == 0x80 else 0) | NF | c
        a = r
    elif op == "NEG":
        a, f = sub8(0, a, 0)
    elif op == "CPL":
        a ^= 0xFF; f = (f & (SF | ZF | PF | CF)) | HF | NF
    elif op == "DAA":
        a, f = daa(a, f)
    elif op == "ADD+DAA":
        a, f = add8(a, b, 0); a, f = daa(a, f)
    elif op == "SUB+DAA":
        a, f = sub8(a, b, 0); a, f = daa(a, f)
    elif op == "SCF":
        f = keep | CF
    elif op == "CCF":
        f = keep | (HF if c else 0) | (0 if c else CF)
    elif op in ("RLCA", "RRCA", "RLA", "RRA"):
        a, co = rot_cb({"RLCA": "RLC", "RRCA": "RRC", "RLA": "RL", "RRA": "RR"}[op], a, f)
        f = keep | co
    elif op.split()[0] in ("RLC", "RRC", "RL", "RR", "SLA", "SRA", "SRL"):
        a, co = rot_cb(op.split()[0], a, f)
        f = szp(a) | co
    elif op.startswith("BIT"):
        n = int(op[4])
        f = (0 if (a >> n) & 1 else ZF) | HF | c
    elif op == "ADD HL,DE":
        r = hl + de
        f = keep | (HF if (hl & 0xFFF) + (de & 0xFFF) > 0xFFF else 0) | (CF if r > 0xFFFF else 0)
        hl = r & 0xFFFF
    elif op == "ADC HL,DE":
        r = hl + de + c
        f = ((r >> 8) & SF) | (ZF if r & 0xFFFF == 0 else 0) | (HF if (hl & 0xFFF) + (de & 0xFFF) + c > 0xFFF else 0)
        f |= PF if ((hl ^ ~de) & (hl ^ r) & 0x8000) else 0
        f |= CF if r > 0xFFFF else 0
        hl = r & 0xFFFF
    elif op == "SBC HL,DE":
        r = hl - de - c
        f = ((r >> 8) & SF) | (ZF if r & 0xFFFF == 0 else 0) | (HF if (hl & 0xFFF) - (de & 0xFFF) - c < 0 else 0) | NF
        f |= PF if ((hl ^ de) & (hl ^ r) & 0x8000) else 0
        f |= CF if r < 0 else 0
        hl = r & 0xFFFF
    else:
        raise ValueError(op)
    return a & 0xFF, f & 0xFF, hl >> 8, hl & 0xFF


# op name -> (asm body, flag mask). BIT leaves S and P/V undocumented, so only Z, H, N, C are compared.
OPS = [
    ("ADD A,B", "add a, b", DOC), ("ADC A,B", "adc a, b", DOC), ("SUB B", "sub a, b", DOC),
    ("SBC A,B", "sbc a, b", DOC), ("AND B", "and a, b", DOC), ("XOR B", "xor a, b", DOC),
    ("OR B", "or a, b", DOC), ("CP B", "cp a, b", DOC), ("INC A", "inc a", DOC), ("DEC A", "dec a", DOC),
    ("NEG", "neg", DOC), ("CPL", "cpl", DOC), ("DAA", "daa", DOC), ("ADD+DAA", "add a, b\n\tdaa", DOC),
    ("SUB+DAA", "sub a, b\n\tdaa", DOC), ("SCF", "scf", DOC), ("CCF", "ccf", DOC),
    ("RLCA", "rlca", DOC), ("RRCA", "rrca", DOC), ("RLA", "rla", DOC), ("RRA", "rra", DOC),
    ("RLC A", "rlc a", DOC), ("RRC A", "rrc a", DOC), ("RL A", "rl a", DOC), ("RR A", "rr a", DOC),
    ("SLA A", "sla a", DOC), ("SRA A", "sra a", DOC), ("SRL A", "srl a", DOC),
    ("BIT 0,A", "bit 0, a", ZF | HF | NF | CF), ("BIT 7,A", "bit 7, a", ZF | HF | NF | CF),
    ("ADD HL,DE", "add hl, de", DOC), ("ADC HL,DE", "adc hl, de", DOC), ("SBC HL,DE", "sbc hl, de", DOC),
]


def vectors():
    edge = [0x00, 0x01, 0x0F, 0x10, 0x7F, 0x80, 0x81, 0x99, 0xFF, 0x09, 0x90, 0x5A, 0x3C, 0xF0]
    flags = [0x00, 0x01, 0x10, 0x11, 0x02, 0x13, 0xFF, 0x12, 0x03, 0x42, 0xD6, 0x29]
    v, x = [], 0x1D35
    for i, a in enumerate(edge):
        b = edge[(i * 5 + 3) % len(edge)]
        v.append((a, b, flags[i % len(flags)]))
        v.append((a, a, flags[(i + 4) % len(flags)]))
    while len(v) < 64:
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        v.append(((x >> 8) & 0xFF, (x >> 16) & 0xFF, flags[(x >> 4) % len(flags)]))
    return v


def crc16(data, crc=0xFFFF):
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return crc


def alu_crc(op, mask):
    out = []
    for a, b, f in vectors():
        # register setup of alu_run: A=a F=f B=b C=5A D=b E=a H=a L=b
        ra, rf, rh, rl = model(op, a, f, b, a, b, b, a)
        out += [ra, rf & mask, rh, rl]
    return crc16(out)


# ---------------------------------------------------------------- CRC-32 (reflected, poly EDB88320)
def crc32_table():
    t = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = (c >> 1) ^ 0xEDB88320 if c & 1 else c >> 1
        t.append(c)
    return t


# Internal ROM bank CRC-32s of both known units (docs/firmware/ROM_REVISIONS.md); checksums only.
BANKS = [(0xD49DECF0, "bank 0"), (0x67EBAB51, "bank 1 u1"), (0x14879354, "bank 1 u2"),
         (0x35C99AC6, "bank 2 u1"), (0x13B41C7F, "bank 2 u2"), (0x021A7E5B, "bank 3 u1"),
         (0x992915F8, "bank 3 u2"), (0x8A1F0214, "bank 4"), (0x63924486, "bank 5"),
         (0x8F71AB6E, "bank 6"), (0xF28A4E52, "bank 7 u1"), (0x0468223B, "bank 7 u2")]

# ---------------------------------------------------------------- keys: (col, row, label); docs/hardware/KEYBOARD.md
KEYS = [
    (0, 1, "PAUSA"), (1, 1, "1"), (2, 0, "2"), (2, 1, "3"), (3, 0, "4"), (3, 1, "5"), (4, 0, "6"), (4, 1, "7"),
    (5, 0, "8"), (5, 1, "9"), (6, 0, "0"), (7, 2, "RETROCESO"), (7, 3, "AVANCE"), (0, 0, "AYUDA"),
    (1, 2, "Q"), (2, 7, "W"), (2, 2, "E"), (3, 7, "R"), (3, 2, "T"), (4, 7, "Y"), (4, 2, "U"), (5, 7, "I"),
    (5, 2, "O"), (6, 7, "P"), (6, 2, "\x9a"), (6, 1, "REPETIR/BORRAR"), (1, 0, "BLOQ. MAYUSCULAS"),
    (1, 3, "A"), (2, 3, "S"), (2, 4, "D"), (3, 3, "F"), (3, 4, "G"), (4, 3, "H"), (4, 4, "J"), (5, 3, "K"),
    (5, 4, "L"), (6, 3, "\x9c"), (6, 4, ";"), (7, 4, "INTRO"), (6, 6, "MAYUSCULAS"), (1, 4, "Z"), (2, 5, "X"),
    (2, 6, "C"), (3, 5, "V"), (3, 6, "B"), (4, 5, "N"), (4, 6, "M"), (5, 5, ","), (5, 6, "."), (6, 5, "'"),
    (1, 7, "JUG. IZQUIERDA/INS"), (1, 5, "ALT"), (1, 6, "ESPACIO"), (7, 6, "RESPUESTA"),
    (7, 5, "JUG. DERECHA/DEL"),
    (0, 8, "BUSCA LA LETRA"), (0, 9, "RECUERDA LA PALABRA"), (0, 10, "PLURALES"), (0, 11, "VERBOS"),
    (0, 12, "REVOLTIJO DE LETRAS"), (1, 8, "PALABRA MISTERIOSA"), (1, 9, "DERIVADOS"), (1, 10, "SINONIMOS"),
    (1, 11, "ANTONIMOS"), (1, 12, "LA LETRA LOCA"), (2, 8, "LA NUEVA PALABRA"), (2, 9, "TRUEQUE DE LETRAS"),
    (2, 10, "ALFAPUZZLE"), (2, 11, "REVOLTIJO"), (2, 12, "ACERTIJO GRAMATICAL"), (3, 8, "SUMA"),
    (3, 9, "RESTA"), (3, 10, "MULTIPLICACION"), (3, 11, "DIVISION"), (3, 12, "FRACC./DECIMALES"),
    (4, 8, "FRACC./PORCENTAJES"), (4, 9, "RATIOS"), (4, 10, "ALGEBRA"), (4, 11, "REPASO MATEMATICAS"),
    (4, 12, "EL SIGNO PERDIDO"), (5, 8, "CIENCIAS"), (5, 9, "CINE Y TELEVISION"),
    (5, 10, "HISTORIA Y GEOGRAFIA"), (5, 11, "GENERAL"), (5, 12, "\x9fQUE SOY?"),
    (6, 8, "EL NUMERO RELAMPAGO"), (6, 9, "BASIC"), (6, 10, "IMPRIMIR TEXTO"), (6, 11, "CALCULADORA"),
    (6, 12, "CARTUCHOS ADICION."), (7, 9, "OFF"), (7, 10, "NIVEL"), (7, 11, "1 JUGADOR"),
    (7, 12, "2 JUGADORES"),
]

# ---------------------------------------------------------------- T-state counted routines
# Each routine is a list of (asm, T-states); a block's cost is asserted against the cycle formula used for it.
TONE_HEAD = [("ld a, c", 4), ("xor a, #0x08", 7), ("and a, #0x28", 7), ("ld c, a", 4), ("out (0x12), a", 11),
             ("ld hl, (_tone_n)", 16)]
TONE_INNER = [("dec hl", 6), ("ld a, h", 4), ("or a, l", 4), ("jr nz, 2$", 12)]   # last pass: jr 7 -> -5
TONE_TAIL = [("dec de", 6), ("ld a, d", 4), ("or a, e", 4), ("jp nz, 1$", 10)]
TONE_FIXED = sum(t for _, t in TONE_HEAD) + sum(t for _, t in TONE_TAIL) - 5
TONE_STEP = sum(t for _, t in TONE_INNER)
assert TONE_STEP == 26 and TONE_FIXED == 68, (TONE_STEP, TONE_FIXED)


def tone_half(n):
    return TONE_FIXED + TONE_STEP * n


TONES = [262, 523, 1047, 2093, 3136]     # C4, C5, C6, C7, G7
TONE_SEC = 0.4

MS_HEAD = [("ld bc, #MS_K", 10)]
MS_INNER = [("dec bc", 6), ("ld a, b", 4), ("or a, c", 4), ("jr nz, 2$", 12)]
MS_TAIL = [("dec de", 6), ("ld a, d", 4), ("or a, e", 4), ("jp nz, 1$", 10)]
MS_K = round((CLOCK / 1000 - (10 + 24 - 5)) / 26)
MS_T = 10 + 26 * MS_K - 5 + 24
assert MS_T == sum(t for _, t in MS_HEAD) + sum(t for _, t in MS_INNER) * MS_K - 5 + sum(t for _, t in MS_TAIL)
assert abs(MS_T / CLOCK * 1000 - 1) < 0.002, MS_T

# interrupt counting loop: one pass = IRQ_LOOP_T cycles (the ISR's own time is not part of it)
IRQ_LOOP = [("ld hl, (_irq_cnt)", 16), ("inc hl", 6), ("ld (_irq_cnt), hl", 16), ("ld a, h", 4), ("or a, l", 4),
            ("jr z, 3$", 7), ("ld a, (_irq_n)", 13), ("cp a, #IRQ_SNAPS", 7), ("jp c, 1$", 10)]
IRQ_LOOP_T = sum(t for _, t in IRQ_LOOP)
assert IRQ_LOOP_T == 83, IRQ_LOOP_T

# Own IM 2 interrupt routine (reached through a vector table in RAM and a JP there). Every interrupt that stores a
# snapshot costs exactly IRQ2_T cycles on top of the loop: acknowledge, JP, and this path.
IRQ2_ACK = [("IM 2 acknowledge", 19), ("jp _irq2_isr (in RAM)", 10)]
IRQ2_ISR = [("push af", 11), ("push de", 11), ("push hl", 11), ("ld a, (_irq_n)", 13), ("cp a, #IRQ_SNAPS", 7),
            ("jr nc, 1$", 7), ("ld e, a", 4), ("ld d, #0", 7), ("ld hl, #_irq_snap", 10), ("add hl, de", 11),
            ("add hl, de", 11), ("ld de, (_irq_cnt)", 20), ("ld (hl), e", 7), ("inc hl", 6), ("ld (hl), d", 7),
            ("inc a", 4), ("ld (_irq_n), a", 13)]
IRQ2_END = [("pop hl", 10), ("pop de", 10), ("pop af", 10), ("ei", 4), ("reti", 14)]
IRQ2_T = sum(t for _, t in IRQ2_ACK + IRQ2_ISR + IRQ2_END)
assert IRQ2_T == 237, IRQ2_T

# gap between LCD writes: lcd_wait is call (17) + ld b (7) + djnz (13*N-5) + ret (10)
LCD_N = 24
LCD_WAIT_T = 17 + 7 + 13 * LCD_N - 5 + 10
assert LCD_WAIT_T / CLOCK > 50e-6, LCD_WAIT_T


def asm_block(lines):
    return "".join("\t\t%s\n" % s for s, _ in lines)


def cstr(s):
    return '"' + "".join(c if 0x20 <= ord(c) < 0x7F and c not in '"\\' else "\\x%02x\" \"" % ord(c) for c in s) + '"'


def main():
    vec = vectors()
    o = ["// Generated by gen_tables.py: do not edit.", "// SPDX-License-Identifier: GPL-3.0-or-later", ""]
    o.append("#define ALU_NVEC %d" % len(vec))
    o.append("static const byte alu_vec[ALU_NVEC * 3] = {")
    o += ["\t" + ", ".join("0x%02X" % x for x in v) + "," for v in vec]
    o.append("};")
    for i, (name, body, mask) in enumerate(OPS):
        o.append("static void alu_op%d(void) __naked { __asm\n\t%s\n\tret\n__endasm; }" % (i, body))
    o.append("typedef struct { void (*fn)(void); word crc; byte mask; const char *name; } alu_op_t;")
    o.append("#define ALU_NOPS %d" % len(OPS))
    o.append("static const alu_op_t alu_ops[ALU_NOPS] = {")
    for i, (name, body, mask) in enumerate(OPS):
        o.append("\t{ alu_op%d, 0x%04X, 0x%02X, %s }," % (i, alu_crc(name, mask), mask, cstr(name)))
    o.append("};\n")

    t = crc32_table()
    for k in range(4):
        o.append("static const byte crc32_t%d[256] = {" % k)
        for r in range(0, 256, 16):
            o.append("\t" + ", ".join("0x%02X" % ((t[i] >> (8 * k)) & 0xFF) for i in range(r, r + 16)) + ",")
        o.append("};")
    o.append("#define NBANKS %d" % len(BANKS))
    o.append("static const byte bank_crc[NBANKS][4] = {")
    o += ["\t{ 0x%02X, 0x%02X, 0x%02X, 0x%02X }," % tuple((c >> s) & 0xFF for s in (0, 8, 16, 24)) for c, _ in BANKS]
    o.append("};")
    o.append("static const char * const bank_name[NBANKS] = { %s };\n" % ", ".join(cstr(n) for _, n in BANKS))

    assert len(KEYS) == 94 and len({(c, r) for c, r, _ in KEYS}) == 94
    assert all(len(n) <= 20 for _, _, n in KEYS)
    o.append("#define NKEYS %d" % len(KEYS))
    o.append("static const byte key_sc[NKEYS] = { %s };" % ", ".join(str(r * 8 + c) for c, r, _ in KEYS))
    o.append("static const char * const key_name[NKEYS] = {")
    o += ["\t%s," % cstr(n) for _, _, n in KEYS]
    o.append("};\n")

    o.append("#define NTONES %d" % len(TONES))
    o.append("static const word tone_tab[NTONES][2] = {   // { inner count, half periods }")
    for f in TONES:
        n = round((CLOCK / (2 * f) - TONE_FIXED) / TONE_STEP)
        half = tone_half(n)
        real = CLOCK / (2 * half)
        assert abs(real / f - 1) < 0.01, (f, real)
        o.append("\t{ %d, %d },   // %d Hz -> %.1f Hz, %d T per half period" % (n, round(TONE_SEC * 2 * real), f, real, half))
    o.append("};\n")

    o.append("#define MS_K %d   // %d T per millisecond loop pass" % (MS_K, MS_T))
    o.append("#define LCD_N %d   // %d T between LCD writes" % (LCD_N, LCD_WAIT_T))
    o.append("#define IRQ_LOOP_T %d" % IRQ_LOOP_T)
    o.append("#define IRQ2_T %d   // own IM 2 routine per stored snapshot, acknowledge included" % IRQ2_T)
    o.append("#define CLOCK_HZ %dUL" % CLOCK)
    o.append("")
    # T-counted routines; parameters and results go through globals
    o.append("""// Square wave on the speaker: tone_cnt half periods of %d + %d * tone_n T-states; bit 0 of port 0x12 stays 0.
static void tone_play(void) __naked { __asm
\t\tld a, (_p12_led)
\t\tld c, a
\t\tld de, (_tone_cnt)
\t1$:
%s\t2$:
%s%s\t\tld a, c
\t\tand a, #0x20
\t\tout (0x12), a
\t\tret
__endasm; }
""" % (TONE_FIXED, TONE_STEP, asm_block(TONE_HEAD), asm_block(TONE_INNER), asm_block(TONE_TAIL)))
    o.append("""// Busy wait of ms_n milliseconds (%d T each), interrupts untouched.
static void delay_ms(void) __naked { __asm
\t\tld de, (_ms_n)
\t1$:
%s\t2$:
%s%s\t\tret
__endasm; }
""" % (MS_T, asm_block(MS_HEAD), asm_block(MS_INNER), asm_block(MS_TAIL)))
    o.append("""// Counts loop passes (%d T each) with interrupts enabled; irq_hook stores irq_cnt at every interrupt.
// Ends after IRQ_SNAPS interrupts or when irq_cnt wraps (no interrupts).
static void irq_count(void) __naked { __asm
\t\tld a, i
\t\tld a, #0
\t\tjp po, 0$
\t\tinc a
\t0$:
\t\tld (_irq_iff0), a
\t\tei
\t1$:
%s\t3$:
\t\tld a, i
\t\tdi
\t\tld a, #0
\t\tjp po, 4$
\t\tinc a
\t4$:
\t\tld (_irq_iff1), a
\t\tret
__endasm; }
""" % (IRQ_LOOP_T, asm_block(IRQ_LOOP)))
    o.append("""// IM 2 interrupt routine: stores irq_cnt like irq_hook; %d T per stored snapshot including acknowledge and JP.
static void irq2_isr(void) __naked { __asm
%s\t1$:
%s__endasm; }
""" % (IRQ2_T, asm_block(IRQ2_ISR), asm_block(IRQ2_END)))
    open(OUT, "w").write("\n".join(o) + "\n")
    print("%s: %d ALU ops x %d vectors, %d keys, %d tones" % (OUT, len(OPS), len(vec), len(KEYS), len(TONES)))


if __name__ == "__main__":
    main()
