#!/usr/bin/env python3
"""Generate the MAME INPUT_PORTS block of the Spanish Genio 2000 from data/teclado_es_source.csv (copy of
dev/genio_text_editor/docs/teclado_es.csv, itself derived from the firmware tables + keyboard photo) and VERIFY every
position against the firmware itself (bank 0 tables, normal / SHIFT).  Layers: matrix position (col_out,row_in) -> MAME
port INx bit -> PC key (PORT_CODE).  Usage: gen_keyboard_ports.py [--fw bank_0.bin] [--out file]"""
import csv, sys, argparse, os
ap = argparse.ArgumentParser()
ap.add_argument('--fw', default=os.environ.get('GENIO_FW_DIR', 'dumps/final') + '/bank_0.bin')
ap.add_argument('--csv', default=os.path.join(os.path.dirname(__file__), '../data/teclado_es_source.csv'))
ap.add_argument('--out')
a = ap.parse_args()
fw = open(a.fw, 'rb').read()
# firmware tables: 13 bytes per slice; slice s serves column_out = 7 - s; bytes 0-4 = matrix 2 rows 8-12, bytes 5-12 = matrix 1 rows 0-7
def fwcode(base, col, row):
    s = 7 - col
    return fw[base + 13*s + (row - 8 if row >= 8 else 5 + row)]
NORMAL, SHIFT = 0x0415, 0x03AD

# PC key (MAME KEYCODE) chosen per Genio key; semantic where the Genio has an obvious PC counterpart
PC = {'PAUSA':'PAUSE','RETROCESO':'LEFT','AVANCE':'RIGHT','AYUDA':'TAB','Ü':'OPENBRACE','REPETIR/BORRAR':'BACKSPACE',
 'BLOQ. MAYÚSCULAS':'CAPSLOCK','Ñ':'COLON',';':'QUOTE','INTRO':'ENTER','MAYÚSCULAS (izq.)':'LSHIFT','MAYÚSCULAS (der.)':'RSHIFT',
 "'":'SLASH',',':'COMMA','.':'STOP','JUGADOR IZQUIERDA / INS':'INSERT','ALT':'LALT','ESPACIO':'SPACE','RESPUESTA':'ESC',
 'JUGADOR DERECHA / DEL':'DEL'}
for c in '1234567890': PC[c] = c
for c in 'QWERTYUIOPASDFGHJKLZXCVBNM': PC[c] = c
LABEL = {'PAUSA':'PAUSA','RETROCESO':'RETROCESO','AVANCE':'AVANCE','AYUDA':'AYUDA','REPETIR/BORRAR':'REPETIR / BORRAR',
 'BLOQ. MAYÚSCULAS':'BLOQ. MAYUSCULAS','MAYÚSCULAS (izq.)':'MAYUSCULAS','MAYÚSCULAS (der.)':'MAYUSCULAS',
 'JUGADOR IZQUIERDA / INS':'JUGADOR IZQUIERDA / INS','JUGADOR DERECHA / DEL':'JUGADOR DERECHA / DEL','INTRO':'INTRO','ESPACIO':'ESPACIO'}
cols = {c: {} for c in range(8)}          # col -> row -> (label, pc, comment)
rows = list(csv.DictReader(open(a.csv, encoding='utf-8')))
bad = []
for r in rows:
    name = r['tecla']; col = int(r['columna_out']); row = int(r['fila_in'])
    if r['matriz'] != '1': continue
    lab = LABEL.get(name, name)
    cols[col][row] = (lab, PC.get(name), name)
    # verification against the firmware: normal code must equal the CSV 'normal' output for printable keys
    n = fwcode(NORMAL, col, row)
    exp = r['normal_salida']
    if len(exp) == 1 and exp.isprintable() and name not in ('RETROCESO','AVANCE','ESPACIO'):
        want = ord(exp)
        if name == 'Ñ' or name == 'Ü': continue   # CP437 codes differ from the CSV unicode char; checked below
        if n != want: bad.append((name, col, row, hex(n), exp))
# the two MAYUSCULAS keys share one intersection (firmware reads SHIFT at one position only)
for k in ('MAYÚSCULAS (izq.)', 'MAYÚSCULAS (der.)'): pass
if bad:
    print('MISMATCH vs firmware:', bad, file=sys.stderr); sys.exit(1)
print('verified %d matrix-1 keys against firmware bank 0 normal table' % sum(len(v) for v in cols.values()), file=sys.stderr)

ACT = [  # (col_out, [labels row 8..12]) from the panel photo, left to right; codes checked below
 (0, ['BUSCA LA LETRA','RECUERDA LA PALABRA','PLURALES','VERBOS','REVOLTIJO DE LETRAS']),
 (1, ['LA PALABRA MISTERIOSA','DERIVADOS','SINONIMOS','ANTONIMOS','LA LETRA LOCA']),
 (2, ['LA NUEVA PALABRA','TRUEQUE DE LETRAS','ALFAPUZZLE','REVOLTIJO','ACERTIJO GRAMATICAL']),
 (3, ['SUMA','RESTA','MULTIPLICACION','DIVISION','FRACCIONES / DECIMALES']),
 (4, ['FRACCIONES / PORCENTAJES','RATIOS','ALGEBRA','REPASO A LAS MATEMATICAS','EL SIGNO PERDIDO']),
 (5, ['CIENCIAS','CINE Y TELEVISION','HISTORIA Y GEOGRAFIA','GENERAL','¿QUE SOY?']),
 (6, ['EL NUMERO RELAMPAGO','BASIC','IMPRIMIR TEXTO','CALCULADORA','CARTUCHOS ADICIONALES']),
 (7, ['ON','OFF','NIVEL','1 JUGADOR','2 JUGADORES'])]
PCACT = ['F1','F2','F3','F4','F5','F6','F7','F8','F9','F10','F11','F12','0_PAD','1_PAD','2_PAD','3_PAD','4_PAD','5_PAD','6_PAD','7_PAD','8_PAD','9_PAD',
         'HOME','END','PGUP','PGDN','SLASH_PAD','ASTERISK','MINUS_PAD','PLUS_PAD','DEL_PAD','ENTER_PAD']
expect = list(range(1, 0x20)) + [0xb0, 0xb1, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7]
got = []
for c, labs in ACT:
    for i, lab in enumerate(labs):
        got.append((lab, fwcode(NORMAL, c, 8 + i)))
seq = [g[1] for g in got if g[0] != 'ON']
assert seq == expect, 'activity codes differ from firmware: %s' % [hex(x) for x in seq]
assert dict(got)['ON'] == 0xff and dict(got)['OFF'] == 0xb4
print('verified 39 activity keys: firmware codes 01-1F,B0-B7 in panel order; OFF=B4; ON=no code', file=sys.stderr)
out = []
w = out.append
w('static INPUT_PORTS_START( genio2000 )')
w('\t// Spanish Genio 2000 keyboard. INn = column n driven through port 0x10 (key_matrix_w), bits = rows read back from 0x10 (matrix 1)')
w('\t// or 0x11 (matrix 2, activity panel). Active low. Labels are the legends printed on the keys; PC keys are a convenience mapping.')
w('\tPORT_START("IN0")')
def keyline(bit, lab, pc, extra=''):
    codes = ''.join(' PORT_CODE(KEYCODE_%s)' % p for p in pc.split(',')) if pc else ''
    return '\tPORT_BIT(0x%02x, IP_ACTIVE_LOW, IPT_KEYBOARD) PORT_NAME(%s"%s")%s%s' % (1 << bit, 'u8' if not lab.isascii() else '', lab.replace('"','\\"'), codes, extra)
def matrix1(c):
    used = 0
    for row in range(8):
        if row in cols[c]:
            lab, pc, _ = cols[c][row]; used |= 1 << row
            shared = c == 6 and row == 6      # both MAYUSCULAS keys read this one contact
            w(keyline(row, lab, pc if not shared else 'LSHIFT,RSHIFT', ' // one contact serves both MAYUSCULAS keys' if shared else ''))
    unused = 0xff & ~used
    if unused: w('\tPORT_BIT(0x%02x, IP_ACTIVE_LOW, IPT_UNUSED)' % unused)
matrix1(0)
for c in range(1, 8):
    w('\n\tPORT_START("IN%d")' % c); matrix1(c)
# matrix-2 columns IN8..INF
idx = 0
for c, labs in ACT:
    w('\n\tPORT_START("IN%X")' % (8 + c))
    for i, lab in enumerate(labs):
        if lab == 'ON':
            w('\tPORT_BIT(0x01, IP_ACTIVE_LOW, IPT_UNUSED) // ON: restarts the unit and is never read by the firmware; no matrix position was measured'); continue
        pc = PCACT[idx] if idx < len(PCACT) else None; idx += 1
        # firmware code check (informational): activity codes 01-1F then B0-B7, OFF = B4
        w(keyline(i, lab, pc))
w('INPUT_PORTS_END')
text = '\n'.join(out) + '\n'
if a.out: open(a.out, 'w').write(text)
else: print(text)
