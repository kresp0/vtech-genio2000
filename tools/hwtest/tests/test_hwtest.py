"""Offline tests of the hwtest program + receiver (Z80 interpreter with a hardware MODEL; no MAME, no hardware). Run: python3 -I -m pytest -q tests  (or python3 -I tests/test_hwtest.py)"""
import os, sys, json, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); HW = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HW, 'tools'))
import sim_hw, hwtest_rx as rx

ROM = open(os.path.join(os.path.dirname(HW), 'rom', 'genio2000_es_128k.bin'), 'rb').read()
CACHE = {}


def go(variant, **kw):
    key = (variant, tuple(sorted(kw.items())))
    if key not in CACHE:
        image = open(os.path.join(HW, 'build', variant, 'hwtest_%s_AT28C256_32K.bin' % variant), 'rb').read()
        R = sim_hw.run(image, ROM, sim_hw.Model(**kw), variant=variant)
        d = tempfile.mkdtemp(prefix='hwsim_')
        sim_hw.write_capture(R, d)
        r = rx.Run(); data = open(os.path.join(d, 'capture.bin'), 'rb').read(); pos = 0
        for line in open(os.path.join(d, 'capture.tlog')):
            t, n = line.split(); n = int(n); r.feed(float(t), data[pos:pos + n]); pos += n
        CACHE[key] = (R, r, rx.report(r, d))
    return CACHE[key]


def test_safety_invariants():
    R, r, res = go('ye')
    assert not R.pc_outside, 'code ran outside the cartridge window / RAM stub'
    assert len(R.rom_writes) == 1 and R.rom_writes[0][0] == 0x9BF0, 'only the same-value /WR probe may write outside RAM'
    assert R.rom_writes[0][1] == R.cpu.rb(0x9BF0), 'the probe must write the byte that is already stored'
    assert not R.bad_ports, 'IN/OUT on the LCD ports outside the LCD driver'
    ports = {p for p, v in R.port_writes}
    assert ports <= {0x03, 0x0A, 0x0B, 0x10, 0x11, 0x12}, sorted(ports)      # never 00 01 02 04 05 06
    assert all(not (v & 1) for p, v in R.port_writes if p == 0x12), 'power-off bit written'
    assert R.cpu.rb(0x8000) == 0x55 and R.cpu.rb(0x8001) == 0xAA, 'window 2 not restored to the cartridge at the end'


def test_complete_run_default_model():
    R, r, res = go('ye')
    assert r.ended and r.rejects == 0 and r.dec.line_errors == 0
    assert all(r.stages.get(s) == 'done' for s in rx.STAGES), r.stages
    assert r.start['variant'] == 'Y' and r.start['build'] == 0x0100
    assert len(r.mem) == 128 and res['e000_ff_blocks'] == 64
    assert res['ports']['12'] == [0xD6] * 3 or res['ports']['12'][0] in (0xDE, 0xD6)
    assert all(v == 'S' for v in res['answers'].values()) and len(res['answers']) == 6


def test_window_decode_matches_model():
    R, r, res = go('ye')
    w = {x['sel']: x for x in res['window']}
    for s in range(8):                                  # internal entries = the real ROM banks
        assert w['%02X' % s]['kind'] == 'internal bank %d' % s and w['%02X' % (s + 8)]['kind'] == 'internal bank %d' % s
    assert all(x['stable'] for x in res['window'])
    assert (w['80']['quarter_8K_lo'], w['80']['quarter_8K_hi'], w['81']['quarter_8K_lo']) == (0, 1, 2)   # A13 + page bit 0 -> EEPROM A14
    assert w['80']['crc32'] == w['82']['crc32'] != w['81']['crc32']


def test_clock_and_irq_recovered():
    for kw in (dict(), dict(f_cpu=4.0e6, irq_hz=50.0, e000='mirror', cart_a13=False, cart_pagebits=0x03)):
        R, r, res = go('ye', **kw)
        f = kw.get('f_cpu', 6.0e6)
        assert abs(res['clock']['cpu_clock_hz'] / f - 1) < 0.01, res['clock']
        assert abs(res['irq']['hz'] / kw.get('irq_hz', 60.0) - 1) < 0.01, res['irq']


def test_other_hardware_model_is_detected():
    R, r, res = go('ye', e000='mirror', cart_a13=False, cart_pagebits=0x03)
    w = {x['sel']: x for x in res['window']}
    assert (w['80']['quarter_8K_lo'], w['80']['quarter_8K_hi']) == (0, 0)             # A13 not wired: both 8K halves identical
    assert w['80']['crc32'] != w['81']['crc32'] == w['82']['crc32']                  # page bits 0/1 both OR into EEPROM A14 (32 KiB part)
    assert res['e000_mirror_blocks'] > 55                                               # RAM mirror at E000 (a few blocks hold live variables)


def test_wr_probe_detects_eeprom_busy():
    R, r, res = go('ye')
    assert res['wr_probe']['eeprom_busy'] is False and res['wr_probe']['content_changed'] is False
    R, r, res = go('ye', cart_wr=True)
    assert res['wr_probe']['eeprom_busy'] is True and res['wr_probe']['content_changed'] is False


def test_irq_stage_never_halts_and_survives_halt_poweroff_model():
    R, r, res = go('ye', halt_poweroff=True)
    assert not getattr(R, 'powered_off', False) and r.ended, 'the program must never execute HALT'
    assert res['irq']['reached_end'] and [f['count'] for f in res['irq']['frames'] if f['phase'] == 2] == [1, 5, 20, 100]
    assert R.cpu.rb(0xDFF5) == 0x33 and R.cpu.rb(0xDFF6) == 0 and R.cpu.rb(0xDFF4) == 0x14      # firmware hook restored


def test_ga_variant_runs():
    R, r, res = go('ga')
    assert r.ended and r.start['variant'] == 'G'


def test_key_events_decoded():
    R, r, res = go('ye')
    flat = ' '.join(' '.join(e['pressed']) for e in res['key_events'])
    assert 'A [col1,port10.b3]' in flat and 'ENTER' in flat


if __name__ == '__main__':
    import traceback
    fails = 0
    for n, f in sorted(globals().items()):
        if n.startswith('test_'):
            try: f(); print('PASS', n)
            except Exception: fails += 1; print('FAIL', n); traceback.print_exc()
    print(('%d failed' % fails) if fails else 'all passed'); sys.exit(1 if fails else 0)
