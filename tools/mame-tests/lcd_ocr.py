#!/usr/bin/env python3
"""Read the 20x4 text from a MAME snapshot of genio2000 by exact matching of every 5x8 cell against the CGROM binary.
Usage: lcd_ocr.py snapshot.png [cgrom.bin]   -> prints 4 lines (unmatched cell = '?', blank = ' ')."""
import sys, numpy as np
from PIL import Image
def load_font(path):
    d = open(path, 'rb').read(); g = {}
    for c in range(0x20, 0x100):
        g[c] = np.array([[(d[c*16+r] >> (4-x)) & 1 for x in range(5)] for r in range(8)], dtype=np.uint8)
    return g
def cells(png):
    """-> array (4, 20, 8, 5) of lit dots.  Two screen formats: gl4000 120x36 (cell 6x9 dots: eight glyph rows then a gap) and genio2000 120x40 (cell 6x10:
    glyph rows 0-6, a blank row, the eighth glyph row, a gap; unlit dots are drawn in a faint third colour, so the threshold is the middle of the range)."""
    im = np.array(Image.open(png).convert('L')).astype(int)
    dark = (im < (im.min() + im.max()) / 2).astype(np.uint8)
    h = dark.shape[0]; out = np.zeros((4, 20, 8, 5), np.uint8)
    for r in range(4):
        for c in range(20):
            if h == 36:
                out[r, c] = dark[r*9:r*9+8, c*6:c*6+5]
            else:
                assert h == 40, dark.shape
                out[r, c, :7] = dark[r*10:r*10+7, c*6:c*6+5]; out[r, c, 7] = dark[r*10+8, c*6:c*6+5]
    return out
def ocr(png, cg):
    font = load_font(cg); dark = cells(png); lines = []
    for r in range(4):
        s = ''
        for c in range(20):
            cell = dark[r, c]
            m = [code for code, gl in font.items() if (gl == cell).all()]
            s += chr(m[0]) if m and 0x20 <= m[0] < 0x7f else ('?' if not m else '\x00')
            if m and m[0] >= 0x7f: s = s[:-1] + '{%02X}' % m[0]
        lines.append(s)
    return lines
if __name__ == '__main__':
    cg = sys.argv[2] if len(sys.argv) > 2 else __file__.replace('tests/lcd_ocr.py', 'data/cgrom/genio2000_cgrom_reconstructed.bin')
    print('\n'.join(ocr(sys.argv[1], cg)))
