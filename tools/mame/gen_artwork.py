#!/usr/bin/env python3
"""gen_artwork.py [--debug]  (needs OpenCV)  – builds the photo-based MAME artwork for genio2000 in artwork/genio2000/ (default.lay, lid.png, base.png).
Sources are the owner's photographs (logs/hardware/photos_2026-11-09: LCD front view and keyboard/panel top view); nothing from the firmware is used.
Every key rectangle is bound to the MAME input field of that key: port IN<col> bit <row> for the 56 main keys (from data/teclado_es_source.csv, matrix 1) and
IN8..INF bits 0-4 for the 5 x 8 activity panel (matrix 2); clicking a rectangle holds that key down while the button is pressed.
--debug also writes work/artwork_debug_{lid,base}.png with the rectangles drawn on the photos."""
import csv, os, sys
import cv2, numpy as np
from PIL import Image, ImageDraw
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PH = os.path.join(H, 'logs/hardware/photos_2026-11-09'); OUT = os.environ.get('ARTOUT', os.path.join(H, 'artwork/genio2000'))
LID_SRC, BASE_SRC = 'I_lcd_front_READY_block_cursor.jpg', 'B_C_keyboard_and_activity_panel_topdown.jpg'
# Perspective correction: both photographs are slightly keystoned, so each is warped so that the printed blue panel (lid) / the body edges (base) become a rectangle.
LID_QUAD = [[351, 403], [1738, 405], [1698, 1153], [362, 1141]]                      # corners of the blue printed panel in the LID photo (found with OpenCV on the blue mask)
LID_OUT = dict(w=1387, h=743, ox=160, oy=120, below=340)                              # panel size in the rectified canvas, margins left/right, above, below (the lower bezel and the hinge are kept)
BASE_QUAD = [[66.5, 250], [1908, 250], [1865, 1400], [101.6, 1400]]                   # left/right body edges (line fits on the desk/body boundary) at y = 250 and 1400 in the BASE photo
BASE_OUT = dict(x0=90, y0=250, w=1841, h=1150, pad=250)
NSTRIP = int(os.environ.get("NSTRIP", 7))                                                                              # strips used to approximate the oval hit area of each activity button
MARGIN = 2                                                                             # background kept beyond the outermost plastic edge, in layout px
BASE_TOP, BASE_BOTTOM = 222, 1470                                                     # rows kept below the hinge down to the whole lower bezel (rectified canvas rows, minus the pad offsets below)
LCD = (787, 658, 1308, 895)                                                      # LCD glass in the LID photo (photo pixels)
SLIDER = (1578, 768, 1692, 818)                                                  # CONTRASTE slide switch (slot) in the LID photo (photo pixels)
LED = (1478, 787, 9)                                                             # caps LED in the LID photo: x, y, radius
# main keys: (x0, x1) per (photo row, position) in BASE photo pixels; row y-ranges below
ROWY = {1: (810, 915), 2: (925, 1035), 3: (1040, 1150), 4: (1155, 1260), 5: (1265, 1370)}
ROWX = {
 1: [(150,262),(268,378),(388,498),(505,617),(625,735),(743,853),(860,970),(978,1088),(1093,1203),(1207,1315),(1322,1430),(1440,1625),(1635,1822)],
 2: [(158,322),(330,440),(448,558),(568,678),(685,797),(803,912),(920,1030),(1038,1145),(1150,1258),(1265,1372),(1380,1488),(1493,1600),(1608,1820)],
 3: [(158,358),(362,472),(480,590),(598,708),(715,825),(832,942),(948,1058),(1063,1173),(1177,1285),(1292,1400),(1405,1510),(1518,1622),(1630,1818)],
 4: [(160,418),(423,533),(540,650),(658,768),(772,885),(890,1000),(1005,1112),(1118,1225),(1232,1338),(1347,1450),(1458,1562),(1570,1812)],
 5: [(160,508),(515,627),(632,1362),(1368,1475),(1480,1812)]}
PANELX = [(175,365),(392,580),(600,790),(810,995),(1018,1200),(1222,1405),(1428,1608),(1628,1810)]      # panel columns 0-7
PANELY_FIX = {(6, 0): (390, 447), (7, 1): (473, 533)}                                                      # columns that sit lower in the photo (the panel is slightly skewed)
PANELY = [(385,442),(458,517),(538,600),(613,677),(692,752)]                                              # panel rows 0-4 (matrix-2 row_in 8-12)

def warp(img, quad, size, dst):
    M = cv2.getPerspectiveTransform(np.float32(quad), np.float32(dst))
    return cv2.warpPerspective(img, M, size, flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE), M
def tp(M, x, y):
    v = M @ np.array([x, y, 1.0]); return v[0] / v[2], v[1] / v[2]
def trect(M, x0, y0, x1, y1, post=None):
    pts = [tp(M, x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    if post: pts = [(post(x, y), y) for x, y in pts]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)
def find_glass(img, gx, gy):
    """the LCD glass inside its blue frame on the rectified lid: (bbox x, y, w, h, 4 hull corners TL TR BR BL)"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    free = (~((hsv[..., 0] > 100) & (hsv[..., 0] < 135) & (hsv[..., 1] > 120) & (hsv[..., 2] < 170))).astype(np.uint8) * 255
    free = cv2.morphologyEx(free, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)); _, lab, st, _ = cv2.connectedComponentsWithStats(free)
    l = lab[int(gy), int(gx)]; cs, _ = cv2.findContours((lab == l).astype(np.uint8) * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hull = cv2.convexHull(max(cs, key=cv2.contourArea)); q = cv2.approxPolyDP(hull, 0.02 * cv2.arcLength(hull, True), True).reshape(-1, 2).astype(float)
    assert len(q) == 4, q
    q = q[np.argsort(q[:, 1])]; top = q[:2][np.argsort(q[:2, 0])]; bot = q[2:][np.argsort(q[2:, 0])]
    return st[l][:4], [top[0], top[1], bot[1], bot[0]]
def refine_panel_homography(img, L):
    """Second rectification pass. The four corners of the printed panel found on the first pass are only approximate (the printed 'window title bar' at the top was still
    sloping 16 px over the width and 8 px thicker on the right). The four sides are measured on the first-pass image - top: upper edge of the teal title bar; bottom: lower
    edge of the blue panel; left/right: first/last blue column - fitted with lines, and the corners are their intersections, mapped to the ideal rectangle."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV); H, W = img.shape[:2]
    teal = (hsv[..., 0] > 78) & (hsv[..., 0] < 100) & (hsv[..., 1] > 110) & (hsv[..., 2] > 90)
    blue = (hsv[..., 0] > 100) & (hsv[..., 0] < 135) & (hsv[..., 1] > 120) & (hsv[..., 2] < 170)
    xs = np.arange(300, 1400, 10); top = []; bot = []
    for x in xs:
        t = np.nonzero(teal[:300, x])[0]; b = np.nonzero(blue[700:960, x])[0]
        top.append(t[0] if len(t) else np.nan); bot.append(700 + b[-1] if len(b) else np.nan)
    ys = np.arange(300, 800, 10); lft = []; rgt = []
    for y in ys:
        l = np.nonzero(blue[y, :400])[0]; r = np.nonzero(blue[y, W - 400:])[0]
        lft.append(l[0] if len(l) else np.nan); rgt.append(W - 400 + r[-1] if len(r) else np.nan)
    def fit(a, b):
        a = np.array(a, float); b = np.array(b, float); ok = ~np.isnan(b); k = np.polyfit(a[ok], b[ok], 1)
        res = np.abs(b[ok] - np.polyval(k, a[ok])); ok2 = res < max(3.0, 2 * np.median(res)); a2, b2 = a[ok][ok2], b[ok][ok2]; return np.polyfit(a2, b2, 1)
    kt, kb = fit(xs, top), fit(xs, bot); kl, kr = fit(ys, lft), fit(ys, rgt)           # y = f(x) for top/bottom; x = f(y) for left/right
    def inter(kh, kv):                                                                   # horizontal-ish line y = kh0*x + kh1, vertical-ish x = kv0*y + kv1
        x = (kv[0] * kh[1] + kv[1]) / (1 - kv[0] * kh[0]); return x, kh[0] * x + kh[1]
    quad = [inter(kt, kl), inter(kt, kr), inter(kb, kr), inter(kb, kl)]
    dst = [[L['ox'], L['oy']], [L['ox'] + L['w'], L['oy']], [L['ox'] + L['w'], L['oy'] + L['h']], [L['ox'], L['oy'] + L['h']]]
    print('panel sides: title bar slope %.4f, bottom slope %.4f, left %.4f, right %.4f (dx/dy)' % (kt[0], kb[0], kl[0], kr[0]))
    return cv2.getPerspectiveTransform(np.float32(quad), np.float32(dst))
def level_top(img, panel_top, x_lo=250, x_hi=1500):
    """The raised plastic frame above the printed panel is photographed at a different depth than the panel, so after the panel correction its outer top edge and the
    inner lip line are still lower on the right (about 35 px). Per column the two edges are measured and the strip above the panel is remapped piecewise-linearly so that
    both become level at the values found on the left (the panel top row stays where it is)."""
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(float), (0, 0), 1.5); n = img.shape[1]
    o = np.full(n, np.nan); e = np.full(n, np.nan)
    for x in range(n):
        col = g[:panel_top, x]; wall = np.median(col[2:10])
        i = np.nonzero(col[10:] < wall - 30)[0]
        if len(i): o[x] = 10 + i[0]
        if len(i):
            j = np.nonzero(col[int(o[x]) + 20:] < 140)[0]
            if len(j): e[x] = int(o[x]) + 20 + j[0]
    def smooth(a):
        a = a.copy(); ok = ~np.isnan(a); idx = np.arange(n); a[~ok] = np.interp(idx[~ok], idx[ok], a[ok])
        a = cv2.medianBlur(a.astype(np.float32).reshape(1, -1), 1).ravel() if False else a
        k = np.ones(31) / 31; a = np.convolve(np.pad(a, 15, mode='edge'), k, mode='valid')
        a[:x_lo] = a[x_lo]; a[x_hi:] = a[x_hi - 1]; return a                           # rounded corners: keep the value of the straight part
    o, e = smooth(o), smooth(e)
    o0, e0 = np.median(o[x_lo:x_lo + 200]), np.median(e[x_lo:x_lo + 200])
    ydst = np.arange(panel_top, dtype=np.float32); mapy = np.tile(np.arange(img.shape[0], dtype=np.float32).reshape(-1, 1), (1, n))
    for x in range(n):
        mapy[:panel_top, x] = np.interp(ydst, [0, o0, e0, panel_top], [0, o[x], e[x], panel_top])
    mapx = np.tile(np.arange(n, dtype=np.float32), (img.shape[0], 1))
    return cv2.remap(img, mapx, mapy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE), (o0, e0, float(o[x_hi - 1]), float(e[x_hi - 1]))
def find_panel_buttons(base):
    """the 40 pill-shaped activity buttons found on the rectified base photo (lavender fill + the ON/OFF pills): list of 8 columns x 5 rows of (x, y, w, h)"""
    hsv = cv2.cvtColor(base[:520], cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] > 110) & (hsv[..., 0] < 140) & (hsv[..., 1] > 12) & (hsv[..., 1] < 100) & (hsv[..., 2] > 170)).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)); cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    bxs = [cv2.boundingRect(c) for c in cs if cv2.contourArea(c) > 3000]
    bxs = [r for r in bxs if r[3] < 80 and r[2] < 260]                             # drops the header band
    assert len(bxs) == 40, len(bxs)
    cols = []; last = None
    for r in sorted(bxs, key=lambda r: r[0]):                                       # columns = groups of buttons whose left edges are within 60 px of each other
        if last is None or r[0] - last > 60: cols.append([])
        cols[-1].append(r); last = r[0]
    assert len(cols) == 8, len(cols)
    assert all(len(c) == 5 for c in cols), [len(c) for c in cols]
    return [sorted(c, key=lambda r: r[1]) for c in cols]
def refine_base_homography(img):
    """Second rectification pass for the keyboard photo, from the printed activity panel: the header band (JUEGOS DE PALABRAS ...) still sloped 21 px over the width. The top edge
    of the teal header band, the bottom and the two side edges of the blue panel are measured and fitted with lines; the corners are their intersections, mapped to a rectangle
    of the same mean size and centre."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    teal = (hsv[..., 0] > 78) & (hsv[..., 0] < 100) & (hsv[..., 1] > 110) & (hsv[..., 2] > 90)
    blue = (hsv[..., 0] > 100) & (hsv[..., 0] < 135) & (hsv[..., 1] > 120) & (hsv[..., 2] < 170)
    xs = np.arange(200, 1700, 10); top = []; bot = []
    for x in xs:
        t = np.nonzero(teal[250:420, x])[0]; b = np.nonzero(blue[620:780, x])[0]
        top.append(250 + t[0] if len(t) else np.nan); bot.append(620 + b[-1] if len(b) else np.nan)
    ys = np.arange(330, 700, 10); lft = []; rgt = []
    for y in ys:
        l = np.nonzero(blue[y, :450])[0]; r = np.nonzero(blue[y, img.shape[1] - 450:])[0]
        lft.append(l[0] if len(l) else np.nan); rgt.append(img.shape[1] - 450 + r[-1] if len(r) else np.nan)
    def fit(a, b):
        a = np.array(a, float); b = np.array(b, float); ok = ~np.isnan(b); k = np.polyfit(a[ok], b[ok], 1)
        res = np.abs(b[ok] - np.polyval(k, a[ok])); ok2 = res < max(3.0, 2 * np.median(res)); return np.polyfit(a[ok][ok2], b[ok][ok2], 1)
    kt, kb, kl, kr = fit(xs, top), fit(xs, bot), fit(ys, lft), fit(ys, rgt)
    def inter(kh, kv):
        x = (kv[0] * kh[1] + kv[1]) / (1 - kv[0] * kh[0]); return x, kh[0] * x + kh[1]
    q = [inter(kt, kl), inter(kt, kr), inter(kb, kr), inter(kb, kl)]
    cx = sum(p[0] for p in q) / 4; cy = sum(p[1] for p in q) / 4; w = (q[1][0] - q[0][0] + q[2][0] - q[3][0]) / 2; h = (q[3][1] - q[0][1] + q[2][1] - q[1][1]) / 2
    dst = [[cx - w / 2, cy - h / 2], [cx + w / 2, cy - h / 2], [cx + w / 2, cy + h / 2], [cx - w / 2, cy + h / 2]]
    print('keyboard photo panel sides: header slope %.4f, bottom %.4f, left %.4f, right %.4f' % (kt[0], kb[0], kl[0], kr[0]))
    return cv2.getPerspectiveTransform(np.float32(q), np.float32(dst))
def refine_key(gray, x0, y0, x1, y1, win=16):
    """snap a hand-placed key rectangle (x0, y0, x1, y1 in base-crop pixels) to the dark gaps around the keycap: each side moves to the darkest line within +-win px of its
    estimate in the mean luminance profile taken along the middle half of the opposite dimension"""
    h, w = gray.shape; x0, y0, x1, y1 = [int(round(v)) for v in (x0, y0, x1, y1)]
    def side(profile, est, lo_lim, hi_lim):
        a, b = max(lo_lim, est - win), min(hi_lim, est + win); return a + int(np.argmin(profile[a:b + 1]))
    ym0, ym1 = y0 + (y1 - y0) // 4, y1 - (y1 - y0) // 4; xm0, xm1 = x0 + (x1 - x0) // 4, x1 - (x1 - x0) // 4
    colp = cv2.GaussianBlur(gray[ym0:ym1].mean(0).reshape(1, -1).astype(np.float32), (0, 0), 1.5).ravel()
    rowp = cv2.GaussianBlur(gray[:, xm0:xm1].mean(1).reshape(1, -1).astype(np.float32), (0, 0), 1.5).ravel()
    return side(colp, x0, 0, w - 1), side(rowp, y0, 0, h - 1), side(colp, x1, 0, w - 1), side(rowp, y1, 0, h - 1)
def edge(g, row, lo, hi, falling):
    r = cv2.GaussianBlur(g[row - 4:row + 5].mean(0).reshape(1, -1), (0, 0), 3).ravel(); d = np.diff(r)[lo:hi]
    return lo + int(np.argmin(d) if falling else np.argmax(d))

def main(debug):
    lid_o = cv2.imread(os.path.join(PH, LID_SRC)); base_o = cv2.imread(os.path.join(PH, BASE_SRC))
    lid_p = lid_o.copy(); lx, ly, lr = LED; cv2.circle(lid_p, (lx, ly), lr, (30, 30, 120), -1, cv2.LINE_AA)   # caps LED painted unlit in the static photo (BGR)
    L = LID_OUT; dstl = [[L['ox'], L['oy']], [L['ox'] + L['w'], L['oy']], [L['ox'] + L['w'], L['oy'] + L['h']], [L['ox'], L['oy'] + L['h']]]
    lsz = (L['w'] + 2 * L['ox'], L['oy'] + L['h'] + L['below'])
    lidw, Ml = warp(lid_p, LID_QUAD, lsz, dstl); lidw_orig, _ = warp(lid_o, LID_QUAD, lsz, dstl)
    H2 = refine_panel_homography(lidw, L)
    lidw = cv2.warpPerspective(lidw, H2, lsz, flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE); lidw_orig = cv2.warpPerspective(lidw_orig, H2, lsz, flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE); Ml = H2 @ Ml
    lidw, topinfo = level_top(lidw, L['oy']); lidw_orig, _ = level_top(lidw_orig, L['oy'])
    print('top frame edges leveled: left outer/lip %.0f/%.0f, right (before) outer/lip %.0f/%.0f' % (topinfo[0], topinfo[1], topinfo[2], topinfo[3]))
    # the LCD bezel stands out of the panel, so it is slightly rotated/keystoned relative to the panel: straighten the glass (the right side was lower than the left)
    gx0, gy0 = tp(Ml, 1050, 780); _, gq = find_glass(lidw, gx0, gy0)
    x0g, x1g = (gq[0][0] + gq[3][0]) / 2, (gq[1][0] + gq[2][0]) / 2; y0g, y1g = (gq[0][1] + gq[1][1]) / 2 - (gq[1][1] - gq[0][1]) / 2, (gq[2][1] + gq[3][1]) / 2
    y0g = gq[0][1]                                                                                  # keep the left-hand top: the right side is stretched up to it
    Hg = cv2.getPerspectiveTransform(np.float32(gq), np.float32([[x0g, y0g], [x1g, y0g], [x1g, y1g], [x0g, y1g]]))
    sw = cv2.warpPerspective(lidw, Hg, (lidw.shape[1], lidw.shape[0]), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    al = np.zeros(lidw.shape[:2], np.float32); al[int(y0g) - 80:int(y1g) + 80, int(x0g) - 130:int(x1g) + 130] = 1; al = cv2.GaussianBlur(al, (0, 0), 14)[..., None]
    lidw = (lidw * (1 - al) + sw * al).astype(np.uint8)
    g = cv2.cvtColor(lidw, cv2.COLOR_BGR2GRAY).astype(float)
    xl, xr = edge(g, 700, 20, 120, True), edge(g, 700, lsz[0] - 140, lsz[0] - 20, False)    # outer edges of the lid frame (wall -> frame, frame -> wall)
    # the lid photo was not taken exactly on the axis: the hinge (the centre of the unit) sat ~14 px right of the middle of the frame. Stretch the left and right halves so that the
    # hinge centre goes to the middle of the frame (frame edges unchanged) and the lid's axis coincides with the keyboard's.
    hy = lsz[1] - 75; hrow = cv2.GaussianBlur(g[hy - 3:hy + 4].mean(0).reshape(1, -1), (0, 0), 2).ravel(); c0 = lsz[0] // 2
    dark = hrow < 130; a_, b_ = c0, c0
    while a_ > 0 and dark[a_ - 1]: a_ -= 1
    while b_ < len(dark) - 1 and dark[b_ + 1]: b_ += 1
    hc, fc = (a_ + b_) / 2, (xl + xr) / 2
    XM_SRC, XM_DST = [0, xl, hc, xr, lsz[0]], [0, xl, fc, xr, lsz[0]]                         # piecewise-linear x remap (source -> destination)
    xmap = lambda x: float(np.interp(x, XM_SRC, XM_DST))
    mapx = np.tile(np.interp(np.arange(lsz[0], dtype=np.float32), XM_DST, XM_SRC).astype(np.float32), (lsz[1], 1)); mapy = np.tile(np.arange(lsz[1], dtype=np.float32).reshape(-1, 1), (1, lsz[0]))
    lidw = cv2.remap(lidw, mapx, mapy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE); lidw_orig = cv2.remap(lidw_orig, mapx, mapy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    print('hinge %d..%d centre %.0f, frame centre %.0f: left/right halves stretched by %.3f / %.3f' % (a_, b_, hc, fc, (fc - xl) / (hc - xl), (xr - fc) / (xr - hc)))
    # Common silhouette: both photographs show the body of the unit with the SAME width at the joint (body edges at the same x, margin MARGIN of background on each side, so all the
    # plastic edges are visible: left/right/bottom of the keyboard and top/left/right of the lid, including the pink hinge switches that stick out of the lid sides).
    BD = BASE_OUT; tl_b, tr_b = BD['x0'], BD['x0'] + BD['w']; s = (tr_b - tl_b) / (xr - xl); mlid = MARGIN / s
    # the pink hinge switches stick out of the frame: the lid crop must reach their outer ends (found on the rectified lid), the top is the outer edge of the frame
    hl = cv2.cvtColor(lidw, cv2.COLOR_BGR2HSV); pk = ((hl[..., 0] > 150) | (hl[..., 0] < 8)) & (hl[..., 1] > 110) & (hl[..., 2] > 120); pk[:, xl + 40:xr - 40] = False; pk[400:] = False
    pcols = np.nonzero(pk.sum(0) >= 3)[0]; pmin, pmax = (int(pcols.min()), int(pcols.max())) if len(pcols) else (xl, xr)
    lid_x0 = int(round(min(xl, pmin) - MARGIN / s)); lid_x1 = int(round(max(xr, pmax) + MARGIN / s)); lid_y0 = max(0, int(topinfo[0]) - 2); lid_y1 = lsz[1] - 7
    print('lid: frame edges %d..%d, pink switches reach %d..%d, crop %d..%d, top %d' % (xl, xr, pmin, pmax, lid_x0, lid_x1, lid_y0))
    lidc = lidw[lid_y0:lid_y1, lid_x0:lid_x1]
    B = BASE_OUT; dstb = [[B['x0'], B['y0']], [B['x0'] + B['w'], B['y0']], [B['x0'] + B['w'], B['y0'] + B['h']], [B['x0'] + (BASE_QUAD[3][0] - BASE_QUAD[0][0]) * 0, B['y0'] + B['h']]]
    dstb[3][0] = B['x0']
    basew, Mb = warp(base_o, BASE_QUAD, (B['x0'] + B['w'] + 120, 1560), dstb)
    H2b = refine_base_homography(basew); basew = cv2.warpPerspective(basew, H2b, (basew.shape[1], basew.shape[0]), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE); Mb = H2b @ Mb
    bx0, bx1, by0 = tl_b - MARGIN, tr_b + MARGIN, BASE_TOP; by1 = BASE_BOTTOM
    # Fit the body to the lid: the outer left/right edges of the body (measured on rows of the keyboard area) are mapped, with a row-dependent horizontal scale, onto the edges
    # of the lid crop, so that the two photographs have the same silhouette at the joint and the whole base is not skewed relative to the lid.
    gb = cv2.GaussianBlur(cv2.cvtColor(basew, cv2.COLOR_BGR2GRAY).astype(float), (0, 0), 2)
    rows = np.arange(by0 + 30, by1 - 90, 20); el = []; er = []
    for y in rows:
        r = gb[y]; el.append(tl_b - 60 + int(np.argmin(np.diff(r[tl_b - 60:tl_b + 60])))); er.append(tr_b - 60 + int(np.argmax(np.diff(r[tr_b - 60:tr_b + 60]))))
    kl2 = np.polyfit(rows, el, 1); kr2 = np.polyfit(rows, er, 1); tl, tr = tl_b, tr_b                          # target edges (the lid crop has its frame edges at 4 px from its sides)
    bmapx = lambda x, y: tl + (x - np.polyval(kl2, y)) * (tr - tl) / (np.polyval(kr2, y) - np.polyval(kl2, y))
    yy, xx = np.mgrid[0:basew.shape[0], 0:basew.shape[1]].astype(np.float32)
    srcx = (np.polyval(kl2, yy) + (xx - tl) * (np.polyval(kr2, yy) - np.polyval(kl2, yy)) / (tr - tl)).astype(np.float32)
    basew = cv2.remap(basew, srcx, yy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    print('body edges fitted to the lid: left slope %.4f right slope %.4f px/px, widths %.0f..%.0f -> %d' % (kl2[0], kr2[0], np.polyval(kr2, rows[0]) - np.polyval(kl2, rows[0]), np.polyval(kr2, rows[-1]) - np.polyval(kl2, rows[-1]), tr - tl))
    hb = cv2.cvtColor(basew, cv2.COLOR_BGR2HSV); woodm = ((hb[..., 0] > 5) & (hb[..., 0] < 30) & (hb[..., 1] > 70) & (hb[..., 2] > 90))[:, tl_b + 300:tr_b - 300].mean(1)   # desk wood
    cand = [y for y in range(by0 + 1000, basew.shape[0] - 2) if woodm[y] > 0.8]; by1 = (cand[0] + MARGIN) if cand else by1
    basec = basew[by0:by1, bx0:bx1]
    W = round((lid_x1 - lid_x0) * s); Wb = basec.shape[1]                                  # the lid defines the width of the view; the narrower keyboard photo is centred under it
    OXb = (xl - lid_x0) * s - MARGIN                                                          # layout x of the keyboard photo (its body edge sits under the lid's frame edge)
    lidc = cv2.resize(lidc, (W, round(lidc.shape[0] * s)), interpolation=cv2.INTER_CUBIC)
    LH, BH = lidc.shape[0], basec.shape[0]
    OXb = float(OXb)
    os.makedirs(OUT, exist_ok=True)
    cv2.imwrite(os.path.join(OUT, 'lid.png'), lidc); cv2.imwrite(os.path.join(OUT, 'base.png'), basec)
    ltr = lambda x, y: ((xmap(tp(Ml, x, y)[0]) - lid_x0) * s, (tp(Ml, x, y)[1] - lid_y0) * s)            # LID photo px -> layout units
    def lrect(x0, y0, x1, y1):
        a = trect(Ml, x0, y0, x1, y1); a = (xmap(a[0]), a[1], xmap(a[2]), a[3]); return ((a[0] - lid_x0) * s, (a[1] - lid_y0) * s, (a[2] - a[0]) * s, (a[3] - a[1]) * s)
    SLB = lrect(*SLIDER)
    # LCD glass: the region inside the blue frame around the LCD (found on the rectified photo), painted with the colour of the unlit LCD; the dot matrix is inset
    # so that all four sides keep a margin of that colour and the photo's own light bevel line at the bottom of the glass is covered
    gx, gy = tp(Ml, 1050, 780); (bx_, by_, bw_, bh_), _q = find_glass(lidw, xmap(gx), gy)
    GL = ((bx_ - lid_x0 + 1) * s, (by_ - lid_y0 + 1) * s, (bw_ - 2) * s, (bh_ - 2) * s)           # glass, layout units
    MG = 3.0                                                                                       # margin in dots on every side
    dw, dh = GL[2] / (120 + 2 * MG), GL[3] / (40 + 2 * MG)
    LCDB = (GL[0] + MG * dw, GL[1] + MG * dh, 120 * dw, 40 * dh)
    cx, cy = ltr(lx, ly); r14 = round(14 * s)
    # lit caps LED overlay (output led_caps), cut from the unpainted photo
    ow = lidw_orig[lid_y0:lid_y1, lid_x0:lid_x1]; ow = cv2.resize(ow, (W, LH), interpolation=cv2.INTER_CUBIC)
    led = ow[round(cy) - r14:round(cy) + r14, round(cx) - r14:round(cx) + r14]; msk = np.zeros(led.shape[:2], np.uint8); cv2.circle(msk, (r14, r14), r14 - 3, 255, -1, cv2.LINE_AA)
    cv2.imwrite(os.path.join(OUT, 'led_on.png'), np.dstack([led, cv2.GaussianBlur(msk, (0, 0), 1.5)]))
    LEDB = (cx - r14, cy - r14, 2 * r14, 2 * r14)
    # right-hand contrast slider position: made from the photo of the LEFT position (no second photograph is used). The inner oval of the switch (the slot opening: handle plus the
    # empty recess, i.e. everything that changes when the switch moves) is selected and flipped horizontally; the cream border and the blue around it are not touched.
    cx0, cy0, cw, ch = [int(round(v)) for v in SLB]; sl = lidc[cy0:cy0 + ch, cx0:cx0 + cw].copy(); hh, ww = sl.shape[:2]
    hsv = cv2.cvtColor(sl, cv2.COLOR_BGR2HSV); mid = hh // 2
    creamm = (hsv[..., 2] > 150) & (hsv[..., 1] < 70); bluem = (hsv[..., 0] > 100) & (hsv[..., 0] < 135) & (hsv[..., 1] > 120) & (hsv[..., 2] < 170)
    opening = (~(creamm | bluem)).astype(np.uint8); opening = cv2.morphologyEx(opening, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(opening); opening = lab == lab[mid, ww // 2]                                  # the component that holds the centre of the slot
    # the oval that is flipped reaches into the middle of the cream ring around the slot, so it includes the bevel and the shadow of the opening and the cut lies in the
    # smooth cream, where it cannot be seen
    ring_n, ring_lab, ring_st, _ = cv2.connectedComponentsWithStats(creamm.astype(np.uint8)); ring = ring_lab == (1 + int(np.argmax(ring_st[1:, 4])))
    mid = float(cv2.distanceTransform(ring.astype(np.uint8), cv2.DIST_L2, 3).max())                                                  # half the thickness of the ring
    dist_open = cv2.distanceTransform((~opening).astype(np.uint8), cv2.DIST_L2, 3)
    region = opening | (ring & (dist_open <= mid))
    cols = np.nonzero(region.any(0))[0]; xo0, xo1 = int(cols.min()), int(cols.max())
    flip = sl.copy(); flip[:, xo0:xo1 + 1] = sl[:, xo0:xo1 + 1][:, ::-1]
    mflip = np.zeros_like(region); mflip[:, xo0:xo1 + 1] = region[:, xo0:xo1 + 1][:, ::-1]
    invalid = region & ~mflip                                                                                                        # target pixels whose mirror falls outside the oval
    flip = cv2.inpaint(flip, cv2.dilate(invalid.astype(np.uint8), np.ones((3, 3), np.uint8)) * 255, 3, cv2.INPAINT_TELEA)
    alpha = cv2.GaussianBlur(region.astype(np.float32), (5, 5), 0)[..., None]
    out = (sl * (1 - alpha) + flip * alpha).astype(np.uint8)
    cv2.imwrite(os.path.join(OUT, 'slider_right.png'), out)
    h0, h1, xr = xo0, xo1, xo1
    print('slider: oval (opening + half the cream ring, %.1f px) columns %d..%d flipped' % (mid, xo0, xo1))
    # faint grid between the LCD dots (120 x 40 dots: four lines of 10 rows), drawn over the emulated screen: the real glass shows the dot pitch
    gr = np.zeros((40 * 8, 120 * 8, 4), np.uint8); gr[..., :3] = (148, 146, 138)
    for i in range(0, 120 * 8, 8): gr[:, i, 3] = 120
    for j in range(0, 40 * 8, 8): gr[j, :, 3] = 120
    cv2.imwrite(os.path.join(OUT, 'lcdgrid.png'), gr)
    # keys and panel buttons (rectangles placed on the BASE photo, transformed with the same homography)
    INSET = 3
    PANEL = find_panel_buttons(basec)
    def bx(x0, x1, y0, y1):
        a = trect(Mb, x0, y0, x1, y1); return (OXb + a[0] - bx0 + INSET, LH + a[1] - by0 + INSET, a[2] - a[0] - 2 * INSET, a[3] - a[1] - 2 * INSET)
    items = []; keys = {}
    for r in csv.DictReader(open(os.path.join(H, 'data/teclado_es_source.csv'), encoding='utf-8')):
        if r['matriz'] == '1':
            keys[(int(r['fila_foto']), int(r['pos_en_fila']))] = (r['tecla'], 'IN%X' % int(r['columna_out']), 1 << int(r['fila_in']))
        elif r['matriz'] == '2':
            col, row = int(r['columna_out']), int(r['fila_in']) - 8
            px, py, pw, ph = PANEL[col][row]; M2 = 3                                      # detected pill (the teal ring around it adds a few px)
            tag, mask = ('POWER', 1) if r['tecla'] == 'ON' else ('IN%X' % (8 + col), 1 << row)                                # ON: separate power contact, not a matrix cell (dev branch)
            # A layout item can only be a rectangle, so the oval (pill) of the button is approximated by NSTRIP horizontal strips, each as wide as the pill at that height; all of them
            # are bound to the same input, and the middle strip comes first so that a script aiming at the centre of the first strip hits the button.
            bxl, byt, bwi, bhe = OXb + px - M2, LH + py - M2, pw + 2 * M2, ph + 2 * M2; rad = bhe / 2.0; cxm, cym = bxl + bwi / 2.0, byt + bhe / 2.0; strips = []
            for k in range(NSTRIP):
                y0s, y1s = byt + k * bhe / NSTRIP, byt + (k + 1) * bhe / NSTRIP; dy = max(abs(y0s - cym), abs(y1s - cym))                    # the farther edge of the strip decides its width
                hw = (bwi / 2.0 - rad) + (max(rad * rad - dy * dy, 0.0) ** 0.5) - 1.0
                strips.append((r['tecla'], tag, mask, cxm - hw, y0s, 2 * hw, y1s - y0s))
            mid = NSTRIP // 2; items += [strips[mid]] + strips[:mid] + strips[mid + 1:]
    gray = cv2.cvtColor(basec, cv2.COLOR_BGR2GRAY).astype(np.float32); shifts = []
    for (row, pos), (name, tag, mask) in sorted(keys.items()):
        x0, x1 = ROWX[row][pos - 1]; y0, y1 = ROWY[row]; a = trect(Mb, x0, y0, x1, y1, bmapx)
        e = (a[0] - bx0, a[1] - by0, a[2] - bx0, a[3] - by0); r = refine_key(gray, *e); shifts.append(max(abs(r[i] - e[i]) for i in range(4)))
        items.append((name, tag, mask, OXb + r[0] + INSET, LH + r[1] + INSET, r[2] - r[0] - 2 * INSET, r[3] - r[1] - 2 * INSET))
    print('keys: rectangles snapped to the keycap gaps, max move %d px, mean %.1f px' % (max(shifts), sum(shifts) / len(shifts)))
    assert len(items) == 56 + 40 * NSTRIP, len(items)   # 13+13+13+12+5 main keys, 5 x 8 panel buttons (incl. ON), NSTRIP strips each
    out = ['<?xml version="1.0"?>', '<!-- Genio 2000 (Spain): photo front panel with a clickable keyboard and activity panel. Generated by tools/gen_artwork.py from the owner\'s photographs. -->',
           '<mamelayout version="2">', ' <element name="lid"><image file="lid.png" /></element>', ' <element name="base"><image file="base.png" /></element>',
           ' <element name="grid"><image file="lcdgrid.png" /></element>',
           ' <element name="glass"><rect state="0"><color red="%.4f" green="%.4f" blue="%.4f" /></rect><rect state="1"><color red="%.4f" green="%.4f" blue="%.4f" /></rect></element>' % (138 / 255, 146 / 255, 148 / 255, 118 / 255, 125 / 255, 127 / 255),
           ' <element name="led"><image file="led_on.png" state="1" /></element>', ' <element name="slider"><image file="slider_right.png" state="1" /></element>',
           ' <element name="hit"><rect state="1"><color red="1.0" green="0.8" blue="0.0" alpha="0.45" /></rect></element>', ' <view name="Photo (clickable)">',
           '  <element ref="lid"><bounds x="0" y="0" width="%d" height="%d" /></element>' % (W, LH),
           '  <element ref="glass" name="lcd_dark"><bounds x="%.1f" y="%.1f" width="%.1f" height="%.1f" /></element>' % GL,
           '  <screen index="0"><bounds x="%.1f" y="%.1f" width="%.1f" height="%.1f" /></screen>' % LCDB,
           '  <element ref="grid"><bounds x="%.1f" y="%.1f" width="%.1f" height="%.1f" /></element>' % LCDB,
           '  <element ref="led" name="led_caps"><bounds x="%.1f" y="%.1f" width="%.1f" height="%.1f" /></element>' % LEDB,
           '  <element ref="slider" inputtag="CONTRAST" inputmask="0x01"><bounds x="%.1f" y="%.1f" width="%.1f" height="%.1f" /></element>' % SLB,
           '  <element ref="base"><bounds x="%.1f" y="%d" width="%d" height="%d" /></element>' % (OXb, LH, Wb, BH)]
    for name, tag, mask, x, y, w, h in items:
        out.append('  <!-- %s -->' % name.replace('--', '- -'))
        out.append('  <element ref="hit" inputtag="%s" inputmask="0x%02X"><bounds x="%d" y="%d" width="%d" height="%d" /></element>' % (tag, mask, x, y, w, h))
    out += [' </view>', '</mamelayout>']
    open(os.path.join(OUT, 'default.lay'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    if debug:
        os.makedirs(os.path.join(H, 'work'), exist_ok=True)
        dl = lidc.copy(); x, y, w, h = LCDB; cv2.rectangle(dl, (int(x), int(y)), (int(x + w), int(y + h)), (0, 0, 255), 3); x, y, w, h = GL; cv2.rectangle(dl, (int(x), int(y)), (int(x + w), int(y + h)), (255, 255, 0), 2); x, y, w, h = SLB; cv2.rectangle(dl, (int(x), int(y)), (int(x + w), int(y + h)), (0, 255, 0), 2)
        x, y, w, h = LEDB; cv2.rectangle(dl, (int(x), int(y)), (int(x + w), int(y + h)), (255, 0, 0), 2); cv2.imwrite(os.path.join(H, 'work/artwork_debug_lid.png'), dl)
        db = basec.copy()
        for name, tag, mask, x, y, w, h in items: cv2.rectangle(db, (int(x - OXb), int(y - LH)), (int(x - OXb + w), int(y - LH + h)), (0, 0, 255), 2)
        cv2.imwrite(os.path.join(H, 'work/artwork_debug_base.png'), db)
    print('wrote %s (%d clickable items = 56 keys + 40 oval buttons x %d strips, view %dx%d)' % (OUT, len(items), NSTRIP, W, LH + BH))
main('--debug' in sys.argv)
