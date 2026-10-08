"""CCTV sets: the rooms the control-room cameras watch.

Each set is a closed room (so cameras see only their own room) placed along
the X axis, furnished with collection instances from the prop library --
the vending machines stand in the break room, the printers in the print room,
the boxes fill the warehouse and the TV plays in the lobby. Every set has one
or two CCTV cameras; their renders become the video-wall feeds.
"""

import math
import random

from mathutils import Vector

from bathroom_gen.geo import new_collection, target
from .materials import mat
from .mesh import Builder
from .studio import area_light, camera

CCTV_LENS = 15.0
FEEDS = []          # (camera object, label) in feed order


def _room(name, ox, W, D, H, wall='wall_light', floor='floor_vinyl', ceiling='ceiling_tile',
          lib=None, panels=(), panel_power=40.0):
    """Inward-facing box room with its corner at (ox, 0, 0)."""
    V = Vector
    f = Builder()
    f.quad([V((ox, 0, 0)), V((ox + W, 0, 0)), V((ox + W, D, 0)), V((ox, D, 0))])
    f.build(name + ' floor', mat(floor), 'FLAT')
    c = Builder()
    c.quad([V((ox, 0, H)), V((ox, D, H)), V((ox + W, D, H)), V((ox + W, 0, H))])
    c.build(name + ' ceiling', mat(ceiling), 'FLAT')
    w = Builder()
    w.quad([V((ox, 0, 0)), V((ox, D, 0)), V((ox, D, H)), V((ox, 0, H))])               # left
    w.quad([V((ox + W, 0, 0)), V((ox + W, 0, H)), V((ox + W, D, H)), V((ox + W, D, 0))])  # right
    w.quad([V((ox, D, 0)), V((ox + W, D, 0)), V((ox + W, D, H)), V((ox, D, H))])        # back
    w.quad([V((ox, 0, 0)), V((ox, 0, H)), V((ox + W, 0, H)), V((ox + W, 0, 0))])        # front
    w.build(name + ' walls', mat(wall), 'FLAT')
    sk = Builder()
    t, hs = 0.012, 0.09
    sk.box((ox, 0, 0), (ox + t, D, hs))
    sk.box((ox + W - t, 0, 0), (ox + W, D, hs))
    sk.box((ox, D - t, 0), (ox + W, D, hs))
    sk.box((ox, 0, 0), (ox + W, t, hs))
    sk.build(name + ' skirting', mat('plastic_dark_grey'), 'FLAT')
    for (x, y) in panels:
        e = lib.place('led_panel', (ox + x, y, H))
        e.scale = (1.0, 1.0, 1.0)
    if panels:
        # soft bounce so the corners are not black on camera
        area_light(name + ' fill', (ox + W / 2, D / 2, H - 0.05), (ox + W / 2, D / 2, 0.0),
                   panel_power * len(panels) * 0.6, min(W, D) * 0.8, color=(0.97, 0.98, 1.0))


def _cctv(name, label, loc, look, lens=CCTV_LENS):
    cam = camera(name, loc, look, lens)
    cam.data.clip_start = 0.05
    FEEDS.append((cam, label))
    return cam


def _grid(x0, x1, y0, y1, step):
    pts = []
    x = x0
    while x <= x1 + 1e-6:
        y = y0
        while y <= y1 + 1e-6:
            pts.append((x, y))
            y += step
        x += step
    return pts


# ---------------------------------------------------------------------------
# Sets
# ---------------------------------------------------------------------------

def break_room(lib, ox):
    W, D, H = 6.0, 5.0, 2.8
    _room('Break room', ox, W, D, H, wall='wall_beige', lib=lib, panels=_grid(1.2, 4.8, 1.2, 3.6, 1.2))
    P = lib.place
    P('vending_classic', (ox + 1.25, D, 0.0))
    P('vending_modern', (ox + 2.5, D, 0.0))
    P('waste_bin', (ox + 0.45, D - 0.3, 0.0))
    # sideboard with the TV on the right
    sb = Builder()
    sb.rounded_box((1.5, 0.45, 0.72), 0.01, (ox + 4.65, D - 0.25, 0.36), seg=2, zseg=2)
    sb.build('Break room sideboard', mat('laminate_white'), 'HARD')
    P('tv', (ox + 4.65, D - 0.3, 0.72))
    P('table_round', (ox + 2.6, 2.1, 0.0))
    for k, a in enumerate((200, 320, 80)):
        r = math.radians(a)
        P('chair_stacking', (ox + 2.6 + 0.72 * math.cos(r), 2.1 + 0.72 * math.sin(r), 0.0),
          rot_z=r - math.pi / 2)
    P('mug', (ox + 2.45, 2.0, 0.74))
    P('palm', (ox + 5.5, 0.6, 0.0))
    P('door', (ox, 1.1, 0.0), rot_z=math.radians(90))
    P('exit_sign', (ox, 1.1, 2.35), rot_z=math.radians(90))
    _cctv('CCTV 01 - Break room', 'BREAK ROOM', (ox + W - 0.25, 0.25, H - 0.15), (ox + 2.2, D - 1.0, 0.7))
    _cctv('CCTV 10 - Vending', 'VENDING AREA', (ox + 0.3, 1.6, H - 0.2), (ox + 2.0, D - 0.4, 1.0), lens=20)


def warehouse(lib, ox, seed=5):
    rng = random.Random(seed)
    W, D, H = 14.0, 12.0, 7.0
    _room('Warehouse', ox, W, D, H, wall='wall_light', floor='floor_concrete', ceiling='wall_dark',
          lib=lib, panels=_grid(2.0, 12.0, 2.0, 10.0, 2.5), panel_power=120.0)
    P = lib.place
    # two runs of racking either side of an aisle
    bays = 4
    for row_y, flip in ((4.0, math.pi), (8.2, 0.0)):
        for b in range(bays):
            x = ox + 2.0 + 1.35 + b * 2.7
            P('pallet_rack', (x, row_y, 0.0), rot_z=flip)
            for level, z in ((0, 0.0), (1, 1.5), (2, 3.0)):
                for k in (-0.65, 0.65):
                    if rng.random() < 0.12:
                        continue
                    px = x + k
                    P('pallet', (px, row_y, z), rot_z=flip)
                    _box_stack(lib, px, row_y, z + 0.144, rng, layers=2 if level < 2 else 1)
    # floor markings along the aisle
    lines = Builder()
    for y in (5.0, 7.2):
        lines.quad([Vector((ox + 1.0, y - 0.05, 0.002)), Vector((ox + W - 1.0, y - 0.05, 0.002)),
                    Vector((ox + W - 1.0, y + 0.05, 0.002)), Vector((ox + 1.0, y + 0.05, 0.002))])
    lines.build('Warehouse floor lines', mat('floor_line_yellow'), 'FLAT')
    # despatch area: pallets of boxes and a couple of open cartons
    for k, (x, y) in enumerate(((1.6, 1.6), (3.2, 1.4), (5.0, 1.8))):
        P('pallet', (ox + x, y, 0.0), rot_z=rng.uniform(-0.1, 0.1))
        _box_stack(lib, ox + x, y, 0.144, rng, layers=rng.randint(1, 3))
    P('box_regular_open', (ox + 7.0, 1.5, 0.0), rot_z=0.4)
    P('box_tall_open', (ox + 7.8, 1.9, 0.0), rot_z=-0.3)
    P('box_closed', (ox + 6.5, 2.2, 0.0), rot_z=0.2)
    _cctv('CCTV 02 - Warehouse aisle', 'WAREHOUSE AISLE', (ox + 0.4, 6.1, 5.2), (ox + 9.0, 6.1, 0.8),
          lens=17)
    _cctv('CCTV 03 - Despatch', 'DESPATCH', (ox + W - 0.4, 0.4, 4.2), (ox + 4.0, 2.8, 0.0))


def _box_stack(lib, cx, cy, z, rng, layers=2):
    """2 x 3 cartons per layer on a 1.2 x 0.8 pallet."""
    for l in range(layers):
        for i in range(3):
            for j in range(2):
                if l == layers - 1 and rng.random() < 0.15:
                    continue
                x = cx - 0.4 + i * 0.4
                y = cy - 0.2 + j * 0.4
                lib.place('box_closed', (x + rng.uniform(-0.01, 0.01), y + rng.uniform(-0.01, 0.01),
                                         z + l * 0.308), rot_z=math.pi / 2 + rng.uniform(-0.03, 0.03))


def print_room(lib, ox):
    W, D, H = 3.8, 3.2, 2.7
    _room('Print room', ox, W, D, H, wall='wall_blue_grey', lib=lib, panels=[(1.3, 1.6), (2.6, 1.6)])
    P = lib.place
    P('office_desk', (ox + 1.5, D - 0.4, 0.0))
    P('printer_inktank', (ox + 1.15, D - 0.42, 0.74))
    P('printer_laser', (ox + 1.95, D - 0.4, 0.74), rot_z=0.05)
    P('shelving_unit', (ox + 3.15, D - 0.3, 0.0))
    for k, z in enumerate((0.08, 0.5125, 0.945)):          # shelf tops of the unit
        P('box_closed', (ox + 2.95, D - 0.3, z), rot_z=math.pi / 2 + 0.05 * k)
        P('box_closed', (ox + 3.38, D - 0.3, z), rot_z=math.pi / 2 - 0.04 * k)
    P('box_regular_open', (ox + 2.9, 1.3, 0.0), rot_z=-0.5)
    P('box_closed', (ox + 0.45, 0.9, 0.0), rot_z=0.3)
    P('waste_bin', (ox + 0.35, D - 0.4, 0.0))
    P('door', (ox + W, 0.9, 0.0), rot_z=math.radians(-90))
    _cctv('CCTV 04 - Print room', 'PRINT ROOM', (ox + 0.25, 0.25, H - 0.15), (ox + 2.1, D - 0.5, 0.55),
          lens=17)


def office(lib, ox, seed=8):
    rng = random.Random(seed)
    W, D, H = 8.0, 6.5, 2.8
    _room('Office', ox, W, D, H, wall='wall_blue_grey', lib=lib, panels=_grid(1.3, 6.7, 1.3, 5.2, 1.3))
    P = lib.place
    for row, y in enumerate((2.2, 4.4)):
        for col, x in enumerate((1.6, 3.2, 5.0, 6.6)):
            P('office_desk', (ox + x, y, 0.0), rot_z=0.0 if row else math.pi)
            sgn = 1 if row else -1
            P('monitor', (ox + x, y + sgn * 0.12, 0.74), rot_z=0.0 if row else math.pi,
              props=screen_tile(14 if (row + col) % 2 else 11))
            P('keyboard', (ox + x, y - sgn * 0.15, 0.74), rot_z=0.0 if row else math.pi)
            P('mouse', (ox + x + 0.32, y - sgn * 0.15, 0.74), rot_z=0.0 if row else math.pi)
            P('office_chair', (ox + x + rng.uniform(-0.1, 0.1), y - sgn * 0.75, 0.0),
              rot_z=(math.pi if row else 0.0) + rng.uniform(-0.4, 0.4))
    P('printer_laser', (ox + 7.4, 0.6, 0.74), rot_z=math.pi / 2)
    P('office_desk', (ox + 7.4, 0.9, 0.0), rot_z=math.pi / 2)
    P('palm', (ox + 0.5, 0.5, 0.0))
    P('palm', (ox + 7.5, 6.0, 0.0))
    _cctv('CCTV 05 - Office', 'OPEN OFFICE', (ox + 0.25, 0.25, H - 0.15), (ox + 4.5, 4.0, 0.4))
    _cctv('CCTV 09 - Office east', 'OFFICE EAST', (ox + W - 0.25, D - 0.25, H - 0.15), (ox + 3.0, 2.0, 0.4))


def corridor(lib, ox):
    W, D, H = 2.4, 18.0, 2.7
    _room('Corridor', ox, W, D, H, lib=lib, panels=[(W / 2, 1.5 + 2.4 * k) for k in range(7)],
          panel_power=35.0)
    P = lib.place
    for k in range(5):
        y = 2.5 + k * 3.0
        P('door', (ox, y, 0.0), rot_z=math.radians(90))
        P('door', (ox + W, y + 1.4, 0.0), rot_z=math.radians(-90))
    P('exit_sign', (ox + W / 2, D, 2.35))
    P('vending_modern', (ox + W / 2, D, 0.0))
    _cctv('CCTV 06 - Corridor', 'CORRIDOR B', (ox + W / 2, 0.25, H - 0.15), (ox + W / 2, 10.0, 0.9),
          lens=18)


def server_room(lib, ox):
    W, D, H = 6.0, 6.5, 3.0
    _room('Server room', ox, W, D, H, wall='wall_light', floor='floor_vinyl', lib=lib,
          panels=_grid(1.5, 4.5, 1.2, 5.2, 1.3), panel_power=30.0)
    P = lib.place
    for row, x, rot in ((0, 1.9, math.pi / 2), (1, 4.1, -math.pi / 2)):
        for k in range(7):
            P('server_rack', (ox + x, 1.0 + k * 0.62, 0.0), rot_z=rot)
    _cctv('CCTV 07 - Server room', 'SERVER ROOM', (ox + W / 2, 0.25, H - 0.15), (ox + W / 2, 5.5, 0.8),
          lens=17)


def lobby(lib, ox):
    W, D, H = 7.0, 6.0, 3.0
    _room('Lobby', ox, W, D, H, wall='wall_beige', lib=lib, panels=_grid(1.4, 5.6, 1.3, 4.7, 1.4),
          panel_power=45.0)
    P = lib.place
    P('reception_desk', (ox + 3.6, 4.2, 0.0))
    P('sofa', (ox + 1.0, 2.2, 0.0), rot_z=math.radians(-90))
    P('sofa', (ox + 2.3, 0.6, 0.0), rot_z=math.radians(180), scale=(0.75, 1.0, 1.0))
    P('table_round', (ox + 2.2, 2.0, 0.0), scale=(0.7, 0.7, 0.55))
    rug = Builder()
    rug.box((ox + 1.4, 1.1, 0.0), (ox + 3.2, 3.0, 0.008))
    rug.build('Lobby rug', mat('fabric_grey'), 'FLAT')
    P('palm', (ox + 0.5, 5.5, 0.0))
    P('palm', (ox + 6.5, 5.5, 0.0))
    P('palm', (ox + 0.5, 0.5, 0.0))
    sb = Builder()
    sb.rounded_box((1.6, 0.45, 0.6), 0.01, (ox + 1.3, D - 0.25, 0.3), seg=2, zseg=2)
    sb.build('Lobby sideboard', mat('desk_charcoal'), 'HARD')
    P('tv', (ox + 1.3, D - 0.3, 0.6))
    P('door', (ox + 4.6, 0.0, 0.0), rot_z=math.pi)
    P('exit_sign', (ox + 4.6, 0.0, 2.4), rot_z=math.pi)
    _cctv('CCTV 08 - Lobby', 'MAIN LOBBY', (ox + W - 0.25, 0.25, H - 0.15), (ox + 2.6, 3.6, 0.5))


SETS = [break_room, warehouse, print_room, office, corridor, server_room, lobby]


def build(scene, lib):
    """Builds every set into ``scene``; returns the CCTV cameras in feed order."""
    FEEDS.clear()
    ox = 0.0
    for fn in SETS:
        coll = new_collection(fn.__name__.replace('_', ' ').title(), scene.collection)
        with target(coll):
            fn(lib, ox)
        ox += 25.0
    FEEDS.sort(key=lambda f: f[0].name)
    return FEEDS


# ---------------------------------------------------------------------------
# Screen atlas addressing
# ---------------------------------------------------------------------------

ATLAS_COLS, ATLAS_ROWS = 4, 4


def screen_tile(index, sub=(0.0, 0.0, 1.0, 1.0)):
    """Custom properties that make a screen instance show atlas tile
    ``index`` (row-major from the top-left), optionally only the sub-rectangle
    ``sub`` = (u0, v0, u1, v1) of it."""
    col = index % ATLAS_COLS
    row = ATLAS_ROWS - 1 - index // ATLAS_COLS        # UV rows count from the bottom
    du, dv = 1.0 / ATLAS_COLS, 1.0 / ATLAS_ROWS
    u0, v0, u1, v1 = sub
    return {'scr_min': [(col + u0) * du, (row + v0) * dv, 0.0],
            'scr_size': [(u1 - u0) * du, (v1 - v0) * dv, 0.0]}
