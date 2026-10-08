"""Materials for the props.

Registered in the bathroom material library (``bathroom_gen.materials``), so
``mat(name)`` returns props and bathroom materials alike. Every material is a
single named colour/finish -- objects never mix materials -- and the names say
what colour they are (``Plastic Black Gloss``, ``Kraft Outer`` ...).
"""

import bpy

from bathroom_gen.materials import (Nodes, _emit, _metal, _simple, hexcol, mat, material,
                                    set_input)

__all__ = ['mat', 'image_material', 'screen_material', 'hexcol']


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uv_axis(n, axis='X'):
    sep = n.add('ShaderNodeSeparateXYZ')
    n.link(n.texcoord('UV'), sep.inputs[0])
    return sep.outputs[axis]


def _speckle_bump(n, p, scale=900.0, strength=0.05):
    nz = n.noise(n.texcoord('Object'), scale=scale, detail=2)
    set_input(p, 'Normal', n.bump(nz.outputs['Fac'], strength, 0.0005))


def _plastic(m, n, color, rough, coat=0.0, texture=0.0, scale=900.0):
    kw = {'Coat': coat, 'Coat_Roughness': 0.05} if coat else {}
    p = n.bsdf(color, rough, **kw)
    if texture:
        _speckle_bump(n, p, scale, texture)
    n.finish(p.outputs[0])
    m.diffuse_color = color
    m.roughness = rough


# ---------------------------------------------------------------------------
# Cardboard
# ---------------------------------------------------------------------------

def _kraft(m, n, color, dark, flute=0.008, flute_amp=0.06, blotch=0.35):
    obj = n.texcoord('Object')
    fib = n.noise(n.mapping(obj, scale=(1.0, 1.0, 3.0)), scale=380, detail=6, rough=0.65)
    blot = n.noise(obj, scale=7, detail=3, rough=0.5)
    # flutes under the liner: faint stripes across the board's U direction
    phase = n.math('MULTIPLY', _uv_axis(n, 'X'), 6.283185 / flute)
    wave = n.math('MULTIPLY_ADD', n.math('SINE', phase), 0.5, 0.5)
    shade = n.math('ADD', n.math('MULTIPLY', blot.outputs['Fac'], blotch),
                   n.math('MULTIPLY', fib.outputs['Fac'], 0.25))
    shade = n.math('ADD', shade, n.math('MULTIPLY', wave, flute_amp), clamp=True)
    col = n.mix_color(shade, color, dark)
    p = n.bsdf(col, 0.82)
    set_input(p, 'Sheen Weight', 0.15)
    height = n.math('ADD', n.math('MULTIPLY', wave, 0.6),
                    n.math('MULTIPLY', fib.outputs['Fac'], 0.4))
    set_input(p, 'Normal', n.bump(height, 0.12, 0.0006))
    n.finish(p.outputs[0])
    m.diffuse_color = color
    m.roughness = 0.82


@material
def kraft_outer(m, n):
    _kraft(m, n, hexcol('#c9a173'), hexcol('#a67b4c'))


@material
def kraft_inner(m, n):
    _kraft(m, n, hexcol('#cdab80'), hexcol('#b08a5e'), flute_amp=0.04, blotch=0.25)


@material
def kraft_edge(m, n):
    nz = n.noise(n.texcoord('Object'), scale=900, detail=3)
    col = n.mix_color(n.math('MULTIPLY', nz.outputs['Fac'], 0.5),
                      hexcol('#dcc29b'), hexcol('#a88459'))
    p = n.bsdf(col, 0.9)
    n.finish(p.outputs[0])
    m.diffuse_color = hexcol('#d3b88f')


@material
def packing_tape(m, n):
    p = n.bsdf(hexcol('#b98a55'), 0.18, Coat=0.6, Coat_Roughness=0.08)
    set_input(p, 'Transmission Weight', 0.25)
    n.finish(p.outputs[0])
    m.diffuse_color = hexcol('#b98a55')


# ---------------------------------------------------------------------------
# Plastics & paints
# ---------------------------------------------------------------------------

@material
def plastic_black_gloss(m, n):
    _plastic(m, n, hexcol('#0b0b0d'), 0.16, coat=0.45)


@material
def plastic_black_matte(m, n):
    _plastic(m, n, hexcol('#141518'), 0.5, texture=0.08)


@material
def plastic_black_satin(m, n):
    _plastic(m, n, hexcol('#18191c'), 0.3, texture=0.03)


@material
def plastic_charcoal(m, n):
    _plastic(m, n, hexcol('#2e3034'), 0.45, texture=0.08)


@material
def plastic_dark_grey(m, n):
    _plastic(m, n, hexcol('#45484d'), 0.4, texture=0.05)


@material
def plastic_mid_grey(m, n):
    _plastic(m, n, hexcol('#8d9095'), 0.35, texture=0.04)


@material
def plastic_light_grey(m, n):
    _plastic(m, n, hexcol('#cfd1d3'), 0.28, coat=0.2)


@material
def plastic_silver_grey(m, n):
    _plastic(m, n, hexcol('#b4b7bb'), 0.25, coat=0.3)


@material
def plastic_white_gloss(m, n):
    _plastic(m, n, hexcol('#eeeeec'), 0.15, coat=0.4)


@material
def plastic_clear(m, n):
    p = n.bsdf(hexcol('#f4f6f8'), 0.04, Transmission=1.0, IOR=1.49)
    n.finish(p.outputs[0])
    m.diffuse_color = (0.95, 0.96, 0.97, 0.3)


@material
def plastic_smoke(m, n):
    p = n.bsdf(hexcol('#202428'), 0.06, Transmission=0.6, IOR=1.49)
    n.finish(p.outputs[0])
    m.diffuse_color = hexcol('#202428')


@material
def studio_white(m, n):
    _simple(m, n, hexcol('#f2f2f2'), 0.9)


@material
def studio_backdrop(m, n):
    """White sweep that glows a little, so it photographs pure white while the
    products keep their true colours (like a lit infinity cove)."""
    p = n.bsdf(hexcol('#f4f4f4'), 0.9)
    set_input(p, 'Emission Color', (1.0, 1.0, 1.0, 1.0))
    set_input(p, 'Emission Strength', 0.2)
    n.finish(p.outputs[0])
    m.diffuse_color = hexcol('#f4f4f4')


@material
def print_black(m, n):
    _simple(m, n, hexcol('#111111'), 0.6)


@material
def print_white(m, n):
    _simple(m, n, hexcol('#f4f4f4'), 0.45)


@material
def print_grey(m, n):
    _simple(m, n, hexcol('#9a9da1'), 0.5)


@material
def label_white(m, n):
    _simple(m, n, hexcol('#f6f6f3'), 0.35)


# ---------------------------------------------------------------------------
# Metals
# ---------------------------------------------------------------------------

@material
def silver_powder_coat(m, n):
    """Silver metallic paint: metallic base with fine flake sparkle."""
    flake = n.noise(n.texcoord('Object'), scale=2500, detail=1)
    rough = n.math('MULTIPLY_ADD', flake.outputs['Fac'], 0.12, 0.26)
    p = n.bsdf(hexcol('#b7bbc0'), 0.3, 0.75, Coat=0.35, Coat_Roughness=0.08)
    set_input(p, 'Roughness', rough)
    set_input(p, 'Normal', n.bump(flake.outputs['Fac'], 0.04, 0.0002))
    n.finish(p.outputs[0])
    m.diffuse_color = hexcol('#b7bbc0')
    m.metallic = 0.75


@material
def black_powder_coat(m, n):
    nz = n.noise(n.texcoord('Object'), scale=1500, detail=2)
    p = n.bsdf(hexcol('#121315'), 0.42)
    set_input(p, 'Normal', n.bump(nz.outputs['Fac'], 0.06, 0.0003))
    n.finish(p.outputs[0])
    m.diffuse_color = hexcol('#121315')


@material
def gunmetal(m, n):
    _metal(m, n, hexcol('#3c3f44'), 0.35)


@material
def coil_steel(m, n):
    _metal(m, n, (0.78, 0.79, 0.80, 1.0), 0.18)


# ---------------------------------------------------------------------------
# Lights, displays, indicators
# ---------------------------------------------------------------------------

@material
def led_red(m, n):
    _emit(m, n, (1.0, 0.08, 0.03, 1.0), 12.0)


@material
def led_red_off(m, n):
    _simple(m, n, hexcol('#2b0808'), 0.3)


@material
def led_green(m, n):
    _emit(m, n, (0.15, 1.0, 0.25, 1.0), 10.0)


@material
def led_blue(m, n):
    _emit(m, n, (0.1, 0.45, 1.0, 1.0), 10.0)


@material
def led_white(m, n):
    _emit(m, n, (0.9, 0.95, 1.0, 1.0), 10.0)


@material
def led_amber(m, n):
    _emit(m, n, (1.0, 0.55, 0.08, 1.0), 10.0)


@material
def lcd_blue(m, n):
    _emit(m, n, hexcol('#3f8fe8'), 2.5)


@material
def fluorescent_tube(m, n):
    _emit(m, n, (0.95, 0.97, 1.0, 1.0), 14.0)


@material
def bulb_warm(m, n):
    _emit(m, n, (1.0, 0.78, 0.5, 1.0), 30.0)


@material
def screen_off(m, n):
    _plastic(m, n, hexcol('#050607'), 0.06, coat=0.5)


# ---------------------------------------------------------------------------
# Liquids & foods
# ---------------------------------------------------------------------------

def _ink(m, n, color):
    p = n.bsdf(color, 0.08, Coat=0.5, Coat_Roughness=0.03)
    set_input(p, 'Subsurface Weight', 0.2)
    set_input(p, 'Subsurface Radius', (0.002, 0.002, 0.002))
    n.finish(p.outputs[0])
    m.diffuse_color = color


@material
def ink_black(m, n):
    _ink(m, n, hexcol('#0d0d10'))


@material
def ink_cyan(m, n):
    _ink(m, n, hexcol('#0097d6'))


@material
def ink_magenta(m, n):
    _ink(m, n, hexcol('#d6127a'))


@material
def ink_yellow(m, n):
    _ink(m, n, hexcol('#f5d000'))


@material
def ink_red(m, n):
    _ink(m, n, hexcol('#d3202c'))


@material
def ink_grey(m, n):
    _ink(m, n, hexcol('#77797d'))


@material
def coffee(m, n):
    p = n.bsdf(hexcol('#2a160b'), 0.05, Coat=0.6, Coat_Roughness=0.0)
    n.finish(p.outputs[0])
    m.diffuse_color = hexcol('#2a160b')


# ---------------------------------------------------------------------------
# Image-mapped materials (one image each)
# ---------------------------------------------------------------------------

def image_material(name, image, rough=0.4, coat=0.0, emission=0.0, interp='Linear'):
    """Material showing ``image`` through the object's UV map."""
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = bpy.data.materials.new(name)
    n = Nodes(m)
    t = n.add('ShaderNodeTexImage')
    t.image = image
    t.interpolation = interp
    n.link(n.texcoord('UV'), t.inputs['Vector'])
    kw = {'Coat': coat, 'Coat_Roughness': 0.06} if coat else {}
    p = n.bsdf((1, 1, 1, 1), rough, **kw)
    n.link(t.outputs['Color'], p.inputs['Base Color'])
    if emission:
        set_input(p, 'Emission Color', t.outputs['Color'])
        set_input(p, 'Emission Strength', emission)
    n.finish(p.outputs[0])
    m.diffuse_color = (0.8, 0.8, 0.8, 1.0)
    return m


def _mix_vec(n, fac, a, b):
    m = n.add('ShaderNodeMix', data_type='VECTOR')
    n.link(fac, m.inputs[0])
    for sock, v in ((m.inputs[4], a), (m.inputs[5], b)):
        if hasattr(v, 'is_output') or isinstance(v, bpy.types.NodeSocket):
            n.link(v, sock)
        else:
            sock.default_value = v
    return m.outputs[1]


def screen_material(name, image, strength=1.2, rough=0.12, atlas=False, coat=0.4, specular=0.5):
    """Glossy display glass showing ``image`` as emitted light.

    With ``atlas`` the screen shows a rectangle of the image chosen by the
    custom properties ``scr_min`` and ``scr_size`` (x, y, 0): those of the
    collection instance if it has them, else those of the screen object
    itself, else the whole image."""
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = bpy.data.materials.new(name)
    n = Nodes(m)
    uv = n.texcoord('UV')
    if atlas:
        def props(kind):
            lo = n.add('ShaderNodeAttribute', attribute_name='scr_min', attribute_type=kind)
            sz = n.add('ShaderNodeAttribute', attribute_name='scr_size', attribute_type=kind)
            sep = n.add('ShaderNodeSeparateXYZ')
            n.link(sz.outputs['Vector'], sep.inputs[0])
            return lo.outputs['Vector'], sz.outputs['Vector'], n.math('GREATER_THAN', sep.outputs['X'], 1e-6)
        lo_i, sz_i, has_i = props('INSTANCER')
        lo_o, sz_o, has_o = props('OBJECT')
        size = _mix_vec(n, has_i, _mix_vec(n, has_o, (1.0, 1.0, 0.0), sz_o), sz_i)
        lo = _mix_vec(n, has_i, _mix_vec(n, has_o, (0.0, 0.0, 0.0), lo_o), lo_i)
        mul = n.add('ShaderNodeVectorMath', operation='MULTIPLY_ADD')
        n.link(uv, mul.inputs[0])
        n.link(size, mul.inputs[1])
        n.link(lo, mul.inputs[2])
        uv = mul.outputs[0]
    t = n.add('ShaderNodeTexImage')
    t.image = image
    t.extension = 'EXTEND'
    n.link(uv, t.inputs['Vector'])
    p = n.bsdf(hexcol('#030304'), rough, Coat=coat, Coat_Roughness=0.03)
    set_input(p, 'Specular IOR Level', specular)
    set_input(p, 'Emission Color', t.outputs['Color'])
    set_input(p, 'Emission Strength', strength)
    n.finish(p.outputs[0])
    m.diffuse_color = (0.2, 0.3, 0.4, 1.0)
    return m


# ---------------------------------------------------------------------------
# Furniture, fabrics, rooms
# ---------------------------------------------------------------------------

def _laminate(m, n, color, rough=0.35, grain=0.04):
    tc = n.mapping(n.texcoord('Object'), scale=(1.0, 14.0, 1.0))
    nz = n.noise(tc, scale=40, detail=3)
    col = n.mix_color(n.math('MULTIPLY', nz.outputs['Fac'], grain * 4), color,
                      (color[0] * 0.8, color[1] * 0.8, color[2] * 0.8, 1.0))
    p = n.bsdf(col, rough, Coat=0.15, Coat_Roughness=0.2)
    n.finish(p.outputs[0])
    m.diffuse_color = color
    m.roughness = rough


@material
def desk_charcoal(m, n):
    _laminate(m, n, hexcol('#2b2c2f'), 0.32)


@material
def laminate_white(m, n):
    _laminate(m, n, hexcol('#e8e8e4'), 0.3, grain=0.01)


@material
def laminate_light_oak(m, n):
    _laminate(m, n, hexcol('#c9a87c'), 0.38, grain=0.08)


def _fabric_weave(m, n, color):
    nz = n.noise(n.texcoord('Object'), scale=700, detail=2)
    weave = n.add('ShaderNodeTexWave', wave_type='BANDS', bands_direction='X')
    weave.inputs['Scale'].default_value = 300.0
    n.link(n.texcoord('Object'), weave.inputs['Vector'])
    h = n.math('ADD', nz.outputs['Fac'], n.math('MULTIPLY', weave.outputs['Fac'], 0.5))
    p = n.bsdf(color, 0.92, Sheen=0.6, Sheen_Roughness=0.5)
    set_input(p, 'Normal', n.bump(h, 0.35, 0.001))
    n.finish(p.outputs[0])
    m.diffuse_color = color


@material
def fabric_charcoal(m, n):
    _fabric_weave(m, n, hexcol('#2d3036'))


@material
def fabric_blue(m, n):
    _fabric_weave(m, n, hexcol('#34557f'))


@material
def fabric_grey(m, n):
    _fabric_weave(m, n, hexcol('#80848b'))


@material
def mesh_black(m, n):
    """Chair-back mesh: dark weave, a little see-through look via bump."""
    w1 = n.add('ShaderNodeTexWave', wave_type='BANDS', bands_direction='X')
    w1.inputs['Scale'].default_value = 120.0
    n.link(n.texcoord('Object'), w1.inputs['Vector'])
    w2 = n.add('ShaderNodeTexWave', wave_type='BANDS', bands_direction='Z')
    w2.inputs['Scale'].default_value = 120.0
    n.link(n.texcoord('Object'), w2.inputs['Vector'])
    h = n.math('MULTIPLY', w1.outputs['Fac'], w2.outputs['Fac'])
    p = n.bsdf(hexcol('#141518'), 0.7)
    set_input(p, 'Normal', n.bump(h, 0.5, 0.001))
    n.finish(p.outputs[0])
    m.diffuse_color = hexcol('#141518')


@material
def steel_blue(m, n):
    _plastic(m, n, hexcol('#1f4f9c'), 0.35, coat=0.2)


@material
def steel_orange(m, n):
    _plastic(m, n, hexcol('#e46f1b'), 0.35, coat=0.2)


@material
def plastic_red(m, n):
    _plastic(m, n, hexcol('#c22f2c'), 0.3)


@material
def plastic_blue(m, n):
    _plastic(m, n, hexcol('#2b62ad'), 0.3)


@material
def wood_pallet(m, n):
    tc = n.mapping(n.texcoord('Object'), scale=(1.0, 1.0, 1.0))
    wave = n.add('ShaderNodeTexWave', wave_type='BANDS', bands_direction='X')
    wave.inputs['Scale'].default_value = 12.0
    wave.inputs['Distortion'].default_value = 6.0
    n.link(tc, wave.inputs['Vector'])
    col = n.ramp(wave.outputs['Fac'], [(0.0, hexcol('#b08452')), (0.6, hexcol('#cfa877')),
                                       (1.0, hexcol('#d9b98b'))])
    p = n.bsdf(col, 0.85)
    n.finish(p.outputs[0])
    m.diffuse_color = hexcol('#c9a06c')


@material
def carpet_dark(m, n):
    nz = n.noise(n.texcoord('Object'), scale=600, detail=4)
    big = n.noise(n.texcoord('Object'), scale=3, detail=2)
    col = n.mix_color(n.math('MULTIPLY', big.outputs['Fac'], 0.3), hexcol('#26292e'),
                      hexcol('#1b1d21'))
    p = n.bsdf(col, 0.95)
    set_input(p, 'Normal', n.bump(nz.outputs['Fac'], 0.6, 0.002))
    n.finish(p.outputs[0])
    m.diffuse_color = hexcol('#23262a')


@material
def wall_dark(m, n):
    nz = n.noise(n.texcoord('Object'), scale=200, detail=4)
    p = n.bsdf(hexcol('#22262c'), 0.8)
    set_input(p, 'Normal', n.bump(nz.outputs['Fac'], 0.05, 0.002))
    n.finish(p.outputs[0])
    m.diffuse_color = hexcol('#22262c')


@material
def acoustic_panel(m, n):
    nz = n.noise(n.texcoord('Object'), scale=900, detail=3)
    p = n.bsdf(hexcol('#2b3038'), 0.95, Sheen=0.4)
    set_input(p, 'Normal', n.bump(nz.outputs['Fac'], 0.4, 0.001))
    n.finish(p.outputs[0])
    m.diffuse_color = hexcol('#2b3038')


@material
def wall_light(m, n):
    nz = n.noise(n.texcoord('Object'), scale=180, detail=5)
    p = n.bsdf(hexcol('#d8d8d3'), 0.8)
    set_input(p, 'Normal', n.bump(nz.outputs['Fac'], 0.04, 0.002))
    n.finish(p.outputs[0])
    m.diffuse_color = hexcol('#d8d8d3')


@material
def floor_concrete(m, n):
    nz = n.noise(n.texcoord('Object'), scale=3, detail=8, rough=0.6)
    fine = n.noise(n.texcoord('Object'), scale=120, detail=4)
    col = n.mix_color(n.math('MULTIPLY', nz.outputs['Fac'], 0.5), hexcol('#a3a19b'),
                      hexcol('#7c7a74'))
    p = n.bsdf(col, 0.55)
    set_input(p, 'Normal', n.bump(fine.outputs['Fac'], 0.1, 0.002))
    n.finish(p.outputs[0])
    m.diffuse_color = hexcol('#94928c')


@material
def floor_vinyl(m, n):
    nz = n.noise(n.texcoord('Object'), scale=40, detail=6)
    col = n.mix_color(n.math('MULTIPLY', nz.outputs['Fac'], 0.25), hexcol('#bdb8ae'),
                      hexcol('#9f9a90'))
    p = n.bsdf(col, 0.3)
    n.finish(p.outputs[0])
    m.diffuse_color = hexcol('#b5b0a6')


@material
def floor_line_yellow(m, n):
    _simple(m, n, hexcol('#e2b318'), 0.5)


@material
def exit_green(m, n):
    _emit(m, n, hexcol('#18c25a'), 4.0)


@material
def wall_beige(m, n):
    nz = n.noise(n.texcoord('Object'), scale=180, detail=5)
    p = n.bsdf(hexcol('#c9bfab'), 0.8)
    set_input(p, 'Normal', n.bump(nz.outputs['Fac'], 0.04, 0.002))
    n.finish(p.outputs[0])
    m.diffuse_color = hexcol('#c9bfab')


@material
def wall_blue_grey(m, n):
    nz = n.noise(n.texcoord('Object'), scale=180, detail=5)
    p = n.bsdf(hexcol('#a7b1ba'), 0.8)
    set_input(p, 'Normal', n.bump(nz.outputs['Fac'], 0.04, 0.002))
    n.finish(p.outputs[0])
    m.diffuse_color = hexcol('#a7b1ba')


@material
def steel_grey(m, n):
    _plastic(m, n, hexcol('#8a8e93'), 0.4, coat=0.1)
