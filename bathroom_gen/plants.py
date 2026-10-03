"""Procedural house plants: a trailing pothos and a floor-standing palm."""

import math
import random

from mathutils import Matrix, Vector

from .geo import MeshBuilder, catmull_rom, group, resample
from .materials import mat


def _leaf_heart(length, width, rows=7, cols=6, fold=0.25, curl=0.12):
    """Heart-shaped leaf in local space: petiole at origin, tip towards +Y,
    face normal +Z. Returns a MeshBuilder."""
    mb = MeshBuilder()
    grid = []
    for j in range(rows + 1):
        s = j / rows                          # 0 = base, 1 = tip
        half = width * 0.5 * (math.sin(math.pi * (0.12 + 0.88 * s)) ** 0.75) * (1.0 - 0.15 * s)
        row = []
        for i in range(cols + 1):
            u = -1.0 + 2.0 * i / cols
            x = u * half
            # heart notch: the midline is pushed forward near the base
            notch = 0.16 * length * (1.0 - abs(u)) * (1.0 - s) ** 3
            y = s * length + notch - 0.10 * length * (1.0 - s) ** 2 * abs(u)
            z = fold * abs(x) - curl * length * s * s
            row.append(mb.v((x, y, z)))
        grid.append(row)
    for j in range(rows):
        for i in range(cols):
            mb.f([grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]])
    return mb


def _leaf_lance(length, width, rows=8):
    """Long narrow leaflet (palm), base at origin, pointing +Y, V-folded."""
    mb = MeshBuilder()
    grid = []
    for j in range(rows + 1):
        s = j / rows
        half = width * 0.5 * math.sin(math.pi * min(1.0, 0.08 + s)) ** 0.6 * (1.0 - 0.6 * s)
        row = []
        for u in (-1.0, 0.0, 1.0):
            row.append(mb.v((u * half, s * length, 0.35 * abs(u) * half - 0.18 * length * s * s)))
        grid.append(row)
    for j in range(rows):
        for i in range(2):
            mb.f([grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]])
    return mb


def _pot(name, r_top, r_bot, h, material='ceramic_matte', rim=0.008):
    mb = MeshBuilder()
    mb.revolve([(0, 0.0), (r_bot - 0.01, 0.0), (r_bot, 0.006), (r_top, h - rim),
                (r_top + 0.002, h), (r_top - rim, h), (r_top - rim * 1.2, h - 0.02),
                (r_bot * 0.9, 0.02), (0, 0.02)], 48)
    mb.build(name, mat(material), subsurf=1)
    sm = MeshBuilder()
    sm.revolve([(0, h - 0.025), (r_top - rim * 1.1, h - 0.028), (r_top - rim * 1.1, h - 0.04),
                (0, h - 0.04)], 32)
    sm.build(name + ' soil', mat('soil'), 'SMOOTH')


def pothos(seed=3, vines=9):
    """Trailing pothos in a small pot. Origin = pot base centre.
    Vines spill towards -Y (over a ledge edge) and hang down to -Z."""
    rng = random.Random(seed)
    with group('Pothos') as root:
        _pot('Pot', 0.075, 0.060, 0.11)
        leaves = MeshBuilder()
        stems = MeshBuilder()
        top = 0.085
        # a bushy crown of upright leaves
        for i in range(14):
            a = rng.uniform(0, 2 * math.pi)
            r = rng.uniform(0.0, 0.05)
            base = Vector((r * math.cos(a), r * math.sin(a), top))
            tilt = rng.uniform(0.5, 1.2)
            m = (Matrix.Translation(base) @ Matrix.Rotation(a + math.pi / 2, 4, 'Z') @
                 Matrix.Rotation(-tilt, 4, 'X'))
            stem_end = m @ Vector((0, 0.05, 0))
            stems.tube([base, stem_end], 0.0018, 6)
            lf = _leaf_heart(rng.uniform(0.06, 0.085), rng.uniform(0.05, 0.065))
            leaves.val = rng.random()
            leaves.merge(lf, Matrix.Translation(stem_end) @ m.to_3x3().to_4x4() @
                         Matrix.Rotation(rng.uniform(-0.6, 0.2), 4, 'X'))
        # trailing vines falling over the ledge
        for v in range(vines):
            a = math.radians(-160 + 140 * v / max(1, vines - 1)) + rng.uniform(-0.1, 0.1)
            out = Vector((math.cos(a), math.sin(a), 0.0))
            length = rng.uniform(0.35, 0.85)
            # pot rim -> ledge edge (y ~ -0.10) -> hanging down
            ctrl = [Vector((0.04 * out.x, 0.04 * out.y, top + 0.01)),
                    Vector((0.08 * out.x, 0.08 * out.y - 0.02, top + 0.02)),
                    Vector((0.13 * out.x, -0.10 + 0.04 * out.y, top - 0.06)),
                    Vector((0.17 * out.x + rng.uniform(-0.03, 0.03), -0.12, top - 0.06 - 0.4 * length)),
                    Vector((0.20 * out.x + rng.uniform(-0.05, 0.05), -0.12 + rng.uniform(-0.02, 0.01),
                            top - 0.06 - length))]
            path = resample(catmull_rom(ctrl, 10), 0.01)
            stems.tube(path, lambda t: 0.0022 - 0.001 * t, 6)
            # leaves alternate along the vine, shrinking towards the tip
            k = 3
            side = 1
            while k < len(path) - 1:
                p = path[k]
                tang = (path[k + 1] - path[k - 1]).normalized()
                side = -side
                size = 1.0 - 0.45 * (k / len(path))
                yaw = math.atan2(tang.y, tang.x) + side * rng.uniform(0.9, 1.6)
                # leaves on hanging vines face outwards (-Y) and droop
                m = (Matrix.Translation(p) @ Matrix.Rotation(yaw - math.pi / 2, 4, 'Z') @
                     Matrix.Rotation(rng.uniform(-1.3, -0.5), 4, 'X') @
                     Matrix.Rotation(rng.uniform(-0.4, 0.4), 4, 'Y'))
                lf = _leaf_heart(0.07 * size * rng.uniform(0.85, 1.15),
                                 0.055 * size * rng.uniform(0.85, 1.15))
                leaves.val = rng.random()
                leaves.merge(lf, m)
                k += rng.randint(3, 5)
        stems.build('Vines', mat('plant_stem'), 'SMOOTH')
        leaves.build('Leaves', mat('leaf_pothos'), 'SMOOTH', attr='leaf_rand')
    return root


def palm(seed=11, fronds=10, height=0.95):
    """Kentia-style palm in a large floor planter. Origin = planter base."""
    rng = random.Random(seed)
    with group('Palm') as root:
        ph = 0.34
        _pot('Planter', 0.17, 0.13, ph)
        leaves = MeshBuilder()
        stems = MeshBuilder()
        top = ph - 0.03
        for f in range(fronds):
            a = 2 * math.pi * f / fronds + rng.uniform(-0.25, 0.25)
            out = Vector((math.cos(a), math.sin(a), 0.0))
            reach = rng.uniform(0.35, 0.6) * height
            rise = rng.uniform(0.55, 1.0) * height
            base = Vector((0.02 * out.x, 0.02 * out.y, top))
            ctrl = [base,
                    base + out * (reach * 0.15) + Vector((0, 0, rise * 0.55)),
                    base + out * (reach * 0.6) + Vector((0, 0, rise * 0.95)),
                    base + out * reach + Vector((0, 0, rise * 0.7))]
            path = resample(catmull_rom(ctrl, 12), 0.015)
            stems.tube(path, lambda t: 0.007 - 0.005 * t, 6)
            n = len(path)
            for k in range(int(n * 0.28), n - 1, 1):
                t = k / n
                p = path[k]
                tang = (path[k + 1] - path[k]).normalized()
                for side in (-1, 1):
                    # leaflets angle forward and droop under their weight
                    side_dir = tang.cross(Vector((0, 0, 1))).normalized() * side
                    if side_dir.length < 1e-6:
                        continue
                    d = (side_dir * 0.8 + tang * 0.6 + Vector((0, 0, -0.25))).normalized()
                    up = side_dir.cross(d).normalized() * side
                    ln = (0.22 - 0.12 * abs(t - 0.55)) * rng.uniform(0.85, 1.1) * height
                    lf = _leaf_lance(ln, 0.026 * rng.uniform(0.8, 1.1))
                    rot = Matrix((d.cross(up).normalized(), d, up)).transposed().to_4x4()
                    leaves.val = rng.random()
                    leaves.merge(lf, Matrix.Translation(p) @ rot)
        stems.build('Palm stems', mat('plant_stem'), 'SMOOTH')
        leaves.build('Palm leaves', mat('leaf_palm'), 'SMOOTH', attr='leaf_rand')
    return root
