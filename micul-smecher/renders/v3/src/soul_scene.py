"""soul_scene.py -- procedural Blender (Cycles) concept renders of SOUL v3, "the amulet".

Evolved from the v1 scene (../../src/suflet_scene.py): same helpers, lights, materials and the
same render -> post.py (OIDN denoise + bloom + AgX) pipeline. v3 is a round coin amulet:
Ø58 mm, 17 mm at the centre, ~11 mm at the edge, a big domed black glass eye window Ø49
(active screen Ø44), a proud frosted "soul light" halo ring that glows in a state colour,
a titanium crown-bail with a split ring on top and an engraved steel caseback (Ø40).

Run headless (Blender 4.0+):
    blender -b --factory-startup --python soul_scene.py -- --shot hero [--preview] [--samples N]
            [--w 1600 --h 1200] [--tmp DIR] [--frames a:b] [--set key=value] [--save-blend]

Shots: hero, necklace, caseback, night, listening, lineup, scale, social (1080x1920),
turntable (540x540 frames). The v1 coin (for the scale shot) is still built by the v1 code
below (build_amulet, outline from ../../../cad/gen_shapes.py).
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
ROOT = os.path.abspath(os.path.join(HERE, '..'))          # .../renders/v3
CAD = os.path.abspath(os.path.join(HERE, '..', '..', '..', 'cad'))
TEX = os.path.join(HERE, 'tex')
sys.dont_write_bytecode = True
sys.path.insert(0, CAD)
import gen_shapes as G  # noqa: E402  (pure math, import has no side effects)

MM = 0.001
# global look parameters (overridable with --set key=value)
TUNE = dict(frost_rough=0.55, frost_dens=45.0, glow_scale=2.0, glow_ring=1, module=1, module_grey=0.5,
            halo_emit=1.0, halo_inner=1.0, body_dens=40.0, halo_dens=30.0, exposure=0.0)

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
ap.add_argument('--tmp', default='/tmp/soul_v3_render')
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


def mat_screen(name, tex_path, strength, r_screen=None):
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', (0.002, 0.002, 0.0025, 1))
    set_in(p, 'Roughness', 0.5)
    set_in(p, 'Specular IOR Level', 0.0)
    set_in(p, 'Coat Weight', 1.0)
    set_in(p, 'Coat Roughness', 0.02)
    set_in(p, 'Coat IOR', 1.5)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    s = 1.0 / (2 * (r_screen or R_SCREEN) * MM)
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


