"""Mountain-lake landscape, rendered once to an image.

The TV wallpaper (reference photo 4) and the photo coming out of the photo
printer show this picture: snowy peaks over a forested shore, pines on the
right, boulders in a calm lake. It is a real 3D scene -- heightfield terrain,
thousands of low-poly pines, rocks, water and a physical sky -- built in a
temporary scene, rendered with Cycles and removed again.
"""

import math
import random

import bpy
from mathutils import Vector, noise

from bathroom_gen.materials import Nodes, hexcol, set_input
from .mesh import Builder

SHORE_Y = 900.0          # far shore of the lake


def _smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def _fbm(x, y, octaves=5):
    return noise.fractal(Vector((x, y, 0.37)), 0.6, 2.0, octaves, noise_basis='PERLIN_NEW')


def _right_shore(y):
    return 16.0 + 0.085 * y + 7.0 * math.sin(y / 55.0)


def _far_shore(x):
    return SHORE_Y + 70.0 * math.sin(x / 260.0) + 40.0 * math.sin(x / 97.0 + 1.0)


def height(x, y):
    """Terrain height in metres; below 0 is lake bed."""
    # far shore: forested hills rising into two snowy massifs
    d = y - _far_shore(x)
    far = _smooth(-40.0, 140.0, d)
    hills = 30.0 + 190.0 * (0.5 + 0.5 * _fbm(x / 500.0, y / 500.0, 5)) * _smooth(0, 900, d)
    ridged = noise.ridged_multi_fractal(Vector((x / 2100.0, y / 2100.0, 0.5)), 0.85, 2.1, 8, 1.0, 2.4,
                                        noise_basis='PERLIN_NEW')
    detail = noise.ridged_multi_fractal(Vector((x / 700.0, y / 700.0, 3.5)), 0.9, 2.2, 6, 1.0, 2.0,
                                        noise_basis='PERLIN_NEW')
    peaks = min(1.0, max(0.0, (ridged - 0.45) / 1.45)) ** 1.5
    m1 = math.exp(-(((x + 1100) / 3200.0) ** 2 + ((y - 7600) / 2800.0) ** 2))
    m2 = math.exp(-(((x - 3300) / 2400.0) ** 2 + ((y - 6200) / 2000.0) ** 2))
    massif = (1900.0 * m1 + 1250.0 * m2) * (0.25 + 0.9 * peaks) + 90.0 * detail * (m1 + m2)
    h_far = far * (hills + massif * _smooth(1300, 3600, y))
    # near right shore where the pines grow
    xs = _right_shore(y)
    near = _smooth(xs - 4.0, xs + 25.0, x) * (1.0 - _smooth(SHORE_Y - 200, SHORE_Y + 100, y))
    h_near = near * (2.0 + 0.07 * max(0.0, x - xs) + 6.0 * _fbm(x / 60.0, y / 60.0, 3))
    land = max(far, near)
    return max(h_far, h_near) - 4.0 * (1.0 - land)


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

def _terrain():
    """Polar grid around the camera: dense close up, coarse far away."""
    mb = Builder()
    na, nr = 480, 600
    a0, a1 = math.radians(-58), math.radians(58)
    r0, r1 = 6.0, 16000.0
    rows = []
    for j in range(nr + 1):
        r = r0 * (r1 / r0) ** (j / nr)
        row = []
        for i in range(na + 1):
            a = a0 + (a1 - a0) * i / na
            x, y = r * math.sin(a), r * math.cos(a)
            row.append(mb.v((x, y, height(x, y))))
        rows.append(row)
    for j in range(nr):
        for i in range(na):
            mb.f([rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]])
    return mb.build('Terrain', _terrain_mat(), 'SMOOTH')


def _pine(mb, base, h, rng):
    """Low-poly spruce: trunk plus jagged drooping tiers."""
    x, y, z = base
    tiers = rng.randint(12, 16)
    seg = 12
    r_base = h * rng.uniform(0.15, 0.19)
    trunk = h * 0.12
    mb.revolve([(0.0, z), (h * 0.015, z), (h * 0.012, z + trunk), (0.0, z + trunk)], 5,
               center=(x, y, 0.0))
    for k in range(tiers):
        t0 = k / tiers
        zb = z + trunk + (h - trunk) * t0 * 0.92
        zt = zb + (h - trunk) * (2.2 / tiers + 0.05)
        rr = r_base * (1.0 - t0) ** 0.9 + 0.15
        ring = []
        for s in range(seg):
            a = 2 * math.pi * (s + rng.random() * 0.4) / seg
            rad = rr * (rng.uniform(0.85, 1.2) if s % 2 else rng.uniform(0.45, 0.7))
            ring.append((x + rad * math.cos(a), y + rad * math.sin(a),
                         zb - rad * 0.25 * rng.uniform(0.6, 1.2)))
        tip = (x + rng.uniform(-0.05, 0.05) * h * 0.1, y, zt)
        ids = [mb.v(p) for p in ring]
        top = mb.v(tip)
        for s in range(seg):
            mb.f([ids[s], ids[(s + 1) % seg], top])
        mb.f(list(reversed(ids)))


def _forest(rng):
    mb = Builder()
    # dense pines on the near right shore
    for k in range(7000):
        y = rng.uniform(22.0, 820.0)
        xs = _right_shore(y)
        x = xs + 2.0 + rng.expovariate(1.0 / 140.0)
        if x > y * 1.5 + 150:
            continue
        z = height(x, y)
        if z < 0.8:
            continue
        h = rng.uniform(16.0, 33.0) * (1.0 if y < 300 else 1.15)
        _pine(mb, (x, y, z - 0.3), h, rng)
    # tree line along the far shore (silhouettes against the hills)
    for k in range(5000):
        x = rng.uniform(-1300.0, 1300.0)
        y = _far_shore(x) + rng.uniform(15.0, 380.0)
        z = height(x, y)
        if z < 1.0:
            continue
        _pine(mb, (x, y, z - 0.5), rng.uniform(16.0, 30.0), rng)
    return mb.build('Pines', _pine_mat(), 'FLAT', auto_link=True)


def _rocks(rng):
    mb = Builder()
    spots = [(-7.0, 16.0, 2.4), (-2.5, 13.0, 1.6), (3.5, 18.0, 2.0), (8.0, 14.0, 1.2),
             (-12.0, 24.0, 2.8), (12.0, 22.0, 2.2), (0.5, 26.0, 1.4), (-4.0, 34.0, 2.0),
             (6.0, 36.0, 1.6), (17.0, 30.0, 2.6), (-17.0, 40.0, 3.0), (2.0, 46.0, 1.8),
             (-9.0, 52.0, 2.2), (10.0, 58.0, 1.8), (21.0, 48.0, 2.4), (-1.5, 9.0, 0.9),
             (5.0, 10.5, 1.0), (-9.5, 10.5, 1.1)]
    for (x, y, s) in spots:
        x += rng.uniform(-0.5, 0.5)
        _boulder(mb, (x, y, -0.3 * s), s, rng)
    for k in range(16):
        y = rng.uniform(8.0, 120.0)
        x = rng.uniform(-y * 0.5, y * 0.6)
        _boulder(mb, (x, y, -0.25), rng.uniform(0.3, 0.9), rng)
    return mb.build('Boulders', _rock_mat(), 'SMOOTH')


def _boulder(mb, c, s, rng):
    seed = Vector((rng.uniform(0, 100), rng.uniform(0, 100), rng.uniform(0, 100)))
    sx, sy, sz = rng.uniform(0.9, 1.25), rng.uniform(0.8, 1.15), rng.uniform(0.7, 0.95)
    nseg, nring = 22, 12
    rows = []
    for j in range(nring + 1):
        phi = math.pi * j / nring - math.pi / 2
        row = []
        for i in range(nseg):
            th = 2 * math.pi * i / nseg
            d = Vector((math.cos(phi) * math.cos(th), math.cos(phi) * math.sin(th), math.sin(phi)))
            k = 1.0 + 0.22 * noise.noise(d * 1.4 + seed) + 0.07 * noise.noise(d * 4.0 + seed) \
                + 0.025 * noise.noise(d * 11.0 + seed)
            p = Vector((d.x * sx, d.y * sy, d.z * sz)) * s * k
            row.append(mb.v((c[0] + p.x, c[1] + p.y, c[2] + max(p.z, -0.6 * s))))
        rows.append(row)
    for j in range(nring):
        for i in range(nseg):
            i2 = (i + 1) % nseg
            mb.f([rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]])


def _water():
    mb = Builder()
    mb.quad([Vector((-9000, 0.5, 0)), Vector((9000, 0.5, 0)), Vector((9000, 9000, 0)),
             Vector((-9000, 9000, 0))])
    return mb.build('Lake', _water_mat(), 'FLAT')


# ---------------------------------------------------------------------------
# Materials (scene-local; deleted with the scene)
# ---------------------------------------------------------------------------

def _haze(n, shader, color=(0.50, 0.62, 0.80, 1.0), dist=30000.0):
    """Aerial perspective: blend towards haze with distance from the camera."""
    cam = n.add('ShaderNodeCameraData')
    f = n.math('DIVIDE', cam.outputs['View Distance'], dist)
    f = n.math('SUBTRACT', 1.0, n.math('EXPONENT', n.math('MULTIPLY', f, -1.0)))
    f = n.math('MULTIPLY', f, 0.7, clamp=True)
    em = n.add('ShaderNodeEmission')
    em.inputs['Color'].default_value = color
    em.inputs['Strength'].default_value = 1.0
    mix = n.add('ShaderNodeMixShader')
    n.link(f, mix.inputs[0])
    n.link(shader, mix.inputs[1])
    n.link(em.outputs[0], mix.inputs[2])
    return mix.outputs[0]


def _terrain_mat():
    m = bpy.data.materials.new('Landscape terrain')
    n = Nodes(m)
    geo = n.add('ShaderNodeNewGeometry')
    sep_n = n.add('ShaderNodeSeparateXYZ')
    n.link(geo.outputs['Normal'], sep_n.inputs[0])
    sep_p = n.add('ShaderNodeSeparateXYZ')
    n.link(geo.outputs['Position'], sep_p.inputs[0])
    z, nz = sep_p.outputs['Z'], sep_n.outputs['Z']
    big = n.noise(geo.outputs['Position'], scale=0.004, detail=6)
    fine = n.noise(geo.outputs['Position'], scale=0.08, detail=8)
    jitter = n.math('MULTIPLY_ADD', big.outputs['Fac'], 500.0, -250.0)
    # snow above a ragged snow line, sliding off the steep rock faces
    snow_h = n.math('GREATER_THAN', n.math('ADD', z, jitter), 900.0)
    snow_s = n.math('GREATER_THAN', n.math('ADD', nz, n.math('MULTIPLY', fine.outputs['Fac'], 0.45)), 0.74)
    snow = n.math('MULTIPLY', snow_h, snow_s)
    # forest below the tree line, on slopes that can hold trees
    forest = n.math('MULTIPLY', n.math('LESS_THAN', n.math('ADD', z, jitter), 620.0),
                    n.math('GREATER_THAN', nz, 0.55))
    rock = n.ramp(fine.outputs['Fac'], [(0.0, hexcol('#2f2c2a')), (0.5, hexcol('#4f4a45')),
                                        (1.0, hexcol('#6f6962'))])
    trees = n.ramp(fine.outputs['Fac'], [(0.0, hexcol('#0f2213')), (0.6, hexcol('#1d3a20')),
                                         (1.0, hexcol('#2f4d2a'))])
    col = n.mix_color(forest, rock, trees)
    col = n.mix_color(snow, col, hexcol('#f3f6fb'))
    shore = n.math('LESS_THAN', z, 1.5)
    col = n.mix_color(shore, col, hexcol('#6b655c'))
    p = n.bsdf(col, 0.85)
    set_input(p, 'Normal', n.bump(fine.outputs['Fac'], 0.6, 2.0))
    n.finish(_haze(n, p.outputs[0]))
    return m


def _pine_mat():
    m = bpy.data.materials.new('Landscape pines')
    n = Nodes(m)
    nz = n.noise(n.texcoord('Object'), scale=0.15, detail=2)
    col = n.ramp(nz.outputs['Fac'], [(0.0, hexcol('#0b1a0c')), (0.5, hexcol('#15301a')),
                                     (1.0, hexcol('#284a25'))])
    p = n.bsdf(col, 0.75)
    set_input(p, 'Sheen Weight', 0.3)
    n.finish(_haze(n, p.outputs[0]))
    return m


def _rock_mat():
    m = bpy.data.materials.new('Landscape rock')
    n = Nodes(m)
    pos = n.texcoord('Object')
    nz = n.noise(pos, scale=3.0, detail=8, rough=0.6)
    col = n.ramp(nz.outputs['Fac'], [(0.0, hexcol('#1f1d1b')), (0.45, hexcol('#3e3a35')),
                                     (0.75, hexcol('#5c564e')), (1.0, hexcol('#7a7368'))])
    geo = n.add('ShaderNodeNewGeometry')
    sep = n.add('ShaderNodeSeparateXYZ')
    n.link(geo.outputs['Position'], sep.inputs[0])
    wet = n.math('LESS_THAN', sep.outputs['Z'], 0.12)
    col = n.mix_color(n.math('MULTIPLY', wet, 0.7), col, hexcol('#2a2723'))
    p = n.bsdf(col, 0.75)
    set_input(p, 'Normal', n.bump(nz.outputs['Fac'], 0.8, 0.05))
    n.finish(p.outputs[0])
    return m


def _water_mat():
    m = bpy.data.materials.new('Landscape lake')
    n = Nodes(m)
    pos = n.mapping(n.texcoord('Object'), scale=(0.6, 3.0, 1.0))
    nz = n.noise(pos, scale=0.25, detail=4)
    p = n.bsdf(hexcol('#174550'), 0.015, IOR=1.33)
    set_input(p, 'Specular IOR Level', 0.5)
    set_input(p, 'Normal', n.bump(nz.outputs['Fac'], 0.06, 0.05))
    n.finish(p.outputs[0])
    return m


def _world(scene):
    w = bpy.data.worlds.new('Landscape sky')
    if bpy.app.version < (5, 0, 0):
        w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    sky = nt.nodes.new('ShaderNodeTexSky')
    sky.sky_type = 'NISHITA'
    sky.sun_disc = False
    sky.sun_elevation = math.radians(28)
    sky.sun_rotation = math.radians(219)
    sky.altitude = 600
    sky.air_density = 1.0
    sky.dust_density = 0.25
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Strength'].default_value = 0.3
    # cumulus layer: noise projected on a plane 1.2 km up, only above the horizon
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    dz = nt.nodes.new('ShaderNodeMath')
    dz.operation = 'MAXIMUM'
    nt.links.new(sep.outputs['Z'], dz.inputs[0])
    dz.inputs[1].default_value = 0.02
    px = nt.nodes.new('ShaderNodeMath')
    px.operation = 'DIVIDE'
    nt.links.new(sep.outputs['X'], px.inputs[0])
    nt.links.new(dz.outputs[0], px.inputs[1])
    py = nt.nodes.new('ShaderNodeMath')
    py.operation = 'DIVIDE'
    nt.links.new(sep.outputs['Y'], py.inputs[0])
    nt.links.new(dz.outputs[0], py.inputs[1])
    cmb = nt.nodes.new('ShaderNodeCombineXYZ')
    nt.links.new(px.outputs[0], cmb.inputs[0])
    nt.links.new(py.outputs[0], cmb.inputs[1])
    cl = nt.nodes.new('ShaderNodeTexNoise')
    cl.inputs['Scale'].default_value = 0.55
    cl.inputs['Detail'].default_value = 7.0
    cl.inputs['Roughness'].default_value = 0.58
    nt.links.new(cmb.outputs[0], cl.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.52
    ramp.color_ramp.elements[1].position = 0.66
    nt.links.new(cl.outputs['Fac'], ramp.inputs[0])
    # fade the clouds out towards the horizon and keep the left side clear
    hor = nt.nodes.new('ShaderNodeMapRange')
    nt.links.new(sep.outputs['Z'], hor.inputs['Value'])
    hor.inputs['From Min'].default_value = 0.06
    hor.inputs['From Max'].default_value = 0.22
    side = nt.nodes.new('ShaderNodeMapRange')
    nt.links.new(sep.outputs['X'], side.inputs['Value'])
    side.inputs['From Min'].default_value = -0.6
    side.inputs['From Max'].default_value = -0.1
    m1 = nt.nodes.new('ShaderNodeMath')
    m1.operation = 'MULTIPLY'
    nt.links.new(ramp.outputs['Color'], m1.inputs[0])
    nt.links.new(hor.outputs['Result'], m1.inputs[1])
    m2 = nt.nodes.new('ShaderNodeMath')
    m2.operation = 'MULTIPLY'
    nt.links.new(m1.outputs[0], m2.inputs[0])
    nt.links.new(side.outputs['Result'], m2.inputs[1])
    # cloud brightness follows the sky (white tops, greyer bases)
    lum = nt.nodes.new('ShaderNodeRGBToBW')
    nt.links.new(sky.outputs['Color'], lum.inputs[0])
    shade = nt.nodes.new('ShaderNodeMapRange')
    nt.links.new(cl.outputs['Fac'], shade.inputs['Value'])
    shade.inputs['From Min'].default_value = 0.55
    shade.inputs['From Max'].default_value = 0.85
    shade.inputs['To Min'].default_value = 1.1
    shade.inputs['To Max'].default_value = 2.4
    cc = nt.nodes.new('ShaderNodeMath')
    cc.operation = 'MULTIPLY'
    nt.links.new(lum.outputs[0], cc.inputs[0])
    nt.links.new(shade.outputs['Result'], cc.inputs[1])
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    nt.links.new(m2.outputs[0], mix.inputs[0])
    nt.links.new(sky.outputs['Color'], mix.inputs[6])
    nt.links.new(cc.outputs[0], mix.inputs[7])
    nt.links.new(mix.outputs[2], bg.inputs['Color'])
    nt.links.new(bg.outputs[0], out.inputs['Surface'])
    scene.world = w
    return w


# ---------------------------------------------------------------------------

def _grade(path, saturation=1.28, contrast=1.08):
    """Wallpaper-style grade: richer colour, firmer contrast, deeper sky."""
    from .textures import load_png, save_png
    import numpy as np
    px = load_png(path)
    lum = (px * np.array([0.2126, 0.7152, 0.0722])).sum(-1, keepdims=True)
    px = lum + (px - lum) * saturation
    px = 0.5 + (px - 0.5) * contrast
    h = px.shape[0]
    # deepen the top of the sky (graduated filter)
    t = np.clip((np.arange(h)[:, None, None] / h - 0.55) / 0.45, 0, 1)
    px = px * (1 - 0.22 * t) + np.array([0.12, 0.30, 0.62]) * 0.22 * t * 1.3
    save_png(np.clip(px, 0, 1), path)


def render(path, res=(1920, 1080), samples=96, seed=4):
    """Build the landscape in a temporary scene, render it to ``path`` and
    delete everything again."""
    before = {k: set(getattr(bpy.data, k)) for k in ('objects', 'meshes', 'materials', 'lights',
                                                    'cameras', 'worlds', 'images')}
    scene = bpy.data.scenes.new('_Landscape')
    rng = random.Random(seed)
    from bathroom_gen import geo
    with geo.target(scene.collection):
        _terrain()
        _forest(rng)
        _rocks(rng)
        _water()
        sun = bpy.data.lights.new('Sun', 'SUN')
        sun.energy = 4.5
        sun.angle = math.radians(1.5)
        sun.color = (1.0, 0.95, 0.88)
        so = bpy.data.objects.new('Sun', sun)
        scene.collection.objects.link(so)
        light_dir = Vector((0.62, 0.5, -0.6)).normalized()      # from the front left
        so.rotation_euler = (-light_dir).to_track_quat('Z', 'Y').to_euler()
        cd = bpy.data.cameras.new('Landscape camera')
        cd.lens = 26
        cd.clip_end = 20000
        cam = bpy.data.objects.new('Landscape camera', cd)
        scene.collection.objects.link(cam)
        cam.location = (0.0, 0.0, 2.6)
        d = Vector((-40.0, 1000.0, 70.0)) - cam.location
        cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        scene.camera = cam
    _world(scene)
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - Punchy'
    except TypeError:
        pass
    scene.view_settings.exposure = 0.0
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True, scene=scene.name)
    _grade(path)
    # clean up everything this function created
    bpy.data.scenes.remove(scene)
    for k, old in before.items():
        coll = getattr(bpy.data, k)
        for item in list(coll):
            if item not in old:
                coll.remove(item)
    return path
