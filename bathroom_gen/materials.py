"""Physically based material library (Cycles / EEVEE).

Materials are created lazily and cached by name: ``mat('ceramic')``.
Colours are authored as sRGB hex values and converted to linear.
"""

import bpy

from . import textures


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexcol(h, alpha=1.0):
    h = h.lstrip('#')
    rgb = [srgb_to_linear(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4)]
    return (rgb[0], rgb[1], rgb[2], alpha)


# ---------------------------------------------------------------------------
# Node helpers
# ---------------------------------------------------------------------------

class Nodes:
    def __init__(self, material):
        if bpy.app.version < (5, 0, 0):
            material.use_nodes = True
        self.nt = material.node_tree
        self.nt.nodes.clear()
        self.out = self.add('ShaderNodeOutputMaterial', (600, 0))
        self._x = 0

    def add(self, kind, loc=None, **props):
        n = self.nt.nodes.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        if loc is not None:
            n.location = loc
        return n

    def link(self, a, b):
        self.nt.links.new(a, b)

    def bsdf(self, color, rough=0.5, metal=0.0, **inputs):
        p = self.add('ShaderNodeBsdfPrincipled', (200, 0))
        set_input(p, 'Base Color', color)
        set_input(p, 'Roughness', rough)
        set_input(p, 'Metallic', metal)
        for k, v in inputs.items():
            set_input(p, k.replace('_', ' '), v)
        return p

    def mix_color(self, fac, a, b, blend='MIX'):
        m = self.add('ShaderNodeMix', data_type='RGBA', blend_type=blend)
        _feed(self, m.inputs[0], fac)
        _feed(self, m.inputs[6], a)
        _feed(self, m.inputs[7], b)
        return m.outputs[2]

    def math(self, op, a, b=0.0, c=0.0, clamp=False):
        m = self.add('ShaderNodeMath', operation=op, use_clamp=clamp)
        _feed(self, m.inputs[0], a)
        _feed(self, m.inputs[1], b)
        _feed(self, m.inputs[2], c)
        return m.outputs[0]

    def ramp(self, fac, stops):
        r = self.add('ShaderNodeValToRGB')
        cr = r.color_ramp
        while len(cr.elements) > 1:
            cr.elements.remove(cr.elements[-1])
        cr.elements[0].position = stops[0][0]
        cr.elements[0].color = stops[0][1]
        for pos, col in stops[1:]:
            e = cr.elements.new(pos)
            e.color = col
        _feed(self, r.inputs[0], fac)
        return r.outputs[0]

    def attribute(self, name, kind='GEOMETRY'):
        a = self.add('ShaderNodeAttribute', attribute_name=name, attribute_type=kind)
        return a.outputs['Fac']

    def texcoord(self, which='Object'):
        if not hasattr(self, '_tc'):
            self._tc = self.add('ShaderNodeTexCoord')
        return self._tc.outputs[which]

    def mapping(self, vec, scale=(1, 1, 1), loc=(0, 0, 0), rot=(0, 0, 0)):
        m = self.add('ShaderNodeMapping')
        _feed(self, m.inputs['Vector'], vec)
        m.inputs['Scale'].default_value = scale
        m.inputs['Location'].default_value = loc
        m.inputs['Rotation'].default_value = rot
        return m.outputs[0]

    def noise(self, vec=None, scale=5.0, detail=4.0, rough=0.5, distortion=0.0):
        n = self.add('ShaderNodeTexNoise')
        if vec is not None:
            _feed(self, n.inputs['Vector'], vec)
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = rough
        n.inputs['Distortion'].default_value = distortion
        return n

    def bump(self, height, strength=0.1, distance=0.01):
        b = self.add('ShaderNodeBump')
        b.inputs['Strength'].default_value = strength
        b.inputs['Distance'].default_value = distance
        _feed(self, b.inputs['Height'], height)
        return b.outputs['Normal']

    def finish(self, shader_out, volume=None):
        self.link(shader_out, self.out.inputs['Surface'])
        if volume is not None:
            self.link(volume, self.out.inputs['Volume'])


def _feed(nodes, socket, value):
    if hasattr(value, 'is_output') or isinstance(value, bpy.types.NodeSocket):
        nodes.link(value, socket)
    else:
        socket.default_value = value


_ALIASES = {
    'Specular': 'Specular IOR Level',
    'Transmission': 'Transmission Weight',
    'Coat': 'Coat Weight',
    'Sheen': 'Sheen Weight',
    'Subsurface': 'Subsurface Weight',
    'Emission': 'Emission Color',
}


def set_input(node, name, value):
    sock = node.inputs.get(name) or node.inputs.get(_ALIASES.get(name, name))
    if sock is None:
        return
    if hasattr(value, 'is_output') or isinstance(value, bpy.types.NodeSocket):
        node.id_data.links.new(value, sock)
    else:
        sock.default_value = value


# ---------------------------------------------------------------------------
# Material definitions
# ---------------------------------------------------------------------------

_CACHE = {}
_DEFS = {}


def material(fn):
    _DEFS[fn.__name__] = fn
    return fn


def mat(name):
    """Return (and create on first use) the named material."""
    m = _CACHE.get(name)
    if m is not None and m.name in bpy.data.materials:
        return m
    m = bpy.data.materials.new(name.replace('_', ' ').title())
    nodes = Nodes(m)
    _DEFS[name](m, nodes)
    _CACHE[name] = m
    return m


def _simple(m, n, color, rough, metal=0.0, viewport=None, **kw):
    p = n.bsdf(color, rough, metal, **kw)
    n.finish(p.outputs[0])
    m.diffuse_color = viewport or color
    m.roughness = rough
    m.metallic = metal
    return p


# --- ceramics & solid surfaces ---------------------------------------------

@material
def ceramic(m, n):
    p = _simple(m, n, hexcol('#f4f4f1'), 0.04, Coat=0.4, Coat_Roughness=0.02)
    set_input(p, 'Subsurface Weight', 0.03)
    set_input(p, 'Subsurface Radius', (0.02, 0.02, 0.02))


@material
def ceramic_matte(m, n):
    _simple(m, n, hexcol('#eceae4'), 0.45)


@material
def acrylic(m, n):
    _simple(m, n, hexcol('#f5f5f3'), 0.08, Coat=0.3, Coat_Roughness=0.03)


@material
def solid_surface(m, n):
    _simple(m, n, hexcol('#f1f1ee'), 0.22)


@material
def paint_white(m, n):
    nz = n.noise(n.texcoord(), scale=180, detail=6)
    p = n.bsdf(hexcol('#efefec'), 0.72)
    set_input(p, 'Normal', n.bump(nz.outputs['Fac'], 0.04, 0.002))
    n.finish(p.outputs[0])
    m.diffuse_color = hexcol('#efefec')


@material
def door_paint(m, n):
    _simple(m, n, hexcol('#f3f3f0'), 0.32)


@material
def frame_white(m, n):
    _simple(m, n, hexcol('#f6f6f3'), 0.45)


@material
def ceiling_tile(m, n):
    nz = n.noise(n.texcoord(), scale=60, detail=8, rough=0.7, distortion=0.4)
    fiss = n.ramp(nz.outputs['Fac'], [(0.0, (0, 0, 0, 1)), (0.36, (0, 0, 0, 1)),
                                      (0.40, (1, 1, 1, 1)), (1.0, (1, 1, 1, 1))])
    p = n.bsdf(hexcol('#eeeeeb'), 0.95)
    set_input(p, 'Normal', n.bump(fiss, 0.25, 0.002))
    n.finish(p.outputs[0])


# --- metals ----------------------------------------------------------------

def _metal(m, n, color, rough, aniso=0.0, brushed=False):
    p = n.bsdf(color, rough, 1.0, Anisotropic=aniso)
    if brushed:
        # fine streaks for a brushed finish
        vec = n.mapping(n.texcoord(), scale=(1.0, 1.0, 1.0))
        nz = n.noise(vec, scale=400, detail=2)
        streak = n.mapping(n.texcoord(), scale=(2.0, 2.0, 400.0))
        nz2 = n.noise(streak, scale=30, detail=1)
        rough_mix = n.math('MULTIPLY_ADD', nz2.outputs['Fac'], 0.12, rough - 0.06)
        set_input(p, 'Roughness', rough_mix)
        set_input(p, 'Normal', n.bump(nz.outputs['Fac'], 0.02, 0.001))
    n.finish(p.outputs[0])
    m.diffuse_color = color
    m.metallic = 1.0
    m.roughness = rough


@material
def brass(m, n):
    _metal(m, n, hexcol('#e6c38a'), 0.24, aniso=0.5, brushed=True)


@material
def chrome(m, n):
    _metal(m, n, (0.92, 0.92, 0.93, 1.0), 0.04)


@material
def steel_brushed(m, n):
    _metal(m, n, (0.70, 0.70, 0.70, 1.0), 0.28, aniso=0.6, brushed=True)


@material
def aluminium(m, n):
    _metal(m, n, (0.80, 0.81, 0.82, 1.0), 0.32)


@material
def mirror(m, n):
    _metal(m, n, (0.94, 0.94, 0.94, 1.0), 0.0)


# --- glass & liquids -------------------------------------------------------

def _glass(m, n, tint, absorb, rough=0.0, ior=1.52, density=8.0):
    p = n.bsdf(tint, rough, Transmission=1.0, IOR=ior)
    vol = n.add('ShaderNodeVolumeAbsorption')
    vol.inputs['Color'].default_value = absorb
    vol.inputs['Density'].default_value = density
    n.finish(p.outputs[0], vol.outputs[0])
    m.diffuse_color = (tint[0], tint[1], tint[2], 0.3)


@material
def glass(m, n):
    _glass(m, n, (0.97, 1.0, 0.98, 1.0), (0.55, 0.9, 0.75, 1.0), density=4.0)


@material
def glass_thin(m, n):
    """Thin-sheet glass: Fresnel reflections over a transparent base, so it
    does not cast the black shadows a refractive solid would without caustics."""
    fr = n.add('ShaderNodeFresnel')
    fr.inputs['IOR'].default_value = 1.52
    tr = n.add('ShaderNodeBsdfTransparent')
    tr.inputs['Color'].default_value = (0.94, 0.98, 0.96, 1.0)
    gl = n.add('ShaderNodeBsdfGlossy')
    gl.inputs['Roughness'].default_value = 0.0
    mix = n.add('ShaderNodeMixShader')
    n.link(fr.outputs[0], mix.inputs[0])
    n.link(tr.outputs[0], mix.inputs[1])
    n.link(gl.outputs[0], mix.inputs[2])
    n.finish(mix.outputs[0])
    m.diffuse_color = (0.9, 1.0, 0.95, 0.2)


@material
def glass_frosted(m, n):
    _glass(m, n, (0.96, 0.98, 0.98, 1.0), (0.7, 0.9, 0.85, 1.0), rough=0.35, density=3.0)


@material
def glass_green(m, n):
    _glass(m, n, (0.55, 0.85, 0.6, 1.0), (0.05, 0.35, 0.12, 1.0), density=40.0)


@material
def glass_amber(m, n):
    _glass(m, n, (0.95, 0.7, 0.45, 1.0), (0.45, 0.16, 0.03, 1.0), density=40.0)


@material
def water(m, n):
    p = n.bsdf((1.0, 1.0, 1.0, 1.0), 0.0, Transmission=1.0, IOR=1.333)
    vol = n.add('ShaderNodeVolumeAbsorption')
    vol.inputs['Color'].default_value = (0.75, 0.92, 0.95, 1.0)
    vol.inputs['Density'].default_value = 2.0
    n.finish(p.outputs[0], vol.outputs[0])


@material
def smoke_window(m, n):
    _simple(m, n, hexcol('#3a4048'), 0.05, Transmission=0.35, viewport=hexcol('#3a4048'))


# --- tiles & grout ---------------------------------------------------------

def _glazed_tile(m, n, base, dark, light, rough=0.09, wave=0.03):
    r = n.attribute('tile_rand')
    col = n.ramp(r, [(0.0, dark), (0.5, base), (1.0, light)])
    # subtle in-tile mottling of the glaze
    nz = n.noise(n.texcoord(), scale=35, detail=3)
    col = n.mix_color(n.math('MULTIPLY', nz.outputs['Fac'], 0.12), col, dark, 'MULTIPLY')
    p = n.bsdf(col, rough, Coat=0.25, Coat_Roughness=0.03)
    # wavy glaze surface catches reflections like real handmade tiles
    wav = n.noise(n.texcoord(), scale=9, detail=2)
    set_input(p, 'Normal', n.bump(wav.outputs['Fac'], wave, 0.003))
    n.finish(p.outputs[0])
    m.diffuse_color = base
    m.roughness = rough


@material
def tile_sage(m, n):
    _glazed_tile(m, n, hexcol('#6e9b84'), hexcol('#66937c'), hexcol('#77a48d'))


@material
def tile_lilac(m, n):
    _glazed_tile(m, n, hexcol('#7660b0'), hexcol('#6f59a9'), hexcol('#7e69b7'), wave=0.015)


def _grout(m, n, color):
    nz = n.noise(n.texcoord(), scale=400, detail=4)
    p = n.bsdf(color, 0.92)
    set_input(p, 'Normal', n.bump(nz.outputs['Fac'], 0.3, 0.001))
    n.finish(p.outputs[0])
    m.diffuse_color = color


@material
def grout_white(m, n):
    _grout(m, n, hexcol('#e2e1dc'))


@material
def grout_grey(m, n):
    _grout(m, n, hexcol('#9e9b95'))


@material
def marble_floor(m, n):
    r = n.attribute('tile_rand')
    # offset texture space per tile so every slab shows a different cut
    off = n.add('ShaderNodeCombineXYZ')
    n.link(n.math('MULTIPLY', r, 17.0), off.inputs[0])
    n.link(n.math('MULTIPLY', r, 31.0), off.inputs[1])
    vec = n.add('ShaderNodeVectorMath', operation='ADD')
    n.link(n.texcoord(), vec.inputs[0])
    n.link(off.outputs[0], vec.inputs[1])
    warp = n.noise(vec.outputs[0], scale=1.4, detail=6, rough=0.6, distortion=1.6)
    wave = n.add('ShaderNodeTexWave', wave_type='BANDS', bands_direction='DIAGONAL')
    wave.inputs['Scale'].default_value = 1.2
    wave.inputs['Distortion'].default_value = 7.0
    wave.inputs['Detail'].default_value = 6.0
    n.link(warp.outputs['Color'], wave.inputs['Vector'])
    veins = n.ramp(wave.outputs['Fac'], [(0.0, hexcol('#b4b4b2')), (0.05, hexcol('#cfcfcc')),
                                         (0.22, hexcol('#dcdcd9')), (1.0, hexcol('#e3e3e0'))])
    cloud = n.noise(vec.outputs[0], scale=4.0, detail=5)
    col = n.mix_color(0.18, veins, cloud.outputs['Color'], 'OVERLAY')
    p = n.bsdf(col, 0.18, Coat=0.15, Coat_Roughness=0.08)
    n.finish(p.outputs[0])
    m.diffuse_color = hexcol('#d8d8d5')


@material
def floor_speckle(m, n):
    r = n.attribute('tile_rand')
    base = n.ramp(r, [(0.0, hexcol('#cfc9bf')), (1.0, hexcol('#ddd8cf'))])
    sp = n.noise(n.texcoord(), scale=220, detail=1)
    dots = n.ramp(sp.outputs['Fac'], [(0.0, (0, 0, 0, 1)), (0.68, (0, 0, 0, 1)),
                                      (0.70, (1, 1, 1, 1)), (1.0, (1, 1, 1, 1))])
    col = n.mix_color(n.math('MULTIPLY', dots, 0.6), base, hexcol('#7d776e'))
    p = n.bsdf(col, 0.32)
    n.finish(p.outputs[0])
    m.diffuse_color = hexcol('#d6d1c8')


# --- plastics, laminates, rubber -------------------------------------------

@material
def plastic_white(m, n):
    _simple(m, n, hexcol('#f2f2f0'), 0.22)


@material
def plastic_grey(m, n):
    _simple(m, n, hexcol('#8f9398'), 0.35)


@material
def plastic_dark(m, n):
    _simple(m, n, hexcol('#2b2d30'), 0.35)


@material
def rubber_black(m, n):
    _simple(m, n, hexcol('#151515'), 0.65)


@material
def sensor_black(m, n):
    _simple(m, n, hexcol('#08080a'), 0.04)


@material
def laminate_grey(m, n):
    _simple(m, n, hexcol('#d9dadb'), 0.38)


@material
def laminate_oak(m, n):
    tc = n.texcoord()
    vec = n.mapping(tc, scale=(1.0, 1.0, 0.12))
    warp = n.noise(vec, scale=3.0, detail=4, distortion=0.6)
    wave = n.add('ShaderNodeTexWave', wave_type='RINGS', rings_direction='Z')
    wave.inputs['Scale'].default_value = 6.0
    wave.inputs['Distortion'].default_value = 4.0
    wave.inputs['Detail'].default_value = 3.0
    n.link(warp.outputs['Color'], wave.inputs['Vector'])
    fine = n.noise(n.mapping(tc, scale=(60.0, 60.0, 2.0)), scale=4.0, detail=2)
    g = n.math('ADD', n.math('MULTIPLY', wave.outputs['Fac'], 0.8),
               n.math('MULTIPLY', fine.outputs['Fac'], 0.25))
    col = n.ramp(g, [(0.0, hexcol('#9b6436')), (0.45, hexcol('#c18649')),
                     (0.8, hexcol('#d29a5c')), (1.0, hexcol('#b97c41'))])
    p = n.bsdf(col, 0.42, Coat=0.2, Coat_Roughness=0.2)
    set_input(p, 'Normal', n.bump(g, 0.05, 0.002))
    n.finish(p.outputs[0])
    m.diffuse_color = hexcol('#c18649')


@material
def towel_cream(m, n):
    _fabric(m, n, hexcol('#ece6da'))


@material
def mat_sage(m, n):
    _fabric(m, n, hexcol('#a9bfae'), ribs=True)


def _fabric(m, n, color, ribs=False):
    nz = n.noise(n.texcoord(), scale=900, detail=2)
    h = nz.outputs['Fac']
    if ribs:
        wave = n.add('ShaderNodeTexWave', wave_type='BANDS', bands_direction='X')
        wave.inputs['Scale'].default_value = 60.0
        n.link(n.texcoord(), wave.inputs['Vector'])
        h = n.math('ADD', h, n.math('MULTIPLY', wave.outputs['Fac'], 1.5))
    col = n.mix_color(n.math('MULTIPLY', nz.outputs['Fac'], 0.3), color,
                      (color[0] * 0.7, color[1] * 0.7, color[2] * 0.7, 1), 'MIX')
    p = n.bsdf(col, 0.95, Sheen=0.8, Sheen_Roughness=0.4)
    set_input(p, 'Normal', n.bump(h, 0.6, 0.002))
    n.finish(p.outputs[0])
    m.diffuse_color = color


@material
def paper(m, n):
    nz = n.noise(n.texcoord(), scale=300, detail=3)
    p = n.bsdf(hexcol('#f6f6f2'), 0.85, Subsurface=0.15)
    set_input(p, 'Subsurface Radius', (0.004, 0.004, 0.004))
    set_input(p, 'Normal', n.bump(nz.outputs['Fac'], 0.15, 0.001))
    n.finish(p.outputs[0])


@material
def cardboard(m, n):
    _simple(m, n, hexcol('#b08d66'), 0.8)


@material
def bin_liner(m, n):
    _simple(m, n, hexcol('#151515'), 0.25)


# --- lights ----------------------------------------------------------------

def _emit(m, n, color, strength):
    e = n.add('ShaderNodeEmission')
    e.inputs['Color'].default_value = color
    e.inputs['Strength'].default_value = strength
    n.finish(e.outputs[0])
    m.diffuse_color = color


@material
def led_warm(m, n):
    _emit(m, n, (1.0, 0.82, 0.62, 1.0), 6.0)


@material
def led_panel(m, n):
    _emit(m, n, (0.96, 0.98, 1.0, 1.0), 3.0)


@material
def led_downlight(m, n):
    _emit(m, n, (1.0, 0.9, 0.78, 1.0), 25.0)


@material
def touch_icon(m, n):
    _emit(m, n, (1.0, 1.0, 1.0, 1.0), 1.5)


@material
def indicator_red(m, n):
    _simple(m, n, hexcol('#c1272d'), 0.3)


@material
def indicator_green(m, n):
    _simple(m, n, hexcol('#2e9e48'), 0.3)


# --- plants ----------------------------------------------------------------

def _leaf(m, n, c_dark, c_mid, c_light, variegate=False):
    r = n.attribute('leaf_rand')
    col = n.ramp(r, [(0.0, c_dark), (0.55, c_mid), (1.0, c_light)])
    if variegate:
        streak = n.add('ShaderNodeTexWave', wave_type='BANDS', bands_direction='X')
        streak.inputs['Scale'].default_value = 3.0
        streak.inputs['Distortion'].default_value = 12.0
        streak.inputs['Detail'].default_value = 4.0
        n.link(n.texcoord('Object'), streak.inputs['Vector'])
        ys = n.ramp(streak.outputs['Fac'], [(0.0, (0, 0, 0, 1)), (0.88, (0, 0, 0, 1)),
                                            (0.95, (1, 1, 1, 1)), (1.0, (1, 1, 1, 1))])
        col = n.mix_color(n.math('MULTIPLY', ys, 0.45), col, hexcol('#c9c56e'))
    p = n.bsdf(col, 0.38, Coat=0.2)
    tr = n.add('ShaderNodeBsdfTranslucent')
    n.link(col, tr.inputs['Color'])
    mix = n.add('ShaderNodeMixShader')
    mix.inputs[0].default_value = 0.22
    n.link(p.outputs[0], mix.inputs[1])
    n.link(tr.outputs[0], mix.inputs[2])
    n.finish(mix.outputs[0])
    m.diffuse_color = c_mid


@material
def leaf_pothos(m, n):
    _leaf(m, n, hexcol('#1f5a22'), hexcol('#2f7a2e'), hexcol('#4f9a3c'), variegate=True)


@material
def leaf_palm(m, n):
    _leaf(m, n, hexcol('#25592a'), hexcol('#3a7a35'), hexcol('#5a9446'))


@material
def plant_stem(m, n):
    _simple(m, n, hexcol('#5c7f3a'), 0.5)


@material
def soil(m, n):
    nz = n.noise(n.texcoord(), scale=120, detail=6)
    p = n.bsdf(hexcol('#2a1d14'), 1.0)
    set_input(p, 'Normal', n.bump(nz.outputs['Fac'], 0.8, 0.004))
    n.finish(p.outputs[0])


# --- images ----------------------------------------------------------------

@material
def art_print(m, n):
    img = textures.art_print_image()
    t = n.add('ShaderNodeTexImage')
    t.image = img
    # the print is a flat XZ plane: map its generated X/Z bounds to U/V
    sep = n.add('ShaderNodeSeparateXYZ')
    n.link(n.texcoord('Generated'), sep.inputs[0])
    uv = n.add('ShaderNodeCombineXYZ')
    n.link(sep.outputs['X'], uv.inputs['X'])
    n.link(sep.outputs['Z'], uv.inputs['Y'])
    n.link(uv.outputs[0], t.inputs['Vector'])
    p = n.bsdf((1, 1, 1, 1), 0.6)
    n.link(t.outputs['Color'], p.inputs['Base Color'])
    n.finish(p.outputs[0])
    m.diffuse_color = (0.9, 0.8, 0.6, 1.0)
