"""Screens and computer gear: the flat-screen TV (reference photo 4), desktop
monitors, video-wall displays, a laptop, keyboard and mouse (photo 3).

Displays face -Y. Free-standing items have their origin on the surface they
stand on; the video-wall display has its back on the wall plane y = 0.

Screens with live content use :func:`materials.screen_material`. Monitors,
video-wall displays and the laptop share one screen material whose image is
the *screens atlas*; each collection instance picks its own picture through
the custom properties ``scr_min`` / ``scr_size`` (see ``scenes.screen_props``).
"""

import math

import bpy
from mathutils import Matrix, Vector

from bathroom_gen.geo import group, ring_xz, rounded_rect
from .facility import screen_tile
from .materials import screen_material
from .mesh import Parts, add_text, front_frame

BRAND = 'VISTA'          # made-up brand on the bezels


# ---------------------------------------------------------------------------
# Screen images
# ---------------------------------------------------------------------------

def _placeholder(name, w=64, h=36):
    img = bpy.data.images.get(name)
    if img is None:
        img = bpy.data.images.new(name, w, h)
        img.generated_type = 'UV_GRID'
    return img


def atlas_screen_material():
    """Shared material for every monitor/video-wall/laptop screen."""
    img = bpy.data.images.get('Screens Atlas') or _placeholder('Screens Atlas')
    return screen_material('Monitor Screen', img, strength=0.85, atlas=True)


def tv_screen_material():
    img = bpy.data.images.get('TV Wallpaper') or _placeholder('TV Wallpaper')
    # anti-glare panel: little specular, so the picture stays rich in a bright room
    return screen_material('TV Screen', img, strength=2.2, rough=0.25, coat=0.0, specular=0.15)


# ---------------------------------------------------------------------------
# Generic flat panel
# ---------------------------------------------------------------------------

def _rr(w, h, r, cx=0.0, cz=0.0, seg=4):
    return rounded_rect(w, h, max(r, 0.0004), seg, (cx, cz))


def flat_panel(P, aw, ah, cz, bezel, frame_t, back, corner=0.003, recess=0.0012,
               bezel_mat='plastic_black_satin', back_mat='plastic_black_matte', screen=None):
    """Display body centred on x = 0 with the screen centre at height cz.

    ``bezel`` = (side, top, bottom) widths, ``frame_t`` the depth of the
    bezel band, ``back`` a list of (inset, y) steps for the back shell.
    Returns the outer size (W, H, z_bottom)."""
    side, top, bottom = bezel
    W, H = aw + 2 * side, ah + top + bottom
    zc = cz + (top - bottom) / 2                # centre of the outline
    outer = _rr(W, H, corner, 0.0, zc)
    inner = _rr(aw, ah, 0.0006, 0.0, cz)
    bz = P('Bezel', bezel_mat, 'HARD')
    bz.loft([ring_xz(outer, frame_t), ring_xz(outer, 0.0), ring_xz(inner, 0.0),
             ring_xz(inner, recess)])
    bk = P('Back cover', back_mat, 'HARD')
    rings = [ring_xz(_rr(W - 2 * i, H - 2 * i, max(corner - i, 0.0006) + i * 0.5, 0.0, zc), y)
             for (i, y) in reversed(back)]
    rings.append(ring_xz(outer, frame_t))
    bk.loft(rings, cap_start=True)
    if screen is not None:
        sc = P('Screen', screen, 'FLAT')
        y = recess
        sc.quad([Vector((-aw / 2, y, cz - ah / 2)), Vector((aw / 2, y, cz - ah / 2)),
                 Vector((aw / 2, y, cz + ah / 2)), Vector((-aw / 2, y, cz + ah / 2))],
                uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
    return W, H, zc - H / 2


def _box_shell(mb, w, h, cz, y0, y1, r, taper=0.0):
    """Rounded block on a panel back, from y0 out to y1 (capped)."""
    a = _rr(w, h, r, 0.0, cz)
    b = _rr(w - 2 * taper, h - 2 * taper, max(r - taper, 0.0005), 0.0, cz)
    mb.loft([ring_xz(b, y1), ring_xz(a, y0)], cap_start=True)


def _default_picture(objs, tile):
    """Picture shown when the screen is not a configured instance."""
    for ob in objs:
        if ob.name.endswith(' - Screen'):
            for k, v in screen_tile(tile).items():
                ob[k] = v


def _logo(P, text, x, z, y, size, material='print_grey'):
    add_text(P('Logo', material, 'FLAT'), text, front_frame((x, y, z), '-Y'), size=size)


# ---------------------------------------------------------------------------
# Flat-screen TV
# ---------------------------------------------------------------------------

def tv_50(name='Flat-screen TV (50 in)'):
    """50" thin-bezel TV on splayed feet; screen shows the landscape."""
    aw, ah = 1.107, 0.623
    lift = 0.085                       # panel bottom above the stand surface
    bezel = (0.0075, 0.0075, 0.0135)
    cz = lift + bezel[2] + ah / 2
    with group(name) as root:
        P = Parts('TV')
        W, H, zb = flat_panel(P, aw, ah, cz, bezel, 0.011,
                              [(0.004, 0.022), (0.012, 0.028)], corner=0.003,
                              screen=tv_screen_material())
        back = P('Back cover', 'plastic_black_matte')
        # electronics box with sloped sides on the lower back
        _box_shell(back, 0.78, 0.40, zb + 0.25, 0.026, 0.074, 0.02, taper=0.03)
        _logo(P, BRAND, 0.0, zb + 0.0068, -0.0003, 0.0085)
        led = P('Standby LED', 'led_red', 'FLAT')
        led.quad([Vector((0.18, -0.0003, zb + 0.0055)), Vector((0.184, -0.0003, zb + 0.0055)),
                  Vector((0.184, -0.0003, zb + 0.0075)), Vector((0.18, -0.0003, zb + 0.0075))])
        dark = P('Ports and vents', 'rubber_black', 'FLAT')
        # VESA holes on the back of the box
        for x in (-0.1, 0.1):
            for z in (zb + 0.15, zb + 0.35):
                dark.revolve([(0.0, 0.0), (0.005, 0.0)], 12, axis='Y', center=(x, 0.0745, z))
        # vent slots along the sloping top of the box
        def top_z(y):
            return zb + 0.45 - 0.03 * (y - 0.026) / 0.048 + 0.0006
        for k in range(18):
            x = -0.30 + k * 0.0355
            dark.quad([Vector((x, 0.034, top_z(0.034))), Vector((x, 0.062, top_z(0.062))),
                       Vector((x + 0.022, 0.062, top_z(0.062))), Vector((x + 0.022, 0.034, top_z(0.034)))])
        # connector panel on the back
        for k in range(6):
            x = 0.16 + k * 0.03
            dark.quad([Vector((x, 0.0746, zb + 0.09)), Vector((x + 0.018, 0.0746, zb + 0.09)),
                       Vector((x + 0.018, 0.0746, zb + 0.098)), Vector((x, 0.0746, zb + 0.098))][::-1])
        # splayed V feet
        feet = P('Feet', 'plastic_black_satin', 'SMOOTH')
        pads = P('Foot pads', 'rubber_black', 'SMOOTH')
        for sx in (-1, 1):
            x = sx * 0.455
            top = Vector((x, 0.03, zb + 0.004))
            for (dx, dy) in ((0.05, -0.11), (0.03, 0.13)):
                end = Vector((x + sx * dx, dy, 0.006))
                feet.tube([top, top.lerp(end, 0.5), end], 0.0075, seg=10)
                pads.revolve([(0.0, 0.0), (0.011, 0.0), (0.011, 0.006), (0.0, 0.006)], 12,
                             center=(end.x, end.y, 0.0))
        # power cord from the box down to the floor
        cord = P('Power cord', 'rubber_black', 'SMOOTH')
        cord.tube([(0.30, 0.06, zb + 0.08), (0.31, 0.10, zb + 0.02), (0.32, 0.13, 0.03),
                   (0.36, 0.20, 0.004), (0.55, 0.30, 0.004)], 0.0032, seg=8)
        P.build()
    return root


# ---------------------------------------------------------------------------
# Desktop monitor
# ---------------------------------------------------------------------------

def monitor_27(name='Desktop monitor (27 in)'):
    aw, ah = 0.597, 0.336
    bezel = (0.006, 0.006, 0.017)
    cz = 0.12 + bezel[2] + ah / 2
    with group(name) as root:
        P = Parts('Monitor')
        W, H, zb = flat_panel(P, aw, ah, cz, bezel, 0.01, [(0.004, 0.018), (0.01, 0.024)],
                              screen=atlas_screen_material())
        back = P('Back cover', 'plastic_black_matte')
        _box_shell(back, 0.30, 0.20, cz - 0.02, 0.022, 0.052, 0.03, taper=0.025)
        _logo(P, BRAND, 0.0, zb + 0.0075, -0.0003, 0.0075)
        led = P('Power LED', 'led_white', 'FLAT')
        led.quad([Vector((0.27, -0.0003, zb + 0.007)), Vector((0.273, -0.0003, zb + 0.007)),
                  Vector((0.273, -0.0003, zb + 0.009)), Vector((0.27, -0.0003, zb + 0.009))])
        stand = P('Stand', 'gunmetal', 'HARD')
        # base plate
        base = _rr(0.25, 0.19, 0.03)
        stand.loft([[Vector((p.x, p.y + 0.06, 0.0)) for p in base],
                    [Vector((p.x, p.y + 0.06, 0.009)) for p in base]], cap_start=True, cap_end=True)
        # neck rising from the back of the base to the panel hinge
        neck = _rr(0.07, 0.016, 0.006)
        path = [Vector((0.0, 0.11, 0.009)), Vector((0.0, 0.085, 0.17)), Vector((0.0, 0.07, cz - 0.02))]
        rings = []
        for p in path:
            rings.append([Vector((p.x + q.x, p.y + q.y, p.z)) for q in neck])
        stand.loft(rings, cap_end=True)
        hinge = P('Stand hinge', 'plastic_black_matte', 'HARD')
        hinge.rounded_box((0.09, 0.03, 0.06), 0.008, (0.0, 0.06, cz - 0.02))
        _default_picture(P.build(), 10)
    return root


# ---------------------------------------------------------------------------
# Video-wall display
# ---------------------------------------------------------------------------

def videowall_55(name='Video-wall display (55 in)'):
    """Ultra-narrow-bezel 55" panel on a pop-out wall mount (back at y = 0)."""
    aw, ah = 1.2096, 0.6804
    depth = 0.105                      # wall to screen
    with group(name) as root:
        P = Parts('Video wall')
        sub = Parts('_')
        W, H, zb = flat_panel(sub, aw, ah, 0.0, (0.0018, 0.0018, 0.0018), 0.012,
                              [(0.006, 0.035), (0.02, 0.045)], corner=0.0008,
                              screen=atlas_screen_material())
        # flat_panel builds with its front at y = 0; push it out from the wall
        m = Matrix.Translation((0.0, -depth, 0.0))
        for (pname, pm), mb in sub.items.items():
            P(pname, pm, sub.shading.get(pname)).merge(mb, m)
        mount = P('Wall mount', 'black_powder_coat', 'FLAT')
        for x in (-0.3, 0.3):
            mount.box((x - 0.03, -depth + 0.045, -0.25), (x + 0.03, -0.004, 0.25))
        mount.box((-0.42, -0.012, -0.29), (0.42, 0.0, -0.23))
        mount.box((-0.42, -0.012, 0.23), (0.42, 0.0, 0.29))
        _default_picture(P.build(), 1)
    return root


# ---------------------------------------------------------------------------
# Laptop
# ---------------------------------------------------------------------------

def laptop(name='Laptop', open_deg=112.0):
    w, d, t = 0.358, 0.245, 0.0175
    with group(name) as root:
        P = Parts('Laptop')
        body = P('Body', 'aluminium', 'HARD')
        body.rounded_box((w, d, t), 0.006, (0.0, 0.0, t / 2), seg=3, zseg=2)
        deck = P('Keyboard well', 'plastic_black_matte', 'FLAT')
        deck.box((-0.145, -0.035, t - 0.0004), (0.145, 0.085, t + 0.0002))
        keys = P('Keys', 'plastic_black_satin', 'HARD')
        legends = P('Key legends', 'print_white', 'FLAT')
        rows = ['QWERTYUIOP', 'ASDFGHJKL', 'ZXCVBNM']
        u = 0.0185
        for r in range(5):
            y = 0.072 - r * u
            if r in (1, 2, 3):
                letters = rows[r - 1]
                n = len(letters)
                x0 = -n * u / 2 + (r - 1) * u * 0.25
                for i, ch in enumerate(letters):
                    x = x0 + (i + 0.5) * u
                    keys.rounded_box((u * 0.86, u * 0.86, 0.0015), 0.0012, (x, y, t + 0.0009), seg=2,
                                     zseg=1)
                    add_text(legends, ch, front_frame((x - u * 0.2, y + u * 0.18, t + 0.0017), '+Z'),
                             size=0.0045)
                # wide end keys
                for x, ww in ((x0 - u * 0.75, u * 1.4), (x0 + n * u + u * 0.75, u * 1.4)):
                    keys.rounded_box((ww * 0.92, u * 0.86, 0.0015), 0.0012, (x, y, t + 0.0009), seg=2,
                                     zseg=1)
            elif r == 0:
                for i in range(13):
                    x = -0.13 + i * 0.0217
                    keys.rounded_box((0.019, 0.0105, 0.0015), 0.001, (x, y + 0.004, t + 0.0009), seg=2,
                                     zseg=1)
            else:
                keys.rounded_box((0.11, u * 0.86, 0.0015), 0.0012, (0.0, y, t + 0.0009), seg=2, zseg=1)
                for x in (-0.11, -0.085, 0.085, 0.11):
                    keys.rounded_box((u * 1.2, u * 0.86, 0.0015), 0.0012, (x, y, t + 0.0009), seg=2,
                                     zseg=1)
        pad = P('Touchpad', 'plastic_silver_grey', 'FLAT')
        pad.box((-0.055, -0.11, t - 0.0002), (0.055, -0.045, t + 0.0002))
        # lid with display, hinged at the back edge
        lid = Parts('_')
        lw, lh, lt = w, 0.235, 0.006
        lb = lid('Lid', 'aluminium', 'HARD')
        lb.rounded_box((lw, lt, lh), 0.004, (0.0, lt / 2, lh / 2), seg=2, zseg=2)
        bz = lid('Display bezel', 'plastic_black_satin', 'FLAT')
        bz.box((-lw / 2 + 0.004, -0.0006, 0.004), (lw / 2 - 0.004, 0.0, lh - 0.004))
        sc = lid('Screen', atlas_screen_material(), 'FLAT')
        sw, sh = 0.332, 0.187
        z0 = 0.022
        sc.quad([Vector((-sw / 2, -0.0008, z0)), Vector((sw / 2, -0.0008, z0)),
                 Vector((sw / 2, -0.0008, z0 + sh)), Vector((-sw / 2, -0.0008, z0 + sh))],
                uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
        add_text(lid('Logo', 'print_grey', 'FLAT'), BRAND, front_frame((0.0, -0.0008, 0.011), '-Y'),
                 size=0.006)
        m = (Matrix.Translation((0.0, d / 2 - 0.006, t)) @ Matrix.Rotation(math.radians(90 - open_deg), 4, 'X'))
        for (pname, pm), mb in lid.items.items():
            P(pname, pm, lid.shading.get(pname)).merge(mb, m)
        _default_picture(P.build(), 13)
    return root


# ---------------------------------------------------------------------------
# Keyboard & mouse
# ---------------------------------------------------------------------------

_ROWS = [
    # (label, width in units, gap before in units)
    [('ESC', 1, 0), ('F1', 1, 1), ('F2', 1, 0), ('F3', 1, 0), ('F4', 1, 0), ('F5', 1, 0.5),
     ('F6', 1, 0), ('F7', 1, 0), ('F8', 1, 0), ('F9', 1, 0.5), ('F10', 1, 0), ('F11', 1, 0),
     ('F12', 1, 0), ('PRT', 1, 0.5), ('SCR', 1, 0), ('PSE', 1, 0)],
    [('`', 1, 0), ('1', 1, 0), ('2', 1, 0), ('3', 1, 0), ('4', 1, 0), ('5', 1, 0), ('6', 1, 0),
     ('7', 1, 0), ('8', 1, 0), ('9', 1, 0), ('0', 1, 0), ('-', 1, 0), ('=', 1, 0), ('BKSP', 2, 0),
     ('INS', 1, 0.5), ('HOME', 1, 0), ('PGUP', 1, 0), ('NUM', 1, 0.5), ('/', 1, 0), ('*', 1, 0),
     ('-', 1, 0)],
    [('TAB', 1.5, 0), ('Q', 1, 0), ('W', 1, 0), ('E', 1, 0), ('R', 1, 0), ('T', 1, 0), ('Y', 1, 0),
     ('U', 1, 0), ('I', 1, 0), ('O', 1, 0), ('P', 1, 0), ('[', 1, 0), (']', 1, 0), ('\\', 1.5, 0),
     ('DEL', 1, 0.5), ('END', 1, 0), ('PGDN', 1, 0), ('7', 1, 0.5), ('8', 1, 0), ('9', 1, 0),
     ('+', 1, 0)],
    [('CAPS', 1.75, 0), ('A', 1, 0), ('S', 1, 0), ('D', 1, 0), ('F', 1, 0), ('G', 1, 0), ('H', 1, 0),
     ('J', 1, 0), ('K', 1, 0), ('L', 1, 0), (';', 1, 0), ("'", 1, 0), ('ENTER', 2.25, 0),
     ('4', 1, 4.0), ('5', 1, 0), ('6', 1, 0)],
    [('SHIFT', 2.25, 0), ('Z', 1, 0), ('X', 1, 0), ('C', 1, 0), ('V', 1, 0), ('B', 1, 0), ('N', 1, 0),
     ('M', 1, 0), (',', 1, 0), ('.', 1, 0), ('/', 1, 0), ('SHIFT', 2.75, 0), ('^', 1, 1.5),
     ('1', 1, 1.5), ('2', 1, 0), ('3', 1, 0), ('ENT', 1, 0)],
    [('CTRL', 1.25, 0), ('WIN', 1.25, 0), ('ALT', 1.25, 0), ('', 6.25, 0), ('ALT', 1.25, 0),
     ('FN', 1.25, 0), ('MENU', 1.25, 0), ('CTRL', 1.25, 0), ('<', 1, 0.5), ('v', 1, 0), ('>', 1, 0),
     ('0', 2, 0.5), ('.', 1, 0)],
]


def keyboard(name='Keyboard'):
    """Full-size low-profile keyboard, front edge towards -Y."""
    u = 0.019
    W, D = 23.0 * u + 0.016, 6.5 * u + 0.012
    with group(name) as root:
        P = Parts('Keyboard')
        body = P('Body', 'plastic_black_matte', 'HARD')
        # slight wedge: thicker at the back
        prof = _rr(W, D, 0.008)
        body.loft([[Vector((p.x, p.y, 0.0)) for p in prof],
                   [Vector((p.x, p.y, 0.012 + 0.006 * (p.y + D / 2) / D)) for p in prof]],
                  cap_start=True, cap_end=True)
        keys = P('Keys', 'plastic_black_satin', 'HARD')
        legends = P('Key legends', 'print_white', 'FLAT')
        x_left = -W / 2 + 0.008
        for r, row in enumerate(_ROWS):
            y = D / 2 - 0.006 - (r + 0.5) * u - (0.25 * u if r else 0.0)
            zt = 0.012 + 0.006 * (y + D / 2) / D
            x = x_left
            for label, wu, gap in row:
                x += gap * u
                kw = wu * u
                cx = x + kw / 2
                tall = label in ('+', 'ENT') and r in (2, 4)
                ky0 = y - (u if tall else 0.0)
                keys.rounded_box((kw - 0.003, (2 * u if tall else u) - 0.003, 0.007), 0.0016,
                                 (cx, (ky0 + y) / 2, zt + 0.0025), seg=2, zseg=1)
                if label:
                    size = 0.0042 if len(label) == 1 else 0.0026
                    add_text(legends, label,
                             front_frame((cx - (kw / 2 - 0.0045 if len(label) > 1 else 0.0025),
                                          y + 0.0025, zt + 0.006), '+Z'),
                             size=size, align='LEFT' if len(label) > 1 else 'CENTER')
                x += kw
        P.build()
    return root


def mouse(name='Mouse'):
    """Right-handed mouse, buttons towards -Y."""
    with group(name) as root:
        P = Parts('Mouse')
        shell = P('Shell', 'plastic_black_satin', 'SMOOTH')
        L = 0.118
        rings = []
        n = 14
        for k in range(n + 1):
            t = k / n
            y = -L / 2 + L * t
            # width and height profiles along the length (hump towards the back)
            wv = 0.030 + 0.006 * math.sin(math.pi * t) - 0.004 * t
            hv = 0.006 + 0.031 * math.sin(math.pi * (0.25 + 0.7 * t)) ** 0.8
            if k in (0, n):
                wv *= 0.55
                hv *= 0.55
            ring = []
            m = 20
            for i in range(m):
                a = 2 * math.pi * i / m
                cx, sz = math.cos(a), math.sin(a)
                x = wv * (abs(cx) ** 0.7) * math.copysign(1, cx)
                z = hv * max(sz, 0) ** 0.8 if sz > 0 else 0.002 * sz
                ring.append(Vector((x, y, z + 0.002)))
            rings.append(ring)
        shell.loft(rings, cap_start=True, cap_end=True)
        wheel = P('Scroll wheel', 'rubber_black', 'SMOOTH')
        wheel.revolve([(0.0, -0.0035), (0.0085, -0.0035), (0.0095, 0.0), (0.0085, 0.0035), (0.0, 0.0035)], 18,
                      axis='X', center=(0.0, -0.032, 0.0315))
        P.build()
    return root
