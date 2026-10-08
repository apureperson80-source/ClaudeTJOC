"""Mesh helpers for the props.

Builds on the bathroom toolkit (``bathroom_gen.geo``) and adds:

* :class:`Builder` -- a MeshBuilder with optional per-face UVs, used for
  printed graphics (snack packs, screens, photos);
* real-geometry text, so labels, legends and logos are separate meshes with a
  single colour instead of being painted into a texture;
* small frame/matrix helpers.

Every part is built as its own **single-material object**: each object in the
file has exactly one colour, which makes recolouring easy and maps one-to-one
onto engines where a part carries a single colour/material (e.g. Roblox).
"""

import math

import bpy
from mathutils import Matrix, Vector

from bathroom_gen.geo import MeshBuilder, link
from .materials import mat as _mat

TAU = 2.0 * math.pi


# ---------------------------------------------------------------------------
# Frames
# ---------------------------------------------------------------------------

def frame(origin=(0, 0, 0), x=(1, 0, 0), y=(0, 1, 0)):
    """4x4 matrix with local X/Y axes ``x``/``y`` (Z = X x Y) at ``origin``."""
    X = Vector(x).normalized()
    Y = Vector(y)
    Y = (Y - X * Y.dot(X)).normalized()
    Z = X.cross(Y)
    m = Matrix.Identity(4)
    for i in range(3):
        m[i][0], m[i][1], m[i][2], m[i][3] = X[i], Y[i], Z[i], origin[i]
    return m


def front_frame(origin, normal='-Y'):
    """Frame for flat details (text, labels) lying on a face with the given
    outward normal, text reading left to right as seen from outside."""
    axes = {
        '-Y': ((1, 0, 0), (0, 0, 1)),
        '+Y': ((-1, 0, 0), (0, 0, 1)),
        '+X': ((0, 1, 0), (0, 0, 1)),
        '-X': ((0, -1, 0), (0, 0, 1)),
        '+Z': ((1, 0, 0), (0, 1, 0)),
        '-Z': ((1, 0, 0), (0, -1, 0)),
    }
    x, y = axes[normal]
    return frame(origin, x, y)


def rot_x(a):
    return Matrix.Rotation(a, 4, 'X')


def rot_y(a):
    return Matrix.Rotation(a, 4, 'Y')


def rot_z(a):
    return Matrix.Rotation(a, 4, 'Z')


def trans(v):
    return Matrix.Translation(Vector(v))


# ---------------------------------------------------------------------------
# UV-aware builder
# ---------------------------------------------------------------------------

def _newell(pts):
    n = Vector((0.0, 0.0, 0.0))
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        n.x += (a.y - b.y) * (a.z + b.z)
        n.y += (a.z - b.z) * (a.x + b.x)
        n.z += (a.x - b.x) * (a.y + b.y)
    return n


class Builder(MeshBuilder):
    """MeshBuilder with optional per-face UVs and single-material output."""

    def __init__(self):
        super().__init__()
        self.face_uv = []

    def f(self, idx, smooth=None, uv=None):
        super().f(idx, smooth)
        self.face_uv.append(uv)

    def merge(self, other, matrix=None):
        super().merge(other, matrix)
        self.face_uv.extend(getattr(other, 'face_uv', None) or [None] * len(other.faces))

    def quad(self, pts, uv=None, smooth=False):
        self.f([self.v(p) for p in pts], smooth=smooth, uv=uv)

    def loft_uv(self, rings, uvs, closed=False, cap_start=False, cap_end=False,
                cap_uv=None):
        """Loft with UVs. ``uvs`` matches ``rings`` point for point; for closed
        rings each uv ring carries one extra entry for the wrap-around seam.
        ``cap_uv(point) -> (u, v)`` maps cap vertices."""
        rings = [[Vector(p) for p in r] for r in rings]
        n = len(rings[0])
        idx = [[self.v(p) for p in r] for r in rings]
        m = n if closed else n - 1
        for k in range(len(rings) - 1):
            A, B, ua, ub = idx[k], idx[k + 1], uvs[k], uvs[k + 1]
            for i in range(m):
                j = (i + 1) % n
                self.f([A[i], A[j], B[j], B[i]], uv=[ua[i], ua[i + 1], ub[i + 1], ub[i]])
        for flag, k, nb in ((cap_start, 0, 1), (cap_end, -1, -2)):
            if not flag:
                continue
            ring = rings[k]
            normal = _newell(ring)
            away = sum(ring, Vector()) / n - sum(rings[nb], Vector()) / n
            face = list(idx[k])
            pts = list(ring)
            if normal.dot(away) < 0:
                face.reverse()
                pts.reverse()
            self.f(face, uv=[cap_uv(p) for p in pts] if cap_uv else None)
        return idx

    def grid(self, fn, nu, nv, uv=None, closed_u=False):
        """Surface patch from ``fn(s, t) -> point`` with s, t in 0..1.
        ``uv(s, t) -> (u, v)`` optionally maps it."""
        cols = nu + (0 if closed_u else 1)
        ids = [[self.v(fn(i / nu, j / nv)) for i in range(cols)] for j in range(nv + 1)]
        for j in range(nv):
            for i in range(nu):
                i2 = (i + 1) % cols if closed_u else i + 1
                face = [ids[j][i], ids[j][i2], ids[j + 1][i2], ids[j + 1][i]]
                uvs = None
                if uv is not None:
                    s0, s1, t0, t1 = i / nu, (i + 1) / nu, j / nv, (j + 1) / nv
                    uvs = [uv(s0, t0), uv(s1, t0), uv(s1, t1), uv(s0, t1)]
                self.f(face, uv=uvs)
        return ids

    # -- output -------------------------------------------------------------
    def build(self, name, material, shading='HARD', subsurf=0, viewport_subsurf=None,
              sharp_angle=30.0, uv_scale=1.0, auto_link=True):
        """Create the object (one material).

        shading: 'HARD'   smooth + weighted normals (crisp flats, soft bevels)
                 'AUTO'   smooth, edges sharper than ``sharp_angle`` split
                 'SMOOTH' smooth shading only
                 'FLAT'   faceted
        Faces without explicit UVs get a box projection (``uv_scale`` metres
        per texture repeat) whenever any face has UVs.
        """
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in self.verts], [], [tuple(f) for f in self.faces])
        me.materials.append(material)
        if any(u is not None for u in self.face_uv):
            flat = []
            for face, uv in zip(self.faces, self.face_uv):
                if uv is None:
                    pts = [self.verts[i] for i in face]
                    nrm = _newell(pts)
                    ax = max(range(3), key=lambda a: abs(nrm[a]))
                    a, b = ((1, 2), (0, 2), (0, 1))[ax]
                    uv = [(p[a] / uv_scale, p[b] / uv_scale) for p in pts]
                for u in uv:
                    flat.extend((u[0], u[1]))
            layer = me.uv_layers.new(name='UVMap')
            layer.data.foreach_set('uv', flat)
        nf = len(me.polygons)
        if shading == 'FLAT' and not subsurf:
            sm = [False] * nf
        elif shading == 'MIXED':
            sm = [bool(s) for s in self.face_smooth[:nf]]
        else:
            sm = [True] * nf
        me.polygons.foreach_set('use_smooth', sm)
        me.validate(clean_customdata=False)
        if shading == 'AUTO' and hasattr(me, 'set_sharp_from_angle'):
            me.set_sharp_from_angle(angle=math.radians(sharp_angle))
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


class Parts:
    """Builders keyed by (part name, material); each becomes one object, so
    every object has a single colour. ``shading`` is remembered per part."""

    def __init__(self, prefix):
        self.prefix = prefix
        self.items = {}
        self.shading = {}

    def __call__(self, name, material, shading=None):
        key = (name, material)
        if key not in self.items:
            self.items[key] = Builder()
        if shading:
            self.shading[name] = shading
        return self.items[key]

    def build(self, shading=None):
        objs = []
        for (name, material), mb in self.items.items():
            if not mb.faces:
                continue
            sh = (shading or {}).get(name) or self.shading.get(name, 'HARD')
            m = _mat(material) if isinstance(material, str) else material
            objs.append(mb.build('%s - %s' % (self.prefix, name), m, sh))
        return objs


# ---------------------------------------------------------------------------
# Real-geometry text
# ---------------------------------------------------------------------------

_TEXT_CACHE = {}


def text_geometry(text, size=0.01, align='CENTER', valign='CENTER', extrude=0.0, spacing=1.0):
    """(verts, faces) of ``text`` set in Blender's built-in font.

    The text lies in the local XY plane facing +Z; ``size`` is the font size
    in metres. (The outline offset is left at 0: offsetting breaks the fill
    of glyphs with counters, such as 6 and 9.)"""
    key = (text, size, align, valign, extrude, spacing)
    hit = _TEXT_CACHE.get(key)
    if hit is not None:
        return hit
    cu = bpy.data.curves.new('_text', 'FONT')
    cu.body = text
    cu.size = size
    cu.align_x = align
    cu.align_y = valign
    cu.extrude = extrude
    cu.space_character = spacing
    ob = bpy.data.objects.new('_text', cu)
    me = bpy.data.meshes.new_from_object(ob)
    verts = [v.co.copy() for v in me.vertices]
    faces = [tuple(p.vertices) for p in me.polygons]
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    bpy.data.meshes.remove(me)
    _TEXT_CACHE[key] = (verts, faces)
    return verts, faces


def text_extent(text, **kw):
    """Width/height of the text's bounding box (metres)."""
    verts, _ = text_geometry(text, **kw)
    if not verts:
        return 0.0, 0.0
    xs = [v.x for v in verts]
    ys = [v.y for v in verts]
    return max(xs) - min(xs), max(ys) - min(ys)


def add_text(mb, text, matrix, fit=None, **kw):
    """Append ``text`` to builder ``mb`` placed by ``matrix``.

    ``fit=(w, h)`` scales the text down (never up) to fit that box."""
    verts, faces = text_geometry(text, **kw)
    m = Matrix(matrix)
    if fit is not None and verts:
        w, h = text_extent(text, **kw)
        s = min(1.0, fit[0] / max(w, 1e-9), fit[1] / max(h, 1e-9))
        m = m @ Matrix.Scale(s, 4)
    base = len(mb.verts)
    mb.verts.extend(m @ v for v in verts)
    for f in faces:
        mb.f([base + i for i in f], smooth=False)


def text_obj(name, text, material, matrix, **kw):
    """A separate object holding one piece of text."""
    mb = Builder()
    add_text(mb, text, matrix, **kw)
    return mb.build(name, material, 'FLAT')
