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
TUNE = dict(frost_rough=0.55, frost_dens=45.0, glow_scale=2.0, glow_ring=1, module=1, module_grey=0.22,
            halo_emit=1.0, halo_inner=1.0, backlight=3.0, body_dens=40.0, halo_dens=12.0, exposure=0.0)

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
                     strength=4.0, z_mm=None):
    """A soft strip light seen ONLY in reflections: puts a thin crescent highlight on the domed screen."""
    bpy.context.view_layer.update()
    c = world_point(par, (0, 0, z_mm if z_mm is not None else H_HALF + 1.25))
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


# ==========================================================================================
# SOUL v3 -- the amulet
# ==========================================================================================
V3 = dict(R=28.0,            # outer radius (Ø56, production size from research/07)
          Z_TOP=8.25,        # glass apex (centre thickness 16.5 mm)
          Z_BOT=-8.25,       # caseback apex
          ZC=0.3,            # height of the rim "equator"
          R_GLASS=23.5,      # eye window radius (Ø47)
          Z_GLASS_EDGE=5.7,
          R_SCR=22.0,        # active screen (Ø44)
          R_CB=20.0,         # caseback disc (Ø40)
          N_SE=2.4)          # superellipse exponent of the river-stone rim
METAL = {'ti': dict(col=(0.66, 0.64, 0.61), rough=0.2, aniso=0.55),
         'gold': dict(col=(0.98, 0.76, 0.43), rough=0.17, aniso=0.45)}
GLOW = {'cream': (1.0, 0.70, 0.40), 'amber': (1.0, 0.45, 0.10), 'blue': (0.10, 0.35, 1.0),
        'ice': (0.62, 0.80, 1.0), 'mint': (0.55, 1.0, 0.78), 'peach': (1.0, 0.70, 0.55),
        'lilac': (0.78, 0.66, 1.0), 'gold': (1.0, 0.72, 0.30)}


def se_pt(cr, cz, a, b, t, n=None):
    n = n or V3['N_SE']
    c, s = math.cos(t), math.sin(t)
    e = 2.0 / n
    return (cr + a * math.copysign(abs(c) ** e, c), cz + b * math.copysign(abs(s) ** e, s))


def revolve_closed(name, prof, seg=128, axis='z'):
    """Closed cross-section (list of (r, h), not repeated) revolved -> torus-like solid."""
    t = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    N = len(prof)
    verts, faces = [], []
    for j in range(seg):
        for r, h in prof:
            if axis == 'z':
                verts.append((r * math.cos(t[j]) * MM, r * math.sin(t[j]) * MM, h * MM))
            else:
                verts.append((r * math.cos(t[j]) * MM, h * MM, r * math.sin(t[j]) * MM))
    for j in range(seg):
        j2 = (j + 1) % seg
        for i in range(N):
            i2 = (i + 1) % N
            faces.append((j * N + i, j * N + i2, j2 * N + i2, j2 * N + i))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def v3_profiles():
    """Cross-sections (r, z) in mm of the body, the halo and the seam height."""
    R, ZC = V3['R'], V3['ZC']
    fr = dict(cr=24.25, a=R - 24.25, b=6.0)          # front (halo) quarter: top z = 6.3 at r = 24.25
    bk = dict(cr=21.0, a=R - 21.0, b=7.45)           # back quarter: bottom z = -7.15 at r = 21.0
    t_split = math.radians(34)
    r_s, z_s = se_pt(fr['cr'], ZC, fr['a'], fr['b'], t_split)
    body = [(0, -6.75), (20.15, -6.75), (20.15, -7.0), (20.3, -7.12), (20.6, -7.15)]
    for t in np.linspace(-math.pi / 2, 0, 30):
        body.append(se_pt(bk['cr'], ZC, bk['a'], bk['b'], t))
    for t in np.linspace(0, t_split - math.radians(1.5), 10)[1:]:
        body.append(se_pt(fr['cr'], ZC, fr['a'], fr['b'], t))
    rr, zz = body[-1]
    rgw = V3['R_GLASS'] + 0.36
    body += [(rr - 0.18, zz + 0.05), (rr - 0.3, z_s - 0.05), (rgw, z_s - 0.05), (rgw, 2.6), (0, 2.6)]
    halo = []
    zb = z_s + 0.06
    ra, za = se_pt(fr['cr'], ZC, fr['a'], fr['b'], t_split + math.radians(1.5))
    halo.append((ra - 0.3, zb))
    halo.append((ra - 0.12, za - 0.02))
    for t in np.linspace(t_split + math.radians(1.5), math.pi / 2, 26):
        halo.append(se_pt(fr['cr'], ZC, fr['a'], fr['b'], t))
    top = halo[-1]
    rf = 0.32
    for a in np.linspace(math.pi / 2, math.pi, 7)[1:]:
        halo.append((top[0] + rf * math.cos(a), top[1] - rf + rf * math.sin(a)))
    halo.append((halo[-1][0], zb + 0.25))
    halo.append((halo[-1][0] + 0.2, zb))
    return body, halo, z_s


def mat_halo(name, tint, glow_rgb, strength, dens=None, white=0.55):
    """Frosted light-guide ring: like the body frosting but whiter, with an inner surface glow."""
    c = srgb(tint)
    w = tuple(min(1.0, white + (1 - white) * x) for x in c[:3])
    hx = '#%02X%02X%02X' % tuple(int(round((x ** (1 / 2.2)) * 255)) for x in w)
    m = mat_frosted(name, hx, rough=0.5, dens=dens or TUNE['halo_dens'])
    p = m.node_tree.nodes['Principled BSDF']
    set_in(p, 'Emission Color', (*glow_rgb, 1))
    set_in(p, 'Emission Strength', strength * TUNE['halo_emit'])
    return m


def mat_caseback(name):
    m, nt, p, out = new_mat(name)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    s = 1.0 / (2 * V3['R_CB'] * MM)
    mp.inputs['Scale'].default_value = (-s, s, 1)       # seen from the back -> mirror x so the text reads
    mp.inputs['Location'].default_value = (0.5, 0.5, 0)
    img = nt.nodes.new('ShaderNodeTexImage')
    img.image = bpy.data.images.load(os.path.join(TEX, 'caseback_engrave.png'), check_existing=True)
    img.image.colorspace_settings.name = 'Non-Color'
    img.extension = 'CLIP'
    img.interpolation = 'Cubic'
    nt.links.new(tc.outputs['Object'], mp.inputs[0])
    nt.links.new(mp.outputs[0], img.inputs[0])
    # radius mask: polished mirror band r > 15.6 mm, concentric brushed centre
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], sep.inputs[0])
    comb = nt.nodes.new('ShaderNodeCombineXYZ')
    nt.links.new(sep.outputs[0], comb.inputs[0])
    nt.links.new(sep.outputs[1], comb.inputs[1])
    ln = nt.nodes.new('ShaderNodeVectorMath')
    ln.operation = 'LENGTH'
    nt.links.new(comb.outputs[0], ln.inputs[0])
    band = nt.nodes.new('ShaderNodeMath')
    band.operation = 'GREATER_THAN'
    band.inputs[1].default_value = 15.6 * MM
    nt.links.new(ln.outputs['Value'], band.inputs[0])
    # roughness = mix(brushed 0.24, polished 0.05, band), then engraved 0.55
    r1 = nt.nodes.new('ShaderNodeMapRange')
    r1.inputs['To Min'].default_value = 0.24
    r1.inputs['To Max'].default_value = 0.05
    nt.links.new(band.outputs[0], r1.inputs['Value'])
    r2 = nt.nodes.new('ShaderNodeMix')
    r2.data_type = 'FLOAT'
    nt.links.new(img.outputs['Color'], r2.inputs['Factor'])
    nt.links.new(r1.outputs['Result'], r2.inputs['A'])
    r2.inputs['B'].default_value = 0.62
    nt.links.new(r2.outputs['Result'], p.inputs['Roughness'])
    cm = nt.nodes.new('ShaderNodeMix')
    cm.data_type = 'RGBA'
    nt.links.new(img.outputs['Color'], cm.inputs['Factor'])
    cm.inputs['A'].default_value = (0.93, 0.92, 0.90, 1)
    cm.inputs['B'].default_value = (0.62, 0.61, 0.59, 1)
    nt.links.new(cm.outputs['Result'], p.inputs['Base Color'])
    set_in(p, 'Metallic', 1.0)
    an = nt.nodes.new('ShaderNodeMath')
    an.operation = 'MULTIPLY_ADD'
    an.inputs[1].default_value = -0.6
    an.inputs[2].default_value = 0.6
    nt.links.new(band.outputs[0], an.inputs[0])
    nt.links.new(an.outputs[0], p.inputs['Anisotropic'])
    tg = nt.nodes.new('ShaderNodeTangent')
    tg.direction_type = 'RADIAL'
    tg.axis = 'Z'
    nt.links.new(tg.outputs[0], p.inputs['Tangent'])
    bp = nt.nodes.new('ShaderNodeBump')
    bp.invert = True
    bp.inputs['Strength'].default_value = 0.6
    bp.inputs['Distance'].default_value = 0.00006
    nt.links.new(img.outputs['Color'], bp.inputs['Height'])
    # fine concentric brushing lines in the centre
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 6000.0
    nz.inputs['Detail'].default_value = 2
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    bp2 = nt.nodes.new('ShaderNodeBump')
    bp2.inputs['Strength'].default_value = 0.02
    nt.links.new(nz.outputs['Fac'], bp2.inputs['Height'])
    nt.links.new(bp2.outputs[0], bp.inputs['Normal'])
    nt.links.new(bp.outputs[0], p.inputs['Normal'])
    return m


def build_crown(tag, mat):
    """Pocket-watch crown fused with a sculpted pendant bow. Axis = local +y, sits on the rim."""
    prof = [(2.5, 27.4, 0), (2.5, 29.45, 0), (2.72, 29.72, 0), (2.98, 29.92, 0), (3.02, 30.22, 0),
            (2.78, 30.36, 0), (2.8, 30.52, 0), (3.3, 30.62, 0.3), (3.5, 30.86, 1), (3.52, 31.7, 1),
            (3.5, 32.6, 1), (3.34, 32.92, 0.4), (3.0, 33.16, 0), (2.3, 33.38, 0), (1.7, 33.62, 0),
            (1.5, 33.95, 0), (1.45, 34.5, 0)]
    dy = V3['R'] - 29.0
    prof = [(r, y + dy, amp) for r, y, amp in prof]
    seg, nfl = 192, 22
    t = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    fl = 0.5 - 0.5 * np.cos(nfl * t)
    fl = fl ** 0.6
    rings = []
    for r, y, amp in prof:
        rr = r * (1.0 - 0.055 * amp * fl)
        rings.append(np.stack([rr * np.cos(t), np.full(seg, y), rr * np.sin(t)], 1) * MM)
    cr = mesh_from_rings(tag + '_crown', rings, cap_start=np.array([0, 27.4 + dy, 0]) * MM,
                         cap_end=np.array([0, 34.5 + dy, 0]) * MM)
    assign(cr, mat)
    # the bow: loop in the face plane, thicker where it grows out of the crown
    Rl = 2.85
    yc = 34.3 + dy + Rl
    cu = bpy.data.curves.new(tag + '_bow', 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = 1.0 * MM
    cu.bevel_resolution = 6
    sp = cu.splines.new('POLY')
    th = np.linspace(-math.pi / 2, 1.5 * math.pi, 96, endpoint=False)
    sp.points.add(len(th) - 1)
    for p, a in zip(sp.points, th):
        p.co = (Rl * math.cos(a) * 1.0 * MM, (yc + Rl * math.sin(a) * 1.08) * MM, 0, 1)
        k = 0.5 + 0.5 * math.sin(a)                      # 0 at the bottom, 1 at the top
        p.radius = 1.18 - 0.38 * k ** 0.7
        p.tilt = 0
    sp.use_cyclic_u = True
    sp.use_smooth = True
    bow = bpy.data.objects.new(tag + '_bow', cu)
    bpy.context.scene.collection.objects.link(bow)
    assign(bow, mat)
    inner_top = yc + Rl * 1.08 - 0.80
    return [cr, bow], inner_top


def build_soul(tag, tint='#F3F1EC', eyes='cream_look', eye_strength=2.8, glow='cream', glow_strength=0.6,
               inner=1.0, metal='ti', ring=True, ring_tilt=-35.0, ring_R=5.2, dens=None, cord=False, halo_white=0.55):
    """SOUL v3. Local frame (mm*MM): x right, y up (crown), z towards the viewer. Returns the parent empty."""
    mats = metal_mats()
    mk = 'metal_' + metal
    if mk not in MATS:
        MATS[mk] = mat_metal(mk, METAL[metal]['col'], METAL[metal]['rough'], METAL[metal]['aniso'], 'Y')
        MATS[mk + '_pol'] = mat_metal(mk + '_pol', METAL[metal]['col'], 0.07, 0.0)
    if 'caseback' not in MATS:
        MATS['caseback'] = mat_caseback('caseback')
        MATS['gold_contact'] = mat_metal('gold_contact', METAL['gold']['col'], 0.12, 0.0)
    glow_rgb = GLOW[glow] if isinstance(glow, str) else glow
    par = bpy.data.objects.new('soul_' + tag, None)
    bpy.context.scene.collection.objects.link(par)
    parts = []
    body_p, halo_p, z_s = v3_profiles()
    body = revolve(tag + '_body', body_p, seg=192)
    assign(body, mat_frosted('frost_' + tag, tint, rough=TUNE['frost_rough'], dens=dens or TUNE['body_dens']))
    parts.append(body)
    halo = revolve_closed(tag + '_halo', halo_p, seg=192)
    assign(halo, mat_halo('halo_' + tag, tint, glow_rgb, glow_strength, white=halo_white))
    parts.append(halo)
    # hidden light source inside the halo ring (the "soul light")
    if inner > 0 and TUNE['halo_inner'] > 0:
        bpy.ops.mesh.primitive_torus_add(major_radius=(V3['R'] - 1.8) * MM, minor_radius=0.35 * MM, major_segments=128,
                                         minor_segments=8, location=(0, 0, (z_s + 1.05) * MM))
        gl = bpy.context.active_object
        gl.name = tag + '_halo_led'
        gl.visible_shadow = False
        assign(gl, mat_emit('led_' + tag, glow_rgb, 60.0 * inner * TUNE['halo_inner']))
        parts.append(gl)
    # thin polished bezel between the eye window and the halo
    rg, zt = V3['R_GLASS'], V3['Z_GLASS_EDGE'] + 0.22
    bz = revolve_closed(tag + '_bezel', [(rg + 0.03, z_s - 0.3), (rg + 0.33, z_s - 0.3), (rg + 0.33, zt - 0.1),
                                         (rg + 0.25, zt), (rg + 0.1, zt), (rg + 0.03, zt - 0.1)], seg=192)
    assign(bz, MATS[mk + '_pol'])
    parts.append(bz)
    # eye window: big domed black glass over the round screen
    r_s, z_le, z_lt = V3['R_GLASS'] - 0.02, V3['Z_GLASS_EDGE'], V3['Z_TOP']
    h = z_lt - z_le
    Rs = (r_s ** 2 + h ** 2) / (2 * h)
    prof = [(0, z_lt)]
    for rr in np.linspace(0, r_s - 0.4, 40)[1:]:
        prof.append((rr, z_lt - (Rs - math.sqrt(Rs * Rs - rr * rr))))
    ze = prof[-1][1]
    for t in np.linspace(math.pi / 2, 0, 6)[1:]:
        prof.append((r_s - 0.4 + 0.4 * math.cos(t), ze - 0.4 + 0.4 * math.sin(t)))
    prof += [(r_s, 2.9), (r_s - 0.3, 2.62), (0, 2.62)]
    stone = revolve(tag + '_glass', prof, seg=192)
    assign(stone, mat_screen('screen_' + tag, os.path.join(TEX, 'eyes_%s.png' % eyes), eye_strength,
                             r_screen=V3['R_SCR']))
    parts.append(stone)
    # engraved steel caseback + two gold charge contacts
    Rcb = V3['R_CB']
    zb0, sag = V3['Z_BOT'], 1.0
    Rd = ((Rcb - 0.4) ** 2 + sag ** 2) / (2 * sag)
    cprof = [(0, zb0)]
    for rr in np.linspace(0, Rcb - 0.4, 40)[1:]:
        cprof.append((rr, zb0 + (Rd - math.sqrt(Rd * Rd - rr * rr))))
    z_e = cprof[-1][1]
    for t in np.linspace(-math.pi / 2, 0, 6)[1:]:
        cprof.append((Rcb - 0.4 + 0.4 * math.cos(t), z_e + 0.4 + 0.4 * math.sin(t)))
    cprof += [(Rcb, -6.9), (0, -6.9)]
    cb = revolve(tag + '_caseback', cprof, seg=256)
    assign(cb, MATS['caseback'])
    parts.append(cb)
    for sx in (-1, 1):
        x, y = sx * 4.6, -1.5
        rr = math.hypot(x, y)
        zc = zb0 + (Rd - math.sqrt(Rd * Rd - rr * rr))
        ct = revolve(tag + '_contact', [(0, zc - 0.12), (1.05, zc - 0.10), (1.3, zc - 0.02), (1.3, zc + 0.4),
                                        (0, zc + 0.4)], seg=48)
        ct.location = (x * MM, y * MM, 0)
        assign(ct, MATS['gold_contact'])
        parts.append(ct)
    # bayonet coin slot at 6 o'clock on the caseback edge + speaker slots hidden beside the crown
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -20.0 * MM, -7.62 * MM))
    cut = bpy.context.active_object
    cut.name = tag + '_coinslot_cutter'
    cut.scale = (5.2 * MM, 2.6 * MM, 1.25 * MM)
    cut.hide_render = True
    cut.parent = cb
    bo = cb.modifiers.new('coinslot', 'BOOLEAN')
    bo.object = cut
    bo.operation = 'DIFFERENCE'
    for sx in (-1, 1):
        a0 = math.radians(90 + sx * 11.0)
        sp_ = rounded_box(tag + '_spk', 4.2 * MM, 0.9 * MM, 0.8 * MM, 0.3 * MM, 3)
        sp_.location = ((V3['R'] - 0.43) * math.cos(a0) * MM, (V3['R'] - 0.43) * math.sin(a0) * MM, V3['ZC'] * MM)
        sp_.rotation_euler = (0, 0, a0 - math.pi / 2)
        assign(sp_, mat_diffuse('slot_dark', (0.012, 0.012, 0.013, 1), 0.7, 0.2))
        parts.append(sp_)
    # the display module / electronics inside (a soft dark disc through the frosting)
    if TUNE['module']:
        g = TUNE['module_grey']
        mod = revolve(tag + '_module', [(0, 2.4), (23.0, 2.4), (23.4, 2.0), (23.4, -3.4), (23.0, -3.8), (0, -3.8)],
                      seg=96)
        assign(mod, mat_diffuse('module_' + tag, (g, g, g * 1.02, 1), 0.6, 0.3))
        parts.append(mod)
    # crown + bow + split ring
    crown_parts, inner_top = build_crown(tag, MATS[mk])
    for ob in crown_parts:
        ob.location = (0, 0, V3['ZC'] * MM)
        parts.append(ob)
    w = 0.5
    contact = inner_top - w
    if ring:
        R = ring_R
        t = np.linspace(0, 4 * math.pi * 0.97, 280)
        pitch = 2 * w + 0.05
        pts = np.column_stack([(t / (2 * math.pi) - 1) * pitch, R - R * np.cos(t), R * np.sin(t)]) * MM
        ringo = curve_obj(tag + '_splitring', pts, w * MM, res=4)
        assign(ringo, MATS[mk + '_pol'] if metal == 'gold' else mats['steel'])
        ringo.location = (0, contact * MM, V3['ZC'] * MM)
        ringo.rotation_euler = (math.radians(ring_tilt), 0, 0)
        parts.append(ringo)
        par['ring_top'] = float(contact + 2 * R)
    for ob in parts:
        ob.parent = par
    par['top_y'] = float(inner_top + 0.8)
    par['bot_y'] = -V3['R']
    par['contact'] = float(contact)
    par['ring_R'] = float(ring_R)
    return par


def ring_top_world(par):
    """World position of the top of the split ring (where a cord would run)."""
    bpy.context.view_layer.update()
    ring = [c for c in par.children if c.name.endswith('_splitring')][0]
    return ring.matrix_world @ Vector((0, 2 * par['ring_R'] * MM, 0))


# ------------------------------------------------------------------------------------------
# props
def mat_linen(name, col='#D9CFBF', scale=1.0):
    m, nt, p, out = new_mat(name)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs['Object'], mp.inputs[0])
    waves = []
    for axis in ('X', 'Z'):
        wv = nt.nodes.new('ShaderNodeTexWave')
        wv.bands_direction = axis
        wv.inputs['Scale'].default_value = 900.0
        wv.inputs['Distortion'].default_value = 1.2
        wv.inputs['Detail'].default_value = 1.5
        wv.inputs['Detail Scale'].default_value = 3.0
        nt.links.new(mp.outputs[0], wv.inputs['Vector'])
        waves.append(wv)
    mx = nt.nodes.new('ShaderNodeMath')
    mx.operation = 'MULTIPLY'
    nt.links.new(waves[0].outputs['Fac'], mx.inputs[0])
    nt.links.new(waves[1].outputs['Fac'], mx.inputs[1])
    nz = nt.nodes.new('ShaderNodeTexNoise')      # slubs / uneven yarn
    nz.inputs['Scale'].default_value = 90.0
    nz.inputs['Detail'].default_value = 6
    nt.links.new(mp.outputs[0], nz.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    c = srgb(col)
    ramp.color_ramp.elements[0].color = (c[0] * 0.82, c[1] * 0.82, c[2] * 0.82, 1)
    ramp.color_ramp.elements[1].color = (min(1, c[0] * 1.06), min(1, c[1] * 1.06), min(1, c[2] * 1.06), 1)
    ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[1].position = 0.7
    nt.links.new(nz.outputs['Fac'], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], p.inputs['Base Color'])
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.6
    bp.inputs['Distance'].default_value = 0.0003
    nt.links.new(mx.outputs[0], bp.inputs['Height'])
    nt.links.new(bp.outputs[0], p.inputs['Normal'])
    set_in(p, 'Roughness', 0.9)
    set_in(p, 'Sheen Weight', 0.5)
    set_in(p, 'Sheen Roughness', 0.4)
    set_in(p, 'Specular IOR Level', 0.2)
    return m


def cord_obj(name, pts, radius=0.7, col='#D8CBB6', rough=0.45):
    """Waxed cotton cord through the given points (metres), smoothed with a NURBS spline."""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = radius * MM
    cu.bevel_resolution = 5
    cu.use_fill_caps = True
    cu.resolution_u = 12
    sp = cu.splines.new('NURBS')
    sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts):
        p.co = (q[0], q[1], q[2], 1)
    sp.order_u = 4
    sp.use_endpoint_u = True
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    m, nt, p, out = new_mat(name + '_mat')
    set_in(p, 'Base Color', srgb(col))
    set_in(p, 'Roughness', rough)
    set_in(p, 'Coat Weight', 0.12)
    set_in(p, 'Coat Roughness', 0.45)
    # twisted strands
    tc = nt.nodes.new('ShaderNodeTexCoord')
    wv = nt.nodes.new('ShaderNodeTexWave')
    wv.wave_type = 'BANDS'
    wv.bands_direction = 'DIAGONAL'
    wv.inputs['Scale'].default_value = 3.0
    nt.links.new(tc.outputs['Generated'], wv.inputs['Vector'])
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.25
    nt.links.new(wv.outputs['Fac'], bp.inputs['Height'])
    nt.links.new(bp.outputs[0], p.inputs['Normal'])
    assign(ob, m)
    return ob


def extrude_outline(name, outline_mm, thick_mm, bevel_mm=0.35):
    bm = bmesh.new()
    vs = [bm.verts.new((x * MM, y * MM, 0)) for x, y in outline_mm]
    f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    for v in [e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)]:
        v.co.z += thick_mm * MM
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    m = ob.modifiers.new('bev', 'BEVEL')
    m.width = bevel_mm * MM
    m.segments = 3
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(30)
    for p in me.polygons:
        p.use_smooth = False
    return ob


def build_key(name):
    """A generic flat house key (no brand), ~58 mm long, lying in the xy plane, 2 mm thick."""
    out = []
    # bow: rounded head with a hole (as a ring polygon traced both ways)
    cxb, R0, Rh = -13.0, 12.0, 2.6
    n = 72
    ang = np.linspace(math.radians(25), math.radians(335), n)
    bow = [(cxb + R0 * math.cos(a) * 1.0, R0 * 0.92 * math.sin(a)) for a in ang]
    # neck to blade
    blade_top, blade_bot = 3.9, -3.9
    x0, x1 = 0.5, 31.0
    top = [(x0, blade_top + 1.4), (x0 + 1.2, blade_top)]
    notches = [(6.0, 1.3), (10.2, 2.0), (14.4, 0.9), (18.6, 1.8), (22.8, 1.1)]
    for xc, d in notches:
        top += [(xc - 1.6, blade_top), (xc, blade_top - d), (xc + 1.6, blade_top)]
    top += [(x1 - 2.0, blade_top), (x1, 1.0), (x1 + 0.6, -0.8), (x1 - 0.6, blade_bot)]
    bot = [(x0 + 1.2, blade_bot), (x0, blade_bot - 1.4)]
    poly = bow[::-1][::-1]  # ccw from lower-right of bow ... keep order: bow ccw from +25deg to 335deg
    outline = [(bow[-1][0], bow[-1][1])] + bot[::-1][::-1]
    outline = list(bow[::-1])           # from 335deg down to 25deg (clockwise) -> reverse below
    outline = list(reversed(outline))   # 25 -> 335 (ccw) : top of bow round to bottom
    # ccw polygon: bow (25 -> 335 deg), bottom neck, blade bottom, tip, blade top (reversed), top neck
    shape = outline + [(x0 - 1.0, blade_bot - 2.4), (x0, blade_bot - 1.4), (x0 + 1.2, blade_bot),
                       (x1 - 0.6, blade_bot), (x1 + 0.6, -0.8), (x1, 1.0), (x1 - 2.0, blade_top)]
    for xc, d in reversed(notches):
        shape += [(xc + 1.6, blade_top), (xc, blade_top - d), (xc - 1.6, blade_top)]
    shape += [(x0 + 1.2, blade_top), (x0, blade_top + 1.4), (x0 - 1.0, blade_top + 2.4)]
    key = extrude_outline(name, shape, 2.0, 0.3)
    # hole
    bpy.ops.mesh.primitive_cylinder_add(radius=Rh * MM, depth=6 * MM, vertices=48, location=((cxb - 5.5) * MM, 0, 0))
    cyl = bpy.context.active_object
    cyl.hide_render = True
    b = key.modifiers.new('hole', 'BOOLEAN')
    b.object = cyl
    b.operation = 'DIFFERENCE'
    key.modifiers.move(1, 0)
    # a milled groove along the blade
    gr = rounded_box(name + '_groove', 24 * MM, 1.1 * MM, 0.5 * MM, 0.2 * MM, 2)
    gr.location = (15.5 * MM, -0.8 * MM, 2.05 * MM)
    gr.parent = key
    m = mat_metal('brass', (0.72, 0.53, 0.29), 0.24, 0.0)
    assign(key, m)
    assign(gr, mat_metal('brass_dark', (0.50, 0.38, 0.22), 0.45, 0.0))
    return key


DF_K = [  # z [m], half-width, half-depth  (a linen dress form, no head)
    (-0.10, 0.130, 0.100), (0.05, 0.140, 0.100), (0.16, 0.165, 0.115), (0.24, 0.170, 0.106),
    (0.30, 0.180, 0.097), (0.335, 0.178, 0.088), (0.36, 0.150, 0.078), (0.38, 0.105, 0.066),
    (0.395, 0.070, 0.056), (0.41, 0.057, 0.051), (0.43, 0.054, 0.050), (0.52, 0.052, 0.050)]
DF_Y = 0.95


def _df_interp(z):
    """Catmull-Rom through DF_K (smooth shoulders)."""
    zs = [k[0] for k in DF_K]
    if z <= zs[0]:
        return DF_K[0][1], DF_K[0][2]
    if z >= zs[-1]:
        return DF_K[-1][1], DF_K[-1][2]
    i = max(0, min(len(zs) - 2, int(np.searchsorted(zs, z)) - 1))
    t = (z - zs[i]) / (zs[i + 1] - zs[i])
    out = []
    for c in (1, 2):
        p0 = DF_K[max(0, i - 1)][c]
        p1, p2 = DF_K[i][c], DF_K[i + 1][c]
        p3 = DF_K[min(len(zs) - 1, i + 2)][c]
        out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                          (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return out[0], out[1]


def dress_form_point(z, ang, off=0.0):
    """Surface point at height z and polar angle ang (0 = +x, -90deg = front, towards -y)."""
    rx, ry = _df_interp(z)
    # superellipse section (flatter front/back than an ellipse)
    c, s_ = math.cos(ang), math.sin(ang)
    e = 2.0 / 2.4
    x = rx * math.copysign(abs(c) ** e, c)
    y = ry * math.copysign(abs(s_) ** e, s_)
    n = Vector((x / (rx * rx), y / (ry * ry), 0)).normalized()
    return Vector((x, y, z)) + n * off


def build_dress_form(mat):
    zs = np.concatenate([np.linspace(-0.10, 0.30, 50), np.linspace(0.305, 0.43, 70), np.linspace(0.44, 0.52, 10)])
    seg = 160
    rings = []
    for z in zs:
        ring = [tuple(dress_form_point(z, a)) for a in np.linspace(0, 2 * np.pi, seg, endpoint=False)]
        rings.append(np.array(ring))
    ob = mesh_from_rings('dressform', rings, cap_start=np.array([0, 0, -0.10]), cap_end=np.array([0, 0, 0.52]))
    assign(ob, mat)
    # turned wooden neck cap
    cap = revolve('neckcap', [(0, 520), (60, 520), (62, 526), (40, 540), (12, 548), (12, 600), (0, 600)], seg=96)
    for v in cap.data.vertices:
        v.co *= 1.0
    cap.scale = (0.9, 0.9, 1)
    return ob


# ------------------------------------------------------------------------------------------
# shots
ANNOT = []
POST = {}


def stand_z(par_bot_y):
    return -par_bot_y * MM


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


def hang_cord(a, spread=0.07, height=0.30, radius=0.75, col='#D8CBB6', sag_x=0.0):
    """A cord running left-right through the split ring, both ends rising out of frame (a V)."""
    bpy.context.view_layer.update()
    ring = [c for c in a.children if c.name.endswith('_splitring')][0]
    M = ring.matrix_world
    R, w = a['ring_R'], 0.5
    P = M @ Vector((0, (2 * R - w - radius - 0.05) * MM, 0))
    ex = (M.to_3x3() @ Vector((1, 0, 0))).normalized()     # hole axis of the ring
    up = Vector((0, 0, 1))
    pts = []
    for s_ in (-1, 1):
        side = [P + ex * s_ * spread + up * height,
                P + ex * s_ * spread * 0.35 + up * height * 0.33,
                P + ex * s_ * 0.004 + up * 0.0012]
        pts.append(side)
    path = pts[0] + [P] + pts[1][::-1]
    return cord_obj('cord', [tuple(v) for v in path], radius, col)


def studio3(tgt, k=1.0, warm=5600, bg=9.0):
    area_light('key', (tgt.x - 0.42, tgt.y - 0.32, tgt.z + 0.42), tgt, 0.5, 2.2 * k, blackbody_rgb(warm), spread=70)
    area_light('fill', (tgt.x + 0.55, tgt.y - 0.25, tgt.z + 0.12), tgt, 0.8, 0.6 * k, blackbody_rgb(5000))
    area_light('rim', (tgt.x - 0.22, tgt.y + 0.35, tgt.z + 0.2), tgt, 0.3, 2.6 * k, blackbody_rgb(5000), spread=50)
    area_light('top', (tgt.x, tgt.y, tgt.z + 0.55), tgt, 0.5, 0.7 * k, blackbody_rgb(5600), spread=60)
    area_light('bg', (0.0, -0.1, 0.9), (0, 0.55, 0.25), 1.2, bg, blackbody_rgb(4500), spread=60)


def shot_hero(social=False, tag='hero'):
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#D9CDBE')
    TUNE['frost_rough'] = min(TUNE['frost_rough'], 0.42)
    a = build_soul(tag, '#F3F1EC', 'cream_look', eye_strength=2.8, glow='cream', glow_strength=0.06, inner=2.5, ring_tilt=0, dens=20.0)
    lift = 0.016
    place(a, (0, 0, V3['R'] * MM + lift), (90, 0, -14))
    hang_cord(a, spread=0.05, height=0.32, radius=0.7)
    tgt = world_point(a, (0, 5.0, 0))
    focus = world_point(a, (-4, 1, 8))
    if social:
        cam = camera((0.16, -0.40, 0.080), tgt, lens=85, fstop=11.0, focus=focus, shift=(0, 0.125))
    else:
        cam = camera((0.165, -0.37, 0.078), tgt, lens=105, fstop=11.0, focus=focus)
    protect_screens(cam, tgt, 1.6, -0.012)
    screen_highlight(a, cam, up_deg=11.0, side_deg=8.5, size=(0.022, 0.3), tilt_deg=-30.0, strength=7.0,
                     z_mm=V3['Z_TOP'])
    studio3(tgt, bg=7.0)
    # back light through the frosted rim (reads as glass, not plastic)
    area_light('back', (tgt.x + 0.08, tgt.y + 0.30, tgt.z - 0.005), tgt + Vector((0, 0, 0.01)), 0.10, 2.5 * TUNE.get('backlight', 1.0),
               blackbody_rgb(4500), spread=35)
    POST['exposure'] = -0.6
    return sc


def twisted_cord(name, pts, radius=0.55, cols=('#9E0A16', '#F4F0E8'), twist_mm=4.0):
    """Two silk strands twisted around a smooth path through pts (metres): the Mărțișor cord."""
    P = np.array([tuple(p) for p in pts])
    # Catmull-Rom resample
    out = []
    Q = np.vstack([P[0], P, P[-1]])
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        for t in np.linspace(0, 1, 40, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1])
    C = np.array(out)
    seg = np.linalg.norm(np.diff(C, axis=0), axis=1)
    L = np.concatenate([[0], np.cumsum(seg)])
    n = max(200, int(L[-1] / (0.25 * MM)))
    Ls = np.linspace(0, L[-1], n)
    C = np.stack([np.interp(Ls, L, C[:, k]) for k in range(3)], 1)
    T = np.gradient(C, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None] + 1e-12
    # parallel-transport frame
    ref = np.array([0, 0, 1.0]) if abs(T[0][2]) < 0.9 else np.array([1.0, 0, 0])
    N_ = np.cross(T[0], ref)
    N_ /= np.linalg.norm(N_)
    frames = []
    for i in range(n):
        if i:
            N_ = N_ - T[i] * np.dot(N_, T[i])
            N_ /= np.linalg.norm(N_) + 1e-12
        frames.append((N_.copy(), np.cross(T[i], N_)))
    obs = []
    for k, col in enumerate(cols):
        ph = k * math.pi
        pts_k = []
        for i in range(n):
            a = ph + 2 * math.pi * Ls[i] / (twist_mm * MM)
            nn, bb = frames[i]
            pts_k.append(C[i] + (nn * math.cos(a) + bb * math.sin(a)) * radius * 0.78 * MM)
        ob = curve_obj(name + str(k), np.array(pts_k), radius * MM, res=4)
        m, nt, p, out_ = new_mat(name + '_silk%d' % k)
        set_in(p, 'Base Color', srgb(col))
        set_in(p, 'Roughness', 0.38)
        set_in(p, 'Sheen Weight', 0.8)
        set_in(p, 'Sheen Roughness', 0.3)
        set_in(p, 'Anisotropic', 0.6)
        assign(ob, m)
        obs.append(ob)
    return obs, C


def hang_twisted(a, spread=0.05, height=0.3):
    bpy.context.view_layer.update()
    ring = [c for c in a.children if c.name.endswith('_splitring')][0]
    M = ring.matrix_world
    R, w, cr = a['ring_R'], 0.5, 1.0
    P = M @ Vector((0, (2 * R - w - cr - 0.05) * MM, 0))
    ex = (M.to_3x3() @ Vector((1, 0, 0))).normalized()
    up = Vector((0, 0, 1))
    left = [P - ex * spread + up * height, P - ex * spread * 0.35 + up * height * 0.33, P - ex * 0.004 + up * 0.0015]
    right = [P + ex * 0.004 + up * 0.0015, P + ex * spread * 0.35 + up * height * 0.33, P + ex * spread + up * height]
    return twisted_cord('martisor', left + [P] + right, 0.55)


# ---- 1 hero / 8 social: see shot_hero above


def shot_necklace():
    """Worn: on a waxed cord around a linen dress form (no head), resting on the chest."""
    sc = reset()
    world_color((0.93, 0.9, 0.86), 0.05)
    plane('wall', (4, 3), (0, 0.9, 1.0), (math.radians(90), 0, 0), mat_diffuse('wall', srgb('#BDB09E'), 0.95, 0.1))
    plane('floor', (4, 4), (0, 0, -0.6), (0, 0, 0), mat_diffuse('floor', srgb('#CFC3B2'), 0.9, 0.1))
    linen = mat_linen('linen', '#D3C4AA', 1.0)
    build_dress_form(linen)
    wood = mat_wood('walnut', srgb('#4A2E1C'), srgb('#24140B'), 0.35, 8.0)
    cap = revolve('neckcap', [(0, 510), (58, 510), (60, 518), (42, 532), (10, 540), (10, 600), (0, 600)], seg=96)
    cap.scale = (1.0, DF_Y + 0.05, 1.0)
    assign(cap, wood)
    # pendant on the sternum: find the chest surface below the neck
    zp = 0.255
    front = dress_form_point(zp, -math.pi / 2)
    dz = 0.004
    f2 = dress_form_point(zp + dz, -math.pi / 2)
    slope = math.atan2(f2.y - front.y, dz)          # chest leans back going up (positive when y grows)
    a = build_soul('necklace', '#F3F1EC', 'cream_down', eye_strength=2.6, glow='cream', glow_strength=0.1,
                   inner=8.0, ring_tilt=0)
    tilt = math.degrees(slope)
    place(a, (0, 0, 0), (90 - tilt * 0.9, 0, 4))
    bpy.context.view_layer.update()
    back = world_point(a, (0, 0, V3['Z_BOT']))
    target = Vector((front.x + 0.004, front.y - 0.0003, zp))
    a.location = Vector(a.location) + (target - back)
    # cord: from the ring up over the collarbones, around the neck base
    bpy.context.view_layer.update()
    ring = [c for c in a.children if c.name.endswith('_splitring')][0]
    Rr = a['ring_R']
    P = ring.matrix_world @ Vector((0, (2 * Rr - 0.5 - 1.0) * MM, 0))
    sides = []
    z0 = P.z + 0.006
    for sx in (-1, 1):
        side = []
        for u in np.linspace(0, 1, 48):
            zz = z0 + (0.402 - z0) * math.sin(u * math.pi / 2) ** 0.85
            ang = 7 + 173 * u ** 1.35
            q = dress_form_point(zz, math.radians(-90 + sx * ang), off=0.0016)
            if u < 0.12:     # leave the chest towards the ring (the pendant stands off the body)
                w_ = (1 - u / 0.12) ** 2
                q = q.lerp(P + Vector((sx * 0.004, 0, 0.004)), w_)
            side.append(q)
        sides.append(side)
    path = sides[0][::-1] + [P] + sides[1]
    cord_obj('cord', [tuple(v) for v in path], 1.0, '#9C8870', 0.5)
    tgt = world_point(a, (0, 12, 0))
    focus = world_point(a, (0, 0, V3['Z_TOP']))
    cam = camera(tgt + Vector((0.30, -0.66, 0.15)), tgt + Vector((0.0, 0, 0.036)), lens=85, fstop=3.5, focus=focus)
    flag(cam, tgt)
    screen_highlight(a, cam, up_deg=10.0, side_deg=9.0, size=(0.022, 0.3), tilt_deg=-30.0, strength=6.0,
                     z_mm=V3['Z_TOP'])
    area_light('window', (tgt.x - 0.9, tgt.y - 0.5, tgt.z + 0.6), tgt, 1.2, 60, blackbody_rgb(5600), 'RECTANGLE', 0.9)
    area_light('fill', (tgt.x + 0.7, tgt.y - 0.6, tgt.z + 0.1), tgt, 1.0, 8, blackbody_rgb(4500), glossy=False)
    area_light('rim', (tgt.x + 0.35, tgt.y + 0.45, tgt.z + 0.35), tgt, 0.5, 12, blackbody_rgb(5000), spread=60)
    POST['exposure'] = -0.1
    return sc


def shot_caseback():
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#DCD2C5')
    a = build_soul('caseback', '#F3F1EC', 'cream', eye_strength=2.0, glow='cream', glow_strength=0.1, inner=6.0,
                   ring_tilt=-30)
    place(a, (0, 0, stand_z(a['bot_y']) + 0.0002), (90, 0, 180 - 8))
    tgt = world_point(a, (0, 6.0, V3['Z_BOT']))
    focus = world_point(a, (8.0, 15.0, V3['Z_BOT']))
    cam = camera(tgt + Vector((-0.15, -0.17, 0.066)), tgt + Vector((-0.002, 0, -0.003)), lens=100, fstop=4.0,
                 focus=focus)
    flag(cam, tgt, dist=0.05, size=(1.2, 1.0), col=(0.03, 0.03, 0.03))
    protect_screens(cam, tgt, 0.5, 0.03)
    area_light('key', (tgt.x + 0.30, tgt.y - 0.30, tgt.z + 0.35), tgt, 0.5, 2.4, blackbody_rgb(5600), spread=80)
    area_light('strip', (tgt.x - 0.25, tgt.y - 0.12, tgt.z + 0.22), tgt, 0.06, 1.5, blackbody_rgb(5600),
               'RECTANGLE', 0.5, spread=60)
    area_light('fill', (tgt.x - 0.4, tgt.y - 0.3, tgt.z + 0.1), tgt, 0.8, 0.5, blackbody_rgb(4500))
    area_light('rim', (tgt.x + 0.1, tgt.y + 0.35, tgt.z + 0.25), tgt, 0.3, 2.0, blackbody_rgb(5000), spread=50)
    area_light('bg', (0.0, -0.1, 0.9), (0, 0.55, 0.25), 1.2, 6.0, blackbody_rgb(4500), spread=60)
    POST['exposure'] = -0.2
    return sc


def shot_night():
    sc = reset()
    world_color((0.02, 0.03, 0.06), 0.35)
    table = rounded_box('table', 0.9, 0.5, 0.03, 0.006)
    table.location = (0, 0.08, -0.015)
    assign(table, mat_wood('walnut', srgb('#3B2416'), srgb('#1C0F08'), 0.35, 5.0))
    plane('wall', (3, 2), (0, 0.4, 0.5), (math.radians(90), 0, 0), mat_diffuse('wall', srgb('#2A2E38'), 0.9, 0.1))
    a = build_soul('night', '#F3F1EC', 'amber_sleepy', eye_strength=3.4, glow='amber', glow_strength=0.12,
                   inner=0.35, dens=70, ring_tilt=-35)
    place(a, (0, 0, stand_z(a['bot_y']) + 0.0002), (90, 0, -16))
    tgt = world_point(a, (0, 2.0, 0))
    focus = world_point(a, (-5, 2, 8))
    camera((0.165, -0.44, 0.08), tgt, lens=105, fstop=2.8, focus=focus)
    area_light('spill', world_point(a, (0, -8, 16)), world_point(a, (0, -40, 40)), 0.03, 0.4,
               blackbody_rgb(2200), 'DISK', spread=150)
    area_light('spill_back', world_point(a, (0, -5, -16)), world_point(a, (0, -40, -60)), 0.03, 0.25,
               blackbody_rgb(2200), 'DISK', spread=150)
    area_light('moon', (-0.9, 0.05, 0.6), tgt, 0.6, 18, blackbody_rgb(8000), 'RECTANGLE', 0.3)
    area_light('moon_rim', (0.3, 0.6, 0.35), tgt, 0.3, 2.5, blackbody_rgb(8000))
    book = rounded_box('book', 0.16, 0.22, 0.025, 0.002)
    book.location = (-0.17, 0.15, 0.0125)
    book.rotation_euler = (0, 0, math.radians(-12))
    assign(book, mat_diffuse('book', srgb('#6B2E2A'), 0.6, 0.3))
    book2 = rounded_box('book2', 0.15, 0.21, 0.02, 0.002)
    book2.location = (-0.16, 0.16, 0.035)
    book2.rotation_euler = (0, 0, math.radians(-5))
    assign(book2, mat_diffuse('book2', srgb('#7A6A55'), 0.7, 0.3))
    return sc


def shot_listening():
    """Editorial: dark grey seamless, hanging on its cord, halo breathing soft blue, eyes looking up."""
    sc = reset()
    world_color((0.05, 0.05, 0.055), 0.2)
    sweep('#2E2F32', rough=0.9, wall_y=0.9, height=3.0)
    a = build_soul('listen', '#F3F1EC', 'listen_up', eye_strength=2.8, glow='blue', glow_strength=0.12,
                   inner=2.2, ring_tilt=0)
    place(a, (0, 0, V3['R'] * MM + 0.12), (90, 0, -18))
    hang_cord(a, spread=0.045, height=0.35, radius=0.7, col='#2C2A28')
    tgt = world_point(a, (0, 4.0, 0))
    focus = world_point(a, (-4, 2, 8))
    cam = camera(tgt + Vector((0.17, -0.40, 0.012)), tgt + Vector((-0.004, 0, 0.0)), lens=105, fstop=5.6,
                 focus=focus)
    protect_screens(cam, tgt, 1.6, -0.012)
    screen_highlight(a, cam, up_deg=11.0, side_deg=8.5, size=(0.022, 0.3), tilt_deg=-30.0, strength=5.0,
                     z_mm=V3['Z_TOP'])
    area_light('key', (tgt.x - 0.45, tgt.y - 0.2, tgt.z + 0.35), tgt, 0.35, 0.45, blackbody_rgb(6500), spread=25)
    area_light('rim_l', (tgt.x - 0.25, tgt.y + 0.3, tgt.z + 0.15), tgt, 0.15, 2.0, blackbody_rgb(8000), spread=40)
    area_light('rim_r', (tgt.x + 0.3, tgt.y + 0.25, tgt.z + 0.2), tgt, 0.15, 1.6, blackbody_rgb(6500), spread=40)
    area_light('bg', (tgt.x - 0.1, 0.3, tgt.z + 0.5), (tgt.x + 0.05, 0.9, tgt.z - 0.05), 0.6, 6.0, blackbody_rgb(6500), spread=60)
    POST['exposure'] = 0.0
    return sc


LINEUP = [  # label, body tint, eyes, glow, metal
    ('bone', '#F3F1EC', 'cream_lu', 'cream', 'ti'),
    ('ice', '#CDE2F6', 'ice', 'ice', 'ti'),
    ('mint', '#BEE2DF', 'mint', 'mint', 'ti'),
    ('peach', '#F7D8CB', 'peach', 'peach', 'ti'),
    ('lilac', '#DCD2F2', 'lilac', 'lilac', 'ti'),
    ('gold', '#E9D6B4', 'gold', 'gold', 'gold'),
    ('onyx', '#1C1C21', 'cream_front', 'cream', 'ti'),
    ('martisor', '#F1ECE2', 'cream_look', 'cream', 'ti'),
]


def build_stand(name, x, y, mat):
    """Small turned stone puck with a slot the coin stands in."""
    st = revolve(name, [(0, 0), (19.0, 0), (20.0, 1.0), (20.0, 7.0), (19.2, 8.0), (0, 8.0)], seg=96)
    st.location = (x, y, 0)
    st.scale = (1.0, 0.72, 1.0)
    assign(st, mat)
    return st


def shot_lineup():
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#DDD2C4', wall_y=0.75)
    stone = mat_diffuse('travertine', srgb('#CFC4B6'), 0.7, 0.3)
    gap = 0.078
    rows = [(LINEUP[:4], 0.075, -1.5 * gap - 0.02), (LINEUP[4:], -0.045, -1.5 * gap + 0.02)]
    for items, y, x0 in rows:
        for i, (lab, tint, eyes, glow, metal) in enumerate(items):
            x = x0 + i * gap
            build_stand('stand_' + lab, x, y, stone)
            a = build_soul(lab, tint, eyes, eye_strength=1.9, glow=glow, glow_strength=0.05, inner=1.5,
                           metal=metal, ring_tilt=-30, dens=(90 if lab == 'onyx' else 45), halo_white=0.2)
            place(a, (x, y, V3['R'] * MM + 0.0045), (90, 0, -22))
            if lab == 'martisor':
                bpy.context.view_layer.update()
                ring = [c for c in a.children if c.name.endswith('_splitring')][0]
                M = ring.matrix_world
                top = M @ Vector((0, (2 * a['ring_R'] - 0.5 - 0.6) * MM, 0))
                loop = [top + Vector((0.0, 0.009 * (1 - math.cos(t)), 0.0)) * 1.0 +
                        Vector((0.0045 * math.sin(t), 0, 0.011 * math.sin(t / 2) ** 2)) for t in
                        np.linspace(0, 2 * math.pi, 24)]
                twisted_cord('mcord', loop, 0.45)
    tgt = Vector((0.0, 0.012, 0.03))
    cam = camera((0.0, -0.80, 0.30), tgt, lens=84, fstop=11.0, focus=Vector((0, 0.0, 0.03)))
    protect_screens(cam, tgt, 1.4, -0.03)
    flag(cam, tgt, dist=0.2, size=(4.0, 3.0))
    studio3(tgt, 1.5)
    POST['exposure'] = -0.35
    return sc


def shot_scale():
    """Top-down-ish: v3 (Ø56), v1 (Ø52) and a generic house key, lying on warm paper."""
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#E6DDD1', wall_y=0.8)
    # v1 coin, from the v1 code (outline from cad/gen_shapes.py, Ø52 x 18.5 mm)
    a1 = build_amulet('v1', 'coin', '#F3F5F7', 'cream_look', eye_strength=2.6, glow_w=0.02, ring_tilt=-90.0)
    a1.location = (-0.066, 0.004, (H_HALF + 0.35) * MM)
    a1.rotation_euler = (0, 0, math.radians(8))
    a3 = build_soul('v3', '#F3F1EC', 'cream_look', eye_strength=2.6, glow='cream', glow_strength=0.1, inner=6.0,
                    ring_tilt=-90.0)
    a3.location = (0.0, 0.004, -V3['Z_BOT'] * MM)
    a3.rotation_euler = (0, 0, math.radians(-4))
    key = build_key('key')
    key.location = (0.062, -0.006, 0.0)
    key.rotation_euler = (0, 0, math.radians(100))
    tgt = Vector((-0.003, -0.004, 0.006))
    cam = camera((0.0, -0.17, 0.46), tgt, lens=90, fstop=11.0, focus=Vector((-0.004, 0, 0.012)), shift=(0, -0.012))
    flag(cam, tgt)
    y0 = min(world_point(a1, (0, 0, 0)).y - 26.0 * MM, world_point(a3, (0, 0, 0)).y - V3['R'] * MM) - 0.011
    for par, r_mm in ((a1, 26.0), (a3, V3['R'])):
        c = world_point(par, (0, 0, 0))
        ANNOT.append(dict(a=Vector((c.x - r_mm * MM, y0, 0)), b=Vector((c.x + r_mm * MM, y0, 0)), label=''))
    ANNOT[0]['label'] = 'SOUL v1 Ø52'
    ANNOT[1]['label'] = 'SOUL Ø56'
    studio3(tgt, 1.2)
    POST['exposure'] = -0.2
    return sc


def shot_martisor():
    """Mărțișor edition: bone body hung on a twisted red-and-white silk cord."""
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#EDE4DA')
    a = build_soul('martisor', '#F1ECE2', 'cream_look', eye_strength=2.7, glow='cream', glow_strength=0.1,
                   inner=10.0, ring_tilt=0)
    place(a, (0, 0, V3['R'] * MM + 0.02), (90, 0, 14))
    hang_twisted(a, spread=0.045, height=0.3)
    tgt = world_point(a, (0, 8.0, 0))
    focus = world_point(a, (4, 1, 8))
    cam = camera(tgt + Vector((-0.17, -0.40, 0.03)), tgt, lens=105, fstop=8.0, focus=focus)
    protect_screens(cam, tgt, 1.6, -0.012)
    screen_highlight(a, cam, up_deg=11.0, side_deg=-8.5, size=(0.022, 0.3), tilt_deg=30.0, strength=7.0,
                     z_mm=V3['Z_TOP'])
    studio3(tgt)
    POST['exposure'] = -0.3
    return sc


def shot_turntable():
    sc = shot_hero(tag='turntable')
    a = bpy.data.objects['soul_turntable']
    for ob in list(bpy.data.objects):
        if ob.name.startswith('cord'):
            bpy.data.objects.remove(ob)
    fr = 120
    sc.frame_start, sc.frame_end = 1, fr
    for f in (1, fr + 1):
        a.rotation_euler = (math.radians(90), 0, math.radians(-14 + (f - 1) * 360.0 / fr))
        a.keyframe_insert('rotation_euler', frame=f)
    for fc in a.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    return sc


SHOTS = {
    'hero': (shot_hero, 1600, 1200, 160),
    'necklace': (shot_necklace, 1600, 1200, 128),
    'caseback': (shot_caseback, 1600, 1200, 160),
    'night': (shot_night, 1600, 1200, 160),
    'listening': (shot_listening, 1600, 1200, 128),
    'lineup': (shot_lineup, 1600, 1200, 128),
    'scale': (shot_scale, 1600, 1200, 96),
    'martisor': (shot_martisor, 1600, 1200, 128),
    'social': (lambda: shot_hero(True, 'social'), 1080, 1920, 128),
    'turntable': (shot_turntable, 540, 540, 24),
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
    from bpy_extras.object_utils import world_to_camera_view
    fn, W, H, S = SHOTS[ARGS.shot]
    t0 = time.time()
    POST.clear()
    POST.update(look='AgX - Medium High Contrast', exposure=0.0, bloom=0.06)
    ANNOT.clear()
    sc = fn()
    POST['exposure'] += TUNE['exposure']
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
    bpy.context.view_layer.update()
    annot = []
    for an in ANNOT:
        pa = world_to_camera_view(sc, sc.camera, an['a'])
        pb = world_to_camera_view(sc, sc.camera, an['b'])
        annot.append(dict(label=an['label'], a=(pa.x, 1 - pa.y), b=(pb.x, 1 - pb.y)))
    if ARGS.shot == 'turntable':
        if ARGS.frames:
            sc.frame_start, sc.frame_end = [int(v) for v in ARGS.frames.split(':')]
        frames = list(range(sc.frame_start, sc.frame_end + 1))
        bpy.ops.render.render(animation=True)
    else:
        frames = [sc.frame_current]
        bpy.ops.render.render(write_still=False)
    meta = dict(POST, w=w, h=h, frames=frames, base=base, stem=stem, samples=sc.cycles.samples,
                seconds=round(time.time() - t0, 1), annot=annot)
    json.dump(meta, open(base + '.json', 'w'), indent=1)
    print('RENDERED', json.dumps(meta)[:300])


main()
