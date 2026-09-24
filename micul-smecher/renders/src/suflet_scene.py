"""suflet_scene.py -- procedural Blender (Cycles) product renders of SUFLET / Micul Smecher.

Run headless (Blender 4.0+):
    blender -b --factory-startup --python suflet_scene.py -- --shot hero [--preview] [--samples N]
            [--w 1600 --h 1200] [--out DIR] [--frames] [--save-blend]

Shots: hero, lineup, night, bag, desk, social (1080x1920), turntable (540x540 frames).
Everything is built from code: the four silhouettes come from ../../cad/gen_shapes.py
(the concept outlines), the eye texture from eyes.py (port of firmware Face.cpp).

Pipeline per shot: Cycles CPU render -> noisy colour + albedo + normal EXRs in --tmp (compositor
File Output) + <shot>.json; then post.py denoises them (Intel Open Image Denoise), adds a soft bloom and
applies Blender's AgX view transform -> PNG. render_all.sh runs both steps.
"""
import argparse
import glob
import math
import os
import sys
import time

import bpy
import bmesh
import numpy as np
from mathutils import Vector, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))          # .../renders
CAD = os.path.abspath(os.path.join(HERE, '..', '..', 'cad'))
TEX = os.path.join(HERE, 'tex')
sys.dont_write_bytecode = True
sys.path.insert(0, CAD)
import gen_shapes as G  # noqa: E402  (pure math, import has no side effects)

MM = 0.001
# global look parameters (overridable with --set key=value)
TUNE = dict(frost_rough=0.55, frost_dens=45.0, glow_scale=2.0, glow_ring=1, module=1, module_grey=0.5)

# ------------------------------------------------------------------------------------------
# args
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--shot', default='hero')
ap.add_argument('--preview', action='store_true', help='half resolution, few samples')
ap.add_argument('--samples', type=int, default=0)
ap.add_argument('--w', type=int, default=0)
ap.add_argument('--h', type=int, default=0)
ap.add_argument('--out', default=ROOT)
ap.add_argument('--tmp', default='/tmp/claude-0/wf/render/tmp')
ap.add_argument('--frames', default='', help='turntable: "start:end" (default all)')
ap.add_argument('--save-blend', action='store_true')
ap.add_argument('--threads', type=int, default=0)
ap.add_argument('--set', action='append', default=[], help='TUNE overrides key=value')
ap.add_argument('--tag', default='')
ARGS = ap.parse_args(argv)
os.makedirs(ARGS.tmp, exist_ok=True)
for kv in ARGS.set:
    k, v = kv.split('=')
    TUNE[k] = type(TUNE[k])(float(v)) if k in TUNE else float(v)
os.makedirs(ARGS.out, exist_ok=True)


# ------------------------------------------------------------------------------------------
# colour helpers
def srgb(h, a=1.0):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (c[0], c[1], c[2], a)


def blackbody_rgb(k):
    # small table good enough for warm lights
    tab = {1900: (1.0, 0.43, 0.08), 2200: (1.0, 0.50, 0.16), 2700: (1.0, 0.62, 0.30),
           3200: (1.0, 0.72, 0.45), 4000: (1.0, 0.82, 0.64), 5000: (1.0, 0.90, 0.81),
           5600: (1.0, 0.94, 0.88), 6500: (1.0, 1.0, 1.0), 8000: (0.82, 0.88, 1.0)}
    return tab[min(tab, key=lambda t: abs(t - k))]


# ------------------------------------------------------------------------------------------
# shapes (outlines in mm, stone centre at the origin, +y up towards the cap)
SHAPE_CFG = {
    # k = mm per concept unit; squash = shorten the part above the screen (like squash_top
    # in micul_smecher.scad); smooth = extra relaxation passes; dy = move the screen up [mm]
    'coin': dict(k=0.2104, squash=1.0, smooth=0, dy=0.0),
    'gem': dict(k=0.2185, squash=1.0, smooth=0, dy=0.0),
    'drop': dict(k=0.282, squash=0.66, smooth=6, dy=0.0),
    'cloud': dict(k=0.272, squash=1.0, smooth=40, dy=1.2),
}
NRES = 360
H_HALF = 9.25          # half thickness (body ~18.5 mm)
R_REC = 19.45          # screen recess radius
FIL = 0.6              # lip fillet
R_STONE = 19.2         # black cover-glass "stone"
R_SCREEN = 18.0        # visible screen (466 px panel, ~36 mm)
_SHAPES = None


def shape_outline(name):
    global _SHAPES
    if _SHAPES is None:
        _SHAPES = G.build()
    c = SHAPE_CFG[name]
    P = list(_SHAPES[name]['P'])
    if c['smooth']:
        P = G.smooth(P, c['smooth'])
    k, sq = c['k'], c['squash']
    P = [(x * k, (y * sq if y > 0 else y) * k - c['dy']) for x, y in P]
    P = G.resample(P, NRES)
    P = np.array(P)
    ang = np.unwrap(np.arctan2(P[:, 1], P[:, 0]))
    if np.any(np.diff(ang) <= 0):
        print('WARNING: outline of %s is not star-shaped about the screen centre' % name)
    return P


# ------------------------------------------------------------------------------------------
# mesh helpers
def mesh_from_rings(name, rings, cap_start=None, cap_end=None, closed=True, smooth=True):
    """rings: list of (N,3) arrays (same N). cap_*: optional single 3D point (fan)."""
    N = len(rings[0])
    verts = []
    for r in rings:
        verts.extend(map(tuple, r))
    faces = []
    for i in range(len(rings) - 1):
        a, b = i * N, (i + 1) * N
        for j in range(N if closed else N - 1):
            j2 = (j + 1) % N
            faces.append((a + j, a + j2, b + j2, b + j))
    if cap_start is not None:
        c = len(verts)
        verts.append(tuple(cap_start))
        for j in range(N):
            faces.append((c, (j + 1) % N, j))
    if cap_end is not None:
        c = len(verts)
        verts.append(tuple(cap_end))
        base = (len(rings) - 1) * N
        for j in range(N):
            faces.append((c, base + j, base + (j + 1) % N))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def revolve(name, prof, seg=128, axis='z', smooth=True):
    """prof: list of (r, h). First/last points with r == 0 become fan caps."""
    t = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    rings, cs, ce = [], None, None
    pts = list(prof)
    if pts[0][0] == 0:
        cs = pts.pop(0)
    if pts[-1][0] == 0:
        ce = pts.pop(-1)

    def P(r, h):
        if axis == 'z':
            return np.stack([r * np.cos(t), r * np.sin(t), np.full(seg, h)], 1)
        return np.stack([r * np.cos(t), np.full(seg, h), r * np.sin(t)], 1)  # axis y

    for r, h in pts:
        rings.append(P(r, h) * MM)
    cap = lambda p: (np.array([0, 0, p[1]]) if axis == 'z' else np.array([0, p[1], 0])) * MM
    return mesh_from_rings(name, rings, cap(cs) if cs else None, cap(ce) if ce else None, smooth=smooth)


def curve_obj(name, pts, radius, closed=False, res=6):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = radius
    cu.bevel_resolution = res
    cu.use_fill_caps = True
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts):
        p.co = (q[0], q[1], q[2], 1)
    sp.use_cyclic_u = closed
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def rounded_box(name, sx, sy, sz, r, seg=6):
    """Axis-aligned box (full sizes, metres) with all edges rounded by r."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    m = ob.modifiers.new('bev', 'BEVEL')
    m.width = r
    m.segments = seg
    m.limit_method = 'NONE'
    for p in ob.data.polygons:
        p.use_smooth = True
    try:
        ob.data.use_auto_smooth = True
        ob.data.auto_smooth_angle = math.radians(40)
    except AttributeError:
        pass
    return ob


# ------------------------------------------------------------------------------------------
# materials
def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    return m, nt, nt.nodes['Principled BSDF'], nt.nodes['Material Output']


def set_in(node, key, val):
    if key in node.inputs:
        node.inputs[key].default_value = val
    else:
        print('  (no input %s on %s)' % (key, node.name))


def mat_frosted(name, tint, rough=0.3, dens=8.0, glow=None):
    m, nt, p, out = new_mat(name)
    c = srgb(tint)
    set_in(p, 'Base Color', c)
    set_in(p, 'Roughness', rough)
    set_in(p, 'IOR', 1.49)
    set_in(p, 'Transmission Weight', 1.0)
    # milky resin: a little scattering + tint absorption inside
    vs = nt.nodes.new('ShaderNodeVolumeScatter')
    vs.inputs['Color'].default_value = (min(1, c[0] * 0.85 + 0.15), min(1, c[1] * 0.85 + 0.15),
                                        min(1, c[2] * 0.85 + 0.15), 1)
    vs.inputs['Density'].default_value = dens
    vs.inputs['Anisotropy'].default_value = 0.35
    va = nt.nodes.new('ShaderNodeVolumeAbsorption')
    va.inputs['Color'].default_value = (c[0] ** 1.8, c[1] ** 1.8, c[2] ** 1.8, 1)
    va.inputs['Density'].default_value = dens * (0.25 if min(c[:3]) > 0.85 else 0.6)
    add = nt.nodes.new('ShaderNodeAddShader')
    nt.links.new(vs.outputs[0], add.inputs[0])
    nt.links.new(va.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs['Volume'])
    return m


def mat_metal(name, col=(0.86, 0.86, 0.87), rough=0.28, aniso=0.6, radial_axis='Y'):
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', (*col, 1))
    set_in(p, 'Metallic', 1.0)
    set_in(p, 'Roughness', rough)
    if aniso > 0:
        set_in(p, 'Anisotropic', aniso)
        tg = nt.nodes.new('ShaderNodeTangent')
        tg.direction_type = 'RADIAL'
        tg.axis = radial_axis
        nt.links.new(tg.outputs[0], p.inputs['Tangent'])
        # fine brushing lines
        tc = nt.nodes.new('ShaderNodeTexCoord')
        mp = nt.nodes.new('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (4000, 4000, 30)
        nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = 1.0
        nz.inputs['Detail'].default_value = 4
        bp = nt.nodes.new('ShaderNodeBump')
        bp.inputs['Strength'].default_value = 0.05
        nt.links.new(tc.outputs['Object'], mp.inputs[0])
        nt.links.new(mp.outputs[0], nz.inputs[0])
        nt.links.new(nz.outputs[0], bp.inputs['Height'])
        nt.links.new(bp.outputs[0], p.inputs['Normal'])
    return m


def mat_glass(name, rough=0.0, ior=1.5):
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', (1, 1, 1, 1))
    set_in(p, 'Roughness', rough)
    set_in(p, 'IOR', ior)
    set_in(p, 'Transmission Weight', 1.0)
    return m


def mat_screen(name, tex_path, strength):
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', (0.002, 0.002, 0.0025, 1))
    set_in(p, 'Roughness', 0.5)
    set_in(p, 'Specular IOR Level', 0.0)
    set_in(p, 'Coat Weight', 1.0)
    set_in(p, 'Coat Roughness', 0.02)
    set_in(p, 'Coat IOR', 1.5)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    s = 1.0 / (2 * R_SCREEN * MM)
    mp.inputs['Scale'].default_value = (s, s, 1)
    mp.inputs['Location'].default_value = (0.5, 0.5, 0)
    img = nt.nodes.new('ShaderNodeTexImage')
    img.image = bpy.data.images.load(tex_path, check_existing=True)
    img.extension = 'CLIP'
    img.interpolation = 'Cubic'
    nt.links.new(tc.outputs['Object'], mp.inputs[0])
    nt.links.new(mp.outputs[0], img.inputs[0])
    nt.links.new(img.outputs['Color'], p.inputs['Emission Color'])
    set_in(p, 'Emission Strength', strength)
    return m


def mat_diffuse(name, col, rough=0.8, spec=0.3):
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', col if len(col) == 4 else (*col, 1))
    set_in(p, 'Roughness', rough)
    set_in(p, 'Specular IOR Level', spec)
    return m


def mat_emit(name, col, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes['Principled BSDF'])
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = (*col, 1)
    e.inputs['Strength'].default_value = strength
    nt.links.new(e.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    return m


def mat_wood(name, c1, c2, rough=0.45, scale=6.0, stretch=(1, 14, 1)):
    m, nt, p, out = new_mat(name)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (scale * stretch[0], scale * stretch[1], scale * stretch[2])
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 3.0
    nz.inputs['Detail'].default_value = 8
    nz.inputs['Distortion'].default_value = 2.5
    wv = nt.nodes.new('ShaderNodeTexWave')
    wv.inputs['Scale'].default_value = 2.0
    wv.inputs['Distortion'].default_value = 6.0
    wv.inputs['Detail'].default_value = 3
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = c1
    ramp.color_ramp.elements[1].color = c2
    mix = nt.nodes.new('ShaderNodeMath')
    mix.operation = 'MULTIPLY_ADD'
    mix.inputs[1].default_value = 0.5
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.08
    nt.links.new(tc.outputs['Object'], mp.inputs[0])
    nt.links.new(mp.outputs[0], nz.inputs[0])
    nt.links.new(mp.outputs[0], wv.inputs[0])
    nt.links.new(wv.outputs['Fac'], mix.inputs[0])
    nt.links.new(nz.outputs['Fac'], mix.inputs[2])
    nt.links.new(mix.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], p.inputs['Base Color'])
    nt.links.new(mix.outputs[0], bp.inputs['Height'])
    nt.links.new(bp.outputs[0], p.inputs['Normal'])
    set_in(p, 'Roughness', rough)
    return m


def mat_leather(name, col, rough=0.5):
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', col)
    set_in(p, 'Roughness', rough)
    set_in(p, 'Sheen Weight', 0.1)
    set_in(p, 'Coat Weight', 0.25)
    set_in(p, 'Coat Roughness', 0.28)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    vo = nt.nodes.new('ShaderNodeTexVoronoi')
    vo.inputs['Scale'].default_value = 1500.0
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 60.0
    nz.inputs['Detail'].default_value = 6
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = tuple(x * 0.75 for x in col[:3]) + (1,)
    ramp.color_ramp.elements[1].color = col
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.18
    bp.inputs['Distance'].default_value = 0.0003
    nt.links.new(tc.outputs['Object'], vo.inputs['Vector'])
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    nt.links.new(vo.outputs['Distance'], bp.inputs['Height'])
    nt.links.new(nz.outputs['Fac'], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], p.inputs['Base Color'])
    nt.links.new(bp.outputs[0], p.inputs['Normal'])
    return m


def assign(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)


# ------------------------------------------------------------------------------------------
# the amulet
MATS = {}


def metal_mats():
    if 'alu' not in MATS:
        MATS['alu'] = mat_metal('brushed_aluminium', (0.88, 0.88, 0.89), 0.34, 0.75, 'Y')
        MATS['steel'] = mat_metal('steel_ring', (0.78, 0.78, 0.80), 0.12, 0.0)
        MATS['lens'] = mat_glass('lens_glass', 0.0, 1.5)
        MATS['black'] = mat_diffuse('black_gloss', (0.006, 0.006, 0.007), 0.12, 0.5)
        MATS['pcb'] = mat_diffuse('pcb', (0.03, 0.032, 0.035), 0.5, 0.4)
    return MATS


def build_body(name, P):
    O = np.asarray(P)                       # (N,2) mm
    r_o = np.hypot(O[:, 0], O[:, 1])
    d = O / r_o[:, None]
    N = len(O)
    r_lip = R_REC + FIL
    L = d * r_lip

    def ring(xy, z):
        return np.column_stack([xy, np.full(len(xy), z)]) * MM

    z_floor = H_HALF - 2.4
    rings = []
    # front: floor (hidden under the stone) -> recess wall -> fillet -> pebble rim
    for f in (0.5, 1.0):
        rings.append(ring(d * R_REC * f, z_floor))
    for t in np.linspace(math.pi, math.pi / 2, 7):
        rings.append(ring(d * (r_lip + FIL * math.cos(t)), H_HALF - FIL + FIL * math.sin(t)))
    phis = np.linspace(math.pi / 2, 0, 25)[1:]
    for ph in phis:
        rings.append(ring(O + (L - O) * (1 - math.cos(ph)), H_HALF * math.sin(ph)))
    # back
    for ph in phis[::-1][1:]:
        rings.append(ring(O + (L - O) * (1 - math.cos(ph)), -H_HALF * math.sin(ph)))
    for f in (1.0, 0.66, 0.33):
        rings.append(ring(d * r_lip * f, -H_HALF - 0.35 * (1 - f * f)))
    ob = mesh_from_rings(name + '_body', rings,
                         cap_start=np.array([0, 0, z_floor]) * MM,
                         cap_end=np.array([0, 0, -H_HALF - 0.35]) * MM)
    return ob


def build_amulet(tag, shape, tint, eyes, eye_strength=4.0, glow_w=0.02, glow_col=2700,
                 ring_tilt=-35.0, ring_extra=None, dens=None, rough=None, module=True):
    """Returns the parent empty. Local frame: x right, y up (cap), z towards the viewer; mm*MM."""
    mats = metal_mats()
    P = shape_outline(shape)
    par = bpy.data.objects.new('amulet_' + tag, None)
    bpy.context.scene.collection.objects.link(par)
    parts = []
    body = build_body(tag, P)
    assign(body, mat_frosted('frost_' + tag, tint, rough=rough or TUNE['frost_rough'],
                             dens=dens or TUNE['frost_dens']))
    parts.append(body)

    # stone: black cover glass with a slightly domed clear top (coat) over the emissive screen
    z_floor = H_HALF - 2.4
    r_s, z_le, z_lt = R_REC - 0.1, H_HALF + 0.15, H_HALF + 1.25
    h = z_lt - z_le
    Rs = (r_s ** 2 + h ** 2) / (2 * h)
    prof = [(0, z_lt)]
    for rr in np.linspace(0, r_s - 0.5, 28)[1:]:
        prof.append((rr, z_lt - (Rs - math.sqrt(Rs * Rs - rr * rr))))
    for t in np.linspace(math.pi / 2, 0, 6)[1:]:
        prof.append((r_s - 0.5 + 0.5 * math.cos(t), z_le - 0.5 + 0.5 * math.sin(t)))
    prof += [(r_s, z_floor + 0.3), (r_s - 0.3, z_floor + 0.02), (0, z_floor + 0.02)]
    stone = revolve(tag + '_stone', prof, seg=192)
    assign(stone, mat_screen('screen_' + tag, os.path.join(TEX, 'eyes_%s.png' % eyes), eye_strength))
    parts.append(stone)

    # cap at the tip: find where the outline is ~7 mm wide below the top
    top_y = P[:, 1].max()
    r_c = 4.4
    ys = np.linspace(top_y, top_y - 15, 300)
    yb = top_y - 2.0
    for y in ys:
        xs = P[np.abs(P[:, 1] - y) < 0.35][:, 0]
        if len(xs) and xs.max() - xs.min() > 2 * r_c * 0.95:
            yb = y
            break
    y0, y1 = yb - 1.2, top_y + 2.6
    cap_prof = [(0, y0), (r_c, y0), (r_c, y1 - 1.3)]
    for t in np.linspace(0, math.pi / 2, 8)[1:]:
        cap_prof.append((r_c - 1.3 + 1.3 * math.cos(t), y1 - 1.3 + 1.3 * math.sin(t)))
    cap_prof.append((0, y1))
    cap = revolve(tag + '_cap', cap_prof, seg=96, axis='y')
    assign(cap, mats['alu'])
    parts.append(cap)
    # a thin groove line: slim dark-ish ring near the base of the cap (reads as a separate part)
    bail_R, bail_r = 2.3, 0.75
    yb_c = y1 + bail_R - 0.35
    bpy.ops.mesh.primitive_torus_add(major_radius=bail_R * MM, minor_radius=bail_r * MM,
                                     major_segments=48, minor_segments=16,
                                     location=(0, yb_c * MM, 0))
    bail = bpy.context.active_object
    bail.name = tag + '_bail'
    bpy.ops.object.shade_smooth()
    assign(bail, mats['alu'])
    parts.append(bail)

    # split ring (2 coils, 12 mm OD), plane y-z, through the bail
    R, w = 5.4, 0.55
    contact = yb_c + bail_R - bail_r - w
    t = np.linspace(0, 4 * math.pi * 0.97, 260)
    pitch = 2 * w + 0.05
    pts = np.column_stack([(t / (2 * math.pi) - 1) * pitch, contact + R - R * np.cos(t), R * np.sin(t)]) * MM
    ringo = curve_obj(tag + '_splitring', pts, w * MM, res=4)
    assign(ringo, mats['steel'])
    ringo.location = (0, contact * MM, 0)
    ringo.data.transform(__import__('mathutils').Matrix.Translation((0, -contact * MM, 0)))
    ringo.rotation_euler = (math.radians(ring_tilt), 0, 0)
    parts.append(ringo)

    # the display module + PCB stack inside (seen as a soft dark disc through the frosting)
    r_o = np.hypot(P[:, 0], P[:, 1])
    z_mt = H_HALF - 2.5
    S = r_o - (R_REC + FIL)
    inset = S * (1 - math.cos(math.asin(min(1.0, z_mt / H_HALF))))
    r_m = float(min(21.7, (r_o - inset).min() - 1.3))
    if module and TUNE['module'] and r_m > 12:
        mod = revolve(tag + '_module', [(0, z_mt), (r_m - 0.6, z_mt), (r_m, z_mt - 0.6), (r_m, z_mt - 6.4),
                                        (r_m - 0.6, z_mt - 7.0), (0, z_mt - 7.0)], seg=96)
        g = TUNE['module_grey']
        assign(mod, mat_diffuse('module_' + tag, (g, g, g * 1.02, 1), 0.6, 0.3))
        parts.append(mod)
    # inner warm glow: a faint emissive ring around the module, blurred by the frosting
    if glow_w > 0 and TUNE['glow_ring']:
        rr = max(r_m, 14) + 1.3
        bpy.ops.mesh.primitive_torus_add(major_radius=rr * MM, minor_radius=1.1 * MM, major_segments=96,
                                         minor_segments=10, location=(0, 0, (z_mt - 3.5) * MM))
        gl = bpy.context.active_object
        gl.name = tag + '_glowring'
        gl.visible_shadow = False
        assign(gl, mat_emit('glow_' + tag, blackbody_rgb(glow_col), glow_w * 100 * TUNE['glow_scale']))
        parts.append(gl)
    for ob in parts:
        ob.parent = par
    par['top_y'] = float(top_y)
    par['bot_y'] = float(P[:, 1].min())
    par['ring_top'] = float(contact + 2 * R + w)
    par['contact'] = float(contact)
    return par


def place(par, loc, rot_deg=(90, 0, 0)):
    par.location = loc
    par.rotation_euler = tuple(math.radians(a) for a in rot_deg)


def world_point(par, local_mm):
    bpy.context.view_layer.update()
    return par.matrix_world @ Vector(tuple(v * MM for v in local_mm))


# ------------------------------------------------------------------------------------------
# scene helpers
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATS.clear()
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.015
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 16
    sc.cycles.diffuse_bounces = 4
    sc.cycles.glossy_bounces = 6
    sc.cycles.transmission_bounces = 14
    sc.cycles.volume_bounces = 2
    sc.cycles.transparent_max_bounces = 8
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.blur_glossy = 0.8
    sc.cycles.sample_clamp_indirect = 8.0
    sc.cycles.volume_step_rate = 1.0
    try:
        sc.cycles.use_light_tree = True
    except AttributeError:
        pass
    if ARGS.threads:
        sc.render.threads_mode = 'FIXED'
        sc.render.threads = ARGS.threads
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass
    sc.render.film_transparent = False
    vl = sc.view_layers[0]
    vl.cycles.denoising_store_passes = True
    w = bpy.data.worlds.new('world')
    sc.world = w
    w.use_nodes = True
    return sc


def world_color(col, strength):
    bg = bpy.context.scene.world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (*col, 1)
    bg.inputs['Strength'].default_value = strength


def area_light(name, loc, target, size, power, col=(1, 1, 1), shape='DISK', size_y=None, spread=180, glossy=True):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.shape = shape
    ld.size = size
    if size_y is not None:
        ld.size_y = size_y
    ld.energy = power
    ld.color = col
    ld.spread = math.radians(spread)
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    aim(ob, target)
    ob.visible_camera = False
    ob.visible_glossy = glossy
    return ob


def aim(ob, target):
    d = Vector(target) - Vector(ob.location)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def camera(loc, target, lens=100, fstop=5.6, focus=None, sensor=36, shift=(0, 0)):
    cd = bpy.data.cameras.new('cam')
    cd.lens = lens
    cd.sensor_width = sensor
    cd.shift_x, cd.shift_y = shift
    ob = bpy.data.objects.new('cam', cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    aim(ob, target)
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = fstop
    cd.dof.aperture_blades = 7
    cd.dof.aperture_rotation = math.radians(10)
    f = Vector(focus if focus is not None else target)
    cd.dof.focus_distance = (f - Vector(loc)).length
    bpy.context.scene.camera = ob
    return ob


def flag(cam, target, dist=0.12, size=(3.0, 2.2), col=(0.02, 0.02, 0.02)):
    """Black card behind the camera: keeps glossy screens black (a photographer's flag)."""
    c = Vector(cam.location)
    d = (c - Vector(target)).normalized()
    ob = plane('flag', size, c + d * dist, (0, 0, 0), mat_diffuse('flag', (*col, 1), 0.9, 0.0))
    aim(ob, Vector(target) + (Vector(target) - ob.location))  # plane normal (+Z) faces the target
    ob.rotation_euler = (d * -1).to_track_quat('-Z', 'Y').to_euler()
    ob.visible_camera = False
    ob.visible_shadow = False
    return ob


def glossy_card(loc, size, rot=(0, 0, 0), col=(0.01, 0.01, 0.01)):
    """Black card seen ONLY in glossy reflections (keeps the black screen black)."""
    ob = plane('card', size, loc, rot, mat_diffuse('card', (*col, 1), 0.9, 0.0))
    ob.visible_camera = False
    ob.visible_diffuse = False
    ob.visible_shadow = False
    ob.visible_transmission = False
    ob.visible_volume_scatter = False
    return ob


def screen_highlight(par, cam, up_deg=8.0, side_deg=-6.0, dist=0.30, size=(0.05, 0.5), tilt_deg=28.0,
                     strength=4.0):
    """A soft strip light seen ONLY in reflections: puts a thin crescent highlight on the domed screen."""
    bpy.context.view_layer.update()
    c = world_point(par, (0, 0, H_HALF + 1.25))
    n = (par.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
    v = (c - Vector(cam.location)).normalized()
    R = (v - 2 * v.dot(n) * n).normalized()
    side = R.cross(Vector((0, 0, 1))).normalized()
    up = side.cross(R).normalized()
    D = (R + up * math.tan(math.radians(up_deg)) + side * math.tan(math.radians(side_deg))).normalized()
    ob = plane('strip', size, c + D * dist, (0, 0, 0), mat_emit('strip', (1.0, 0.98, 0.95), strength))
    q = (-D).to_track_quat('-Z', 'Y')
    ob.rotation_euler = q.to_euler()
    ob.rotation_euler.rotate_axis('Z', math.radians(tilt_deg))
    ob.visible_camera = False
    ob.visible_diffuse = False
    ob.visible_shadow = False
    ob.visible_transmission = False
    ob.visible_volume_scatter = False
    return ob


def sweep(col='#EFE8DF', rough=0.85, wall_y=0.55, radius=0.45, width=4.0, height=2.0, front=-2.5):
    """Seamless paper: floor z=0 from y=front to the curve, then up a wall at y=wall_y."""
    prof = [(front, 0.0)]
    y0 = wall_y - radius
    for t in np.linspace(0, math.pi / 2, 24):
        prof.append((y0 + radius * math.sin(t), radius - radius * math.cos(t)))
    prof.append((wall_y, height))
    verts, faces = [], []
    for i, (y, z) in enumerate(prof):
        verts += [(-width / 2, y, z), (width / 2, y, z)]
        if i:
            a = 2 * (i - 1)
            faces.append((a, a + 1, a + 3, a + 2))
    me = bpy.data.meshes.new('sweep')
    me.from_pydata(verts, [], faces)
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new('sweep', me)
    bpy.context.scene.collection.objects.link(ob)
    assign(ob, mat_diffuse('paper', srgb(col), rough, 0.2))
    return ob


def plane(name, size, loc, rot=(0, 0, 0), mat=None):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = (size[0], size[1], 1)
    if mat:
        assign(ob, mat)
    return ob


# ------------------------------------------------------------------------------------------
# shots
def stand_z(par_bot_y):
    return -par_bot_y * MM


def shot_hero(social=False):
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#E4DBCF')
    a = build_amulet('hero', 'coin', '#F3F5F7', 'cream_look', eye_strength=2.8, glow_w=0.02)
    place(a, (0, 0, stand_z(a['bot_y']) + 0.0002), (90, 0, -12))
    tgt = world_point(a, (0, 5.0, 0))
    focus = world_point(a, (-4, 1, 10))
    if social:
        cam = camera((0.108, -0.275, 0.062), tgt, lens=85, fstop=11.0, focus=focus, shift=(0, 0.07))
    else:
        cam = camera((0.135, -0.305, 0.066), tgt, lens=105, fstop=11.0, focus=focus)
    protect_screens(cam, tgt, 1.6, -0.012)
    screen_highlight(a, cam, up_deg=11.0, side_deg=8.5, size=(0.022, 0.3), tilt_deg=-30.0, strength=7.0)
    area_light('key', (-0.40, -0.30, 0.45), tgt, 0.45, 2.0, blackbody_rgb(5600), spread=70)
    area_light('fill', (0.55, -0.25, 0.18), tgt, 0.8, 0.55, blackbody_rgb(5000))
    area_light('rim', (-0.22, 0.35, 0.22), tgt, 0.3, 2.5, blackbody_rgb(5000), spread=50)
    area_light('top', (0.0, 0.0, 0.6), tgt, 0.5, 0.65, blackbody_rgb(5600), spread=60)
    area_light('bg', (0.0, -0.1, 0.9), (0, 0.55, 0.25), 1.2, 9.0, blackbody_rgb(4500), spread=60)
    return sc


def protect_screens(cam, tgt, width=0.35, near=0.012):
    """Flag behind the camera + a glossy-only black card on the floor between object and camera."""
    flag(cam, tgt)
    c = Vector((cam.location.x, cam.location.y, 0))
    t = Vector((tgt.x, tgt.y, 0))
    d = (c - t)
    L = d.length
    u = d.normalized()
    ext = 0.8  # run the card well past the camera so low reflections stay black too
    mid = t + u * (near + (L - near + ext) / 2)
    glossy_card((mid.x, mid.y, 0.0004), (width, L - near + ext), (0, 0, math.atan2(-u.x, u.y)))


def studio(tgt, k=1.0, bg_target=(0, 0.55, 0.25)):
    area_light('key', (tgt.x - 0.40, tgt.y - 0.30, 0.45), tgt, 0.45, 2.0 * k, blackbody_rgb(5600), spread=70)
    area_light('fill', (tgt.x + 0.55, tgt.y - 0.25, 0.18), tgt, 0.8, 0.55 * k, blackbody_rgb(5000))
    area_light('rim', (tgt.x - 0.22, tgt.y + 0.35, 0.22), tgt, 0.3, 2.5 * k, blackbody_rgb(5000), spread=50)
    area_light('top', (tgt.x, tgt.y, 0.6), tgt, 0.5, 0.65 * k, blackbody_rgb(5600), spread=60)
    area_light('bg', (0.0, -0.1, 0.9), bg_target, 1.2, 9.0, blackbody_rgb(4500), spread=60)


def shot_lineup():
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#E4DBCF')
    specs = [('cloud', 'cloud', '#F3F5F7', 'cream', 0.0),
             ('coin', 'coin', '#DCD2F2', 'lilac', 0.012),
             ('gem', 'gem', '#CDE2F6', 'ice', -0.004),
             ('drop', 'drop', '#F7D8CB', 'peach', 0.010)]
    objs = []
    for tag, shape, tint, eyes, dy in specs:
        a = build_amulet(tag, shape, tint, eyes, eye_strength=2.8, glow_w=0.02)
        P = shape_outline(shape)
        objs.append((a, P[:, 0].min() * MM, P[:, 0].max() * MM, dy))
    gap = 0.011
    total = sum(w2 - w1 for _, w1, w2, _ in objs) + gap * (len(objs) - 1)
    x = -total / 2
    for a, w1, w2, dy in objs:
        place(a, (x - w1, dy, stand_z(a['bot_y']) + 0.0002), (90, 0, 0))
        x += (w2 - w1) + gap
    tgt = Vector((0, 0.004, 0.032))
    cam = camera((0.0, -0.66, 0.10), tgt, lens=85, fstop=11.0, focus=Vector((0, -0.006, 0.03)))
    protect_screens(cam, tgt, 0.75, 0.02)
    studio(tgt, 1.6)
    return sc


def shot_night():
    sc = reset()
    sc.view_settings.look = 'AgX - Base Contrast' if False else sc.view_settings.look
    world_color((0.02, 0.03, 0.06), 0.4)
    table = rounded_box('table', 0.9, 0.5, 0.03, 0.006)
    table.location = (0, 0.08, -0.015)
    assign(table, mat_wood('walnut', srgb('#3B2416'), srgb('#1C0F08'), 0.35, 5.0))
    wall = plane('wall', (3, 2), (0, 0.4, 0.5), (math.radians(90), 0, 0),
                 mat_diffuse('wall', srgb('#2A2E38'), 0.9, 0.1))
    a = build_amulet('night', 'coin', '#F3F5F7', 'amber', eye_strength=4.0, glow_w=0.022, glow_col=2200,
                     dens=90)
    place(a, (0, 0, stand_z(a['bot_y']) + 0.0002), (90, 0, -16))
    tgt = world_point(a, (0, 2.0, 0))
    focus = world_point(a, (-5, 2, 10))
    camera((0.15, -0.40, 0.075), tgt, lens=105, fstop=2.8, focus=focus)
    # spill of the glow on the table (the real light escapes the frosted body)
    spill = area_light('spill', world_point(a, (0, -8, 16)), world_point(a, (0, -40, 40)), 0.03, 0.35,
                       blackbody_rgb(2200), 'DISK', spread=150)
    spill2 = area_light('spill_back', world_point(a, (0, -5, -16)), world_point(a, (0, -40, -60)), 0.03,
                        0.25, blackbody_rgb(2200), 'DISK', spread=150)
    # cool moonlight from a window, camera-left
    area_light('moon', (-0.9, 0.05, 0.6), tgt, 0.6, 18, blackbody_rgb(8000), 'RECTANGLE', 0.3)
    area_light('moon_rim', (0.3, 0.6, 0.35), tgt, 0.3, 2.5, blackbody_rgb(8000))
    # a blurred lamp shade shape in the back (off) + a book
    book = rounded_box('book', 0.16, 0.22, 0.025, 0.002)
    book.location = (-0.16, 0.14, 0.0125)
    book.rotation_euler = (0, 0, math.radians(-12))
    assign(book, mat_diffuse('book', srgb('#6B2E2A'), 0.6, 0.3))
    book2 = rounded_box('book2', 0.15, 0.21, 0.02, 0.002)
    book2.location = (-0.15, 0.15, 0.035)
    book2.rotation_euler = (0, 0, math.radians(-5))
    assign(book2, mat_diffuse('book2', srgb('#7A6A55'), 0.7, 0.3))
    sc.view_settings.exposure = 0.0
    return sc


def shot_desk():
    sc = reset()
    world_color((0.93, 0.95, 1.0), 0.05)
    desk = rounded_box('desk', 1.6, 0.9, 0.03, 0.004)
    desk.location = (0, 0.2, -0.015)
    assign(desk, mat_wood('oak', srgb('#C8A27A'), srgb('#9E7650'), 0.5, 4.0))
    plane('wall', (4, 2), (0, 0.75, 0.8), (math.radians(90), 0, 0), mat_diffuse('wall', srgb('#E9E6E1'), 0.9, 0.1))
    # laptop (space grey aluminium): base with keyboard + trackpad, lid open at the back
    lap = rounded_box('laptop', 0.31, 0.215, 0.012, 0.004, 8)
    lap.location = (0.2, 0.10, 0.006)
    lap.rotation_euler = (0, 0, math.radians(-14))
    assign(lap, mat_metal('spacegrey', (0.36, 0.37, 0.39), 0.35, 0.0))
    kb = rounded_box('keys', 0.27, 0.10, 0.0012, 0.0005, 2)
    kb.parent = lap
    kb.location = (0, 0.035, 0.0062)
    assign(kb, mat_diffuse('keys', srgb('#1A1B1D'), 0.5, 0.3))
    pad = rounded_box('trackpad', 0.12, 0.075, 0.0006, 0.0005, 2)
    pad.parent = lap
    pad.location = (0, -0.06, 0.0060)
    assign(pad, mat_metal('pad', (0.33, 0.34, 0.36), 0.25, 0.0))
    lid = rounded_box('lid', 0.31, 0.006, 0.21, 0.003, 6)
    lid.parent = lap
    lid.location = (0, 0.107 + 0.02, 0.1)
    lid.rotation_euler = (math.radians(-18), 0, 0)
    assign(lid, mat_metal('spacegrey2', (0.36, 0.37, 0.39), 0.35, 0.0))
    scr = plane('laptop_screen', (0.29, 0.19), (0, -0.0035, 0.004), (math.radians(90), 0, 0),
                mat_emit('lcd', srgb('#2B3A55')[:3], 1.0))
    scr.parent = lid
    # mug for scale / context
    mug = revolve('mug', [(0, 0.004), (0.036, 0.004), (0.041, 0.0) if False else (0.040, 0.008), (0.041, 0.09),
                          (0.037, 0.093), (0.035, 0.012), (0, 0.012)], seg=96)
    for v in mug.data.vertices:
        v.co *= 1000  # revolve works in mm; this profile is in metres
    mug.location = (-0.19, 0.16, 0.0)
    assign(mug, mat_diffuse('ceramic', srgb('#F2EEE8'), 0.25, 0.5))
    # walnut stand holding the coin tilted back 15 deg
    st = rounded_box('stand', 0.046, 0.030, 0.012, 0.004, 6)
    st.location = (-0.02, 0.0, 0.006)
    st.rotation_euler = (0, 0, math.radians(20))
    assign(st, mat_wood('walnut', srgb('#5A3A24'), srgb('#2E1B10'), 0.4, 9.0))
    a = build_amulet('desk', 'coin', '#CDE2F6', 'cream_up', eye_strength=2.8, glow_w=0.02, ring_tilt=-60)
    place(a, (-0.02, 0.003, 0.012 + 0.0185), (75, 0, 20))
    tgt = world_point(a, (0, 0, 0))
    focus = world_point(a, (0, 3, 10))
    cam = camera((-0.15, -0.37, 0.085), Vector(tgt) + Vector((0.055, 0, 0.012)), lens=85, fstop=4.0, focus=focus)
    protect_screens(cam, tgt, 0.3, 0.02)
    screen_highlight(a, cam, up_deg=11.0, side_deg=8.5, size=(0.022, 0.3), tilt_deg=-30.0, strength=6.0)
    area_light('window', (-0.9, -0.2, 0.7), tgt, 1.2, 40, blackbody_rgb(6500), 'RECTANGLE', 0.8)
    area_light('fill', (0.5, -0.6, 0.3), tgt, 1.0, 4, blackbody_rgb(4000), glossy=False)
    area_light('rim', (0.1, 0.5, 0.4), tgt, 0.4, 5, blackbody_rgb(5000))
    return sc


def shot_bag():
    sc = reset()
    world_color((0.95, 0.93, 0.9), 0.05)
    sweep('#DCD0C0', wall_y=1.0)
    leather = mat_leather('leather', srgb('#4A2A15'), 0.4)
    # bag body: rounded tan leather block; front face at y = 0.08
    bag = rounded_box('bag', 0.36, 0.12, 0.26, 0.03, 10)
    bag.location = (0.03, 0.14, 0.13)
    assign(bag, leather)
    # handle: leather strap arc on top, attached near the front edge
    hy = 0.095
    pts = [(0.03 + 0.12 * math.cos(t), hy, 0.255 + 0.15 * math.sin(t)) for t in np.linspace(0, math.pi, 72)]
    han = curve_obj('handle', np.array(pts), 0.0075, res=6)
    assign(han, leather)
    # contrast stitching along the bag's front face, 9 mm inside the border
    cu = bpy.data.curves.new('stitches', 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = 0.00045
    cu.bevel_resolution = 2
    x0, x1, z0, z1, yf = 0.03 - 0.141, 0.03 + 0.141, 0.019, 0.241, 0.08 - 0.0003
    path = []
    for (xa, za), (xb, zb) in (((x0, z0), (x0, z1)), ((x0, z1), (x1, z1)), ((x1, z1), (x1, z0))):
        L = math.hypot(xb - xa, zb - za)
        n = int(L / 0.004)
        for i in range(n):
            f0, f1 = i / n, (i + 0.55) / n
            path.append(((xa + (xb - xa) * f0, za + (zb - za) * f0), (xa + (xb - xa) * f1, za + (zb - za) * f1)))
    for (a0, b0) in path:
        sp = cu.splines.new('POLY')
        sp.points.add(1)
        sp.points[0].co = (a0[0], yf, a0[1], 1)
        sp.points[1].co = (b0[0], yf, b0[1], 1)
    stob = bpy.data.objects.new('stitches', cu)
    bpy.context.scene.collection.objects.link(stob)
    assign(stob, mat_diffuse('thread', srgb('#D9C3A0'), 0.6, 0.3))
    # brass ferrules where the handle enters the bag
    brass = mat_metal('brass', (0.80, 0.62, 0.34), 0.3, 0.0)
    for fx in (0.03 - 0.12, 0.03 + 0.12):
        fer = revolve('ferrule', [(0, 0.0), (9.0, 0.0), (9.0, 5.0), (8.2, 6.5), (0, 6.5)], seg=64)
        fer.location = (fx, hy, 0.256)
        assign(fer, brass)
    # metal D-ring at the handle root, in front of the bag
    ax = 0.03 - 0.12
    dz = 0.262
    ring_pts = [(ax + 0.010 * math.cos(t), hy - 0.012, dz + 0.010 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 64, endpoint=False)]
    dring = curve_obj('dring', np.array(ring_pts), 0.0014, closed=True, res=4)
    dring.rotation_euler = (math.radians(-20), 0, 0)
    assign(dring, metal_mats()['steel'])
    a = build_amulet('bag', 'drop', '#BEE2DF', 'cream_look', eye_strength=2.8, glow_w=0.02, ring_tilt=0, dens=60.0)
    # short chain from the bottom of the D-ring
    Lk, Wk, wr = 7.5, 4.6, 0.75
    top = Vector((ax, hy - 0.016, dz - 0.010 + 0.001))
    n_links = 4
    link_len = (Lk - 2 * wr - 0.3) * MM
    for i in range(n_links):
        c = top - Vector((0, 0, (i + 0.5) * link_len))
        pts = []
        for t in np.linspace(0, 2 * math.pi, 64, endpoint=False):
            x = (Wk / 2) * math.cos(t)
            z = (Lk / 2 - Wk / 2) * np.sign(math.sin(t)) + (Wk / 2) * math.sin(t)
            if i % 2:
                pts.append((c.x, c.y + x * MM, c.z + z * MM))
            else:
                pts.append((c.x + x * MM, c.y, c.z + z * MM))
        ln = curve_obj('link%d' % i, np.array(pts), wr * MM, closed=True, res=4)
        assign(ln, metal_mats()['steel'])
    chain_bottom = top - Vector((0, 0, n_links * link_len + 0.0005))
    place(a, (0, 0, 0), (90, 0, -10))
    rt = world_point(a, (0, a['ring_top'], 0))
    a.location = Vector(a.location) + (chain_bottom - rt)
    tgt = world_point(a, (0, -2, 0))
    focus = world_point(a, (0, 0, 10))
    cam = camera((tgt.x + 0.12, tgt.y - 0.44, tgt.z + 0.05), tgt + Vector((0.016, 0, 0.030)), lens=85, fstop=5.6,
                 focus=focus)
    flag(cam, tgt)
    screen_highlight(a, cam, up_deg=11.0, side_deg=8.5, size=(0.022, 0.3), tilt_deg=-30.0, strength=6.0)
    area_light('key', (tgt.x - 0.40, tgt.y - 0.30, tgt.z + 0.40), tgt, 0.5, 4.0, blackbody_rgb(6500), spread=70)
    area_light('fill', (tgt.x + 0.5, tgt.y - 0.25, tgt.z + 0.1), tgt, 0.8, 1.2, blackbody_rgb(5600), glossy=False)
    area_light('rim', (tgt.x + 0.30, tgt.y + 0.05, tgt.z + 0.35), tgt, 0.4, 5.0, blackbody_rgb(5000), spread=60)
    area_light('rim2', (tgt.x - 0.30, tgt.y + 0.02, tgt.z + 0.30), tgt, 0.4, 3.0, blackbody_rgb(5000), spread=60)
    return sc


def shot_turntable():
    sc = shot_hero()
    a = bpy.data.objects['amulet_hero']
    fr = 150
    sc.frame_start, sc.frame_end = 1, fr
    for f in (1, fr + 1):
        sc.frame_set(f)
        a.rotation_euler = (math.radians(90), 0, math.radians(18 + (f - 1) * 360.0 / fr))
        a.keyframe_insert('rotation_euler', frame=f)
    for fc in a.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    return sc


SHOTS = {
    'hero': (shot_hero, 1600, 1200, 160),
    'social': (lambda: shot_hero(True), 1080, 1920, 160),
    'lineup': (shot_lineup, 1600, 1200, 160),
    'night': (shot_night, 1600, 1200, 192),
    'desk': (shot_desk, 1600, 1200, 160),
    'bag': (shot_bag, 1600, 1200, 160),
    'turntable': (shot_turntable, 540, 540, 48),
}


# ------------------------------------------------------------------------------------------
# render: noisy colour + albedo + normal EXRs; post.py denoises and tone-maps them
def setup_compositor(sc, base):
    sc.use_nodes = True
    nt = sc.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    rl = nt.nodes.new('CompositorNodeRLayers')
    comp = nt.nodes.new('CompositorNodeComposite')
    nt.links.new(rl.outputs['Image'], comp.inputs['Image'])
    fo = nt.nodes.new('CompositorNodeOutputFile')
    fo.base_path = os.path.dirname(base)
    fo.format.file_format = 'OPEN_EXR'
    fo.format.color_depth = '32'
    fo.format.exr_codec = 'ZIP'
    fo.file_slots.clear()
    stem = os.path.basename(base)
    for slot, outname in (('color', 'Image'), ('albedo', 'Denoising Albedo'), ('normal', 'Denoising Normal')):
        fo.file_slots.new(stem + '_' + slot + '_')
        nt.links.new(rl.outputs[outname], fo.inputs[-1])
    return fo


def main():
    import json
    fn, W, H, S = SHOTS[ARGS.shot]
    t0 = time.time()
    POST.clear()
    POST.update(look='AgX - Medium High Contrast', exposure=0.0, bloom=0.06)
    sc = fn()
    sc.render.resolution_x = ARGS.w or W
    sc.render.resolution_y = ARGS.h or H
    sc.render.resolution_percentage = 50 if ARGS.preview else 100
    sc.cycles.samples = ARGS.samples or (max(24, S // 4) if ARGS.preview else S)
    sc.render.use_persistent_data = True
    stem = ARGS.shot + ('_preview' if ARGS.preview else '') + (('_' + ARGS.tag) if ARGS.tag else '')
    base = os.path.join(ARGS.tmp, stem)
    for f in glob.glob(base + '_*_????.exr'):
        os.remove(f)
    setup_compositor(sc, base)
    sc.render.filepath = os.path.join(ARGS.tmp, 'composite_' + stem + '_')
    if ARGS.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ARGS.tmp, stem + '.blend'))
    w = int(sc.render.resolution_x * sc.render.resolution_percentage / 100)
    h = int(sc.render.resolution_y * sc.render.resolution_percentage / 100)
    if ARGS.shot == 'turntable':
        if ARGS.frames:
            sc.frame_start, sc.frame_end = [int(v) for v in ARGS.frames.split(':')]
        frames = list(range(sc.frame_start, sc.frame_end + 1))
        bpy.ops.render.render(animation=True)
    else:
        frames = [sc.frame_current]
        bpy.ops.render.render(write_still=False)
    meta = dict(POST, w=w, h=h, frames=frames, base=base, stem=stem, samples=sc.cycles.samples,
                seconds=round(time.time() - t0, 1))
    json.dump(meta, open(base + '.json', 'w'), indent=1)
    print('RENDERED', json.dumps(meta))


POST = {}
main()
