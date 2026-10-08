"""Corrugated cardboard boxes (regular slotted containers).

The board has real thickness: outer liner, inner liner and cut edges are three
separate single-colour objects. Walls form a closed ring with rounded corner
folds; every flap is joined to its wall by a bent fold, so flaps can be posed
at any angle. Box coordinates: centred on the origin, bottom at z = 0, the
long side (L) along X and the short side (W) along Y; the front faces -Y.
"""

import math

from mathutils import Vector

from bathroom_gen.geo import group, rounded_rect
from .materials import mat
from .mesh import Builder

SIDES = ('front', 'right', 'back', 'left')


class _Board:
    """The three faces of corrugated board, collected per colour."""

    def __init__(self):
        self.outer = Builder()
        self.inner = Builder()
        self.edge = Builder()

    def build(self, prefix):
        out = []
        for part, key in ((self.outer, 'kraft_outer'), (self.inner, 'kraft_inner'),
                          (self.edge, 'kraft_edge')):
            if part.faces:
                out.append(part.build('%s %s' % (prefix, key.split('_')[1]), mat(key), 'SMOOTH'))
        return out


def _side_map(side, L, W, t):
    """(u, n, z) -> 3D for a side; n is the outward offset from the side's
    centre plane, u runs left to right seen from outside."""
    if side == 'front':
        c = -W / 2 + t / 2
        return lambda u, n, z: Vector((u, c - n, z))
    if side == 'back':
        c = W / 2 - t / 2
        return lambda u, n, z: Vector((-u, c + n, z))
    if side == 'right':
        c = L / 2 - t / 2
        return lambda u, n, z: Vector((c + n, u, z))
    c = -L / 2 + t / 2
    return lambda u, n, z: Vector((c - n, -u, z))


def _fold_path(theta, rc, depth, bow, seg_fold=8, seg_flap=10):
    """Centre line of a fold + flap in the side plane, as (n, s) points where
    s is the distance away from the wall edge. Returns points and tangents.

    ``theta`` > 0 leans the flap outwards (0 = straight on from the wall,
    -90 = folded flat over the box). ``bow`` curls the flap a little more."""
    sg = 1.0 if theta >= 0 else -1.0
    a = abs(math.radians(theta))
    pts, tans = [], []
    for k in range(seg_fold + 1):
        phi = a * k / seg_fold
        pts.append((sg * (rc - rc * math.cos(phi)), rc * math.sin(phi)))
        tans.append((sg * math.sin(phi), math.cos(phi)))
    # straight-ish flap, continuing the fold with a gentle extra curl
    length = depth - rc * a
    step = length / seg_flap
    ang = sg * a
    n_, s_ = pts[-1]
    for k in range(seg_flap):
        ang += math.radians(bow) / seg_flap
        n_ += step * math.sin(ang)
        s_ += step * math.cos(ang)
        pts.append((n_, s_))
        tans.append((math.sin(ang), math.cos(ang)))
    return pts, tans


def _flap(board, side_fn, u0, u1, base_z, up, theta, rc, depth, t, bow=0.0, twist=0.0,
          nu=4, v_offset=0.0):
    """Fold + flap of board thickness ``t`` spanning u0..u1 along the side.

    ``up`` = +1 for top flaps (rising from ``base_z``), -1 for bottom ones."""
    cols = []
    for i in range(nu + 1):
        su = i / nu
        th = theta + twist * (su - 0.5)
        pts, tans = _fold_path(th, rc, depth, bow)
        u = u0 + (u1 - u0) * su
        col = []
        for (pn, ps), (tn, ts) in zip(pts, tans):
            nn, ns = ts, -tn                         # outward normal of the centre line
            out = side_fn(u, pn + nn * t / 2, base_z + up * (ps + ns * t / 2))
            inn = side_fn(u, pn - nn * t / 2, base_z + up * (ps - ns * t / 2))
            col.append((out, inn))
        cols.append(col)
    npts = len(cols[0])
    # arc length along the centre line for the V coordinate
    pts0, _ = _fold_path(theta, rc, depth, bow)
    acc = [0.0]
    for a, b in zip(pts0, pts0[1:]):
        acc.append(acc[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    flip = up < 0
    for i in range(nu):
        ua = u0 + (u1 - u0) * i / nu
        ub = u0 + (u1 - u0) * (i + 1) / nu
        for k in range(npts - 1):
            va, vb = v_offset + acc[k], v_offset + acc[k + 1]
            o = [cols[i][k][0], cols[i + 1][k][0], cols[i + 1][k + 1][0], cols[i][k + 1][0]]
            uv = [(ua, va), (ub, va), (ub, vb), (ua, vb)]
            inn = [cols[i][k][1], cols[i][k + 1][1], cols[i + 1][k + 1][1], cols[i + 1][k][1]]
            uvi = [(ua, va), (ua, vb), (ub, vb), (ub, va)]
            if flip:
                for lst in (o, uv, inn, uvi):
                    lst.reverse()
            board.outer.quad(o, uv, smooth=True)
            board.inner.quad(inn, uvi, smooth=True)
    # cut edges: the two ends and the tip
    for i, sgn in ((0, -1), (nu, 1)):
        for k in range(npts - 1):
            q = [cols[i][k][0], cols[i][k + 1][0], cols[i][k + 1][1], cols[i][k][1]]
            if (sgn > 0) != flip:
                q.reverse()
            board.edge.quad(q)
    for i in range(nu):
        q = [cols[i][-1][0], cols[i][-1][1], cols[i + 1][-1][1], cols[i + 1][-1][0]]
        if not flip:
            q.reverse()
        board.edge.quad(q)


def _wall_ring(board, L, W, t, z0, z1, r, seg=6):
    """Closed ring of walls with rounded vertical folds."""
    outer = rounded_rect(L, W, r, seg)
    inner = rounded_rect(L - 2 * t, W - 2 * t, max(r - t, 0.0005), seg)
    # arc-length U so the flute stripes run on continuously round the box
    def arclen(poly):
        acc = [0.0]
        for a, b in zip(poly, poly[1:] + poly[:1]):
            acc.append(acc[-1] + (b - a).length)
        return acc
    ao, ai = arclen(outer), arclen(inner)
    ro = [[Vector((p.x, p.y, z)) for p in outer] for z in (z0, z1)]
    ri = [[Vector((p.x, p.y, z)) for p in inner] for z in (z1, z0)]
    board.outer.loft_uv(ro, [[(u, z0) for u in ao], [(u, z1) for u in ao]], closed=True)
    board.inner.loft_uv(ri, [[(u, z1) for u in ai], [(u, z0) for u in ai]], closed=True)
    # cut rims (seen in the slots between flaps)
    n = len(outer)
    for z, up in ((z1, True), (z0, False)):
        for i in range(n):
            j = (i + 1) % n
            q = [Vector((outer[i].x, outer[i].y, z)), Vector((outer[j].x, outer[j].y, z)),
                 Vector((inner[j].x, inner[j].y, z)), Vector((inner[i].x, inner[i].y, z))]
            if not up:
                q.reverse()
            board.edge.quad(q)


def cardboard_box(L=0.46, W=0.31, H=0.30, t=0.004, flaps=None, bow=None, twist=None,
                  name='Cardboard box', tape=True, glue_joint=True):
    """Open regular slotted carton.

    ``flaps`` maps side -> top flap angle in degrees (0 = upright, positive =
    leaning out, -90 = closed). ``bow``/``twist`` give each flap a little
    curl/warp in degrees, so the board does not look machine-flat."""
    flaps = flaps or {'front': 100, 'back': 20, 'left': 50, 'right': 45}
    bow = bow or {}
    twist = twist or {}
    zb, zt = 2.0 * t, H
    r_fold = 1.2 * t
    slot = 2.0 * r_fold
    depth = W / 2.0
    board = _Board()
    with group(name) as root:
        _wall_ring(board, L, W, t, zb, zt, r_fold)
        for side in SIDES:
            major = side in ('front', 'back')
            span = L if major else W
            fn = _side_map(side, L, W, t)
            u0, u1 = -span / 2 + slot / 2, span / 2 - slot / 2
            # top flaps; closed ones nest like the bottom (minor flaps inside)
            closed = flaps[side] <= -80
            rc = (1.5 * t if major else 0.5 * t) if closed else 1.2 * t
            _flap(board, fn, u0, u1, zt, +1, flaps[side], rc, depth - (0.001 if major else 0.0),
                  t, bow=bow.get(side, 0.0 if closed else 4.0), twist=twist.get(side, 0.0),
                  v_offset=zt)
            # bottom flaps, folded shut: major flaps (front/back) outside
            inset = 0.0 if major else t
            _flap(board, fn, u0 + inset, u1 - inset, zb, -1, -90.0, 1.5 * t if major else 0.5 * t,
                  depth - (0.001 if major else 0.0), t, bow=0.0, v_offset=-depth)
        if glue_joint:
            _glue_tab(board, L, W, t, zb, zt)
        board.build(name)
        if tape:
            _tape(L, 0.0, -1, name + ' tape (bottom)')
            if all(a <= -80 for a in flaps.values()):
                _tape(L, zt + 2.0 * t, +1, name + ' tape (top)')
    return root


def _glue_tab(board, L, W, t, zb, zt, width=0.032, taper=0.01):
    """Manufacturer's joint: the glued tab inside the back-left corner."""
    x0 = -L / 2 + t                      # inner face of the left wall
    yc = W / 2 - t                       # inner face of the back wall
    # tab lies on the back wall's inner face, running from the corner
    pts_out = []
    for (u, z) in ((0.0, zb + 0.002), (width, zb + 0.002 + taper),
                   (width, zt - 0.002 - taper), (0.0, zt - 0.002)):
        pts_out.append((x0 + 0.002 + u, z))
    front = [Vector((x, yc - t, z)) for x, z in pts_out]
    back = [Vector((x, yc - 0.0002, z)) for x, z in pts_out]
    board.outer.quad(front)
    for i in range(4):
        j = (i + 1) % 4
        board.edge.quad([front[j], front[i], back[i], back[j]])


def _tape(L, z_face, up, name, width=0.048, lap=0.065, th=0.0003, r=0.003):
    """Packing tape over a flap seam (bottom: up=-1, top: up=+1) that laps
    over both end walls. Profile in (x, h), h measured from the taped face
    towards the middle of the box."""
    x_end = L / 2 + th
    path = [(-x_end, lap)]
    for k in range(7):
        a = math.pi + math.pi / 2 * k / 6
        path.append((-L / 2 + r + (r + th) * math.cos(a), r + (r + th) * math.sin(a)))
    for k in range(7):
        a = 1.5 * math.pi + math.pi / 2 * k / 6
        path.append((L / 2 - r + (r + th) * math.cos(a), r + (r + th) * math.sin(a)))
    path.append((x_end, lap))
    ys = (-width / 2, width / 2) if up < 0 else (width / 2, -width / 2)
    rings = [[Vector((x, y, z_face - up * h)) for y in ys] for x, h in path]
    mb = Builder()
    mb.loft(rings, closed=False)
    mb.build(name, mat('packing_tape'), 'SMOOTH')


# ---------------------------------------------------------------------------
# The two boxes from the reference photo
# ---------------------------------------------------------------------------

def box_tall_open():
    """Tall square carton with all four flaps opened out."""
    return cardboard_box(0.40, 0.40, 0.60, t=0.0045,
                         flaps={'front': 60, 'back': 28, 'left': 57, 'right': 24},
                         bow={'front': 6, 'back': 5, 'left': 7, 'right': 4},
                         twist={'front': 4, 'left': -5, 'right': 3},
                         name='Cardboard box (tall)')


def box_regular_open():
    """Regular shipping carton, open, flaps spread."""
    return cardboard_box(0.46, 0.32, 0.30, t=0.004,
                         flaps={'front': 102, 'back': 12, 'left': 48, 'right': 62},
                         bow={'front': -6, 'back': 5, 'left': 6, 'right': 7},
                         twist={'front': -3, 'left': 4, 'right': -4},
                         name='Cardboard box (regular)')


def box_closed(L=0.40, W=0.30, H=0.30, name='Cardboard box (closed)'):
    """Taped-shut carton for stacking (warehouse dressing)."""
    root = cardboard_box(L, W, H, flaps={'front': -90, 'back': -90, 'left': -90, 'right': -90},
                         name=name)
    return root
