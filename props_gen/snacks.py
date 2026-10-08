"""Snack products for the vending machines.

The packaging artwork is painted with numpy into one atlas image (made-up
brands, so the models stay free of real trademarks). Products are flow-wrap
"pillow" packs -- chip bags, candy bars and cookie packs -- built as UV-mapped
meshes; all products of a machine go into one object with one material.
"""

import math
import random

import numpy as np
from mathutils import Matrix, Vector

from .materials import image_material
from .textures import Canvas, packed_image

# ---------------------------------------------------------------------------
# Designs: (key, kind, base colour, accent, logo colour, brand, flavour, art)
# ---------------------------------------------------------------------------

BAGS = [
    ('crispo_blue', '#1f5fbf', '#f7c600', '#d81e25', 'CRISPO', 'CLASSIC', 'chips'),
    ('sunny_yellow', '#f4c20d', '#d71f26', '#ffffff', 'SUNNY', 'SALTED', 'chips'),
    ('nacho_red', '#c8102e', '#111111', '#ffffff', 'NACHO', 'CHEESE', 'tortilla'),
    ('cheezy_orange', '#f07d18', '#1d4aa8', '#ffffff', 'CHEEZY', 'PUFFS', 'puffs'),
    ('crispo_green', '#1f8a3a', '#f7c600', '#ffffff', 'CRISPO', 'SOUR CREAM', 'chips'),
    ('smoky_maroon', '#7a1420', '#f29a1b', '#ffe9b0', 'SMOKY', 'BBQ', 'chips'),
    ('kettle_black', '#18181a', '#c9a64b', '#18181a', 'KETTLE', 'SEA SALT', 'chips'),
    ('twists_navy', '#1b2a5a', '#e8b23a', '#ffffff', 'TWISTS', 'PRETZELS', 'pretzels'),
    ('popcorn_white', '#f4f1ea', '#d42a2a', '#ffffff', 'POP!', 'BUTTER', 'popcorn'),
    ('trail_kraft', '#a8773f', '#2f5d34', '#fff6dc', 'TRAIL', 'NUTS & FRUIT', 'nuts'),
    ('zing_cyan', '#18a7c9', '#ffffff', '#0b2e6b', 'ZING', 'SALT & VINEGAR', 'chips'),
    ('corn_gold', '#e9a400', '#8f1d14', '#ffd23a', 'CORNY', 'CORN CHIPS', 'tortilla'),
]

BARS = [
    ('bar_brown', '#5a3214', '#f4e1c0', '#ffffff', 'NUTTY'),
    ('bar_red', '#c4161c', '#ffffff', '#ffffff', 'CHOCO'),
    ('bar_blue', '#1b4fa0', '#ffd400', '#ffffff', 'CRUNCH'),
    ('bar_orange', '#ef7a1a', '#4a2511', '#4a2511', 'PEANUT'),
    ('bar_white', '#f2efe8', '#2c6fb5', '#2c6fb5', 'COCO'),
    ('bar_green', '#1d7d48', '#ffffff', '#ffffff', 'MINTY'),
    ('bar_purple', '#5b2a86', '#f5c400', '#f5c400', 'CARAMEL'),
    ('bar_black', '#202020', '#e23b2e', '#e23b2e', 'DARK'),
]

PACKS = [
    ('cookies_blue', '#1e56a8', '#ffffff', 'COOKIES', 'cookies'),
    ('cakes_yellow', '#f5cf1f', '#c2241e', 'CAKES', 'cakes'),
    ('wafer_pink', '#e7739e', '#ffffff', 'WAFERS', 'wafers'),
    ('crackers_orange', '#e86a1d', '#ffffff', 'CRACKERS', 'crackers'),
    ('mints_white', '#f3f5f7', '#1f8a5a', 'MINTS', 'mints'),
    ('gum_teal', '#13a3a0', '#ffffff', 'GUM', 'mints'),
]

KINDS = {
    'bag': [d[0] for d in BAGS],
    'bar': [d[0] for d in BARS],
    'pack': [d[0] for d in PACKS],
}

BAG_PX = (256, 384)
BAR_PX = (112, 416)
PACK_PX = (224, 288)


def _shade(c, k):
    c = np.array([int(c.lstrip('#')[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])
    return np.clip(c * k, 0, 1)


def _lum(c):
    r, g, b = _shade(c, 1.0)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _seals(cv, h, w, base, n=4):
    band = int(h * 0.075)
    for y0 in (0, h - band):
        cv.rect(0, y0, w, y0 + band, _shade(base, 0.82))
        for x in range(3, w, 7):
            cv.rect(x, y0, x + 2, y0 + band, _shade(base, 0.68))
    return band


def _art(cv, kind, cx, cy, s, rng):
    """Product illustration around (cx, cy) of size ~s px."""
    if kind == 'chips':
        for k in range(9):
            x = cx + rng.uniform(-0.9, 0.9) * s
            y = cy + rng.uniform(-0.45, 0.45) * s
            cv.ellipse(x, y, s * 0.42, s * 0.30, '#b8862c', angle=rng.uniform(0, 3))
            cv.ellipse(x - 2, y + 2, s * 0.39, s * 0.27, '#f2c45a', angle=rng.uniform(0, 3))
            cv.ellipse(x + s * 0.1, y, s * 0.05, s * 0.04, '#c58a2a')
    elif kind == 'tortilla':
        for k in range(7):
            x = cx + rng.uniform(-0.9, 0.9) * s
            y = cy + rng.uniform(-0.4, 0.4) * s
            a = rng.uniform(0, 6.28)
            pts = [(x + s * 0.5 * math.cos(a + i * 2.094), y + s * 0.5 * math.sin(a + i * 2.094))
                   for i in range(3)]
            cv.polygon(pts, '#c26a12')
            pts = [(px + (x - px) * 0.12, py + (y - py) * 0.12) for px, py in pts]
            cv.polygon(pts, '#f39a1e')
    elif kind == 'puffs':
        for k in range(14):
            x = cx + rng.uniform(-1.0, 1.0) * s
            y = cy + rng.uniform(-0.45, 0.45) * s
            cv.ellipse(x, y, s * 0.36, s * 0.16, '#d9620c', angle=rng.uniform(0, 3))
            cv.ellipse(x - 1, y + 2, s * 0.30, s * 0.11, '#ff9a2e', angle=rng.uniform(0, 3))
    elif kind == 'pretzels':
        for k in range(6):
            x = cx + rng.uniform(-0.8, 0.8) * s
            y = cy + rng.uniform(-0.35, 0.35) * s
            cv.ring(x - s * 0.18, y, s * 0.2, s * 0.09, '#7a3d12')
            cv.ring(x + s * 0.18, y, s * 0.2, s * 0.09, '#7a3d12')
            cv.ring(x, y - s * 0.12, s * 0.25, s * 0.09, '#8f4a18')
    elif kind == 'popcorn':
        for k in range(18):
            x = cx + rng.uniform(-1.0, 1.0) * s
            y = cy + rng.uniform(-0.5, 0.5) * s
            for j in range(3):
                cv.ellipse(x + rng.uniform(-6, 6), y + rng.uniform(-6, 6), s * 0.16, s * 0.14,
                           '#fff7d6' if j else '#f1d27a')
    elif kind == 'nuts':
        for k in range(12):
            x = cx + rng.uniform(-1.0, 1.0) * s
            y = cy + rng.uniform(-0.5, 0.5) * s
            cv.ellipse(x, y, s * 0.2, s * 0.13, rng.choice(['#8b5a2b', '#c08a4a', '#5e3a1a']),
                       angle=rng.uniform(0, 3))
    elif kind in ('cookies', 'cakes', 'crackers', 'wafers', 'mints'):
        cols = {'cookies': ('#9b6430', '#4a2a12'), 'cakes': ('#f3d9a0', '#ffffff'),
                'crackers': ('#e7a64b', '#b8732a'), 'wafers': ('#f0c98a', '#d9a35c'),
                'mints': ('#ffffff', '#cfeee0')}[kind]
        for k in range(3):
            x = cx + (k - 1) * s * 0.75
            y = cy + rng.uniform(-0.1, 0.1) * s
            if kind in ('wafers', 'crackers'):
                cv.rect(x - s * 0.33, y - s * 0.33, x + s * 0.33, y + s * 0.33, cols[0], r=3)
                for j in range(4):
                    cv.line(x - s * 0.3, y - s * 0.2 + j * s * 0.13, x + s * 0.3,
                            y - s * 0.2 + j * s * 0.13, 2, cols[1])
            else:
                cv.ellipse(x, y, s * 0.36, s * 0.36, cols[0])
                for j in range(5):
                    cv.ellipse(x + rng.uniform(-0.2, 0.2) * s, y + rng.uniform(-0.2, 0.2) * s,
                               s * 0.05, s * 0.04, cols[1])


def _paint_bag(spec, seed):
    key, base, accent, logo_col, brand, flavour, art = spec
    w, h = BAG_PX
    rng = random.Random(seed)
    cv = Canvas(w, h, base)
    cv.vgradient(0, 0, w, h, _shade(base, 0.78), _shade(base, 1.08))
    band = _seals(cv, h, w, base)
    # big product shot in the lower half
    _art(cv, art, w * 0.5, h * 0.33, w * 0.2, rng)
    # logo badge
    cy = h * 0.68
    cv.ellipse(w / 2, cy, w * 0.43, h * 0.13, '#ffffff')
    cv.ellipse(w / 2, cy, w * 0.40, h * 0.115, accent)
    cv.text(brand, w / 2, cy - h * 0.035, h * 0.07, logo_col, weight=0.95, align='center',
            outline=0.5 if logo_col == '#ffffff' else 0.0, outline_color=_shade(base, 0.5),
            max_width=w * 0.7, slant=0.12)
    # flavour ribbon
    fy = h * 0.52
    rib = accent if accent != base else '#ffffff'
    cv.polygon([(w * 0.08, fy - 14), (w * 0.92, fy - 10), (w * 0.92, fy + 12), (w * 0.08, fy + 16)], rib)
    # readable flavour text: white on dark ribbons, else the bag colour (or black)
    if _lum(rib) < 0.45:
        fcol = '#ffffff'
    else:
        fcol = base if _lum(base) < 0.45 else '#111111'
    cv.text(flavour, w / 2, fy - 7, 15, fcol, weight=0.6, align='center', max_width=w * 0.78)
    cv.text('NET WT 1 OZ (28g)', w * 0.06, band + 10, 9, '#ffffff' if base != '#f4f1ea' else '#333333',
            weight=0.4)
    cv.noise(0.012, seed)
    return cv


def _paint_bar(spec, seed):
    key, base, accent, text_col, brand = spec
    w, h = BAR_PX
    # painted landscape, then turned so the brand reads bottom-to-top
    cv = Canvas(h, w, base)
    cv.vgradient(0, 0, h, w, _shade(base, 0.85), _shade(base, 1.1))
    for x0 in (0, h - 30):
        cv.rect(x0, 0, x0 + 30, w, _shade(base, 0.8))
        for y in range(2, w, 6):
            cv.rect(x0, y, x0 + 30, y + 2, _shade(base, 0.66))
    cv.rect(40, w * 0.18, h - 40, w * 0.25, accent)
    cv.rect(40, w * 0.75, h - 40, w * 0.82, accent)
    cv.text(brand, h / 2, w * 0.33, w * 0.36, text_col, weight=1.0, align='center',
            max_width=h - 110, slant=0.1)
    cv.noise(0.01, seed)
    out = Canvas(w, h)
    out.px = np.rot90(cv.px, k=1).copy()
    return out


def _paint_pack(spec, seed):
    key, base, text_col, brand, art = spec
    w, h = PACK_PX
    rng = random.Random(seed)
    cv = Canvas(w, h, base)
    cv.vgradient(0, 0, w, h, _shade(base, 0.85), _shade(base, 1.06))
    _seals(cv, h, w, base)
    cv.rect(w * 0.1, h * 0.2, w * 0.9, h * 0.52, '#ffffff', r=16)
    cv.rect(w * 0.13, h * 0.23, w * 0.87, h * 0.49, _shade(base, 0.35) if base != '#f3f5f7'
            else '#cfe7da', r=12)
    _art(cv, art, w / 2, h * 0.36, w * 0.17, rng)
    cv.text(brand, w / 2, h * 0.62, h * 0.09, text_col, weight=0.9, align='center',
            max_width=w * 0.8)
    cv.text('6 PACK', w / 2, h * 0.11, 12, text_col, weight=0.5, align='center')
    cv.noise(0.01, seed)
    return cv


# ---------------------------------------------------------------------------
# Atlas
# ---------------------------------------------------------------------------

_ATLAS = {}


def snack_atlas():
    """Return (material, {design: (u0, v0, u1, v1)})."""
    if _ATLAS:
        return _ATLAS['mat'], _ATLAS['uv']
    W, H = 2048, 1536
    atlas = Canvas(W, H, '#808080')
    uv = {}
    x, y, row_h = 0, 0, 0
    items = ([(s[0], _paint_bag, s) for s in BAGS] + [(s[0], _paint_pack, s) for s in PACKS]
             + [(s[0], _paint_bar, s) for s in BARS])
    for k, (key, painter, spec) in enumerate(items):
        cv = painter(spec, 100 + k)
        if x + cv.w > W:
            x, y, row_h = 0, y + row_h, 0
        atlas.paste(cv, x, y)
        # half-pixel inset keeps neighbours from bleeding in
        uv[key] = ((x + 0.5) / W, (y + 0.5) / H, (x + cv.w - 0.5) / W, (y + cv.h - 0.5) / H)
        x += cv.w
        row_h = max(row_h, cv.h)
    img = packed_image('Snack Packaging (generated)', atlas.px, quality=92)
    m = image_material('Snack Packaging', img, rough=0.32, coat=0.5)
    _ATLAS['mat'], _ATLAS['uv'] = m, uv
    return m, uv


# ---------------------------------------------------------------------------
# Pack geometry
# ---------------------------------------------------------------------------

# kind: (width, height, depth, seal fraction, side exponent, puff exponent)
SHAPES = {
    'bag': (0.118, 0.205, 0.052, 0.075, 0.55, 0.45),
    'bag_small': (0.100, 0.165, 0.042, 0.075, 0.55, 0.45),
    'pack': (0.088, 0.125, 0.034, 0.075, 0.30, 0.25),
    'bar': (0.034, 0.140, 0.019, 0.075, 0.18, 0.15),
}


def pillow_pack(mb, kind, rect, matrix, rng, nu=8, nv=12):
    """Flow-wrapped pack standing on its bottom seal, front facing -Y,
    centred on x = y = 0. ``rect`` is its art in the atlas."""
    w, h, d, seal, ex, ep = SHAPES[kind]
    w *= rng.uniform(0.97, 1.03)
    h *= rng.uniform(0.98, 1.02)
    u0, v0, u1, v1 = rect
    wob = [rng.uniform(-1, 1) for _ in range(6)]
    m = Matrix(matrix)

    def surf(s, t, side):
        tt = (t - seal) / (1 - 2 * seal)
        if 0.0 < tt < 1.0:
            fill = math.sin(math.pi * tt) ** ep
        else:
            fill = 0.0
        puff = max(math.sin(math.pi * s), 0.0) ** ex * fill
        x = (s - 0.5) * w * (1.0 - 0.07 * fill)
        z = t * h
        # crimped seal edges
        if t <= 0.0 or t >= 1.0:
            z += 0.0015 * (1 if int(s * 24) % 2 else -1) * (1 if t >= 1.0 else -1)
        wrinkle = 0.0025 * fill * (wob[0] * math.sin(7 * s + wob[1]) * math.sin(5 * t + wob[2])
                                    + 0.5 * wob[3] * math.sin(13 * s * t + wob[4]))
        y = side * (0.0007 + (d / 2) * puff + wrinkle * puff)
        return m @ Vector((x, y, z))

    for side in (-1, 1):
        def uvf(s, t, side=side):
            ss = s if side < 0 else 1 - s
            return (u0 + (u1 - u0) * ss, v0 + (v1 - v0) * t)
        if side < 0:
            mb.grid(lambda s, t: surf(s, t, -1), nu, nv, uv=uvf)
        else:
            # reversed winding for the back
            mb.grid(lambda s, t: surf(1 - s, t, 1), nu, nv, uv=lambda s, t: uvf(1 - s, t))
    # thin closing strips round the edges (where the seals meet)
    edge_uv = [(u0, v0)] * 4
    for k in range(nv):
        t0, t1 = k / nv, (k + 1) / nv
        for s in (0.0, 1.0):
            a, b = surf(s, t0, -1), surf(s, t1, -1)
            c, e = surf(s, t1, 1), surf(s, t0, 1)
            q = [a, b, c, e] if s == 0.0 else [a, e, c, b]
            mb.quad(q, edge_uv)
    for k in range(nu):
        s0, s1 = k / nu, (k + 1) / nu
        for t in (0.0, 1.0):
            a, b = surf(s0, t, -1), surf(s1, t, -1)
            c, e = surf(s1, t, 1), surf(s0, t, 1)
            q = [a, e, c, b] if t == 0.0 else [a, b, c, e]
            mb.quad(q, edge_uv)


def design_rect(key):
    return snack_atlas()[1][key]
