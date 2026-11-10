#!/usr/bin/env python3
"""artwork_click_test.py <outdir>  – end-to-end GUI check of the photo artwork on a real X display (needs xdotool + ImageMagick `import`; it moves the mouse pointer for ~70 s).
Starts the dev-branch MAME with the artwork, clicks BASIC, OFF, ON and the CONTRASTE switch with the mouse and saves a window capture after each step."""
import subprocess, sys, time, os, re
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); out = sys.argv[1]; os.makedirs(out, exist_ok=True)
import xml.etree.ElementTree as ET
LAY = ET.parse(os.path.join(H, 'artwork/genio2000/default.lay'), parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))).getroot(); VIEW = LAY.find('view')
LAYW = float(VIEW.find("element[@ref='lid']/bounds").get('width'))                  # layout width in units
def centre(label=None, tag=None):
    """centre of the clickable item for the key legend `label` (the comment before it) or the input tag `tag`, in layout units"""
    kids = list(VIEW)
    for i, e in enumerate(kids):
        if e.tag == 'element' and e.get('inputtag') and ((tag and e.get('inputtag') == tag) or (label and i > 0 and kids[i - 1].tag is ET.Comment and kids[i - 1].text.strip() == label)):
            b = e.find('bounds'); return float(b.get('x')) + float(b.get('width')) / 2, float(b.get('y')) + float(b.get('height')) / 2
    raise KeyError(label or tag)
def info():
    """(window id, absolute x, y, width, height) of the MAME window, from xwininfo (None until it exists)"""
    t = subprocess.run(['xwininfo', '-root', '-tree'], capture_output=True, text=True).stdout
    for line in t.splitlines():
        if 'Genio 2000 (Spain) [genio2000]' in line:
            wid = line.split()[0]
            i = subprocess.run(['xwininfo', '-id', wid], capture_output=True, text=True).stdout
            g = lambda k: int(re.search(k + r':\s+(-?\d+)', i).group(1))
            return wid, g('Absolute upper-left X'), g('Absolute upper-left Y'), g('Width'), g('Height')
def click(w, x, y):
    wid, ax, ay, ww, wh = w; sc = ww / LAYW
    subprocess.run(['xdotool', 'mousemove', str(int(ax + x * sc)), str(int(ay + y * sc))]); time.sleep(0.3)
    subprocess.run(['xdotool', 'mousedown', '1']); time.sleep(0.6); subprocess.run(['xdotool', 'mouseup', '1'])
def grab(w, name):
    wid, ax, ay, ww, wh = w; subprocess.run(['import', '-window', 'root', '-crop', '%dx%d+%d+%d' % (ww, wh, ax, ay), '+repage', os.path.join(out, name)])
win = info
p = subprocess.Popen([os.path.join(H, 'mame/genio'), 'genio2000', '-rompath', os.path.join(H, 'roms_local'), '-artpath', os.path.join(H, 'artwork'), '-homepath', out + '/h',
    '-cfg_directory', out + '/cfg', '-nvram_directory', out + '/n', '-video', 'soft', '-window', '-nomax', '-sound', 'none', '-skip_gameinfo', '-seconds_to_run', '400'],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
try:
    for _ in range(40):
        w = win()
        if w: break
        time.sleep(0.5)
    time.sleep(3); w = win(); click(w, LAYW / 2, 60)                                   # a click on a non-interactive part of the lid dismisses the ROM warning screen
    time.sleep(16); w = win(); grab(w, '1_welcome.png')
    click(w, *centre('OFF')); time.sleep(9); w = win(); grab(w, '2_after_click_OFF.png')              # OFF: panel column 8, row 2
    click(w, *centre('ON')); time.sleep(18); w = win(); grab(w, '3_after_click_ON.png')              # ON: column 8, row 1 (hard reset: new window)
    click(w, *centre('BASIC')); time.sleep(30); w = win(); grab(w, '4_after_click_BASIC.png')           # BASIC: panel column 7, row 2
    click(w, *centre(tag='CONTRAST')); time.sleep(3); w = win(); grab(w, '5_after_click_CONTRASTE.png')
    click(w, *centre(tag='CONTRAST')); time.sleep(3); w = win(); grab(w, '6_after_click_CONTRASTE_again.png')
finally:
    p.terminate()
