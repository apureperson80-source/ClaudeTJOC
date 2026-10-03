"""Images generated with numpy and packed into the .blend file."""

import math

import bpy
import numpy as np


def _hex(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def _rot(X, Y, cx, cy, ang):
    c, s = math.cos(ang), math.sin(ang)
    dx, dy = X - cx, Y - cy
    return dx * c + dy * s, -dx * s + dy * c


def art_print_image(w=600, h=800):
    """Abstract botanical print in the style of the reference photo:
    pastel paper cut-outs behind a dark palm fan."""
    name = 'Art Print (generated)'
    img = bpy.data.images.get(name)
    if img is not None:
        return img
    ys, xs = np.mgrid[0:h, 0:w]
    X = xs / w
    Y = ys / h * (h / w)             # keep shapes round; Y up (Blender pixel order)
    rng = np.random.default_rng(7)

    paper = _hex('#f4efe6')
    canvas = np.ones((h, w, 3)) * paper
    grain = rng.normal(0, 0.012, (h, w, 1))
    canvas += grain

    def paint(mask, col, soft=0.004):
        a = np.clip(mask / soft, 0, 1)[..., None] if soft else mask[..., None]
        canvas[:] = canvas * (1 - a) + _hex(col) * a

    def blob(cx, cy, rx, ry, ang, ex, col, wobble=0.0, seed=0):
        u, v = _rot(X, Y, cx, cy, ang)
        th = np.arctan2(v / ry, u / rx)
        wob = 1 + wobble * np.sin(3 * th + seed) + wobble * 0.5 * np.sin(5 * th + 2 * seed)
        d = (np.abs(u / rx) ** ex + np.abs(v / ry) ** ex) ** (1 / ex)
        paint((wob - d) * min(rx, ry), col)

    H = h / w
    blob(0.34, H * 0.70, 0.22, 0.15, 0.35, 2.6, '#f2a96b', 0.06, 1)      # peach
    blob(0.70, H * 0.36, 0.20, 0.13, -0.45, 3.5, '#e9bf45', 0.05, 2)     # mustard
    blob(0.26, H * 0.30, 0.13, 0.07, 0.25, 4.0, '#f0b9b9', 0.04, 3)      # blush pink
    blob(0.78, H * 0.80, 0.07, 0.07, 0.0, 2.0, '#c9b9e6', 0.0, 0)        # lilac dot
    blob(0.60, H * 0.12, 0.10, 0.035, 0.1, 4.0, '#e7d3c0', 0.03, 4)      # sand strip

    # palm fan: leaflets radiating from a point, dark green with light midribs
    cx, cy = 0.50, H * 0.47
    dx, dy = X - cx, Y - cy
    r = np.sqrt(dx * dx + dy * dy)
    th = np.arctan2(dy, dx)
    n_leaf = 15
    for i in range(n_leaf):
        a = math.radians(10 + 160 * i / (n_leaf - 1))
        length = 0.30 + 0.06 * math.sin(i * 1.7)
        dth = np.angle(np.exp(1j * (th - a)))
        t = np.clip(r / length, 0, 1)
        width = 0.11 * np.sin(np.pi * t) ** 0.8 * (1 - 0.3 * t) + 0.004
        inside = (r > 0.035) & (r < length)
        paint(np.where(inside, width - np.abs(dth), -1.0), '#1d4a3a', soft=0.01)
        paint(np.where(inside & (r > 0.05), 0.006 - np.abs(dth), -1.0), '#4b7a5e', soft=0.004)
    # stem
    sx = np.abs(X - (0.50 + (cy - Y) * 0.06))
    paint(np.where(Y < cy, 0.006 - sx, -1.0), '#1d4a3a', soft=0.002)
    # fine ink squiggle
    sq = np.abs(Y - (H * 0.18 + 0.02 * np.sin(X * 28))) - 0.0025
    paint(np.where((X > 0.12) & (X < 0.45), -sq, -1.0), '#2c2c2c', soft=0.002)

    canvas = np.clip(canvas, 0, 1)
    # byte images store display (sRGB) values directly
    img = bpy.data.images.new(name, w, h, alpha=False, float_buffer=False)
    img.colorspace_settings.name = 'sRGB'
    rgba = np.concatenate([canvas, np.ones((h, w, 1))], axis=2).astype(np.float32)
    img.pixels.foreach_set(rgba.ravel())
    img.pack()
    return img
