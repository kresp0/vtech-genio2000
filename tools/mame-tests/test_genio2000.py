"""Automated tests for the genio2000 driver.  Needs the PRIVATE ROMs in roms_local/ (never published) and the build in mame/genio.
Run: python3 -m pytest -q tests      Environment: GENIO_MAME, GENIO_ROMPATH, GENIO_BASELINE_BIN (unpatched build, for regression)."""
import os, sys, re, glob, hashlib, zlib, subprocess, tempfile, pytest, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import genio_run as G, render_lib as R, lcd_ocr
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import analyze_p12
FW = os.path.join(G.ROMS, 'genio2000', 'genio2000_es_128k.bin')
CGFILE = os.path.join(G.ROMS, 'genio2000', 'genio2000_cgrom_reconstructed.bin')
CART = os.path.join(G.ROMS, 'carts', 'genio_demo_gl4000_AT28C256_32K.bin')
BASE = os.environ.get('GENIO_BASELINE_BIN', os.path.join(ROOT, '..', 'dev', 'mame-cgrom', 'mame-src-build', 'mame_baseline_genio'))
CGROM = open(CGFILE, 'rb').read()
# Tests that need the EXPERIMENTAL CLOCK / IRQ / SOUND switches exist only on branch genio2000-dev; run the PR-candidate binary with GENIO_CANDIDATE=1.
dev_only = pytest.mark.skipif(bool(os.environ.get('GENIO_CANDIDATE')), reason='experimental switches are not part of the PR candidate')

def mame(args, env=None, timeout=300, binary=None):
    if '-artpath' not in args: args = args + ['-snapview', 'native', '-artpath', os.path.join(ROOT, 'work', 'noart')]      # the photo artwork would change the snapshots
    return subprocess.run([binary or G.MAME] + args, capture_output=True, text=True, timeout=timeout, env=dict(os.environ, **(env or {})))
def tmp(): return tempfile.mkdtemp(prefix='g_', dir=os.path.join(ROOT, 'work'))
def lua(script, seconds, env, machine='genio2000', binary=None, extra=()):
    w = tmp()
    a = [machine, '-rompath', G.ROMS, '-homepath', w + '/h', '-cfg_directory', w + '/c', '-nvram_directory', w + '/n', '-snapshot_directory', w + '/s',
         '-video', 'none', '-sound', 'none', '-seconds_to_run', str(seconds), '-nothrottle', '-skip_gameinfo', '-snapview', 'native', '-artpath', os.path.join(ROOT, 'work', 'noart'), '-autoboot_script', os.path.join(HERE, 'lua', script), *extra]
    p = mame(a, env, binary=binary); return p, w

# ---- hashes / ROM definition -------------------------------------------------------------------------------------------------
def test_firmware_hashes():
    d = open(FW, 'rb').read()
    assert len(d) == 131072
    assert hashlib.sha1(d).hexdigest() == '76e41bc3b19f3f0c0ae4605257ba4ee9d812659f'
    assert hashlib.sha256(d).hexdigest() == 'f66f4d51d7152a8264ff9d99cbeb38dbbb5cc2d6f087e3fffb4e067f42e5ea48'
    assert '%08x' % zlib.crc32(d) == '7a9d7b8a'

def test_cgrom_binary_format():
    assert len(CGROM) == 4096
    assert '%08x' % zlib.crc32(CGROM) == '1f712c25' and hashlib.sha1(CGROM).hexdigest() == '0ad6de16db67c014f44211dfd1328091be389cc7'
    assert not any(CGROM[0x00 * 16:0x20 * 16])                 # codes 0x00-0x1F are CGRAM, must be zero in the ROM
    assert all(b & 0xE0 == 0 for b in CGROM)                    # 5-pixel wide glyphs
    assert not any(any(CGROM[c * 16 + 8:c * 16 + 16]) for c in range(256))   # rows 8-15 unused in the 5x8 font
    assert all(any(CGROM[c * 16:c * 16 + 8]) for c in range(0x21, 0x7f))   # every printable ASCII glyph non-blank

def test_cgrom_eighth_row_used_only_by_ten_symbol_glyphs():
    # normal letters with descenders (g j p q y , ;) stay inside the first 7 rows; the 8th row is used by 10 codes in 0xE0-0xFC (owner's observation, docs/CGROM.md)
    assert [c for c in range(256) if CGROM[c * 16 + 7]] == [0xE0, 0xE1, 0xE4, 0xE5, 0xEA, 0xEC, 0xEE, 0xF2, 0xF3, 0xFC]
    assert not any(CGROM[ord(ch) * 16 + 7] for ch in 'gjpqy,;')

def test_validate_and_romdef():
    p = mame(['-validate', 'genio2000']); assert p.returncode == 0, p.stdout + p.stderr
    p = mame(['-listroms', 'genio2000']); out = p.stdout
    assert '27-5575-00' in out and '7a9d7b8a' in out.lower() and '76e41bc3b19f3f0c0ae4605257ba4ee9d812659f' in out
    assert 'genio2000_cgrom_reconstructed.bin' in out and '1f712c25' in out.lower()
    p = mame(['-rompath', G.ROMS, '-verifyroms', 'genio2000']); assert 'NEEDS REDUMP' in p.stdout     # BAD_DUMP honoured
    assert '27-5575-00' not in p.stdout          # -verifyroms only reports problems: the firmware (CRC/SHA1) is fine

def test_bank_mirroring_matches_hardware_observation():
    """Entry n of the 32 selectable banks = bank (n & 7): measured on the real unit for selector 0x00-0x1F of port 0x01."""
    log = os.path.join(tmp(), 'bank.txt'); p, w = lua('bank_check.lua', 3, {'GENIO_FW': FW, 'GENIO_LOG': log}); txt = open(log).read()
    assert 'RESULT OK' in txt and txt.count(': OK') == 32, txt

def test_cgrom_region_is_the_reconstructed_file():
    out = os.path.join(tmp(), 'r.bin'); lua('region_dump.lua', 3, {'GENIO_OUT': out, 'GENIO_REGION': ':hd44780'})
    assert open(out, 'rb').read() == CGROM

def test_gl4000_keeps_device_default_cgrom():
    out = os.path.join(tmp(), 'g.bin'); lua('region_dump.lua', 3, {'GENIO_OUT': out, 'GENIO_REGION': ':hd44780:cgrom'}, machine='gl4000')
    got = open(out, 'rb').read(); assert len(got) == 4096 and got != CGROM

# ---- boot / LCD ---------------------------------------------------------------------------------------------------------------
def test_boot_welcome_screen():
    shots, p, _ = G.run('9:snap;10:quit', seconds=12)
    assert shots and shots[0][0].strip().endswith('Hola! Por favor') and 'elige' in shots[0][1] and 'una' in shots[0][2]
    assert shots[0][0].startswith('  {A9}Hola!')          # inverted exclamation mark = CGROM 0xA9

def test_lcd_data_register_sends_a9_before_hola():
    log = os.path.join(tmp(), 'l.log'); lua('lcd_data_log.lua', 20, {'GENIO_LOG': log, 'GENIO_STOP': '14'})
    dr = [int(l.split()[2], 16) for l in open(log) if ' DR ' in l]
    s = bytes(dr); assert b'\xa9Hola!' in s and b'\xadHola!' not in s

# ---- keyboard (layer E: what the firmware does with a key; layer D: PORT_NAME = legend on the Genio key) -----------------------
ACT = [('ALGEBRA', 'ALGEBRA'), ('BASIC', 'BASIC'), ('SUMA', 'SUMA'), ('PLURALES', 'PLURAL'), ('SINONIMOS', 'SINONIMOS'),
       ('CALCULADORA', 'CALCULADORA'), ('IMPRIMIR TEXTO', 'IMPRIMIR'), ('RESTA', 'RESTA'), ('MULTIPLICACION', 'MULTIPLICACION'),
       ('DIVISION', 'DIVISION'), ('CIENCIAS', 'CIENCIAS'), ('RATIOS', 'RATIOS')]
@pytest.mark.parametrize('key,expect', ACT)
def test_activity_key_opens_its_activity(key, expect):
    shots, p, _ = G.run('20:press:%s;' % key + ';'.join('%.1f:snap' % t for t in (20.8, 21.2, 21.6, 22.0, 22.5, 23.0, 23.5, 24.0, 24.5, 25.0, 26.0)) + ';27:quit', seconds=28)
    assert 'MISSING FIELD' not in p.stdout
    text = '\n'.join('\n'.join(s) for s in shots); assert expect in text, text

def test_off_key_says_goodbye():
    shots, _, _ = G.run('20:press:OFF;22:snap;23:snap;24:snap;25:quit', seconds=26); assert any('HASTA LUEGO' in '\n'.join(s) for s in shots)

def fields():
    log = os.path.join(tmp(), 'f.txt'); lua('list_fields.lua', 2, {'GENIO_LOG': log})
    return [l.rstrip('\n').split('\t') for l in open(log)]

def test_keyboard_labels_match_firmware_verified_table():
    """Every matrix-1 key: field INcol bit row has the legend of data/teclado_es_source.csv (derived from the firmware tables + photo)."""
    import csv
    f = {(r[0], int(r[1], 16)): r[3] for r in fields() if len(r) > 3}
    rows = [r for r in csv.DictReader(open(os.path.join(ROOT, 'data/teclado_es_source.csv'), encoding='utf-8')) if r['matriz'] == '1']
    assert len(rows) >= 55
    for r in rows:
        tag = ':IN%d' % int(r['columna_out']); mask = 1 << int(r['fila_in'])
        assert (tag, mask) in f, (r['tecla'], tag, mask)
    names = set(f.values())
    for n in ('PAUSA', 'AYUDA', 'ALT', 'INTRO', 'ESPACIO', 'RESPUESTA', 'BLOQ. MAYUSCULAS', 'RETROCESO', 'AVANCE', 'BASIC', 'OFF', '2 JUGADORES', 'CARTUCHOS ADICIONALES'):
        assert n in names, n
    assert not names & {'Letter Hunt', 'Plurals', 'Calculator', 'Caps Lock', 'HOME'}      # German driver labels must not leak in
    assert len([n for n in names if n in ('MAYUSCULAS', 'MAYUSCULAS (izq.)', 'MAYUSCULAS (der.)')]) == 1  # one matrix intersection serves both shift keys

# ---- bank selects --------------------------------------------------------------------------------------------------------------
def test_bank_selects_boot_and_algebra():
    d = tmp(); bl = d + '/banks.log'; inv = d + '/inv.txt'
    G.run  # noqa
    p, w = lua('io_inventory.lua', 40, {'GENIO_STOP': '28', 'GENIO_SCEN': '21:press:ALGEBRA', 'GENIO_LOG': inv, 'GENIO_BANKLOG': bl})
    rows = [l.split() for l in open(bl)]
    first = [(r[1], r[2]) for r in rows[:3]]
    assert ('01', '00') in first                                   # boot: XOR A; OUT (01),A
    assert ('01', '05') in [(r[1], r[2]) for r in rows]            # ALGEBRA selects bank 5 in the 0x4000 window
    assert all(r[1] != '00' for r in rows)                         # port 0x00 never written (also true of the static analysis)
    assert all(int(r[2], 16) <= 0x1f or r[1] == '03' for r in rows)
    inv_txt = open(inv).read(); assert '06 W 40' in inv_txt and not re.search(r'^06 R', inv_txt, re.M)

# ---- CGROM diagnostic pages (demo cartridge, option 4) ---------------------------------------------------------------------------
@pytest.fixture(scope='session')
def pages():
    shots_dir = tmp()
    scen = '9:snap;10:press:4;12:snap;13:press:ESPACIO;15:snap;16:press:ESPACIO;18:snap;19:quit'
    G.run(scen, seconds=20, extra=['-cart', CART], snapdir=shots_dir)
    import glob; return sorted(glob.glob(shots_dir + '/snap/*/*.png'))

def test_demo_menu_boots(pages):
    assert len(pages) == 4
    menu = R.decode_snapshot(pages[0])
    for r, line in enumerate(['GENIO 2000 ES  DEMO  ', '1 LCD 2 ESP 3 TECL  ', '4 CGROM  OFF=APAGAR  '][:3]):
        for c, ch in enumerate(line[:20]):
            if ch != ' ': assert (menu[r, c] == R.glyph_bits(CGROM, ord(ch))).all(), (r, c, ch)

@pytest.mark.parametrize('page,base', [(1, 0x20), (2, 0x70), (3, 0xC0)])
def test_three_cgrom_diagnostic_screens_match_binary(pages, page, base):
    got = R.decode_snapshot(pages[page]); exp = R.expected_screen(CGROM, R.page_codes(base))
    diff = np.argwhere((got != exp).any(axis=(2, 3))); assert len(diff) == 0, diff.tolist()

def test_cgrom_differs_from_stock_a00(pages):
    stock = os.path.join(G.ROMS, 'hd44780', 'hd44780_a00.bin')
    assert os.path.exists(stock)
    a = open(stock, 'rb').read(); diff = sum(1 for c in range(0xA0, 0x100) if a[c * 16:c * 16 + 8] != CGROM[c * 16:c * 16 + 8]); assert diff > 20

# ---- regression: gl4000 unchanged ------------------------------------------------------------------------------------------------
@pytest.mark.skipif(not os.path.exists(BASE), reason='no unpatched baseline build')
def test_gl4000_identical_to_baseline():
    outs = []
    for b in (G.MAME, BASE):
        d = tmp()
        a = ['gl4000', '-rompath', G.ROMS, '-homepath', d + '/h', '-cfg_directory', d + '/c', '-nvram_directory', d + '/n', '-snapshot_directory', d + '/s', '-video', 'none',
             '-sound', 'none', '-seconds_to_run', '14', '-nothrottle', '-skip_gameinfo', '-cart', CART, '-autoboot_script', os.path.join(HERE, 'lua/scenario.lua')]
        mame(a, {'GENIO_SCEN': '9:snap;10:press:IN3;11:quit'}, binary=b)
        import glob; outs.append([open(f, 'rb').read() for f in sorted(glob.glob(d + '/s/*/*.png'))])
    assert outs[0] and outs[0] == outs[1]

# ---- sound / clock (EXPERIMENTAL switches; nothing here proves the real clock) -------------------------------------------------------
def tone_freqs(clocksel=0):
    d = tmp(); log = d + '/p.log'
    if clocksel:
        subprocess.run([sys.executable, os.path.join(ROOT, 'tools/set_cfg.py'), d + '/c', 'CLOCK=%d' % clocksel], check=True)
    a = ['genio2000', '-rompath', G.ROMS, '-homepath', d + '/h', '-cfg_directory', d + '/c', '-nvram_directory', d + '/n', '-video', 'none', '-sound', 'none', '-seconds_to_run', '6',
         '-nothrottle', '-skip_gameinfo', '-autoboot_script', os.path.join(HERE, 'lua/port12_log.lua')]
    mame(a, {'GENIO_LOG': log, 'GENIO_STOP': '3'})
    return analyze_p12.tones(log)

@dev_only
def test_boot_melody_is_a_bit_banged_scale_at_4_mhz():
    t = [x for x in tone_freqs(9) if x[2] > 20]
    assert len(t) >= 5
    f = [x[1] for x in t[:5]]
    # tone routine at 0x1364: period = 256 + 52*HL T-states; HL values of the note stubs give a major scale -> ratios 5:4, 3:2, 4:3, 5:4
    r = [x / f[0] for x in f]; assert abs(r[1] - 1.267) < 0.01 and abs(r[2] - 1.506) < 0.01 and abs(r[3] - 1.333) < 0.01 and abs(r[4] - 1.267) < 0.01
    assert abs(f[0] - 305.5) < 1.0                              # 4 MHz default (analytic: 4e6 / (256 + 52*HL) with HL = 0xE3?)

# Emulator behaviour of the experimental CLOCK switch (NOT a statement about the hardware): the notes are bit-banged by a tone loop that is interrupted by the
# enabled 50 Hz IM 1 interrupt, so pitch AND tempo scale with (clock - S) where S = irq_rate x ISR_cycles; fitted on the 3..8 MHz runs: S = 0.476e6 cycles/s
# (about 9.5k T-states per interrupt).  See docs/CLOCK_AND_SOUND.md.
CLOCKS = {1: 3.0, 2: 3.579545, 3: 4.194304, 4: 4.9152, 5: 5.0, 6: 6.0, 7: 6.144, 8: 8.0}
@dev_only
@pytest.mark.parametrize('sel', sorted(CLOCKS))
def test_clock_switch_follows_effective_clock_model(sel):
    S = 0.476e6
    def note104(t): return [x for x in t if x[2] == 104][0]
    b = note104(tone_freqs(9)); a = note104(tone_freqs(sel))             # index 9 = 4.000 MHz, the reference of the model
    pred = (CLOCKS[sel] * 1e6 - S) / (4e6 - S)
    assert abs(a[1] / b[1] / pred - 1) < 0.015, (a, b, pred)
    assert abs((b[3] / a[3]) / pred - 1) < 0.015

# ---- CGRAM / codes 0x00-0x0F / 8th row ---------------------------------------------------------------------------------------------
def test_cgram_codes_and_aliases_render_like_the_hd44780():
    codes = list(range(0x10)) + [0x41, 0x9B, 0x9C, 0x82, 0xA9, 0x9F, 0xE4, 0xED, 0xBE, 0xB7] + [0xFF - i for i in range(54)]
    shots_dir = tmp(); w = shots_dir
    a = ['genio2000', '-rompath', G.ROMS, '-homepath', w + '/h', '-cfg_directory', w + '/c', '-nvram_directory', w + '/n', '-snapshot_directory', w + '/s', '-video', 'none', '-sound', 'none',
         '-seconds_to_run', '40', '-nothrottle', '-skip_gameinfo', '-cart', CART, '-autoboot_script', os.path.join(HERE, 'lua/cgram_probe.lua')]
    mame(a, {'GENIO_POKE': ','.join('%02X' % c for c in codes[:80])})
    import glob; shots = sorted(glob.glob(w + '/s/*/*.png')); assert shots
    cg = [((k + 1) * (r + 3) * 5) & 0x1F for k in range(8) for r in range(8)]
    got = R.decode_snapshot(shots[-1]); exp = R.expected_screen(CGROM, codes[:80], cg)
    # the firmware may keep drawing its own screen on top (IRQ-driven redraw is not expected here); compare cell by cell
    diff = np.argwhere((got != exp).any(axis=(2, 3))); assert len(diff) == 0, diff.tolist()
    # aliases: code 0x08+n shows the same glyph as 0x00+n
    assert all((got[0, n] == got[0, 8 + n]).all() for n in range(8))


# ---- timing reproduction (experimental switches; tools/timing_run.sh) ---------------------------------------------------------------
import json
def timing(sc, clk, irq):
    out = os.path.join(tmp(), 't')
    p = subprocess.run([os.path.join(ROOT, 'tools', 'timing_run.sh'), sc, str(clk), str(irq), out], capture_output=True, text=True, timeout=300)
    assert p.returncode == 0, p.stderr
    return json.loads(open(os.path.join(out, 'summary.json')).read())

@dev_only
def test_timing_reference_runs_are_stable():
    # emulation-only reference values (logs/timing/emulation); any change means the driver timing changed
    b = timing('boot', 9, 0); assert abs(b['first_char_A9'] - 4.403) < 0.005 and abs(b['typing_span'] - 5.124) < 0.01
    b = timing('boot', 6, 0); assert abs(b['title_to_first_char'] - 2.809) < 0.01 and abs(b['typing_span'] - 5.123) < 0.01
    assert abs(timing('off', 9, 0)['sound_span'] - 3.784) < 0.01 and abs(timing('off', 6, 0)['sound_span'] - 2.523) < 0.01

@dev_only
@pytest.mark.parametrize('irq,hz', [(1, 40), (4, 60), (6, 100)])
def test_irq_switch_scales_welcome_typing_only(irq, hz):
    # the welcome-screen typing is paced by interrupt ticks: ~256.1 ticks at any CPU clock
    b = timing('boot', 6, irq)
    if hz <= 60: assert abs(b['typing_span'] * hz - 256.1) < 0.6, b
    assert abs(timing('off', 6, irq)['sound_span'] - 2.523) < 0.01     # the farewell sound is CPU-bound, not interrupt-paced


# ---- BASIC editor special keys (T5): the real unit showed the same behaviour (hardware observation 2026-11-09, docs/KEYBOARD.md) ------------------------
def test_basic_editor_special_keys_match_hardware_observation():
    # keys are sent once the BASIC prompt is up (a key pressed before ~25 s of emulated time is lost: BASIC is still initialising).  In the real unit's editor ALT+U-umlaut, ALT+; (up/down codes), RESPUESTA,
    # AYUDA and REPETIR/BORRAR have no visible effect, and SHIFT+PAUSA gives a line break.
    shift = 'MAYUSCULAS' if 'MAYUSCULAS' in {r[3] for r in fields() if len(r) > 3} else 'MAYUSCULAS (der.)'   # the PR 2 review renamed the shared contact
    keys = ['B', 'ALT+\u00dc', 'ALT+;', 'RESPUESTA', 'AYUDA', 'REPETIR / BORRAR', shift + '+REPETIR / BORRAR', shift + '+PAUSA']
    t = 30; scen = '12:press:BASIC'
    for k in keys:
        scen += ';%d:press:%s;%d:snap' % (t, k, t + 1.5); t += 3
    shots, p, _ = G.run(scen + ';%d:quit' % (t + 1), seconds=t + 3, hold=0.4)
    assert 'MISSING FIELD' not in p.stdout and len(shots) == len(keys)
    typed = ['|'.join(l.rstrip() for l in s) for s in shots]
    assert typed[0] == 'READY|b?||'
    assert all(x == typed[0] for x in typed[1:-1]), typed       # no visible effect (presumably used by the activities, not by the BASIC editor; not verified)
    assert typed[-1] == 'READY|b|?|', typed                      # SHIFT+PAUSA = line break


# ---- photo artwork, power model, contrast switch, LED output (artwork/genio2000, tools/gen_artwork.py) --------------------------------------------------------
def layout_fields():
    log = os.path.join(tmp(), 'f.txt'); lua('list_fields.lua', 3, {'GENIO_LOG': log})
    return {(l.split('\t')[0].lstrip(':'), int(l.split('\t')[1], 16)): l.split('\t')[3] for l in open(log, encoding='utf-8')}

def test_artwork_clickable_items_exist_as_input_fields():
    import xml.etree.ElementTree as ET
    f = layout_fields(); items = [e for e in ET.parse(os.path.join(ROOT, 'artwork', 'genio2000', 'default.lay')).getroot().iter('element') if e.get('inputtag')]
    assert len({(e.get('inputtag'), e.get('inputmask')) for e in items}) == 96   # 55 distinct main-key positions (both SHIFT keys share one contact) + 40 panel buttons (incl. ON; each one is several strips approximating its oval) + the contrast switch   # was 56 keys + 40 panel buttons (incl. ON; each one is several strips approximating its oval) + the contrast switch
    for e in items:
        tag, mask = e.get('inputtag'), int(e.get('inputmask'), 16)
        assert (tag, mask) in f, (tag, mask)

def test_power_off_blanks_lcd_and_on_restarts_with_full_boot():
    # OFF (port 0x12 bit 0) halts the CPU and blanks the LCD; ON restarts the machine in place and shows the full start-up; the caps LED output follows port 0x12 bit 5
    d = tmp(); log = os.path.join(d, 'log')
    a = ['genio2000', '-rompath', G.ROMS, '-homepath', d + '/h', '-cfg_directory', d + '/c', '-nvram_directory', d + '/n', '-snapshot_directory', d + '/s', '-video', 'none', '-sound', 'none',
         '-seconds_to_run', '70', '-nothrottle', '-skip_gameinfo', '-snapview', 'native', '-artpath', os.path.join(ROOT, 'work', 'noart'), '-autoboot_script', os.path.join(HERE, 'lua', 'power_cycle.lua')]
    p = mame(a, {'GENIO_LOG': log}); text = open(log).read()
    assert 'led_caps after CAPS = 1' in text and 'led_caps after CAPS again = 0' in text, text
    shots = sorted(glob.glob(d + '/s/*/*.png')); assert len(shots) == 2, shots
    from PIL import Image
    assert len(set(Image.open(shots[0]).convert('RGB').getdata())) == 1                       # powered off: one flat colour
    assert 'Hola' in ' '.join(lcd_ocr.ocr(shots[1], G.CG)) or '\u00a1' in ' '.join(lcd_ocr.ocr(shots[1], G.CG)) or 'elige' in ' '.join(lcd_ocr.ocr(shots[1], G.CG))

def test_contrast_switch_darkens_the_lcd_by_the_photographed_ratio():
    # right position: LCD 14 % darker (all colours x 0.86) and the unlit dots more visible (22 % instead of 10 % of the way to a lit dot); the switch toggles back
    from PIL import Image
    shots, p, w = G.run('20:snap;21:press:Contrast switch (right = darker);23:snap;24:press:Contrast switch (right = darker);26:snap;28:quit', seconds=30)
    fs = sorted(glob.glob(w + '/snap/*/*.png')); assert len(fs) == 3, fs
    def pens(f):
        a = np.asarray(Image.open(f).convert('RGB')).reshape(-1, 3); u, n = np.unique(a, axis=0, return_counts=True)
        order = u.sum(1).argsort(); u = u[order].astype(float)          # darkest first: lit, then unlit, then background (three pens)
        assert len(u) == 3, u; return u
    left, right, back = pens(fs[0]), pens(fs[1]), pens(fs[2])
    assert np.abs(right[2] - left[2] * 0.86).max() <= 1 and np.abs(right[0] - left[0] * 0.86).max() <= 1, (left, right)     # background and lit dots x 0.86
    frac = lambda u: (u[2] - u[1]).sum() / (u[2] - u[0]).sum()                 # how far the unlit dot is from the background towards the lit one
    assert 0.08 < frac(left) < 0.12 and 0.19 < frac(right) < 0.25, (frac(left), frac(right))      # 10 % and 22 % (8-bit colours are rounded)
    assert np.array_equal(left, back)


def test_lcd_photographed_drawing_cell_layout():
    # 6x10 cells = glyph rows 0-6, row 7 never lit, glyph row 8 (eighth byte, e.g. the cursor underline), row 9 line gap; unlit dots faintly visible (third colour)
    from PIL import Image
    d = tmp()
    snaps = ';'.join('%.1f:snap' % t for t in (32.0, 32.3, 32.6, 32.9, 33.2, 33.5, 33.8, 34.1, 34.4, 34.7, 35.0))
    G.run('12:press:BASIC;' + snaps + ';36:quit', seconds=38, snapdir=d)
    fs = sorted(glob.glob(d + '/snap/*/*.png')); assert len(fs) == 11
    imgs = [np.asarray(Image.open(f).convert('RGB')).astype(int) for f in fs]
    bg = tuple(imgs[0][7, 0])
    for a in imgs:
        assert a.shape[:2] == (40, 120)
        assert all(tuple(c) == bg for c in a[7::10, :].reshape(-1, 3)), 'row 7 of every cell must be unlit background'
        assert all(tuple(c) == bg for c in a[9::10, :].reshape(-1, 3)), 'row 9 (line gap) must be unlit background'
        assert all(tuple(c) == bg for c in a[:, 5::6].reshape(-1, 3)), 'column 5 (character gap) must be unlit background'
    cols = {tuple(c) for a in imgs for c in a.reshape(-1, 3)}
    assert len(cols) == 3, cols                                                   # background, unlit dot, lit dot
    lit = [tuple(c) for c in cols if sum(c) == min(sum(x) for x in cols)][0]
    assert any(all(tuple(a[18, x]) == lit for x in range(5)) for a in imgs), 'cursor underline never seen in row 8 of cell (1,0)'
    unlit = [c for c in cols if c != bg and c != lit][0]
    assert 0 < sum(bg) - sum(unlit) < 0.2 * (sum(bg) - sum(lit)) + 1             # faint: closer to the background than to a lit dot


def test_on_button_resets_and_clears_ram_at_any_time():
    # hardware (owner): ON is reset + RAM clear + power-on, also when the machine is already running; done without a MAME hard reset (the window is kept)
    d = tmp(); log = os.path.join(d, 'log')
    a = ['genio2000', '-rompath', G.ROMS, '-homepath', d + '/h', '-cfg_directory', d + '/c', '-nvram_directory', d + '/n', '-snapshot_directory', d + '/s', '-video', 'none', '-sound', 'none',
         '-seconds_to_run', '70', '-nothrottle', '-skip_gameinfo', '-snapview', 'native', '-artpath', os.path.join(ROOT, 'work', 'noart'), '-autoboot_script', os.path.join(HERE, 'lua', 'on_reset.lua')]
    mame(a, {'GENIO_LOG': log}); shots = sorted(glob.glob(d + '/s/*/*.png')); assert len(shots) == 3, shots
    before, a1, a2 = ['\n'.join(lcd_ocr.ocr(f, G.CG)) for f in shots]
    assert 'READY' in before and 'b' in before, before                                         # BASIC with a typed character
    assert 'READY' not in a1 and 'READY' not in a2, (a1, a2)
    assert 'VTECH' in a1 or 'GENIO' in a1 or 'ELECTRONICS' in a1, a1                          # title screen of the start-up sequence
    assert 'Hola' in a2 or 'elige' in a2 or '\u00a1' in a2, a2                                  # then the welcome screen


def test_speaker_plays_the_boot_melody_at_the_measured_clock():
    # the 1-bit speaker follows port 0x12 bit 3: the start-up melody is 9 notes ending about 2.6 s after power-on (recordings of the unit: same tempo and pitch)
    from scipy.io import wavfile
    from scipy.signal import butter, sosfiltfilt
    d = tmp(); wav = os.path.join(d, 'boot.wav')
    mame(['genio2000', '-rompath', G.ROMS, '-homepath', d + '/h', '-cfg_directory', d + '/c', '-nvram_directory', d + '/n', '-video', 'none', '-wavwrite', wav, '-seconds_to_run', '5',
          '-nothrottle', '-skip_gameinfo', '-snapview', 'native', '-artpath', os.path.join(ROOT, 'work', 'noart')])
    sr, x = wavfile.read(wav); x = x.astype(float); x = x.mean(1) if x.ndim > 1 else x
    y = sosfiltfilt(butter(4, [350, 2500], 'band', fs=sr, output='sos'), x); n = int(sr * .01)
    env = np.array([np.sqrt(np.mean(y[i:i + n] ** 2)) for i in range(0, len(y) - n, n)]); on = env > 0.25 * np.percentile(env, 99)
    starts = [i for i in range(1, len(on)) if on[i] and not on[i - 1]] if on[0] else [i for i in range(1, len(on)) if on[i] and not on[i - 1]]
    runs = []
    for i in starts:
        if runs and (i - runs[-1]) * 0.01 < 0.03: continue
        runs.append(i)
    assert len(runs) >= 9, runs
    last_end = max(i for i in range(len(on)) if on[i]) * 0.01
    assert 2.4 < last_end < 2.8, last_end                                  # 2.59 s at 6.13179 MHz (the melody ends at 4.15 s at 4 MHz)
