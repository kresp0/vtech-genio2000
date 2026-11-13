#!/usr/bin/env python3
"""PC side of the pc-link cartridge: sends data to a Genio 2000 over the printer port BUSY line.

Wiring: USB-serial TXD -> DB25 pin 11 (BUSY), DB25 pin 2 (DATA0) -> USB-serial RXD, ground to ground (18-25).

  pclink.py --port /dev/ttyUSB0 line            toggle the line (break) so the Genio shows SPC / MARK
  pclink.py --port /dev/ttyUSB0 send "Hola"     raw bytes; the Genio shows them and echoes them back
  pclink.py --port /dev/ttyUSB0 term            type lines, see the echo
  pclink.py --port /dev/ttyUSB0 ping            statistics packet
  pclink.py --port /dev/ttyUSB0 test -n 100     random packets, each acknowledged with an echo
  pclink.py --port /dev/ttyUSB0 baud 19200      switch both ends to another rate
  pclink.py --port /dev/ttyUSB0 reset           3 s break: the Genio goes back to 76800 baud
  pclink.py --port /dev/ttyUSB0 scope 128000    record a known pattern at a capture rate and measure its edges
  pclink.py --port /dev/ttyUSB0 skew -13        capture decoder: rising edges are 13 T early (the default)
  pclink.py --port /dev/ttyUSB0 sweep -n 20     test the stable rates 2400-76800 (--experimental: also 115200
                                                and 128000; or --bauds), then back to 76800
  pclink.py --port /dev/ttyUSB0 margin -n 10    at 9600: shift the Genio's receive timing -7..+7 % until it fails

--mame DIR talks to the cartridge running in MAME through tests/bridge.lua instead of a serial port.
Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse
import os
import random
import sys
import time

BAUDS = [2400, 4800, 9600, 19200, 38400, 57600, 76800, 115200, 128000]
STABLE = BAUDS[:7]            # all worked on the unit, every packet first time
CAPTURE = BAUDS[7:]           # experimental: the cartridge records 11.4 ms of line and decodes it afterwards
CAP_T = 34 * 128 * 16 + 34 * 14   # T-states of one capture at 6.13179 MHz
DEFAULT = 76800               # the rate the cartridge starts at and goes back to after a break
TRIMS = range(-7, 8)          # receive-timing offsets (percent) the cartridge has at 9600 baud
MAXP = 240
DEBUG = os.environ.get("PCLINK_DEBUG") == "1"
NAK_REASONS = {1: "CRC", 2: "length", 3: "type"}


def crc16(data, crc=0xFFFF):
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def max_payload(baud):
    """Largest payload that fits in one capture (2 FF + 7 framing bytes, one character of slack)."""
    if baud not in CAPTURE:
        return MAXP
    return min(MAXP, int(CAP_T / (6131790 / baud * 10)) - 10)


def preamble(baud):
    """FF bytes (no falling edge inside) for a receiver that is busy; at the capture rates about 2 ms of them, the
    sync byte 00 after which the Genio starts recording, and two more FF while the recording starts."""
    if baud not in CAPTURE:
        return b"\xFF\xFF"
    return b"\xFF" * (baud // 5000 + 1) + b"\x00\xFF\xFF"


def packet(typ, seq, payload):
    body = bytes([typ, seq, len(payload)]) + bytes(payload)
    c = crc16(body)
    return b"\xA5\x5A" + body + bytes([c & 0xFF, c >> 8])


class SerialLink:
    def __init__(self, port, baud):
        import serial            # pyserial, only needed for the real cable
        self.s = serial.Serial(port, baud, timeout=0)
        self.s.reset_input_buffer()

    def write(self, data):
        self.s.write(data)
        self.s.flush()

    def read(self):
        return self.s.read(4096)

    def set_baud(self, tx, rx):
        self.s.baudrate = tx     # a real UART uses one rate for both directions

    def set_break(self, on):
        self.s.break_condition = on

    def mark(self, tag):
        pass

    def close(self):
        self.s.close()


class MameLink:
    def __init__(self, d, baud):
        self.d = d
        self.ctl = open(os.path.join(d, "ctl.txt"), "a")
        try:
            self.pos = os.path.getsize(os.path.join(d, "rx.bin"))     # skip what earlier runs received
        except FileNotFoundError:
            self.pos = 0
        self.set_baud(baud, baud)

    def _cmd(self, line):
        self.ctl.write(line + "\n")
        self.ctl.flush()

    def write(self, data):
        self._cmd("data " + bytes(data).hex())

    def read(self):
        try:
            with open(os.path.join(self.d, "rx.bin"), "rb") as f:
                f.seek(self.pos)
                b = f.read()
        except FileNotFoundError:
            return b""
        self.pos += len(b)
        return b

    def set_baud(self, tx, rx):
        self._cmd("baud %s %s" % (tx, rx))

    def set_break(self, on):
        self._cmd("break %d" % on)

    def mark(self, tag):
        self._cmd("screen " + tag)
        self._cmd("snap")

    def close(self):
        self._cmd("stats")
        if os.environ.get("PCLINK_MAME_QUIT", "1") == "1":
            self._cmd("quit")


class Genio:
    def __init__(self, link, baud, skew):
        self.link, self.skew, self.buf, self.seq = link, skew, bytearray(), 0
        self.garbage = 0
        self.set_rate(baud)

    def set_rate(self, baud):
        self.baud = baud
        self.link.set_baud(round(baud * (1 + self.skew / 100)), baud)

    def drain(self):
        time.sleep(0.05)
        self.link.read()
        self.buf.clear()

    def poll(self):
        self.buf += self.link.read()

    def get_packet(self, timeout):
        """Next valid reply packet (type, seq, payload), skipping anything else; None on timeout."""
        end = time.time() + timeout
        while True:
            self.poll()
            i = self.buf.find(b"\xA5\x5A")
            if DEBUG and (i > 0 or (i < 0 and len(self.buf) > 1)):
                print("  [stray %s]" % bytes(self.buf[:i if i >= 0 else len(self.buf)]).hex())
            if i < 0:
                keep = 1 if self.buf[-1:] == b"\xA5" else 0
                self.garbage += len(self.buf) - keep
                del self.buf[:len(self.buf) - keep]
            else:
                self.garbage += i
                del self.buf[:i]
                if len(self.buf) >= 5 and len(self.buf) >= 7 + self.buf[4]:
                    n = self.buf[4]
                    body = bytes(self.buf[2:5 + n])
                    c = crc16(body)
                    if self.buf[5 + n] == c & 0xFF and self.buf[6 + n] == c >> 8:
                        del self.buf[:7 + n]
                        return body[0], body[1], body[3:]
                    del self.buf[:1]
                    self.garbage += 1
                    continue
            if time.time() > end:
                return None
            time.sleep(0.002)

    def reply_timeout(self, n_out, n_back):
        return 0.4 + (n_out + n_back + 4) * 10 / self.baud * 1.5 + (0.4 if self.baud in CAPTURE else 0)   # decoding

    def transact(self, typ, payload, retries=3):
        """Sends a packet and waits for its reply; returns (reply, attempts) with reply = (type, seq, payload) or None."""
        self.seq = (self.seq + 1) & 0xFF
        p = preamble(self.baud) + packet(ord(typ), self.seq, payload)
        for attempt in range(1, retries + 1):
            if DEBUG:
                print("  [%.3f send %s seq %02X try %d at %d]" % (time.time(), typ, self.seq, attempt, self.baud))
            self.link.write(p)
            while True:
                r = self.get_packet(self.reply_timeout(len(p), len(p)))
                if DEBUG:
                    print("  [%.3f reply %s]" % (time.time(), r and (chr(r[0]), r[1])))
                if r is None or (r[1] == self.seq and r[0] in (ord("A"), ord("N"))):   # not an echo of ours
                    break
            if r is not None and (r[0] == ord("A") or attempt == retries):
                return r, attempt
            if r is not None and len(r[2]) == 3:
                print("  NAK seq %02X: %s, Genio got %d bytes" % (r[1], NAK_REASONS.get(r[2][0], r[2][0]),
                                                                   r[2][1] | r[2][2] << 8))
            time.sleep(0.05)
        return r, retries


def show_stats(p):
    names = ["ok", "bad", "raw", "fe", "brk"]
    v = {k: p[4 + 2 * i] | p[5 + 2 * i] << 8 for i, k in enumerate(names)}
    trim = (p[14] ^ 0x80) - 0x80 if len(p) > 14 else 0
    return "v%d %d baud%s pol %s echo %s | packets ok %d bad %d | raw bytes %d | framing errors %d | breaks %d" % (
        p[0], BAUDS[p[1]], " trim %+d%%" % trim if trim else "", "AB"[p[2]], "on" if p[3] else "off",
        v["ok"], v["bad"], v["raw"], v["fe"], v["brk"])


def cmd_ping(g, a):
    for _ in range(a.tries):
        r, _ = g.transact("P", b"", retries=1)
        if r and r[0] == ord("A"):
            print(show_stats(r[2]))
            return 0
        time.sleep(0.3)
    print("no answer at %d baud" % g.baud)
    return 1


def cmd_clear(g, a):
    r, _ = g.transact("C", b"")
    print(show_stats(r[2]) if r and r[0] == ord("A") else "no answer")
    return 0 if r else 1


def cmd_line(g, a):
    print("The top right corner of the Genio should alternate SPC / MARK every %.1f s" % a.period)
    for i in range(a.count):
        g.link.set_break(True)
        print("  line low (break)  -> SPC", flush=True)
        time.sleep(a.period)
        g.link.set_break(False)
        print("  line high (idle)  -> MARK", flush=True)
        time.sleep(a.period)
    return 0


def send_raw(g, data, echo, chunk):
    bad = 0
    for i in range(0, len(data), chunk):
        part = data[i:i + chunk]
        g.drain()
        g.link.write(preamble(g.baud) + part if g.baud in CAPTURE else part)
        if not echo:
            time.sleep(len(part) * 10 / g.baud + 0.1)
            continue
        end = time.time() + 0.5 + len(part) * 30 / g.baud
        got = bytearray()
        while len(got) < len(part) and time.time() < end:
            got += g.link.read()
            time.sleep(0.005)
        time.sleep(0.02)
        got += g.link.read()
        if bytes(got) == part:
            print("  %d bytes echoed OK" % len(part))
        else:
            bad += 1
            print("  sent %r\n  echo %r" % (part, bytes(got)))
    return bad


def cmd_send(g, a):
    data = open(a.file, "rb").read() if a.file else " ".join(a.text).encode("ascii", "replace")
    return 1 if send_raw(g, data, not a.no_echo, a.chunk) else 0


def cmd_term(g, a):
    print("Type lines (Ctrl-D ends). Each one is sent with a line feed.")
    for line in sys.stdin:
        send_raw(g, line.rstrip("\n").encode("ascii", "replace") + b"\n", not a.no_echo, 200)
    return 0


def run_test(g, n, lo, hi, quiet=False, retries=3, give_up=0, silent=False):
    """n random 'D' packets; returns the number that failed. give_up: stop after that many failures in a row
    (the rest count as failed)."""
    rnd = random.Random(a_seed)
    hi = min(hi, max_payload(g.baud))
    lo = min(lo, hi)
    first = retried = failed = 0
    payload_bytes = 0
    row = 0
    t0 = time.time()
    for i in range(n):
        if give_up and row >= give_up:
            failed += n - i
            if not silent:
                print("  %d failures in a row: the other %d packets count as failed" % (row, n - i))
            break
        m = rnd.randint(lo, hi)
        p = bytes(rnd.choice(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,:-+*/") for _ in range(m))
        r, att = g.transact("D", p, retries=retries)
        ok = r is not None and r[0] == ord("A") and r[2] == p
        row = 0 if ok else row + 1
        if ok and att == 1:
            first += 1
        elif ok:
            retried += 1
        else:
            failed += 1
            if not silent:
                print("  packet %d (%d bytes) failed: %s" % (i, m, "no answer" if r is None else
                                                        "NAK" if r[0] == ord("N") else "echo differs"))
        payload_bytes += m
        if not quiet and (i + 1) % 10 == 0:
            print("  %d/%d" % (i + 1, n), flush=True)
    dt = time.time() - t0
    if silent:
        return failed
    print("%d baud: %d packets, %d OK first time, %d OK after retry, %d failed; %d payload bytes in %.1f s "
          "(%.0f B/s each way); %d stray bytes ignored" % (g.baud, n, first, retried, failed, payload_bytes, dt,
                                                          payload_bytes / dt, g.garbage))
    return failed


def cmd_test(g, a):
    return 1 if run_test(g, a.n, a.min, a.max) else 0


def switch(g, baud):
    if baud == g.baud:
        return True
    r, _ = g.transact("B", bytes([BAUDS.index(baud)]))
    if not r or r[0] != ord("A"):
        print("no ACK for the baud change")
        return False
    old = g.baud
    time.sleep(0.1)
    g.set_rate(baud)
    g.drain()
    r, _ = g.transact("P", b"", retries=3)
    if r and r[0] == ord("A"):
        print("now at %d baud" % baud)
        return True
    print("no answer at %d baud; the Genio goes back to %d after about 4 s" % (baud, old))
    time.sleep(5)
    g.set_rate(old)
    g.drain()
    return False


def recover(g):
    """Holds the line low for 3 s: the Genio goes back to the default rate."""
    print("  break of 3 s: the Genio goes back to %d baud" % DEFAULT, flush=True)
    g.link.set_break(True)
    time.sleep(3)
    g.link.set_break(False)
    time.sleep(0.3)
    g.set_rate(DEFAULT)
    g.drain()
    r, _ = g.transact("P", b"", retries=3)
    return r is not None and r[0] == ord("A")


CLOCK = 6131790
CAP_N = 34 * 128


def t_of(i):
    """Time of capture sample i in T-states (INI every 16 T, 14 T more after each block of 128)."""
    return 16 * i + 14 * (i >> 7)


def scope_pattern(baud):
    """Known bytes for the scope: alternating bits, long runs, single bits in both senses, then a ramp."""
    head = [0x55] * 8 + [0x00, 0xFF] * 3 + [0x0F, 0xF0] * 3 + [0x01, 0x80, 0xFE, 0x7F] * 2 + [0x33, 0xCC] * 2
    n = int(CAP_T / (CLOCK / baud * 10)) - 8
    return bytes((head + [(17 * k + 5) & 0xFF for k in range(n)])[:n])


def analyse(space, baud, sent):
    """Edges of the recording against the bytes sent (bytes found in order, each timed from its own start edge).
    Returns a report and the suggested skew (rising minus falling edge delay, T)."""
    bit = CLOCK / baud
    ch = [i for i in range(1, CAP_N) if space[i] != space[i - 1]]
    est = {i: t_of(i) - (t_of(i) - t_of(i - 1)) / 2 for i in ch}      # a change happened between two samples
    starts, k = [], 0
    while k < len(ch):                                                  # start edges, as the Genio finds them
        i = ch[k]
        if space[i]:
            starts.append(i)
            while k < len(ch) and est[ch[k]] - est[i] < 9.5 * bit:
                k += 1
        else:
            k += 1
    best = None
    for skip in range(0, 4):                                            # which sent byte the first start belongs to
        err_f, err_r, bits_bad, slope = [], [], 0, []
        for n, i0 in enumerate(starts):
            if n + skip >= len(sent):
                break
            v = sent[n + skip]
            level = [1] + [0 if (v >> b) & 1 else 1 for b in range(8)] + [0]     # 1 = space, start..stop
            want = [b for b in range(1, 10) if level[b] != level[b - 1]]      # boundaries with a change
            got = [c for c in ch if i0 < c and est[c] - est[i0] < 9.5 * bit]
            for j, c in enumerate(got):
                rel = est[c] - est[i0]
                if len(got) == len(want):
                    b = want[j]                                                # the j-th change is the j-th boundary
                else:
                    b = min(want, key=lambda w: abs(w * bit - rel)) if want else round(rel / bit)
                e = rel - b * bit
                (err_r if not space[c] else err_f).append(e)
                if space[c]:
                    slope.append((b, rel))                                     # falling edges: not delayed
                if abs(e) > bit / 2:
                    bits_bad += 1
            if len(got) != len(want):
                bits_bad += abs(len(got) - len(want))
        score = bits_bad
        if best is None or score < best[0]:
            best = (score, skip, err_f, err_r, slope)
    score, skip, err_f, err_r, slope = best
    mean = lambda x: sum(x) / len(x) if x else 0.0
    sd = lambda x: (sum((v - mean(x)) ** 2 for v in x) / len(x)) ** 0.5 if x else 0.0
    if slope:
        n = len(slope); sb = sum(b for b, _ in slope); sr = sum(r for _, r in slope)
        sbb = sum(b * b for b, _ in slope); sbr = sum(b * r for b, r in slope)
        bt = (n * sbr - sb * sr) / (n * sbb - sb * sb) if n * sbb != sb * sb else bit
    else:
        bt = bit
    us = 1e6 / CLOCK
    rep = ["%d baud: %d start edges found, %d bytes sent (first %d not seen)" % (baud, len(starts), len(sent), skip),
           "  bit time from the falling edges: %.2f T = %.3f us (nominal %.2f T): the adapter sends %.0f baud if the Genio "
           "runs at 6.13179 MHz (%+.2f %%)" % (bt, bt * us, bit, CLOCK / bt, (bit / bt - 1) * 100),
           "  falling edges (to low): %d, mean %+.1f T, spread %.1f T" % (len(err_f), mean(err_f), sd(err_f)),
           "  rising edges (to high): %d, mean %+.1f T (%+.2f us), spread %.1f T" % (len(err_r), mean(err_r),
                                                                                mean(err_r) * us, sd(err_r)),
           "  (edges are timed from each byte's start edge; +-8 T of spread is the 16 T sampling itself)",
           "  edges more than half a bit off, or missing / extra: %d" % score]
    return "\n".join(rep), round(mean(err_r) - mean(err_f))


def cmd_scope(g, a):
    if not switch(g, DEFAULT) and not recover(g):
        return 1
    sent = b"\xFF\xFF" + scope_pattern(a.rate)
    r, _ = g.transact("K", bytes([BAUDS.index(a.rate)]))
    if not r or r[0] != ord("A"):
        print("the Genio did not take the scope request")
        return 1
    time.sleep(0.1)
    g.set_rate(a.rate)
    time.sleep(0.1)
    g.link.write(b"\xFF" * (a.rate // 5000 + 1) + b"\x00" + sent)
    time.sleep(0.5)
    g.set_rate(DEFAULT)
    g.drain()
    raw = b""
    for page in range((CAP_N // 8 + 239) // 240):
        r, _ = g.transact("R", bytes([page]))
        if not r or r[0] != ord("A"):
            print("no recording (page %d): did the Genio show SCOPE RECORDED?" % page)
            return 1
        raw += r[2]
    space = [(raw[i >> 3] >> (i & 7)) & 1 for i in range(CAP_N)]
    name = a.out or "scope_%d.txt" % a.rate
    with open(name, "w") as f:
        f.write("# pc-link scope: %d baud, sample i at 16 i + 14 (i / 128) T, 1 = line low; sent (hex): %s\n"
                % (a.rate, sent.hex()))
        for i in range(0, CAP_N, 128):
            f.write("".join(str(v) for v in space[i:i + 128]) + "\n")
    rep, skew = analyse(space, a.rate, sent)
    print(rep)
    print("  recording saved in %s" % name)
    if abs(skew) >= 2:
        print("  suggested: pclink.py skew %d   (the decoder then moves rising edges %d T earlier)" % (skew, skew))
    return 0


def cmd_skew(g, a):
    r, _ = g.transact("W", bytes([a.t & 0xFF]))
    print("skew %+d T set" % a.t if r and r[0] == ord("A") else "no answer")
    return 0 if r else 1


def cmd_reset(g, a):
    return 0 if recover(g) else 1


def cmd_baud(g, a):
    return 0 if switch(g, a.rate) else 1


def cmd_sweep(g, a):
    res = {}
    a.bauds = a.bauds or (BAUDS if a.experimental else STABLE)
    for b in a.bauds:
        if not switch(g, b):
            res[b] = "no link"
            if not ping_ok(g):
                recover(g)
            continue
        f = run_test(g, a.n, a.min, a.max, quiet=True, give_up=a.give_up)
        res[b] = "%d/%d failed" % (f, a.n)
        if f and not ping_ok(g):
            recover(g)
    if not switch(g, DEFAULT):
        recover(g)
    for b in a.bauds:
        print("%6d: %s" % (b, res[b]))
    return 0 if all(v.startswith("0/") for v in res.values()) else 1


def ping_ok(g):
    r, _ = g.transact("P", b"", retries=2)
    return r is not None and r[0] == ord("A")


def set_trim(g, t):
    """Sets the Genio's receive offset; if it no longer understands us, waits for its 4 s fallback."""
    r, _ = g.transact("T", bytes([t & 0xFF]), retries=2)
    if r and r[0] == ord("A"):
        return True
    time.sleep(5)
    g.drain()
    return False


def cmd_margin(g, a):
    if not switch(g, 9600):
        return 1
    res = {}
    for t in a.trims:
        if not set_trim(g, t):
            print("trim %+d%%: the Genio did not take it" % t)
            continue
        f = run_test(g, a.n, a.min, a.max, quiet=True, retries=1, give_up=3, silent=True)
        res[t] = f
        print("trim %+d%%: %d/%d failed" % (t, f, a.n), flush=True)
        if not set_trim(g, 0):
            print("  (the Genio went back to trim 0 by itself)")
    ok = [t for t in sorted(res) if res[t] == 0]
    print("\nreceive offset  " + " ".join("%+3d" % t for t in sorted(res)))
    print("failed packets  " + " ".join("%3d" % res[t] for t in sorted(res)))
    if ok:
        lo, hi = min(ok), max(ok)
        print("works from %+d%% to %+d%%: centre %+.1f%%, margin about +-%.1f%%" % (lo, hi, (lo + hi) / 2, (hi - lo) / 2))
        print("(a positive centre means the PC's bits are shorter than the Genio expects: PC fast or Genio slow)")
    switch(g, DEFAULT)
    return 0


a_seed = 1


def main():
    global a_seed
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--port", help="serial device, e.g. /dev/ttyUSB0")
    src.add_argument("--mame", metavar="DIR", help="bridge directory of a MAME run with tests/bridge.lua")
    ap.add_argument("--baud", type=int, default=DEFAULT, choices=BAUDS, help="rate the Genio is set to (default %d)" % DEFAULT)
    ap.add_argument("--skew", type=float, default=0, help="send this many percent faster (negative: slower)")
    ap.add_argument("--seed", type=int, default=1)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("line"); p.add_argument("--period", type=float, default=1.0); p.add_argument("--count", type=int, default=5)
    p = sub.add_parser("send"); p.add_argument("text", nargs="*"); p.add_argument("--file")
    p.add_argument("--no-echo", action="store_true"); p.add_argument("--chunk", type=int, default=200)
    p = sub.add_parser("term"); p.add_argument("--no-echo", action="store_true")
    p = sub.add_parser("ping"); p.add_argument("--tries", type=int, default=5)
    sub.add_parser("clear")
    for name in ("test", "sweep", "margin"):
        p = sub.add_parser(name)
        p.add_argument("-n", type=int, default={"test": 50, "sweep": 20, "margin": 10}[name])
        p.add_argument("--min", type=int, default=100 if name == "margin" else 1)
        p.add_argument("--max", type=int, default=MAXP)
        if name == "sweep":
            p.add_argument("--bauds", type=int, nargs="+", choices=BAUDS)
            p.add_argument("--experimental", action="store_true", help="also the capture rates 115200 and 128000")
            p.add_argument("--give-up", type=int, default=5, help="stop a rate after this many failures in a row")
        if name == "margin":
            p.add_argument("--trims", type=int, nargs="+", default=list(TRIMS), choices=list(TRIMS))
    p = sub.add_parser("baud"); p.add_argument("rate", type=int, choices=BAUDS)
    sub.add_parser("reset")
    p = sub.add_parser("scope"); p.add_argument("rate", type=int, choices=CAPTURE); p.add_argument("--out")
    p = sub.add_parser("skew"); p.add_argument("t", type=int, help="T-states, -40..40 (default -13)")
    a = ap.parse_args()
    a_seed = a.seed
    if not 1 <= getattr(a, "min", 1) <= getattr(a, "max", 1) <= MAXP:
        ap.error("need 1 <= --min <= --max <= %d" % MAXP)
    if a.port and a.skew:
        print("note: a real UART sends and receives at the same rate, so --skew also shifts the PC's receiver "
              "and the Genio's answers may be lost; 'margin' shifts the Genio instead")
    link = SerialLink(a.port, a.baud) if a.port else MameLink(a.mame, a.baud)
    g = Genio(link, a.baud, a.skew)
    try:
        rc = globals()["cmd_" + a.cmd](g, a)
        time.sleep(0.3)
        link.mark(a.cmd)
        time.sleep(0.2)
        return rc
    finally:
        link.close()


if __name__ == "__main__":
    sys.exit(main())
