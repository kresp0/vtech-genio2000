#!/usr/bin/env python3
"""Recursive-descent Z80 tracer over bank *images*.

An image is (bank, window): 16 KiB bank k visible at logical window W (0x0000, 0x4000 or 0x8000).
Window 0x0000 is always bank 0 (the firmware never writes port 0x00; CONFIRMED statically, see docs).
Control flow that stays inside the image or goes to window 0 (bank 0) is followed exactly.
Transfers to another non-zero window are recorded as *far* references (resolved by the caller of this
module, from MAME dynamic traces or explicit seeds): they are never guessed here.

API:
  Tracer(rom).run(seeds)  where seeds = [(bank, window, addr, why)]
  .code[(bank,window)]  -> {addr: Insn}
  .far                  -> list of (src_bank, src_win, src_pc, kind, target)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import z80dis

BANK = 0x4000


class Tracer:
    def __init__(self, rom):
        self.rom = rom
        self.code = {}       # (bank,win) -> {addr: Insn}
        self.far = []        # (sb, sw, spc, kind, target)
        self.labels = {}     # (bank,win,addr) -> set(reasons)
        self.callers = {}    # (bank,win,addr) -> list[(sb,sw,spc,kind)]
        self.jpind = []      # (bank,win,pc,text)
        self.todo = []

    def rd_factory(self, bank, win):
        base = bank * BANK
        rom = self.rom

        def rd(a):
            a &= 0xFFFF
            if a < 0x4000 and win != 0:   # window 0 always bank 0
                return rom[a]
            if a < 0x4000 and win == 0:
                return rom[a]
            if win <= a < win + BANK:
                return rom[base + a - win]
            return 0xFF  # outside the image: unknown (only used for operand fetch at the image edge)
        return rd

    def resolve(self, bank, win, target):
        """Return the image containing `target` when seen from (bank, win); None if ambiguous."""
        if target < 0x4000:
            return (0, 0)
        if win and win <= target < win + BANK:
            return (bank, win)
        return None

    def add_seed(self, bank, win, addr, why, src=None):
        key = (bank, win, addr)
        self.labels.setdefault(key, set()).add(why)
        if src is not None:
            self.callers.setdefault(key, []).append(src)
        self.todo.append(key)

    def run(self, seeds):
        for s in seeds:
            self.add_seed(*s)
        while self.todo:
            bank, win, pc = self.todo.pop()
            self._walk(bank, win, pc)
        return self

    def _walk(self, bank, win, pc):
        img = (0, 0) if pc < 0x4000 else (bank, win)
        if pc < 0x4000:
            bank, win = 0, 0
        code = self.code.setdefault(img, {})
        rd = self.rd_factory(bank, win)
        lim_lo, lim_hi = (0, 0x4000) if img == (0, 0) else (win, win + BANK)
        while True:
            if pc in code:
                return
            if not (lim_lo <= pc < lim_hi):
                return
            i = z80dis.decode(rd, pc)
            # instruction must not straddle the end of the image
            if pc + i.length > lim_hi:
                return
            code[pc] = i
            k = i.kind
            if k == "bad":
                return
            if k in ("jp", "jr", "djnz", "call", "rst"):
                t = i.target
                tw = self.resolve(bank, win, t)
                kind = "call" if k in ("call", "rst") else "jump"
                if tw is None:
                    self.far.append((bank, win, pc, kind, t))
                else:
                    self.add_seed(tw[0], tw[1], t, "%s_target" % kind, (bank, win, pc, kind))
                if k == "jp" and i.cond is None:
                    return
                if k == "jr" and i.cond is None:
                    return
            elif k in ("ret", "reti", "halt"):
                if i.cond is None:
                    return
            elif k == "jpind":
                self.jpind.append((bank, win, pc, i.text))
                return
            pc += i.length

    def coverage(self, bank, win):
        code = self.code.get((bank, win), {})
        n = sum(i.length for i in code.values())
        return n
