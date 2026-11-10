"""sim_hw - runs the REAL compiled hwtest image instruction by instruction in the Z80 interpreter (tests/z80core.py of the dumper repository, read-only)
against a MODEL of the Genio 2000 (windows per port 01/03 with the real ROM banks, cartridge EEPROM 32 KiB, RAM, scripted keyboard).
This validates the program logic, the protocol and the receiver arithmetic offline. It does NOT validate the unit itself, and it does not use MAME.

Replaced by Python hooks (they are the hardware-validated asm routines of the dumper): tx_send, wait_bits, line_set, crc32_run, and gap_dly
(synthetic time only). A synthetic clock (f_cpu) timestamps every transmitted byte so the receiver's clock / IRQ analysis can be checked.
"""
import os, re, sys, zlib, random
HERE = os.path.dirname(os.path.abspath(__file__)); HW = os.path.dirname(HERE); RA = os.path.dirname(HW)
GEN = os.path.dirname(os.path.dirname(RA))
DUMPER = os.environ.get('GENIO_DUMPER_DIR', os.path.join(RA, 'dumper'))      # clone of the dumper repository
sys.path.insert(0, os.path.join(DUMPER, 'tests')); sys.path.insert(0, os.path.join(DUMPER, 'tools'))
from z80core import Z80
import gframe as g

KEYPOS = {'\r': (7, 4, 0x10), 'S': (2, 3, 0x10), 'N': (4, 5, 0x10), 'A': (1, 3, 0x10)}
GL4 = [0,1,2,3,8,9,10,11,12,13,14,15,24,25,26,27,28,29,30,31,64,65,66,67,72,73,74,75,76,77,78,79,88,89,90,91,92,93,94,95,
       4,5,6,7,16,17,18,19,20,21,22,23,32,33,34,35,36,37,38,39,68,69,70,71,80,81,82,83,84,85,86,87,96,97,98,99,100,101,102,103]
QUEUE = ['\r'] * 5 + ['S'] * 6 + ['\r', 'A', '\r'] + ['\r'] * 5 + ['\r'] * 5


def symbols(mapfile):
    sym = {}
    for line in open(mapfile):
        m = re.match(r'^\s+([0-9A-F]{8})\s+(\S+)\s+\S+\s*$', line)
        if m: sym[m.group(2)] = int(m.group(1), 16)
    for line in open(mapfile[:-4] + '.sym'):
        m = re.match(r'\s+(\d)\s+(\S+)\s+([0-9A-F]{8})', line)
        if m and m.group(2) not in sym: sym[m.group(2)] = (0x8020 if m.group(1) == '0' else 0xC000) + int(m.group(3), 16)
    return sym


class Model:
    """Hardware assumptions of the simulation (what the unit might do; the test exists to find out). Defaults = MAME-like."""
    def __init__(self, **kw):
        self.f_cpu = 6.0e6
        self.irq_hz = 60.0
        self.e000 = 'open'              # 'open' (FF) | 'mirror'
        self.cart_a13 = True            # CPU A13 reaches EEPROM A13
        self.cart_pagebits = 0x01       # page bits (of port 03 & 0x0F) wired to EEPROM A14
        self.internal_mask = 0x07       # internal entry -> bank = sel & mask
        self.port_defaults = {0x12: 0xDE}
        self.halt_poweroff = False      # hypothesis: executing HALT cuts the power (the firmware only HALTs when powering off)
        self.cart_wr = False             # /WR reaches the EEPROM: a write starts a short busy period (DQ7 inverted)
        self.queue = list(QUEUE)
        self.__dict__.update(kw)


def run(image, rom, model=None, max_instr=400_000_000, variant='ye', verbose=False):
    model = model or Model()
    bdir = os.path.join(HW, 'build', variant)
    sym = symbols(os.path.join(bdir, 'hwtest.map'))
    banks = [rom[i * 0x4000:(i + 1) * 0x4000] for i in range(8)]
    cpu = Z80()
    R = type('R', (), {})()
    R.cap = []; R.rom_writes = []; R.bad_ports = []; R.port_writes = []; R.pc_outside = []; R.t = 0.0; R.ddram = bytearray(b' ' * 128)
    st = dict(w1=0, w2=0x80, mask=0, polls=0, down=None, hold=0, idle=0, ad=0, qi=0, port12=0xDE)
    Tbit = 642.0 / model.f_cpu

    def cart_byte(off, page):
        a = off & 0x3FFF
        if not model.cart_a13: a &= 0x1FFF
        a |= ((page & model.cart_pagebits) != 0) << 14
        return image[a & 0x7FFF]

    def cart_win(page):
        return bytes(cart_byte(o, page) for o in range(0x4000))

    def set_win2(v):
        st['w2'] = v
        if v & 0x80: data = cart_win(v & 0x0F)
        else: data = banks[v & model.internal_mask]
        cpu.mem[0x8000:0xC000] = data

    def set_win1(v): st['w1'] = v; cpu.mem[0x4000:0x8000] = banks[v & 7]
    cpu.mem[0x0000:0x4000] = banks[0]; set_win1(0); set_win2(0x80)
    for a in range(0xC000, 0xE000): cpu.mem[a] = 0
    for a in range(0xE000, 0x10000): cpu.mem[a] = 0xFF if model.e000 == 'open' else 0
    cpu.mem[0xDFF3] = 0x80; cpu.mem[0xDFF1] = 0
    cpu.sp = 0xDFF0; cpu.pc = 0x8004
    cpu.mem[0xDFF4] = 0x14; cpu.mem[0xDFF5] = 0x33; cpu.mem[0xDFF6] = 0
    st['next_irq'] = 1.0 / model.irq_hz; st['isr_ret'] = None

    def hook_tx(c):
        R.cap.append((R.t, c.rb(sym['_serial_byte']))); R.t += (10 * 642 + 230) / model.f_cpu; c.pc = c.pop()
    def hook_wait(c): R.t += c.rw(sym['_wb_n']) * Tbit; c.pc = c.pop()
    def hook_line(c): c.pc = c.pop()
    def hook_gap(c): R.t += 6729 / model.f_cpu; c.pc = c.pop()
    def hook_crc(c):
        p, n = c.rw(sym['_c32_ptr']), c.rw(sym['_c32_len'])
        crc = c.rb(sym['_c32']) | c.rb(sym['_c32'] + 1) << 8 | c.rb(sym['_c32'] + 2) << 16 | c.rb(sym['_c32'] + 3) << 24
        crc = (~zlib.crc32(bytes(c.mem[p:p + n]), (~crc) & 0xFFFFFFFF)) & 0xFFFFFFFF
        for i in range(4): c.mem[sym['_c32'] + i] = (crc >> (8 * i)) & 0xFF
        c.pc = c.pop()
    for name, h in (('_tx_send', hook_tx), ('_wait_bits', hook_wait), ('_line_set', hook_line), ('_gap_dly', hook_gap), ('_crc32_run', hook_crc)):
        cpu.hooks[sym[name]] = h

    def io_out(p, v):
        R.port_writes.append((p, v))
        if p == 0x01: set_win1(v)
        elif p == 0x03: set_win2(v)
        elif p == 0x0A:
            if v == 1: R.ddram[:] = b' ' * 128; st['ad'] = 0
            elif v == 2: st['ad'] = 0
            elif v & 0x80: st['ad'] = v & 0x7F
        elif p == 0x0B: R.ddram[st['ad'] & 0x7F] = v; st['ad'] = (st['ad'] + 1) & 0x7F
        elif p == 0x10:
            st['mask'] = v
            if v == 0x80:
                st['polls'] += 1
                if st['down'] is not None:
                    st['hold'] -= 1
                    if st['hold'] <= 0: st['down'] = None; st['idle'] = 0
                else:
                    st['idle'] += 1
                    if st['idle'] >= 3 and st['qi'] < len(model.queue):
                        st['down'] = model.queue[st['qi']]; st['qi'] += 1; st['hold'] = 8
        elif p == 0x12: st['port12'] = v

    def io_in(p):
        if p in (0x10, 0x11):
            if st['down'] is not None:
                r, k, port = KEYPOS[st['down']]
                if p == port and st['mask'] == (1 << r): return 0xFF & ~(1 << k)
            return 0xFF if p == 0x10 else 0x1F
        if p == 0x12: return st['port12']
        if p in (0x0A, 0x0B): R.bad_ports.append(p)
        return model.port_defaults.get(p, 0xFF)
    cpu.io_out = io_out; cpu.io_in = io_in
    cpu.write_hook = lambda a, v: R.rom_writes.append((a, v)) if not (0xC000 <= a < 0xE000) else None
    n = 0; end_seen = False; nw = 0; busy = None
    while n < max_instr:
        pc = cpu.pc
        if pc == 0xFFF0 and st['isr_ret'] is not None: cpu.pc = st['isr_ret']; st['isr_ret'] = None; cpu.iff = 1; continue
        if not (0x8000 <= pc < 0xA000 or 0xD800 <= pc < 0xD8C0 or pc == 0x0033): R.pc_outside.append(pc); break
        cpu.step(); n += 1
        R.t += 8.0 / model.f_cpu                                # ~8 T-states per instruction: time advances while it computes
        if cpu.iff and st['isr_ret'] is None and R.t >= st['next_irq']:       # IM 1 interrupt: modelled as 'call the hook at DFF5' (the firmware ISR itself is not simulated)
            st['isr_ret'] = cpu.pc; cpu.iff = 0; cpu.push(0xFFF0); cpu.pc = cpu.rw(0xDFF5); st['next_irq'] = R.t + 1.0 / model.irq_hz; R.irqs = getattr(R, 'irqs', 0) + 1
        if len(R.rom_writes) > nw:
            nw = len(R.rom_writes); a, v = R.rom_writes[-1]
            if model.cart_wr and 0x8000 <= a < 0xC000 and st['w2'] & 0x80: cpu.mem[a] = v ^ 0x80; busy = (a, v, n + 80)
        if busy and n >= busy[2]: cpu.mem[busy[0]] = busy[1]; busy = None
        if cpu.halted:
            if model.halt_poweroff: R.powered_off = True; break
            cpu.halted = False
        if (n & 0xFFFF) == 0 and any(b == 0xC0 for _, b in R.cap[-3:]):
            d = g.Decoder(); fr = d.feed(bytes(b for _, b in R.cap[-120:]))
            if any(x[0] == 'frame' and x[1].type == g.T_END for x in fr): end_seen = True
        if end_seen:
            R.end_n = getattr(R, 'end_n', n)
            if n > R.end_n + 300_000: break
    R.instr = n; R.cpu = cpu; R.sym = sym; R.keys_left = len(model.queue) - st['qi']
    R.screen = [''.join((chr(R.ddram[GL4[r * 20 + c]]) if 32 <= R.ddram[GL4[r * 20 + c]] < 127 else '?') for c in range(20)) for r in range(4)]
    return R


def write_capture(R, outdir):
    os.makedirs(outdir, exist_ok=True)
    chunks, cur, t0 = [], bytearray(), None      # a USB-serial read returns what arrived during ~16 ms
    for t, b in R.cap:
        if cur and t - t0 >= 0.016: chunks.append((t0 + 0.016, bytes(cur))); cur = bytearray()
        if not cur: t0 = t
        cur.append(b)
    if cur: chunks.append((t0 + 0.016, bytes(cur)))
    with open(os.path.join(outdir, 'capture.bin'), 'wb') as f, open(os.path.join(outdir, 'capture.tlog'), 'w') as tl:
        for t, d in chunks:
            ff = d.replace(b'\xff', b'\xff\xff')     # PARMRK escaping of literal FF
            f.write(ff); tl.write('%.4f %d\n' % (t, len(ff)))
    return os.path.join(outdir, 'capture.bin')
