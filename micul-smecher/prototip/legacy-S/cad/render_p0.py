"""render_p0.py -- Blender preview renders of SOUL-P0 from the exported STL files.

    blender -b -P render_p0.py -- [variant]        (variant: plastic | alu | alu_band, default plastic)

Reads ../stl/assembly/<variant>_*.stl (product frame, mm) and writes ../img/*.png:
  <v>_assembled_front / _hero / _side / _back / _bottom, <v>_exploded, <v>_part_<name> (one per printed part).
These are engineering previews (grey clay + colour-coded internals), not marketing renders.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
ASM = os.path.join(ROOT, 'stl', 'assembly')
IMG = os.path.join(ROOT, 'img')
os.makedirs(IMG, exist_ok=True)
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
VAR = argv[0] if argv else 'plastic'
ONLY = argv[1:]  # optional list of shot names

MM = 0.001
NS = Vector((0.0, 1.0, -0.0396)).normalized()        # seam normal (toward the back)
N_OUT = Vector((0.0, -math.cos(math.radians(7.63)), math.sin(math.radians(7.63))))

COL = {
    'front_shell': (0.93, 0.91, 0.87, 1), 'back_shell': (0.93, 0.91, 0.87, 1), 'seam_band': (0.25, 0.25, 0.27, 1),
    'chassis': (0.95, 0.45, 0.12, 1), 'pin_pwr': (0.2, 0.55, 0.9, 1), 'pin_boot': (0.2, 0.55, 0.9, 1),
    'battery': (0.55, 0.72, 0.9, 1), 'speaker': (0.15, 0.15, 0.16, 1), 'usb_plug': (0.6, 0.6, 0.62, 1),
    'board_glass': (0.01, 0.01, 0.012, 1), 'board_module': (0.08, 0.08, 0.09, 1),
    'board_components': (0.1, 0.35, 0.2, 1),
}
if VAR.startswith('alu'):
    COL['front_shell'] = COL['back_shell'] = (0.78, 0.79, 0.80, 1)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception:
        pass
    sc.render.resolution_x = 1400
    sc.render.resolution_y = 1400
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'
    w = bpy.data.worlds.new('w')
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.94, 0.93, 0.91, 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = 0.9
    return sc


def mat(name, rgba, metal=0.0, rough=0.45, glass=False):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = rgba
    b.inputs['Metallic'].default_value = metal
    b.inputs['Roughness'].default_value = 0.08 if glass else rough
    return m


def load(name):
    fn = os.path.join(ASM, f'{VAR}_{name}.stl')
    if not os.path.exists(fn):
        return None
    try:
        bpy.ops.wm.stl_import(filepath=fn)
    except Exception:
        bpy.ops.import_mesh.stl(filepath=fn)
    ob = bpy.context.selected_objects[0]
    ob.name = name
    ob.scale = (MM, MM, MM)
    bpy.ops.object.transform_apply(scale=True)
    bpy.ops.object.shade_smooth()
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    except Exception:
        ob.data.use_auto_smooth = True if hasattr(ob.data, 'use_auto_smooth') else None
    key = name if name in COL else ('board_' + name.split('board_')[-1] if 'board_' in name else name)
    rgba = COL.get(key, (0.12, 0.12, 0.13, 1))
    metal = 0.9 if (VAR.startswith('alu') and name in ('front_shell', 'back_shell')) else 0.0
    rough = 0.35 if metal else (0.12 if name == 'board_glass' else 0.5)
    ob.data.materials.append(mat('m_' + name, rgba, metal, rough))
    return ob


def lights(sc, target=Vector((0, 0, 0.037))):
    for loc, e, s in [((-0.25, -0.35, 0.35), 60, 0.25), ((0.35, -0.1, 0.2), 25, 0.3), ((0.0, 0.35, 0.3), 30, 0.3)]:
        L = bpy.data.lights.new('L', 'AREA')
        L.energy = e
        L.size = s
        o = bpy.data.objects.new('L', L)
        sc.collection.objects.link(o)
        o.location = loc
        d = target - Vector(loc)
        o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    # floor
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, -0.0001))
    fl = bpy.context.active_object
    fl.data.materials.append(mat('floor', (0.94, 0.93, 0.91, 1), rough=0.9))
    fl.is_shadow_catcher = False


def camera(sc, loc, target, lens=85, ortho=None):
    c = bpy.data.cameras.new('C')
    c.lens = lens
    c.clip_start = 0.001
    if ortho:
        c.type = 'ORTHO'
        c.ortho_scale = ortho
    o = bpy.data.objects.new('C', c)
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = o
    return o


def shoot(sc, name):
    if ONLY and name not in ONLY:
        return
    sc.render.filepath = os.path.join(IMG, f'{VAR}_{name}.png')
    bpy.ops.render.render(write_still=True)
    print('wrote', sc.render.filepath)


SHELLS = ['front_shell', 'back_shell', 'seam_band']
INSIDE = ['chassis', 'pin_pwr', 'pin_boot', 'battery', 'speaker', 'board_glass', 'board_module', 'board_components',
          'board_header_8pin', 'board_usb_receptacle', 'board_conn_spk', 'board_conn_bat', 'board_standoff_1',
          'board_standoff_2', 'board_standoff_3', 'board_btn_pwr', 'board_btn_boot']


def assembled():
    sc = reset()
    obs = [load(n) for n in SHELLS + ['board_glass']]
    lights(sc)
    tgt = (0, 0, 0.036)
    D = 0.42
    views = {
        'assembled_front': ((0, -D, 0.040), tgt),
        'assembled_hero': ((-D * 0.62, -D * 0.72, 0.12), tgt),
        'assembled_side': ((D, 0.0, 0.040), tgt),
        'assembled_back': ((0.22, D * 0.9, 0.10), tgt),
        'assembled_bottom': ((0.08, -0.10, -0.40), (0, 0, 0.0)),
    }
    for k, (loc, t) in views.items():
        if k == 'assembled_bottom':
            bpy.data.objects['Plane'].hide_render = True
        camera(sc, loc, t, lens=100)
        shoot(sc, k)
        bpy.data.objects['Plane'].hide_render = False


def exploded():
    sc = reset()
    offs = {'front_shell': -26, 'board': -12, 'chassis': 8, 'battery': 14, 'speaker': 14, 'back_shell': 34,
            'seam_band': 4, 'pin_pwr': 44, 'pin_boot': 44}
    for n in SHELLS + INSIDE:
        ob = load(n)
        if ob is None:
            continue
        k = 'board' if n.startswith('board_') else n
        d = offs.get(k, 0) * MM
        v = NS * d
        if n.startswith('pin_'):
            v = Vector((math.copysign(10, 1 if 'boot' in n else -1) * MM, 30 * MM, 14 * MM))
        ob.location = v
    lights(sc, Vector((0, 0.004, 0.04)))
    bpy.data.objects['Plane'].location.z = -0.004
    camera(sc, (0.40, -0.26, 0.20), (0.0, 0.004, 0.034), lens=62)
    shoot(sc, 'exploded')
    # inside view: back shell hidden
    for n in ['back_shell', 'seam_band']:
        if n in bpy.data.objects:
            bpy.data.objects[n].hide_render = True
    for ob in bpy.data.objects:
        if ob.type == 'MESH' and ob.name != 'Plane':
            ob.location = (0, 0, 0)
    camera(sc, (0.16, 0.36, 0.14), (0, 0, 0.036), lens=85)
    shoot(sc, 'inside_open_back')


def parts():
    names = ['front_shell', 'back_shell', 'chassis', 'seam_band', 'pin_pwr']
    for n in names:
        sc = reset()
        ob = load(n)
        if ob is None:
            continue
        lights(sc)
        bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        c = sum(bb, Vector()) / 8
        size = max((max(p[i] for p in bb) - min(p[i] for p in bb)) for i in range(3))
        bpy.data.objects['Plane'].location.z = min(p[2] for p in bb) - 0.0002
        if n == 'front_shell':
            loc = c + Vector((0.12, 0.30, 0.10)) * (size / 0.075)    # look into the inside
        elif n.startswith('pin'):
            loc = c + Vector((0.05, -0.08, 0.06)) * 0.4
        else:
            loc = c + Vector((-0.18, -0.30, 0.14)) * (size / 0.075)
            if n == 'back_shell':
                loc = c + Vector((0.14, -0.30, 0.12)) * (size / 0.075)
        camera(sc, loc, c, lens=85)
        shoot(sc, f'part_{n}')


if __name__ == '__main__':
    what = os.environ.get('P0_WHAT', 'assembled,exploded,parts').split(',')
    if 'assembled' in what:
        assembled()
    if 'exploded' in what:
        exploded()
    if 'parts' in what:
        parts()
