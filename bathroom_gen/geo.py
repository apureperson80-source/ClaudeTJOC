"""Procedural mesh helpers.

Everything here builds geometry directly through the data API (no bpy.ops),
so the generator runs identically in the UI, in ``blender --background`` and
with the standalone ``bpy`` module.

The workhorse is :class:`MeshBuilder`: shapes are described as *rings* of
points that get lofted together (lathe profiles, superellipse cross-sections,
swept tubes, rounded polygons ...), then turned into a Blender object with a
chosen shading style.
"""

import math
import random
from contextlib import contextmanager

import bpy
from mathutils import Matrix, Vector

TAU = 2.0 * math.pi


# ---------------------------------------------------------------------------
# Object placement context
# ---------------------------------------------------------------------------

class _Context:
    collection = None
    parents = []


_ctx = _Context()


@contextmanager
def target(collection):
    """New objects are linked into ``collection`` while the block runs."""
    prev = _ctx.collection
    _ctx.collection = collection
    try:
        yield collection
    finally:
        _ctx.collection = prev


def link(obj):
    coll = _ctx.collection or bpy.context.scene.collection
    coll.objects.link(obj)
    if _ctx.parents:
        obj.parent = _ctx.parents[-1]
    return obj


@contextmanager
def group(name, location=(0, 0, 0), rotation=(0, 0, 0), size=0.1):
    """Parent every object created in the block to a new empty.

    Parts are modelled around the origin; the empty is moved to ``location``
    when the block exits, carrying the whole assembly with it.
    """
    root = bpy.data.objects.new(name, None)
    root.empty_display_type = 'PLAIN_AXES'
    root.empty_display_size = size
    link(root)
    _ctx.parents.append(root)
    try:
        yield root
    finally:
        _ctx.parents.pop()
        root.location = location
        root.rotation_euler = rotation


def new_collection(name, parent):
    coll = bpy.data.collections.new(name)
    parent.children.link(coll)
    return coll


# ---------------------------------------------------------------------------
# Small math helpers
# ---------------------------------------------------------------------------

def sgnpow(x, p):
    return math.copysign(abs(x) ** p, x)


def lerp(a, b, t):
    return a + (b - a) * t


def v2(x, y):
    return Vector((x, y))


def plane_map(origin, u_axis, v_axis, n_axis=None):
    """Return f(u, v, w) -> origin + u*U + v*V + w*N."""
    o = Vector(origin)
    U = Vector(u_axis)
    V = Vector(v_axis)
    N = Vector(n_axis) if n_axis is not None else U.cross(V)

    def f(u, v, w=0.0):
        return o + U * u + V * v + N * w
    return f


# Common axis frames for 2D ring -> 3D placement
def ring_xy(pts, z):
    """2D (x, y) ring lying flat at height z."""
    return [Vector((p[0], p[1], z)) for p in pts]


def ring_xz(pts, y):
    """2D (x, z) ring standing in a plane of constant y."""
    return [Vector((p[0], y, p[1])) for p in pts]


def ring_yz(pts, x):
    """2D (y, z) ring standing in a plane of constant x."""
    return [Vector((x, p[0], p[1])) for p in pts]


# ---------------------------------------------------------------------------
# 2D ring generators
# ---------------------------------------------------------------------------

def superellipse(n, w, d_neg, d_pos=None, e_neg=2.0, e_pos=None,
                 center=(0.0, 0.0), scale=1.0, phase=0.0):
    """Superellipse ring with separate extent/exponent on each side of v.

    ``w`` is the half width along u. ``d_neg``/``d_pos`` are the extents
    towards -v / +v (for fixtures -v is the front, +v the wall side).
    Exponent 2 is an ellipse, larger exponents approach a rectangle.
    Points run counter-clockwise starting at +u.
    """
    d_pos = d_neg if d_pos is None else d_pos
    e_pos = e_neg if e_pos is None else e_pos
    pts = []
    for i in range(n):
        t = phase + TAU * i / n
        ct, st = math.cos(t), math.sin(t)
        if st >= 0:
            e, d = e_pos, d_pos
        else:
            e, d = e_neg, d_neg
        u = w * scale * sgnpow(ct, 2.0 / e)
        v = d * scale * sgnpow(st, 2.0 / e)
        pts.append(v2(center[0] + u, center[1] + v))
    return pts


def circle(n, r, center=(0.0, 0.0), phase=0.0):
    return [v2(center[0] + r * math.cos(phase + TAU * i / n),
               center[1] + r * math.sin(phase + TAU * i / n)) for i in range(n)]


def rounded_poly(corners, radii, seg=6):
    """Polygon with circular-arc corners.

    ``radii`` is a number or one value per corner. A radius of 0 keeps a sharp
    corner (one point). Works for convex and concave corners of a CCW polygon.
    """
    n = len(corners)
    cs = [v2(*c) for c in corners]
    if not isinstance(radii, (list, tuple)):
        radii = [radii] * n
    out = []
    for i in range(n):
        p0, p1, p2 = cs[i - 1], cs[i], cs[(i + 1) % n]
        r = radii[i]
        if r <= 0:
            out.append(p1.copy())
            continue
        a = p1 - p0
        b = p2 - p1
        la, lb = a.length, b.length
        d1, d2 = a / la, b / lb
        cross = d1.x * d2.y - d1.y * d2.x
        phi = math.acos(max(-1.0, min(1.0, d1.dot(d2))))
        if phi < 1e-4:
            out.append(p1.copy())
            continue
        t = r * math.tan(phi / 2.0)
        tmax = 0.499 * min(la, lb)
        if t > tmax:
            t = tmax
            r = t / math.tan(phi / 2.0)
        s = 1.0 if cross > 0 else -1.0
        t1 = p1 - d1 * t
        nrm = v2(-d1.y * s, d1.x * s)
        c = t1 + nrm * r
        a0 = math.atan2(t1.y - c.y, t1.x - c.x)
        for k in range(seg + 1):
            ang = a0 + s * phi * k / seg
            out.append(v2(c.x + r * math.cos(ang), c.y + r * math.sin(ang)))
    return out


def rounded_rect(w, h, r, seg=6, center=(0.0, 0.0)):
    """Rounded rectangle of full size w x h (CCW)."""
    cx, cy = center
    hw, hh = w / 2.0, h / 2.0
    corners = [(cx + hw, cy - hh), (cx + hw, cy + hh),
               (cx - hw, cy + hh), (cx - hw, cy - hh)]
    return rounded_poly(corners, r, seg)


def offset_poly(corners, d):
    """Offset a CCW polygon inwards by ``d`` (negative grows it)."""
    cs = [v2(*c) for c in corners]
    n = len(cs)
    lines = []
    for i in range(n):
        a, b = cs[i], cs[(i + 1) % n]
        e = (b - a).normalized()
        nl = v2(-e.y, e.x)
        lines.append((a + nl * d, e))
    out = []
    for i in range(n):
        p1, e1 = lines[i - 1]
        p2, e2 = lines[i]
        den = e1.x * e2.y - e1.y * e2.x
        if abs(den) < 1e-9:
            out.append(p2)
            continue
        t = ((p2.x - p1.x) * e2.y - (p2.y - p1.y) * e2.x) / den
        out.append(p1 + e1 * t)
    return out


# ---------------------------------------------------------------------------
# 3D path helpers
# ---------------------------------------------------------------------------

def fillet_path(path, radius, seg=8):
    """Round the interior corners of a polyline (quadratic Bezier arcs)."""
    pts = [Vector(p) for p in path]
    if len(pts) < 3:
        return pts
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        p0, p1, p2 = pts[i - 1], pts[i], pts[i + 1]
        a, b = p1 - p0, p2 - p1
        if a.length < 1e-9 or b.length < 1e-9:
            continue
        phi = a.angle(b)
        if phi < 1e-3:
            out.append(p1)
            continue
        t = min(radius * math.tan(phi / 2.0), 0.5 * a.length, 0.5 * b.length)
        q0 = p1 - a.normalized() * t
        q1 = p1 + b.normalized() * t
        for k in range(seg + 1):
            s = k / seg
            out.append(q0 * (1 - s) ** 2 + p1 * 2 * (1 - s) * s + q1 * s * s)
    out.append(pts[-1])
    return out


def catmull_rom(points, samples=10):
    """Smooth spline through ``points`` (end points are kept)."""
    pts = [Vector(p) for p in points]
    ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for k in range(samples):
            t = k / samples
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t +
                              (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1])
    return out


def resample(path, step):
    """Re-sample a polyline at (approximately) constant spacing."""
    pts = [Vector(p) for p in path]
    lengths = [0.0]
    for a, b in zip(pts, pts[1:]):
        lengths.append(lengths[-1] + (b - a).length)
    total = lengths[-1]
    n = max(2, int(round(total / step)) + 1)
    out = []
    j = 0
    for i in range(n):
        s = total * i / (n - 1)
        while j < len(pts) - 2 and lengths[j + 1] < s:
            j += 1
        seg_len = lengths[j + 1] - lengths[j]
        t = 0.0 if seg_len < 1e-12 else (s - lengths[j]) / seg_len
        out.append(pts[j].lerp(pts[j + 1], t))
    return out


def path_length(path):
    return sum((Vector(b) - Vector(a)).length for a, b in zip(path, path[1:]))


def frames_along(path, up=None):
    """Rotation-minimising frames (tangent, normal, binormal) along a path."""
    pts = [Vector(p) for p in path]
    n = len(pts)
    tangents = []
    for i in range(n):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = (pts[i] - pts[i - 1]).normalized() + (pts[i + 1] - pts[i]).normalized()
            if t.length < 1e-9:
                t = pts[i + 1] - pts[i]
        tangents.append(t.normalized())
    t0 = tangents[0]
    if up is not None:
        nrm = Vector(up)
        nrm = (nrm - t0 * nrm.dot(t0))
    else:
        ref = Vector((0, 0, 1)) if abs(t0.z) < 0.9 else Vector((1, 0, 0))
        nrm = ref - t0 * ref.dot(t0)
    nrm.normalize()
    frames = []
    for i in range(n):
        t = tangents[i]
        nrm = nrm - t * nrm.dot(t)
        if nrm.length < 1e-9:
            nrm = t.orthogonal()
        nrm.normalize()
        frames.append((t, nrm, t.cross(nrm)))
    return pts, frames


# ---------------------------------------------------------------------------
# Mesh builder
# ---------------------------------------------------------------------------

def _centroid(pts):
    c = Vector((0.0, 0.0, 0.0))
    for p in pts:
        c += p
    return c / len(pts)


def _newell(pts):
    n = Vector((0.0, 0.0, 0.0))
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        n.x += (a.y - b.y) * (a.z + b.z)
        n.y += (a.z - b.z) * (a.x + b.x)
        n.z += (a.x - b.x) * (a.y + b.y)
    return n


class MeshBuilder:
    """Accumulates vertices/faces (with per-face material, smoothing and an
    optional float attribute) and turns them into a Blender mesh object."""

    def __init__(self):
        self.verts = []
        self.faces = []
        self.face_mat = []
        self.face_smooth = []
        self.face_val = []
        self.mat = 0          # material slot for new faces
        self.smooth = True    # smooth flag for new faces
        self.val = 0.0        # attribute value for new faces

    # -- primitives ---------------------------------------------------------
    def v(self, co):
        self.verts.append(Vector(co))
        return len(self.verts) - 1

    def f(self, idx, smooth=None):
        self.faces.append(list(idx))
        self.face_mat.append(self.mat)
        self.face_smooth.append(self.smooth if smooth is None else smooth)
        self.face_val.append(self.val)

    def mark(self):
        return len(self.verts)

    def polygon(self, points, smooth=False):
        """Single n-gon face (winding as given)."""
        self.f([self.v(p) for p in points], smooth=smooth)

    def transform(self, matrix, start=0):
        m = Matrix(matrix)
        for i in range(start, len(self.verts)):
            self.verts[i] = m @ self.verts[i]

    def merge(self, other, matrix=None):
        """Append another builder's geometry (optionally transformed)."""
        start = len(self.verts)
        m = Matrix(matrix) if matrix is not None else None
        self.verts.extend((m @ v) if m is not None else v.copy() for v in other.verts)
        for f, fs, fv in zip(other.faces, other.face_smooth, other.face_val):
            self.faces.append([i + start for i in f])
            self.face_mat.append(self.mat)
            self.face_smooth.append(fs)
            self.face_val.append(fv)

    # -- lofting ------------------------------------------------------------
    def loft(self, rings, closed=True, cap_start=False, cap_end=False,
             cyclic=False, cap_smooth=False):
        """Bridge consecutive rings (lists of 3D points, equal length) with quads.

        A ring whose points all coincide is collapsed to one vertex (fan).
        ``closed`` wraps each ring, ``cyclic`` also bridges last -> first ring.
        Caps are oriented away from the neighbouring ring automatically.
        """
        rings = [[Vector(p) for p in r] for r in rings]
        n = len(rings[0])
        idx = []
        for r in rings:
            c = _centroid(r)
            if max((p - c).length for p in r) < 1e-7:
                vi = self.v(c)
                idx.append([vi] * n)
            else:
                idx.append([self.v(p) for p in r])
        pairs = list(zip(range(len(rings) - 1), range(1, len(rings))))
        if cyclic:
            pairs.append((len(rings) - 1, 0))
        m = n if closed else n - 1
        for ka, kb in pairs:
            A, B = idx[ka], idx[kb]
            for i in range(m):
                j = (i + 1) % n
                quad = [A[i], A[j], B[j], B[i]]
                # drop repeated indices of collapsed rings
                face = []
                for q in quad:
                    if q not in face:
                        face.append(q)
                if len(face) >= 3:
                    self.f(face)
        if closed:
            if cap_start:
                self._cap(idx[0], rings[0], rings[1], cap_smooth)
            if cap_end:
                self._cap(idx[-1], rings[-1], rings[-2], cap_smooth)
        return idx

    def _cap(self, ids, ring, neighbour, smooth):
        if len(set(ids)) < 3:
            return
        normal = _newell(ring)
        away = _centroid(ring) - _centroid(neighbour)
        if away.length < 1e-9:
            # same centroid (e.g. rim top ring): use point-wise direction
            away = Vector((0.0, 0.0, 0.0))
            for a, b in zip(ring, neighbour):
                away += a - b
        face = list(ids)
        if normal.dot(away) < 0:
            face.reverse()
        self.f(face, smooth=smooth)

    # -- shapes -------------------------------------------------------------
    def revolve(self, profile, seg=32, axis='Z', center=(0, 0, 0),
                cap_start=False, cap_end=False, ribs=None, closed_profile=False,
                phase=0.0):
        """Lathe a (radius, height) profile around an axis.

        ``ribs`` = (count, depth, first_index, last_index) adds knurling to the
        profile points in that index range.
        """
        c = Vector(center)
        rings = []
        for pi, (r, h) in enumerate(profile):
            pts = []
            for i in range(seg):
                a = phase + TAU * i / seg
                rr = r
                if ribs and ribs[2] <= pi <= ribs[3] and r > 0:
                    rr = r * (1.0 - ribs[1] * (0.5 + 0.5 * math.cos(ribs[0] * a)))
                x, y = rr * math.cos(a), rr * math.sin(a)
                if axis == 'Z':
                    p = Vector((x, y, h))
                elif axis == 'X':
                    p = Vector((h, x, y))
                else:  # 'Y' -- profile height runs along -Y (out of a wall)
                    p = Vector((x, -h, y))
                pts.append(c + p)
            rings.append(pts)
        return self.loft(rings, cap_start=cap_start, cap_end=cap_end,
                         cyclic=closed_profile)

    def tube(self, path, radius, seg=16, cap_start=True, cap_end=True, up=None):
        """Sweep a circle along a path. ``radius`` may be a callable(t in 0..1)."""
        pts, frames = frames_along(path, up)
        total = max(path_length(pts), 1e-9)
        rings = []
        acc = 0.0
        for i, (p, (t, nrm, b)) in enumerate(zip(pts, frames)):
            if i > 0:
                acc += (pts[i] - pts[i - 1]).length
            r = radius(acc / total) if callable(radius) else radius
            rings.append([p + (nrm * math.cos(TAU * k / seg) + b * math.sin(TAU * k / seg)) * r
                          for k in range(seg)])
        return self.loft(rings, cap_start=cap_start, cap_end=cap_end)

    def sweep(self, path, profile, closed_profile=True, cap_start=True,
              cap_end=True, up=None, scale=None):
        """Sweep a 2D profile (u along normal, v along binormal) along a path."""
        pts, frames = frames_along(path, up)
        rings = []
        for i, (p, (t, nrm, b)) in enumerate(zip(pts, frames)):
            s = scale(i / max(1, len(pts) - 1)) if scale else 1.0
            rings.append([p + nrm * (q[0] * s) + b * (q[1] * s) for q in profile])
        return self.loft(rings, closed=closed_profile,
                         cap_start=cap_start and closed_profile,
                         cap_end=cap_end and closed_profile)

    def prism(self, poly2d, z0, z1, mapper=None, cap=True):
        """Extrude a 2D polygon between w=z0 and w=z1.

        ``mapper(u, v, w)`` places it in 3D (default: XY plane, Z up).
        """
        if mapper is None:
            def mapper(u, v, w):
                return Vector((u, v, w))
        rings = [[mapper(p[0], p[1], z0) for p in poly2d],
                 [mapper(p[0], p[1], z1) for p in poly2d]]
        return self.loft(rings, cap_start=cap, cap_end=cap)

    def box(self, mn, mx, smooth=False):
        x0, y0, z0 = mn
        x1, y1, z1 = mx
        b = [self.v(p) for p in [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                 (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]]
        for f in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
                  (2, 3, 7, 6), (3, 0, 4, 7)]:
            self.f([b[i] for i in f], smooth=smooth)

    def rounded_box(self, size, r, center=(0, 0, 0), seg=4, zseg=3):
        """Box with all edges rounded (no modifiers needed)."""
        sx, sy, sz = size
        cx, cy, cz = center
        r = min(r, sx / 2.0 - 1e-5, sy / 2.0 - 1e-5, sz / 2.0 - 1e-5)
        rings = []
        for k in range(zseg + 1):
            a = (math.pi / 2.0) * k / zseg
            inset = r * (1.0 - math.sin(a))
            z = cz - sz / 2.0 + r * (1.0 - math.cos(a))
            rings.append((inset, z))
        top = [(i, 2 * cz - z) for (i, z) in reversed(rings)]
        out = []
        for inset, z in rings + top:
            rr = max(r - inset, 1e-5)
            poly = rounded_rect(sx - 2 * inset, sy - 2 * inset, rr, seg, (cx, cy))
            out.append(ring_xy(poly, z))
        return self.loft(out, cap_start=True, cap_end=True)

    def disc(self, r, seg=32, center=(0, 0, 0), normal='Z', thickness=0.0):
        prof = [(0.0, 0.0), (r, 0.0)]
        if thickness:
            prof += [(r, thickness), (0.0, thickness)]
        return self.revolve(prof, seg, axis=normal, center=center)

    def sphere(self, r, center=(0, 0, 0), seg=24, rings=12):
        prof = [(r * math.sin(math.pi * i / rings), -r * math.cos(math.pi * i / rings))
                for i in range(rings + 1)]
        return self.revolve(prof, seg, center=center)

    # -- output -------------------------------------------------------------
    def build(self, name, materials, shading='HARD', subsurf=0, attr=None,
              viewport_subsurf=None, auto_link=True):
        """Create the object.

        shading: 'HARD'   smooth + weighted normals (crisp flats, soft curves)
                 'SMOOTH' smooth shading only
                 'FLAT'   faceted
        subsurf: Catmull-Clark render levels (adds smooth shading).
        attr:    name for the per-face float attribute (``self.val``).
        """
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in self.verts], [],
                       [tuple(f) for f in self.faces])
        if not isinstance(materials, (list, tuple)):
            materials = [materials]
        for m in materials:
            me.materials.append(m)
        nf = len(me.polygons)
        if len(materials) > 1:
            me.polygons.foreach_set('material_index', self.face_mat[:nf])
        if shading == 'FLAT' and not subsurf:
            sm = [False] * nf
        elif subsurf or shading == 'SMOOTH':
            sm = [True] * nf
        else:
            sm = [bool(s) for s in self.face_smooth[:nf]]
            if shading == 'HARD':
                sm = [True] * nf
        me.polygons.foreach_set('use_smooth', sm)
        if attr:
            a = me.attributes.new(attr, 'FLOAT', 'FACE')
            a.data.foreach_set('value', self.face_val[:nf])
        me.validate(clean_customdata=False)
        me.update()
        obj = bpy.data.objects.new(name, me)
        if auto_link:
            link(obj)
        if subsurf:
            m = obj.modifiers.new('Subdivision', 'SUBSURF')
            m.levels = subsurf if viewport_subsurf is None else viewport_subsurf
            m.render_levels = subsurf
            m.boundary_smooth = 'PRESERVE_CORNERS'
        elif shading == 'HARD':
            m = obj.modifiers.new('WeightedNormal', 'WEIGHTED_NORMAL')
            m.mode = 'FACE_AREA'
            m.weight = 100
            m.keep_sharp = True
        return obj


# ---------------------------------------------------------------------------
# Convenience one-shot builders
# ---------------------------------------------------------------------------

def box_obj(name, mn, mx, mat, bevel=0.0, seg=2):
    mb = MeshBuilder()
    if bevel > 0:
        size = [b - a for a, b in zip(mn, mx)]
        center = [(a + b) / 2.0 for a, b in zip(mn, mx)]
        mb.rounded_box(size, bevel, center, seg=seg, zseg=seg)
        return mb.build(name, mat, 'HARD')
    mb.box(mn, mx)
    return mb.build(name, mat, 'FLAT')


def revolve_obj(name, profile, mat, seg=32, axis='Z', center=(0, 0, 0),
                cap_start=True, cap_end=True, shading='HARD', subsurf=0, **kw):
    mb = MeshBuilder()
    mb.revolve(profile, seg, axis, center, cap_start, cap_end, **kw)
    return mb.build(name, mat, shading, subsurf)


def tube_obj(name, path, radius, mat, seg=16, caps=True, shading='HARD'):
    mb = MeshBuilder()
    mb.tube(path, radius, seg, caps, caps)
    return mb.build(name, mat, shading)


# ---------------------------------------------------------------------------
# Rectangle maths (tiles, walls with openings)
# ---------------------------------------------------------------------------

def rect_subtract(r, h):
    """r - h for axis aligned rects (u0, v0, u1, v1). Returns list of rects."""
    u0, v0, u1, v1 = r
    h0, k0, h1, k1 = h
    if h0 >= u1 or h1 <= u0 or k0 >= v1 or k1 <= v0:
        return [r]
    out = []
    if k0 > v0:
        out.append((u0, v0, u1, k0))
    if k1 < v1:
        out.append((u0, k1, u1, v1))
    mv0, mv1 = max(v0, k0), min(v1, k1)
    if h0 > u0:
        out.append((u0, mv0, h0, mv1))
    if h1 < u1:
        out.append((h1, mv0, u1, mv1))
    return out


def rects_minus(rects, holes, min_size=0.004):
    for h in holes:
        nxt = []
        for r in rects:
            nxt.extend(rect_subtract(r, h))
        rects = nxt
    return [r for r in rects if r[2] - r[0] > min_size and r[3] - r[1] > min_size]


def panel_with_holes(mb, width, height, holes, mapper, w=0.0):
    """Flat rectangle (0..width, 0..height) with rectangular openings."""
    us = sorted({0.0, width} | {min(max(h[0], 0), width) for h in holes}
                | {min(max(h[2], 0), width) for h in holes})
    vs = sorted({0.0, height} | {min(max(h[1], 0), height) for h in holes}
                | {min(max(h[3], 0), height) for h in holes})
    for i in range(len(us) - 1):
        for j in range(len(vs) - 1):
            cu = (us[i] + us[i + 1]) / 2.0
            cv = (vs[j] + vs[j + 1]) / 2.0
            if any(h[0] <= cu <= h[2] and h[1] <= cv <= h[3] for h in holes):
                continue
            ids = [mb.v(mapper(us[i], vs[j], w)), mb.v(mapper(us[i + 1], vs[j], w)),
                   mb.v(mapper(us[i + 1], vs[j + 1], w)), mb.v(mapper(us[i], vs[j + 1], w))]
            mb.f(ids, smooth=False)


def tile_field(mb, width, height, tile_w, tile_h, grout, thickness, mapper,
               holes=(), chamfer=0.0015, pattern='stack', start=(0.0, 0.0),
               rng=None, lippage=0.0004, tilt=0.002):
    """Lay real 3D tiles over a 0..width x 0..height region.

    Tiles are cut at the region border and around rectangular ``holes``.
    The visible tile face sits at w=0 and the tile extends to w=-thickness,
    so the region describes the *finished* surface. Each tile stores a random
    value in the builder attribute (for colour variation in the shader).
    """
    rng = rng or random.Random(1)
    pu, pv = tile_w + grout, tile_h + grout
    nu = int(math.ceil((width - start[0]) / pu)) + 2
    nv = int(math.ceil((height - start[1]) / pv)) + 2
    region = (0.0, 0.0, width, height)
    c1 = chamfer * 0.35
    for j in range(-1, nv):
        shift = (pu / 2.0 if (pattern == 'running' and j % 2) else 0.0)
        for i in range(-1, nu):
            u0 = start[0] + i * pu + shift + grout / 2.0
            v0 = start[1] + j * pv + grout / 2.0
            u1, v1 = u0 + tile_w, v0 + tile_h
            # clip to region
            cu0, cv0 = max(u0, region[0]), max(v0, region[1])
            cu1, cv1 = min(u1, region[2]), min(v1, region[3])
            if cu1 - cu0 < 0.004 or cv1 - cv0 < 0.004:
                continue
            pieces = rects_minus([(cu0, cv0, cu1, cv1)], holes)
            mb.val = rng.random()
            dw = rng.uniform(-lippage, lippage)
            tu = rng.uniform(-tilt, tilt)
            tv = rng.uniform(-tilt, tilt)
            for (a0, b0, a1, b1) in pieces:
                _tile(mb, a0, b0, a1, b1, thickness, chamfer, c1, mapper, dw, tu, tv,
                      (u0 + u1) / 2, (v0 + v1) / 2)


def _tile(mb, u0, v0, u1, v1, t, ch, c1, mapper, dw, tu, tv, cu, cv):
    ch = min(ch, (u1 - u0) / 3.0, (v1 - v0) / 3.0)
    c1 = min(c1, ch)

    def P(u, v, w):
        # small random lippage/tilt per tile, like a hand-laid surface
        return mapper(u, v, w + dw + (u - cu) * tu + (v - cv) * tv)

    rings = [
        [P(u0, v0, -t), P(u1, v0, -t), P(u1, v1, -t), P(u0, v1, -t)],
        [P(u0, v0, -ch), P(u1, v0, -ch), P(u1, v1, -ch), P(u0, v1, -ch)],
        [P(u0 + c1, v0 + c1, -c1), P(u1 - c1, v0 + c1, -c1),
         P(u1 - c1, v1 - c1, -c1), P(u0 + c1, v1 - c1, -c1)],
        [P(u0 + ch, v0 + ch, 0), P(u1 - ch, v0 + ch, 0),
         P(u1 - ch, v1 - ch, 0), P(u0 + ch, v1 - ch, 0)],
    ]
    mb.loft(rings, cap_end=True)
