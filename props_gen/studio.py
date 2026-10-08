"""Photo studio for product shots: white cyclorama, soft-box lights, cameras."""

import math

import bpy
from mathutils import Vector

from bathroom_gen.geo import link
from .materials import mat
from .mesh import Builder


def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def camera(name, loc, target, lens=50.0, shift=(0.0, 0.0), sensor=36.0):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_width = sensor
    cam.shift_x, cam.shift_y = shift
    cam.clip_start = 0.02
    cam.clip_end = 500.0
    obj = bpy.data.objects.new(name, cam)
    link(obj)
    obj.location = loc
    look_at(obj, target)
    return obj


def area_light(name, loc, target, power, size, size_y=None, color=(1.0, 1.0, 1.0),
               visible=False, spread=180.0):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.energy = power
    ld.color = color
    if size_y is None:
        ld.shape = 'SQUARE'
        ld.size = size
    else:
        ld.shape = 'RECTANGLE'
        ld.size, ld.size_y = size, size_y
    if hasattr(ld, 'spread'):
        ld.spread = math.radians(spread)
    obj = bpy.data.objects.new(name, ld)
    link(obj)
    obj.location = loc
    look_at(obj, target)
    if not visible:
        for attr in ('visible_camera', 'visible_glossy', 'visible_transmission'):
            if hasattr(obj, attr):
                setattr(obj, attr, False)
    return obj


def point_light(name, loc, power, radius=0.05, color=(1.0, 1.0, 1.0)):
    ld = bpy.data.lights.new(name, 'POINT')
    ld.energy = power
    ld.color = color
    ld.shadow_soft_size = radius
    obj = bpy.data.objects.new(name, ld)
    link(obj)
    obj.location = loc
    return obj


def spot_light(name, loc, target, power, angle=60.0, blend=0.6, radius=0.03,
               color=(1.0, 1.0, 1.0)):
    ld = bpy.data.lights.new(name, 'SPOT')
    ld.energy = power
    ld.color = color
    ld.spot_size = math.radians(angle)
    ld.spot_blend = blend
    ld.shadow_soft_size = radius
    obj = bpy.data.objects.new(name, ld)
    link(obj)
    obj.location = loc
    look_at(obj, target)
    return obj


def cyclorama(x0, x1, depth=6.0, height=4.0, radius=1.2, back_y=0.0, name='Cyclorama'):
    """Seamless floor-to-wall backdrop: floor for y < back_y - radius, then a
    cove of ``radius`` curving up into a wall at y = back_y."""
    prof = [(back_y - depth, 0.0)]
    for k in range(13):
        a = math.pi / 2 * k / 12
        prof.append((back_y - radius + radius * math.sin(a), radius - radius * math.cos(a)))
    prof.append((back_y, height))
    mb = Builder()
    rings = [[Vector((x, y, z)) for (y, z) in prof] for x in (x1, x0)]
    mb.loft(rings, closed=False)
    return mb.build(name, mat('studio_backdrop'), 'SMOOTH')


def soft_box_rig(center, width, height=2.2, dist=3.2, power=1.0, key_side=-1):
    """Three-light product setup around ``center``: big key soft box, fill on
    the other side and a top light. ``power`` scales everything."""
    c = Vector(center)
    key = area_light('Key light', c + Vector((key_side * dist * 0.75, -dist, height)), c,
                     900 * power, 2.4 * max(1.0, width / 2), 1.6)
    fill = area_light('Fill light', c + Vector((-key_side * dist * 0.9, -dist * 0.8, height * 0.6)),
                      c, 320 * power, 2.0, 1.4)
    top = area_light('Top light', c + Vector((0.0, -0.4, height + 1.4)), c, 600 * power,
                     max(2.0, width), 1.6)
    return [key, fill, top]
