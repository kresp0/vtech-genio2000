#!/usr/bin/env python3
"""Run the emulated Genio through many activities (one run each, parallel) with tests/lua/io_inventory.lua and merge the I/O port inventories.
Output: work/io_survey.txt (port, R/W, value, total count, first pc, runs).  Observation in EMULATION only."""
import os, sys, subprocess, tempfile, collections, concurrent.futures as cf
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS = ['', 'BASIC', 'IMPRIMIR TEXTO', 'CALCULADORA', 'CARTUCHOS ADICIONALES', 'SUMA', 'ALGEBRA', 'PLURALES', 'CIENCIAS', 'EL NUMERO RELAMPAGO', 'BUSCA LA LETRA', 'NIVEL', '1 JUGADOR', 'GENERAL', 'ALFAPUZZLE', 'OFF']
def one(k):
    d = tempfile.mkdtemp(prefix='ios_', dir=os.path.join(ROOT, 'work')); inv = d + '/inv.txt'
    scen = '21:press:%s;27:press:RESPUESTA;31:press:A;33:press:INTRO' % k if k else '25:snap'
    e = dict(os.environ, GENIO_STOP='36', GENIO_SCEN=scen, GENIO_LOG=inv, GENIO_BANKLOG=d + '/b.log')
    subprocess.run([os.path.join(ROOT, 'mame/genio'), 'genio2000', '-rompath', os.path.join(ROOT, 'roms_local'), '-homepath', d + '/h', '-cfg_directory', d + '/c', '-nvram_directory', d + '/n',
        '-snapshot_directory', d + '/s', '-video', 'none', '-sound', 'none', '-seconds_to_run', '50', '-nothrottle', '-skip_gameinfo', '-autoboot_script', os.path.join(ROOT, 'tests/lua/io_inventory.lua')],
        env=e, capture_output=True, timeout=600)
    return k, [l.split() for l in open(inv)]
tot = collections.OrderedDict()
with cf.ThreadPoolExecutor(12) as ex:
    for k, rows in ex.map(one, KEYS):
        for r in rows:
            key = (r[0], r[1], r[2]); c = int(r[3].split('=')[1]); pc = r[4].split('=')[1]
            t = tot.setdefault(key, [0, pc, set()]); t[0] += c; t[2].add(k or '(idle)')
with open(os.path.join(ROOT, 'work/io_survey.txt'), 'w') as f:
    for key in sorted(tot):
        n, pc, runs = tot[key]; f.write('%s %s %s count=%d first_pc=%s runs=%d\n' % (*key, n, pc, len(runs)))
print(open(os.path.join(ROOT, 'work/io_survey.txt')).read())
