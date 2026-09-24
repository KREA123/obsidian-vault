"""soul_scene.py -- procedural Blender (Cycles) product renders of SOUL v2 (palm-size pebble).

Run headless (Blender 4.0+):
    blender -b --factory-startup --python soul_scene.py -- --shot hero [--preview] [--samples N]
            [--w W --h H] [--tmp DIR] [--frames a:b] [--set key=value] [--save-blend]

Shots: hero, hand, scale, os, colors, night, social (1080x1920), turntable (540x540 frames).

Re-uses the v1 pipeline (../../src/suflet_scene.py is loaded as a library: scene reset, lights,
cameras, flags, sweep, v1 amulet for the scale shot, compositor -> EXR passes) and post.py
(OIDN denoise + bloom + AgX). New here: the pebble body, a frosted-glass material with visible
sub-surface light, the 1.75" screen, side button, strap lug + fabric wrist strap, magnetic stand,
a stylised hand, and the v2 shots.
"""
import argparse
import json
import math
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.abspath(os.path.join(HERE, '..'))
V1_SRC = os.path.abspath(os.path.join(HERE, '..', '..', 'src'))
TEX = os.path.join(HERE, 'tex')
sys.dont_write_bytecode = True

# ------------------------------------------------------------------------------------------
# args (v2)
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--shot', default='hero')
ap.add_argument('--preview', action='store_true', help='half resolution, few samples')
ap.add_argument('--samples', type=int, default=0)
ap.add_argument('--w', type=int, default=0)
ap.add_argument('--h', type=int, default=0)
ap.add_argument('--tmp', default='/tmp/soul_v2_render')
ap.add_argument('--frames', default='')
ap.add_argument('--save-blend', action='store_true')
ap.add_argument('--threads', type=int, default=0)
ap.add_argument('--set', action='append', default=[])
ap.add_argument('--tag', default='')
ARGS = ap.parse_args(argv)
os.makedirs(ARGS.tmp, exist_ok=True)

# ------------------------------------------------------------------------------------------
# load the v1 scene script as a library (everything except its final main() call)
V1 = {'__name__': 'suflet_v1', '__file__': os.path.join(V1_SRC, 'suflet_scene.py')}
_argv = sys.argv
sys.argv = ['blender', '--', '--tmp', ARGS.tmp, '--out', ARGS.tmp] + (
    ['--threads', str(ARGS.threads)] if ARGS.threads else [])
_src = open(V1['__file__']).read()
exec(compile(_src[:_src.rindex('\nmain()')], V1['__file__'], 'exec'), V1)
sys.argv = _argv

srgb, blackbody_rgb = V1['srgb'], V1['blackbody_rgb']
mesh_from_rings, revolve, curve_obj, rounded_box = V1['mesh_from_rings'], V1['revolve'], V1['curve_obj'], V1['rounded_box']
new_mat, set_in, assign = V1['new_mat'], V1['set_in'], V1['assign']
mat_metal, mat_glass, mat_diffuse, mat_emit, mat_wood = (V1['mat_metal'], V1['mat_glass'], V1['mat_diffuse'],
                                                         V1['mat_emit'], V1['mat_wood'])
world_color, area_light, aim, camera, flag, glossy_card, plane, sweep = (
    V1['world_color'], V1['area_light'], V1['aim'], V1['camera'], V1['flag'], V1['glossy_card'], V1['plane'],
    V1['sweep'])
MM = V1['MM']

# look parameters (override with --set key=value)
TUNE = dict(frost_rough=0.25, frost_dens=90.0, frost_bump=0.2, glow=1.0, eye=3.0, module_grey=0.3, absk=0.35, aniso=0.8,
            darkfield=0,
            caustics=1, chassis_grey=0.0, aqua=1.0, core=0.0, core_inset=2.2, core_mfp=6.0,
            tint_abs=0.9, rim_clear=0.9, rim_r0=22.0, rim_r1=31.0, grain_scale=3000.0, lens=62.0, sx=-0.05)
TUNE['aqua'] = 1.3
for kv in ARGS.set:
    k, v = kv.split('=')
    TUNE[k] = float(v)
POST = dict(look='AgX - Medium High Contrast', exposure=0.0, bloom=0.06)

# ------------------------------------------------------------------------------------------
# pebble dimensions (mm).  Outline 70 x 64, 21.9 mm thick at the centre (8.6 front + 1.35 lens + 11.6 back
# + 0.35 back cap), screen: 1.75" AMOLED, Ø44 visible under a Ø46.4 domed black lens.
P2 = dict(a=35.0, b_top=30.6, b_bot=33.4, n=2.45, HF=8.6, HB=11.6, R_REC=23.2, FIL=0.8, R_SCREEN=22.0,
          dome=1.35, lug_deg=205.0, button_deg=-24.0)
NRES = 400


def pebble_outline(N=NRES):
    t = np.linspace(0, 2 * np.pi, 4000, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    e = 2.0 / P2['n']
    x = P2['a'] * np.sign(c) * np.abs(c) ** e
    b = np.where(s > 0, P2['b_top'], P2['b_bot'])
    y = b * np.sign(s) * np.abs(s) ** e
    # a little river-stone irregularity (low-frequency, keeps it convex)
    ang = np.arctan2(y, x)
    k = 1 + 0.010 * np.sin(2 * ang + 0.7) + 0.006 * np.sin(3 * ang + 1.9)
    x, y = x * k, y * k
    # resample uniformly by arc length
    P = np.column_stack([x, y])
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(np.r_[P, P[:1]], axis=0).T))]
    u = np.linspace(0, d[-1], N, endpoint=False)
    Q = np.column_stack([np.interp(u, d, np.r_[P[:, 0], P[0, 0]]), np.interp(u, d, np.r_[P[:, 1], P[0, 1]])])
    return Q


def outline_at(P, deg):
    """Point + outward normal + tangent of the outline in direction deg (from the screen centre)."""
    ang = np.arctan2(P[:, 1], P[:, 0])
    i = int(np.argmin(np.abs((ang - math.radians(deg) + np.pi) % (2 * np.pi) - np.pi)))
    p = P[i]
    tng = P[(i + 1) % len(P)] - P[i - 1]
    tng /= np.linalg.norm(tng)
    nrm = np.array([tng[1], -tng[0]])
    if nrm.dot(p) < 0:
        nrm = -nrm
    return p, nrm, tng


def build_pebble_body(name, P, inset=0.0):
    """Outer glass body (inset=0, with the screen recess) or the milky inner core (inset>0: the same
    river-stone form shrunk by `inset` mm, with a flat top under the display)."""
    O0 = np.asarray(P)
    r0 = np.hypot(O0[:, 0], O0[:, 1])
    d = O0 / r0[:, None]
    O = O0 - d * inset
    HF, HB, R_REC, FIL = P2['HF'] - inset, P2['HB'] - inset, P2['R_REC'], P2['FIL']
    r_lip = R_REC + FIL
    L = d * r_lip

    def ring(xy, z):
        return np.column_stack([xy, np.full(len(xy), z)]) * MM

    rings = []
    if inset == 0:
        z_floor = HF - 2.4
        for f in (0.5, 1.0):
            rings.append(ring(d * R_REC * f, z_floor))
        for t in np.linspace(math.pi, math.pi / 2, 8):
            rings.append(ring(d * (r_lip + FIL * math.cos(t)), HF - FIL + FIL * math.sin(t)))
        top = z_floor
    else:
        top = P2['HF'] - 2.4 - 0.25          # just under the display module
        HF = top
        for f in (0.5, 0.85):
            rings.append(ring(L * f, top))
        rings.append(ring(L, top))
    # front shoulder: quarter ellipse lip -> equator (very soft), denser near the equator
    nf = 34
    for i in range(1, nf + 1):
        ph = (math.pi / 2) * (1 - (1 - i / nf) ** 1.25)
        rings.append(ring(L + (O - L) * math.sin(ph), HF * math.cos(ph)))
    # back: superellipse equator -> flat-ish bottom
    eb = 2.0 / 2.7
    nb = 40
    for i in range(1, nb):
        ps = (math.pi / 2) * (i / nb) ** 0.9
        rings.append(ring(O * math.cos(ps) ** eb, -HB * math.sin(ps) ** eb))
    ob = mesh_from_rings(name + ('_body' if inset == 0 else '_core'), rings,
                         cap_start=np.array([0, 0, top]) * MM, cap_end=np.array([0, 0, -HB - 0.05]) * MM)
    return ob


def mat_core(name, tint, dark=False):
    """Milky inner core (opal diffuser) under the clear frosted shell: sub-surface scattering, so light
    that enters anywhere glows through the whole stone."""
    m, nt, p, out = new_mat(name)
    c = srgb(tint)
    set_in(p, 'Base Color', c)
    set_in(p, 'Roughness', 0.6)
    set_in(p, 'Subsurface Weight', 1.0)
    set_in(p, 'Subsurface Radius', (1.0, 0.95, 0.9) if not dark else (0.6, 0.6, 0.65))
    set_in(p, 'Subsurface Scale', TUNE['core_mfp'] * MM)
    set_in(p, 'Specular IOR Level', 0.2)
    try:
        p.subsurface_method = 'RANDOM_WALK'
    except Exception:
        pass
    return m


# ------------------------------------------------------------------------------------------
# materials
def mat_frost(name, tint, rough=None, dens=None, dark=False):
    """Frosted (acid-etched) glass: rough transmission + fine grain bump + light volume scattering,
    so light visibly travels through the body and the thin edges glow when back-lit."""
    rough = TUNE['frost_rough'] if rough is None else rough
    dens = TUNE['frost_dens'] if dens is None else dens
    m, nt, p, out = new_mat(name)
    c = srgb(tint)
    set_in(p, 'Base Color', c)
    set_in(p, 'IOR', 1.47)
    set_in(p, 'Transmission Weight', 1.0)
    # grain: very fine noise -> bump + small roughness variation (the matte etched feel)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = TUNE['grain_scale']
    nz.inputs['Detail'].default_value = 3.0
    nz.inputs['Roughness'].default_value = 0.7
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = TUNE['frost_bump']
    bp.inputs['Distance'].default_value = 0.00005
    nt.links.new(nz.outputs['Fac'], bp.inputs['Height'])
    nt.links.new(bp.outputs[0], p.inputs['Normal'])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['To Min'].default_value = rough * 0.85
    mr.inputs['To Max'].default_value = rough * 1.15
    nt.links.new(nz.outputs['Fac'], mr.inputs['Value'])
    nt.links.new(mr.outputs[0], p.inputs['Roughness'])
    vs = nt.nodes.new('ShaderNodeVolumeScatter')
    sc = tuple(min(1, x * 0.7 + 0.3) for x in c[:3]) if not dark else tuple(x * 0.6 + 0.05 for x in c[:3])
    vs.inputs['Color'].default_value = (*sc, 1)
    vs.inputs['Density'].default_value = dens
    if TUNE['rim_clear'] > 0:
        # clearer glass towards the rim, milky core: the thin outer band reads as glass and glows
        vl = nt.nodes.new('ShaderNodeVectorMath')
        vl.operation = 'LENGTH'
        sep = nt.nodes.new('ShaderNodeVectorMath')
        sep.operation = 'MULTIPLY'
        sep.inputs[1].default_value = (1.0, 1.08, 0.0)       # radial distance in the pebble plane
        nt.links.new(tc.outputs['Object'], sep.inputs[0])
        nt.links.new(sep.outputs[0], vl.inputs[0])
        rm = nt.nodes.new('ShaderNodeMapRange')
        rm.interpolation_type = 'SMOOTHSTEP'
        rm.inputs['From Min'].default_value = TUNE['rim_r0'] * MM
        rm.inputs['From Max'].default_value = TUNE['rim_r1'] * MM
        rm.inputs['To Min'].default_value = dens
        rm.inputs['To Max'].default_value = dens * (1 - TUNE['rim_clear'])
        nt.links.new(vl.outputs['Value'], rm.inputs['Value'])
        nt.links.new(rm.outputs[0], vs.inputs['Density'])
    vs.inputs['Anisotropy'].default_value = TUNE['aniso']
    va = nt.nodes.new('ShaderNodeVolumeAbsorption')
    aq = (1 - 0.10 * TUNE['aqua'], 1 - 0.025 * TUNE['aqua'], 1 - 0.04 * TUNE['aqua'])   # soda-lime edge tint
    va.inputs['Color'].default_value = (c[0] ** 1.5 * aq[0], c[1] ** 1.5 * aq[1], c[2] ** 1.5 * aq[2], 1)
    va.inputs['Density'].default_value = dens * TUNE['absk'] * (1.0 if min(c[:3]) > 0.8 else TUNE['tint_abs']) * (3.0 if dark else 1.0)
    add = nt.nodes.new('ShaderNodeAddShader')
    nt.links.new(vs.outputs[0], add.inputs[0])
    nt.links.new(va.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs['Volume'])
    return m


def mat_screen2(name, tex_path, strength):
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', (0.002, 0.002, 0.0025, 1))
    set_in(p, 'Roughness', 0.5)
    set_in(p, 'Specular IOR Level', 0.0)
    set_in(p, 'Coat Weight', 1.0)
    set_in(p, 'Coat Roughness', 0.015)
    set_in(p, 'Coat IOR', 1.5)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    s = 1.0 / (2 * P2['R_SCREEN'] * MM)
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


def mat_fabric(name, col, sheen=0.6):
    """Woven nylon/cotton strap: ribs across the length (UV u = length in mm) + fibre noise."""
    m, nt, p, out = new_mat(name)
    uv = nt.nodes.new('ShaderNodeUVMap')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(uv.outputs[0], sep.inputs[0])
    wv = nt.nodes.new('ShaderNodeTexWave')
    wv.wave_type = 'BANDS'
    wv.bands_direction = 'X'
    wv.inputs['Scale'].default_value = 0.0
    # explicit ribs: sin(u * 2pi / 0.7 mm) via math nodes (u is in mm)
    mul = nt.nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    mul.inputs[1].default_value = 2 * math.pi / 0.75
    nt.links.new(sep.outputs['X'], mul.inputs[0])
    sn = nt.nodes.new('ShaderNodeMath')
    sn.operation = 'SINE'
    nt.links.new(mul.outputs[0], sn.inputs[0])
    ab = nt.nodes.new('ShaderNodeMath')
    ab.operation = 'ABSOLUTE'
    nt.links.new(sn.outputs[0], ab.inputs[0])
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 3000.0
    nz.inputs['Detail'].default_value = 6.0
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    h = nt.nodes.new('ShaderNodeMath')
    h.operation = 'MULTIPLY_ADD'
    h.inputs[1].default_value = 0.8
    nt.links.new(ab.outputs[0], h.inputs[0])
    nt.links.new(nz.outputs['Fac'], h.inputs[2])
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.45
    bp.inputs['Distance'].default_value = 0.00012
    nt.links.new(h.outputs[0], bp.inputs['Height'])
    nt.links.new(bp.outputs[0], p.inputs['Normal'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = tuple(x * 0.72 for x in col[:3]) + (1,)
    ramp.color_ramp.elements[1].color = col
    nt.links.new(h.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], p.inputs['Base Color'])
    set_in(p, 'Roughness', 0.85)
    set_in(p, 'Sheen Weight', sheen)
    set_in(p, 'Sheen Roughness', 0.4)
    set_in(p, 'Specular IOR Level', 0.25)
    return m


def mat_skin(name, col='#C68B6C'):
    m, nt, p, out = new_mat(name)
    c = srgb(col)
    set_in(p, 'Base Color', c)
    set_in(p, 'Roughness', 0.52)
    set_in(p, 'Subsurface Weight', 0.35)
    set_in(p, 'Subsurface Radius', (1.0, 0.45, 0.25))
    set_in(p, 'Subsurface Scale', 0.004)
    set_in(p, 'Specular IOR Level', 0.35)
    set_in(p, 'Coat Weight', 0.08)
    set_in(p, 'Coat Roughness', 0.45)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 900.0
    nz.inputs['Detail'].default_value = 8.0
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.06
    bp.inputs['Distance'].default_value = 0.0002
    nt.links.new(nz.outputs['Fac'], bp.inputs['Height'])
    nt.links.new(bp.outputs[0], p.inputs['Normal'])
    return m


MATS = {}


def mats():
    if 'alu' not in MATS:
        MATS['alu'] = mat_metal('brushed_alu', (0.90, 0.90, 0.91), 0.30, 0.8, 'Z')
        MATS['alu_plain'] = mat_metal('alu_plain', (0.90, 0.90, 0.91), 0.26, 0.0)
        MATS['alu_dark'] = mat_metal('alu_dark', (0.30, 0.31, 0.33), 0.32, 0.6, 'Z')
    return MATS


# ------------------------------------------------------------------------------------------
# the pebble
def build_pebble(tag, tint, screen, eye_strength=None, glow_w=0.0, glow_col=2700, dens=None, rough=None,
                 dark=False, metal='alu', inner_light=0.0):
    """Local frame: x right, y up (top of the face), z out of the screen (mm*MM). Returns the parent."""
    eye_strength = TUNE['eye'] if eye_strength is None else eye_strength
    M = mats()
    P = pebble_outline()
    par = bpy.data.objects.new('pebble_' + tag, None)
    bpy.context.scene.collection.objects.link(par)
    parts = []
    body = build_pebble_body(tag, P)
    assign(body, mat_frost('frost_' + tag, tint, rough, dens, dark))
    parts.append(body)
    if TUNE['core'] > 0:
        core = build_pebble_body(tag, P, inset=TUNE['core_inset'])
        assign(core, mat_core('core_' + tag, tint, dark))
        parts.append(core)
    HF, R_REC = P2['HF'], P2['R_REC']
    # black domed lens over the emissive AMOLED
    z_floor = HF - 2.4
    r_s, z_le, z_lt = R_REC - 0.1, HF + 0.12, HF + 0.12 + P2['dome']
    h = z_lt - z_le
    Rs = (r_s ** 2 + h ** 2) / (2 * h)
    prof = [(0, z_lt)]
    for rr in np.linspace(0, r_s - 0.6, 36)[1:]:
        prof.append((rr, z_lt - (Rs - math.sqrt(Rs * Rs - rr * rr))))
    for t in np.linspace(math.pi / 2, 0, 7)[1:]:
        prof.append((r_s - 0.6 + 0.6 * math.cos(t), z_le - 0.6 + 0.6 * math.sin(t)))
    prof += [(r_s, z_floor + 0.3), (r_s - 0.3, z_floor + 0.02), (0, z_floor + 0.02)]
    stone = revolve(tag + '_lens', prof, seg=256)
    tex = screen if os.path.isabs(screen) else os.path.join(TEX, screen + '.png')
    assign(stone, mat_screen2('screen_' + tag, tex, eye_strength))
    parts.append(stone)
    # display module + battery stack seen softly through the frosting
    z_mt = z_floor - 0.15
    r_m = 23.6
    mod = revolve(tag + '_module', [(0, z_mt), (r_m - 0.8, z_mt), (r_m, z_mt - 0.8), (r_m, z_mt - 9.0),
                                    (r_m - 1.5, z_mt - 10.5), (0, z_mt - 10.5)], seg=128)
    g = TUNE['module_grey']
    assign(mod, V1['mat_diffuse']('module_' + tag, (g, g, g * 1.02, 1), 0.6, 0.3))
    parts.append(mod)
    # PCB + battery chassis (larger than the screen): a soft darker core seen through the frosted shoulder
    if TUNE['chassis_grey'] > 0:
        Q = P * 0.80
        rings = [np.column_stack([Q * f, np.full(len(Q), z)]) * MM for f, z in
                 ((0.97, -0.6), (1.0, -1.4), (1.0, -5.2), (0.97, -6.0))]
        ch = mesh_from_rings(tag + '_chassis', rings, cap_start=np.array([0, 0, -0.6]) * MM,
                             cap_end=np.array([0, 0, -6.0]) * MM)
        g2 = TUNE['chassis_grey']
        assign(ch, V1['mat_diffuse']('chassis_' + tag, (g2, g2, g2 * 1.03, 1), 0.5, 0.4))
        parts.append(ch)
    # side button (thin brushed-aluminium pill on the right edge)
    p, n, t = outline_at(P, P2['button_deg'])
    btn = rounded_box(tag + '_button', 13.0 * MM, 2.2 * MM, 2.6 * MM, 1.05 * MM, 6)
    btn.location = Vector(((p[0] + n[0] * -0.2) * MM, (p[1] + n[1] * -0.2) * MM, 0.9 * MM))
    btn.rotation_euler = (0, 0, math.atan2(t[1], t[0]))
    assign(btn, M[metal])
    parts.append(btn)
    # strap lug: a small stadium loop of aluminium wire, in the pebble plane, half sunk into the edge
    p, n, t = outline_at(P, P2['lug_deg'])
    Lh, Wh, wr = 5.2, 2.9, 0.95          # half length (tangent), half width (radial), wire radius
    c0 = p + n * 1.2
    pts = []
    for a in np.linspace(0, 2 * math.pi, 96, endpoint=False):
        ca, sa = math.cos(a), math.sin(a)
        # stadium: straight tangent sides, round ends
        tt = (Lh - Wh) * np.sign(ca) + Wh * ca if abs(ca) > 1e-9 else 0
        pts.append(c0 + t * tt + n * Wh * sa)
    lug = curve_obj(tag + '_lug', np.array([(x * MM, y * MM, 0) for x, y in pts]), wr * MM, closed=True, res=6)
    assign(lug, M[metal])
    parts.append(lug)
    bar = c0 + n * Wh                    # centre of the outer bar of the lug
    # inner glow (night light): warm emissive ring around the module + an optional light inside
    if glow_w > 0:
        bpy.ops.mesh.primitive_torus_add(major_radius=25.4 * MM, minor_radius=1.0 * MM, major_segments=128,
                                         minor_segments=12, location=(0, 0, (z_mt - 5.5) * MM))
        gl = bpy.context.active_object
        gl.name = tag + '_glowring'
        gl.visible_shadow = False
        assign(gl, mat_emit('glow_' + tag, blackbody_rgb(glow_col), glow_w * 100 * TUNE['glow']))
        parts.append(gl)
    if inner_light > 0:
        ld = bpy.data.lights.new(tag + '_inner', 'POINT')
        ld.energy = inner_light
        ld.color = blackbody_rgb(glow_col)
        ld.shadow_soft_size = 0.004
        il = bpy.data.objects.new(tag + '_inner', ld)
        bpy.context.scene.collection.objects.link(il)
        il.location = (0, 0, (z_mt - 11.5) * MM)
        parts.append(il)
    for ob in parts:
        ob.parent = par
    par['bar'] = [float(bar[0]), float(bar[1])]
    par['n_lug'] = [float(n[0]), float(n[1])]
    par['t_lug'] = [float(t[0]), float(t[1])]
    return par


def world_point(par, local_mm):
    bpy.context.view_layer.update()
    return par.matrix_world @ Vector(tuple(v * MM for v in local_mm))


def world_dir(par, local):
    return (par.matrix_world.to_3x3() @ Vector(local)).normalized()


def lay_flat(par, x, y, yaw_deg, floor=0.0):
    par.location = (x, y, floor + (P2['HB'] + 0.05) * MM)
    par.rotation_euler = (0, 0, math.radians(yaw_deg))


# ------------------------------------------------------------------------------------------
# fabric strap (mesh built from a centre line with a per-point "thickness" direction)
def band_mesh(name, pts, hints, width, thick, closed=True, seg=18):
    pts = np.asarray(pts, float)
    n = len(pts)
    T = np.roll(pts, -1, 0) - np.roll(pts, 1, 0) if closed else np.gradient(pts, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    H = np.asarray(hints, float)
    N = H - (H * T).sum(1)[:, None] * T
    N /= np.linalg.norm(N, axis=1)[:, None]
    W = np.cross(T, N)
    # rounded-rectangle (stadium) section
    rc = thick / 2
    sec = []
    for k in range(seg):
        a = 2 * math.pi * k / seg
        cx = (width / 2 - rc) * (1 if math.cos(a) >= 0 else -1)
        sec.append((cx + rc * math.cos(a), rc * math.sin(a)))
    sec = np.array(sec)
    verts, uvs = [], []
    s_len = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    for i in range(n):
        for (sx, sy) in sec:
            verts.append(pts[i] + W[i] * sx + N[i] * sy)
    faces = []
    for i in range(n if closed else n - 1):
        i2 = (i + 1) % n
        for k in range(seg):
            k2 = (k + 1) % seg
            faces.append((i * seg + k, i * seg + k2, i2 * seg + k2, i2 * seg + k))
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    uvl = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            i, k = divmod(vi, seg)
            uvl.data[li].uv = (s_len[i] / MM if i < len(s_len) else 0, k / seg)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def strap_flat(tag, par, floor=0.0, L_loop=150.0, W_loop=44.0, bend=0.35, col='#D9D0C3', width=8.0,
               thick=1.15, twist_at=0.25, metal='alu'):
    """Wrist strap through the lug of a pebble lying flat: lark's-head around the lug bar, aluminium
    crimp ferrule, then a long teardrop loop lying on the floor (with one natural half twist)."""
    bpy.context.view_layer.update()
    B = world_point(par, (par['bar'][0], par['bar'][1], 0))
    u = world_dir(par, (par['n_lug'][0], par['n_lug'][1], 0))
    u = Vector((u.x, u.y, 0)).normalized()
    ez = Vector((0, 0, 1))
    v = ez.cross(u)
    hb = (B.z - floor) / MM
    rw = 0.95
    rr = rw + thick / 2 + 0.05
    Lj = 17.0
    Bf = Vector((B.x, B.y, floor))

    def W(s, q, h):
        return Bf + u * (s * MM) + v * (q * MM) + ez * (h * MM)

    path, hint = [], []
    # top layer, from above the bar out to the joint
    for s in np.linspace(0, Lj, 12)[:-1]:
        path.append(W(s, 0, hb + rr)); hint.append(ez)
    # loop halves: teardrop, descending to the floor, curving to one side (bend)
    K = 90

    def half(sig, reverse):
        seq = []
        for i in range(K + 1):
            th = math.pi * i / K
            s = Lj + L_loop * (1 - math.cos(th)) / 2
            q = sig * (W_loop / 2 / 1.299) * math.sin(th) * (1 - math.cos(th))
            q += bend * (s - Lj) ** 2 / L_loop
            h0 = hb + sig * rr
            h = h0 + ((thick / 2 + 0.03) - h0) * smoothstep(Lj + 2, Lj + 34, s)
            nrm = ez
            if sig < 0:
                # half twist on the lower strand (flat side up on the floor, flat side down in the lark's head)
                k = smoothstep(Lj + L_loop * (twist_at - 0.12), Lj + L_loop * (twist_at + 0.12), s)
                nrm = ez * math.cos(math.pi * (1 - k)) + v * math.sin(math.pi * (1 - k)) * 0.999
            seq.append((W(s, q, h), nrm))
        return seq[::-1] if reverse else seq

    for p_, n_ in half(+1, False):
        path.append(p_); hint.append(n_)
    for p_, n_ in half(-1, True)[1:]:
        path.append(p_); hint.append(n_)
    # bottom layer back to the bar, then round the bar (through the lug, on its inner side)
    for s in np.linspace(Lj, 0, 12)[1:]:
        path.append(W(s, 0, hb - rr)); hint.append(-ez)
    for a in np.linspace(-math.pi / 2, math.pi / 2, 19)[1:-1]:
        s, h = -rr * math.cos(a), hb + rr * math.sin(a)
        path.append(W(s, 0, h)); hint.append((u * -math.cos(a) + ez * math.sin(a)).normalized())
    pts = np.array([tuple(p) for p in path])
    hin = np.array([tuple(h) for h in hint])
    # light smoothing of the centre line (keeps the ends of the tight wrap)
    for _ in range(3):
        pts = 0.5 * pts + 0.25 * (np.roll(pts, 1, 0) + np.roll(pts, -1, 0))
    ob = band_mesh(tag + '_strap', pts, hin, width * MM, thick * MM)
    assign(ob, mat_fabric('strap_' + tag, srgb(col)))
    # crimp ferrule hiding the joint
    fer = rounded_box(tag + '_ferrule', 9.5 * MM, (width + 1.6) * MM, (2 * rr + thick + 1.2) * MM, 1.3 * MM, 6)
    fer.location = W(Lj - 5.5, 0, hb)
    fer.rotation_euler = (0, 0, math.atan2(u.y, u.x))
    assign(fer, mats()[metal])
    return ob


# ------------------------------------------------------------------------------------------
# magnetic stand: aluminium puck with a slanted top + soft-touch pad
def build_stand(tag, loc, yaw_deg, tilt_deg=28.0, r=19.0, h_front=6.0, metal='alu', pad='#2A2B2E'):
    """Returns (stand parent, top-centre point, top normal) in world space."""
    a = math.radians(tilt_deg)
    tn = math.tan(a)
    h_c = h_front + tn * r
    t = np.linspace(0, 2 * np.pi, 160, endpoint=False)
    ct, st = np.cos(t), np.sin(t)
    rings = []
    f = 1.4
    for rr, z in ((r - f, 0.0), (r - f * (1 - math.cos(math.radians(45))), f * (1 - math.sin(math.radians(45)))),
                  (r, f)):
        rings.append(np.column_stack([rr * ct, rr * st, np.full_like(t, z)]))
    for k in np.linspace(0, 1, 5)[1:]:
        ang = k * math.pi / 2
        rr = r - f + f * math.cos(ang)
        rings.append(np.column_stack([rr * ct, rr * st, h_c + tn * (r * st) - f + f * math.sin(ang)]))
    rings = [x * MM for x in rings]
    ob = mesh_from_rings(tag + '_stand', rings, cap_start=np.array([0, 0, 0.0]),
                         cap_end=np.array([0, 0, h_c * MM]))
    assign(ob, mats()[metal])
    # pad (dark soft-touch disc) on the slanted face
    pd = revolve(tag + '_pad', [(0, 0.35), (r - 3.2, 0.35), (r - 2.9, 0.1), (r - 2.9, -0.5), (0, -0.5)], seg=128)
    pd.parent = ob
    pd.location = (0, 0, h_c * MM)
    pd.rotation_euler = (a, 0, 0)
    assign(pd, mat_diffuse('pad_' + tag, srgb(pad), 0.55, 0.3))
    ob.location = loc
    ob.rotation_euler = (0, 0, math.radians(yaw_deg))
    bpy.context.view_layer.update()
    top = ob.matrix_world @ Vector((0, 0, (h_c + 0.35) * MM))
    nrm = (ob.matrix_world.to_3x3() @ Vector((0, -math.sin(a), math.cos(a)))).normalized()
    return ob, top, nrm, a


def on_stand(par, stand_top, a, yaw_deg):
    par.rotation_euler = (a, 0, math.radians(yaw_deg))
    bpy.context.view_layer.update()
    nrm = world_dir(par, (0, 0, 1))
    par.location = stand_top + nrm * (P2['HB'] + 0.05) * MM


def dock(par, tag, x, y, yaw_deg, tilt_from_vertical=18.0, floor=0.0, metal='alu', pad='#2B2C30'):
    """Magnetic dock: the stone stands on a low aluminium plinth, leaning back on a slim backrest
    (the magnet + pogo pins sit in the backrest).  Mostly hidden behind the stone, like a watch dock."""
    a = math.radians(90.0 - tilt_from_vertical)
    par.location = (x, y, 0.1)
    par.rotation_euler = (a, 0, math.radians(yaw_deg))
    bpy.context.view_layer.update()
    body = [c for c in par.children if c.name.endswith('_body')][0]
    Mw = body.matrix_world
    zs = [(Mw @ v.co).z for v in body.data.vertices]
    H_pl = 6.5 * MM
    par.location = (x, y, 0.1 - (min(zs) - (floor + H_pl)))
    bpy.context.view_layer.update()
    nrm = world_dir(par, (0, 0, 1))
    upv = world_dir(par, (0, 1, 0))
    fwd = Vector((nrm.x, nrm.y, 0)).normalized()
    low = world_point(par, (0, -P2['b_bot'], -2.0))
    pl = rounded_box(tag + '_plinth', 66 * MM, 34 * MM, H_pl, 2.6 * MM, 6)
    pl.location = Vector((low.x, low.y, floor + H_pl / 2)) - fwd * 7 * MM
    pl.rotation_euler = (0, 0, math.radians(yaw_deg))
    assign(pl, mats()[metal])
    # dark soft-touch inlay in the plinth top, where the stone's edge sits
    inl = rounded_box(tag + '_inlay', 58 * MM, 12 * MM, 0.6 * MM, 0.3 * MM, 3)
    inl.location = Vector((low.x, low.y, floor + H_pl + 0.1 * MM)) - fwd * 1.5 * MM
    inl.rotation_euler = (0, 0, math.radians(yaw_deg))
    assign(inl, mat_diffuse('inlay_' + tag, srgb(pad), 0.6, 0.3))
    br = rounded_box(tag + '_backrest', 34 * MM, 7 * MM, 46 * MM, 3.0 * MM, 6)
    c = world_point(par, (0, -8.0, -P2['HB'] - 3.6))
    br.location = c
    br.rotation_euler = (a - math.pi / 2, 0, math.radians(yaw_deg))
    assign(br, mats()[metal])
    return pl


# ------------------------------------------------------------------------------------------
# reflections on the black domed lens
def lens_card(par, cam, dist=0.28, size=0.22, up_deg=15.0, side_deg=-15.0, strip=(0.012, 0.12), tilt_deg=-30.0,
              strength=5.0, card=True):
    """Glossy-only black card where the lens reflects (keeps the screen black) + a soft strip light
    for the thin crescent highlight on the dome."""
    bpy.context.view_layer.update()
    c = world_point(par, (0, 0, P2['HF'] + P2['dome']))
    n = world_dir(par, (0, 0, 1))
    v = (c - Vector(cam.location)).normalized()
    R = (v - 2 * v.dot(n) * n).normalized()
    if card:
        cd = glossy_card(c + R * (dist + 0.08), (size * 1.6, size * 1.6))
        cd.rotation_euler = (-R).to_track_quat('-Z', 'Y').to_euler()
    side = R.cross(Vector((0, 0, 1)))
    if side.length < 1e-3:
        side = Vector((1, 0, 0))
    side.normalize()
    up = side.cross(R).normalized()
    D = (R + up * math.tan(math.radians(up_deg)) + side * math.tan(math.radians(side_deg))).normalized()
    if strength > 0:
        ob = plane('strip', strip, c + D * dist, (0, 0, 0), mat_emit('strip', (1.0, 0.98, 0.95), strength))
        ob.rotation_euler = (-D).to_track_quat('-Z', 'Y').to_euler()
        ob.rotation_euler.rotate_axis('Z', math.radians(tilt_deg))
        for attr in ('visible_camera', 'visible_diffuse', 'visible_shadow', 'visible_transmission',
                     'visible_volume_scatter'):
            setattr(ob, attr, False)


def reset():
    sc = V1['reset']()
    MATS.clear()
    sc.cycles.caustics_refractive = bool(TUNE['caustics'])   # light through the frosted body into its shadow
    sc.cycles.caustics_reflective = False
    sc.cycles.blur_glossy = 1.0
    sc.cycles.volume_bounces = 4
    sc.cycles.transmission_bounces = 16
    sc.cycles.sample_clamp_indirect = 6.0
    return sc


def dark_field(tgt, cam, dist=0.07, h=0.03, size=(0.05, 0.10)):
    """Black cards just outside the frame, seen only in reflection/refraction: they draw the dark
    edge lines glass photographers use to define a translucent object on a light background."""
    c = Vector(cam.location)
    fwd = (Vector(tgt) - c)
    fwd.z = 0
    fwd.normalize()
    side = fwd.cross(Vector((0, 0, 1))).normalized()
    for sgn in (-1, 1):
        loc = Vector(tgt) + side * sgn * dist + Vector((0, 0, h)) + fwd * 0.01
        ob = glossy_card(loc, size, col=(0.004, 0.004, 0.004))
        ob.visible_transmission = True
        ob.rotation_euler = (Vector(tgt) - loc).to_track_quat('Z', 'Y').to_euler()


def glass_lights(tgt, k=1.0, back=1.0, bg=(0, 0.55, 0.25), bg_power=7.0, fill_side=1.0):
    """Back-lit glass setup: the main light is BEHIND the object (shadow falls towards the camera and
    the light that crosses the frosted body shows up as a warm caustic glow inside the shadow and as
    glowing edges); a big soft front box fills the face; bounce from the paper does the rest."""
    area_light('back', (tgt.x - 0.20 * fill_side, tgt.y + 0.36, tgt.z + 0.30), tgt, 0.22, 4.5 * back,
               blackbody_rgb(5200), spread=60)
    area_light('back2', (tgt.x + 0.26 * fill_side, tgt.y + 0.30, tgt.z + 0.12), tgt, 0.18, 1.6 * back,
               blackbody_rgb(4800), spread=50)
    area_light('front', (tgt.x + 0.30 * fill_side, tgt.y - 0.45, tgt.z + 0.35), tgt, 0.9, 1.0 * k,
               blackbody_rgb(5600), spread=80)
    area_light('top', (tgt.x, tgt.y, tgt.z + 0.55), tgt, 0.6, 0.35 * k, blackbody_rgb(5600), spread=60)
    area_light('bg', (0.0, -0.1, 0.9), bg, 1.2, bg_power, blackbody_rgb(4500), spread=60)


def studio_lights(tgt, k=1.0, rim=1.0, warm=5600, bg=(0, 0.55, 0.25), bg_power=9.0):
    area_light('key', (tgt.x - 0.42, tgt.y - 0.26, tgt.z + 0.46), tgt, 0.5, 1.6 * k, blackbody_rgb(warm), spread=70)
    area_light('fill', (tgt.x + 0.55, tgt.y - 0.30, tgt.z + 0.20), tgt, 0.9, 0.55 * k, blackbody_rgb(5000),
               glossy=False)
    # rims from behind: light passes through the thin frosted edges -> glowing rim
    rz = TUNE.get('rimz', 0.10)
    area_light('rim_l', (tgt.x - 0.28, tgt.y + 0.36, tgt.z + rz), tgt, 0.25, 5.0 * rim * TUNE.get('rimk', 1), blackbody_rgb(5200),
               spread=45)
    area_light('rim_r', (tgt.x + 0.30, tgt.y + 0.30, tgt.z + rz * 0.8), tgt, 0.22, 3.5 * rim * TUNE.get('rimk', 1), blackbody_rgb(4800),
               spread=45)
    area_light('top', (tgt.x, tgt.y + 0.05, tgt.z + 0.6), tgt, 0.5, 0.6 * k, blackbody_rgb(5600), spread=60)
    area_light('bg', (0.0, -0.1, 0.9), bg, 1.2, bg_power, blackbody_rgb(4500), spread=60)


# ------------------------------------------------------------------------------------------
# shots
ANNOT = []


def shot_hero(social=False):
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep(TUNE.get('paper', '#DCD2C5') if isinstance(TUNE.get('paper'), str) else ('#D8CDBF' if not TUNE.get('darkbg') else '#3A3A3C'), wall_y=0.5)
    p = build_pebble('hero', '#F4F6F8', 'eyes_cream_look')
    lay_flat(p, 0, 0, -8)
    strap_flat('hero', p, L_loop=112, W_loop=50, bend=-0.30, col='#BFAE95')
    tgt = world_point(p, (0, -2, 2))
    focus = world_point(p, (0, -6, 10))
    if social:
        cam = camera(tgt + Vector((0.07, -0.24, 0.24)), tgt, lens=58, fstop=8.0, focus=focus,
                     shift=(-0.03, 0.10))
    else:
        cam = camera(tgt + Vector((0.085, -0.25, 0.185)), tgt, lens=TUNE.get('lens', 55), fstop=8.0, focus=focus, shift=(TUNE.get('sx', -0.0), TUNE.get('sy', 0.0)))
    flag(cam, tgt)
    lens_card(p, cam)
    if TUNE.get('darkfield', 1):
        dark_field(world_point(p, (0, 0, 0)), cam)
    if TUNE.get('glassl', 1):
        glass_lights(tgt, TUNE.get('keyk', 1.0), TUNE.get('backk', 1.0), bg_power=TUNE.get('bgp', 7.0))
    else:
        studio_lights(tgt, TUNE.get('keyk', 1.0), bg_power=TUNE.get('bgp', 9.0))
    return sc


def shot_social():
    return shot_hero(True)


def shot_os():
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#E2D8CB', wall_y=0.45)
    p = build_pebble('os', '#F4F6F8', 'ui_reminder', eye_strength=2.6)
    dock(p, 'os', 0, 0, -14, 20.0)
    tgt = world_point(p, (1.0, 0.5, 9))
    focus = world_point(p, (0, 4, 10))
    cam = camera(tgt + Vector((0.10, -0.29, 0.07)), tgt + Vector((0.006, 0, -0.008)), lens=105, fstop=5.6,
                 focus=focus)
    flag(cam, tgt)
    V1['protect_screens'](cam, tgt, 0.35, 0.03)
    lens_card(p, cam, up_deg=14, side_deg=14, tilt_deg=-28, strength=4.0)
    glass_lights(tgt, 0.9, 1.0, bg_power=7.0)
    return sc


COLORWAYS = [  # name, body tint, screen, strap, dark
    ('cloud', '#F4F6F8', 'eyes_cream_look', '#D8CEC0', False),
    ('sky', '#BFD9F0', 'eyes_ice_look', '#8FA9C4', False),
    ('peach', '#F6CBB5', 'eyes_peach_look', '#D9A58C', False),
    ('graphite', '#6A6F78', 'eyes_cream_front', '#3E4046', True),
    ('lilac', '#D7CBF0', 'eyes_lilac_look', '#A898C9', False),
]


def shot_colors():
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#DDD3C6', wall_y=0.7)
    # two staggered rows (reads left to right: cloud, sky, peach, graphite, lilac)
    xs = [-0.078, -0.039, 0.0, 0.039, 0.078]
    ys = [0.034, -0.036, 0.036, -0.034, 0.032]
    yaws = [6, -4, 3, -7, 5]
    peb = []
    for i, (name, tint, scr, strap, dark) in enumerate(COLORWAYS):
        p = build_pebble(name, tint, scr, dark=dark, metal='alu_dark' if dark else 'alu')
        lay_flat(p, xs[i], ys[i], yaws[i])
        peb.append(p)
    tgt = Vector((0, 0.0, 0.012))
    cam = camera((0.0, -0.40, 0.52), tgt, lens=72, fstop=11.0, focus=Vector((0, 0.0, 0.016)), shift=(0, 0.0))
    flag(cam, tgt, size=(4, 3))
    for p in peb:
        lens_card(p, cam, up_deg=16, side_deg=-17, strip=(0.008, 0.08), strength=2.5)
    glass_lights(tgt, 1.3, 1.4, bg_power=7.0)
    return sc


def shot_scale():
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#E6DDD1', wall_y=0.6)
    # v1 charm (coin, 58 mm, 18.8 mm) from the v1 script, lying flat on its back
    V1['SHAPE_CFG']['coin']['k'] = 0.2104 * 58.0 / 52.0
    V1['H_HALF'] = 9.4
    V1['_SHAPES'] = None
    a1 = V1['build_amulet']('v1', 'coin', '#F3F5F7', 'cream_look', eye_strength=2.8, glow_w=0.0,
                            ring_tilt=-90.0)
    a1.location = (-0.052, 0.004, (9.4 + 0.35) * MM)
    a1.rotation_euler = (0, 0, math.radians(12))
    p = build_pebble('v2', '#F4F6F8', 'eyes_cream_look')
    lay_flat(p, 0.036, 0.0, -8)
    tgt = Vector((-0.008, -0.006, 0.008))
    cam = camera((0.0, -0.20, 0.46), tgt, lens=78, fstop=11.0, focus=Vector((-0.008, 0, 0.012)), shift=(0, -0.03))
    flag(cam, tgt)
    lens_card(p, cam, up_deg=15, side_deg=-15, strip=(0.01, 0.1), strength=4.0)
    glass_lights(tgt, 1.0, 1.0, bg_power=7.0)
    # annotation anchors: diameter ends of each device (world), projected in main()
    for key, par, half_w, y_off in (('v1', a1, 29.0, -38.0), ('v2', p, 35.0, -41.0)):
        c = world_point(par, (0, 0, 0))
        c = Vector((c.x, c.y + y_off * MM, 0.0))
        ANNOT.append(dict(key=key, a=c - Vector((half_w * MM, 0, 0)), b=c + Vector((half_w * MM, 0, 0))))
    ANNOT[0]['label'] = 'SOUL v1 · Ø58 mm'
    ANNOT[1]['label'] = 'SOUL v2 · 70 × 64 mm'
    return sc


def shot_night():
    sc = reset()
    world_color((0.02, 0.03, 0.06), 0.35)
    table = rounded_box('table', 0.9, 0.5, 0.03, 0.006)
    table.location = (0, 0.08, -0.015)
    assign(table, mat_wood('walnut', srgb('#3B2416'), srgb('#1C0F08'), 0.35, 5.0))
    plane('wall', (3, 2), (0, 0.42, 0.5), (math.radians(90), 0, 0), mat_diffuse('wall', srgb('#2A2E38'), 0.9, 0.1))
    p = build_pebble('night', '#F4F6F8', 'eyes_amber_sleepy', eye_strength=3.6, glow_w=0.035, glow_col=2200,
                     inner_light=0.06)
    dock(p, 'night', 0, 0, -16, 20.0)
    tgt = world_point(p, (0, 0, 0))
    focus = world_point(p, (-4, 2, 10))
    cam = camera(tgt + Vector((0.17, -0.42, 0.075)), tgt + Vector((0.012, 0, 0.006)), lens=85, fstop=2.8, focus=focus)
    # the warm spill the glowing body throws on the table and the wall
    area_light('spill', world_point(p, (0, -10, 20)), world_point(p, (0, -40, 60)), 0.03, 0.5,
               blackbody_rgb(2200), 'DISK', spread=150)
    area_light('spill_back', world_point(p, (0, -6, -18)), world_point(p, (0, -40, -60)), 0.03, 0.35,
               blackbody_rgb(2200), 'DISK', spread=150)
    area_light('moon', (-0.9, 0.05, 0.6), tgt, 0.6, 14, blackbody_rgb(8000), 'RECTANGLE', 0.3)
    area_light('moon_rim', (0.3, 0.6, 0.35), tgt, 0.3, 2.0, blackbody_rgb(8000))
    book = rounded_box('book', 0.16, 0.22, 0.025, 0.002)
    book.location = (-0.17, 0.14, 0.0125)
    book.rotation_euler = (0, 0, math.radians(-12))
    assign(book, mat_diffuse('book', srgb('#6B2E2A'), 0.6, 0.3))
    book2 = rounded_box('book2', 0.15, 0.21, 0.02, 0.002)
    book2.location = (-0.16, 0.15, 0.035)
    book2.rotation_euler = (0, 0, math.radians(-5))
    assign(book2, mat_diffuse('book2', srgb('#7A6A55'), 0.7, 0.3))
    # a glass of water behind, catching the amber light
    gl = revolve('glass', [(0, 1.5), (30, 1.5), (31.5, 3), (33, 95), (31.2, 95), (29.8, 4.5), (0, 4.5)], seg=96)
    gl.location = (0.12, 0.13, 0)
    assign(gl, mat_glass('glass', 0.02, 1.5))
    return sc


# ---- hand ---------------------------------------------------------------------------------
def build_hand(name, loc, yaw_deg=0.0):
    """Stylised right hand, palm up (mesh from hand_sdf.py: tex/hand.npz, mm)."""
    path = os.path.join(TEX, 'hand.npz')
    if not os.path.exists(path):
        import subprocess
        subprocess.run(['python3', os.path.join(HERE, 'hand_sdf.py'), path], check=True)
    D = np.load(path)
    v = D['verts'].astype(float) * MM
    f = D['faces']
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(v))
    me.vertices.foreach_set('co', v.ravel())
    me.loops.add(f.size)
    me.loops.foreach_set('vertex_index', f.ravel())
    me.polygons.add(len(f))
    me.polygons.foreach_set('loop_start', np.arange(0, f.size, 3))
    me.polygons.foreach_set('loop_total', np.full(len(f), 3))
    me.update()
    me.validate()
    import bmesh as _bm
    bm = _bm.new()
    bm.from_mesh(me)
    _bm.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    sm = ob.modifiers.new('smooth', 'CORRECTIVE_SMOOTH') if False else ob.modifiers.new('smooth', 'SMOOTH')
    sm.factor = 0.5
    sm.iterations = 4
    ob.location = loc
    ob.rotation_euler = (0, 0, math.radians(yaw_deg))
    assign(ob, mat_skin('skin'))
    return ob


def shot_hand():
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#D3C7B8', wall_y=0.55)
    hand = build_hand('hand', (0.0, 0.0, 0.030), 18.0)
    p = build_pebble('hand', '#F4F6F8', 'eyes_cream_look')
    p.location = (0.004, 0.012, 0.030 + 0.0125 + (P2['HB'] - 1.5) * MM)
    p.rotation_euler = (math.radians(16), math.radians(-6), math.radians(12))
    tgt = world_point(p, (0, 0, 0))
    focus = world_point(p, (0, -6, 10))
    cam = camera(tgt + Vector((0.17, -0.40, 0.17)), tgt + Vector((-0.006, 0.035, 0.004)), lens=62, fstop=7.1,
                 focus=focus)
    flag(cam, tgt)
    lens_card(p, cam)
    glass_lights(tgt, 0.9, 1.0, bg_power=6.0)
    POST['exposure'] = -0.45
    return sc


def shot_turntable():
    sc = shot_hero()
    # remove the floor strap for the spin (it would sweep through the floor loop), keep the pebble
    for ob in list(bpy.data.objects):
        if ob.name.startswith('hero_strap') or ob.name.startswith('hero_ferrule'):
            bpy.data.objects.remove(ob)
    p = bpy.data.objects['pebble_hero']
    fr = 150
    sc.frame_start, sc.frame_end = 1, fr
    for f in (1, fr + 1):
        sc.frame_set(f)
        p.rotation_euler = (0, 0, math.radians(-8 + (f - 1) * 360.0 / fr))
        p.keyframe_insert('rotation_euler', frame=f)
    for fc in p.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    return sc


SHOTS = {
    'hero': (shot_hero, 1600, 1200, 192),
    'social': (shot_social, 1080, 1920, 192),
    'hand': (shot_hand, 1600, 1200, 192),
    'scale': (shot_scale, 1600, 1200, 160),
    'os': (shot_os, 1600, 1200, 192),
    'colors': (shot_colors, 1600, 1200, 192),
    'night': (shot_night, 1600, 1200, 256),
    'turntable': (shot_turntable, 540, 540, 40),
}


def main():
    fn, W, H, S = SHOTS[ARGS.shot]
    t0 = time.time()
    sc = fn()
    if os.environ.get('DBG'):          # debugging hook: python snippet run after the scene is built
        exec(open(os.environ['DBG']).read())
    sc.render.resolution_x = ARGS.w or W
    sc.render.resolution_y = ARGS.h or H
    sc.render.resolution_percentage = 50 if ARGS.preview else 100
    sc.cycles.samples = ARGS.samples or (max(24, S // 4) if ARGS.preview else S)
    sc.render.use_persistent_data = True
    stem = ARGS.shot + ('_preview' if ARGS.preview else '') + (('_' + ARGS.tag) if ARGS.tag else '')
    base = os.path.join(ARGS.tmp, stem)
    for f in __import__('glob').glob(base + '_*_????.exr'):
        os.remove(f)
    V1['setup_compositor'](sc, base)
    sc.render.filepath = os.path.join(ARGS.tmp, 'composite_' + stem + '_')
    if ARGS.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ARGS.tmp, stem + '.blend'))
    w = int(sc.render.resolution_x * sc.render.resolution_percentage / 100)
    h = int(sc.render.resolution_y * sc.render.resolution_percentage / 100)
    annot = []
    for a in ANNOT:
        pa = world_to_camera_view(sc, sc.camera, a['a'])
        pb = world_to_camera_view(sc, sc.camera, a['b'])
        annot.append(dict(label=a['label'], a=[pa.x, 1 - pa.y], b=[pb.x, 1 - pb.y]))
    if ARGS.shot == 'turntable':
        if ARGS.frames:
            sc.frame_start, sc.frame_end = [int(v) for v in ARGS.frames.split(':')]
        frames = list(range(sc.frame_start, sc.frame_end + 1))
        bpy.ops.render.render(animation=True)
    else:
        frames = [sc.frame_current]
        bpy.ops.render.render(write_still=False)
    meta = dict(POST, w=w, h=h, frames=frames, base=base, stem=stem, samples=sc.cycles.samples,
                annot=annot, seconds=round(time.time() - t0, 1))
    json.dump(meta, open(base + '.json', 'w'), indent=1)
    print('RENDERED', json.dumps(meta))


main()
