"""Residential bathroom fixtures (modelled after the sage-green reference).

Convention for every fixture: built around the origin with the mounting wall
at local y = 0, the front facing -Y and the floor (or mounting height) at
z = 0 unless stated otherwise. Dimensions are in metres.
"""

import math

import bpy
from mathutils import Matrix, Vector

from .geo import (MeshBuilder, catmull_rom, fillet_path, group, link,
                  offset_poly, path_length, resample, ring_xy, ring_xz,
                  rounded_poly, rounded_rect, superellipse)
from .materials import mat


def se(w, df, db, ef, eb, cy, z, n=48, s=1.0, cx=0.0):
    """Horizontal superellipse ring: half-width w, front/back extents."""
    return ring_xy(superellipse(n, w, df, db, ef, eb, (cx, cy), s), z)


def _lerp_spec(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


# ---------------------------------------------------------------------------
# Close-coupled toilet
# ---------------------------------------------------------------------------

# (w, d_front, d_back, e_front, e_back, cy, z) -- pan, outside then bowl
PAN_CC = [
    (0.150, 0.250, 0.250, 4.0, 5.0, -0.360, 0.000),
    (0.152, 0.252, 0.252, 4.0, 5.0, -0.360, 0.008),
    (0.160, 0.272, 0.268, 4.2, 5.5, -0.355, 0.150),
    (0.172, 0.292, 0.288, 4.6, 6.0, -0.345, 0.300),
    (0.180, 0.300, 0.300, 5.0, 6.0, -0.340, 0.385),
    (0.179, 0.299, 0.299, 5.0, 6.0, -0.340, 0.396),
    (0.175, 0.295, 0.295, 5.0, 6.0, -0.340, 0.400),
    (0.130, 0.215, 0.165, 2.4, 2.6, -0.370, 0.400),
    (0.127, 0.211, 0.160, 2.4, 2.6, -0.370, 0.394),
    (0.120, 0.198, 0.145, 2.3, 2.5, -0.370, 0.360),
    (0.100, 0.165, 0.115, 2.2, 2.3, -0.370, 0.300),
    (0.075, 0.120, 0.080, 2.1, 2.2, -0.355, 0.240),
    (0.055, 0.070, 0.055, 2.0, 2.0, -0.330, 0.200),
    (0.045, 0.045, 0.045, 2.0, 2.0, -0.310, 0.170),
    (0.042, 0.042, 0.042, 2.0, 2.0, -0.300, 0.100),
]


def _water(specs, z, grow=1.03, n=48):
    """Flat water surface matching the bowl cross-section at height z.

    The bowl is the only part of a pan profile whose rings run downwards,
    so the first descending pair that brackets z is the one to interpolate.
    """
    for a, b in zip(specs, specs[1:]):
        if a[6] > b[6] and a[6] >= z >= b[6]:
            t = (a[6] - z) / (a[6] - b[6])
            w, df, db, ef, eb, cy, _ = _lerp_spec(a, b, t)
            mb = MeshBuilder()
            mb.loft([se(w, df, db, ef, eb, cy, z, n, grow * 0.5),
                     se(w, df, db, ef, eb, cy, z, n, grow)], cap_start=True)
            return mb.build('Water', mat('water'), 'SMOOTH')
    return None


def toilet_seat(cy, w, df, db, inner, z0, lid=True, color='ceramic', n=48):
    """Soft-close seat (+ optional closed lid) sitting on a pan rim at z0."""
    iw, idf, idb, icy = inner
    mb = MeshBuilder()

    def O(s, z):
        return se(w, df, db, 4.5, 6.0, cy, z, n, s)

    def I(s, z):
        return se(iw, idf, idb, 2.3, 2.5, icy, z, n, s)
    mb.loft([O(0.985, z0 + 0.003), O(1.0, z0 + 0.010), O(1.0, z0 + 0.019),
             O(0.988, z0 + 0.025), I(1.04, z0 + 0.025), I(1.0, z0 + 0.021),
             I(1.0, z0 + 0.008), I(1.03, z0 + 0.003)], cyclic=True)
    seat = mb.build('Seat', mat(color), subsurf=2)
    parts = [seat]
    # rubber buffers under the seat
    bm = MeshBuilder()
    for x, y in [(-0.12, cy - 0.12), (0.12, cy - 0.12), (-0.13, cy + 0.08), (0.13, cy + 0.08)]:
        bm.revolve([(0, z0), (0.008, z0), (0.008, z0 + 0.004), (0, z0 + 0.004)], 16,
                   center=(x, y, 0))
    parts.append(bm.build('Seat buffers', mat('rubber_black')))
    if lid:
        lm = MeshBuilder()
        zl = z0 + 0.027

        def L(s, z):
            return se(w * 1.005, df * 1.005, db, 4.5, 6.0, cy, z, n, s)
        lm.loft([L(0.96, zl), L(0.995, zl + 0.002), L(1.0, zl + 0.010),
                 L(0.996, zl + 0.021), L(0.97, zl + 0.0275), L(0.85, zl + 0.029)],
                cap_start=True, cap_end=True)
        parts.append(lm.build('Lid', mat(color), subsurf=2))
    # hinge covers
    hm = MeshBuilder()
    yb = cy + db - 0.006
    for x in (-0.105, 0.105):
        hm.revolve([(0, -0.018), (0.010, -0.018), (0.012, -0.015), (0.012, 0.015),
                    (0.010, 0.018), (0, 0.018)], 24, axis='X', center=(x, yb, z0 + 0.03))
        hm.revolve([(0, 0), (0.014, 0), (0.014, 0.006), (0, 0.006)], 24,
                   center=(x, yb + 0.012, z0 - 0.004))
    parts.append(hm.build('Seat hinges', mat('chrome')))
    return parts


def dual_flush_button(center, r=0.021, material='chrome'):
    cx, cy, cz = center
    mb = MeshBuilder()
    mb.revolve([(r + 0.0005, 0), (r + 0.0045, 0), (r + 0.0045, 0.002),
                (r + 0.0035, 0.0035), (r + 0.0005, 0.0035)], 48,
               center=center, closed_profile=True)
    gap = 0.0012
    for side in (-1, 1):
        pts = []
        for i in range(25):
            a = -math.pi / 2 + math.pi * i / 24
            pts.append((side * (gap + (r - 0.0004) * math.cos(a)), (r - 0.0004) * math.sin(a)))
        if side < 0:
            pts.reverse()
        poly = [(cx + u, cy + v) for u, v in pts]
        mb.prism(poly, cz - 0.003, cz + (0.0028 if side > 0 else 0.0022))
    return mb.build('Flush button', mat(material))


def toilet_close_coupled():
    with group('Toilet (close-coupled)') as root:
        mb = MeshBuilder()
        mb.loft([se(*s) for s in PAN_CC], cap_start=True, cap_end=True)
        mb.build('Pan', mat('ceramic'), subsurf=2, viewport_subsurf=1)
        _water(PAN_CC, 0.255)
        toilet_seat(-0.41, 0.176, 0.225, 0.225, (0.118, 0.17, 0.12, -0.385), 0.400)

        # cistern + lid
        cm = MeshBuilder()

        def C(s, z):
            return se(0.178, 0.085, 0.085, 8.0, 8.0, -0.090, z, 48, s)
        cm.loft([C(0.97, 0.402), C(1.0, 0.410), C(1.0, 0.776), C(0.99, 0.784)],
                cap_start=True, cap_end=True)
        cm.build('Cistern', mat('ceramic'), subsurf=2, viewport_subsurf=1)
        lm = MeshBuilder()

        def CL(s, z):
            return se(0.181, 0.0885, 0.0885, 8.0, 8.0, -0.090, z, 48, s)
        lm.loft([CL(0.975, 0.786), CL(1.0, 0.791), CL(1.0, 0.811), CL(0.985, 0.8175),
                 CL(0.9, 0.8185)], cap_start=True, cap_end=True)
        lm.build('Cistern lid', mat('ceramic'), subsurf=2, viewport_subsurf=1)
        dual_flush_button((0.0, -0.090, 0.8185))
        # bolts covers at the pan foot
        bm = MeshBuilder()
        for x in (-0.135, 0.135):
            bm.sphere(0.011, (x, -0.33, 0.06), 16, 8)
        bm.build('Bolt caps', mat('ceramic'), 'SMOOTH')
    return root


# ---------------------------------------------------------------------------
# Pedestal basin
# ---------------------------------------------------------------------------

def basin_pedestal():
    with group('Pedestal basin') as root:
        rim = 0.85
        outer = [
            (0.170, 0.130, 0.180, 2.5, 6.0, -0.190, rim - 0.170),
            (0.200, 0.170, 0.195, 2.5, 7.0, -0.200, rim - 0.150),
            (0.245, 0.215, 0.205, 2.6, 8.0, -0.205, rim - 0.100),
            (0.268, 0.235, 0.210, 2.6, 8.0, -0.210, rim - 0.050),
            (0.275, 0.240, 0.210, 2.6, 8.0, -0.210, rim - 0.015),
            (0.274, 0.239, 0.210, 2.6, 8.0, -0.210, rim - 0.003),
            (0.270, 0.235, 0.207, 2.6, 8.0, -0.210, rim),
        ]
        inner = [
            (0.245, 0.182, 0.128, 2.4, 2.4, -0.250, rim),
            (0.242, 0.178, 0.126, 2.4, 2.4, -0.250, rim - 0.005),
            (0.235, 0.170, 0.120, 2.3, 2.3, -0.250, rim - 0.030),
            (0.205, 0.145, 0.100, 2.2, 2.2, -0.252, rim - 0.080),
            (0.150, 0.100, 0.070, 2.1, 2.1, -0.254, rim - 0.120),
            (0.080, 0.060, 0.045, 2.0, 2.0, -0.255, rim - 0.145),
            (0.033, 0.033, 0.033, 2.0, 2.0, -0.255, rim - 0.150),
            (0.032, 0.032, 0.032, 2.0, 2.0, -0.255, rim - 0.175),
        ]
        mb = MeshBuilder()
        mb.loft([se(*s) for s in outer + inner], cap_start=True, cap_end=True)
        mb.build('Basin', mat('ceramic'), subsurf=2, viewport_subsurf=1)

        pm = MeshBuilder()

        def P(w, df, z):
            return se(w, df, 0.075, 2.6, 9.0, -0.075, z, 40)
        pm.loft([P(0.100, 0.085, 0.0), P(0.101, 0.086, 0.008), P(0.088, 0.072, 0.30),
                 P(0.086, 0.070, 0.42), P(0.100, 0.088, 0.66), P(0.104, 0.092, 0.69)],
                cap_start=True, cap_end=True)
        pm.build('Pedestal', mat('ceramic'), subsurf=2, viewport_subsurf=1)

        # click-clack waste
        wm = MeshBuilder()
        z = rim - 0.150
        wm.revolve([(0, z + 0.006), (0.020, z + 0.0055), (0.029, z + 0.004),
                    (0.031, z + 0.002), (0.031, z - 0.001), (0, z - 0.001)], 48,
                   center=(0, -0.255, 0))
        wm.build('Pop-up waste', mat('chrome'))
        # overflow ring on the front inner wall
        om = MeshBuilder()
        om.revolve([(0.006, 0), (0.010, 0), (0.010, 0.0015), (0.006, 0.0015)], 24,
                   axis='Y', center=(0, 0, 0), closed_profile=True)
        o = om.build('Overflow', mat('chrome'))
        o.location = (0.0, -0.402, rim - 0.045)
        o.rotation_euler = (math.radians(-28), 0, 0)
    return root


# ---------------------------------------------------------------------------
# Taps
# ---------------------------------------------------------------------------

def aerator(mb_dark, center, r, axis='Z'):
    mb_dark.revolve([(0, 0), (r, 0), (r, -0.002), (0, -0.002)], 20,
                    axis=axis, center=center)


def tap_basin_mixer(metal='brass'):
    """Tall single-lever basin mixer (as in the reference photo)."""
    with group('Basin mixer') as root:
        mb = MeshBuilder()
        mb.revolve([(0, 0), (0.027, 0), (0.027, 0.003), (0.0255, 0.0065), (0.0215, 0.008),
                    (0.0195, 0.0085), (0.0195, 0.166), (0.0188, 0.170), (0.0130, 0.171),
                    (0.0130, 0.186), (0.0122, 0.188), (0, 0.188)], 48)
        # spout with a slight fall
        mb.tube([(0, -0.012, 0.150), (0, -0.128, 0.143)], 0.0105, 32)
        # lever
        prof = rounded_rect(0.0075, 0.013, 0.0035, 4)
        path = [Vector((0, -0.004, 0.184)), Vector((0, 0.030, 0.192)), Vector((0, 0.075, 0.204))]
        mb.sweep(path, prof, up=(0, 0, 1), scale=lambda s: 1.0 - 0.25 * s)
        mb.build('Tap body', mat(metal))
        dm = MeshBuilder()
        aerator(dm, (0, -0.118, 0.1345), 0.0075)
        dm.build('Aerator', mat('rubber_black'))
    return root


def bath_filler_wall(metal='brass'):
    """Wall-mounted bath filler: two knurled heads on a bar with a spout."""
    with group('Bath filler') as root:
        mb = MeshBuilder()
        for x in (-0.08, 0.08):
            mb.revolve([(0, 0), (0.030, 0), (0.030, 0.004), (0.026, 0.010), (0.014, 0.012),
                        (0.012, 0.012), (0.012, 0.050), (0, 0.050)], 40, axis='Y',
                       center=(x, 0, 0))
        mb.revolve([(0, -0.11), (0.020, -0.11), (0.022, -0.107), (0.022, 0.107),
                    (0.020, 0.11), (0, 0.11)], 40, axis='X', center=(0, -0.065, 0))
        for sgn in (-1, 1):
            prof = [(0, 0.11 * sgn), (0.024, 0.11 * sgn), (0.026, 0.114 * sgn),
                    (0.026, 0.146 * sgn), (0.023, 0.150 * sgn), (0, 0.150 * sgn)]
            if sgn < 0:
                prof.reverse()
            mb.revolve(prof, 64, axis='X', center=(0, -0.065, 0),
                       ribs=(24, 0.07, 1, 4))
        path = fillet_path([(0, -0.065, 0), (0, -0.175, 0), (0, -0.20, -0.045)], 0.035, 10)
        mb.tube(path, lambda t: 0.015 - 0.002 * t, 32)
        mb.build('Bath filler body', mat(metal))
        dm = MeshBuilder()
        aerator(dm, (0, -0.1985, -0.045), 0.010)
        dm.build('Aerator', mat('rubber_black'))
    return root


# ---------------------------------------------------------------------------
# Thermostatic shower
# ---------------------------------------------------------------------------

def _nozzle_disc(mb, center, radius, normal_axis, rings):
    """Silicone nozzle nubs on a shower face (normal_axis is 'Z-' or 'Y-')."""
    cx, cy, cz = center
    nubs = [(0.0, 0.0)]
    for k in range(1, rings + 1):
        rr = radius * k / (rings + 0.6)
        cnt = 6 * k
        for i in range(cnt):
            a = 2 * math.pi * (i + 0.5 * (k % 2)) / cnt
            nubs.append((rr * math.cos(a), rr * math.sin(a)))
    for u, v in nubs:
        if normal_axis == 'Z-':
            mb.revolve([(0.0022, 0.0), (0.0019, -0.0022), (0.0, -0.0026)], 8,
                       center=(cx + u, cy + v, cz))
        else:
            mb.revolve([(0.0018, 0.0), (0.0015, 0.0020), (0.0, 0.0024)], 8, axis='Y',
                       center=(cx + u, cy, cz + v))


def handset(metal='brass'):
    """Shower handset in its own frame: handle along +Z from the hose nut at
    z=0, spray face pointing -Y at the top."""
    parts = []
    mb = MeshBuilder()
    mb.revolve([(0, -0.012), (0.009, -0.012), (0.010, -0.006), (0.012, 0.0), (0.0135, 0.010),
                (0.0150, 0.120), (0.0170, 0.160), (0.0170, 0.170), (0, 0.172)], 32)
    mb.revolve([(0, 0.0), (0.050, 0.0), (0.052, 0.003), (0.052, 0.017), (0.048, 0.022),
                (0.020, 0.024), (0, 0.024)], 48, axis='Y', center=(0, 0.012, 0.215))
    parts.append(mb.build('Handset', mat(metal)))
    nm = MeshBuilder()
    nm.revolve([(0, 0), (0.044, 0), (0.044, 0.0006), (0, 0.0006)], 48, axis='Y',
               center=(0, 0.0122, 0.215))
    _nozzle_disc(nm, (0, 0.0116, 0.215), 0.036, 'Y-', 3)
    parts.append(nm.build('Handset face', mat('rubber_black')))
    return parts


def shower_thermostatic(metal='brass', valve_z=1.10, top_z=2.06, arm=0.33):
    """Exposed bar valve + rigid riser + overhead head + handset on hose."""
    yb = -0.075
    M = mat(metal)
    with group('Thermostatic shower') as root:
        mb = MeshBuilder()
        # wall elbows
        for x in (-0.075, 0.075):
            mb.revolve([(0, 0), (0.032, 0), (0.032, 0.004), (0.029, 0.011), (0.015, 0.013),
                        (0.0135, 0.013), (0.0135, -yb - 0.018), (0, -yb - 0.018)], 40,
                       axis='Y', center=(x, 0, valve_z))
            mb.revolve([(0, 0.035), (0.018, 0.035), (0.018, 0.050), (0, 0.050)], 6, axis='Y',
                       center=(x, 0, valve_z))  # hex union nut
        # bar body with decorative grooves
        prof = [(0, -0.15), (0.027, -0.15), (0.030, -0.147)]
        for g in (-0.122, 0.122):
            prof += [(0.030, g - 0.002), (0.0285, g - 0.001), (0.0285, g + 0.001), (0.030, g + 0.002)]
        prof += [(0.030, 0.147), (0.027, 0.15), (0, 0.15)]
        mb.revolve(prof, 48, axis='X', center=(0, yb, valve_z))
        # knurled control knobs
        for sgn in (-1, 1):
            p = [(0, 0.150), (0.026, 0.150), (0.030, 0.153), (0.033, 0.158), (0.033, 0.192),
                 (0.031, 0.196), (0, 0.197)]
            p = [(r, h * sgn) for r, h in p]
            if sgn < 0:
                p.reverse()
            mb.revolve(p, 72, axis='X', center=(0, yb, valve_z), ribs=(36, 0.06, 2, 5))
        # outlet nuts top & bottom
        mb.revolve([(0, 0.024), (0.016, 0.024), (0.016, 0.050), (0.013, 0.053), (0, 0.053)], 6,
                   center=(0, yb, valve_z))
        mb.revolve([(0, -0.024), (0.015, -0.024), (0.015, -0.050), (0, -0.050)], 6,
                   center=(0, yb, valve_z))
        # riser + swan arm
        path = fillet_path([(0, yb, valve_z + 0.05), (0, yb, top_z), (0, yb - arm, top_z)], 0.09, 16)
        mb.tube(path, 0.0115, 32)
        hx, hy = 0.0, yb - arm
        mb.sphere(0.0165, (hx, hy, top_z - 0.004), 24, 12)
        mb.tube([(hx, hy, top_z - 0.01), (hx, hy, top_z - 0.040)], 0.0085, 24)
        # overhead head
        hz = top_z - 0.060
        mb.revolve([(0, 0), (0.112, 0), (0.120, 0.004), (0.120, 0.010), (0.112, 0.014),
                    (0.030, 0.020), (0, 0.021)], 96, center=(hx, hy, hz))
        # riser wall bracket
        bz = 1.80
        mb.revolve([(0, 0), (0.024, 0), (0.024, 0.004), (0.020, 0.010), (0.009, 0.012),
                    (0.008, 0.012), (0.008, -yb - 0.012), (0, -yb - 0.012)], 32,
                   axis='Y', center=(0, 0, bz))
        mb.revolve([(0.0118, -0.011), (0.0175, -0.011), (0.0175, 0.011), (0.0118, 0.011)], 40,
                   center=(0, yb, bz), closed_profile=True)
        # slide holder and handset
        sz = 1.463
        mb.revolve([(0.0118, -0.011), (0.0175, -0.011), (0.0175, 0.011), (0.0118, 0.011)], 40,
                   center=(0, yb, sz), closed_profile=True)
        Mh = (Matrix.Translation((0, yb - 0.055, 1.40)) @ Matrix.Rotation(0.35, 4, 'X'))
        cup_c = Mh @ Vector((0, 0, 0.0675))
        mb.tube([(0, yb - 0.016, sz), (0, cup_c.y + 0.012, sz)], 0.0065, 16)
        k = mb.mark()
        mb.revolve([(0.0165, -0.017), (0.0205, -0.017), (0.0205, 0.017), (0.0165, 0.017)], 40,
                   closed_profile=True)
        mb.transform(Mh @ Matrix.Translation((0, 0, 0.0675)), k)
        mb.build('Shower body', M)

        nm = MeshBuilder()
        nm.revolve([(0, 0), (0.104, 0), (0.104, -0.0006), (0, -0.0006)], 64,
                   center=(hx, hy, hz))
        _nozzle_disc(nm, (hx, hy, hz - 0.0005), 0.095, 'Z-', 6)
        nm.build('Head face', mat('rubber_black'))

        hs = handset(metal)
        for o in hs:
            o.matrix_basis = Mh @ o.matrix_basis

        # ribbed metal hose from the valve outlet up to the handset
        start = Vector((0, yb, valve_z - 0.050))
        end = Mh @ Vector((0, 0, -0.012))
        down = (Mh.to_3x3() @ Vector((0, 0, -1))).normalized()
        ctrl = [start, start + Vector((0.0, -0.005, -0.16)), Vector((0.07, yb - 0.08, 0.80)),
                Vector((0.12, yb - 0.11, 0.76)), Vector((0.12, yb - 0.10, 0.92)),
                end + down * 0.22 + Vector((0.03, 0, 0)), end + down * 0.06, end]
        path = resample(catmull_rom(ctrl, 24), 0.0016)
        nrib = path_length(path) / 0.0048

        def rib(t):
            return 0.0072 + 0.0007 * math.cos(2 * math.pi * nrib * t)
        hm = MeshBuilder()
        hm.tube(path, rib, 14)
        # conical hose ferrules
        for p, d in ((start, Vector((0, 0, -1))), (end, -down)):
            ferrule = MeshBuilder()
            ferrule.revolve([(0, 0), (0.0105, 0), (0.0105, 0.012), (0.0085, 0.030), (0, 0.030)], 6)
            rot = Vector((0, 0, 1)).rotation_difference(d).to_matrix().to_4x4()
            hm.merge(ferrule, Matrix.Translation(p) @ rot)
        hm.build('Shower hose', M)
    return root


# ---------------------------------------------------------------------------
# L-shaped shower bath (right hand) + screen
# ---------------------------------------------------------------------------

BATH_L = [(0.0, 0.0), (-0.85, 0.0), (-0.85, -0.78), (-0.70, -0.98), (-0.70, -1.70), (0.0, -1.70)]
# Convex floor outline with the same corner count as BATH_L: capping the
# concave L directly gives a subdivided n-gon with folded (striped) shading.
BATH_FLOOR = [(-0.22, -0.22), (-0.49, -0.22), (-0.505, -0.62), (-0.505, -1.08),
              (-0.49, -1.48), (-0.22, -1.48)]


def _bath_ring(off, radii, z, seg=6):
    return ring_xy(rounded_poly(offset_poly(BATH_L, off), radii, seg), z)


def bath_l_shaped(rim=0.56):
    """Origin = the wall corner at the tap end; the bath runs along -X/-Y."""
    with group('L-shaped shower bath') as root:
        outer_r = [0.012, 0.03, 0.12, 0.12, 0.03, 0.012]

        def inner_r(k):
            return [0.10 + k, 0.13 + k, 0.10 + k, 0.16 + k, 0.20 + k, 0.16 + k]
        rings = [
            _bath_ring(0.015, outer_r, rim - 0.025),
            _bath_ring(0.000, outer_r, rim - 0.025),
            _bath_ring(0.000, outer_r, rim - 0.006),
            _bath_ring(0.004, outer_r, rim - 0.001),
            _bath_ring(0.010, outer_r, rim),
            _bath_ring(0.065, inner_r(0.0), rim),
            _bath_ring(0.071, inner_r(0.0), rim - 0.006),
            _bath_ring(0.080, inner_r(0.005), rim - 0.06),
            _bath_ring(0.100, inner_r(0.010), rim - 0.21),
            _bath_ring(0.130, inner_r(0.015), rim - 0.34),
            _bath_ring(0.165, inner_r(0.020), rim - 0.395),
            _bath_ring(0.190, inner_r(0.020), rim - 0.410),
            ring_xy(rounded_poly(BATH_FLOOR, [0.08, 0.10, 0.15, 0.15, 0.10, 0.08], 6), rim - 0.410),
        ]
        mb = MeshBuilder()
        mb.loft(rings, cap_end=True)
        mb.build('Bath tub', mat('acrylic'), subsurf=2, viewport_subsurf=1)

        # L-shaped front panel with a recessed plinth
        pr = [0.0, 0.02, 0.12, 0.12, 0.02, 0.0]
        pm = MeshBuilder()
        pm.loft([_bath_ring(0.045, pr, 0.0), _bath_ring(0.045, pr, 0.07),
                 _bath_ring(0.014, pr, 0.072), _bath_ring(0.012, pr, 0.076),
                 _bath_ring(0.012, pr, rim - 0.027), _bath_ring(0.02, pr, rim - 0.027)])
        pm.build('Bath panel', mat('acrylic'), 'HARD')

        # waste + overflow
        wm = MeshBuilder()
        fz = rim - 0.410
        wm.revolve([(0, fz + 0.005), (0.028, fz + 0.004), (0.036, fz + 0.0015),
                    (0.037, fz - 0.001), (0, fz - 0.001)], 48, center=(-0.42, -0.30, 0))
        ov = MeshBuilder()
        ov.revolve([(0, 0.0), (0.034, 0.0), (0.034, 0.004), (0.030, 0.008), (0, 0.010)], 48,
                   axis='Y')
        wm.merge(ov, Matrix.Translation((-0.42, -0.097, rim - 0.12)) @
                 Matrix.Rotation(math.radians(-8), 4, 'X'))
        wm.build('Bath waste & overflow', mat('brass'))
    return root


def bath_screen(width=0.80, height=1.45, metal='brass'):
    """Fixed bath screen: glass in the local YZ plane, wall at y=0."""
    with group('Bath screen') as root:
        t = 0.008
        poly = [(-0.012, 0.004), (-0.012, height), (-width, height), (-width, 0.004)]
        rings = [[Vector((w, u, v)) for u, v in poly] for w in (-t / 2, t / 2)]
        # Polished edges are solid green-tinted glass. The large faces use
        # thin glass so the screen doesn't cast a black shadow into the bath;
        # it is a single mid-plane face because two parallel thin-glass faces
        # render black in Cycles 4.2.
        em = MeshBuilder()
        em.loft(rings)
        em.build('Glass edges', mat('glass'), 'FLAT')
        gm = MeshBuilder()
        gm.polygon([Vector((0.0, u, v)) for u, v in poly])
        gm.build('Glass', mat('glass_thin'), 'FLAT')
        mb = MeshBuilder()
        # wall channel (U profile) and free-edge stiffener profile
        mb.rounded_box((0.024, 0.026, height + 0.01), 0.002, (0, -0.013, height / 2 + 0.002), 2, 2)
        mb.rounded_box((0.016, 0.014, height - 0.004), 0.002,
                       (0, -width - 0.002, height / 2 + 0.004), 2, 2)
        # top cap of the stiffener
        mb.rounded_box((0.018, 0.020, 0.010), 0.002, (0, -width - 0.002, height + 0.006), 2, 2)
        mb.build('Screen profiles', mat(metal))
        sm = MeshBuilder()
        sm.rounded_box((0.014, width - 0.03, 0.010), 0.003, (0, -width / 2 - 0.006, 0.0), 2, 2)
        sm.build('Seal', mat('glass_frosted'))
    return root


# ---------------------------------------------------------------------------
# Mirror with brass frame & LED backlight
# ---------------------------------------------------------------------------

def mirror_led(w=0.60, h=0.80, r=0.075, metal='brass', standoff=0.03):
    with group('LED mirror') as root:
        def RR(k, y):
            return ring_xz(rounded_rect(w - 2 * k, h - 2 * k, max(r - k, 0.004), 10), y)
        y0 = -standoff
        fm = MeshBuilder()
        fm.loft([RR(0.004, y0 - 0.001), RR(0.0, y0 - 0.004), RR(0.0, y0 - 0.022),
                 RR(0.0025, y0 - 0.025), RR(0.0125, y0 - 0.025), RR(0.0145, y0 - 0.020),
                 RR(0.0145, y0 - 0.004)], cyclic=True)
        fm.build('Mirror frame', mat(metal), 'HARD')
        gm = MeshBuilder()
        gm.loft([RR(0.0125, y0 - 0.008), RR(0.0125, y0 - 0.0185)], cap_start=True, cap_end=True)
        gm.build('Mirror glass', mat('mirror'), 'FLAT')
        # hidden carrier + LED band shining on the wall
        bm = MeshBuilder()
        bm.loft([RR(0.06, 0.0), RR(0.06, y0 - 0.002)], cap_start=True, cap_end=True)
        bm.build('Mirror carrier', mat('plastic_dark'), 'FLAT')
        lm = MeshBuilder()
        lm.loft([RR(0.058, -0.004), RR(0.058, y0 + 0.002)])
        lm.build('LED strip', mat('led_warm'), 'FLAT')
        # touch sensor icons
        im = MeshBuilder()
        for x in (-0.013, 0.013):
            im.revolve([(0, 0), (0.0045, 0), (0.0045, 0.0002), (0, 0.0002)], 20, axis='Y',
                       center=(x, y0 - 0.0186, -h / 2 + 0.05))
        im.build('Touch icons', mat('touch_icon'), 'FLAT')
    return root


# ---------------------------------------------------------------------------
# Accessories
# ---------------------------------------------------------------------------

def toilet_roll_holder(metal='brass'):
    """Wall plate at origin; arm runs to +X."""
    with group('Toilet roll holder') as root:
        mb = MeshBuilder()
        mb.revolve([(0, 0), (0.026, 0), (0.026, 0.004), (0.023, 0.009), (0.010, 0.011),
                    (0, 0.011)], 40, axis='Y')
        path = fillet_path([(0, -0.008, 0), (0, -0.045, 0), (0.135, -0.045, 0)], 0.022, 12)
        mb.tube(path, 0.0065, 24)
        mb.sphere(0.0075, (0.137, -0.045, 0), 20, 10)
        mb.build('Holder', mat(metal))
        # paper roll hanging over the front
        rm = MeshBuilder()
        x0, x1, ri, ro = 0.018, 0.116, 0.021, 0.056
        rm.revolve([(ri, x0), (ro - 0.002, x0), (ro, x0 + 0.002), (ro, x1 - 0.002),
                    (ro - 0.002, x1), (ri, x1)], 48, axis='X', center=(0, -0.045, -0.006),
                   closed_profile=True)
        # loose sheet: tangent from the front of the roll, falling with a slight curl
        ys, zs = -0.045 - ro, -0.006
        sheet = [Vector((0, ys, zs)), Vector((0, ys - 0.004, zs - 0.06)),
                 Vector((0, ys - 0.002, zs - 0.10))]
        prof = [(0.0004, -0.047), (0.0004, 0.047), (-0.0004, 0.047), (-0.0004, -0.047)]
        k = rm.mark()
        rm.sweep(catmull_rom(sheet, 8), prof, up=(0, 1, 0))
        rm.transform(Matrix.Translation((0.067, 0, 0)), k)
        rm.build('Toilet roll', mat('paper'), 'SMOOTH')
        cm = MeshBuilder()
        cm.revolve([(ri - 0.001, x0 - 0.0005), (ri + 0.0005, x0 - 0.0005),
                    (ri + 0.0005, x1 + 0.0005), (ri - 0.001, x1 + 0.0005)], 32, axis='X',
                   center=(0, -0.045, -0.006), closed_profile=True)
        cm.build('Roll core', mat('cardboard'))
    return root


def toilet_brush(metal='brass'):
    """Floor standing brush holder."""
    with group('Toilet brush') as root:
        mb = MeshBuilder()
        mb.revolve([(0, 0), (0.055, 0), (0.055, 0.004), (0.050, 0.008), (0.044, 0.008),
                    (0.044, 0.155), (0.046, 0.158), (0.046, 0.162), (0.041, 0.162),
                    (0.041, 0.015), (0, 0.015)], 48)
        mb.tube([(0, 0, 0.12), (0, 0, 0.42)], 0.0055, 16)
        mb.sphere(0.011, (0, 0, 0.425), 20, 10)
        mb.build('Brush holder', mat(metal))
    return root


def soap_pump(glass='glass_green', pump='plastic_dark', scale=1.0, name='Soap pump'):
    with group(name) as root:
        s = scale
        bm = MeshBuilder()
        bm.revolve([(0, 0), (0.030 * s, 0), (0.032 * s, 0.003 * s), (0.032 * s, 0.10 * s),
                    (0.030 * s, 0.112 * s), (0.017 * s, 0.124 * s), (0.0125 * s, 0.128 * s),
                    (0.0125 * s, 0.135 * s), (0, 0.135 * s)], 48)
        bm.build('Bottle', mat(glass), 'SMOOTH', subsurf=1)
        pm = MeshBuilder()
        z = 0.133 * s
        pm.revolve([(0, z), (0.0145 * s, z), (0.0145 * s, z + 0.016 * s),
                    (0.010 * s, z + 0.019 * s), (0, z + 0.019 * s)], 48, ribs=(30, 0.05, 1, 2))
        pm.tube([(0, 0, z + 0.018 * s), (0, 0, z + 0.035 * s)], 0.0045 * s, 16)
        pm.rounded_box((0.020 * s, 0.026 * s, 0.013 * s), 0.004 * s,
                       (0, -0.004 * s, z + 0.040 * s), 3, 2)
        pm.tube([(0, -0.012 * s, z + 0.041 * s), (0, -0.040 * s, z + 0.039 * s)],
                0.0042 * s, 16)
        pm.build('Pump', mat(pump))
    return root


def bottle(r=0.028, h=0.17, neck=0.012, glass='glass_green', cap='plastic_dark', name='Bottle'):
    with group(name) as root:
        bm = MeshBuilder()
        bm.revolve([(0, 0), (r, 0), (r * 1.03, 0.004), (r * 1.03, h * 0.72), (r * 0.8, h * 0.82),
                    (neck * 1.1, h * 0.92), (neck, h * 0.95), (neck, h), (0, h)], 40)
        bm.build('Glass', mat(glass), 'SMOOTH', subsurf=1)
        cm = MeshBuilder()
        cm.revolve([(0, h - 0.002), (neck * 1.25, h - 0.002), (neck * 1.25, h + 0.022),
                    (neck * 1.1, h + 0.025), (0, h + 0.025)], 32, ribs=(24, 0.04, 1, 2))
        cm.build('Cap', mat(cap))
    return root


def jar(r=0.04, h=0.07, name='Jar'):
    with group(name) as root:
        bm = MeshBuilder()
        bm.revolve([(0, 0), (r, 0), (r * 1.02, 0.004), (r * 1.02, h), (0, h)], 40)
        bm.build('Jar', mat('ceramic_matte'), 'SMOOTH', subsurf=1)
        cm = MeshBuilder()
        cm.revolve([(0, h), (r * 1.04, h), (r * 1.04, h + 0.018), (r * 0.98, h + 0.021),
                    (0, h + 0.021)], 40)
        cm.build('Lid', mat('brass'))
    return root


def tumbler_with_brushes():
    with group('Tumbler') as root:
        gm = MeshBuilder()
        gm.revolve([(0, 0), (0.033, 0), (0.035, 0.10), (0.032, 0.10), (0.031, 0.008), (0, 0.008)],
                   40)
        gm.build('Tumbler', mat('glass_frosted'), 'SMOOTH', subsurf=1)
        bm = MeshBuilder()
        hm = MeshBuilder()
        for i, (ang, col) in enumerate(((0.18, 0), (-0.22, 1))):
            k = bm.mark()
            bm.rounded_box((0.010, 0.006, 0.17), 0.0028, (0, 0, 0.085), 3, 2)
            m = (Matrix.Translation((0.008 * (1 if i else -1), 0, 0.01)) @
                 Matrix.Rotation(ang, 4, 'Y'))
            bm.transform(m, k)
            k2 = hm.mark()
            hm.rounded_box((0.011, 0.012, 0.026), 0.002, (0, -0.007, 0.165), 2, 2)
            hm.transform(m, k2)
        bm.build('Brush handles', mat('plastic_white'))
        hm.build('Bristles', mat('ceramic_matte'))
    return root


def art_print(w=0.32, h=0.42, depth=0.022):
    """Framed print. Origin at the bottom-back edge of the frame."""
    with group('Framed print') as root:
        def RR(k, y, r=0.0015):
            return ring_xz(rounded_rect(w - 2 * k, h - 2 * k, r, 2, (0, h / 2)), y)
        fm = MeshBuilder()
        fm.loft([RR(0.0, 0.0), RR(0.0, -depth + 0.002), RR(0.002, -depth), RR(0.018, -depth),
                 RR(0.020, -depth + 0.003), RR(0.020, -0.004)], cyclic=True)
        fm.build('Frame', mat('frame_white'), 'HARD')
        mm = MeshBuilder()
        mm.loft([RR(0.020, -0.006), RR(0.020, -0.008)], cap_start=True, cap_end=True)
        mm.build('Mount board', mat('paper'), 'FLAT')
        pm = MeshBuilder()
        pw, ph = w - 0.09, h - 0.10
        poly = [(pw / 2, h / 2 - ph / 2), (pw / 2, h / 2 + ph / 2),
                (-pw / 2, h / 2 + ph / 2), (-pw / 2, h / 2 - ph / 2)]
        pm.loft([ring_xz(poly, -0.0082), ring_xz(poly, -0.0084)], cap_start=True, cap_end=True)
        pm.build('Print', mat('art_print'), 'FLAT')
        gm = MeshBuilder()
        gm.polygon(RR(0.017, -depth + 0.007))
        gm.build('Frame glass', mat('glass_thin'), 'FLAT')
    return root


def towel_radiator(w=0.50, h=1.20, metal='brass', towel=True):
    """Ladder towel warmer; origin on the wall at the floor below its centre."""
    with group('Towel radiator') as root:
        yb = -0.06
        z0 = 0.18
        mb = MeshBuilder()
        for x in (-w / 2, w / 2):
            mb.tube([(x, yb, z0), (x, yb, z0 + h)], 0.0145, 24)
            mb.sphere(0.0145, (x, yb, z0 + h), 24, 8)
            mb.sphere(0.0145, (x, yb, z0), 24, 8)
            for bz in (z0 + 0.15, z0 + h - 0.15):
                mb.revolve([(0, 0), (0.022, 0), (0.022, 0.004), (0.010, 0.008), (0.0085, 0.008),
                            (0.0085, -yb - 0.012), (0, -yb - 0.012)], 24, axis='Y',
                           center=(x, 0, bz))
            # angled valves into the floor
            mb.tube(fillet_path([(x, yb, z0 - 0.002), (x, yb, z0 - 0.05), (x, yb + 0.03, z0 - 0.07),
                                 (x, yb + 0.03, 0.0)], 0.02, 8), 0.010, 20)
            mb.revolve([(0, 0), (0.016, 0), (0.016, 0.04), (0.014, 0.045), (0, 0.045)], 6,
                       axis='Y', center=(x, yb - 0.01, z0 - 0.05))
        bars = 11
        bar_z = []
        for i in range(bars):
            bz = z0 + 0.06 + (h - 0.12) * i / (bars - 1)
            if i in (3, 7):
                continue  # gaps for towels
            bar_z.append(bz)
            mb.tube([(-w / 2 + 0.01, yb, bz), (w / 2 - 0.01, yb, bz)], 0.011, 20)
        mb.build('Radiator', mat(metal))
        if towel:
            tb = bar_z[-2]
            path = catmull_rom([(0, yb - 0.017, tb - 0.46), (0, yb - 0.021, tb - 0.22),
                                (0, yb - 0.016, tb - 0.01), (0, yb, tb + 0.016),
                                (0, yb + 0.016, tb - 0.01), (0, yb + 0.019, tb - 0.20),
                                (0, yb + 0.017, tb - 0.38)], 10)
            prof = []
            n = 24
            for i in range(n + 1):
                u = -0.22 + 0.44 * i / n
                prof.append((0.005 + 0.0015 * math.sin(i * 1.3), u))
            for i in range(n, -1, -1):
                u = -0.22 + 0.44 * i / n
                prof.append((-0.005 + 0.0015 * math.sin(i * 1.3), u))
            tm = MeshBuilder()
            tm.sweep(path, prof, up=(0, 1, 0))
            tm.build('Towel', mat('towel_cream'), subsurf=1)
    return root


def downlight(trim='brass', power=14.0):
    """Recessed ceiling downlight. Origin = ceiling surface (fitting hangs -Z)."""
    with group('Downlight') as root:
        mb = MeshBuilder()
        mb.revolve([(0.034, 0.0), (0.046, 0.0), (0.046, -0.002), (0.044, -0.004),
                    (0.034, -0.004)], 48, closed_profile=True)
        mb.build('Trim', mat(trim))
        rm = MeshBuilder()
        rm.revolve([(0.034, -0.004), (0.030, 0.012), (0.019, 0.030), (0, 0.030)], 48)
        rm.build('Reflector', mat('plastic_white'))
        em = MeshBuilder()
        em.disc(0.017, 32, (0, 0, 0.0285))
        em.build('Emitter', mat('led_downlight'), 'FLAT')
        ld = bpy.data.lights.new('Downlight', 'SPOT')
        ld.energy = power
        ld.color = (1.0, 0.88, 0.76)
        ld.spot_size = math.radians(115)
        ld.spot_blend = 0.65
        ld.shadow_soft_size = 0.03
        lo = bpy.data.objects.new('Downlight lamp', ld)
        lo.location = (0, 0, -0.006)
        link(lo)
    return root


def bath_mat(w=0.50, d=0.80):
    with group('Bath mat') as root:
        mb = MeshBuilder()
        mb.rounded_box((w, d, 0.014), 0.007, (0, 0, 0.007), 6, 3)
        mb.build('Bath mat', mat('mat_sage'), 'SMOOTH')
    return root


def door_panel(w=0.826, h=2.04, metal='brass'):
    """Shaker door on the wall plane y=0 opening to -Y, origin bottom centre."""
    with group('Door') as root:
        t = 0.044
        mb = MeshBuilder()
        mb.rounded_box((w, t, h), 0.003, (0, -t / 2 - 0.005, h / 2), 2, 2)
        # applied mouldings on the room face
        for (z0, z1) in ((0.12, 0.90), (1.02, h - 0.12)):
            for (a, b) in (((-w / 2 + 0.11, z0), (w / 2 - 0.11, z0 + 0.016)),
                           ((-w / 2 + 0.11, z1 - 0.016), (w / 2 - 0.11, z1)),
                           ((-w / 2 + 0.11, z0), (-w / 2 + 0.126, z1)),
                           ((w / 2 - 0.126, z0), (w / 2 - 0.11, z1))):
                mb.rounded_box((b[0] - a[0], 0.006, b[1] - a[1]), 0.002,
                               ((a[0] + b[0]) / 2, -t - 0.005 - 0.003, (a[1] + b[1]) / 2), 2, 1)
        # architrave
        aw = 0.07
        for x in (-w / 2 - aw / 2 - 0.004, w / 2 + aw / 2 + 0.004):
            mb.rounded_box((aw, 0.018, h + aw + 0.004), 0.004, (x, -0.009, (h + aw) / 2), 3, 2)
        mb.rounded_box((w + 2 * aw + 0.008, 0.018, aw), 0.004, (0, -0.009, h + 0.004 + aw / 2), 3, 2)
        mb.build('Door leaf', mat('door_paint'), 'HARD')
        hm = MeshBuilder()
        hx = w / 2 - 0.065
        yf = -t - 0.005
        hm.revolve([(0, 0), (0.026, 0), (0.026, 0.003), (0.021, 0.009), (0.011, 0.012),
                    (0, 0.012)], 40, axis='Y', center=(hx, yf, 1.0))
        lever = fillet_path([(hx, yf - 0.010, 1.0), (hx, yf - 0.058, 1.0), (hx - 0.13, yf - 0.058, 1.0)],
                            0.025, 12)
        hm.tube(lever, lambda s: 0.0095 - 0.002 * s, 24)
        hm.revolve([(0, 0), (0.016, 0), (0.016, 0.004), (0.012, 0.007), (0, 0.007)], 32,
                   axis='Y', center=(hx, yf, 0.93))
        hm.rounded_box((0.006, 0.014, 0.020), 0.0025, (hx, yf - 0.012, 0.93), 2, 2)
        hm.build('Door furniture', mat(metal))
    return root


def extractor_fan():
    """Ceiling extractor grille, origin on the ceiling surface."""
    with group('Extractor fan') as root:
        mb = MeshBuilder()
        mb.rounded_box((0.18, 0.18, 0.012), 0.004, (0, 0, -0.006), 3, 2)
        mb.build('Extractor', mat('plastic_white'), 'HARD')
        sm = MeshBuilder()
        for i in range(7):
            x = -0.06 + 0.02 * i
            sm.box((x - 0.004, -0.06, -0.0122), (x + 0.004, 0.06, -0.0118))
        sm.build('Extractor slots', mat('plastic_dark'), 'FLAT')
    return root
