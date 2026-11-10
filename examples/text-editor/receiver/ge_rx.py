#!/usr/bin/env python3
"""ge_rx.py - host receiver of the Genio 2000 editor (it ONLY receives: the Genio transmits through DB25 DATA0 -> CP2102 RXD, 9600 8N1).

Protocolo: docs/PROTOCOLO.md (SLIP + CRC-16/CCITT-FALSE, 'GE' v1). Tipos: HELLO, DOC_BEGIN/DATA/END (texto exportado), KEY, LED, STATUS (diagnostico).
Saves to --outdir (default <project>/captures/<date>, inside the project; it never creates folders in the home directory unless asked explicitly):
    export_NNN.txt (+ .sha256)   exported text in UTF-8, ONLY if the length and CRC of the DOC_END frame match
    export_NNN.PARTIAL_UNVERIFIED.txt   with --keep-partial, for incomplete documents (not a valid export)
    key_events.jsonl             pulsaciones / liberaciones / fantasmas, con modificadores y codigos decodificados
    modifier_events.jsonl        changes of SHIFT / ALT / BLOQ.MAYUS / SYM / LED deduced from the events
    led_events.jsonl             LED state changes (with the value written to port 0x12)
    protocol_errors.jsonl        tramas rechazadas y huecos de secuencia
    raw_stream.bin               flujo crudo recibido
Uso en vivo :  python3 -I ge_rx.py --port /dev/ttyUSB0 [--outdir DIR]
Sin hardware:  python3 -I ge_rx.py --input captura_cruda.bin --outdir DIR
"""
import os, sys, json, time, hashlib, argparse
sys.dont_write_bytecode = True

END, ESC, ESC_END, ESC_ESC = 0xC0, 0xDB, 0xDC, 0xDD
VER = 1
T_HELLO, T_DOC_BEGIN, T_DOC_DATA, T_DOC_END, T_KEY, T_LED, T_STATUS = 0x01, 0x10, 0x11, 0x12, 0x20, 0x22, 0x30
TYPE_NAMES = {T_HELLO: 'HELLO', T_DOC_BEGIN: 'DOC_BEGIN', T_DOC_DATA: 'DOC_DATA', T_DOC_END: 'DOC_END', T_KEY: 'KEY', T_LED: 'LED', T_STATUS: 'STATUS'}
STATUS_NAMES = {1: 'DIAG_ENTER', 2: 'DIAG_EXIT', 3: 'EVQ_LOST', 4: 'GHOST'}
EV_NAMES = {0: 'up', 1: 'down', 2: 'ghost'}
KIND_NAMES = {0: 'none', 1: 'char', 2: 'func', 3: 'mod'}
LCDK_NAMES = {0: 'none', 1: 'CGROM', 2: 'CGRAM'}
FUNC_NAMES = {0: 'NONE', 1: 'LEFT', 2: 'RIGHT', 3: 'UP', 4: 'DOWN', 5: 'HOME', 6: 'END', 7: 'PGUP', 8: 'PGDN', 9: 'ENTER', 10: 'BKSP', 11: 'DEL', 12: 'INS',
              13: 'HELP', 14: 'PAUSE', 15: 'ANSWER', 16: 'REPEAT', 17: 'TAB', 18: 'CLEAR', 19: 'EXPORT', 20: 'SYM', 21: 'OFF'}
MOD_BITS = (('shift_l', 0x01), ('shift_r', 0x02), ('alt', 0x04), ('caps', 0x08), ('sym', 0x10), ('insert', 0x20))
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def crc16(data, crc=0xFFFF):
    """CRC-16/CCITT-FALSE: poly 0x1021, init 0xFFFF, sin reflejo. crc16(b'123456789') == 0x29B1"""
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def encode_frame(ftype, seq, payload):
    """reference encoder (for tests and for making captures): END stuff(GE ver type seq len payload crc) END"""
    body = bytes([0x47, 0x45, VER, ftype]) + seq.to_bytes(2, 'little') + len(payload).to_bytes(2, 'little') + bytes(payload)
    body += crc16(body).to_bytes(2, 'little')
    out = bytearray([END])
    for b in body:
        if b == END: out += bytes([ESC, ESC_END])
        elif b == ESC: out += bytes([ESC, ESC_ESC])
        else: out.append(b)
    out.append(END)
    return bytes(out)


class FrameParser:
    """splits SLIP frames and validates header, length and CRC. feed(bytes) -> list of ('frame', dict) / ('error', dict)"""
    def __init__(self):
        self.buf = bytearray(); self.esc = False; self.bad = False; self.pos = 0

    def feed(self, data):
        out = []
        for b in data:
            self.pos += 1
            if b == END:
                if self.buf or self.esc or self.bad:
                    out.append(self._finish())
                self.buf = bytearray(); self.esc = False; self.bad = False
                continue
            if self.bad: continue
            if self.esc:
                self.esc = False
                if b == ESC_END: self.buf.append(END)
                elif b == ESC_ESC: self.buf.append(ESC)
                else: self.bad = 'bad_escape'
            elif b == ESC: self.esc = True
            else: self.buf.append(b)
        return out

    def _finish(self):
        pos = self.pos
        if self.bad: return ('error', dict(kind=self.bad, at=pos))
        if self.esc: return ('error', dict(kind='truncated_escape', at=pos))
        f = bytes(self.buf)
        if len(f) < 10: return ('error', dict(kind='too_short', len=len(f), at=pos))
        if f[0:2] != b'GE': return ('error', dict(kind='bad_magic', at=pos))
        if f[2] != VER: return ('error', dict(kind='bad_version', version=f[2], at=pos))
        ln = int.from_bytes(f[6:8], 'little')
        if len(f) != 8 + ln + 2: return ('error', dict(kind='bad_length', declared=ln, actual=len(f) - 10, at=pos))
        crc = int.from_bytes(f[-2:], 'little')
        if crc16(f[:-2]) != crc: return ('error', dict(kind='bad_crc', got=crc, want=crc16(f[:-2]), at=pos))
        return ('frame', dict(type=f[3], seq=int.from_bytes(f[4:6], 'little'), payload=f[8:8 + ln], at=pos))


def u16(b, o): return int.from_bytes(b[o:o + 2], 'little')


class Receiver:
    def __init__(self, outdir, keep_partial=False, key_names=None, log=print):
        self.outdir = outdir; self.keep_partial = keep_partial; self.log = log
        os.makedirs(outdir, exist_ok=True)
        self.parser = FrameParser()
        self.expect_seq = None
        self.doc = None; self.ndoc = 0
        self.counts = dict(frames=0, errors=0, docs_ok=0, docs_bad=0, keys=0, leds=0, seq_gaps=0)
        self.last_mods = None; self.last_led = None
        self.f = {n: open(os.path.join(outdir, n), 'a', encoding='utf-8') for n in ('key_events.jsonl', 'modifier_events.jsonl', 'led_events.jsonl', 'protocol_errors.jsonl')}
        self.key_names = key_names or {}
        self.results = []

    def close(self):
        for f in self.f.values(): f.close()
        with open(os.path.join(self.outdir, 'summary.json'), 'w') as fh: json.dump(self.counts, fh, indent=1)

    def _w(self, name, obj): self.f[name].write(json.dumps(obj, ensure_ascii=False) + '\n'); self.f[name].flush()
    def _err(self, kind, **kw): self.counts['errors'] += 1; d = dict(kind=kind, t=time.time(), **kw); self._w('protocol_errors.jsonl', d); self.log('ERROR de protocolo: %s %s' % (kind, kw)); self.results.append(('error', d))

    def feed(self, data):
        for what, d in self.parser.feed(data):
            if what == 'error': self._err(**d); continue
            self.counts['frames'] += 1
            if self.expect_seq is not None and d['seq'] != self.expect_seq:
                self.counts['seq_gaps'] += 1; self._err('seq_gap', expected=self.expect_seq, got=d['seq'])
            self.expect_seq = (d['seq'] + 1) & 0xFFFF
            self.handle(d['type'], d['payload'], d['seq'])

    def handle(self, t, p, seq):
        if t == T_HELLO and len(p) == 8:
            self.results.append(('hello', dict(ver=p[0], hc=p[1], f=p[2], ram_ok=u16(p, 4), doc_max=u16(p, 6))))
        elif t == T_DOC_BEGIN and len(p) == 6:
            if self.doc is not None: self._err('doc_begin_while_open')
            self.doc = dict(total=u16(p, 0), nchars=u16(p, 2), nlines=u16(p, 4), data=bytearray(), gaps=0)
        elif t == T_DOC_DATA and len(p) >= 2:
            if self.doc is None: self._err('doc_data_without_begin'); return
            off = u16(p, 0)
            if off != len(self.doc['data']): self.doc['gaps'] += 1; self._err('doc_offset_gap', expected=len(self.doc['data']), got=off); return
            self.doc['data'] += p[2:]
        elif t == T_DOC_END and len(p) == 4:
            self.end_doc(u16(p, 0), u16(p, 2))
        elif t == T_KEY and len(p) == 14:
            self.key(p)
        elif t == T_LED and len(p) == 6:
            d = dict(ev=u16(p, 0), tick=u16(p, 2), led=p[4], port12=p[5])
            self.counts['leds'] += 1; self._w('led_events.jsonl', d); self.results.append(('led', d))
            self._mod_change(d['ev'], d['tick'], None, d['led'])
        elif t == T_STATUS and len(p) == 7:
            d = dict(ev=u16(p, 0), tick=u16(p, 2), code=STATUS_NAMES.get(p[4], p[4]), arg=u16(p, 5))
            self.results.append(('status', d)); self._w('key_events.jsonl', dict(status=d))
        else:
            self._err('unknown_or_bad_frame', type=t, len=len(p))

    def end_doc(self, total, crc):
        d = self.doc; self.doc = None
        if d is None: self._err('doc_end_without_begin'); return
        data = bytes(d['data']); ok = True; why = []
        if len(data) != total or total != d['total']: ok = False; why.append('length %d/%d/%d' % (len(data), total, d['total']))
        if crc16(data) != crc: ok = False; why.append('crc %04X/%04X' % (crc16(data), crc))
        if d['gaps']: ok = False; why.append('gaps')
        try: text = data.decode('utf-8')
        except UnicodeDecodeError as e: ok = False; why.append('utf8: %s' % e); text = None
        if ok and (len(text) != d['nchars'] or text.count('\n') + 1 != d['nlines']): ok = False; why.append('lines/chars')
        self.ndoc += 1
        base = os.path.join(self.outdir, 'export_%03d' % self.ndoc)
        if ok:
            with open(base + '.txt', 'wb') as fh: fh.write(data)
            with open(base + '.txt.sha256', 'w') as fh: fh.write('%s  %s\n' % (hashlib.sha256(data).hexdigest(), os.path.basename(base) + '.txt'))
            self.counts['docs_ok'] += 1; self.log('documento OK -> %s.txt (%d bytes UTF-8, %d caracteres)' % (base, len(data), len(text)))
        else:
            self.counts['docs_bad'] += 1; self._err('doc_rejected', why=why)
            if self.keep_partial:
                with open(base + '.PARTIAL_UNVERIFIED.txt', 'wb') as fh: fh.write(data)
        self.results.append(('doc', dict(ok=ok, why=why, bytes=data, text=text, path=base + '.txt' if ok else None)))

    def key(self, p):
        mods = {n: bool(p[8] & b) for n, b in MOD_BITS}
        kind = KIND_NAMES.get(p[9], p[9]); val = u16(p, 10)
        d = dict(ev=u16(p, 0), tick=u16(p, 2), event=EV_NAMES.get(p[4], p[4]), scan=p[5], scan_hex='%02X' % p[5], matrix=2 if p[5] >= 0x40 else 1,
                 col=p[6], row=p[7], key=self.key_names.get(p[5], '?'), mods=mods, kind=kind, value=val,
                 lcd_kind=LCDK_NAMES.get(p[12], p[12]), lcd=p[13] if p[12] else None)
        if kind == 'char': d['unicode'] = 'U+%04X' % val; d['char'] = chr(val)
        elif kind == 'func': d['func'] = FUNC_NAMES.get(val, val)
        self.counts['keys'] += 1; self._w('key_events.jsonl', d); self.results.append(('key', d))
        self._mod_change(d['ev'], d['tick'], p[8], None)

    def _mod_change(self, ev, tick, mods, led):
        cur = dict(self.last_mods or {})
        if mods is not None:
            new = {n: bool(mods & b) for n, b in MOD_BITS if n != 'insert'}
            for n, v in new.items():
                if cur.get(n) != v: self._w('modifier_events.jsonl', dict(ev=ev, tick=tick, modifier=n, state=v)); cur[n] = v
            self.last_mods = cur
        if led is not None and led != self.last_led:
            self._w('modifier_events.jsonl', dict(ev=ev, tick=tick, modifier='led', state=bool(led))); self.last_led = led


def default_outdir():
    return os.path.join(PROJECT, 'captures', time.strftime('%Y%m%d_%H%M%S'))


def load_key_names():
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import ge_keynames
        return ge_keynames.NAMES
    except Exception:
        return {}


def main(argv=None):
    ap = argparse.ArgumentParser(description='Receiver of the Genio 2000 editor (receive only)')
    ap.add_argument('--port'); ap.add_argument('--baud', type=int, default=9600)
    ap.add_argument('--input', help='captura cruda (sin hardware)')
    ap.add_argument('--outdir', help='carpeta de salida (por defecto <proyecto>/captures/<fecha>)')
    ap.add_argument('--keep-partial', action='store_true')
    ap.add_argument('--duration', type=float, default=0, help='segundos (0 = hasta Ctrl-C)')
    a = ap.parse_args(argv)
    if bool(a.port) == bool(a.input): ap.error('indica --port o --input')
    outdir = os.path.abspath(a.outdir) if a.outdir else default_outdir()
    rx = Receiver(outdir, a.keep_partial, load_key_names())
    raw = open(os.path.join(outdir, 'raw_stream.bin'), 'ab')
    try:
        if a.input:
            with open(a.input, 'rb') as fh: data = fh.read()
            raw.write(data); rx.feed(data)
        else:
            import serial
            ser = serial.Serial(a.port, a.baud, bytesize=8, parity='N', stopbits=1, timeout=0.2)
            print('escuchando %s %d 8N1 -> %s (Ctrl-C para terminar)' % (a.port, a.baud, outdir)); t0 = time.time()
            try:
                while not a.duration or time.time() - t0 < a.duration:
                    d = ser.read(256)
                    if d: raw.write(d); raw.flush(); rx.feed(d)
            except KeyboardInterrupt: pass
            ser.close()
    finally:
        raw.close(); rx.close()
    c = rx.counts
    print('tramas %d, errores %d, documentos OK %d / rechazados %d, teclas %d, LED %d, huecos de secuencia %d' % (c['frames'], c['errors'], c['docs_ok'], c['docs_bad'], c['keys'], c['leds'], c['seq_gaps']))
    return 0 if c['errors'] == 0 else 2


if __name__ == '__main__':
    sys.exit(main())
