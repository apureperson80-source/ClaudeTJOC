"""Generate the bathroom .blend file (and optionally render previews).

Usage (Blender 4.2+):

    blender --background --python build_bathroom.py -- [options]

or with the standalone ``bpy`` module (pip install bpy):

    python build_bathroom.py [options]

Options:
    --output PATH      .blend file to write (default: bathroom.blend)
    --render           render every camera into renders/
    --cameras A,B      only render cameras whose name contains one of these
    --samples N        Cycles samples for renders (default 256)
    --scale PCT        render resolution percentage (default 100)

The script can also be pasted into Blender's Text Editor and run; it then
replaces the open file's contents with the generated scenes.
"""

import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy  # noqa: E402

from bathroom_gen import scenes  # noqa: E402

# per scene: (resolution, exposure)
RENDER = {
    'Residential Bathroom': ((1500, 1390), -0.2),
    'Public Washroom': ((1700, 1040), -0.2),
    'Fixture Library': ((2000, 1000), -0.8),
}


def parse_args():
    if '--' in sys.argv:                       # blender ... --python file -- args
        argv = sys.argv[sys.argv.index('--') + 1:]
    elif sys.argv and sys.argv[0].endswith('.py'):   # python build_bathroom.py args
        argv = sys.argv[1:]
    else:                                      # Blender's text editor
        argv = []
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--output', default=os.path.join(HERE, 'bathroom.blend'))
    p.add_argument('--render', action='store_true')
    p.add_argument('--cameras', default='')
    p.add_argument('--samples', type=int, default=256)
    p.add_argument('--scale', type=int, default=100)
    p.add_argument('--no-save', action='store_true')
    return p.parse_args(argv)


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    home = bpy.context.scene
    home.name = 'Residential Bathroom'
    public = bpy.data.scenes.new('Public Washroom')
    library = bpy.data.scenes.new('Fixture Library')
    for sc in (home, public, library):
        sc.unit_settings.system = 'METRIC'

    lib = scenes.build_library(library)
    catalogue = scenes.catalogue_set(library)
    cams = {home.name: scenes.build_residential(home, lib),
            public.name: scenes.build_public(public, lib),
            library.name: catalogue}
    for sc in (home, public, library):
        res, exposure = RENDER[sc.name]
        scenes.setup_render(sc, res, exposure=exposure)
    return cams


def render(cams, args):
    out_dir = os.path.join(HERE, 'renders')
    os.makedirs(out_dir, exist_ok=True)
    wanted = [c.strip().lower() for c in args.cameras.split(',') if c.strip()]
    for scene_name, cam_list in cams.items():
        sc = bpy.data.scenes[scene_name]
        sc.cycles.samples = args.samples
        for k, cam in enumerate(cam_list):
            if wanted and not any(w in cam.name.lower() for w in wanted):
                continue
            sc.camera = cam
            # hero shot at full size, close-ups smaller
            scale = args.scale if k == 0 or scene_name == 'Fixture Library' else args.scale * 0.65
            sc.render.resolution_percentage = int(scale)
            fname = cam.name.lower().replace(' - ', '_').replace(' ', '_') + '.png'
            sc.render.filepath = os.path.join(out_dir, fname)
            t = time.time()
            bpy.ops.render.render(write_still=True, scene=sc.name)
            print('Rendered %s in %.0fs' % (fname, time.time() - t))
        sc.camera = cam_list[0]


def main():
    args = parse_args()
    t = time.time()
    cams = build()
    print('Built scenes in %.1fs' % (time.time() - t))
    if not args.no_save:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.output), compress=True)
        print('Saved', args.output)
    if args.render:
        render(cams, args)


if __name__ == '__main__':
    main()
