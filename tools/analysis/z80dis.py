#!/usr/bin/env python3
"""Table-free Z80 decoder (x/y/z/p/q decomposition) with control-flow classification.

decode(rd, pc) -> Insn(pc, length, text, kind, target, cond, bytes)
  kind: 'seq' | 'jp' | 'jr' | 'djnz' | 'call' | 'ret' | 'reti' | 'jpind' | 'rst' | 'halt' | 'bad'
  target: static target address or None
Undocumented DD/FD/ED forms are decoded where unambiguous (IXH/IXL, SLL); other ED holes -> 'bad' (NOP-like, len 2).
Cross-checked against MAME unidasm by tools/check_dis.py.
"""
from collections import namedtuple

Insn = namedtuple("Insn", "pc length text kind target cond bytes")

R = ["b", "c", "d", "e", "h", "l", "(hl)", "a"]
RP = ["bc", "de", "hl", "sp"]
RP2 = ["bc", "de", "hl", "af"]
CC = ["nz", "z", "nc", "c", "po", "pe", "p", "m"]
ALU = ["add a,", "adc a,", "sub ", "sbc a,", "and ", "xor ", "or ", "cp "]
ROT = ["rlc", "rrc", "rl", "rr", "sla", "sra", "sll", "srl"]
IM = [0, 0, 1, 2, 0, 0, 1, 2]


def _idx(ix, d):
    return "(%s%s%s)" % (ix, "-" if d < 0 else "+", "$%02X" % abs(d))


def h8(v):
    return "$%02X" % (v & 0xFF)


def h16(v):
    return "$%04X" % (v & 0xFFFF)


def decode(rd, pc):
    start = pc
    b = []

    def fetch():
        nonlocal pc
        v = rd(pc) & 0xFF
        b.append(v)
        pc = (pc + 1) & 0xFFFF
        return v

    def imm16():
        lo = fetch()
        hi = fetch()
        return lo | (hi << 8)

    def s8():
        v = fetch()
        return v - 256 if v & 0x80 else v

    def done(text, kind="seq", target=None, cond=None):
        return Insn(start, len(b), text, kind, target, cond, bytes(b))

    op = fetch()
    if op in (0xDD, 0xFD):
        ix = "ix" if op == 0xDD else "iy"
        # chains of prefixes: the last one wins, earlier behave as NOP
        while True:
            op = fetch()
            if op in (0xDD, 0xFD):
                ix = "ix" if op == 0xDD else "iy"
                continue
            break
        if op == 0xED:
            return done("nop", "bad")
        if op == 0xCB:
            d = s8()
            op2 = fetch()
            x, y, z = op2 >> 6, (op2 >> 3) & 7, op2 & 7
            mem = _idx(ix, d)
            if x == 0:
                t = "%s %s" % (ROT[y], mem)
                if z != 6:
                    t += ",%s" % R[z]
            elif x == 1:
                t = "bit %d,%s" % (y, mem)
            else:
                t = "%s %d,%s" % ("res" if x == 2 else "set", y, mem)
                if z != 6:
                    t += ",%s" % R[z]
            return done(t)
        return _decode_main(op, fetch, imm16, s8, done, ix)
    if op == 0xED:
        op = fetch()
        x, y, z = op >> 6, (op >> 3) & 7, op & 7
        p, q = y >> 1, y & 1
        if x == 1:
            if z == 0:
                return done("in %s,(c)" % ("f" if y == 6 else R[y]))
            if z == 1:
                return done("out (c),%s" % ("0" if y == 6 else R[y]))
            if z == 2:
                return done("%s hl,%s" % ("sbc" if q == 0 else "adc", RP[p]))
            if z == 3:
                nn = imm16()
                return done("ld (%s),%s" % (h16(nn), RP[p]) if q == 0 else "ld %s,(%s)" % (RP[p], h16(nn)))
            if z == 4:
                return done("neg")
            if z == 5:
                return done("reti" if y == 1 else "retn", "reti" if y == 1 else "ret")
            if z == 6:
                return done("im %d" % IM[y])
            if z == 7:
                return done(["ld i,a", "ld r,a", "ld a,i", "ld a,r", "rrd", "rld", "nop", "nop"][y])
        if x == 2 and z <= 3 and y >= 4:
            names = [["ldi", "cpi", "ini", "outi"], ["ldd", "cpd", "ind", "outd"],
                     ["ldir", "cpir", "inir", "otir"], ["lddr", "cpdr", "indr", "otdr"]]
            return done(names[y - 4][z])
        return done("nop", "bad")
    if op == 0xCB:
        op = fetch()
        x, y, z = op >> 6, (op >> 3) & 7, op & 7
        if x == 0:
            return done("%s %s" % (ROT[y], R[z]))
        if x == 1:
            return done("bit %d,%s" % (y, R[z]))
        return done("%s %d,%s" % ("res" if x == 2 else "set", y, R[z]))
    return _decode_main(op, fetch, imm16, s8, done, None)


def _decode_main(op, fetch, imm16, s8, done, ix):
    x, y, z = op >> 6, (op >> 3) & 7, op & 7
    p, q = y >> 1, y & 1
    # register-name resolvers with index substitution
    def reg(i):
        if ix is None:
            return R[i]
        if i == 4:
            return ix + "h"
        if i == 5:
            return ix + "l"
        return R[i]

    def hl():
        return ix or "hl"

    def rp(i):
        return hl() if i == 2 else RP[i]

    def rp2(i):
        return hl() if i == 2 else RP2[i]

    def mem():
        if ix is None:
            return "(hl)"
        d = s8()
        return _idx(ix, d)

    if x == 0:
        if z == 0:
            if y == 0:
                return done("nop")
            if y == 1:
                return done("ex af,af'")
            d = s8()
            return _rel(done, y, d)
        if z == 1:
            if q == 0:
                nn = imm16()
                return done("ld %s,%s" % (rp(p), h16(nn)))
            return done("add %s,%s" % (hl(), rp(p)))
        if z == 2:
            if q == 0:
                if p == 0:
                    return done("ld (bc),a")
                if p == 1:
                    return done("ld (de),a")
                nn = imm16()
                return done("ld (%s),%s" % (h16(nn), hl()) if p == 2 else "ld (%s),a" % h16(nn))
            if p == 0:
                return done("ld a,(bc)")
            if p == 1:
                return done("ld a,(de)")
            nn = imm16()
            return done("ld %s,(%s)" % (hl(), h16(nn)) if p == 2 else "ld a,(%s)" % h16(nn))
        if z == 3:
            return done(("inc %s" if q == 0 else "dec %s") % rp(p))
        if z in (4, 5):
            if y == 6:
                m = mem()
            else:
                m = reg(y)
            return done(("inc %s" if z == 4 else "dec %s") % m)
        if z == 6:
            if y == 6:
                m = mem()
                n = fetch()
                return done("ld %s,%s" % (m, h8(n)))
            n = fetch()
            return done("ld %s,%s" % (reg(y), h8(n)))
        return done(["rlca", "rrca", "rla", "rra", "daa", "cpl", "scf", "ccf"][y])
    if x == 1:
        if op == 0x76:
            return done("halt", "halt")
        if y == 6:
            m = mem()
            return done("ld %s,%s" % (m, R[z]))
        if z == 6:
            m = mem()
            return done("ld %s,%s" % (R[y], m))
        return done("ld %s,%s" % (reg(y), reg(z)))
    if x == 2:
        src = mem() if z == 6 else reg(z)
        return done("%s%s" % (ALU[y], src))
    # x == 3
    if z == 0:
        return done("ret %s" % CC[y], "ret", None, CC[y])
    if z == 1:
        if q == 0:
            return done("pop %s" % rp2(p))
        if p == 0:
            return done("ret", "ret")
        if p == 1:
            return done("exx")
        if p == 2:
            return done("jp (%s)" % hl(), "jpind")
        return done("ld sp,%s" % hl())
    if z == 2:
        nn = imm16()
        return done("jp %s,%s" % (CC[y], h16(nn)), "jp", nn, CC[y])
    if z == 3:
        if y == 0:
            nn = imm16()
            return done("jp %s" % h16(nn), "jp", nn)
        if y == 2:
            n = fetch()
            return done("out (%s),a" % h8(n))
        if y == 3:
            n = fetch()
            return done("in a,(%s)" % h8(n))
        if y == 4:
            return done("ex (sp),%s" % hl())
        if y == 5:
            return done("ex de,hl")
        if y == 6:
            return done("di")
        if y == 7:
            return done("ei")
    if z == 4:
        nn = imm16()
        return done("call %s,%s" % (CC[y], h16(nn)), "call", nn, CC[y])
    if z == 5:
        if q == 0:
            return done("push %s" % rp2(p))
        if p == 0:
            nn = imm16()
            return done("call %s" % h16(nn), "call", nn)
        return done("nop", "bad")
    if z == 6:
        n = fetch()
        return done("%s%s" % (ALU[y], h8(n)))
    return done("rst %s" % h8(y * 8), "rst", y * 8)


def _rel(done, y, d):
    """JR/DJNZ: the target depends on the address after the instruction."""
    ins = done("")  # to get start/len
    tgt = (ins.pc + ins.length + d) & 0xFFFF
    if y == 2:
        return done("djnz %s" % h16(tgt), "djnz", tgt)
    if y == 3:
        return done("jr %s" % h16(tgt), "jr", tgt)
    c = CC[y - 4]
    return done("jr %s,%s" % (c, h16(tgt)), "jr", tgt, c)


def disasm_range(rd, start, end):
    pc = start
    while pc < end:
        i = decode(rd, pc)
        yield i
        pc = (pc + i.length) & 0xFFFF
