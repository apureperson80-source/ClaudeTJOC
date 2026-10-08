"""Snack vending machines: a classic silver spiral machine and a modern black
glass-front one (reference photo 2).

Local coordinates: floor at z = 0, centred on x, back against a wall at
y = 0 and the front facing -Y. Every part is a single-colour object.
"""

import math
import random

from mathutils import Matrix, Vector

from bathroom_gen.geo import group, panel_with_holes, plane_map, rounded_rect
from . import snacks
from .materials import screen_material
from .mesh import Builder, Parts, add_text, front_frame
from .studio import area_light
from .textures import Canvas

CLASSIC = {
    'name': 'Vending machine (classic)',
    'W': 0.99, 'D': 0.86, 'H': 1.83, 'base': 0.09,
    'body': 'silver_powder_coat', 'door': 'silver_powder_coat',
    'interior': 'plastic_charcoal',
    'window': (-0.440, 0.570, 0.275, 1.745),           # x0, z0, x1, z1
    'panel': (0.300, 0.330, 0.465, 1.520),
    'delivery': (-0.425, 0.330, 0.255, 0.470),
    # rows top to bottom: (kind, selections, clear height)
    'rows': [('bag', 6, 0.215), ('bag_small', 6, 0.190), ('pack', 7, 0.180),
             ('bar', 10, 0.170), ('bar', 9, 0.170), ('bag', 6, 0.230)],
    'seed': 3,
}

MODERN = {
    'name': 'Vending machine (modern)',
    'W': 1.12, 'D': 0.85, 'H': 1.83, 'base': 0.05,
    'body': 'plastic_black_gloss', 'door': 'plastic_black_gloss',
    'interior': 'plastic_dark_grey',
    'window': (-0.505, 0.600, 0.200, 1.745),
    'panel': (0.245, 0.560, 0.520, 1.745),
    'delivery': (-0.400, 0.230, 0.090, 0.420),
    'rows': [('bag_small', 7, 0.200), ('bag_small', 7, 0.190), ('pack', 8, 0.180),
             ('bar', 10, 0.170), ('bar', 10, 0.170), ('bag', 6, 0.235)],
    'seed': 11,
}

DOOR_T = 0.06          # door thickness
GLASS_Y = 0.034        # glass plane behind the door face


# ---------------------------------------------------------------------------
# Small geometry helpers
# ---------------------------------------------------------------------------

def _rbox(mb, mn, mx, r, seg=3):
    size = [b - a for a, b in zip(mn, mx)]
    c = [(a + b) / 2 for a, b in zip(mn, mx)]
    mb.rounded_box(size, r, c, seg=seg, zseg=seg)


def _hole_returns(mb, x0, z0, x1, z1, y0, y1):
    """Inward-facing reveal faces of a rectangular opening (y0 -> y1 deep)."""
    P = lambda x, y, z: Vector((x, y, z))
    mb.quad([P(x0, y0, z0), P(x1, y0, z0), P(x1, y1, z0), P(x0, y1, z0)])   # sill (faces +Z)
    mb.quad([P(x0, y0, z1), P(x0, y1, z1), P(x1, y1, z1), P(x1, y0, z1)])   # head (faces -Z)
    mb.quad([P(x0, y0, z0), P(x0, y1, z0), P(x0, y1, z1), P(x0, y0, z1)])   # left jamb (+X)
    mb.quad([P(x1, y0, z0), P(x1, y0, z1), P(x1, y1, z1), P(x1, y1, z0)])   # right jamb (-X)


def _frame_ring(mb, x0, z0, x1, z1, width, y0, y1, r=0.0):
    """Rectangular frame (picture-frame trim) between y0 (front) and y1."""
    outer = rounded_rect(x1 - x0 + 2 * width, z1 - z0 + 2 * width, r + width if r else 0.0, 4,
                         ((x0 + x1) / 2, (z0 + z1) / 2))
    inner = rounded_rect(x1 - x0, z1 - z0, r, 4, ((x0 + x1) / 2, (z0 + z1) / 2))
    to3 = lambda poly, y: [Vector((p.x, y, p.y)) for p in poly]
    # ring order: outer back, outer front, inner front, inner back
    mb.loft([to3(outer, y1), to3(outer, y0), to3(inner, y0), to3(inner, y1)], cyclic=False)


def _coil(mb, xc, zc, y0, y1, R, pitch, wire=0.0022, seg_turn=18, ring=6):
    turns = (y1 - y0) / pitch
    n = max(8, int(turns * seg_turn))
    path = []
    for k in range(n + 1):
        a = 2 * math.pi * turns * k / n
        path.append((xc + R * math.sin(a), y0 + (y1 - y0) * k / n, zc - R * math.cos(a)))
    # straight tail into the motor coupling
    path.append((xc, y1 + 0.004, zc))
    path.append((xc, y1 + 0.03, zc))
    mb.tube(path, wire, seg=ring)


# ---------------------------------------------------------------------------
# Cabinet
# ---------------------------------------------------------------------------

def _cabinet(P, s):
    W, D, H, zb = s['W'], s['D'], s['H'], s['base']
    body = P('Cabinet', s['body'])
    yb0 = -D + DOOR_T + 0.002          # body front (behind the door)
    t = 0.02
    # sides, top, back as slightly rounded slabs
    _rbox(body, (-W / 2, yb0, zb), (-W / 2 + t, 0.0, H), 0.004)
    _rbox(body, (W / 2 - t, yb0, zb), (W / 2, 0.0, H), 0.004)
    _rbox(body, (-W / 2 + t - 0.001, yb0, H - t), (W / 2 - t + 0.001, 0.0, H), 0.003)
    _rbox(body, (-W / 2 + t - 0.001, yb0, zb), (W / 2 - t + 0.001, 0.0, zb + t), 0.003)
    back = P('Back panel', 'plastic_dark_grey')
    back.box((-W / 2 + t, -0.012, zb + t), (W / 2 - t, -0.002, H - t))
    # door: front face with openings + edges
    door = P('Door', s['door'])
    wx0, wz0, wx1, wz1 = s['window']
    px0, pz0, px1, pz1 = s['panel']
    dx0, dz0, dx1, dz1 = s['delivery']
    holes = [(wx0 + W / 2, wz0 - zb, wx1 + W / 2, wz1 - zb),
             (px0 + W / 2, pz0 - zb, px1 + W / 2, pz1 - zb),
             (dx0 + W / 2, dz0 - zb, dx1 + W / 2, dz1 - zb)]
    gap = 0.0025
    dw, dh = W - 2 * gap, H - zb - gap
    mapper = plane_map((-W / 2 + gap, -D, zb), (1, 0, 0), (0, 0, 1), (0, -1, 0))
    holes_d = [(a - gap, b, c - gap, d) for (a, b, c, d) in holes]
    panel_with_holes(door, dw, dh, holes_d, mapper)
    # door edge band (thickness) all round
    x0, x1, z0, z1 = -W / 2 + gap, W / 2 - gap, zb, H - gap
    _hole_returns(door, x0, z0, x1, z1, -D + DOOR_T, -D)       # reversed = outward
    _hole_returns(door, wx0, wz0, wx1, wz1, -D, -D + GLASS_Y)
    _hole_returns(door, px0, pz0, px1, pz1, -D, -D + 0.012)
    _hole_returns(door, dx0, dz0, dx1, dz1, -D, -D + 0.02)
    # dark seam behind the door gap
    seam = P('Door seal', 'rubber_black')
    _frame_ring(seam, -W / 2 + 0.012, zb + 0.012, W / 2 - 0.012, H - 0.012, 0.011,
                -D + DOOR_T - 0.004, -D + DOOR_T + 0.002)


def _glass_and_interior(P, s, light=True):
    D = s['D']
    wx0, wz0, wx1, wz1 = s['window']
    gy = -D + GLASS_Y
    glass = P('Glass', 'glass_thin')
    glass.quad([Vector((wx0, gy, wz0)), Vector((wx1, gy, wz0)), Vector((wx1, gy, wz1)),
                Vector((wx0, gy, wz1))])
    gasket = P('Glass gasket', 'rubber_black')
    _frame_ring(gasket, wx0, wz0, wx1, wz1, 0.006, gy - 0.002, gy + 0.004)
    # product compartment (open towards the glass)
    inner = P('Interior', s['interior'])
    ix0, ix1 = wx0 - 0.02, wx1 + 0.02
    iz0, iz1 = wz0 - 0.03, wz1 + 0.02
    iy0, iy1 = gy + 0.004, -0.02
    V = Vector
    inner.quad([V((ix0, iy1, iz0)), V((ix1, iy1, iz0)), V((ix1, iy1, iz1)), V((ix0, iy1, iz1))])
    inner.quad([V((ix0, iy0, iz0)), V((ix0, iy1, iz0)), V((ix0, iy1, iz1)), V((ix0, iy0, iz1))])
    inner.quad([V((ix1, iy0, iz0)), V((ix1, iy0, iz1)), V((ix1, iy1, iz1)), V((ix1, iy1, iz0))])
    inner.quad([V((ix0, iy0, iz1)), V((ix0, iy1, iz1)), V((ix1, iy1, iz1)), V((ix1, iy0, iz1))])
    inner.quad([V((ix0, iy0, iz0)), V((ix1, iy0, iz0)), V((ix1, iy1, iz0)), V((ix0, iy1, iz0))])
    if light:
        # the cabinet light: a real light so the stock is lit through the glass
        cx = (wx0 + wx1) / 2
        L = area_light(s['name'] + ' interior light', (cx, gy + 0.06, wz1 - 0.01),
                       (cx, -0.3, wz0 + 0.2), 26.0, wx1 - wx0, 0.04, color=(0.95, 0.97, 1.0),
                       visible=False)
        return L


def _trays(P, s, stock):
    """Product trays with spirals, price channel + labels and the stock."""
    D = s['D']
    wx0, wz0, wx1, wz1 = s['window']
    rng = random.Random(s['seed'])
    snack_mat, rects = snacks.snack_atlas()
    tray = P('Trays', 'plastic_dark_grey')
    chan = P('Price channels', 'plastic_black_satin')
    coils = P('Spirals', 'coil_steel')
    motors = P('Spiral motors', 'plastic_black_matte')
    labels = P('Price labels', 'label_white')
    ink = P('Price label text', 'print_black')
    prods = P('Snacks', snack_mat)
    x0, x1 = wx0 - 0.012, wx1 + 0.012
    yf = -D + GLASS_Y + 0.06           # tray front lip
    yb = -0.09                         # back (motors)
    z = wz1 - 0.012
    letters = 'ABCDEF'
    prices = {'bag': ['1.75', '2.00', '1.50'], 'bag_small': ['1.25', '1.50'], 'pack': ['1.50', '1.75'],
              'bar': ['1.25', '1.00', '1.50']}
    for r, (kind, n, clear) in enumerate(s['rows']):
        z -= clear
        zf = z                          # tray floor
        tray.box((x0, yf, zf - 0.006), (x1, yb, zf))
        tray.box((x0, yb, zf), (x1, yb + 0.012, zf + 0.10))          # motor wall
        # price channel on the tray front
        chan.box((x0, yf - 0.012, zf - 0.034), (x1, yf, zf + 0.006))
        pitch_x = (x1 - x0) / n
        R = {'bag': 0.056, 'bag_small': 0.05, 'pack': 0.045, 'bar': 0.031}[kind]
        pitch = {'bag': 0.072, 'bag_small': 0.06, 'pack': 0.05, 'bar': 0.034}[kind]
        pool = snacks.KINDS['bar' if kind == 'bar' else ('pack' if kind == 'pack' else 'bag')]
        picks = rng.sample(pool, min(n, len(pool)))
        while len(picks) < n:
            picks.append(rng.choice(pool))
        for i in range(n):
            xc = x0 + pitch_x * (i + 0.5)
            zc = zf + R + 0.004
            yc0 = yf + 0.012
            _coil(coils, xc, zc, yc0, yb - 0.03, R, pitch)
            motors.revolve([(0.0, 0.0), (0.018, 0.0), (0.018, 0.02), (0.0, 0.02)], 12, axis='Y',
                           center=(xc, yb, zc))
            # price label: selection code + price
            lw = min(0.034, pitch_x * 0.8)
            ly = yf - 0.0125
            lz0, lz1 = zf - 0.03, zf - 0.008
            labels.quad([Vector((xc - lw / 2, ly, lz0)), Vector((xc + lw / 2, ly, lz0)),
                         Vector((xc + lw / 2, ly, lz1)), Vector((xc - lw / 2, ly, lz1))])
            code = '%s%d' % (letters[r], i + 1)
            add_text(ink, code, front_frame((xc, ly - 0.0004, lz1 - 0.0075), '-Y'),
                     size=0.0085, fit=(lw * 0.9, 0.01))
            add_text(ink, rng.choice(prices[kind]), front_frame((xc, ly - 0.0004, lz0 + 0.0045), '-Y'),
                     size=0.0065, fit=(lw * 0.9, 0.008))
            if not stock:
                continue
            # stock: front items always there, a few slots sold out at random
            count = rng.choice([3, 4, 4, 5])
            if rng.random() < 0.08:
                count = 0
            for k in range(count):
                yk = yc0 + pitch * (k + 0.55)
                if yk > yb - 0.05:
                    break
                lean = math.radians(rng.uniform(4, 10))
                m = (Matrix.Translation((xc + rng.uniform(-0.003, 0.003), yk, zf + 0.002))
                     @ Matrix.Rotation(rng.uniform(-0.05, 0.05), 4, 'Z')
                     @ Matrix.Rotation(-lean, 4, 'X'))
                snacks.pillow_pack(prods, kind, rects[picks[i]], m, rng)
    return prods


# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------

def _seven_segment(P, text, x, z, y, h, w_digit, on='led_red', off='led_red_off'):
    """7-segment digits; '.' after a digit lights its decimal point."""
    segs = {  # a b c d e f g
        '0': 'abcdef', '1': 'bc', '2': 'abged', '3': 'abgcd', '4': 'fgbc', '5': 'afgcd',
        '6': 'afgedc', '7': 'abc', '8': 'abcdefg', '9': 'abcfgd', '-': 'g', ' ': ''}
    lit = P('Display segments (lit)', on)
    dark = P('Display segments (off)', off)
    t = h * 0.12
    hw, hh = w_digit / 2, h / 2
    geo = {
        'a': (-hw + t, hh - t, hw - t, hh), 'g': (-hw + t, -t / 2, hw - t, t / 2),
        'd': (-hw + t, -hh, hw - t, -hh + t),
        'f': (-hw, t / 2, -hw + t, hh - t), 'b': (hw - t, t / 2, hw, hh - t),
        'e': (-hw, -hh + t, -hw + t, -t / 2), 'c': (hw - t, -hh + t, hw, -t / 2),
    }
    digits = []
    for ch in text:
        if ch == '.' and digits:
            digits[-1][1] = True
        else:
            digits.append([ch, False])
    pitch = w_digit * 1.45
    x -= pitch * (len(digits) - 1) / 2
    for ch, dp in digits:
        on_set = segs.get(ch, '')
        for sname, (a0, b0, a1, b1) in geo.items():
            mb = lit if sname in on_set else dark
            sk = 0.12 * w_digit                       # italic slant
            pts = [(x + a0 + sk * (b0 / hh), z + b0), (x + a1 + sk * (b0 / hh), z + b0),
                   (x + a1 + sk * (b1 / hh), z + b1), (x + a0 + sk * (b1 / hh), z + b1)]
            mb.quad([Vector((px, y, pz)) for px, pz in pts])
        mb = lit if dp else dark
        cx, cz = x + hw + t * 1.2, z - hh + t / 2
        mb.quad([Vector((cx - t / 2, y, cz - t / 2)), Vector((cx + t / 2, y, cz - t / 2)),
                 Vector((cx + t / 2, y, cz + t / 2)), Vector((cx - t / 2, y, cz + t / 2))])
        x += pitch


def _keypad(P, cx, cz, y, rows, key_w, key_h, gap, key_mat, legend_mat, depth=0.006):
    keys = P('Keypad buttons', key_mat)
    legend = P('Keypad legends', legend_mat)
    nr, nc = len(rows), len(rows[0])
    total_w = nc * key_w + (nc - 1) * gap
    total_h = nr * key_h + (nr - 1) * gap
    for r, row in enumerate(rows):
        for c, label in enumerate(row):
            kx = cx - total_w / 2 + key_w / 2 + c * (key_w + gap)
            kz = cz + total_h / 2 - key_h / 2 - r * (key_h + gap)
            _rbox(keys, (kx - key_w / 2, y - depth, kz - key_h / 2), (kx + key_w / 2, y, kz + key_h / 2),
                  0.0025)
            add_text(legend, label, front_frame((kx, y - depth - 0.0003, kz), '-Y'),
                     size=key_h * 0.5, fit=(key_w * 0.8, key_h * 0.6))
    return total_w, total_h


def _coin_slot(P, cx, cz, y, w=0.045, h=0.07):
    bezel = P('Coin slot', 'chrome')
    _rbox(bezel, (cx - w / 2, y - 0.008, cz - h / 2), (cx + w / 2, y, cz + h / 2), 0.006)
    slot = P('Slots (dark)', 'rubber_black')
    slot.box((cx - 0.002, y - 0.0085, cz - 0.016), (cx + 0.002, y - 0.0079, cz + 0.016))


def _bill_acceptor(P, cx, cz, y, w=0.09, h=0.13):
    body = P('Bill acceptor', 'plastic_black_matte')
    _rbox(body, (cx - w / 2, y - 0.03, cz - h / 2), (cx + w / 2, y, cz + h / 2), 0.008)
    slot = P('Slots (dark)', 'rubber_black')
    slot.box((cx - w * 0.36, y - 0.0306, cz - 0.003), (cx + w * 0.36, y - 0.0296, cz + 0.003))
    led = P('Bill acceptor LEDs', 'led_green')
    for sx in (-1, 1):
        x = cx + sx * w * 0.4
        led.quad([Vector((x - 0.004, y - 0.0305, cz - 0.004)), Vector((x + 0.004, y - 0.0305, cz - 0.004)),
                  Vector((x + 0.004, y - 0.0305, cz + 0.004)), Vector((x - 0.004, y - 0.0305, cz + 0.004))])
    label = P('Bill acceptor print', 'print_white')
    add_text(label, 'INSERT BILL', front_frame((cx, y - 0.0306, cz + h * 0.3), '-Y'), size=0.009,
             fit=(w * 0.8, 0.012))


def _coin_return(P, cx, cz, y, w=0.11, h=0.09, metal='chrome'):
    """Recessed coin-return cup with a hinged flap."""
    cup = P('Coin return cup', 'rubber_black')
    a0, a1 = cx - w / 2 + 0.008, cx + w / 2 - 0.008
    b0, b1 = cz - h / 2 + 0.008, cz + h / 2 - 0.008
    cup.quad([Vector((a0, y - 0.0008, b0)), Vector((a1, y - 0.0008, b0)), Vector((a1, y - 0.0008, b1)),
              Vector((a0, y - 0.0008, b1))])
    bez = P('Coin return', metal)
    _frame_ring(bez, a0, b0, a1, b1, 0.008, y - 0.006, y + 0.002, r=0.004)
    # hinged flap covering the upper half of the opening
    _rbox(bez, (a0 + 0.004, y - 0.0045, cz - 0.004), (a1 - 0.004, y - 0.0025, b1 - 0.002), 0.001)


def _controls_classic(P, s):
    D = s['D']
    x0, z0, x1, z1 = s['panel']
    yp = -D + 0.012                      # recessed panel face
    cx = (x0 + x1) / 2
    panel = P('Control panel', 'plastic_black_satin')
    panel.box((x0, yp, z0), (x1, yp + 0.01, z1))
    # price display
    disp = P('Display window', 'plastic_smoke')
    _rbox(disp, (cx - 0.055, yp - 0.006, 1.395), (cx + 0.055, yp, 1.465), 0.004)
    back = P('Display back', 'sensor_black')
    back.box((cx - 0.05, yp - 0.0015, 1.40), (cx + 0.05, yp - 0.001, 1.46))
    _seven_segment(P, '1.25', cx, 1.43, yp - 0.0018, 0.032, 0.016)
    # selection keypad
    rows = [['A', 'B', 'C'], ['D', 'E', 'F'], ['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9'],
            ['*', '0', '#']]
    _keypad(P, cx, 1.20, yp, rows, 0.034, 0.028, 0.008, 'plastic_silver_grey', 'print_black')
    ink = P('Panel print', 'print_white')
    add_text(ink, 'MAKE SELECTION', front_frame((cx, yp - 0.0003, 1.355), '-Y'), size=0.0085,
             fit=(x1 - x0 - 0.02, 0.01))
    _coin_slot(P, cx - 0.035, 0.97, yp)
    add_text(ink, 'COINS', front_frame((cx - 0.035, yp - 0.0003, 1.02), '-Y'), size=0.007)
    _bill_acceptor(P, cx + 0.03, 0.85, yp, w=0.085, h=0.12)
    btn = P('Coin return button', 'chrome')
    btn.revolve([(0, 0), (0.013, 0), (0.013, 0.008), (0.010, 0.011), (0, 0.011)], 20, axis='Y',
                center=(cx - 0.035, yp, 0.86))
    add_text(ink, 'RETURN', front_frame((cx - 0.035, yp - 0.0003, 0.835), '-Y'), size=0.0065)
    _coin_return(P, cx, 0.46, yp)


def _controls_modern(P, s):
    D = s['D']
    x0, z0, x1, z1 = s['panel']
    yp = -D                               # flush with the door
    cx = (x0 + x1) / 2
    face = P('Control panel', 'plastic_black_gloss')
    face.box((x0, yp, z0), (x1, yp + 0.01, z1))
    trim = P('Panel trim', 'aluminium')
    _frame_ring(trim, x0 + 0.004, z0 + 0.004, x1 - 0.004, z1 - 0.004, 0.004, yp - 0.003, yp + 0.002)
    # touch screen with a menu
    sw, sh, sz = 0.20, 0.27, 1.575
    bez = P('Touch screen bezel', 'plastic_black_matte')
    _rbox(bez, (cx - sw / 2 - 0.012, yp - 0.012, sz - sh / 2 - 0.012),
          (cx + sw / 2 + 0.012, yp, sz + sh / 2 + 0.012), 0.006)
    scr = P('Touch screen', screen_material('Vending Menu Screen', _menu_image(), strength=1.0))
    u0 = Vector((cx - sw / 2, yp - 0.0122, sz - sh / 2))
    scr.quad([u0, u0 + Vector((sw, 0, 0)), u0 + Vector((sw, 0, sh)), u0 + Vector((0, 0, sh))],
             uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
    # card reader with contactless symbol
    rdr = P('Card reader', 'plastic_black_matte')
    _rbox(rdr, (cx - 0.05, yp - 0.03, 1.32), (cx + 0.05, yp, 1.405), 0.008)
    blue = P('Card reader light', 'led_blue')
    for k, r in enumerate((0.008, 0.014, 0.020)):
        pts = []
        for j in range(9):
            a = math.radians(-50 + 100 * j / 8)
            pts.append(Vector((cx - 0.012 + r * math.cos(a), yp - 0.0303, 1.3625 + r * math.sin(a))))
        blue.tube(pts, 0.0012, seg=6)
    # keypad module with an LCD line
    mod = P('Keypad module', 'plastic_black_matte')
    _rbox(mod, (cx - 0.075, yp - 0.012, 1.06), (cx + 0.075, yp, 1.30), 0.006)
    lcd = P('LCD', 'lcd_blue')
    lcd.quad([Vector((cx - 0.06, yp - 0.0122, 1.255)), Vector((cx + 0.06, yp - 0.0122, 1.255)),
              Vector((cx + 0.06, yp - 0.0122, 1.29)), Vector((cx - 0.06, yp - 0.0122, 1.29))])
    lcd_ink = P('LCD text', 'print_black')
    add_text(lcd_ink, 'SELECT ITEM', front_frame((cx, yp - 0.0124, 1.2725), '-Y'), size=0.011,
             fit=(0.11, 0.014))
    rows = [['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9'], ['C', '0', 'OK']]
    _keypad(P, cx, 1.155, yp - 0.012, rows, 0.034, 0.03, 0.009, 'aluminium', 'print_black')
    _bill_acceptor(P, cx, 0.93, yp, w=0.10, h=0.13)
    _coin_slot(P, cx - 0.06, 0.80, yp, w=0.04, h=0.06)
    ink = P('Panel print', 'print_white')
    add_text(ink, 'COINS', front_frame((cx - 0.06, yp - 0.0003, 0.845), '-Y'), size=0.007)
    btn = P('Coin return button', 'aluminium')
    btn.revolve([(0, 0), (0.012, 0), (0.012, 0.006), (0.009, 0.009), (0, 0.009)], 20, axis='Y',
                center=(cx + 0.05, yp, 0.80))
    _coin_return(P, cx, 0.66, yp, w=0.12, h=0.09, metal='aluminium')


def _menu_image():
    w, h = 400, 540
    cv = Canvas(w, h, '#f4f6f8')
    cv.rect(0, h - 70, w, h, '#1e4f9a')
    cv.text('TOUCH TO ORDER', w / 2, h - 46, 22, '#ffffff', weight=0.7, align='center')
    cols = ['#d81e25', '#f4c20d', '#1f5fbf', '#1f8a3a', '#f07d18', '#5b2a86']
    for i in range(6):
        cx = 100 + (i % 2) * 200
        cy = h - 150 - (i // 2) * 140
        cv.rect(cx - 85, cy - 60, cx + 85, cy + 55, '#ffffff', r=10)
        cv.rect(cx - 40, cy - 25, cx + 40, cy + 45, cols[i], r=8)
        cv.text('$%d.%02d' % (1 + i % 2, 25 * (i % 4)), cx, cy - 50, 14, '#222222', weight=0.6,
                align='center')
    cv.rect(0, 0, w, 40, '#e9ecef')
    cv.text('CARD  -  CASH  -  PHONE', w / 2, 13, 13, '#555555', weight=0.5, align='center')
    return cv.to_image('Vending Menu (generated)')


# ---------------------------------------------------------------------------
# Delivery door, legs, plinth, lighting strips
# ---------------------------------------------------------------------------

def _delivery(P, s):
    D = s['D']
    x0, z0, x1, z1 = s['delivery']
    bin_ = P('Delivery bin', 'rubber_black')
    yd = -D + 0.02
    bin_.box((x0, yd, z0 - 0.08), (x1, yd + 0.25, z0))                 # bin floor
    bin_.box((x0, yd + 0.24, z0 - 0.08), (x1, yd + 0.25, z1 + 0.02))   # back
    classic = s is CLASSIC
    flap_mat = 'steel_brushed' if classic else 'plastic_light_grey'
    flap = P('Delivery flap', flap_mat)
    # flap hinged at the top, hanging slightly inwards
    ang = math.radians(6)
    hgt = z1 - z0 - 0.006
    m = Matrix.Translation((0, yd + 0.003, z1 - 0.003)) @ Matrix.Rotation(ang, 4, 'X')
    fb = Builder()
    _rbox(fb, (x0 + 0.004, 0.0, -hgt), (x1 - 0.004, 0.006, 0.0), 0.002)
    flap.merge(fb, m)
    text = P('Delivery flap print', 'print_grey' if classic else 'print_black')
    tb = Builder()
    add_text(tb, 'PUSH', front_frame(((x0 + x1) / 2, -0.0004, -hgt * 0.55), '-Y'), size=0.045,
             spacing=1.6)
    text.merge(tb, m)
    if not classic:
        trim = P('Delivery trim', 'aluminium')
        _frame_ring(trim, x0, z0, x1, z1, 0.012, -D - 0.004, -D + 0.004, r=0.01)


def _legs(P, s):
    W, D = s['W'], s['D']
    leg = P('Legs', 'black_powder_coat')
    feet = P('Leveling feet', 'rubber_black')
    hb = s['base']
    for x in (-W / 2 + 0.045, W / 2 - 0.045):
        for y in (-D + 0.07, -0.06):
            leg.revolve([(0.0, hb), (0.022, hb), (0.022, hb - 0.012), (0.016, hb - 0.02),
                         (0.012, 0.012), (0.0, 0.012)], 16, center=(x, y, 0.0), cap_start=True)
            feet.revolve([(0.0, 0.012), (0.026, 0.012), (0.028, 0.004), (0.026, 0.0), (0.0, 0.0)],
                         16, center=(x, y, 0.0))


def _plinth(P, s):
    W, D = s['W'], s['D']
    pl = P('Plinth', 'plastic_black_matte')
    pl.box((-W / 2 + 0.03, -D + 0.05, 0.0), (W / 2 - 0.03, -0.03, s['base']))


def _light_strips(P, s):
    D = s['D']
    wx0, wz0, wx1, wz1 = s['window']
    gy = -D + GLASS_Y
    if s is CLASSIC:
        tube = P('Fluorescent tube', 'fluorescent_tube')
        tube.tube([(wx0 - 0.004, gy + 0.03, wz0 + 0.03), (wx0 - 0.004, gy + 0.03, wz1 - 0.03)],
                  0.0125, seg=12)
    else:
        led = P('LED strips', 'led_white')
        for x in (wx0 - 0.006, wx1 + 0.006):
            led.box((x - 0.003, gy + 0.012, wz0 + 0.02), (x + 0.003, gy + 0.02, wz1 - 0.02))


def _trim_modern(P, s):
    D = s['D']
    wx0, wz0, wx1, wz1 = s['window']
    trim = P('Window trim', 'aluminium')
    _frame_ring(trim, wx0, wz0, wx1, wz1, 0.014, -D - 0.006, -D + 0.002, r=0.012)


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------

def _vending(s, stock=True, light=True):
    with group(s['name']) as root:
        P = Parts(s['name'].split('(')[1].rstrip(')').capitalize() + ' vending')
        _cabinet(P, s)
        _glass_and_interior(P, s, light)
        _trays(P, s, stock)
        _delivery(P, s)
        _light_strips(P, s)
        if s is CLASSIC:
            _controls_classic(P, s)
            _legs(P, s)
        else:
            _controls_modern(P, s)
            _trim_modern(P, s)
            _plinth(P, s)
        P.build({'Glass': 'FLAT', 'Snacks': 'SMOOTH', 'Spirals': 'SMOOTH', 'Price label text': 'FLAT',
                 'Keypad legends': 'FLAT', 'Panel print': 'FLAT', 'Delivery flap print': 'FLAT',
                 'Bill acceptor print': 'FLAT', 'Header print': 'FLAT', 'LCD text': 'FLAT',
                 'Display segments (lit)': 'FLAT', 'Display segments (off)': 'FLAT',
                 'Door': 'FLAT', 'Interior': 'FLAT', 'Trays': 'FLAT', 'Price channels': 'FLAT',
                 'Price labels': 'FLAT', 'Back panel': 'FLAT', 'Door seal': 'FLAT',
                 'Delivery bin': 'FLAT', 'Fluorescent tube': 'SMOOTH', 'Card reader light': 'SMOOTH',
                 'Legs': 'AUTO', 'Leveling feet': 'AUTO', 'Coin return button': 'AUTO',
                 'Spiral motors': 'AUTO', 'Plinth': 'FLAT', 'LED strips': 'FLAT', 'LCD': 'FLAT',
                 'Touch screen': 'FLAT', 'Slots (dark)': 'FLAT', 'Bill acceptor LEDs': 'FLAT',
                 'Glass gasket': 'FLAT', 'Window trim': 'AUTO', 'Panel trim': 'FLAT',
                 'Header plate': 'FLAT', 'Delivery trim': 'AUTO', 'Coin return cup': 'FLAT'})
    return root


def vending_classic():
    """Silver spiral snack machine on legs (reference photo 2, right)."""
    return _vending(CLASSIC)


def vending_modern():
    """Black glass-front machine with touch screen and card reader (photo 2, left)."""
    return _vending(MODERN)
