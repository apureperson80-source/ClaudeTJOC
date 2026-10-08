"""Generate the props .blend file (and optionally render previews).

Models built from the reference photos: open cardboard boxes, a modern and a
classic snack vending machine, a 50" TV, a laser and a photo printer, and a
security control room whose video wall shows CCTV feeds of the other props.

Usage (Blender 4.2+):

    blender --background --python build_props.py -- [options]

or with the standalone ``bpy`` module (pip install bpy):

    python build_props.py [options]

Options:
    --output PATH        .blend file to write (default: props.blend)
    --render             render every camera into renders/
    --cameras A,B        only render cameras whose name contains one of these
    --samples N          Cycles samples for renders (default 256)
    --scale PCT          render resolution percentage (default 100)
    --refresh-screens    re-render the TV landscape and the CCTV feeds
                         (props_gen/images/) instead of reusing them
    --no-feeds           do not render missing CCTV feeds (screens show
                         'no signal' for them)

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

from props_gen import landscape, scenes, screens  # noqa: E402
from props_gen.textures import load_png, packed_image  # noqa: E402

LIBRARY, CONTROL, CCTV = 'Prop Library', 'Security Control Room', 'CCTV Sets'

# per scene: (resolution, exposure, view transform, world colour, world strength)
RENDER = {
    LIBRARY: ((1600, 1200), -1.3, 'Standard', (1.0, 1.0, 1.0), 0.35),
    CONTROL: ((1600, 900), 0.6, 'AgX', (0.12, 0.16, 0.22), 0.04),
    CCTV: ((800, 450), -1.1, 'AgX', (0.5, 0.52, 0.55), 0.05),
}
# per camera overrides of the scene resolution
CAMERA_RES = {
    'Product - Boxes': (1400, 1050),
    'Product - Vending Machines': (1300, 1150),
    'Product - TV': (1400, 1000),
    'Product - Printers': (1600, 1000),
    'Product - Control Room Kit': (1600, 1050),
    'Product - Set Dressing': (2000, 1000),
}


def isolate_rig(scene, cam):
    """Product shots: light only the camera's own product group."""
    rig = cam.get('rig')
    for ob in scene.objects:
        if ob.type == 'LIGHT' and 'rig' in ob:
            ob.hide_render = rig is not None and ob['rig'] != rig


def parse_args():
    if '--' in sys.argv:                       # blender ... --python file -- args
        argv = sys.argv[sys.argv.index('--') + 1:]
    elif sys.argv and sys.argv[0].endswith('.py'):   # python build_props.py args
        argv = sys.argv[1:]
    else:                                      # Blender's text editor
        argv = []
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--output', default=os.path.join(HERE, 'props.blend'))
    p.add_argument('--render', action='store_true')
    p.add_argument('--cameras', default='')
    p.add_argument('--samples', type=int, default=256)
    p.add_argument('--scale', type=int, default=100)
    p.add_argument('--refresh-screens', action='store_true')
    p.add_argument('--no-feeds', action='store_true')
    p.add_argument('--no-save', action='store_true')
    return p.parse_args(argv)


def tv_wallpaper(refresh):
    path = os.path.join(screens.IMAGES, 'landscape.png')
    if refresh or not os.path.exists(path):
        print('Rendering the landscape wallpaper ...')
        os.makedirs(screens.IMAGES, exist_ok=True)
        landscape.render(path)
    return packed_image('TV Wallpaper', load_png(path), quality=92)


def build(args):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    library = bpy.context.scene
    library.name = LIBRARY
    control = bpy.data.scenes.new(CONTROL)
    cctv = bpy.data.scenes.new(CCTV)
    for sc in (library, control, cctv):
        sc.unit_settings.system = 'METRIC'
    tv_wallpaper(args.refresh_screens)

    lib = scenes.build_library(library)
    cams = {LIBRARY: scenes.catalogue_set(library)}
    cams[CCTV], feeds = scenes.build_cctv(cctv, lib)
    for sc in (library, control, cctv):
        res, exposure, view, world, strength = RENDER[sc.name]
        scenes.setup_render(sc, res, exposure=exposure, view=view, world=world, world_strength=strength)

    labels = [label for _, label in feeds]
    screens.build_atlas(labels)                   # UIs + any feeds already rendered
    missing = [i for i in range(len(feeds)) if not os.path.exists(screens.feed_path(i))]
    if args.refresh_screens or (missing and not args.no_feeds):
        print('Rendering %d CCTV feeds ...' % len(feeds))
        screens.render_feeds(cctv, feeds)
        screens.build_atlas(labels)
    cctv.camera = feeds[0][0]
    cams[CONTROL] = scenes.build_control_room(control, lib)
    return cams


def render(cams, args):
    out_dir = os.path.join(HERE, 'renders')
    os.makedirs(out_dir, exist_ok=True)
    wanted = [c.strip().lower() for c in args.cameras.split(',') if c.strip()]
    for scene_name, cam_list in cams.items():
        if scene_name == CCTV and not any('cctv' in w for w in wanted):
            continue                              # the feeds are in props_gen/images
        sc = bpy.data.scenes[scene_name]
        sc.cycles.samples = args.samples
        base = (sc.render.resolution_x, sc.render.resolution_y)
        for cam in cam_list:
            if wanted and not any(w in cam.name.lower() for w in wanted):
                continue
            sc.camera = cam
            isolate_rig(sc, cam)
            sc.render.resolution_x, sc.render.resolution_y = CAMERA_RES.get(cam.name, base)
            sc.render.resolution_percentage = args.scale
            fname = 'props_' + cam.name.lower().replace(' - ', '_').replace(' ', '_') + '.png'
            sc.render.filepath = os.path.join(out_dir, fname)
            t = time.time()
            bpy.ops.render.render(write_still=True, scene=sc.name)
            print('Rendered %s in %.0fs' % (fname, time.time() - t))
        sc.render.resolution_x, sc.render.resolution_y = base
        sc.camera = cam_list[0]
        for ob in sc.objects:              # leave every light on in the saved file
            if ob.type == 'LIGHT':
                ob.hide_render = False


def main():
    args = parse_args()
    t = time.time()
    cams = build(args)
    print('Built scenes in %.1fs' % (time.time() - t))
    if not args.no_save:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.output), compress=True)
        print('Saved', args.output)
    if args.render:
        render(cams, args)


if __name__ == '__main__':
    main()
