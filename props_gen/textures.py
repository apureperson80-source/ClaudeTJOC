"""Images generated with numpy and packed into the .blend file.

Contains a tiny vector *stroke font* (capitals, digits, a little punctuation)
plus anti-aliased 2D primitives, used to paint printed graphics: snack
packaging, on-screen user interfaces and CCTV overlays. Canvases are float
RGB arrays in Blender's pixel order (row 0 at the bottom, y up).
"""

import math
import os
import tempfile

import bpy
import numpy as np

# ---------------------------------------------------------------------------
# Stroke font (cap height 6 units, baseline 0)
# ---------------------------------------------------------------------------


def _arc(cx, cy, rx, ry, a0, a1, n=None):
    n = n or max(4, int(abs(a1 - a0) / 12))
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]


def _dot(x, y):
    return [(x, y), (x, y + 0.01)]


def _glyphs():
    g = {}
    g['A'] = (4, [[(0, 0), (2, 6), (4, 0)], [(0.7, 2), (3.3, 2)]])
    g['B'] = (4.2, [[(0, 0), (0, 6), (2.5, 6)] + _arc(2.5, 4.5, 1.5, 1.5, 90, -90)[1:] + [(0, 3)],
                    [(0, 3), (2.7, 3)] + _arc(2.7, 1.5, 1.5, 1.5, 90, -90)[1:] + [(0, 0)]])
    g['C'] = (4.2, [_arc(2.15, 3, 2.15, 3, 48, 312)])
    g['D'] = (4.1, [[(0, 0), (0, 6), (1.6, 6)] + _arc(1.6, 3, 2.5, 3, 90, -90)[1:] + [(0, 0)]])
    g['E'] = (3.8, [[(3.8, 6), (0, 6), (0, 0), (3.8, 0)], [(0, 3), (3.1, 3)]])
    g['F'] = (3.7, [[(3.7, 6), (0, 6), (0, 0)], [(0, 3), (3.0, 3)]])
    g['G'] = (4.3, [_arc(2.15, 3, 2.15, 3, 48, 360) + [(2.5, 3)]])
    g['H'] = (4, [[(0, 0), (0, 6)], [(4, 0), (4, 6)], [(0, 3), (4, 3)]])
    g['I'] = (0, [[(0, 0), (0, 6)]])
    g['J'] = (3.1, [[(3.1, 6), (3.1, 1.6)] + _arc(1.55, 1.6, 1.55, 1.6, 0, -180)[1:]])
    g['K'] = (4, [[(0, 0), (0, 6)], [(3.9, 6), (0, 2.1)], [(1.45, 3.45), (4, 0)]])
    g['L'] = (3.6, [[(0, 6), (0, 0), (3.6, 0)]])
    g['M'] = (4.8, [[(0, 0), (0, 6), (2.4, 1.4), (4.8, 6), (4.8, 0)]])
    g['N'] = (4, [[(0, 0), (0, 6), (4, 0), (4, 6)]])
    g['O'] = (4.6, [_arc(2.3, 3, 2.3, 3, 0, 360, 36)])
    g['P'] = (4, [[(0, 0), (0, 6), (2.4, 6)] + _arc(2.4, 4.4, 1.6, 1.6, 90, -90)[1:] + [(0, 2.8)]])
    g['Q'] = (4.6, [_arc(2.3, 3, 2.3, 3, 0, 360, 36), [(2.8, 1.3), (4.6, -0.4)]])
    g['R'] = (4.1, [[(0, 0), (0, 6), (2.4, 6)] + _arc(2.4, 4.4, 1.6, 1.6, 90, -90)[1:] + [(0, 2.8)],
                    [(2.2, 2.8), (4.1, 0)]])
    g['S'] = (4, [_arc(2.0, 4.5, 1.9, 1.5, 15, 270)[:-1] + _arc(2.0, 1.5, 2.0, 1.5, 90, -165)])
    g['T'] = (4.2, [[(0, 6), (4.2, 6)], [(2.1, 6), (2.1, 0)]])
    g['U'] = (4, [[(0, 6), (0, 2)] + _arc(2, 2, 2, 2, 180, 360)[1:] + [(4, 6)]])
    g['V'] = (4.2, [[(0, 6), (2.1, 0), (4.2, 6)]])
    g['W'] = (5.4, [[(0, 6), (1.3, 0), (2.7, 4.6), (4.1, 0), (5.4, 6)]])
    g['X'] = (4, [[(0, 0), (4, 6)], [(0, 6), (4, 0)]])
    g['Y'] = (4.2, [[(0, 6), (2.1, 3), (4.2, 6)], [(2.1, 3), (2.1, 0)]])
    g['Z'] = (4, [[(0, 6), (4, 6), (0, 0), (4, 0)]])
    g['0'] = (3.6, [_arc(1.8, 3, 1.8, 3, 0, 360, 32)])
    g['1'] = (2.0, [[(0.0, 4.6), (1.5, 6), (1.5, 0)]])
    g['2'] = (3.8, [_arc(1.85, 4.15, 1.85, 1.85, 160, -35) + [(0, 0), (3.8, 0)]])
    g['3'] = (3.7, [_arc(1.8, 4.5, 1.7, 1.5, 155, -90)[:-1] + _arc(1.8, 1.55, 1.9, 1.45, 90, -155)])
    g['4'] = (4, [[(3.0, 0), (3.0, 6), (0, 1.8), (4, 1.8)]])
    g['5'] = (3.8, [[(3.6, 6), (0.5, 6), (0.3, 3.3)] + _arc(1.9, 1.95, 1.9, 1.95, 125, -150)])
    g['6'] = (3.9, [_arc(2.0, 3.0, 1.9, 3.0, 75, 180)[:-1] + [(0.02, 2.0)]
                    + _arc(1.95, 1.95, 1.93, 1.95, 180, 540, 32)])
    g['7'] = (3.8, [[(0, 6), (3.8, 6), (1.3, 0)]])
    g['8'] = (3.9, [_arc(1.95, 4.55, 1.6, 1.45, 0, 360, 28), _arc(1.95, 1.55, 1.95, 1.55, 0, 360, 28)])
    six = g['6'][1]
    g['9'] = (3.9, [[(3.9 - x, 6 - y) for (x, y) in s] for s in six])
    g['.'] = (0.2, [_dot(0.1, 0.1)])
    g[','] = (0.6, [[(0.5, 0.3), (0.1, -0.9)]])
    g[':'] = (0.2, [_dot(0.1, 0.2), _dot(0.1, 3.6)])
    g['-'] = (2.8, [[(0.2, 2.6), (2.6, 2.6)]])
    g['_'] = (3.6, [[(0, -0.6), (3.6, -0.6)]])
    g['+'] = (3.6, [[(0, 3), (3.6, 3)], [(1.8, 1.2), (1.8, 4.8)]])
    g['/'] = (3, [[(0, -0.4), (3, 6.4)]])
    g['$'] = (4, g['S'][1] + [[(2.0, 6.9), (2.0, -0.9)]])
    g['%'] = (4.4, [_arc(0.9, 4.9, 0.9, 1.1, 0, 360, 16), _arc(3.5, 1.1, 0.9, 1.1, 0, 360, 16),
                    [(0.2, 0), (4.2, 6)]])
    g['('] = (1.6, [_arc(3.4, 3, 3.2, 3.8, 128, 232)])
    g[')'] = (1.6, [[(1.6 - x + 0.0, y) for (x, y) in _arc(3.4, 3, 3.2, 3.8, 128, 232)]])
    g['!'] = (0.2, [[(0.1, 6), (0.1, 1.9)], _dot(0.1, 0.1)])
    g['?'] = (3.6, [_arc(1.8, 4.3, 1.8, 1.7, 155, -60) + [(1.8, 2.3), (1.8, 1.7)], _dot(1.8, 0.1)])
    g["'"] = (0.2, [[(0.1, 6), (0.1, 4.4)]])
    g['"'] = (1.4, [[(0.1, 6), (0.1, 4.4)], [(1.3, 6), (1.3, 4.4)]])
    g['#'] = (4, [[(1.2, 0), (1.7, 6)], [(2.6, 0), (3.1, 6)], [(0, 2), (4, 2)], [(0.2, 4), (4.2, 4)]])
    g['*'] = (3, [[(1.5, 2.6), (1.5, 6)], [(0, 5.1), (3, 3.5)], [(0, 3.5), (3, 5.1)]])
    g['<'] = (3, [[(3, 5), (0, 3), (3, 1)]])
    g['>'] = (3, [[(0, 5), (3, 3), (0, 1)]])
    g['='] = (3.4, [[(0, 2), (3.4, 2)], [(0, 4), (3.4, 4)]])
    g['|'] = (0.2, [[(0.1, -0.8), (0.1, 6.8)]])
    g['&'] = (4.4, [[(4.4, 0), (1.1, 4.1)] + _arc(1.9, 4.9, 1.1, 1.1, 225, -45)[1:]
                    + [(0.4, 1.9)] + _arc(1.7, 1.5, 1.4, 1.5, 160, 300)[1:] + [(4.0, 2.6)]])
    g[' '] = (2.2, [])
    return g


GLYPHS = _glyphs()


def text_width(text, size, weight=0.5, tracking=1.0):
    """Width in pixels of ``text`` at cap height ``size`` (pixels)."""
    u = size / 6.0
    w = 0.0
    for ch in text.upper():
        adv, _ = GLYPHS.get(ch, GLYPHS['?'])
        w += (adv + 1.3 * tracking + 2 * weight) * u
    return max(0.0, w - 1.3 * tracking * u)


def _seg_dist(px, py, segs):
    """Min distance from pixel centres (px, py arrays) to segments (S, 4)."""
    ax, ay, bx, by = segs[:, 0], segs[:, 1], segs[:, 2], segs[:, 3]
    dx, dy = bx - ax, by - ay
    ll = np.maximum(dx * dx + dy * dy, 1e-12)
    PX, PY = px[..., None], py[..., None]
    t = np.clip(((PX - ax) * dx + (PY - ay) * dy) / ll, 0.0, 1.0)
    qx, qy = ax + t * dx - PX, ay + t * dy - PY
    return np.sqrt(np.min(qx * qx + qy * qy, axis=-1))


# ---------------------------------------------------------------------------
# Canvas
# ---------------------------------------------------------------------------

def hexrgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def _col(c):
    return hexrgb(c) if isinstance(c, str) else np.asarray(c, dtype=float)[:3]


class Canvas:
    """Float RGB image with anti-aliased drawing helpers (pixel units, y up)."""

    def __init__(self, w, h, color='#ffffff'):
        self.w, self.h = w, h
        self.px = np.ones((h, w, 3)) * _col(color)

    # -- core -------------------------------------------------------------
    def _region(self, x0, y0, x1, y1):
        i0, i1 = max(0, int(math.floor(x0)) - 1), min(self.w, int(math.ceil(x1)) + 2)
        j0, j1 = max(0, int(math.floor(y0)) - 1), min(self.h, int(math.ceil(y1)) + 2)
        if i0 >= i1 or j0 >= j1:
            return None
        ys, xs = np.mgrid[j0:j1, i0:i1]
        return (slice(j0, j1), slice(i0, i1)), xs + 0.5, ys + 0.5

    def blend(self, sl, alpha, color):
        a = np.clip(alpha, 0.0, 1.0)[..., None]
        if isinstance(color, np.ndarray) and color.ndim == 3:
            col = color
        else:
            col = _col(color)
        self.px[sl] = self.px[sl] * (1 - a) + col * a

    def sdf_fill(self, bbox, sdf, color, opacity=1.0):
        """Fill where ``sdf(x, y) < 0`` (signed distance in pixels)."""
        reg = self._region(*bbox)
        if reg is None:
            return
        sl, X, Y = reg
        a = np.clip(0.5 - sdf(X, Y), 0.0, 1.0) * opacity
        if callable(color):
            color = color(X, Y)
        self.blend(sl, a, color)

    # -- shapes -----------------------------------------------------------
    def rect(self, x0, y0, x1, y1, color, r=0.0, opacity=1.0):
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        hx, hy = abs(x1 - x0) / 2, abs(y1 - y0) / 2
        r = min(r, hx, hy)

        def sdf(X, Y):
            qx = np.abs(X - cx) - hx + r
            qy = np.abs(Y - cy) - hy + r
            return (np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2)
                    + np.minimum(np.maximum(qx, qy), 0) - r)
        self.sdf_fill((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)), sdf, color, opacity)

    def frame(self, x0, y0, x1, y1, width, color, r=0.0):
        self.rect(x0, y0, x1, y0 + width, color)
        self.rect(x0, y1 - width, x1, y1, color)
        self.rect(x0, y0, x0 + width, y1, color)
        self.rect(x1 - width, y0, x1, y1, color)

    def ellipse(self, cx, cy, rx, ry, color, opacity=1.0, angle=0.0):
        c, s = math.cos(angle), math.sin(angle)

        def sdf(X, Y):
            u = (X - cx) * c + (Y - cy) * s
            v = -(X - cx) * s + (Y - cy) * c
            k = np.sqrt((u / rx) ** 2 + (v / ry) ** 2)
            return (k - 1.0) * min(rx, ry)
        rr = max(rx, ry)
        self.sdf_fill((cx - rr, cy - rr, cx + rr, cy + rr), sdf, color, opacity)

    def ring(self, cx, cy, r, width, color):
        def sdf(X, Y):
            return np.abs(np.hypot(X - cx, Y - cy) - r) - width / 2
        self.sdf_fill((cx - r - width, cy - r - width, cx + r + width, cy + r + width), sdf, color)

    def polygon(self, pts, color, opacity=1.0):
        """Convex polygon (any winding)."""
        P = np.asarray(pts, dtype=float)
        if _area(P) < 0:
            P = P[::-1]

        def sdf(X, Y):
            d = None
            for i in range(len(P)):
                a, b = P[i], P[(i + 1) % len(P)]
                e = b - a
                n = np.array([e[1], -e[0]]) / max(np.hypot(*e), 1e-9)   # outward
                di = (X - a[0]) * n[0] + (Y - a[1]) * n[1]
                d = di if d is None else np.maximum(d, di)
            return d
        self.sdf_fill((P[:, 0].min(), P[:, 1].min(), P[:, 0].max(), P[:, 1].max()), sdf,
                      color, opacity)

    def star(self, cx, cy, r0, r1, n, color, phase=0.0):
        def sdf(X, Y):
            th = np.arctan2(Y - cy, X - cx) + phase
            rr = r0 + (r1 - r0) * (0.5 + 0.5 * np.cos(n * th))
            return (np.hypot(X - cx, Y - cy) - rr) * 0.8
        self.sdf_fill((cx - r1, cy - r1, cx + r1, cy + r1), sdf, color)

    def line(self, x0, y0, x1, y1, width, color):
        segs = np.array([[x0, y0, x1, y1]], dtype=float)
        r = width / 2

        def sdf(X, Y):
            return _seg_dist(X, Y, segs) - r
        self.sdf_fill((min(x0, x1) - r, min(y0, y1) - r, max(x0, x1) + r, max(y0, y1) + r),
                      sdf, color)

    def polyline(self, pts, width, color):
        segs = np.array([[a[0], a[1], b[0], b[1]] for a, b in zip(pts, pts[1:])], dtype=float)
        r = width / 2
        P = np.asarray(pts)

        def sdf(X, Y):
            return _seg_dist(X, Y, segs) - r
        self.sdf_fill((P[:, 0].min() - r, P[:, 1].min() - r, P[:, 0].max() + r,
                       P[:, 1].max() + r), sdf, color)

    def vgradient(self, x0, y0, x1, y1, c0, c1):
        """Vertical gradient from c0 (bottom) to c1 (top)."""
        j0, j1 = max(0, int(y0)), min(self.h, int(math.ceil(y1)))
        i0, i1 = max(0, int(x0)), min(self.w, int(math.ceil(x1)))
        t = ((np.arange(j0, j1) + 0.5 - y0) / max(y1 - y0, 1e-9))[:, None, None]
        self.px[j0:j1, i0:i1] = _col(c0) * (1 - t) + _col(c1) * t

    def noise(self, amount, seed=0, region=None):
        rng = np.random.default_rng(seed)
        if region is None:
            self.px += rng.normal(0.0, amount, self.px.shape[:2])[..., None]
        else:
            x0, y0, x1, y1 = [int(v) for v in region]
            sub = self.px[y0:y1, x0:x1]
            sub += rng.normal(0.0, amount, sub.shape[:2])[..., None]

    # -- text -------------------------------------------------------------
    def text(self, s, x, y, size, color, weight=0.5, align='left', tracking=1.0, slant=0.0,
             outline=0.0, outline_color='#000000', xscale=1.0, max_width=None):
        """Draw ``s`` with its baseline at y. ``size`` = cap height in px,
        ``weight`` = stroke radius in font units (0.3 light .. 0.9 heavy).
        ``outline`` adds a border of that many font units in ``outline_color``
        (all outlines are drawn first, so they never cut into a letter)."""
        if max_width:
            w = text_width(s, size, weight, tracking) * xscale
            if w > max_width:
                xscale *= max_width / w
        u = size / 6.0
        width = text_width(s, size, weight, tracking) * xscale
        if align == 'center':
            x -= width / 2
        elif align == 'right':
            x -= width
        # lay the glyphs out once; both passes share these strokes
        pen = x + weight * u * xscale
        glyphs = []
        for ch in s.upper():
            adv, strokes = GLYPHS.get(ch, GLYPHS['?'])
            segs = []
            for st in strokes:
                pts = [(pen + (gx + gy * slant) * u * xscale, y + gy * u) for gx, gy in st]
                segs += [[a[0], a[1], b[0], b[1]] for a, b in zip(pts, pts[1:])]
            if segs:
                glyphs.append(np.array(segs))
            pen += (adv + 1.3 * tracking + 2 * weight) * u * xscale
        passes = ([((weight + outline) * u, outline_color)] if outline else []) + [(weight * u, color)]
        for r, col in passes:
            for S in glyphs:
                bx0, by0 = S[:, [0, 2]].min() - r, S[:, [1, 3]].min() - r
                bx1, by1 = S[:, [0, 2]].max() + r, S[:, [1, 3]].max() + r
                self.sdf_fill((bx0, by0, bx1, by1), lambda X, Y, S=S, r=r: _seg_dist(X, Y, S) - r, col)
        return width

    # -- output -----------------------------------------------------------
    def paste(self, other, x, y):
        h, w = other.px.shape[:2]
        self.px[y:y + h, x:x + w] = other.px

    def to_image(self, name, alpha=None):
        img = bpy.data.images.get(name)
        if img is not None and tuple(img.size) == (self.w, self.h):
            pass
        else:
            if img is not None:
                bpy.data.images.remove(img)
            img = bpy.data.images.new(name, self.w, self.h, alpha=alpha is not None)
        rgba = np.ones((self.h, self.w, 4), dtype=np.float32)
        rgba[..., :3] = np.clip(self.px, 0.0, 1.0)
        if alpha is not None:
            rgba[..., 3] = alpha
        img.pixels.foreach_set(rgba.ravel())
        img.pack()
        return img


def packed_image(name, px, quality=None):
    """Image datablock ``name`` holding ``px`` (float sRGB, y up), packed into
    the .blend. With ``quality`` it is stored as a JPEG, which keeps busy
    images (photos, CCTV footage, artwork with grain) small. An existing image
    of that name is replaced everywhere it is used."""
    h, w = px.shape[:2]
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :3] = np.clip(px, 0.0, 1.0)
    tmp = bpy.data.images.new('_packed_tmp', w, h)
    tmp.pixels.foreach_set(rgba.ravel())
    if quality is None:
        tmp.pack()
        img = tmp
    else:
        path = os.path.join(tempfile.mkdtemp(), 'image.jpg')
        tmp.filepath_raw = path
        tmp.file_format = 'JPEG'
        tmp.save(quality=quality)
        bpy.data.images.remove(tmp)
        img = bpy.data.images.load(path, check_existing=False)
        img.pack()
        os.remove(path)
        img.filepath_raw = '//textures/%s.jpg' % name.lower().replace(' ', '_')
    old = bpy.data.images.get(name)
    if old is not None and old != img:
        old.user_remap(img)
        bpy.data.images.remove(old)
    img.name = name
    return img


def _area(P):
    x, y = P[:, 0], P[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)


def load_png(path):
    """Read a PNG through Blender into a float RGB array (y up)."""
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    a = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)[..., :3].astype(float)


def save_png(px, path):
    h, w = px.shape[:2]
    img = bpy.data.images.new('_save', w, h)
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :3] = np.clip(px, 0.0, 1.0)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)


def resize(px, w, h):
    """Box-filtered downscale / bilinear resample of an RGB array."""
    H, W = px.shape[:2]
    if W % w == 0 and H % h == 0:
        fx, fy = W // w, H // h
        return px.reshape(h, fy, w, fx, 3).mean(axis=(1, 3))
    ys = (np.arange(h) + 0.5) * H / h - 0.5
    xs = (np.arange(w) + 0.5) * W / w - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, H - 1)
    x0 = np.clip(np.floor(xs).astype(int), 0, W - 1)
    y1, x1 = np.clip(y0 + 1, 0, H - 1), np.clip(x0 + 1, 0, W - 1)
    ty, tx = (ys - y0)[:, None, None], (xs - x0)[None, :, None]
    a = px[y0][:, x0] * (1 - tx) + px[y0][:, x1] * tx
    b = px[y1][:, x0] * (1 - tx) + px[y1][:, x1] * tx
    return a * (1 - ty) + b * ty
