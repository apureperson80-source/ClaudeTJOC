"""Furniture and desk items.

Control-room pieces from reference photo 3 (architect desk lamp, coffee mug,
operator console, operator chair) plus simpler set dressing for the rooms the
CCTV cameras watch (tables, chairs, office desks, pallet racking, server
racks, sofa, reception desk, exit sign).

Origin on the floor (or desk top) at the footprint centre, front facing -Y.
"""

import math
import random

from mathutils import Matrix, Vector

from bathroom_gen.geo import group, rounded_rect
from .mesh import Builder, Parts, add_text, front_frame
from .studio import spot_light


def _rr(w, d, r, cx=0.0, cy=0.0, seg=4):
    return rounded_rect(w, d, max(r, 0.0004), seg, (cx, cy))


def _rbox(mb, mn, mx, r, seg=2):
    size = [b - a for a, b in zip(mn, mx)]
    c = [(a + b) / 2 for a, b in zip(mn, mx)]
    mb.rounded_box(size, r, c, seg=seg, zseg=seg)


def _rod(mb, a, b, r, seg=10):
    mb.tube([Vector(a), Vector(b)], r, seg=seg)


# ---------------------------------------------------------------------------
# Desk lamp
# ---------------------------------------------------------------------------

def desk_lamp(name='Desk lamp (architect)', lower=72.0, upper=-28.0, head=-60.0, light=True):
    """Black spring-balanced desk lamp. Angles in degrees from horizontal;
    the arms reach towards -Y (over the desk in front of the base)."""
    with group(name) as root:
        P = Parts('Desk lamp')
        metal = P('Body', 'black_powder_coat', 'AUTO')
        metal.revolve([(0.0, 0.0), (0.075, 0.0), (0.077, 0.004), (0.074, 0.02), (0.066, 0.026),
                       (0.02, 0.03), (0.0, 0.03)], 40)
        metal.revolve([(0.0, 0.03), (0.013, 0.03), (0.013, 0.05), (0.0, 0.05)], 16)
        L1, L2 = 0.36, 0.34
        piv = Vector((0.0, 0.0, 0.055))
        a1 = math.radians(lower)
        elbow = piv + Vector((0.0, -L1 * math.cos(a1), L1 * math.sin(a1)))
        a2 = math.radians(upper)
        wrist = elbow + Vector((0.0, -L2 * math.cos(a2), L2 * math.sin(a2)))
        for sx in (-0.012, 0.012):
            off = Vector((sx, 0, 0))
            _rod(metal, piv + off, elbow + off, 0.0035)
            _rod(metal, elbow + off, wrist + off, 0.0035)
        for c in (piv, elbow, wrist):
            metal.revolve([(0.0, -0.018), (0.009, -0.018), (0.009, 0.018), (0.0, 0.018)], 14, axis='X',
                          center=tuple(c))
        # springs beside the lower arm
        springs = P('Springs', 'steel_brushed', 'SMOOTH')
        for sx in (-0.024, 0.024):
            a = piv + Vector((sx, 0.012, 0.03))
            b = piv + (elbow - piv) * 0.55 + Vector((sx, 0.012, 0.0))
            d = (b - a)
            n = 40
            axis = d.normalized()
            side = axis.cross(Vector((1, 0, 0))).normalized()
            up = axis.cross(side)
            pts = [a + d * (k / n) + (side * math.cos(k * 1.1) + up * math.sin(k * 1.1)) * 0.0045
                   for k in range(n + 1)]
            springs.tube(pts, 0.0009, seg=5)
        # shade on the wrist, aimed down at the desk
        ah = math.radians(head)
        axis = Vector((0.0, -math.cos(ah), math.sin(ah)))
        shade_rot = Vector((0, 0, -1)).rotation_difference(axis).to_matrix().to_4x4()
        m = Matrix.Translation(wrist) @ shade_rot
        sub = Parts('_')
        sh = sub('Shade', 'black_powder_coat', 'SMOOTH')
        prof = [(0.016, 0.03), (0.022, 0.0), (0.034, -0.035), (0.062, -0.09), (0.075, -0.125),
                (0.077, -0.13)]
        sh.revolve([(0.0, 0.03)] + prof, 32)
        inner = sub('Shade lining', 'plastic_white_gloss', 'SMOOTH')
        inner.revolve([(0.072, -0.128), (0.059, -0.088), (0.032, -0.034), (0.02, -0.002), (0.0, 0.0)], 32)
        bulb = sub('Bulb', 'bulb_warm', 'SMOOTH')
        bulb.sphere(0.024, center=(0.0, 0.0, -0.045), seg=16, rings=10)
        for (pname, pm), mb in sub.items.items():
            P(pname, pm, sub.shading.get(pname)).merge(mb, m)
        P.build()
        if light:
            tip = wrist + axis * 0.05
            spot_light('Desk lamp light', tuple(tip), tuple(tip + axis), 18.0, angle=95, blend=0.7,
                       radius=0.02, color=(1.0, 0.8, 0.55))
    return root


# ---------------------------------------------------------------------------
# Coffee mug
# ---------------------------------------------------------------------------

def mug(name='Coffee mug'):
    with group(name) as root:
        P = Parts('Mug')
        body = P('Ceramic', 'ceramic', 'SMOOTH')
        body.revolve([(0.0, 0.0), (0.034, 0.0), (0.038, 0.004), (0.0405, 0.012), (0.041, 0.095),
                      (0.0395, 0.0975), (0.0375, 0.095), (0.0365, 0.012), (0.03, 0.008), (0.0, 0.008)], 40)
        pts = []
        for k in range(13):
            a = math.pi * (-0.5 + k / 12)
            pts.append((0.04 + 0.024 * math.cos(a), 0.0, 0.05 + 0.028 * math.sin(a)))
        body.tube(pts, 0.0055, seg=10)
        coffee = P('Coffee', 'coffee', 'SMOOTH')
        coffee.revolve([(0.0, 0.078), (0.0367, 0.078), (0.0367, 0.07)], 40)
        P.build()
    return root


# ---------------------------------------------------------------------------
# Operator console desk
# ---------------------------------------------------------------------------

def console_desk(width=3.0, depth=0.9, height=0.74, riser=0.14, name='Operator console desk'):
    """Long control-room desk with a raised monitor shelf along the back."""
    with group(name) as root:
        P = Parts('Console desk')
        top = P('Desk top', 'desk_charcoal', 'HARD')
        _rbox(top, (-width / 2, -depth / 2, height - 0.03), (width / 2, depth / 2, height), 0.004)
        edge = P('Edge band', 'rubber_black', 'HARD')
        _rbox(edge, (-width / 2 - 0.002, -depth / 2 - 0.006, height - 0.032), (width / 2 + 0.002, -depth / 2 + 0.004,
                                                                               height + 0.002), 0.005)
        shelf = P('Monitor shelf', 'desk_charcoal', 'HARD')
        sy0 = depth / 2 - 0.32
        _rbox(shelf, (-width / 2 + 0.02, sy0, height + riser - 0.025), (width / 2 - 0.02, depth / 2, height + riser),
              0.004)
        frame = P('Frame', 'black_powder_coat', 'HARD')
        for x in (-width / 2 + 0.05, -width / 6, width / 6, width / 2 - 0.05):
            _rbox(frame, (x - 0.02, sy0 + 0.02, height), (x + 0.02, depth / 2 - 0.02, height + riser - 0.025), 0.004)
            # side panels / legs
            _rbox(frame, (x - 0.025, -depth / 2 + 0.06, 0.0), (x + 0.025, depth / 2 - 0.04, height - 0.03), 0.006)
        modesty = P('Modesty panel', 'black_powder_coat', 'FLAT')
        modesty.box((-width / 2 + 0.03, depth / 2 - 0.06, 0.12), (width / 2 - 0.03, depth / 2 - 0.045, height - 0.03))
        # cable grommets
        dark = P('Grommets', 'rubber_black', 'AUTO')
        for x in (-width / 3, 0.0, width / 3):
            dark.revolve([(0.0, height + 0.0005), (0.03, height + 0.0005), (0.034, height + 0.003),
                          (0.026, height + 0.003), (0.0, height + 0.001)], 24, center=(x, sy0 - 0.05, 0.0))
        P.build()
    return root


# ---------------------------------------------------------------------------
# Chairs
# ---------------------------------------------------------------------------

def _star_base(P, r=0.33, z=0.075, material='plastic_black_matte'):
    base = P('Base', material, 'AUTO')
    for k in range(5):
        a = math.radians(90 + 72 * k)
        tip = Vector((r * math.cos(a), r * math.sin(a), z))
        base.tube([Vector((0, 0, z + 0.015)), Vector((tip.x * 0.5, tip.y * 0.5, z + 0.01)), tip], 0.016, seg=8)
        cast = P('Casters', 'rubber_black', 'SMOOTH')
        cast.revolve([(0.0, -0.012), (0.024, -0.012), (0.026, 0.0), (0.024, 0.012), (0.0, 0.012)], 14,
                     axis='X', center=(tip.x, tip.y, 0.026))
        base.box((tip.x - 0.008, tip.y - 0.008, 0.03), (tip.x + 0.008, tip.y + 0.008, z))
    base.revolve([(0.0, z - 0.01), (0.04, z - 0.01), (0.045, z + 0.03), (0.0, z + 0.035)], 20)


def operator_chair(name='Operator chair', seat_h=0.48, turn=0.0):
    """24/7 control-room chair: star base, gas lift, padded seat, mesh back,
    headrest and armrests. The sitter faces -Y."""
    with group(name) as root:
        P = Parts('Operator chair')
        _star_base(P)
        lift = P('Gas lift', 'chrome', 'SMOOTH')
        lift.revolve([(0.0, 0.1), (0.014, 0.1), (0.014, seat_h - 0.12), (0.0, seat_h - 0.12)], 16)
        shroud = P('Lift cover', 'plastic_black_matte', 'SMOOTH')
        shroud.revolve([(0.0, 0.1), (0.026, 0.1), (0.022, 0.26), (0.0, 0.26)], 16)
        mech = P('Mechanism', 'black_powder_coat', 'HARD')
        _rbox(mech, (-0.11, -0.12, seat_h - 0.12), (0.11, 0.1, seat_h - 0.07), 0.01)
        seat = P('Seat cushion', 'fabric_charcoal', 'SMOOTH')
        seat.rounded_box((0.5, 0.5, 0.085), 0.035, (0.0, -0.02, seat_h - 0.03), seg=4, zseg=3)
        # backrest frame and mesh, tilted back
        bk = Parts('_')
        fr = bk('Back frame', 'plastic_black_matte', 'HARD')
        outline = _rr(0.46, 0.62, 0.12)
        fr.loft([[Vector((p.x, 0.0, p.y)) for p in outline], [Vector((p.x, 0.03, p.y)) for p in outline]],
                cap_start=False, cap_end=False)
        inner = _rr(0.40, 0.56, 0.09)
        fr.loft([[Vector((p.x, 0.0, p.y)) for p in outline], [Vector((p.x, 0.0, p.y)) for p in inner]])
        fr.loft([[Vector((p.x, 0.03, p.y)) for p in inner], [Vector((p.x, 0.03, p.y)) for p in outline]])
        mesh = bk('Back mesh', 'mesh_black', 'FLAT')
        mesh.polygon([Vector((p.x, 0.012, p.y)) for p in inner])
        head = bk('Headrest', 'fabric_charcoal', 'SMOOTH')
        head.rounded_box((0.3, 0.07, 0.14), 0.03, (0.0, 0.0, 0.44), seg=3, zseg=3)
        fr.box((-0.02, 0.01, 0.3), (0.02, 0.03, 0.38))
        m = (Matrix.Translation((0.0, 0.24, seat_h + 0.33)) @ Matrix.Rotation(math.radians(-12), 4, 'X'))
        for (pname, pm), mb in bk.items.items():
            P(pname, pm, bk.shading.get(pname)).merge(mb, m)
        spine = P('Back spine', 'black_powder_coat', 'HARD')
        spine.tube([(0.0, 0.1, seat_h - 0.08), (0.0, 0.25, seat_h - 0.02), (0.0, 0.265, seat_h + 0.12)], 0.018, seg=8)
        arms = P('Armrests', 'plastic_black_matte', 'HARD')
        pads = P('Arm pads', 'rubber_black', 'HARD')
        for sx in (-1, 1):
            x = sx * 0.27
            arms.box((x - 0.015, -0.02, seat_h - 0.06), (x + 0.015, 0.06, seat_h + 0.18))
            _rbox(pads, (x - 0.04, -0.13, seat_h + 0.18), (x + 0.04, 0.12, seat_h + 0.21), 0.012)
        P.build()
        root.rotation_euler[2] = math.radians(turn)
    return root


def chair_stacking(name='Stacking chair', color='plastic_red'):
    with group(name) as root:
        P = Parts('Stacking chair')
        legs = P('Frame', 'chrome', 'SMOOTH')
        for sx in (-1, 1):
            x = sx * 0.2
            legs.tube([(x, -0.2, 0.0), (x, -0.19, 0.45), (x, 0.17, 0.45), (x, 0.2, 0.0)], 0.009, seg=8)
            legs.tube([(x, 0.17, 0.45), (x * 0.95, 0.22, 0.85)], 0.009, seg=8)
        shell = P('Shell', color, 'SMOOTH')
        shell.rounded_box((0.44, 0.42, 0.02), 0.009, (0.0, -0.01, 0.465), seg=2, zseg=2)
        bm = Builder()
        bm.rounded_box((0.42, 0.02, 0.26), 0.009, (0.0, 0.0, 0.0), seg=2, zseg=2)
        shell.merge(bm, Matrix.Translation((0.0, 0.205, 0.72)) @ Matrix.Rotation(math.radians(-10), 4, 'X'))
        P.build()
    return root


def office_chair_simple(name='Office chair'):
    with group(name) as root:
        P = Parts('Office chair')
        _star_base(P, r=0.3)
        lift = P('Gas lift', 'chrome', 'SMOOTH')
        lift.revolve([(0.0, 0.1), (0.014, 0.1), (0.014, 0.38), (0.0, 0.38)], 12)
        seat = P('Seat', 'fabric_blue', 'SMOOTH')
        seat.rounded_box((0.46, 0.46, 0.07), 0.03, (0.0, 0.0, 0.45), seg=3, zseg=2)
        bm = Builder()
        bm.rounded_box((0.44, 0.06, 0.48), 0.03, (0.0, 0.0, 0.0), seg=3, zseg=2)
        seat.merge(bm, Matrix.Translation((0.0, 0.25, 0.78)) @ Matrix.Rotation(math.radians(-10), 4, 'X'))
        P.build()
    return root


# ---------------------------------------------------------------------------
# Tables and desks
# ---------------------------------------------------------------------------

def table_round(name='Round table', r=0.45, h=0.74):
    with group(name) as root:
        P = Parts('Round table')
        top = P('Top', 'laminate_white', 'AUTO')
        top.revolve([(0.0, h - 0.025), (r, h - 0.025), (r + 0.002, h - 0.012), (r, h), (0.0, h)], 48)
        base = P('Pedestal', 'black_powder_coat', 'AUTO')
        base.revolve([(0.0, 0.0), (0.26, 0.0), (0.26, 0.012), (0.05, 0.03), (0.04, 0.04), (0.04, h - 0.03),
                      (0.12, h - 0.03), (0.12, h - 0.025), (0.0, h - 0.025)], 32)
        P.build()
    return root


def office_desk(name='Office desk', w=1.4, d=0.7, h=0.74):
    with group(name) as root:
        P = Parts('Office desk')
        top = P('Top', 'laminate_light_oak', 'HARD')
        _rbox(top, (-w / 2, -d / 2, h - 0.025), (w / 2, d / 2, h), 0.003)
        legs = P('Legs', 'aluminium', 'HARD')
        for sx in (-1, 1):
            x = sx * (w / 2 - 0.05)
            _rbox(legs, (x - 0.025, -d / 2 + 0.05, 0.0), (x + 0.025, -d / 2 + 0.1, h - 0.025), 0.004)
            _rbox(legs, (x - 0.025, d / 2 - 0.1, 0.0), (x + 0.025, d / 2 - 0.05, h - 0.025), 0.004)
            _rbox(legs, (x - 0.02, -d / 2 + 0.05, h - 0.08), (x + 0.02, d / 2 - 0.05, h - 0.03), 0.004)
        panel = P('Modesty panel', 'laminate_white', 'FLAT')
        panel.box((-w / 2 + 0.08, d / 2 - 0.04, 0.3), (w / 2 - 0.08, d / 2 - 0.025, h - 0.03))
        P.build()
    return root


def reception_desk(name='Reception desk', w=2.2):
    with group(name) as root:
        P = Parts('Reception desk')
        body = P('Body', 'laminate_white', 'HARD')
        _rbox(body, (-w / 2, -0.1, 0.0), (w / 2, 0.0, 1.08), 0.006)
        work = P('Work top', 'laminate_light_oak', 'HARD')
        _rbox(work, (-w / 2, 0.0, 0.72), (w / 2, 0.7, 0.75), 0.004)
        cap = P('Counter cap', 'laminate_light_oak', 'HARD')
        _rbox(cap, (-w / 2 - 0.02, -0.16, 1.08), (w / 2 + 0.02, 0.06, 1.11), 0.004)
        sides = P('Sides', 'laminate_white', 'HARD')
        for sx in (-1, 1):
            x = sx * (w / 2 - 0.02)
            _rbox(sides, (x - 0.02, 0.0, 0.0), (x + 0.02, 0.7, 0.72), 0.004)
        logo = P('Sign', 'plastic_blue', 'FLAT')
        logo.box((-0.35, -0.104, 0.55), (0.35, -0.1, 0.62))
        txt = P('Sign text', 'print_white', 'FLAT')
        add_text(txt, 'RECEPTION', front_frame((0.0, -0.1045, 0.585), '-Y'), size=0.05)
        P.build()
    return root


def sofa(name='Sofa', w=1.9):
    with group(name) as root:
        P = Parts('Sofa')
        fab = P('Upholstery', 'fabric_blue', 'SMOOTH')
        fab.rounded_box((w, 0.85, 0.24), 0.04, (0.0, 0.0, 0.25), seg=3, zseg=3)
        fab.rounded_box((w, 0.22, 0.5), 0.05, (0.0, 0.32, 0.55), seg=3, zseg=3)
        for sx in (-1, 1):
            fab.rounded_box((0.2, 0.85, 0.32), 0.05, (sx * (w / 2 - 0.1), 0.0, 0.46), seg=3, zseg=3)
        cush = P('Cushions', 'fabric_grey', 'SMOOTH')
        n = 3
        cw = (w - 0.4) / n
        for k in range(n):
            cush.rounded_box((cw - 0.01, 0.62, 0.12), 0.04, (-w / 2 + 0.2 + cw * (k + 0.5), -0.08, 0.43), seg=3, zseg=3)
        legs = P('Legs', 'black_powder_coat', 'AUTO')
        for sx in (-1, 1):
            for sy in (-1, 1):
                legs.revolve([(0.0, 0.0), (0.02, 0.0), (0.025, 0.13), (0.0, 0.13)], 10,
                             center=(sx * (w / 2 - 0.08), sy * 0.33, 0.0))
        P.build()
    return root


# ---------------------------------------------------------------------------
# Warehouse and server room
# ---------------------------------------------------------------------------

def pallet(name='Pallet'):
    with group(name) as root:
        P = Parts('Pallet')
        wood = P('Timber', 'wood_pallet', 'FLAT')
        L, W = 1.2, 0.8
        for k in range(7):
            y = -W / 2 + 0.05 + k * (W - 0.1) / 6
            wood.box((-L / 2, y - 0.05, 0.122), (L / 2, y + 0.05, 0.144))
        for y in (-W / 2 + 0.05, 0.0, W / 2 - 0.05):
            wood.box((-L / 2, y - 0.05, 0.1), (L / 2, y + 0.05, 0.122))
            for x in (-L / 2 + 0.05, 0.0, L / 2 - 0.05):
                wood.box((x - 0.05, y - 0.05, 0.022), (x + 0.05, y + 0.05, 0.1))
        for k in range(3):
            x = -L / 2 + 0.05 + k * (L - 0.1) / 2
            wood.box((x - 0.05, -W / 2, 0.0), (x + 0.05, W / 2, 0.022))
        P.build()
    return root


def pallet_rack(name='Pallet rack bay', w=2.7, d=1.1, levels=(0.0, 1.5, 3.0), h=4.2):
    """One bay of pallet racking; origin at the floor centre, aisle side -Y."""
    with group(name) as root:
        P = Parts('Pallet rack')
        up = P('Uprights', 'steel_blue', 'HARD')
        for x in (-w / 2, w / 2):
            for y in (-d / 2, d / 2):
                _rbox(up, (x - 0.04, y - 0.035, 0.0), (x + 0.04, y + 0.035, h), 0.004)
            # diagonal bracing between the front and back uprights
            for k in range(6):
                z0 = 0.15 + k * 0.65
                up.tube([(x, -d / 2, z0), (x, d / 2, z0 + 0.6)], 0.012, seg=6)
        beams = P('Beams', 'steel_orange', 'HARD')
        decks = P('Wire decks', 'aluminium', 'FLAT')
        for z in levels:
            if z <= 0.0:
                continue
            for y in (-d / 2, d / 2):
                _rbox(beams, (-w / 2 + 0.04, y - 0.025, z - 0.11), (w / 2 - 0.04, y + 0.025, z), 0.004)
            for k in range(12):
                x = -w / 2 + 0.1 + k * (w - 0.2) / 11
                decks.box((x - 0.006, -d / 2, z - 0.004), (x + 0.006, d / 2, z))
        P.build()
    return root


def server_rack(name='Server rack', seed=2):
    rng = random.Random(seed)
    with group(name) as root:
        P = Parts('Server rack')
        body = P('Cabinet', 'plastic_black_matte', 'HARD')
        w, d, h = 0.6, 1.07, 2.0
        _rbox(body, (-w / 2, -d / 2, 0.0), (w / 2, d / 2, h), 0.006)
        door = P('Perforated door', 'mesh_black', 'FLAT')
        door.box((-w / 2 + 0.03, -d / 2 - 0.006, 0.08), (w / 2 - 0.03, -d / 2 - 0.002, h - 0.08))
        units = P('Servers', 'gunmetal', 'FLAT')
        green = P('LEDs (green)', 'led_green', 'FLAT')
        amber = P('LEDs (amber)', 'led_amber', 'FLAT')
        blue = P('LEDs (blue)', 'led_blue', 'FLAT')
        z = 0.15
        while z < h - 0.2:
            uh = rng.choice((0.0445, 0.0445, 0.089, 0.0445))
            units.box((-w / 2 + 0.05, -d / 2 - 0.0005, z + 0.002), (w / 2 - 0.05, -d / 2 + 0.01, z + uh - 0.002))
            for k in range(rng.randint(2, 6)):
                x = -w / 2 + 0.08 + k * 0.025
                led = rng.choice((green, green, green, amber, blue))
                led.quad([Vector((x, -d / 2 - 0.0012, z + 0.012)), Vector((x + 0.006, -d / 2 - 0.0012, z + 0.012)),
                          Vector((x + 0.006, -d / 2 - 0.0012, z + 0.018)), Vector((x, -d / 2 - 0.0012, z + 0.018))])
            z += uh
        P.build()
    return root


def exit_sign(name='Exit sign'):
    """Wall-mounted emergency exit sign; back on the wall plane y = 0."""
    with group(name) as root:
        P = Parts('Exit sign')
        box = P('Housing', 'plastic_white_gloss', 'HARD')
        _rbox(box, (-0.18, -0.05, -0.08), (0.18, 0.0, 0.08), 0.006)
        face = P('Sign face', 'exit_green', 'FLAT')
        face.box((-0.16, -0.0505, -0.065), (0.16, -0.05, 0.065))
        txt = P('Sign text', 'print_white', 'FLAT')
        add_text(txt, 'EXIT', front_frame((0.0, -0.051, 0.0), '-Y'), size=0.08)
        P.build()
    return root


def shelving_unit(name='Shelving unit', w=1.0, d=0.45, h=1.85, shelves=5):
    """Boltless steel shelving; origin at the floor centre, front -Y."""
    with group(name) as root:
        P = Parts('Shelving unit')
        posts = P('Posts', 'steel_grey', 'FLAT')
        for x in (-w / 2, w / 2 - 0.035):
            for y in (-d / 2, d / 2 - 0.035):
                posts.box((x, y, 0.0), (x + 0.035, y + 0.035, h))
        boards = P('Shelves', 'steel_grey', 'HARD')
        for k in range(shelves):
            z = 0.08 + k * (h - 0.12) / (shelves - 1)
            _rbox(boards, (-w / 2, -d / 2, z - 0.025), (w / 2, d / 2, z), 0.003)
        P.build()
    return root
