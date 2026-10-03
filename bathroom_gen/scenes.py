"""Scene assembly: fixture library, room shells, tiling, lights and cameras."""

import math
import random

import bpy
from mathutils import Vector

from . import fixtures_home as H
from . import fixtures_public as P
from . import plants
from .geo import (MeshBuilder, box_obj, link, new_collection, panel_with_holes,
                  plane_map, rects_minus, target, tile_field)
from .materials import mat

TILE_T = 0.008      # wall tile thickness
FLOOR_T = 0.010     # floor tile thickness


# ---------------------------------------------------------------------------
# Fixture library: every product lives once in its own (asset-marked)
# collection; rooms place collection instances of it.
# ---------------------------------------------------------------------------

class Library:
    def __init__(self, scene):
        self.scene = scene
        self.root = new_collection('Fixture Library', scene.collection)
        self.items = {}

    def add(self, key, title, builder, pos, rot=(0, 0, 0), tags=()):
        coll = new_collection(title, self.root)
        with target(coll):
            root = builder()
        root.location = pos
        root.rotation_euler = rot
        coll.instance_offset = pos
        try:
            coll.asset_mark()
            coll.asset_data.description = title
            for t in ('bathroom',) + tuple(tags):
                coll.asset_data.tags.new(t, skip_if_exists=True)
        except (AttributeError, RuntimeError):
            pass
        self.items[key] = coll
        return coll

    def place(self, key, loc, rot_z=0.0, name=None, rot=None, scale=None):
        coll = self.items[key]
        e = bpy.data.objects.new(name or coll.name, None)
        e.instance_type = 'COLLECTION'
        e.instance_collection = coll
        e.empty_display_size = 0.2
        link(e)
        e.location = loc
        e.rotation_euler = rot if rot is not None else (0, 0, rot_z)
        if scale is not None:
            e.scale = scale
        return e


def build_library(scene):
    """Builds every reusable fixture and lays them out as a catalogue along a
    studio wall (wall plane y = 0)."""
    lib = Library(scene)
    A = lib.add
    # residential
    A('basin', 'Pedestal Basin', H.basin_pedestal, (0.0, 0, 0), tags=('sink', 'ceramic'))
    A('tap_brass', 'Basin Mixer Tap (brass)', H.tap_basin_mixer, (0.0, -0.065, 0.85), tags=('tap',))
    A('soap_ceramic', 'Soap Pump (ceramic)',
      lambda: H.soap_pump(glass='ceramic_matte', pump='brass', name='Soap pump (ceramic)'),
      (0.19, -0.06, 0.85), tags=('soap',))
    A('mirror_led', 'LED Mirror (brass frame)', H.mirror_led, (0.0, 0, 1.68), tags=('mirror',))
    A('toilet_cc', 'Close-Coupled Toilet', H.toilet_close_coupled, (0.85, 0, 0), tags=('toilet',))
    A('roll_holder', 'Toilet Roll Holder (brass)', H.toilet_roll_holder, (1.22, 0, 0.72))
    A('brush', 'Toilet Brush (brass)', H.toilet_brush, (1.30, -0.15, 0))
    A('art', 'Framed Print', H.art_print, (0.85, -0.002, 1.25))
    A('bath_l', 'L-Shaped Shower Bath', H.bath_l_shaped, (3.05, 0, 0), tags=('bath',))
    A('bath_filler', 'Wall Bath Filler (brass)', H.bath_filler_wall, (2.625, 0, 0.70), tags=('tap',))
    A('shower', 'Thermostatic Shower Kit (brass)', H.shower_thermostatic, (2.625, 0, 0),
      tags=('shower',))
    A('screen', 'Bath Screen', H.bath_screen, (2.235, 0, 0.56), tags=('glass',))
    A('pump_green', 'Soap Pump (green glass)', lambda: H.soap_pump(name='Soap pump (green glass)'),
      (3.35, -0.1, 0.0))
    A('bottle_green', 'Bottle (green glass)',
      lambda: H.bottle(r=0.024, h=0.13, name='Bottle (green glass)'), (3.45, -0.1, 0.0))
    A('jar', 'Ceramic Jar', H.jar, (3.55, -0.1, 0.0))
    A('tumbler', 'Toothbrush Tumbler', H.tumbler_with_brushes, (3.65, -0.1, 0.0))
    A('radiator', 'Ladder Towel Radiator', H.towel_radiator, (4.0, 0, 0), tags=('heating',))
    A('bath_mat', 'Bath Mat', H.bath_mat, (2.6, -2.2, 0))
    A('pothos', 'Pothos (trailing plant)', plants.pothos, (1.75, -0.15, 0.45), tags=('plant',))
    A('palm', 'Kentia Palm', plants.palm, (4.85, -0.35, 0), tags=('plant',))
    A('door', 'Shaker Door', H.door_panel, (5.75, 0, 0))
    A('downlight', 'Downlight (brass)', H.downlight, (1.6, -0.6, 2.6), tags=('light',))
    A('extractor', 'Extractor Fan', H.extractor_fan, (2.0, -0.6, 2.6))
    # public
    A('vanity2', 'Vanity Counter (2 bowls)', lambda: P.vanity_counter(n=2)[0], (7.0, 0, 0),
      tags=('sink',))
    A('tap_sensor', 'Sensor Tap (chrome)', P.tap_sensor, (7.575, -0.075, 0.85), tags=('tap',))
    A('soap_wall', 'Soap Dispenser (wall)', P.soap_dispenser_wall, (7.775, 0, 1.02), tags=('soap',))
    A('mirror_strip', 'Frameless Mirror', lambda: P.mirror_strip(1.6, 0.7), (7.05, 0, 1.32),
      tags=('mirror',))
    A('wc_hung', 'Wall-Hung WC', P.wc_wall_hung, (9.25, 0, 0), tags=('toilet',))
    A('flush_plate', 'Flush Plate', P.flush_plate, (9.25, 0, 0.98))
    A('urinal', 'Urinal', P.urinal, (10.05, 0, 0), tags=('urinal',))
    A('urinal_screen', 'Urinal Screen', P.urinal_screen, (10.45, 0, 0))
    A('hand_dryer', 'Hand Dryer', P.hand_dryer, (11.0, 0, 1.10))
    A('towel_disp', 'Paper Towel Dispenser', P.paper_towel_dispenser, (11.55, 0, 1.10))
    A('waste_bin', 'Waste Bin', P.waste_bin, (11.55, -0.25, 0))
    A('jumbo_roll', 'Jumbo Roll Dispenser', P.jumbo_roll_dispenser, (12.1, 0, 0.78))
    A('sanitary_bin', 'Sanitary Bin', P.sanitary_bin, (12.1, 0, 0))
    A('coat_hook', 'Coat Hook', P.coat_hook, (12.45, 0, 1.6))
    A('led_panel', 'LED Panel 600', P.led_panel, (9.0, -1.2, 2.9), tags=('light',))
    return lib


def catalogue_set(scene):
    """Studio backdrop + cameras for the fixture catalogue scene."""
    coll = new_collection('Studio', scene.collection)
    with target(coll):
        box_obj('Studio floor', (-1.0, -8.0, -0.05), (13.5, 1.0, 0.0), mat('floor_speckle'))
        mb = MeshBuilder()
        mb.box((-1.0, 0.0, 0.0), (13.5, 0.05, 3.0))
        mb.box((-1.0, -8.05, 0.0), (13.5, -8.0, 3.0))   # backdrop seen in mirrors
        mb.build('Studio walls', mat('paint_white'), 'FLAT')
        box_obj('Plinth', (1.58, -0.225, 0.0), (1.92, 0.0, 0.45), mat('frame_white'), bevel=0.004)
        _studio_light(scene, (2.4, -3.5, 2.6), (2.4, 0, 0.9), 260, 3.0)
        _studio_light(scene, (9.6, -3.5, 2.6), (9.6, 0, 0.9), 260, 3.0)
        _studio_light(scene, (-0.5, -2.0, 2.0), (2.0, 0, 1.0), 70, 1.5)
        _studio_light(scene, (13.0, -2.0, 2.0), (10.0, 0, 1.0), 70, 1.5)
        cams = [_camera('Catalogue - Residential', (2.45, -5.6, 1.55), (2.45, 0, 0.98), 30),
                _camera('Catalogue - Public', (9.75, -5.2, 1.5), (9.75, 0, 0.95), 30)]
    scene.camera = cams[0]
    return cams


# ---------------------------------------------------------------------------
# Generic room helpers
# ---------------------------------------------------------------------------

def _camera(name, loc, look_at, lens, shift=(0.0, 0.0)):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_width = 36
    cam.shift_x, cam.shift_y = shift
    cam.clip_start = 0.05
    obj = bpy.data.objects.new(name, cam)
    link(obj)
    obj.location = loc
    obj.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return obj


def _studio_light(scene, loc, look_at, power, size):
    ld = bpy.data.lights.new('Studio light', 'AREA')
    ld.energy = power
    ld.size = size
    obj = bpy.data.objects.new('Studio light', ld)
    link(obj)
    obj.location = loc
    obj.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return obj


def _fill_light(name, loc, size, power, color=(1.0, 0.95, 0.9)):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.shape = 'RECTANGLE'
    ld.size, ld.size_y = size
    ld.energy = power
    ld.color = color
    obj = bpy.data.objects.new(name, ld)
    link(obj)
    obj.location = loc
    # soft bounce light: not seen directly or in reflections
    for attr in ('visible_camera', 'visible_glossy', 'visible_transmission'):
        if hasattr(obj, attr):
            setattr(obj, attr, False)
    return obj


def tiled_surface(name, origin, u_axis, v_axis, n_axis, size, tile, grout, tile_mat,
                  grout_mat, holes=(), start=(0.0, 0.0), thickness=TILE_T, seed=0,
                  pattern='stack', chamfer=0.0015, lippage=0.00025, tilt=0.0012):
    """Real tiles + recessed grout bed over one rectangular surface."""
    mapper = plane_map(origin, u_axis, v_axis, n_axis)
    mb = MeshBuilder()
    tile_field(mb, size[0], size[1], tile[0], tile[1], grout, thickness, mapper,
               holes=holes, chamfer=chamfer, pattern=pattern, start=start,
               rng=random.Random(seed), lippage=lippage, tilt=tilt)
    tiles = mb.build(name + ' tiles', tile_mat, 'HARD', attr='tile_rand')
    gm = MeshBuilder()
    panel_with_holes(gm, size[0], size[1], holes, mapper, w=-thickness * 0.45)
    grout_obj = gm.build(name + ' grout', grout_mat, 'FLAT')
    return tiles, grout_obj


def slab(name, rect, axis, depth0, depth1, material, holes=()):
    """Wall/floor slab pieces around rectangular openings.

    ``rect`` = (a0, b0, a1, b1) in the two in-plane axes; ``axis`` is the
    normal ('X', 'Y' or 'Z') and depth0..depth1 its extent."""
    mb = MeshBuilder()
    for a0, b0, a1, b1 in rects_minus([rect], holes):
        if axis == 'X':
            mb.box((depth0, a0, b0), (depth1, a1, b1))
        elif axis == 'Y':
            mb.box((a0, depth0, b0), (a1, depth1, b1))
        else:
            mb.box((a0, b0, depth0), (a1, b1, depth1))
    return mb.build(name, material, 'FLAT')


def _grid_start(length, pitch, align_end=True):
    """Grid offset so that a grout line falls exactly at ``length``."""
    return (length % pitch) - pitch if align_end else 0.0


# ---------------------------------------------------------------------------
# Residential bathroom
# ---------------------------------------------------------------------------

def build_residential(scene, lib):
    W, D, Hh = 3.0, 2.6, 2.45
    bath_w, bath_l, rim = 0.85, 1.70, 0.56
    xb = W - bath_w                 # bath's room-side edge
    duct_d, duct_h = 0.15, 1.15
    yd = D - duct_d                 # duct front plane
    tw, th, g = 0.075, 0.300, 0.002
    pu, pv = tw + g, th + g

    arch = new_collection('Architecture', scene.collection)
    fix = new_collection('Fixtures', scene.collection)
    acc = new_collection('Accessories & Plants', scene.collection)
    lights = new_collection('Lighting & Cameras', scene.collection)

    # niche in the right wall, snapped to the tile grid (8 tiles x 1 tile)
    su_right = _grid_start(D, pu)
    k1 = int(round((D - 0.92 - su_right) / pu))
    n_u0 = su_right + (k1 - 8) * pu
    n_u1 = su_right + k1 * pu
    n_v0, n_v1 = 3 * pv, 4 * pv
    niche_d = 0.10

    sage, grout = mat('tile_sage'), mat('grout_white')
    with target(arch):
        # shell
        box_obj('Floor slab', (-0.2, -0.2, -0.25), (W + 0.2, D + 0.2, -FLOOR_T), mat('paint_white'))
        box_obj('Ceiling', (-0.2, -0.2, Hh), (W + 0.2, D + 0.2, Hh + 0.15), mat('paint_white'))
        slab('Back wall', (-0.2, -0.2, W + 0.2, Hh + 0.2), 'Y', D + TILE_T, D + 0.2,
             mat('paint_white'))
        slab('Left wall', (-0.2, -0.2, D + 0.2, Hh + 0.2), 'X', -0.2, 0.0, mat('paint_white'))
        slab('Front wall', (-0.2, -0.2, W + 0.2, Hh + 0.2), 'Y', -0.2, 0.0, mat('paint_white'))
        slab('Right wall', (-0.2, -0.2, D + 0.2, Hh + 0.2), 'X', W + TILE_T, W + 0.25,
             mat('paint_white'), holes=[(n_u0, n_v0, n_u1, n_v1)])
        box_obj('Niche back', (W + niche_d + TILE_T, n_u0 - 0.01, n_v0 - 0.01),
                (W + 0.25, n_u1 + 0.01, n_v1 + 0.01), mat('paint_white'))
        box_obj('Duct', (0.0, yd + TILE_T, 0.0), (xb - TILE_T, D + TILE_T, duct_h - TILE_T),
                mat('paint_white'))
        # skirting-free tiled walls
        # each tiled face stops a tile-thickness short of the faces it meets,
        # so tiles butt against each other instead of overlapping
        tiled_surface('Duct front', (0, yd, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0),
                      (xb, duct_h - TILE_T), (tw, th), g, sage, grout, seed=1)
        tiled_surface('Duct top', (0, yd, duct_h), (1, 0, 0), (0, 1, 0), (0, 0, 1),
                      (xb - TILE_T, duct_d + TILE_T), (tw, th), g, sage, grout, seed=2)
        tiled_surface('Duct side', (xb, yd + TILE_T, rim), (0, 1, 0), (0, 0, 1), (1, 0, 0),
                      (duct_d - TILE_T, duct_h - rim - TILE_T), (tw, th), g, sage, grout,
                      seed=3, start=(0, -(rim % pv)))
        tiled_surface('Bath wall', (xb, D, rim), (1, 0, 0), (0, 0, 1), (0, -1, 0),
                      (bath_w, Hh - rim), (tw, th), g, sage, grout, seed=4,
                      start=(-(xb % pu), -(rim % pv)))
        tiled_surface('Right wall', (W, 0, 0), (0, 1, 0), (0, 0, 1), (-1, 0, 0),
                      (D, Hh), (tw, th), g, sage, grout, seed=5, start=(su_right, 0),
                      holes=[(n_u0, n_v0, n_u1, n_v1), (D - bath_l + 0.02, 0, D + 0.1, rim - 0.01)])
        # niche lining
        tiled_surface('Niche back', (W + niche_d, 0, 0), (0, 1, 0), (0, 0, 1), (-1, 0, 0),
                      (n_u1, n_v1), (tw, th), g, sage, grout, seed=6, start=(su_right, 0),
                      holes=[(0, 0, n_u0, n_v1), (n_u0, 0, n_u1, n_v0)])
        nd = niche_d - TILE_T
        x0 = W + TILE_T
        for k, (nm, org, ua, va, na, size) in enumerate((
                ('Niche sill', (x0, n_u0, n_v0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (nd, n_u1 - n_u0)),
                ('Niche head', (x0, n_u0, n_v1), (1, 0, 0), (0, 1, 0), (0, 0, -1), (nd, n_u1 - n_u0)),
                ('Niche side A', (x0, n_u0, n_v0), (1, 0, 0), (0, 0, 1), (0, 1, 0), (nd, n_v1 - n_v0)),
                ('Niche side B', (x0, n_u1, n_v0), (1, 0, 0), (0, 0, 1), (0, -1, 0), (nd, n_v1 - n_v0)))):
            tiled_surface(nm, org, ua, va, na, size, (0.10, tw), g, sage, grout, seed=20 + k)
        # brushed brass tile trims on exposed edges
        tm = MeshBuilder()
        tm.box((-0.001, yd - 0.004, duct_h - 0.002), (xb, yd + 0.006, duct_h + 0.002))
        tm.box((xb - 0.004, yd - 0.004, duct_h - 0.002), (xb + 0.002, D, duct_h + 0.002))
        tm.box((xb - 0.003, D - 0.002, duct_h), (xb + 0.003, D + TILE_T, Hh))
        tm.box((xb - 0.004, yd - 0.004, rim), (xb + 0.002, yd + 0.002, duct_h))
        for (a0, a1, b0, b1) in ((n_u0, n_u1, n_v0, n_v0), (n_u0, n_u1, n_v1, n_v1)):
            tm.box((W - 0.003, a0, b0 - 0.0025), (W + 0.004, a1, b0 + 0.0025))
        for a in (n_u0, n_u1):
            tm.box((W - 0.003, a - 0.0025, n_v0), (W + 0.004, a + 0.0025, n_v1))
        tm.build('Tile trims', mat('brass'), 'FLAT')
        # large-format marble floor
        fs = 0.6 + 0.003
        tiled_surface('Floor', (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (W, D),
                      (0.6, 0.6), 0.003, mat('marble_floor'), mat('grout_grey'),
                      thickness=FLOOR_T, seed=7, chamfer=0.001, lippage=0.0003, tilt=0.0005,
                      start=(-(W % fs) / 2, -(D % fs) / 2 + fs / 2),
                      holes=[(0, yd, xb, D + 0.1), (xb + 0.02, D - 0.78, W + 0.1, D + 0.1),
                             (W - 0.68, D - bath_l + 0.02, W + 0.1, D - 0.78)])

    with target(fix):
        lib.place('basin', (0.55, yd, 0))
        lib.place('tap_brass', (0.55, yd - 0.065, 0.85))
        lib.place('mirror_led', (0.55, D + TILE_T, 1.68))
        lib.place('toilet_cc', (1.45, yd, 0))
        lib.place('bath_l', (W, D, 0))
        lib.place('bath_filler', (W - bath_w / 2, D, 0.70))
        lib.place('shower', (W - bath_w / 2, D, 0))
        lib.place('screen', (xb + 0.035, D, rim))
        lib.place('radiator', (0.0, 1.35, 0), rot_z=math.radians(90))
        lib.place('door', (1.15, 0.0, 0), rot_z=math.pi)

    with target(acc):
        lib.place('soap_ceramic', (0.55 + 0.19, yd - 0.06, 0.85))
        lib.place('roll_holder', (1.84, yd, 0.72))
        lib.place('brush', (1.07, yd - 0.12, 0))
        lean = math.radians(-7)
        lib.place('art', (1.62, D - 0.42 * math.sin(-lean) - 0.003, duct_h),
                  rot=(lean, 0, math.radians(-3)))
        lib.place('pothos', (1.02, D - 0.078, duct_h), rot_z=math.radians(10))
        lib.place('tumbler', (0.12, D - 0.08, duct_h))
        lib.place('palm', (W - 0.32, 0.42, 0))
        lib.place('bath_mat', (1.80, 1.55, 0))
        lib.place('pump_green', (W + 0.05, n_u0 + 0.12, n_v0), rot_z=math.radians(-80))
        lib.place('bottle_green', (W + 0.055, n_u0 + 0.24, n_v0))
        lib.place('jar', (W + 0.05, n_u0 + 0.45, n_v0))

    with target(lights):
        for x, y in ((0.55, 1.75), (1.45, 1.75), (W - 0.42, 1.95), (W - 0.42, 1.15),
                     (0.9, 0.7)):
            lib.place('downlight', (x, y, Hh))
        lib.place('extractor', (2.0, 0.45, Hh))
        _fill_light('Ceiling bounce', (W / 2, D / 2, Hh - 0.02), (2.4, 2.0), 70)
        _fill_light('Front bounce', (W / 2, 0.15, 1.3), (2.0, 1.2), 35)
        bpy.data.objects['Front bounce'].rotation_euler = (math.radians(-90), 0, 0)
        cams = [
            _camera('Home - Main', (0.42, 0.30, 1.42), (2.05, 2.6, 1.02), 17),
            _camera('Home - Shower', (2.25, 0.80, 1.62), (W - 0.40, D, 1.28), 24),
            _camera('Home - Vanity', (1.15, 1.25, 1.35), (0.75, D, 0.95), 30),
            _camera('Home - Toilet', (2.0, 1.1, 1.25), (1.4, D, 0.55), 28),
        ]
    scene.camera = cams[0]
    return cams


# ---------------------------------------------------------------------------
# Public washroom
# ---------------------------------------------------------------------------

def build_public(scene, lib):
    W, D, Hh = 6.4, 5.6, 2.7
    t = 0.150
    g = 0.002
    pitch = t + g
    arch = new_collection('Architecture', scene.collection)
    fix = new_collection('Fixtures', scene.collection)
    acc = new_collection('Accessories', scene.collection)
    lights = new_collection('Lighting & Cameras', scene.collection)
    lilac, grout = mat('tile_lilac'), mat('grout_white')

    n_basins, spacing, end = 5, 0.75, 0.20
    v_len = n_basins * spacing + 2 * end
    v_y0 = D - 0.2 - v_len
    n_cub, bay, depth, end_w = 4, 0.95, 1.55, 0.08
    row_total = n_cub * bay + end_w
    c_y0 = D - row_total
    duct_d = 0.20

    door_x = 3.4
    with target(arch):
        box_obj('Floor slab', (-0.2, -0.2, -0.25), (W + 0.2, D + 0.2, -FLOOR_T), mat('paint_white'))
        box_obj('Soffit', (-0.2, -0.2, Hh + 0.35), (W + 0.2, D + 0.2, Hh + 0.45), mat('paint_white'))
        slab('Back wall', (-0.2, -0.2, W + 0.2, Hh + 0.5), 'Y', D + TILE_T, D + 0.2, mat('paint_white'))
        slab('Front wall', (-0.2, -0.2, W + 0.2, Hh + 0.5), 'Y', -0.2, -TILE_T, mat('paint_white'))
        slab('Left wall', (-0.2, -0.2, D + 0.2, Hh + 0.5), 'X', -0.2, -TILE_T, mat('paint_white'))
        slab('Right wall', (-0.2, -0.2, D + 0.2, Hh + 0.5), 'X', W + TILE_T, W + 0.2, mat('paint_white'))
        s = _grid_start
        tiled_surface('Back wall', (0, D, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0), (W, Hh),
                      (t, t), g, lilac, grout, seed=11, start=(0, 0))
        tiled_surface('Front wall', (W, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 1, 0), (W, Hh),
                      (t, t), g, lilac, grout, seed=12,
                      holes=[(W - door_x - 0.50, 0, W - door_x + 0.50, 2.12)])
        tiled_surface('Left wall', (0, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0), (D, Hh),
                      (t, t), g, lilac, grout, seed=13, start=(s(D, pitch), 0),
                      holes=[(v_y0 + 0.04, 1.30, v_y0 + v_len - 0.04, 2.04)])
        tiled_surface('Right wall', (W, 0, 0), (0, 1, 0), (0, 0, 1), (-1, 0, 0), (D, Hh),
                      (t, t), g, lilac, grout, seed=14, start=(s(D, pitch), 0),
                      holes=[(c_y0 + 0.01, 0, D + 0.1, 1.10)])
        tiled_surface('Floor', (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (W, D),
                      (0.3, 0.3), 0.003, mat('floor_speckle'), mat('grout_grey'),
                      thickness=FLOOR_T, seed=15, chamfer=0.001, lippage=0.0003, tilt=0.0004)
        # service duct behind the WCs (laminate panels)
        box_obj('WC duct', (W - duct_d, c_y0, 0.0), (W, D, 1.10), mat('laminate_grey'), bevel=0.004)
        # suspended ceiling: tiles + T-bar grid, with openings for LED panels
        _suspended_ceiling(W, D, Hh, lib)

    with target(fix):
        root, taps, _ = P.vanity_counter(n_basins, spacing, 0.55, 0.85, end)
        root.location = (0.0, v_y0, 0.0)
        root.rotation_euler = (0, 0, math.radians(90))
        for i, tp in enumerate(taps):
            wy = v_y0 + tp.x
            lib.place('tap_sensor', (-tp.y, wy, tp.z), rot_z=math.radians(90))
            lib.place('soap_wall', (0.0, wy + 0.21, 1.02), rot_z=math.radians(90))
        m = P.mirror_strip(v_len - 0.1, 0.72)
        m.location = (0.0, v_y0 + 0.05, 1.31)
        m.rotation_euler = (0, 0, math.radians(90))
        # cubicles along the right wall (mirrored so the open end faces the room)
        root, centres, _ = P.cubicle_row(n_cub, bay, depth, 2.0, end_w=end_w,
                                         open_doors={0: 80.0, 2: 25.0})
        root.location = (W, c_y0, 0)
        root.rotation_euler = (0, 0, math.radians(-90))
        root.scale = (-1, 1, 1)
        for i, c in enumerate(centres):
            wy = c_y0 + c
            lib.place('wc_hung', (W - duct_d, wy, 0), rot_z=math.radians(-90))
            lib.place('flush_plate', (W - duct_d, wy, 0.97), rot_z=math.radians(-90))
            # roll dispenser on the far partition (or the back wall in the last bay)
            side_y = c_y0 + (i + 1) * bay - 0.0065 if i < n_cub - 1 else D
            lib.place('jumbo_roll', (W - 0.62, side_y, 0.78))
            if i % 2 == 0:
                lib.place('sanitary_bin', (W - duct_d - 0.02, wy - 0.30, 0), rot_z=math.radians(-90))
        # urinals with privacy screens on the back wall
        for x in (2.95, 3.75):
            lib.place('urinal', (x, D, 0))
        for x in (2.55, 3.35, 4.15):
            lib.place('urinal_screen', (x, D, 0))
        lib.place('door', (door_x, 0.0, 0), rot_z=math.pi)

    with target(acc):
        lib.place('hand_dryer', (1.05, D, 1.10))
        lib.place('hand_dryer', (1.60, D, 1.10))
        lib.place('towel_disp', (2.10 - 0.02, D, 1.15))
        lib.place('waste_bin', (2.08, D - 0.25, 0))

    with target(lights):
        _fill_light('Room bounce', (W / 2, D / 2, Hh - 0.05), (4.0, 3.5), 50, (0.95, 0.97, 1.0))
        cams = [
            _camera('Public - Main', (3.35, 0.22, 1.62), (2.35, D, 1.22), 17),
            _camera('Public - Vanity', (1.9, 1.2, 1.55), (0.25, 3.6, 0.95), 24),
            _camera('Public - Cubicle', (3.75, 2.5, 1.6), (W - 0.45, c_y0 + bay / 2, 0.55), 24),
        ]
    scene.camera = cams[0]
    return cams


def _suspended_ceiling(W, D, Hh, lib):
    cell = 0.6
    nx = int(math.ceil(W / cell))
    ny = int(math.ceil(D / cell))
    ox = (W - nx * cell) / 2
    oy = (D - ny * cell) / 2
    panel_cells = {(i, j) for i in (1, 4, 8) for j in (1, 3, 5, 7)}
    tm = MeshBuilder()
    gm = MeshBuilder()
    for i in range(nx):
        for j in range(ny):
            x0, y0 = max(0.0, ox + i * cell), max(0.0, oy + j * cell)
            x1, y1 = min(W, ox + (i + 1) * cell), min(D, oy + (j + 1) * cell)
            if (i, j) in panel_cells:
                lib.place('led_panel', ((x0 + x1) / 2, (y0 + y1) / 2, Hh))
                continue
            tm.box((x0 + 0.006, y0 + 0.006, Hh + 0.002), (x1 - 0.006, y1 - 0.006, Hh + 0.017))
    for i in range(nx + 1):
        x = min(max(ox + i * cell, 0.006), W - 0.006)
        gm.box((x - 0.012, 0, Hh - 0.002), (x + 0.012, D, Hh + 0.004))
        gm.box((x - 0.002, 0, Hh + 0.004), (x + 0.002, D, Hh + 0.04))
    for j in range(ny + 1):
        y = min(max(oy + j * cell, 0.006), D - 0.006)
        gm.box((0, y - 0.012, Hh - 0.0021), (W, y + 0.012, Hh + 0.0039))
    tm.build('Ceiling tiles', mat('ceiling_tile'), 'FLAT')
    gm.build('Ceiling grid', mat('plastic_white'), 'FLAT')


# ---------------------------------------------------------------------------
# Render setup
# ---------------------------------------------------------------------------

def setup_render(scene, res=(1600, 1200), samples=256, exposure=-0.2):
    scene.render.engine = 'CYCLES'
    cy = scene.cycles
    cy.device = 'CPU'
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.02
    cy.use_denoising = True
    try:
        cy.denoiser = 'OPENIMAGEDENOISE'
    except TypeError:
        pass
    cy.max_bounces = 10
    cy.diffuse_bounces = 4
    cy.glossy_bounces = 4
    cy.transmission_bounces = 10
    cy.transparent_max_bounces = 8
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.blur_glossy = 1.0
    cy.sample_clamp_indirect = 8.0
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    vs = scene.view_settings
    vs.view_transform = 'AgX'
    try:
        vs.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass
    vs.exposure = exposure
    world = bpy.data.worlds.get('Interior') or bpy.data.worlds.new('Interior')
    if bpy.app.version < (5, 0, 0):
        world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    if bg:
        bg.inputs['Color'].default_value = (0.55, 0.58, 0.62, 1.0)
        bg.inputs['Strength'].default_value = 0.15
    scene.world = world
