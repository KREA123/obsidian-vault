"""render_p0.py -- Blender previews of SOUL-P0 size M, rendered from the exported CAD meshes, in the v6 look.

    blender -b -P render_p0.py -- [variant]     (plastic | alu; default alu)
    P0_WHAT=assembled,family,exploded,parts,inside   (default: all)

Inputs: ../stl/assembly/m_<variant>_*.stl (product frame, mm) + frame_m.json (lens centre / normal).
Outputs ../img/m_<variant>_*.png. The shells get the v6 anodised-aluminium CMF (bead-blast, Silver, Graphite,
Midnight, Ember, Champagne), the lens is black glass with the two cream eyes on the 70.64 mm screen, the
base plate + foot are the matte polymer in the body tone. These are renders of the P0 CAD, not photos.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
ASM = os.path.join(ROOT, 'stl', 'assembly')
IMG = os.path.join(ROOT, 'img')
os.makedirs(IMG, exist_ok=True)
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
VAR = argv[0] if argv else 'alu'
FR = json.load(open(os.path.join(HERE, 'frame_m.json')))
MM = 0.001
G = Vector(FR['G']) * MM
N_OUT = Vector(FR['N_OUT'])
UP = Vector(FR['UP'])
NS = Vector((0.0, 1.0, -FR['SEAM_B'])).normalized()

COLOURS = {   # v6 table: aluminium sRGB, polymer sRGB
    'silver': ('#CBCDCF', '#B4B6B8'), 'graphite': ('#55575B', '#3C3E41'), 'midnight': ('#26324C', '#1D2435'),
    'ember': ('#D2622C', '#A44A22'), 'champagne': ('#D8C3A2', '#BDAA8A'),
}


def srgb(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c) + (1.0,)


def reset(res=(1600, 1200), samples=int(os.environ.get('P0_SAMPLES', 64))):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass
    w = bpy.data.worlds.new('w')
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs[0].default_value = srgb('#EFE9E2')
    bg.inputs[1].default_value = 0.35
    return sc


def m_alu(name, hexcol, rough=0.40):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = srgb(hexcol)
    b.inputs['Metallic'].default_value = 1.0
    b.inputs['Roughness'].default_value = rough
    try:
        b.inputs['Anisotropic'].default_value = 0.15
        b.inputs['Coat Weight'].default_value = 0.25
        b.inputs['Coat Roughness'].default_value = 0.3
    except Exception:
        pass
    # bead-blast grain
    tc = nt.nodes.new('ShaderNodeTexCoord')
    vo = nt.nodes.new('ShaderNodeTexVoronoi')
    vo.inputs['Scale'].default_value = 9000.0
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.05
    bump.inputs['Distance'].default_value = 0.00002
    nt.links.new(tc.outputs['Object'], vo.inputs['Vector'])
    nt.links.new(vo.outputs['Distance'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m


def m_plain(name, rgba, rough=0.5, metal=0.0, emit=None, strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = rgba
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit:
        b.inputs['Emission Color' if 'Emission Color' in b.inputs else 'Emission'].default_value = emit
        b.inputs['Emission Strength'].default_value = strength
    return m


def load(name, mat):
    fn = os.path.join(ASM, f'm_{VAR}_{name}.stl')
    if not os.path.exists(fn):
        return None
    for o in bpy.context.selected_objects:
        o.select_set(False)
    try:
        bpy.ops.wm.stl_import(filepath=fn)
    except Exception:
        bpy.ops.import_mesh.stl(filepath=fn)
    ob = bpy.context.selected_objects[0]
    ob.name = name
    ob.data = ob.data.copy()
    ob.data.transform(Matrix.Scale(MM, 4))
    ob.data.update()
    for poly in ob.data.polygons:
        poly.use_smooth = True
    try:
        ob.data.use_auto_smooth = True
        ob.data.auto_smooth_angle = math.radians(30)
    except Exception:
        pass
    ob.data.materials.append(mat)
    ob.select_set(False)
    return ob


def eyes(offset=Vector((0, 0, 0)), night=False):
    """the two SOUL eyes on the screen: upright ovals whose top is cut by a slanted brow line (as in v6/v8)"""
    import bmesh
    col = srgb('#FFC96B') if night else srgb('#FFF0C8')
    m = m_plain('eye', col, 0.4, emit=col, strength=4.0)
    xax = Vector((1, 0, 0))
    base = G + offset + N_OUT * 0.00008
    rx, ry = 0.0079, 0.0125
    for sx in (-1, 1):
        pts = []
        for k in range(96):
            a = 2 * math.pi * k / 96
            x, y = rx * math.cos(a), ry * math.sin(a)
            ycut = 0.55 * ry + (-sx) * 0.42 * x          # brow: lower on the inner side
            pts.append((x, min(y, ycut)))
        c = base + xax * (sx * 0.0130) - UP * 0.0012
        me = bpy.data.meshes.new('eye')
        bm = bmesh.new()
        vs = [bm.verts.new(c + xax * x + UP * y) for x, y in pts]
        bm.faces.new(vs)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new('eye', me)
        bpy.context.scene.collection.objects.link(ob)
        me.materials.append(m)


def studio(sc, target):
    for loc, e, sz, col in [((-0.35, -0.45, 0.45), 14, 0.35, '#FFF4E8'), ((0.45, -0.15, 0.25), 5, 0.4, '#E8F0FF'),
                            ((0.05, 0.45, 0.4), 7, 0.4, '#FFFFFF'), ((0.0, -0.25, 0.6), 4, 0.6, '#FFFFFF')]:
        L = bpy.data.lights.new('L', 'AREA')
        L.energy, L.size = e, sz
        L.color = srgb(col)[:3]
        o = bpy.data.objects.new('L', L)
        sc.collection.objects.link(o)
        o.location = loc
        o.rotation_euler = (target - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        o.visible_camera = False
    # a long soft card above-left: the single diagonal glint on the black glass
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-0.10, -0.55, 0.30))
    card = bpy.context.active_object
    card.scale = (0.05, 0.6, 1)
    card.rotation_euler = (math.radians(60), 0, math.radians(35))
    card.data.materials.append(m_plain('card', (1, 1, 1, 1), 1.0, emit=(1, 1, 1, 1), strength=3.0))
    card.visible_camera = False
    card.select_set(False)
    bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0, -FR['FOOT_H'] * MM))
    fl = bpy.context.active_object
    fl.name = 'Plane'
    fl.data.materials.append(m_plain('floor', srgb('#EFE8E0'), 0.85))
    fl.select_set(False)


def camera(sc, loc, target, lens=85):
    c = bpy.data.cameras.new('C')
    c.lens = lens
    c.clip_start = 0.001
    c.dof.use_dof = False
    o = bpy.data.objects.new('C', c)
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = o


def shoot(sc, name):
    sc.render.filepath = os.path.join(IMG, f'm_{VAR}_{name}.png')
    bpy.ops.render.render(write_still=True)
    print('wrote', sc.render.filepath)


def body(colour='silver', offset=Vector((0, 0, 0)), with_eyes=True):
    al, poly = COLOURS[colour]
    if VAR == 'plastic':
        shell = m_plain('shell_' + colour, srgb(al), 0.35)
    else:
        shell = m_alu('alu_' + colour, al, 0.40 if colour == 'silver' else 0.46)
    obs = [load('front_shell', shell), load('back_shell', shell), load('base_plate', m_plain('poly_' + colour, srgb(poly), 0.7))]
    gl = load('in_lens', m_plain('glass', (0.002, 0.002, 0.0025, 1), 0.03))
    for o in obs + [gl]:
        if o is not None:
            o.location = offset
    if with_eyes:
        eyes(offset)
    return obs


def assembled():
    sc = reset()
    body('silver')
    tgt = Vector((0, 0, 0.060))
    studio(sc, tgt)
    D = 0.62
    shots = {
        'hero': ((-D * 0.55, -D * 0.80, 0.16), tgt, 85),
        'front': ((0, -D, 0.066), tgt, 85),
        'side': ((D, 0.0, 0.064), tgt, 85),
        'back': ((0.30, D * 0.9, 0.16), tgt, 85),
        'bottom': ((0.10, -0.16, -0.55), Vector((0, 0, 0.0)), 85),
    }
    for k, (loc, t, lens) in shots.items():
        bpy.data.objects['Plane'].hide_render = (k == 'bottom')
        camera(sc, loc, t, lens)
        shoot(sc, 'assembled_' + k)


def family():
    sc = reset(res=(2000, 1125))
    xs = [-0.26, -0.13, 0.0, 0.13, 0.26]
    for x, c in zip(xs, ['graphite', 'ember', 'silver', 'midnight', 'champagne']):
        body(c, Vector((x, 0.0 + abs(x) * 0.25, 0)))
    studio(sc, Vector((0, 0, 0.06)))
    camera(sc, (0.0, -0.95, 0.20), (0, 0.03, 0.055), 70)
    shoot(sc, 'family')


INSIDE = ['chassis', 'pin_boot', 'pin_rst', 'in_battery', 'in_speaker', 'in_amp', 'in_mic', 'in_usb_plug',
          'in_usb_socket', 'in_lcd', 'in_pcb', 'in_pcb_tab', 'in_components', 'in_bat_conn', 'in_bat_plug', 'in_switch',
          'in_key_boot', 'in_key_rst', 'in_usb_l', 'in_usb_r']
ICOL = {'chassis': '#E8742A', 'in_battery': '#8FB4D9', 'in_speaker': '#2A2C31', 'in_amp': '#1F5FA8', 'in_mic': '#3B8F4A',
        'in_usb_plug': '#9A9A9E', 'in_usb_socket': '#9A9A9E', 'in_pcb': '#1F5FA8', 'in_components': '#2E7D4F',
        'in_lcd': '#111114', 'in_pcb_tab': '#C8A040', 'pin_boot': '#3F7FD0', 'pin_rst': '#3F7FD0'}


def exploded():
    sc = reset(res=(1800, 1400))
    offs = {'front_shell': -48, 'in_lens': -30, 'board': -16, 'chassis': 8, 'inside': 16, 'back_shell': 58,
            'base_plate': 0}
    shell = m_alu('alu', COLOURS['silver'][0]) if VAR != 'plastic' else m_plain('pl', srgb('#EDEAE4'), 0.35)
    groups = {'front_shell': shell, 'back_shell': shell, 'base_plate': m_plain('poly', srgb(COLOURS['silver'][1]), 0.7),
              'in_lens': m_plain('glass', (0.004, 0.004, 0.005, 1), 0.04)}
    for n, m in groups.items():
        ob = load(n, m)
        if ob:
            ob.location = NS * offs[n] * MM + (Vector((0, 0, -0.030)) if n == 'base_plate' else Vector())
    for n in INSIDE:
        ob = load(n, m_plain('m_' + n, srgb(ICOL.get(n, '#202226')), 0.5))
        if ob is None:
            continue
        k = 'chassis' if n == 'chassis' else ('board' if n in ('in_lcd', 'in_pcb', 'in_pcb_tab', 'in_components',
                                                               'in_bat_conn', 'in_switch', 'in_key_boot', 'in_key_rst',
                                                               'in_usb_l', 'in_usb_r') else 'inside')
        ob.location = NS * offs[k] * MM
        if n.startswith('pin_'):
            ob.location += Vector((0.025, 0, 0))
    studio(sc, Vector((0, 0.005, 0.06)))
    bpy.data.objects['Plane'].location.z = -0.034
    camera(sc, (0.62, -0.42, 0.34), (0.0, 0.004, 0.052), 60)
    shoot(sc, 'exploded')


def inside():
    sc = reset(res=(1600, 1200))
    shell = m_alu('alu', COLOURS['silver'][0]) if VAR != 'plastic' else m_plain('pl', srgb('#EDEAE4'), 0.35)
    load('front_shell', shell)
    load('base_plate', m_plain('poly', srgb(COLOURS['silver'][1]), 0.7))
    for n in INSIDE:
        load(n, m_plain('m_' + n, srgb(ICOL.get(n, '#202226')), 0.5))
    studio(sc, Vector((0, 0, 0.06)))
    camera(sc, (0.26, 0.52, 0.24), (0, 0, 0.060), 70)
    shoot(sc, 'inside_open_back')


def parts():
    shell = m_alu('alu', COLOURS['silver'][0]) if VAR != 'plastic' else m_plain('pl', srgb('#EDEAE4'), 0.35)
    looks = {'front_shell': (Vector((0.25, 0.55, 0.30)), shell), 'back_shell': (Vector((0.30, -0.55, 0.30)), shell),
             'base_plate': (Vector((0.25, -0.35, -0.45)), m_plain('poly', srgb(COLOURS['silver'][1]), 0.7)),
             'chassis': (Vector((0.25, 0.45, 0.30)), m_plain('ch', srgb('#E8742A'), 0.5))}
    for n, (d, mat) in looks.items():
        sc = reset(res=(1200, 1200), samples=48)
        ob = load(n, mat)
        if ob is None:
            continue
        bbw = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        c = sum(bbw, Vector()) / 8
        studio(sc, c)
        bpy.data.objects['Plane'].hide_render = True
        camera(sc, c + d * 0.95, c, 70)
        shoot(sc, 'part_' + n)


if __name__ == '__main__':
    what = os.environ.get('P0_WHAT', 'assembled,family,exploded,inside,parts').split(',')
    for w in what:
        globals()[w]()
