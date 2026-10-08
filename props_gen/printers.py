"""Printers (reference photo 5): a compact two-tone mono laser printer with its
manual feed tray folded open, and a wide A3+ ink-tank photo printer printing
the landscape photo. Brands are made up.

Origin at the centre of the footprint on the desk, front facing -Y.
"""

import math

import bpy
from mathutils import Matrix, Vector

from bathroom_gen.geo import group, ring_xy, rounded_rect
from .materials import image_material
from .mesh import Builder, Parts, add_text, front_frame

LASER_BRAND = 'NOVA'
INKJET_BRAND = 'PRISMA'


def _rr(w, d, r, cx=0.0, cy=0.0, seg=5):
    return rounded_rect(w, d, max(r, 0.0004), seg, (cx, cy))


def _slab(mb, w, d, z0, z1, r, rb=0.0, rt=0.0, cx=0.0, cy=0.0, seg=3):
    """Rounded-rect slab with optional bottom/top edge fillets."""
    rings = []
    for k in range(seg + 1):
        if rb <= 0 and k:
            break
        a = math.pi / 2 * k / seg
        inset = rb * (1 - math.sin(a)) if rb else 0.0
        rings.append(ring_xy(_rr(w - 2 * inset, d - 2 * inset, max(r - inset, 0.0004), cx, cy),
                             z0 + (rb * (1 - math.cos(a)) if rb else 0.0)))
    top = []
    for k in range(seg + 1):
        if rt <= 0 and k:
            break
        a = math.pi / 2 * k / seg
        inset = rt * (1 - math.cos(a)) if rt else 0.0
        top.append(ring_xy(_rr(w - 2 * inset, d - 2 * inset, max(r - inset, 0.0004), cx, cy),
                           z1 - rt + (rt * math.sin(a) if rt else rt)))
    mb.loft(rings + top, cap_start=True, cap_end=True)


def _feet(P, pts, h=0.006, r=0.009):
    feet = P('Feet', 'rubber_black', 'AUTO')
    for (x, y) in pts:
        feet.revolve([(0.0, 0.0), (r, 0.0), (r, h), (0.0, h)], 12, center=(x, y, 0.0))


# ---------------------------------------------------------------------------
# Compact mono laser printer
# ---------------------------------------------------------------------------

def printer_laser(name='Laser printer (compact)'):
    W, D, H = 0.331, 0.215, 0.178
    zs = 0.112                 # colour split: black lower body / light grey top
    with group(name) as root:
        P = Parts('Laser printer')
        lower = P('Lower body', 'plastic_black_gloss', 'HARD')
        _slab(lower, W, D, 0.006, zs, 0.014, rb=0.004)
        # light grey top cover with the output bay sunk into it
        top = P('Top cover', 'plastic_light_grey', 'HARD')
        bay_w, bay_d, bay_cx, bay_cy = 0.238, 0.142, -0.022, 0.012
        outline = lambda inset, z: ring_xy(_rr(W - 2 * inset, D - 2 * inset, 0.014 - inset * 0.5), z)
        bay = lambda z, grow=0.0: ring_xy(_rr(bay_w + grow, bay_d + grow, 0.012 + grow / 2, bay_cx, bay_cy), z)
        rings = [outline(0.0, zs), outline(0.0, H - 0.016)]
        for k in range(1, 5):
            a = math.pi / 2 * k / 4
            rings.append(outline(0.016 * (1 - math.cos(a)), H - 0.016 + 0.016 * math.sin(a)))
        rings += [bay(H, 0.012), bay(H - 0.002)]
        top.loft(rings)
        # dark output bay: walls and a floor sloping down to the exit slot at the back
        well = P('Output bay', 'plastic_black_satin', 'HARD')
        floor = []
        for p in _rr(bay_w, bay_d, 0.012, bay_cx, bay_cy):
            t = (p.y - (bay_cy - bay_d / 2)) / bay_d
            floor.append(Vector((p.x, p.y, H - 0.018 - 0.016 * t)))
        well.loft([bay(H - 0.002), floor])
        well.polygon(floor)
        # paper exit slot with rollers at the back of the bay
        slot = P('Paper exit', 'rubber_black', 'FLAT')
        ys = bay_cy + bay_d / 2 - 0.004
        slot.quad([Vector((bay_cx - 0.1, ys, H - 0.034)), Vector((bay_cx + 0.1, ys, H - 0.034)),
                   Vector((bay_cx + 0.1, ys, H - 0.024)), Vector((bay_cx - 0.1, ys, H - 0.024))])
        rollers = P('Exit rollers', 'plastic_mid_grey', 'SMOOTH')
        for k in range(4):
            x = bay_cx - 0.075 + k * 0.05
            rollers.revolve([(0.0, -0.008), (0.005, -0.008), (0.005, 0.008), (0.0, 0.008)], 12, axis='X',
                            center=(x, ys - 0.003, H - 0.029))
        # ribs on the bay floor that the paper slides on
        ribs = P('Bay ribs', 'plastic_black_matte', 'FLAT')
        for k in range(7):
            x = bay_cx - 0.09 + k * 0.03
            y0, y1 = bay_cy - bay_d / 2 + 0.012, bay_cy + bay_d / 2 - 0.012
            z0 = H - 0.018 - 0.016 * 0.08
            z1 = H - 0.018 - 0.016 * 0.92
            ribs.quad([Vector((x - 0.0015, y0, z0 + 0.0015)), Vector((x + 0.0015, y0, z0 + 0.0015)),
                       Vector((x + 0.0015, y1, z1 + 0.0015)), Vector((x - 0.0015, y1, z1 + 0.0015))])
        # control panel strip on the top right
        panel = P('Control panel', 'plastic_silver_grey', 'HARD')
        px = W / 2 - 0.032
        panel.rounded_box((0.03, 0.12, 0.004), 0.004, (px, 0.0, H - 0.0005), seg=2, zseg=1)
        btn = P('Buttons', 'plastic_mid_grey', 'AUTO')
        for y in (-0.03, 0.015):
            btn.revolve([(0.0, 0.0), (0.0075, 0.0), (0.0075, 0.003), (0.006, 0.0042), (0.0, 0.0042)], 18,
                        center=(px, y, H + 0.0015))
        led = P('Status LEDs', 'led_green', 'FLAT')
        for y in (0.04, 0.05):
            led.quad([Vector((px - 0.004, y - 0.002, H + 0.0016)), Vector((px + 0.004, y - 0.002, H + 0.0016)),
                      Vector((px + 0.004, y + 0.002, H + 0.0016)), Vector((px - 0.004, y + 0.002, H + 0.0016))])
        # front: logo on the black band, manual feed opening
        ink = P('Logo', 'print_white', 'FLAT')
        add_text(ink, LASER_BRAND, front_frame((0.0, -D / 2 - 0.0003, 0.085), '-Y'), size=0.016, spacing=1.25)
        mouth = P('Feed opening', 'rubber_black', 'FLAT')
        mouth.quad([Vector((-0.125, -D / 2 - 0.0004, 0.026)), Vector((0.125, -D / 2 - 0.0004, 0.026)),
                    Vector((0.125, -D / 2 - 0.0004, 0.058)), Vector((-0.125, -D / 2 - 0.0004, 0.058))])
        # vent slots on the right side
        vents = P('Vents', 'rubber_black', 'FLAT')
        for k in range(9):
            y = -0.06 + k * 0.015
            vents.quad([Vector((W / 2 + 0.0003, y, 0.03)), Vector((W / 2 + 0.0003, y + 0.006, 0.03)),
                        Vector((W / 2 + 0.0003, y + 0.006, 0.075)), Vector((W / 2 + 0.0003, y, 0.075))])
        _laser_tray(P, D)
        _feet(P, [(sx * (W / 2 - 0.03), sy * (D / 2 - 0.03)) for sx in (-1, 1) for sy in (-1, 1)])
        P.build()
    return root


def _laser_tray(P, D):
    """Manual feed tray folded down in front, with paper and guides."""
    hinge = Vector((0.0, -D / 2 + 0.004, 0.034))
    ang = math.radians(9)                  # slopes down towards the front
    L, w = 0.19, 0.25
    m = Matrix.Translation(hinge) @ Matrix.Rotation(ang, 4, 'X')
    sub = Parts('_')
    tray = sub('Feed tray', 'plastic_charcoal', 'HARD')
    tray.rounded_box((w, L, 0.006), 0.002, (0.0, -L / 2, -0.003), seg=2, zseg=1)
    for sx in (-1, 1):                     # side rails
        tray.rounded_box((0.006, L - 0.01, 0.012), 0.002, (sx * (w / 2 - 0.003), -L / 2, 0.003), seg=2, zseg=1)
    ext = sub('Tray extension', 'plastic_light_grey', 'HARD')
    ext.rounded_box((w * 0.8, 0.07, 0.005), 0.002, (0.0, -L - 0.03, -0.0035), seg=2, zseg=1)
    # finger tab / paper stop at the front
    ext.rounded_box((0.05, 0.012, 0.016), 0.003, (0.0, -L - 0.058, 0.004), seg=2, zseg=2)
    paper = sub('Paper', 'paper', 'FLAT')
    pw, pl, pt = 0.2159, 0.23, 0.003
    paper.box((-pw / 2, -pl + 0.03, 0.0), (pw / 2, 0.03, pt))
    guides = sub('Paper guides', 'plastic_light_grey', 'HARD')
    for sx in (-1, 1):
        x = sx * (pw / 2 + 0.003)
        guides.rounded_box((0.005, 0.06, 0.016), 0.0015, (x, -0.07, 0.007), seg=2, zseg=1)
    for (pname, pm), mb in sub.items.items():
        P(pname, pm, sub.shading.get(pname)).merge(mb, m)


# ---------------------------------------------------------------------------
# Wide ink-tank photo printer
# ---------------------------------------------------------------------------

INKS = [('ink_black', 0.80), ('ink_cyan', 0.62), ('ink_magenta', 0.55), ('ink_yellow', 0.70),
        ('ink_red', 0.45), ('ink_grey', 0.66)]


def printer_inktank(name='Photo printer (ink tank, A3+)', photo=True):
    W, D, H = 0.705, 0.322, 0.150
    with group(name) as root:
        P = Parts('Photo printer')
        body = P('Body', 'plastic_charcoal', 'HARD')
        _slab(body, W, D, 0.006, H, 0.02, rb=0.004, rt=0.006)
        lid = P('Top cover', 'plastic_black_satin', 'HARD')
        _slab(lid, W - 0.012, D - 0.03, H - 0.002, H + 0.012, 0.016, rt=0.008, cy=0.009)
        # raised rear paper-feed cover
        rear = P('Rear feeder cover', 'plastic_charcoal', 'HARD')
        rm = Matrix.Translation((0.0, D / 2 - 0.045, H + 0.012)) @ Matrix.Rotation(math.radians(-14), 4, 'X')
        rb = Builder()
        rb.rounded_box((W * 0.66, 0.07, 0.008), 0.003, (0.0, 0.0, 0.004), seg=2, zseg=1)
        rear.merge(rb, rm)
        logo = P('Logo', 'print_white', 'FLAT')
        add_text(logo, INKJET_BRAND, front_frame((0.0, -D / 2 + 0.05, H + 0.0122), '+Z'), size=0.019,
                 spacing=1.15)
        # front: output slot and the pulled-out tray
        dark = P('Output slot', 'rubber_black', 'FLAT')
        sx0, sx1 = -0.245, 0.16
        dark.quad([Vector((sx0, -D / 2 - 0.0004, 0.052)), Vector((sx1, -D / 2 - 0.0004, 0.052)),
                   Vector((sx1, -D / 2 - 0.0004, 0.082)), Vector((sx0, -D / 2 - 0.0004, 0.082))])
        tray = P('Output tray', 'plastic_dark_grey', 'HARD')
        tw = 0.37
        tcx = (sx0 + sx1) / 2
        for k, (y0, y1, z) in enumerate(((-D / 2 + 0.02, -D / 2 - 0.10, 0.058),
                                         (-D / 2 - 0.10, -D / 2 - 0.19, 0.0545),
                                         (-D / 2 - 0.19, -D / 2 - 0.27, 0.051))):
            ww = tw - 0.02 * k
            tray.rounded_box((ww, y0 - y1, 0.005), 0.002, (tcx, (y0 + y1) / 2, z), seg=2, zseg=1)
        tray.rounded_box((0.2, 0.006, 0.03), 0.002, (tcx, -D / 2 - 0.268, 0.066), seg=2, zseg=1)  # stopper
        if photo:
            _photo(P, tcx, D)
        # control buttons on the front left
        btn = P('Buttons', 'plastic_black_matte', 'AUTO')
        lights = P('Button lights', 'led_white', 'FLAT')
        for k, x in enumerate((-0.322, -0.300, -0.282, -0.264)):
            r = 0.0065 if k == 0 else 0.0048
            btn.revolve([(0.0, 0.0), (r, 0.0), (r, 0.003), (r * 0.8, 0.004), (0.0, 0.004)], 18, axis='Y',
                        center=(x, -D / 2, 0.128))
            if k == 0:              # power button: lit ring
                lights.revolve([(r * 0.45, 0.0042), (r * 0.6, 0.0042)], 18, axis='Y', center=(x, -D / 2, 0.128))
            else:                   # status dot
                y = -D / 2 - 0.0042
                lights.quad([Vector((x - 0.0015, y, 0.1265)), Vector((x + 0.0015, y, 0.1265)),
                             Vector((x + 0.0015, y, 0.1295)), Vector((x - 0.0015, y, 0.1295))])
        _ink_tanks(P, W, D, H)
        _feet(P, [(sx * (W / 2 - 0.05), sy * (D / 2 - 0.04)) for sx in (-1, 1) for sy in (-1, 1)])
        P.build()
    return root


def _ink_tanks(P, W, D, H):
    """Integrated tank unit on the front right: window onto six inks."""
    x0, x1 = W / 2 - 0.135, W / 2 - 0.018
    z0, z1 = 0.035, 0.118
    yf = -D / 2
    frame = P('Tank unit', 'plastic_charcoal', 'HARD')
    frame.rounded_box((x1 - x0 + 0.012, 0.012, z1 - z0 + 0.022), 0.004,
                      ((x0 + x1) / 2, yf - 0.004, (z0 + z1) / 2 + 0.004), seg=2, zseg=2)
    back = P('Tank backing', 'plastic_white_gloss', 'FLAT')
    back.box((x0, yf - 0.0102, z0), (x1, yf - 0.0098, z1))
    n = len(INKS)
    pitch = (x1 - x0) / n
    for i, (key, level) in enumerate(INKS):
        cx = x0 + pitch * (i + 0.5)
        ink = P('Ink %s' % key.split('_')[1], key, 'FLAT')
        ink.box((cx - pitch * 0.32, yf - 0.0105, z0 + 0.006), (cx + pitch * 0.32, yf - 0.0102,
                                                               z0 + 0.006 + (z1 - z0 - 0.02) * level))
        marks = P('Tank marks', 'print_black', 'FLAT')
        for zz in (z0 + 0.012, z1 - 0.014):
            marks.box((cx - pitch * 0.38, yf - 0.0107, zz), (cx + pitch * 0.38, yf - 0.0105, zz + 0.0008))
    win = P('Tank window', 'plastic_clear', 'FLAT')
    win.quad([Vector((x0, yf - 0.0108, z0)), Vector((x1, yf - 0.0108, z0)), Vector((x1, yf - 0.0108, z1)),
              Vector((x0, yf - 0.0108, z1))])
    lbl = P('Tank label', 'indicator_red', 'FLAT')
    lbl.box((x0 + 0.02, yf - 0.0106, z1 + 0.003), (x1 - 0.02, yf - 0.0102, z1 + 0.012))
    txt = P('Tank label text', 'print_white', 'FLAT')
    add_text(txt, 'INK TANK', front_frame(((x0 + x1) / 2, yf - 0.0108, z1 + 0.0075), '-Y'), size=0.006)


def _photo(P, cx, D):
    """A3+ sheet halfway out of the printer, curling gently; it shows the
    landscape photo (cropped to the visible part of the sheet)."""
    img = bpy.data.images.get('TV Wallpaper')
    if img is None:
        img = bpy.data.images.new('TV Wallpaper', 64, 36)
        img.generated_type = 'COLOR_GRID'
    m = image_material('Photo Print', img, rough=0.12, coat=0.6)
    ph = P('Photo print', m, 'SMOOTH')
    pw, out = 0.329, 0.26                  # sheet width, length out of the slot
    y_slot = -D / 2 + 0.03
    u0, u1 = 0.14, 0.86                    # crop keeps the picture's proportions
    rows = 12
    rings, vs = [], []
    for k in range(rows + 1):
        t = k / rows                        # 0 at the slot, 1 at the leading edge
        y = y_slot - out * t
        z = 0.07 - 0.01 * t + 0.008 * math.sin(math.pi * t)
        rings.append([Vector((cx - pw / 2, y, z)), Vector((cx + pw / 2, y, z))])
        vs.append(1.0 - t)
    for k in range(rows):
        a, b = rings[k], rings[k + 1]
        ph.quad([b[0], b[1], a[1], a[0]], uv=[(u0, vs[k + 1]), (u1, vs[k + 1]), (u1, vs[k]), (u0, vs[k])])
