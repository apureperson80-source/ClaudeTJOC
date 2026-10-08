"""Scene assembly: prop library + studio product shots, the security control
room and the CCTV sets."""

import math

import bpy
from mathutils import Euler, Matrix, Vector

from bathroom_gen import fixtures_home as BH
from bathroom_gen import fixtures_public as BP
from bathroom_gen import plants
from bathroom_gen.geo import link, new_collection, target
from . import boxes, electronics, facility, office, printers, vending
from .materials import mat
from .mesh import Builder
from .studio import area_light, camera, cyclorama, spot_light


# ---------------------------------------------------------------------------
# Library: every model lives once in its own asset-marked collection
# ---------------------------------------------------------------------------

class Library:
    def __init__(self, scene):
        self.scene = scene
        self.root = new_collection('Prop Library', scene.collection)
        self.groups = {}
        self.items = {}

    def group(self, title):
        if title not in self.groups:
            self.groups[title] = new_collection(title, self.root)
        return self.groups[title]

    def add(self, key, title, builder, pos, rot_z=0.0, tags=(), group='Props from the photos', rot=None):
        coll = new_collection(title, self.group(group))
        with target(coll):
            root = builder()
        rot = rot or (0.0, 0.0, rot_z)
        root.location = pos
        root.rotation_euler = rot
        coll.instance_offset = pos
        try:
            coll.asset_mark()
            coll.asset_data.description = title
            for t in ('props',) + tuple(tags):
                coll.asset_data.tags.new(t, skip_if_exists=True)
        except (AttributeError, RuntimeError):
            pass
        self.items[key] = (coll, Euler(rot).to_matrix())
        return coll

    def place(self, key, loc, rot_z=0.0, name=None, props=None, scale=None):
        """Collection instance of ``key`` at ``loc`` (its own catalogue
        rotation is undone, so rot_z = 0 means the model's natural pose)."""
        coll, base = self.items[key]
        e = bpy.data.objects.new(name or coll.name, None)
        e.instance_type = 'COLLECTION'
        e.instance_collection = coll
        e.empty_display_size = 0.2
        link(e)
        e.location = loc
        e.rotation_euler = (Matrix.Rotation(rot_z, 3, 'Z') @ base.inverted()).to_euler()
        if scale is not None:
            e.scale = scale
        for k, v in (props or {}).items():
            e[k] = v
        return e


def build_library(scene):
    """All models, arranged as product groups along a long studio sweep."""
    lib = Library(scene)
    A = lib.add
    # -- reference photo 1: boxes
    A('box_tall_open', 'Cardboard Box (tall, open)', boxes.box_tall_open, (-0.40, 0.45, 0.0),
      math.radians(45), tags=('box', 'cardboard'))
    A('box_regular_open', 'Cardboard Box (regular, open)', boxes.box_regular_open, (0.40, 0.35, 0.0),
      math.radians(-22), tags=('box', 'cardboard'))
    A('box_closed', 'Cardboard Box (closed, taped)', boxes.box_closed, (-1.7, 0.9, 0.0),
      math.radians(10), tags=('box', 'cardboard'))
    # -- photo 2: vending machines (backs on y = 1.6)
    A('vending_modern', 'Vending Machine (modern, black)', vending.vending_modern, (3.35, 1.7, 0.0),
      math.radians(12), tags=('vending',))
    A('vending_classic', 'Vending Machine (classic, silver)', vending.vending_classic, (4.75, 1.7, 0.0),
      math.radians(-4), tags=('vending',))
    # -- photo 4: TV
    A('tv', 'Flat-screen TV (50 in)', electronics.tv_50, (8.0, 0.8, 0.0), 0.0, tags=('tv', 'screen'))
    # -- photo 5: printers
    A('printer_laser', 'Laser Printer (compact)', printers.printer_laser, (10.92, 0.5, 0.0),
      math.radians(14), tags=('printer',))
    A('printer_inktank', 'Photo Printer (ink tank, A3+)', printers.printer_inktank, (11.6, 0.62, 0.0),
      math.radians(-8), tags=('printer',))
    # -- photo 3: control-room kit
    kx = 15.5
    A('console_desk', 'Operator Console Desk', office.console_desk, (kx, 1.3, 0.0), 0.0,
      tags=('desk', 'control room'))
    A('monitor', 'Desktop Monitor (27 in)', electronics.monitor_27, (kx - 0.75, 1.62, 0.88),
      math.radians(14), tags=('screen', 'control room'))
    A('laptop', 'Laptop', electronics.laptop, (kx - 1.15, 1.2, 0.74), math.radians(18),
      tags=('screen', 'control room'))
    A('keyboard', 'Keyboard', electronics.keyboard, (kx, 1.08, 0.74), 0.0, tags=('control room',))
    A('mouse', 'Mouse', electronics.mouse, (kx + 0.36, 1.06, 0.74), math.radians(-6),
      tags=('control room',))
    A('desk_lamp', 'Desk Lamp (architect)', office.desk_lamp, (kx + 1.0, 1.55, 0.88),
      math.radians(25), tags=('light', 'control room'))
    A('mug', 'Coffee Mug', office.mug, (kx - 0.55, 1.02, 0.74), math.radians(150),
      tags=('control room',))
    A('operator_chair', 'Operator Chair', office.operator_chair, (kx + 0.15, 0.55, 0.0),
      math.radians(160), tags=('chair', 'control room'))
    A('videowall', 'Video-wall Display (55 in)', electronics.videowall_55, (kx, 3.0, 1.75), 0.0,
      tags=('screen', 'control room'))
    # -- set dressing used in the CCTV sets
    G = 'Set dressing'
    sx = 20.0
    A('pallet_rack', 'Pallet Rack Bay', office.pallet_rack, (sx + 1.4, 2.25, 0.0), group=G)
    A('pallet', 'Pallet', office.pallet, (sx + 1.4, 2.25, 1.5), group=G)
    A('shelving_unit', 'Shelving Unit', office.shelving_unit, (sx + 3.5, 2.4, 0.0), group=G)
    A('server_rack', 'Server Rack', office.server_rack, (sx + 4.6, 2.2, 0.0), group=G)
    A('door', 'Door', BH.door_panel, (sx + 5.85, 2.75, 0.0), group=G)
    A('exit_sign', 'Exit Sign', office.exit_sign, (sx + 5.85, 2.75, 2.35), group=G)
    A('palm', 'Kentia Palm', plants.palm, (sx + 7.0, 2.2, 0.0), group=G)
    A('table_round', 'Round Table', office.table_round, (sx + 0.4, 0.5, 0.0), group=G)
    A('chair_stacking', 'Stacking Chair', office.chair_stacking, (sx + 1.1, 0.35, 0.0),
      math.radians(-115), group=G)
    A('office_desk', 'Office Desk', office.office_desk, (sx + 2.6, 0.75, 0.0), group=G)
    A('office_chair', 'Office Chair', office.office_chair_simple, (sx + 2.6, 0.05, 0.0), math.pi,
      group=G)
    A('waste_bin', 'Waste Bin', BP.waste_bin, (sx + 3.7, 0.5, 0.0), group=G)
    A('sofa', 'Sofa', office.sofa, (sx + 5.0, 0.6, 0.0), group=G)
    A('reception_desk', 'Reception Desk', office.reception_desk, (sx + 7.5, 0.5, 0.0), group=G)
    A('led_panel', 'LED Panel 600', BP.led_panel, (sx + 3.9, -0.6, 0.0), group=G, rot=(math.pi, 0.0, 0.0))
    return lib


# ---------------------------------------------------------------------------
# Studio catalogue (product shots like the reference photos)
# ---------------------------------------------------------------------------

def catalogue_set(scene):
    coll = new_collection('Studio', scene.collection)
    with target(coll):
        cyclorama(-3.0, 37.0, depth=10.0, height=5.0, radius=1.4, back_y=3.0)
        # one soft-box rig per product group; each rig and its camera share a
        # 'rig' tag so a render can switch the other groups' lights off
        rigs = [  # (tag, centre, width, height, distance, power)
            ('Boxes', (0.0, 0.4, 0.35), 1.6, 2.0, 2.8, 0.5),
            ('Vending', (4.0, 1.0, 0.95), 3.0, 2.6, 3.6, 0.9),
            ('TV', (8.0, 0.8, 0.45), 1.6, 2.0, 3.0, 0.45),
            ('Printers', (11.2, 0.6, 0.12), 1.8, 1.6, 2.4, 0.35),
            ('Control room kit', (15.5, 1.4, 0.9), 3.0, 2.4, 3.4, 0.7),
            ('Set dressing', (23.8, 1.2, 0.9), 8.0, 3.2, 5.0, 1.3),
        ]
        for tag, c, w, h, dist, pw in rigs:
            c = Vector(c)
            for L in (area_light('Key light', c + Vector((-dist * 0.75, -dist, h)), c, 900 * pw,
                                 2.4 * max(1.0, w / 2), 1.6),
                      area_light('Fill light', c + Vector((dist * 0.9, -dist * 0.8, h * 0.6)), c,
                                 320 * pw, 2.0, 1.4),
                      area_light('Top light', c + Vector((0.0, -0.4, h + 1.4)), c, 600 * pw,
                                 max(2.0, w), 1.6)):
                L['rig'] = tag
        cams = [
            ('Boxes', camera('Product - Boxes', (0.05, -2.15, 1.62), (0.02, 0.4, 0.3), 50)),
            ('Vending', camera('Product - Vending Machines', (4.05, -2.75, 1.25), (4.05, 1.0, 0.98), 36)),
            ('TV', camera('Product - TV', (7.25, -1.3, 0.72), (8.0, 0.8, 0.44), 45)),
            ('Printers', camera('Product - Printers', (11.28, -1.05, 0.74), (11.3, 0.55, 0.07), 42)),
            ('Control room kit', camera('Product - Control Room Kit', (14.6, -2.9, 1.75),
                                        (15.5, 1.4, 0.95), 35)),
            ('Set dressing', camera('Product - Set Dressing', (24.25, -6.4, 2.9), (24.25, 1.4, 1.0), 27)),
        ]
        for tag, cam in cams:
            cam['rig'] = tag
        cams = [cam for _, cam in cams]
    scene.camera = cams[0]
    return cams


# ---------------------------------------------------------------------------
# Security control room (reference photo 3)
# ---------------------------------------------------------------------------

def build_control_room(scene, lib):
    W, D, H = 7.0, 6.2, 3.0
    arch = new_collection('Architecture', scene.collection)
    wall_c = new_collection('Video Wall', scene.collection)
    desk_c = new_collection('Operator Desk', scene.collection)
    lights = new_collection('Lighting & Cameras', scene.collection)
    V = Vector
    with target(arch):
        f = Builder()
        f.quad([V((0, 0, 0)), V((W, 0, 0)), V((W, D, 0)), V((0, D, 0))])
        f.build('Floor', mat('carpet_dark'), 'FLAT')
        c = Builder()
        c.quad([V((0, 0, H)), V((0, D, H)), V((W, D, H)), V((W, 0, H))])
        c.build('Ceiling', mat('wall_dark'), 'FLAT')
        wl = Builder()
        wl.quad([V((0, 0, 0)), V((0, D, 0)), V((0, D, H)), V((0, 0, H))])
        wl.quad([V((W, 0, 0)), V((W, 0, H)), V((W, D, H)), V((W, D, 0))])
        wl.quad([V((0, 0, 0)), V((0, 0, H)), V((W, 0, H)), V((W, 0, 0))])
        wl.build('Side walls', mat('acoustic_panel'), 'FLAT')
        bw = Builder()
        bw.quad([V((0, D, 0)), V((W, D, 0)), V((W, D, H)), V((0, D, H))])
        bw.build('Video wall back wall', mat('wall_dark'), 'FLAT')
        # vertical acoustic battens on the side walls
        bt = Builder()
        for k in range(14):
            y = 0.25 + k * 0.42
            bt.box((0.0, y, 0.12), (0.035, y + 0.06, H - 0.1))
            bt.box((W - 0.035, y, 0.12), (W, y + 0.06, H - 0.1))
        bt.build('Wall battens', mat('desk_charcoal'), 'FLAT')
        sk = Builder()
        sk.box((0.0, 0.0, 0.0), (0.012, D, 0.1))
        sk.box((W - 0.012, 0.0, 0.0), (W, D, 0.1))
        sk.box((0.0, D - 0.012, 0.0), (W, D, 0.1))
        sk.build('Skirting', mat('rubber_black'), 'FLAT')
        lib.place('door', (0.0, 1.2, 0.0), rot_z=math.radians(90))
        lib.place('exit_sign', (0.0, 1.2, 2.35), rot_z=math.radians(90))
    with target(wall_c):
        _video_wall(lib, W, D)
    with target(desk_c):
        dx, dy = W / 2, 3.55
        lib.place('console_desk', (dx, dy, 0.0))
        zs = 0.74 + 0.14
        for k, (x, tile, rot) in enumerate(((-0.74, 10, 16), (0.0, 11, 0), (0.74, 12, -16))):
            lib.place('monitor', (dx + x, dy + 0.27 - abs(x) * 0.08, zs), rot_z=math.radians(rot),
                      props=facility.screen_tile(tile))
        lib.place('laptop', (dx - 1.12, dy - 0.12, 0.74), rot_z=math.radians(24),
                  props=facility.screen_tile(13))
        lib.place('keyboard', (dx - 0.05, dy - 0.24, 0.74), rot_z=math.radians(-2))
        lib.place('mouse', (dx + 0.34, dy - 0.25, 0.74), rot_z=math.radians(-8))
        lib.place('desk_lamp', (dx + 1.18, dy + 0.3, zs), rot_z=math.radians(-62))
        lib.place('mug', (dx - 0.62, dy - 0.28, 0.74), rot_z=math.radians(200))
        lib.place('operator_chair', (dx + 0.85, dy - 1.05, 0.0), rot_z=math.radians(145))
    with target(lights):
        for (x, y) in ((1.6, 1.4), (5.4, 1.4), (1.6, 4.4), (5.4, 4.4), (3.5, 2.6)):
            spot_light('Downlight', (x, y, H - 0.02), (x, y, 0.0), 28.0, angle=70, blend=0.8,
                       radius=0.05, color=(0.75, 0.85, 1.0))
            dl = Builder()
            dl.revolve([(0.0, H - 0.004), (0.05, H - 0.004), (0.06, H)], 24, center=(x, y, 0.0))
            dl.build('Downlight trim', mat('aluminium'), 'SMOOTH')
        area_light('Screen spill', (W / 2, D - 0.6, 1.7), (W / 2, 1.5, 0.9), 260.0, 3.4, 1.4,
                   color=(0.55, 0.8, 1.0))
        area_light('Ceiling fill', (W / 2, 2.6, H - 0.05), (W / 2, 2.6, 0.0), 90.0, 4.0, 3.0,
                   color=(0.7, 0.82, 1.0))
        cams = [
            camera('Control Room - Main', (2.45, 1.75, 1.42), (3.95, D, 1.68), 19),
            camera('Control Room - Desk', (2.55, 2.45, 1.28), (3.7, 3.65, 0.86), 28),
            camera('Control Room - Video Wall', (W / 2, 1.0, 1.7), (W / 2, D, 1.7), 24),
        ]
    scene.camera = cams[0]
    return cams


def _video_wall(lib, W, D):
    """3 x 2 panels flat on the wall plus a 1 x 2 wing either side, angled
    in towards the operator. Each panel shows one feed of the atlas."""
    pw, ph = 1.2126, 0.6840
    z0 = 1.02
    zc = [z0 + ph / 2 + ph, z0 + ph / 2]                    # top row, bottom row
    x0 = W / 2 - 1.5 * pw
    centre = [[1, 0, 4], [2, 7, 6]]
    for r in range(2):
        for c in range(3):
            lib.place('videowall', (x0 + (c + 0.5) * pw, D, zc[r]), props=facility.screen_tile(centre[r][c]))
    wings = {-1: [3, 5], 1: [8, 9]}
    a = math.radians(32)
    depth = 0.105
    for side, tiles in wings.items():
        # rotate about the shared screen edge so the screens meet without a gap
        ex = W / 2 + side * 1.5 * pw
        off = Vector((pw / 2 * math.cos(a) + depth * math.sin(a), pw / 2 * math.sin(a) - depth * math.cos(a)))
        ox = ex + side * off.x
        oy = D - depth - off.y
        for r in range(2):
            lib.place('videowall', (ox, oy, zc[r]), rot_z=side * -a, props=facility.screen_tile(tiles[r]))
    # black surround behind the array
    s = Builder()
    s.box((x0 - 0.04, D - 0.02, z0 - 0.06), (x0 + 3 * pw + 0.04, D, z0 + 2 * ph + 0.06))
    s.box((x0 - 0.04, D - 0.11, z0 - 0.06), (x0 + 3 * pw + 0.04, D - 0.02, z0 - 0.02))
    s.box((x0 - 0.04, D - 0.11, z0 + 2 * ph + 0.02), (x0 + 3 * pw + 0.04, D - 0.02, z0 + 2 * ph + 0.06))
    s.build('Video wall surround', mat('black_powder_coat'), 'FLAT')
    cab = Builder()
    cab.rounded_box((3 * pw + 0.2, 0.45, 0.62), 0.01, (W / 2, D - 0.24, 0.31), seg=2, zseg=2)
    cab.build('Equipment cabinet', mat('desk_charcoal'), 'HARD')


# ---------------------------------------------------------------------------
# CCTV sets scene
# ---------------------------------------------------------------------------

def build_cctv(scene, lib):
    feeds = facility.build(scene, lib)
    scene.camera = feeds[0][0]
    return [cam for cam, _ in feeds], feeds


# ---------------------------------------------------------------------------
# Render setup
# ---------------------------------------------------------------------------

def setup_render(scene, res, samples=128, exposure=0.0, view='AgX', look='AgX - Medium High Contrast',
                 world=(0.5, 0.52, 0.55), world_strength=0.1):
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
    cy.max_bounces = 8
    cy.diffuse_bounces = 3
    cy.glossy_bounces = 4
    cy.transmission_bounces = 8
    cy.transparent_max_bounces = 12
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.blur_glossy = 1.0
    cy.sample_clamp_indirect = 6.0
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    vs = scene.view_settings
    vs.view_transform = view
    try:
        vs.look = look if view == 'AgX' else 'None'
    except TypeError:
        pass
    vs.exposure = exposure
    name = '%s World' % scene.name
    w = bpy.data.worlds.get(name) or bpy.data.worlds.new(name)
    if bpy.app.version < (5, 0, 0):
        w.use_nodes = True
    bg = w.node_tree.nodes.get('Background')
    if bg:
        bg.inputs['Color'].default_value = (*world, 1.0)
        bg.inputs['Strength'].default_value = world_strength
    scene.world = w
