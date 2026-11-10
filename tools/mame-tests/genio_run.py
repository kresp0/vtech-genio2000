"""Helpers: run genio2000 headless with a scripted scenario, return OCR text of every snapshot."""
import os, subprocess, tempfile, glob, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tests'))
import lcd_ocr
MAME = os.environ.get('GENIO_MAME', os.path.join(ROOT, 'mame', 'genio'))
ROMS = os.environ.get('GENIO_ROMPATH', os.path.join(ROOT, 'roms_local'))
CG = os.path.join(ROOT, 'data', 'cgrom', 'genio2000_cgrom_reconstructed.bin')
def run(scen, seconds=20, machine='genio2000', extra=(), env=None, snapdir=None, hold=0.4, lua=None):
    work = snapdir or tempfile.mkdtemp(prefix='genio_', dir=os.path.join(ROOT, 'work'))
    e = dict(os.environ, GENIO_SCEN=scen, GENIO_HOLD=str(hold)); e.update(env or {})
    cmd = [MAME, machine, '-rompath', ROMS, '-homepath', work + '/home', '-cfg_directory', work + '/cfg', '-nvram_directory', work + '/nvram',
           '-snapshot_directory', work + '/snap', '-video', 'none', '-sound', 'none', '-seconds_to_run', str(seconds), '-nothrottle',
           '-skip_gameinfo', '-snapview', 'native', '-artpath', os.path.join(ROOT, 'work', 'noart'), '-autoboot_script', lua or os.path.join(ROOT, 'tests/lua/scenario.lua')] + list(extra)
    p = subprocess.run(cmd, env=e, capture_output=True, text=True, timeout=600)
    shots = sorted(glob.glob(work + '/snap/*/*.png'))
    return [lcd_ocr.ocr(s, CG) for s in shots], p, work
