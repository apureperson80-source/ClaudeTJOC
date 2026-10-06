"""Export the bathroom models as Roblox-ready OBJ files.

Usage:

    blender --background --python export_roblox.py -- [options]
    python export_roblox.py [options]          # with the standalone bpy module

Writes to ``roblox/``:

    fixtures/<name>.obj + .mtl   every library fixture on its own, centred
    rooms/<scene>.obj + .mtl     each room fully assembled
    apply_materials.lua          Studio command-bar script that gives every
                                 imported part its Roblox colour/material
    textures/art_print.png       image for the framed print

What the export does to fit Roblox:
  * collection instances are made real, modifiers applied (subdivision at a
    lower level), lights/cameras dropped;
  * meshes are split per material and into chunks below the MeshPart
    triangle limit; every part is named ``<object>__<material key>`` so the
    Lua script can style it;
  * box-projected UVs are added so Roblox's textured materials tile properly;
  * geometry is scaled from metres to studs (1 stud = 0.28 m) and written
    Y-up, the way Studio's 3D Importer expects.

Options:
    --blend PATH     source file (default: bathroom.blend next to this script)
    --out DIR        output directory (default: roblox/)
    --studs-per-m N  scale factor (default 3.571)
    --max-tris N     triangle budget per part (default 19000)
    --subdiv N       subdivision level for curved fixtures (default 1)
"""

import argparse
import os
import re
import sys

import bpy  # must precede bmesh/mathutils when run with the bpy module
import bmesh
import numpy as np
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOMS = ('Residential Bathroom', 'Public Washroom')
LIBRARY = 'Fixture Library'


def parse_args():
    if '--' in sys.argv:
        argv = sys.argv[sys.argv.index('--') + 1:]
    elif sys.argv and sys.argv[0].endswith('.py'):
        argv = sys.argv[1:]
    else:
        argv = []
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--blend', default=os.path.join(HERE, 'bathroom.blend'))
    p.add_argument('--out', default=os.path.join(HERE, 'roblox'))
    p.add_argument('--studs-per-m', type=float, default=1.0 / 0.28)
    p.add_argument('--max-tris', type=int, default=19000)
    p.add_argument('--subdiv', type=int, default=1)
    return p.parse_args(argv)


def slug(name):
    return re.sub(r'[^A-Za-z0-9]+', '_', name).strip('_')


def mat_key(material):
    return slug(material.name) if material else 'Default'


# ---------------------------------------------------------------------------
# Scene handling
# ---------------------------------------------------------------------------

def open_scene(blend, scene_name, subdiv):
    """Open the file with only ``scene_name`` left, so it is the context scene."""
    bpy.ops.wm.open_mainfile(filepath=blend)
    _EXPORT_MATS.clear()
    for sc in list(bpy.data.scenes):
        if sc.name != scene_name:
            bpy.data.scenes.remove(sc)
    for ob in bpy.data.objects:
        for m in ob.modifiers:
            if m.type == 'SUBSURF':
                m.levels = min(m.render_levels, subdiv)
    return bpy.context.scene


def evaluated_parts(scene, keep=None):
    """Yield (name, evaluated object, world matrix) for every mesh that
    renders, including the objects inside collection instances."""
    dg = bpy.context.evaluated_depsgraph_get()
    for inst in dg.object_instances:
        ob = inst.object
        if ob.type != 'MESH':
            continue
        if keep is not None and not keep(inst):
            continue
        if inst.is_instance and inst.parent is not None:
            name = '%s_%s' % (inst.parent.name, ob.original.name)
        else:
            name = ob.original.name
        # instance references are only valid during iteration: keep originals
        yield name, ob.original, inst.matrix_world.copy(), dg


# ---------------------------------------------------------------------------
# Mesh preparation
# ---------------------------------------------------------------------------

def realize(name, ob, matrix, dg):
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True,
                                         depsgraph=dg)
    me.transform(matrix)
    if matrix.determinant() < 0:      # mirrored instances (cubicle row)
        me.flip_normals()
    me.name = name
    return me


def hard_surface(ob):
    return any(m.type in ('WEIGHTED_NORMAL', 'BEVEL') for m in ob.modifiers)


def add_box_uvs(me, tile=1.0):
    """Box-projected UVs in world units (one texture repeat per ``tile`` m)."""
    if not me.polygons:
        return
    uv = me.uv_layers.new(name='UVMap')
    n = len(me.loops)
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    lv = np.empty(n, dtype=np.int64)
    me.loops.foreach_get('vertex_index', lv)
    pn = np.empty(len(me.polygons) * 3)
    me.polygons.foreach_get('normal', pn)
    pn = np.abs(pn.reshape(-1, 3))
    ls = np.empty(len(me.polygons), dtype=np.int64)
    lt = np.empty(len(me.polygons), dtype=np.int64)
    me.polygons.foreach_get('loop_start', ls)
    me.polygons.foreach_get('loop_total', lt)
    axis = np.repeat(np.argmax(pn, axis=1), lt)
    p = co[lv]
    u = np.where(axis == 0, p[:, 1], p[:, 0])
    v = np.where(axis == 2, p[:, 1], p[:, 2])
    uv.data.foreach_set('uv', (np.stack([u, v], 1) / tile).ravel())


def add_print_uvs(me):
    """The framed print plane gets a proper 0..1 mapping for its image."""
    co = np.array([v.co[:] for v in me.vertices])
    lo, hi = co.min(0), co.max(0)
    span = np.maximum(hi - lo, 1e-6)
    horiz = 0 if span[0] >= span[1] else 1
    uv = me.uv_layers.new(name='UVMap')
    vals = []
    for loop in me.loops:
        p = co[loop.vertex_index]
        vals += [(p[horiz] - lo[horiz]) / span[horiz], (p[2] - lo[2]) / span[2]]
    uv.data.foreach_set('uv', vals)


def split_mesh(me, max_tris, flat):
    """Split by material, then into chunks of at most ``max_tris`` triangles.
    Returns [(material, mesh)]. Unsplit meshes keep their custom normals."""
    me.calc_loop_triangles()
    mats = list(me.materials)
    by_mat = {}
    for p in me.polygons:
        by_mat.setdefault(p.material_index, []).append(p.index)
    if len(by_mat) <= 1 and len(me.loop_triangles) <= max_tris:
        mat = mats[next(iter(by_mat))] if by_mat and mats else None
        return [(mat, me)]
    out = []
    tris_per_poly = [len(p.vertices) - 2 for p in me.polygons]
    for mi, polys in by_mat.items():
        chunks, cur, count = [], [], 0
        for pi in polys:
            if cur and count + tris_per_poly[pi] > max_tris:
                chunks.append(cur)
                cur, count = [], 0
            cur.append(pi)
            count += tris_per_poly[pi]
        if cur:
            chunks.append(cur)
        for k, chunk in enumerate(chunks):
            bm = bmesh.new()
            bm.from_mesh(me)
            bm.faces.ensure_lookup_table()
            keep = set(chunk)
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in keep], context='FACES')
            if flat:
                for f in bm.faces:
                    f.smooth = False
            part = bpy.data.meshes.new('%s_%d_%d' % (me.name, mi, k))
            bm.to_mesh(part)
            bm.free()
            part.materials.clear()
            if mats and mi < len(mats):
                part.materials.append(mats[mi])
            out.append((mats[mi] if mats and mi < len(mats) else None, part))
    return out


_EXPORT_MATS = {}


def export_material(mat):
    """Plain Principled stand-in so the .mtl carries the real colour (the
    procedural node trees can't be written to OBJ/MTL)."""
    key = mat_key(mat)
    m = _EXPORT_MATS.get(key)
    if m is not None:
        return m
    rgb, enum, refl, transp = roblox_style(key, mat)
    m = bpy.data.materials.new(key)
    if bpy.app.version < (5, 0, 0):
        m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    lin = [((c / 255 + 0.055) / 1.055) ** 2.4 if c > 10 else c / 255 / 12.92 for c in rgb]
    p.inputs['Base Color'].default_value = (*lin, 1.0)
    p.inputs['Metallic'].default_value = 1.0 if enum == 'Metal' else 0.0
    p.inputs['Roughness'].default_value = 0.1 if enum in ('Glass', 'SmoothPlastic') else 0.5
    p.inputs['Alpha'].default_value = 1.0 - transp
    if enum == 'Neon':
        p.inputs['Emission Color'].default_value = (*lin, 1.0)
        p.inputs['Emission Strength'].default_value = 1.0
    _EXPORT_MATS[key] = m
    return m


def build_export_objects(parts, max_tris, offset=None):
    """Turn evaluated parts into flat, uniquely named export objects."""
    coll = bpy.data.collections.new('Roblox export')
    bpy.context.scene.collection.children.link(coll)
    used = {}
    for name, ob, matrix, dg in parts:
        if offset is not None:
            matrix = Matrix.Translation(-offset) @ matrix
        me = realize(name, ob, matrix, dg)
        if not me.polygons:
            continue
        for mat, part in split_mesh(me, max_tris, flat=hard_surface(ob)):
            if mat is not None and mat.name.startswith('Art Print'):
                add_print_uvs(part)
            else:
                add_box_uvs(part)
            part.materials.clear()
            part.materials.append(export_material(mat))
            base = '%s__%s' % (slug(name), mat_key(mat))
            used[base] = used.get(base, 0) + 1
            obj_name = base if used[base] == 1 else '%s_%d__%s' % (
                slug(name), used[base], mat_key(mat))
            ob = bpy.data.objects.new(obj_name, part)
            coll.objects.link(ob)
    return coll


def export_obj(coll, path, scale):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    for ob in coll.objects:
        ob.select_set(True)
    bpy.ops.wm.obj_export(
        filepath=path, export_selected_objects=True, apply_modifiers=False,
        global_scale=scale, forward_axis='NEGATIVE_Z', up_axis='Y',
        export_uv=True, export_normals=True, export_materials=True,
        export_triangulated_mesh=True, export_object_groups=False,
        path_mode='STRIP')
    tris = 0
    for ob in coll.objects:
        ob.data.calc_loop_triangles()
        tris += len(ob.data.loop_triangles)
    print('  %-48s %4d parts %8d triangles' % (os.path.relpath(path, HERE),
                                                len(coll.objects), tris))


# ---------------------------------------------------------------------------
# Roblox styling script
# ---------------------------------------------------------------------------

def _srgb255(c):
    def f(x):
        x = max(0.0, min(1.0, x))
        return 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055
    return tuple(int(round(f(x) * 255)) for x in c[:3])


def roblox_style(key, material):
    """(RGB, Enum.Material name, reflectance, transparency) for a material."""
    k = key.lower()
    rgb = _srgb255(material.diffuse_color) if material else (200, 200, 200)
    if k.startswith(('led', 'touch')):
        return rgb, 'Neon', 0, 0
    if k.startswith('glass_thin'):
        return (230, 245, 240), 'Glass', 0.1, 0.85
    if k.startswith(('glass', 'water', 'smoke')):
        t = {'glass': 0.6, 'glass_frosted': 0.4, 'water': 0.5, 'smoke_window': 0.3}.get(k, 0.35)
        return rgb, 'Glass', 0.05, t
    if k == 'mirror':
        return (220, 225, 228), 'SmoothPlastic', 0.9, 0
    if k == 'chrome':
        return (205, 208, 212), 'SmoothPlastic', 0.5, 0
    if material is not None and material.metallic > 0.5:
        return rgb, 'Metal', 0.15, 0
    if 'oak' in k:
        return rgb, 'Wood', 0, 0
    if 'marble' in k:
        return rgb, 'Marble', 0.05, 0
    if k.startswith(('towel', 'mat_')):
        return rgb, 'Fabric', 0, 0
    if k.startswith(('tile', 'ceramic', 'acrylic')):
        return rgb, 'SmoothPlastic', 0.08, 0
    if k.startswith(('leaf', 'plant')):
        return rgb, 'SmoothPlastic', 0.02, 0
    if k == 'soil':
        return rgb, 'Ground', 0, 0
    return rgb, 'SmoothPlastic', 0, 0


LUA_TEMPLATE = '''-- Styles the bathroom parts imported from %(src)s.
-- Usage: import the .obj with File > Import 3D, select the imported model(s)
-- in the Explorer, then paste this whole script into the Command Bar
-- (View > Command Bar) and press Enter.
local STYLES = {
%(rows)s
}

-- Roblox asset id of art_print.png once uploaded (Asset Manager), e.g.
-- "rbxassetid://1234567890". Leave empty to keep the print a flat colour.
local ART_PRINT_TEXTURE = ""

local Selection = game:GetService("Selection")
local styled, unknown = 0, {}
local roots = Selection:Get()
if #roots == 0 then roots = {workspace} end
for _, root in ipairs(roots) do
	for _, part in ipairs(root:GetDescendants()) do
		if part:IsA("MeshPart") then
			local key = string.match(part.Name, "__([%%w_]+)$")
			local s = key and STYLES[key]
			if s then
				part.Color = s[1]
				part.Material = s[2]
				part.Reflectance = s[3]
				part.Transparency = s[4]
				part.CastShadow = s[4] < 0.5
				if key == "Art_Print" and ART_PRINT_TEXTURE ~= "" then
					part.TextureID = ART_PRINT_TEXTURE
					part.Color = Color3.new(1, 1, 1)
				end
				part.Anchored = true
				styled += 1
			elseif key then
				unknown[key] = true
			end
		end
	end
end
print(("Bathroom: styled %%d parts"):format(styled))
for key in pairs(unknown) do warn("Bathroom: no style for " .. key) end
'''


def write_lua(path, blend):
    rows = []
    for m in sorted(bpy.data.materials, key=lambda m: m.name):
        if m.users == 0 and not m.use_fake_user:
            continue
        key = mat_key(m)
        rgb, enum, refl, transp = roblox_style(key, m)
        rows.append('\t%-16s = {Color3.fromRGB(%3d, %3d, %3d), Enum.Material.%s, %.2f, %.2f},'
                    % (key, rgb[0], rgb[1], rgb[2], enum, refl, transp))
    with open(path, 'w') as f:
        f.write(LUA_TEMPLATE % {'src': os.path.basename(blend), 'rows': '\n'.join(rows)})


def save_art_print(path):
    img = next((i for i in bpy.data.images if i.name.startswith('Art Print')), None)
    if img is None:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()


# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    blend = os.path.abspath(args.blend)
    out = os.path.abspath(args.out)
    print('Exporting %s -> %s (%.3f studs per metre)' % (blend, out, args.studs_per_m))

    # every library fixture as its own model, centred on its catalogue spot
    open_scene(blend, LIBRARY, args.subdiv)
    lib_root = bpy.data.collections[LIBRARY]
    fixtures = list(lib_root.children)
    for coll in fixtures:
        names = {o.name for o in coll.all_objects}
        offset = coll.instance_offset.copy()
        parts = list(evaluated_parts(
            bpy.context.scene, keep=lambda inst, names=names: (
                not inst.is_instance and inst.object.original.name in names)))
        exp = build_export_objects(parts, args.max_tris, offset)
        export_obj(exp, os.path.join(out, 'fixtures', slug(coll.name) + '.obj'),
                   args.studs_per_m)
    save_art_print(os.path.join(out, 'textures', 'art_print.png'))
    write_lua(os.path.join(out, 'apply_materials.lua'), blend)

    # whole rooms
    for room in ROOMS:
        open_scene(blend, room, args.subdiv)
        exp = build_export_objects(list(evaluated_parts(bpy.context.scene)), args.max_tris)
        export_obj(exp, os.path.join(out, 'rooms', slug(room) + '.obj'), args.studs_per_m)


if __name__ == '__main__':
    main()
