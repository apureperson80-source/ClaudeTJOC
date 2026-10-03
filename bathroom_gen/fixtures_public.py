"""Commercial / public washroom fixtures (modelled after the lilac reference).

Same conventions as fixtures_home: wall at local y = 0, front towards -Y.
"""

import math

import bpy
from mathutils import Matrix, Vector

from .fixtures_home import _water, se, toilet_seat
from .geo import (MeshBuilder, catmull_rom, fillet_path, group, link, ring_xy,
                  ring_xz, rounded_poly, rounded_rect, superellipse)
from .materials import mat


# ---------------------------------------------------------------------------
# Wall-hung WC + flush plate
# ---------------------------------------------------------------------------

PAN_WH = [
    (0.120, 0.080, 0.080, 2.5, 8.0, -0.080, 0.215),
    (0.150, 0.150, 0.150, 2.5, 8.0, -0.150, 0.240),
    (0.170, 0.220, 0.220, 2.6, 8.0, -0.220, 0.290),
    (0.178, 0.258, 0.258, 2.6, 8.0, -0.258, 0.350),
    (0.180, 0.270, 0.270, 2.6, 8.0, -0.270, 0.395),
    (0.179, 0.269, 0.269, 2.6, 8.0, -0.270, 0.404),
    (0.175, 0.265, 0.265, 2.6, 8.0, -0.270, 0.408),
    (0.132, 0.215, 0.165, 2.4, 2.6, -0.300, 0.408),
    (0.129, 0.211, 0.160, 2.4, 2.6, -0.300, 0.402),
    (0.120, 0.195, 0.145, 2.3, 2.5, -0.300, 0.370),
    (0.100, 0.160, 0.115, 2.2, 2.3, -0.290, 0.330),
    (0.075, 0.115, 0.080, 2.1, 2.2, -0.270, 0.300),
    (0.055, 0.065, 0.055, 2.0, 2.0, -0.230, 0.285),
    (0.044, 0.044, 0.044, 2.0, 2.0, -0.200, 0.278),
]


def wc_wall_hung(seat_color='ceramic'):
    with group('WC (wall-hung)') as root:
        mb = MeshBuilder()
        mb.loft([se(*s) for s in PAN_WH], cap_start=True, cap_end=True)
        mb.build('Pan', mat('ceramic'), subsurf=2, viewport_subsurf=1)
        _water(PAN_WH, 0.315)
        toilet_seat(-0.315, 0.176, 0.225, 0.18, (0.118, 0.165, 0.12, -0.30), 0.408,
                    lid=False, color=seat_color)
    return root


def flush_plate(metal='steel_brushed'):
    """Dual-flush plate on a duct face; origin = plate centre on the wall."""
    with group('Flush plate') as root:
        mb = MeshBuilder()
        poly = rounded_rect(0.246, 0.164, 0.006, 4)
        mb.loft([ring_xz(poly, 0.0), ring_xz(poly, -0.004),
                 ring_xz(rounded_rect(0.240, 0.158, 0.004, 4), -0.006)],
                cap_start=True, cap_end=True)
        for x0, x1 in ((-0.105, -0.004), (0.004, 0.105)):
            b = rounded_rect(x1 - x0, 0.128, 0.004, 4, ((x0 + x1) / 2, 0))
            mb.loft([ring_xz(b, -0.005), ring_xz(b, -0.0085),
                     ring_xz(rounded_rect(x1 - x0 - 0.003, 0.125, 0.003, 4, ((x0 + x1) / 2, 0)),
                             -0.0095)], cap_end=True)
        mb.build('Flush plate', mat(metal))
        dm = MeshBuilder()
        # flush volume symbols (one/two drops)
        for cx, n in ((-0.0545, 1), (0.0545, 2)):
            for k in range(n):
                dm.revolve([(0, 0), (0.0045, 0), (0.0045, 0.0003), (0, 0.0003)], 16, axis='Y',
                           center=(cx + (k - (n - 1) / 2) * 0.012, -0.0094, 0.0))
        dm.build('Flush icons', mat('plastic_dark'), 'FLAT')
    return root


# ---------------------------------------------------------------------------
# Urinal + sensor + privacy screen
# ---------------------------------------------------------------------------

URINAL = [  # (w, d_bottom, d_top, e_bottom, e_top, cz, y)
    (0.160, 0.300, 0.280, 2.6, 2.2, 0.950, 0.000),
    (0.172, 0.310, 0.290, 2.6, 2.2, 0.950, -0.100),
    (0.170, 0.300, 0.290, 2.6, 2.2, 0.945, -0.220),
    (0.160, 0.280, 0.280, 2.6, 2.2, 0.940, -0.300),
    (0.152, 0.270, 0.270, 2.6, 2.2, 0.940, -0.320),
    (0.145, 0.262, 0.262, 2.6, 2.2, 0.940, -0.326),
    (0.130, 0.245, 0.245, 2.5, 2.2, 0.945, -0.326),
    (0.127, 0.240, 0.240, 2.5, 2.2, 0.945, -0.319),
    (0.122, 0.235, 0.232, 2.4, 2.2, 0.945, -0.270),
    (0.118, 0.225, 0.225, 2.3, 2.2, 0.950, -0.170),
    (0.105, 0.190, 0.200, 2.2, 2.1, 0.960, -0.080),
    (0.080, 0.130, 0.160, 2.0, 2.0, 0.970, -0.045),
]


def _urinal_ring(spec, n=48):
    w, db, dt, eb, et, cz, y = spec
    pts = superellipse(n, w, db, dt, eb, et, (0.0, cz))
    k = 0.28 * (-y / 0.326)       # slanted rim: the lip juts out at the bottom
    return [Vector((p.x, y + k * (p.y - cz), p.y)) for p in pts]


def urinal():
    with group('Urinal') as root:
        mb = MeshBuilder()
        mb.loft([_urinal_ring(s) for s in URINAL], cap_start=True, cap_end=True)
        mb.build('Urinal bowl', mat('ceramic'), subsurf=2, viewport_subsurf=1)
        # strainer at the bottom of the bowl
        dm = MeshBuilder()
        dm.revolve([(0, 0.004), (0.026, 0.003), (0.03, 0.0), (0, 0.0)], 32)
        for i in range(8):
            a = math.pi * i / 8
            dm.box((-0.022, -0.0015, 0.0042), (0.022, 0.0015, 0.0046))
            dm.transform(Matrix.Rotation(a, 4, 'Z'), len(dm.verts) - 8)
        dm.transform(Matrix.Translation((0, -0.11, 0.735)) @ Matrix.Rotation(-0.35, 4, 'X'))
        dm.build('Strainer', mat('chrome'))
        # sensor flush valve above
        sm = MeshBuilder()
        sm.rounded_box((0.085, 0.045, 0.13), 0.012, (0, -0.0225, 1.36), 4, 3)
        sm.tube([(0, -0.030, 1.296), (0, -0.030, 1.24), (0, -0.045, 1.215)], 0.010, 20)
        sm.revolve([(0, 0), (0.016, 0), (0.016, 0.012), (0.012, 0.016), (0, 0.016)], 24,
                   center=(0, -0.045, 1.200))
        sm.build('Flush sensor', mat('chrome'))
        wm = MeshBuilder()
        b = rounded_rect(0.05, 0.03, 0.008, 4, (0, 1.38))
        wm.loft([ring_xz(b, -0.0452), ring_xz(b, -0.0462)], cap_end=True)
        wm.build('Sensor window', mat('sensor_black'), 'FLAT')
    return root


def urinal_screen(depth=0.45, height=0.85, z0=0.55, metal='steel_brushed'):
    """Privacy screen in the local YZ plane (thickness along X)."""
    with group('Urinal screen') as root:
        t = 0.013
        poly = [(-0.01, 0.0), (-depth + 0.08, 0.0), (-depth, 0.08), (-depth, height - 0.08),
                (-depth + 0.08, height), (-0.01, height)]
        pp = rounded_poly(list(reversed(poly)), [0.0, 0.06, 0.06, 0.06, 0.06, 0.0], 6)
        mb = MeshBuilder()
        mb.prism([(u, v + z0) for u, v in pp], -t / 2, t / 2,
                 lambda u, v, w: Vector((w, u, v)))
        mb.build('Screen panel', mat('laminate_oak'), 'HARD')
        bm = MeshBuilder()
        for z in (z0 + 0.12, z0 + height - 0.12):
            bm.rounded_box((0.04, 0.05, 0.03), 0.004, (0, -0.025, z), 2, 2)
        bm.build('Screen brackets', mat(metal))
    return root


# ---------------------------------------------------------------------------
# Basin taps, soap dispensers, dryers ...
# ---------------------------------------------------------------------------

def tap_sensor(metal='chrome'):
    """Deck-mounted infra-red swan-neck tap. Origin at deck surface."""
    with group('Sensor tap') as root:
        mb = MeshBuilder()
        mb.revolve([(0, 0), (0.030, 0), (0.030, 0.004), (0.026, 0.010), (0.019, 0.013),
                    (0, 0.013)], 40)
        path = catmull_rom([(0, 0, 0.005), (0, 0, 0.09), (0, -0.025, 0.155),
                            (0, -0.085, 0.165), (0, -0.13, 0.135), (0, -0.138, 0.118)], 12)
        mb.tube(path, lambda t: 0.0175 - 0.005 * t, 32)
        mb.build('Tap body', mat(metal))
        dm = MeshBuilder()
        end = Vector(path[-1])
        dm.revolve([(0, 0), (0.0095, 0), (0.0095, -0.0015), (0, -0.0015)], 20,
                   center=(end.x, end.y + 0.002, end.z + 0.002))
        # IR eye on the front of the column
        dm.revolve([(0, 0), (0.0055, 0), (0.0055, 0.0012), (0, 0.0012)], 20, axis='Y',
                   center=(0, -0.0168, 0.065))
        dm.build('Sensor eye', mat('sensor_black'))
    return root


def soap_dispenser_wall(body='plastic_white'):
    """Automatic wall soap dispenser, origin = wall at the bottom centre."""
    with group('Soap dispenser') as root:
        mb = MeshBuilder()

        def R(s, z):
            return se(0.060, 0.052, 0.052, 3.2, 9.0, -0.052, z, 40, s)
        mb.loft([R(0.88, 0.0), R(0.97, 0.004), R(1.0, 0.014), R(1.0, 0.225), R(0.97, 0.236),
                 R(0.88, 0.240)], cap_start=True, cap_end=True)
        mb.build('Dispenser body', mat(body), subsurf=1)
        wm = MeshBuilder()
        # smoked level window wrapping the front
        pts_lo = [p for p in superellipse(40, 0.046, 0.0545, 0.0, 3.2, 2.0, (0, -0.052))
                  if p.y < -0.06]
        rows = []
        for z in (0.09, 0.19):
            rows.append([Vector((p.x, p.y - 0.0012, z)) for p in pts_lo])
        wm.loft(rows, closed=False)
        wm.build('Level window', mat('smoke_window'), 'SMOOTH')
        nm = MeshBuilder()
        nm.revolve([(0, 0.002), (0.006, 0.002), (0.006, -0.008), (0.003, -0.010), (0, -0.010)],
                   20, center=(0, -0.075, 0))
        nm.build('Nozzle', mat('chrome'))
        em = MeshBuilder()
        em.revolve([(0, 0), (0.007, 0), (0.007, -0.0008), (0, -0.0008)], 20,
                   center=(0, -0.045, 0.0))
        em.build('IR sensor', mat('sensor_black'), 'FLAT')
    return root


def hand_dryer(body='steel_brushed'):
    """High-speed hand dryer; origin = wall, bottom centre."""
    with group('Hand dryer') as root:
        mb = MeshBuilder()

        def R(df, s, z):
            return se(0.140, df, 0.04, 3.0, 9.0, -0.04, z, 48, s)
        mb.loft([R(0.06, 0.85, 0.0), R(0.11, 0.97, 0.008), R(0.12, 1.0, 0.04),
                 R(0.115, 1.0, 0.20), R(0.09, 0.98, 0.265), R(0.07, 0.9, 0.275)],
                cap_start=True, cap_end=True)
        mb.build('Dryer body', mat(body), subsurf=2, viewport_subsurf=1)
        dm = MeshBuilder()
        slot = rounded_rect(0.16, 0.022, 0.010, 4, (0, -0.10))
        dm.loft([ring_xy(slot, 0.0065), ring_xy(slot, 0.0050)], cap_start=True)
        # side intake slots
        for side in (-1, 1):
            for i in range(9):
                z = 0.07 + 0.016 * i
                x = side * 0.1385
                dm.box((x - 0.002, -0.10, z), (x + 0.002, -0.03, z + 0.006))
        dm.build('Dryer vents', mat('plastic_dark'), 'FLAT')
        lm = MeshBuilder()
        b = rounded_rect(0.06, 0.012, 0.006, 4, (0, 0.17))
        lm.loft([ring_xz(b, -0.153), ring_xz(b, -0.160)], cap_end=True)
        lm.revolve([(0, 0), (0.006, 0), (0.006, 0.001), (0, 0.001)], 16, center=(0, -0.088, 0.005))
        lm.build('Dryer badge', mat('sensor_black'))
    return root


def paper_towel_dispenser():
    with group('Paper towel dispenser') as root:
        mb = MeshBuilder()
        mb.rounded_box((0.28, 0.11, 0.37), 0.025, (0, -0.055, 0.185), 5, 3)
        mb.build('Towel dispenser', mat('plastic_white'), 'HARD')
        wm = MeshBuilder()
        b = rounded_rect(0.22, 0.20, 0.02, 5, (0, 0.235))
        wm.loft([ring_xz(b, -0.1095), ring_xz(b, -0.112)], cap_end=True)
        wm.build('Window', mat('smoke_window'))
        km = MeshBuilder()
        km.revolve([(0, 0), (0.008, 0), (0.008, 0.004), (0, 0.004)], 20, axis='Y',
                   center=(0, -0.110, 0.345))
        km.build('Lock', mat('chrome'))
        pm = MeshBuilder()
        path = catmull_rom([(0, -0.07, 0.02), (0, -0.075, -0.03), (0, -0.09, -0.08)], 6)
        pm.sweep(path, [(0.0006, -0.11), (0.0006, 0.11), (-0.0006, 0.11), (-0.0006, -0.11)],
                 up=(0, 1, 0))
        pm.build('Towel sheet', mat('paper'), 'SMOOTH')
    return root


def jumbo_roll_dispenser():
    with group('Jumbo roll dispenser') as root:
        mb = MeshBuilder()
        mb.revolve([(0, 0), (0.145, 0), (0.15, 0.006), (0.15, 0.11), (0.143, 0.122), (0, 0.122)],
                   64, axis='Y', center=(0, 0, 0))
        mb.build('Roll dispenser', mat('plastic_grey'), subsurf=1)
        wm = MeshBuilder()
        wm.revolve([(0, 0), (0.06, 0), (0.06, 0.002), (0, 0.002)], 40, axis='Y',
                   center=(0, -0.121, 0.03))
        wm.build('Window', mat('smoke_window'))
        pm = MeshBuilder()
        path = catmull_rom([(0, -0.085, -0.135), (0, -0.09, -0.18), (0, -0.08, -0.25)], 6)
        pm.sweep(path, [(0.0006, -0.045), (0.0006, 0.045), (-0.0006, 0.045), (-0.0006, -0.045)],
                 up=(0, 1, 0))
        pm.build('Paper', mat('paper'), 'SMOOTH')
    return root


def waste_bin(metal='steel_brushed'):
    with group('Waste bin') as root:
        mb = MeshBuilder()
        mb.revolve([(0, 0.0), (0.150, 0.0), (0.154, 0.006), (0.170, 0.55), (0.174, 0.555),
                    (0.174, 0.565), (0.166, 0.565), (0.163, 0.55), (0.147, 0.012), (0, 0.012)], 64)
        mb.build('Bin', mat(metal))
        lm = MeshBuilder()
        lm.revolve([(0.163, 0.53), (0.177, 0.56), (0.179, 0.535), (0.180, 0.50)], 64)
        lm.build('Bin liner', mat('bin_liner'), 'SMOOTH')
    return root


def sanitary_bin():
    with group('Sanitary bin') as root:
        mb = MeshBuilder()
        mb.rounded_box((0.19, 0.36, 0.40), 0.03, (0, -0.18, 0.20), 4, 3)
        mb.build('Sanitary bin', mat('plastic_grey'), 'HARD')
        lm = MeshBuilder()
        lm.rounded_box((0.17, 0.20, 0.02), 0.008, (0, -0.24, 0.402), 3, 2)
        lm.build('Flap', mat('plastic_white'), 'HARD')
    return root


def coat_hook(metal='steel_brushed'):
    with group('Coat hook') as root:
        mb = MeshBuilder()
        mb.revolve([(0, 0), (0.018, 0), (0.018, 0.003), (0.012, 0.008), (0, 0.009)], 24, axis='Y')
        path = fillet_path([(0, -0.006, 0), (0, -0.045, 0), (0, -0.05, 0.03)], 0.015, 10)
        mb.tube(path, 0.006, 16)
        mb.sphere(0.0075, (0, -0.05, 0.03), 16, 8)
        mb.build('Hook', mat(metal))
    return root


def led_panel(size=0.6, power=26.0):
    """Recessed 600x600 LED panel, origin = ceiling plane (hangs -Z)."""
    with group('LED panel') as root:
        mb = MeshBuilder()
        outer = rounded_rect(size - 0.004, size - 0.004, 0.004, 2)
        inner = rounded_rect(size - 0.04, size - 0.04, 0.002, 2)
        mb.loft([ring_xy(outer, 0.0), ring_xy(outer, -0.008), ring_xy(inner, -0.008),
                 ring_xy(inner, -0.004)])
        mb.build('Panel frame', mat('plastic_white'), 'HARD')
        em = MeshBuilder()
        em.loft([ring_xy(inner, -0.0045), ring_xy(inner, -0.0046)], cap_end=True)
        em.build('Diffuser', mat('led_panel'), 'FLAT')
        ld = bpy.data.lights.new('LED panel', 'AREA')
        ld.shape = 'SQUARE'
        ld.size = size - 0.06
        ld.energy = power
        ld.color = (0.96, 0.98, 1.0)
        lo = bpy.data.objects.new('LED panel lamp', ld)
        lo.location = (0, 0, -0.012)
        link(lo)
    return root


def mirror_strip(length, height, t=0.006):
    """Long frameless mirror on a wall (x along length), origin bottom-left."""
    with group('Mirror') as root:
        mb = MeshBuilder()
        poly = rounded_rect(length, height, 0.004, 2, (length / 2, height / 2))
        mb.loft([ring_xz(poly, -0.004), ring_xz(poly, -0.004 - t)], cap_start=True)
        mb.build('Mirror edges', mat('glass'), 'FLAT')
        gm = MeshBuilder()
        gm.loft([ring_xz(poly, -0.004 - t + 0.0002), ring_xz(poly, -0.004 - t - 0.0001)],
                cap_end=True)
        gm.build('Mirror', mat('mirror'), 'FLAT')
        cm = MeshBuilder()
        n = max(2, int(length / 0.8) + 1)
        for i in range(n):
            x = 0.05 + (length - 0.1) * i / (n - 1)
            for z in (0.0, height):
                cm.revolve([(0, 0), (0.012, 0), (0.012, 0.012), (0.010, 0.014), (0, 0.014)], 24,
                           axis='Y', center=(x, 0, z))
        cm.build('Mirror clips', mat('chrome'))
    return root


# ---------------------------------------------------------------------------
# Vanity counter with integrated bowls
# ---------------------------------------------------------------------------

def _rect_ring_at_angles(x0, x1, y0, y1, cx, cy, angles):
    pts = []
    for a in angles:
        dx, dy = math.cos(a), math.sin(a)
        ts = []
        if abs(dx) > 1e-9:
            ts += [(x0 - cx) / dx, (x1 - cx) / dx]
        if abs(dy) > 1e-9:
            ts += [(y0 - cy) / dy, (y1 - cy) / dy]
        t = min(t for t in ts if t > 0)
        pts.append(Vector((cx + dx * t, cy + dy * t)))
    return pts


def vanity_counter(n=5, spacing=0.75, depth=0.55, top=0.85, end=0.20):
    """Solid-surface counter with ``n`` integrated oval bowls.

    Local frame: wall at y=0, front at -depth, length along +X from 0.
    Returns (root, tap_positions).
    """
    length = n * spacing + 2 * end
    taps = []
    with group('Vanity counter') as root:
        mb = MeshBuilder()
        front = -depth + 0.016
        a, b = 0.215, 0.155
        for i in range(n + 2):
            if i == 0:
                x0, x1 = 0.0, end
            elif i == n + 1:
                x0, x1 = end + n * spacing, length
            else:
                x0 = end + (i - 1) * spacing
                x1 = x0 + spacing
            if i in (0, n + 1):
                q = [mb.v((x0, front, top)), mb.v((x1, front, top)),
                     mb.v((x1, 0, top)), mb.v((x0, 0, top))]
                mb.f(q, smooth=False)
                continue
            cx, cy = (x0 + x1) / 2, -0.30
            corner = [math.atan2(y - cy, x - cx) for x, y in
                      ((x1, front), (x1, 0.0), (x0, 0.0), (x0, front))]
            uni = [-math.pi + 2 * math.pi * k / 48 for k in range(48)]
            angles = sorted(set(round(v, 9) for v in uni + corner))
            angles = [v for k, v in enumerate(angles)
                      if k == 0 or v - angles[k - 1] > 1e-4]
            rect = _rect_ring_at_angles(x0, x1, front, 0.0, cx, cy, angles)

            def ell(s, z, sy=1.0):
                out = []
                for ang in angles:
                    c, sn = math.cos(ang), math.sin(ang)
                    r = 1.0 / math.sqrt((c / a) ** 2 + (sn / (b * sy)) ** 2)
                    out.append(Vector((cx + r * s * c, cy + r * s * sn, z)))
                return out
            rings = [[Vector((p.x, p.y, top)) for p in rect], ell(1.06, top), ell(1.0, top),
                     ell(0.99, top - 0.004), ell(0.95, top - 0.04), ell(0.80, top - 0.10),
                     ell(0.50, top - 0.14), ell(0.17, top - 0.152, 1.35),
                     ell(0.15, top - 0.152, 1.35), ell(0.15, top - 0.175, 1.35)]
            mb.loft(rings, cap_end=True)
            taps.append(Vector((cx, -0.075, top)))
        mb.build('Counter top', mat('solid_surface'), subsurf=2, viewport_subsurf=1)

        am = MeshBuilder()
        am.rounded_box((length, 0.020, 0.13), 0.005, (length / 2, -depth + 0.010, top - 0.065), 3, 3)
        am.rounded_box((0.016, depth - 0.02, 0.13), 0.004, (0.008, -depth / 2 + 0.01, top - 0.065), 2, 2)
        am.rounded_box((0.016, depth - 0.02, 0.13), 0.004,
                       (length - 0.008, -depth / 2 + 0.01, top - 0.065), 2, 2)
        am.rounded_box((length, 0.014, 0.10), 0.004, (length / 2, -0.007, top + 0.05), 3, 2)
        am.build('Apron & upstand', mat('solid_surface'), 'HARD')

        dm = MeshBuilder()
        tm = MeshBuilder()
        for t in taps:
            cx = t.x
            z = top - 0.152
            dm.revolve([(0, z + 0.003), (0.024, z + 0.0025), (0.030, z + 0.001),
                        (0.030, z - 0.001), (0, z - 0.001)], 32, center=(cx, -0.30, 0))
            # chrome bottle trap into the wall
            tm.tube([(cx, -0.30, top - 0.18), (cx, -0.30, top - 0.30)], 0.016, 20)
            tm.revolve([(0, 0), (0.024, 0), (0.024, 0.11), (0.02, 0.12), (0, 0.12)], 24,
                       center=(cx, -0.30, top - 0.42))
            tm.tube(fillet_path([(cx, -0.30, top - 0.36), (cx, -0.15, top - 0.36),
                                 (cx, 0.0, top - 0.36)], 0.03, 6), 0.016, 20)
        dm.build('Basin wastes', mat('chrome'))
        tm.build('Bottle traps', mat('chrome'))
    return root, taps, length


# ---------------------------------------------------------------------------
# Toilet cubicles
# ---------------------------------------------------------------------------

def _leg(mb, x, y):
    mb.revolve([(0, 0), (0.030, 0), (0.030, 0.004), (0.012, 0.006), (0.012, 0.07),
                (0.020, 0.07), (0.020, 0.145), (0.0, 0.145)], 24, center=(x, y, 0))


def cubicle_row(n=4, bay=0.95, depth=1.55, height=2.0, pil=0.24, end_w=0.08,
                open_doors=None, gap=0.004):
    """Row of WC cubicles. Local frame: back wall y=0, fronts at y=-depth,
    bays along +X starting at x=0. Returns (root, bay_centres)."""
    open_doors = open_doors or {}
    t = 0.013
    z0 = 0.15
    total = n * bay + end_w
    centres = []
    with group('Cubicles') as root:
        pm = MeshBuilder()   # partitions & pilasters
        hw = MeshBuilder()   # aluminium/steel hardware
        for i in range(n + 1):
            x = i * bay
            if i < n:
                # side partition
                pm.rounded_box((t, depth - 0.03, height - z0), 0.003,
                               (x, -depth / 2 + 0.005, (height + z0) / 2), 2, 2)
                for z in (0.45, 1.75):
                    hw.rounded_box((0.03, 0.03, 0.05), 0.003, (x, -0.015, z), 2, 2)
                # pilaster on the hinge side of the bay
                pm.rounded_box((pil, t, height - z0), 0.003,
                               (x + pil / 2 - t / 2, -depth, (height + z0) / 2), 2, 2)
                _leg(hw, x + pil / 2 - t / 2, -depth)
                hw.rounded_box((0.03, 0.03, 0.05), 0.003, (x, -depth + 0.02, 0.45), 2, 2)
                hw.rounded_box((0.03, 0.03, 0.05), 0.003, (x, -depth + 0.02, 1.75), 2, 2)
                centres.append(x + bay / 2)
        # end pilaster against the side wall
        pm.rounded_box((end_w, t, height - z0), 0.003,
                       (n * bay + end_w / 2, -depth, (height + z0) / 2), 2, 2)
        _leg(hw, n * bay + end_w / 2, -depth)
        # headrail
        hw.rounded_box((total + 0.02, 0.026, 0.034), 0.006, (total / 2 - 0.01, -depth, height + 0.017),
                       3, 3)
        pm.build('Partitions & pilasters', mat('laminate_grey'), 'HARD')
        hw.build('Cubicle hardware', mat('aluminium'))

        for i in range(n):
            hinge_x = i * bay + pil - t / 2 + gap
            door_w = bay - pil - 2 * gap
            ang = math.radians(open_doors.get(i, 0.0))
            with group('Door %d' % (i + 1), location=(hinge_x, -depth, 0),
                       rotation=(0, 0, ang)):
                dmb = MeshBuilder()
                dmb.rounded_box((door_w, t, height - z0 - 0.02), 0.003,
                                (door_w / 2, 0, (height + z0) / 2 - 0.005), 2, 2)
                dmb.build('Door leaf', mat('laminate_oak'), 'HARD')
                hm = MeshBuilder()
                for z in (0.35, 1.10, 1.85):
                    hm.tube([(0.0, -0.0, z - 0.05), (0.0, -0.0, z + 0.05)], 0.009, 16)
                # indicator lock (outside) and turn (inside)
                lx = door_w - 0.055
                hm.revolve([(0, 0), (0.030, 0), (0.030, 0.004), (0.026, 0.008), (0, 0.008)],
                           32, axis='Y', center=(lx, -t / 2, 1.05))
                hm.revolve([(0, 0), (0.022, 0), (0.022, -0.006), (0, -0.006)], 24, axis='Y',
                           center=(lx, t / 2, 1.05))
                hm.rounded_box((0.010, 0.016, 0.032), 0.003, (lx, t / 2 + 0.012, 1.05), 2, 2)
                # pull handle
                hp = fillet_path([(lx, -t / 2, 0.92), (lx, -t / 2 - 0.045, 0.92),
                                  (lx, -t / 2 - 0.045, 0.78), (lx, -t / 2, 0.78)], 0.018, 8)
                hm.tube(hp, 0.0085, 16)
                # coat hook inside
                hm.revolve([(0, 0), (0.016, 0), (0.016, -0.004), (0, -0.004)], 20, axis='Y',
                           center=(door_w / 2, t / 2, 1.70))
                hm.tube(fillet_path([(door_w / 2, t / 2 + 0.004, 1.70),
                                     (door_w / 2, t / 2 + 0.045, 1.70),
                                     (door_w / 2, t / 2 + 0.05, 1.73)], 0.012, 8), 0.0055, 12)
                hm.build('Door hardware', mat('steel_brushed'))
                # occupancy window: red = engaged (closed), green = vacant (open)
                im = MeshBuilder()
                win = rounded_rect(0.026, 0.011, 0.004, 3, (lx, 1.062))
                im.prism(win, -t / 2 - 0.0084, -t / 2 - 0.0078, lambda u, v, w: Vector((u, w, v)))
                engaged = open_doors.get(i, 0.0) == 0.0
                im.build('Indicator', mat('indicator_red' if engaged else 'indicator_green'), 'FLAT')
    return root, centres, total
