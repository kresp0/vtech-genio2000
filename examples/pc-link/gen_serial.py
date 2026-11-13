#!/usr/bin/env python3
# Generates serial.h for the pc-link cartridge: the bit-banged UART receiver (printer BUSY, port 0x11 bit 5) and
# transmitter (printer DATA0, port 0x10) for 2400/4800/9600/19200 baud, a millisecond delay and the LCD write wait.
# Every routine is a list of (asm, T-states); the sampling and bit-edge instants are asserted against the ideal ones.
# Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later

CLOCK = 6131790          # Hz, measured on the CPU CLK pin of the unit (docs/hardware/CLOCK_AND_SOUND.md)
BAUDS = [2400, 4800, 9600, 19200]           # the rates tested on the unit (2026-11-13): routines kept unchanged
FAST = [38400, 57600, 76800]                # no stop-bit check, tighter polling (rx_fast)
CAPTURE = [115200, 128000]   # experimental: line captured with INI, decoded afterwards (cap_decode)
CAPBUF, CAP_BLOCKS = 0xCA00, 34             # 34 blocks of 128 samples: CA00-DAFF
CAP_SAMPLE_T, CAP_GAP_T = 16, 14            # INI; DEC D / JP NZ after each block
TRIM_BAUDS = [9600]                         # extra polarity-A receivers with the bit time scaled by 1 + TRIMS/100
TRIMS = [t for t in range(-7, 8) if t]
RXBUF = 0xC800           # 256-byte aligned receive buffer: L is the byte count
OUT = "serial.h"

ST_IDLE, ST_END, ST_FULL, ST_BREAK, ST_STUCK, ST_CAP = 0, 1, 2, 3, 4, 5

# Start-bit polling loop: three checks of 25 T, then the timeout counter (24 T). The gaps between the sampling
# instants of consecutive checks are 25, 25 and 49 T, so the mean detection latency for a random edge is:
POLL_GAPS = [25, 25, 49]
LAT = sum(g * g / 2 for g in POLL_GAPS) / sum(POLL_GAPS)
WAIT_ITER_T = sum(POLL_GAPS)
MARK_ITER_T = 49
MAX_ERR_T = 3            # largest allowed distance of a sampling instant or bit edge from the ideal one


def pads(n, r="a"):
    """nop (4 T) and ld r,#0 (7 T) adding up to n, fewest instructions; None if impossible."""
    for b in range(0, n // 7 + 1):
        if (n - 7 * b) % 4 == 0:
            return [("nop", 4)] * ((n - 7 * b) // 4) + [("ld %s, #0" % r, 7)] * b
    return None


class Gen:
    def __init__(self, loop_reg="a", pad_reg="a"):
        """loop_reg / pad_reg: registers the delays may destroy (the flags are destroyed too)."""
        self.lab = 0
        self.lr, self.pr = loop_reg, pad_reg

    def label(self):
        self.lab += 1
        return "%d$" % self.lab

    def delay(self, n):
        """Exactly n T-states (A and flags are destroyed), or None."""
        if n < 0:
            return None
        if n < 40:
            return pads(n, self.pr)
        for k in range((n - 7) // 14, 0, -1):
            p = pads(n - 7 - 14 * k, self.pr)
            if p is not None and k <= 255:
                l = self.label()
                return [("ld %s, #%d" % (self.lr, k), 7), (l[:-1] + "$: dec %s" % self.lr, 4),
                        ("jp nz, " + l, 10)] + p
        return None

    def delay_near(self, n):
        """The achievable delay closest to n: (code, T)."""
        for d in range(0, 8):
            for m in (n + d, n - d):
                c = self.delay(m)
                if c is not None:
                    return c, m
        raise AssertionError("no delay near %d" % n)


def cost(code, loops=True):
    """T-states of straight-line code; a delay loop 'ld a,#k / dec a / jp nz' counts k passes."""
    t, i = 0, 0
    while i < len(code):
        a, n = code[i]
        if loops and a[:3] == "ld " and a[4:8] == ", #" and i + 2 < len(code) and code[i + 1][0].endswith("dec " + a[3]) \
                and code[i + 2][0].startswith("jp nz"):
            k = int(a.split("#")[1])
            t += 7 + 14 * k
            i += 3
            continue
        t += n
        i += 1
    return t


def emit(code):
    out = []
    for a, _ in code:
        if "$: " in a:
            l, ins = a.split(": ", 1)
            out.append("%s:\t%s" % (l, ins))
        else:
            out.append("\t\t" + a)
    return out


def rx_routine(baud, pol, gap, trim=0):
    """Receives a burst into RXBUF. pol 0: BUSY bit 5 = 1 while the wire is low (space), as on the GL4000.
    trim: the bit time is (1 + trim/100) times the nominal one, as if the PC were trim % fast."""
    g = Gen()
    bit = CLOCK / baud * (1 + trim / 100)
    space, mark = ("nz", "z") if pol == 0 else ("z", "nz")
    data_bit = ("cp a, #1", 7) if pol == 0 else ("add a, #0xE0", 7)   # carry = received bit
    name = "rx_%d_%s" % (baud, "ab"[pol]) + ("" if not trim else "_%s%d" % ("pm"[trim < 0], abs(trim)))
    W, ST, FERR, FULL, EXIT, M, READY, BRK = ["%s_%s" % (name, s) for s in
                                              ("w", "st", "ferr", "full", "exit", "m", "ready", "brk")]
    L = ["static void %s(void) __naked { __asm" % name,
         "\t\tld hl, #0x%04X" % RXBUF, "\t\tld b, #0x20", "\t\txor a, a", "\t\tld (_rx_ferr), a",
         "\t\tld de, (_rx_idle)",
         # the line must be idle (mark) before a start bit counts
         "%s:\tin a, (0x11)" % M, "\t\tand a, b", "\t\tjp %s, %s" % (mark, READY),
         "\t\tdec de", "\t\tld a, d", "\t\tor a, e", "\t\tjp nz, %s" % M,
         "\t\tld a, #%d" % ST_STUCK, "\t\tjp %s" % EXIT,
         "%s:\tld de, (_rx_idle)" % READY]
    poll = [("in a, (0x11)", 11), ("and a, b", 4), ("jp %s, %s" % (space, ST), 10)]
    assert [cost(poll)] * 2 + [cost(poll) + 24] == POLL_GAPS
    L.append("%s:\tin a, (0x11)" % W)
    L += emit(poll[1:] + poll * 2)
    L += ["\t\tdec de", "\t\tld a, d", "\t\tor a, e", "\t\tjp nz, %s" % W,      # 6 + 4 + 4 + 10 = 24 T
          "\t\tld a, l", "\t\tor a, a", "\t\tld a, #%d" % ST_IDLE, "\t\tjp z, %s" % EXIT,
          "\t\tld a, #%d" % ST_END, "\t\tjp %s" % EXIT]

    # time 0 = start of the IN that saw the start bit; the instants below are the starts of the sampling INs
    ideal = [0.5 * bit - LAT] + [(1.5 + i) * bit - LAT for i in range(8)] + [9.5 * bit - LAT]
    t = cost(poll)
    body = []
    samples = []
    for i, target in enumerate(ideal):
        code, d = g.delay_near(round(target) - t)
        body += code
        t += d
        samples.append(t)
        assert abs(t - target) <= MAX_ERR_T, (name, i, t, target)
        if i == 0:
            s = [("in a, (0x11)", 11), ("and a, b", 4), ("jp %s, %s" % (mark, W), 10)]   # false start: back to waiting
        elif i < 9:
            s = [("in a, (0x11)", 11), ("and a, b", 4), data_bit, ("rr c", 8)]
        else:
            s = [("in a, (0x11)", 11), ("and a, b", 4), ("jp %s, %s" % (space, FERR), 10)]
        body += s
        t += cost(s)
    store = [("ld (hl), c", 7), ("inc l", 4), ("jp z, " + FULL, 10), ("ld de, #%d" % gap, 10), ("jp " + W, 10)]
    body += store
    back = cost([("in a, (0x11)", 11), ("and a, b", 4), ("jp nz, x", 10)] + store)
    # the next start edge comes half a bit after the stop sample, less the latency of this byte's detection
    assert back < 0.5 * bit - (max(POLL_GAPS) - LAT), (name, back, bit)
    for a, n in zip(samples[1:], samples[2:]):
        assert abs((n - a) - bit) <= 2 * MAX_ERR_T
    L.append("%s:" % ST)
    L += emit(body)
    L += ["%s:\tld (hl), c" % FERR,
          "\t\tld a, (_rx_ferr)", "\t\tinc a", "\t\tjr z, %s_sat" % FERR, "\t\tld (_rx_ferr), a",
          "%s_sat:\tinc l" % FERR, "\t\tjp z, %s" % FULL,
          "\t\tld de, #%d" % gap,
          # a stop bit at space: wait for the line to return to mark, or report a break
          "%s:\tin a, (0x11)" % BRK, "\t\tand a, b", "\t\tjp %s, %s" % (mark, W),
          "\t\tdec de", "\t\tld a, d", "\t\tor a, e", "\t\tjp nz, %s" % BRK,
          "\t\tld a, #%d" % ST_BREAK, "\t\tjp %s" % EXIT,
          "%s:\tld a, #%d" % (FULL, ST_FULL),
          "%s:\tld (_rx_stat), a" % EXIT, "\t\tld a, l", "\t\tld (_rx_cnt), a", "\t\tret",
          "__endasm; }", ""]
    return name, L, samples


FAST_GAPS = [25] * 7 + [39]     # eight checks, then DEC E / JP NZ; every 256 passes DEC D / JP NZ adds 14 T
FAST_LAT = sum(g * g / 2 for g in FAST_GAPS) / sum(FAST_GAPS)


def de_count(n):
    """DE for a DEC E / DEC D double loop of n passes (n <= 65280)."""
    d = (n - 1) // 256 + 1
    return (d << 8) | ((n - 256 * (d - 1)) & 0xFF)


def rx_fast(baud, pol, idle, gap):
    """Receiver for rates above 19200: the stop bit is not sampled (the store and the return to the polling loop
    happen while it is on the line) and the polling loop checks the line every 25 T between counter updates."""
    g = Gen()
    bit = CLOCK / baud
    space, mark = ("nz", "z") if pol == 0 else ("z", "nz")
    data_bit = ("cp a, #1", 7) if pol == 0 else ("add a, #0xE0", 7)
    name = "rx_%d_%s" % (baud, "ab"[pol])
    W, ST, FULL, EXIT, M, READY = ["%s_%s" % (name, s) for s in ("w", "st", "full", "exit", "m", "ready")]
    L = ["static void %s(void) __naked { __asm" % name,
         "\t\tld hl, #0x%04X" % RXBUF, "\t\tld b, #0x20", "\t\txor a, a", "\t\tld (_rx_ferr), a",
         "\t\tld de, (_rx_idle)",
         "%s:\tin a, (0x11)" % M, "\t\tand a, b", "\t\tjp %s, %s" % (mark, READY),
         "\t\tdec de", "\t\tld a, d", "\t\tor a, e", "\t\tjp nz, %s" % M,
         "\t\tld a, #%d" % ST_STUCK, "\t\tjp %s" % EXIT,
         "%s:\tld de, #0x%04X" % (READY, de_count(idle))]
    poll = [("in a, (0x11)", 11), ("and a, b", 4), ("jp %s, %s" % (space, ST), 10)]
    assert [cost(poll)] * 7 + [cost(poll) + 14] == FAST_GAPS
    L.append("%s:\tin a, (0x11)" % W)
    L += emit(poll[1:] + poll * 7)
    L += ["\t\tdec e", "\t\tjp nz, %s" % W, "\t\tdec d", "\t\tjp nz, %s" % W,
          "\t\tld a, l", "\t\tor a, a", "\t\tld a, #%d" % ST_IDLE, "\t\tjp z, %s" % EXIT,
          "\t\tld a, #%d" % ST_END, "\t\tjp %s" % EXIT]
    ideal = [0.5 * bit - FAST_LAT] + [(1.5 + i) * bit - FAST_LAT for i in range(8)]
    t = cost(poll)
    body, samples = [], []
    for i, target in enumerate(ideal):
        code, d = g.delay_near(round(target) - t)
        body += code
        t += d
        samples.append(t)
        assert abs(t - target) <= MAX_ERR_T, (name, i, t, target)
        if i == 0:
            s = [("in a, (0x11)", 11), ("and a, b", 4), ("jp %s, %s" % (mark, W), 10)]
        else:
            s = [("in a, (0x11)", 11), ("and a, b", 4), data_bit, ("rr c", 8)]
        body += s
        t += cost(s)
    store = [("ld (hl), c", 7), ("inc l", 4), ("jp z, " + FULL, 10), ("ld de, #0x%04X" % de_count(gap), 10),
             ("jp " + W, 10)]
    body += store
    back = cost([("in a, (0x11)", 11), ("and a, b", 4), data_bit, ("rr c", 8)] + store)
    # the next start edge comes 1.5 bits after the last data sample
    assert back < 1.5 * bit - (max(FAST_GAPS) - FAST_LAT), (name, back, bit)
    L.append("%s:" % ST)
    L += emit(body)
    L += ["%s:\tld a, #%d" % (FULL, ST_FULL),
          "%s:\tld (_rx_stat), a" % EXIT, "\t\tld a, l", "\t\tld (_rx_cnt), a", "\t\tret",
          "__endasm; }", ""]
    return name, L, samples


def rx_capture():
    """Waits for a sync byte 00 (polarity from pol), then from its stop bit stores port 0x11 every 16 T into
    CAPBUF with INI: sample i is taken 16 i + 14 (i / 128) T after the first one."""
    blocks = ["\t\tini"] * 128
    return ["static void rx_capture(void) __naked { __asm",
            "\t\tld a, (_pol)", "\t\tor a, a", "\t\tld b, #0", "\t\tjr z, 1$", "\t\tld b, #0x20",
            "1$:\tld de, (_rx_idle)",
            "2$:\tin a, (0x11)", "\t\txor a, b", "\t\tand a, #0x20", "\t\tjr z, 3$",     # wait for mark
            "\t\tdec de", "\t\tld a, d", "\t\tor a, e", "\t\tjr nz, 2$",
            "\t\tld a, #%d" % ST_STUCK, "\t\tjp 6$",
            "3$:\tld de, (_rx_idle)",
            "4$:\tin a, (0x11)", "\t\txor a, b", "\t\tand a, #0x20", "\t\tjr nz, 5$",    # wait for space
            "\t\tdec de", "\t\tld a, d", "\t\tor a, e", "\t\tjr nz, 4$",
            "\t\tld a, #%d" % ST_IDLE, "\t\tjp 6$",
            # a sync byte 00: the line must stay low for about 6 bits (45 T a pass), then capture from its stop bit
            "5$:\tld a, (_cap_sync)", "\t\tld e, a",
            "8$:\tin a, (0x11)", "\t\txor a, b", "\t\tand a, #0x20", "\t\tjr z, 3$",
            "\t\tdec e", "\t\tjr nz, 8$",
            "\t\tld d, #0",
            "9$:\tin a, (0x11)", "\t\txor a, b", "\t\tand a, #0x20", "\t\tjr z, 10$",
            "\t\tdec d", "\t\tjr nz, 9$",
            "\t\tjp 1$",                                   # still low after about 1.4 ms: a break
            "10$:\tld hl, #0x%04X" % CAPBUF, "\t\tld c, #0x11", "\t\tld d, #%d" % CAP_BLOCKS,
            "7$:"] + blocks + [
            "\t\tdec d", "\t\tjp nz, 7$",
            "\t\tld a, #%d" % ST_CAP,
            "6$:\tld (_rx_stat), a", "\t\tret", "__endasm; }", ""]


TRBUF, TREND = 0xC200, 0xC800              # transition list of cap_scan: one byte per change (0 = 255 samples more)


def cap_scan():
    """Turns the capture into the distances (in samples) between level changes; tr_lvl0 = level of sample 0
    (0x20 = space), tr_end = end of the list. 45 T a sample without a change."""
    endh = (CAPBUF + CAP_BLOCKS * 128) >> 8
    return ["static void cap_scan(void) __naked { __asm",
            "\t\tld a, (_pol)", "\t\tor a, a", "\t\tld c, #0", "\t\tjr z, 1$", "\t\tld c, #0x20",
            "1$:\tld hl, #0x%04X" % CAPBUF, "\t\tld (_tr_last), hl", "\t\tld de, #0x%04X" % TRBUF,
            "\t\tld a, (hl)", "\t\txor a, c", "\t\tand a, #0x20", "\t\tld b, a", "\t\tld (_tr_lvl0), a",
            "2$:\tld a, (hl)", "\t\txor a, c", "\t\tand a, #0x20", "\t\tcp a, b", "\t\tjr nz, 4$",
            "3$:\tinc l", "\t\tjr nz, 2$", "\t\tinc h", "\t\tld a, h", "\t\tcp a, #0x%02X" % endh, "\t\tjr nz, 2$",
            "\t\tjr 9$",
            "4$:\tld b, a", "\t\tld (_tr_p), hl", "\t\tpush bc", "\t\tld bc, (_tr_last)", "\t\tor a, a",
            "\t\tsbc hl, bc", "\t\tld bc, (_tr_p)", "\t\tld (_tr_last), bc",
            "5$:\tld a, h", "\t\tor a, a", "\t\tjr z, 6$",
            "\t\txor a, a", "\t\tld (de), a", "\t\tinc de", "\t\tld bc, #-255", "\t\tadd hl, bc", "\t\tjr 5$",
            "6$:\tld a, l", "\t\tld (de), a", "\t\tinc de",
            "\t\tpop bc", "\t\tld hl, (_tr_p)",
            "\t\tld a, d", "\t\tcp a, #0x%02X" % ((TREND >> 8) - 1), "\t\tjr c, 3$",   # stop 256 bytes early
            "9$:\tld (_tr_end), de", "\t\tret", "__endasm; }", ""]


SCOPE_BYTES = CAP_BLOCKS * 128 // 8          # the packed recording: one bit a sample, 1 = space


def cap_pack():
    """Packs the recording into TRBUF, one bit a sample (LSB first, 1 = space), for the scope packets."""
    end = TRBUF + SCOPE_BYTES
    return ["static void cap_pack(void) __naked { __asm",
            "\t\tld a, (_pol)", "\t\tor a, a", "\t\tld c, #0", "\t\tjr z, 1$", "\t\tld c, #0x20",
            "1$:\tld de, #0x%04X" % CAPBUF, "\t\tld hl, #0x%04X" % TRBUF,
            "2$:\tld b, #8",
            "3$:\tld a, (de)", "\t\txor a, c", "\t\tand a, #0x20", "\t\tadd a, #0xE0", "\t\trr (hl)",
            "\t\tinc de", "\t\tdjnz 3$",
            "\t\tinc hl", "\t\tld a, l", "\t\tcp a, #0x%02X" % (end & 0xFF), "\t\tjr nz, 2$",
            "\t\tld a, h", "\t\tcp a, #0x%02X" % (end >> 8), "\t\tjr nz, 2$",
            "\t\tret", "__endasm; }", ""]


def tx_turbo(baud):
    """Transmitter for the capture rates: A = ~byte, OUT then RRCA (15 T a bit); bit 0 of the port value is the
    inverted line level, the other DATA pins carry the rest of the byte. The stop bit lasts at least one bit."""
    g = Gen("b", "c")         # A holds the byte being sent
    bit = CLOCK / baud
    name = "tx_%d" % baud
    L = ["static void %s(void) __naked { __asm" % name,
         "\t\tld hl, (_tx_ptr)", "\t\tld de, (_tx_len)", "\t\tld a, d", "\t\tor a, e", "\t\tret z",
         "%s_b:\tld a, #0xFF" % name]
    # time 0 = start of the OUT of the start bit
    code = [("out (0x10), a", 11), ("ld a, (hl)", 7), ("cpl", 4)]
    t = cost(code)
    for k in range(1, 10):
        c, d = g.delay_near(round(k * bit) - t - (4 if k == 9 else 0))
        assert d >= 0
        code += c
        t += d
        if k == 9:
            code.append(("xor a, a", 4))
            t += 4
        assert abs(t - k * bit) <= MAX_ERR_T, (name, k, t, k * bit)
        code.append(("out (0x10), a", 11))
        t += 11
        if k < 9:
            code.append(("rrca", 4))
            t += 4
    loop = [("inc hl", 6), ("dec de", 6), ("ld a, d", 4), ("or a, e", 4), ("jp nz, %s_b" % name, 10)]
    lead = 7
    c, d = g.delay_near(max(0, round(10 * bit) - t - cost(loop) - lead))
    code += c + loop
    stop = t + d + cost(loop) + lead - 9 * bit
    assert stop >= bit - MAX_ERR_T, (name, stop, bit)
    tail, _ = g.delay_near(round(bit))
    code += tail + [("ret", 10)]
    L += emit(code)
    L += ["__endasm; }", ""]
    return name, L, round(stop / bit, 2)


def tx_routine(baud):
    """Sends tx_len bytes from tx_ptr on DATA0: port value 0xFF = wire low (space), 0x00 = wire high (mark)."""
    g = Gen()
    bit = CLOCK / baud
    name = "tx_%d" % baud
    pins = [("ld a, #0xFF", 7), ("out (0x11), a", 11)]   # as the hardware-tested transmitter does after each bit
    edges = [round(k * bit) for k in range(11)]          # start, 8 data bits, stop, next start
    L = ["static void %s(void) __naked { __asm" % name,
         "\t\tld hl, (_tx_ptr)", "\t\tld de, (_tx_len)", "\t\tld a, d", "\t\tor a, e", "\t\tret z"]
    lead = [("ld c, (hl)", 7), ("ld a, #0xFF", 7)]
    L.append("%s_b:\tld c, (hl)" % name)
    L.append("\t\tld a, #0xFF")
    # time 0 = start of the OUT of the start bit
    t = 0
    code = [("out (0x10), a", 11)] + pins
    t += cost(code)
    out_at = [0]
    for k in range(1, 10):
        c, d = g.delay_near(edges[k] - t - (16 if k < 9 else 4))
        code += c
        t += d
        if k < 9:
            s = [("rr c", 8), ("sbc a, a", 4), ("cpl", 4)]
        else:
            s = [("xor a, a", 4)]
        code += s
        t += cost(s)
        out_at.append(t)
        assert abs(t - k * bit) <= MAX_ERR_T, (name, k, t, k * bit)
        code += [("out (0x10), a", 11)] + pins
        t += 11 + cost(pins)
    loop = [("inc hl", 6), ("dec de", 6), ("ld a, d", 4), ("or a, e", 4), ("jp nz, %s_b" % name, 10)]
    c, d = g.delay_near(edges[10] - t - cost(loop) - cost(lead))
    code += c
    t += d + cost(loop) + cost(lead)
    assert abs(t - 10 * bit) <= MAX_ERR_T, (name, t, 10 * bit)
    out_at.append(t)
    code += loop
    # after the last byte, hold the stop level for one more bit before anything else may touch port 0x10
    tail, _ = g.delay_near(round(bit))
    code += tail + [("ret", 10)]
    L += emit(code)
    L += ["__endasm; }", ""]
    return name, L, out_at


def main():
    o = ["// Generated by gen_serial.py: do not edit.", ""]
    for i, b in enumerate(BAUDS + FAST + CAPTURE):
        o.append("#define BAUD_%d %d" % (b, i))
    o.append("#define N_BAUDS %d" % len(BAUDS + FAST + CAPTURE))
    o.append("#define N_RX %d   // rates with their own receive routine; the others use rx_capture" % len(BAUDS + FAST))
    o.append("#define CAPBUF 0x%04X" % CAPBUF)
    o.append("#define CAP_N %d" % (CAP_BLOCKS * 128))
    o += ["#define ST_IDLE %d" % ST_IDLE, "#define ST_END %d" % ST_END, "#define ST_FULL %d" % ST_FULL,
          "#define ST_BREAK %d" % ST_BREAK, "#define ST_STUCK %d" % ST_STUCK, "#define ST_CAP %d" % ST_CAP, "#define RXBUF 0x%04X" % RXBUF, ""]

    # millisecond delay: ms_n passes of MS_T T-states
    ms_k = round((CLOCK / 1000 - 29) / 26)
    ms_t = 10 + (6 + 4 + 4 + 12) * ms_k - 5 + 6 + 4 + 4 + 10
    assert abs(ms_t / CLOCK * 1000 - 1) < 0.003, ms_t
    o += ["// Busy wait of ms_n milliseconds (%d T each)." % ms_t,
          "static void delay_ms(void) __naked { __asm",
          "\t\tld de, (_ms_n)", "1$:\tld bc, #%d" % ms_k, "2$:\tdec bc", "\t\tld a, b", "\t\tor a, c",
          "\t\tjr nz, 2$", "\t\tdec de", "\t\tld a, d", "\t\tor a, e", "\t\tjp nz, 1$", "\t\tret", "__endasm; }", ""]
    lcd_n = 24
    lcd_t = 17 + 7 + 13 * lcd_n - 5 + 10
    assert lcd_t / CLOCK > 50e-6, lcd_t
    o.append("#define LCD_N %d   // %d T between LCD writes" % (lcd_n, lcd_t))

    # timeouts in passes of the polling loops
    idle = round(0.050 * CLOCK / WAIT_ITER_T)
    gaps = [min(65535, round(max(0.006, 3 * 10 / b) * CLOCK / WAIT_ITER_T)) for b in BAUDS]
    o.append("#define RX_IDLE %d   // about 50 ms of waiting for a start bit" % idle)
    o.append("")

    rx_names, tx_names = [], []
    report = []
    for b in BAUDS + FAST:
        for pol in (0, 1):
            if b in FAST:
                fi = round(0.050 * CLOCK / sum(FAST_GAPS))
                fg = round(0.006 * CLOCK / sum(FAST_GAPS))
                n, l, s = rx_fast(b, pol, fi, fg)
            else:
                n, l, s = rx_routine(b, pol, gaps[BAUDS.index(b)])
            rx_names.append(n)
            o += l
            if pol == 0:
                report.append("rx %5d: bit %.1f T, samples %s" % (b, CLOCK / b, s))
        n, l, e = tx_routine(b)
        tx_names.append(n)
        o += l
        report.append("tx %5d: edges %s" % (b, e))
    trim_names = []
    for b in TRIM_BAUDS:
        for t in TRIMS:
            n, l, s = rx_routine(b, 0, gaps[BAUDS.index(b)], t)
            trim_names.append(n)
            o += l
        trim_names.insert(len(trim_names) - len(TRIMS) // 2, "rx_%d_a" % b)    # trim 0 = the plain routine
    report.append("trims %s%%: %s" % (TRIMS, ", ".join(trim_names)))
    o += rx_capture()
    o += cap_scan()
    o += cap_pack()
    o.append("#define SCOPE_BYTES %d" % SCOPE_BYTES)
    o.append("#define TRBUF 0x%04X" % TRBUF)
    for b in CAPTURE:
        n, l, st = tx_turbo(b)
        tx_names.append(n)
        o += l
        report.append("tx %6d: stop bit %.2f bits" % (b, st))
    o.append("static void (* const rx_tab[N_RX * 2])(void) = { %s };" % ", ".join(rx_names))
    o.append("static void (* const tx_tab[N_BAUDS])(void) = { %s };" % ", ".join(tx_names))
    o.append("static const word baud_div10[N_BAUDS] = { %s };" % ", ".join(str(b // 10) for b in BAUDS + FAST + CAPTURE))
    o.append("// bit time in 1/16 T for the capture rates (index baud - N_RX)")
    b16 = [round(CLOCK / b * 16) for b in CAPTURE]
    o.append("static const word cap_bit16[%d] = { %s };" % (len(CAPTURE), ", ".join(map(str, b16))))
    o.append("static const word cap_nine[%d] = { %s };   // 9 bits in T" % (len(CAPTURE), ", ".join(str(v * 9 // 16) for v in b16)))
    o.append("static const word cap_stop[%d] = { %s };   // 9.5 bits in T" % (len(CAPTURE), ", ".join(str(v * 19 // 32) for v in b16)))
    o.append("static const word cap_stop16[%d] = { %s };   // 9.5 bits in T x 16" % (len(CAPTURE), ", ".join(str(v * 19 // 2) for v in b16)))
    o.append("static const byte cap_sync_tab[%d] = { %s };   // passes of 45 T in 6 bits" % (
        len(CAPTURE), ", ".join(str(max(2, round(6 * CLOCK / b / 45))) for b in CAPTURE)))
    o.append("#define TRIM_MAX %d" % max(TRIMS))
    o.append("static const signed char trim_set[N_BAUDS] = { %s };   // row of rx_trim_tab, or -1"
             % ", ".join(str(TRIM_BAUDS.index(b)) if b in TRIM_BAUDS else "-1" for b in BAUDS + FAST + CAPTURE))
    o.append("static void (* const rx_trim_tab[%d][%d])(void) = { %s };" % (
        len(TRIM_BAUDS), len(TRIMS) + 1, ", ".join("{ %s }" % ", ".join(trim_names[i:i + len(TRIMS) + 1])
                                                    for i in range(0, len(trim_names), len(TRIMS) + 1))))
    open(OUT, "w").write("\n".join(o) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main()
