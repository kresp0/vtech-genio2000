"""Helpers shared by tests and figure scripts: decode a MAME gl4000/genio2000 snapshot (120x36) into 4x20 cells of 8x5 bits,
and render the expected screen from a CGROM binary (+ optional CGRAM)."""
import numpy as np, cv2

def decode_snapshot(path):
    im = cv2.imread(path, cv2.IMREAD_COLOR).astype(int)
    h = im.shape[0]; assert im.shape[1] == 120 and h in (36, 40), im.shape          # gl4000 120x36 (cell 6x9) or genio2000 120x40 (cell 6x10, see lcd_ocr.py)
    lum = im.sum(2)
    mid = (lum.min() + lum.max()) / 2                  # unlit dots (third colour) and the background are above, lit dots below
    dark = lum < mid
    cells = np.zeros((4, 20, 8, 5), bool)
    for r in range(4):
        for c in range(20):
            if h == 36:
                cells[r, c] = dark[r*9:r*9+8, c*6:c*6+5]
            else:
                cells[r, c, :7] = dark[r*10:r*10+7, c*6:c*6+5]; cells[r, c, 7] = dark[r*10+8, c*6:c*6+5]
    return cells

def glyph_bits(cgrom, code):
    return np.array([[(cgrom[code*16 + y] >> (4 - x)) & 1 for x in range(5)] for y in range(8)], bool)

def expected_screen(cgrom, codes, cgram=None):
    cells = np.zeros((4, 20, 8, 5), bool)
    for k, code in enumerate(codes):
        r, c = divmod(k, 20)
        if code < 0x10:
            cells[r, c] = np.array([[(cgram[(code & 7)*8 + y] >> (4 - x)) & 1 for x in range(5)] for y in range(8)], bool)
        else:
            cells[r, c] = glyph_bits(cgrom, code)
    return cells

def page_codes(base):
    return [(base + k) if base + k < 0x100 else 0x20 for k in range(80)]

def to_image(cells, scale=6, on=(88, 83, 92), off=(148, 146, 138)):
    img = np.zeros((4*9*scale, 20*6*scale, 3), np.uint8); img[:] = off
    for r in range(4):
        for c in range(20):
            for y in range(8):
                for x in range(5):
                    if cells[r, c, y, x]:
                        y0, x0 = (r*9+y)*scale, (c*6+x)*scale
                        img[y0:y0+scale-1, x0:x0+scale-1] = on
    return img
