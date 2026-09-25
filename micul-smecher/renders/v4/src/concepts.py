"""concepts.py -- SOUL concept round (A LENS, B ORB, C EVE, D SOUL hybrid), Blender Cycles.

Reuses every helper of soul_scene.py (materials, lights, flags, eyes texture, render/EXR pipeline) and
adds the four concept bodies. Same post.py (OIDN + AgX) afterwards.

    blender -b --factory-startup --python concepts.py -- --shot A_lens [--preview] [--samples N] [--tmp DIR]
Shots: A_lens A_desk B_orb B_desk C_eve C_desk D_soul D_dock D_back lineup
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(_HERE, 'soul_scene.py')).read()
exec(compile(_src[:_src.rindex('\nmain()')], os.path.join(_HERE, 'soul_scene.py'), 'exec'), globals())

# ==========================================================================================
# materials
ORANGE = srgb('#D97757')


def _noise_bump(nt, p, scale, strength, dist=0.00002):
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = scale
    nz.inputs['Detail'].default_value = 3
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = strength
    bp.inputs['Distance'].default_value = dist
    nt.links.new(nz.outputs['Fac'], bp.inputs['Height'])
    nt.links.new(bp.outputs[0], p.inputs['Normal'])
    return tc, bp


def mat_blast(name, col=(0.60, 0.58, 0.55), rough=0.36, etch=None):
    """Bead-blasted titanium / aluminium: satin metal with a fine grain. etch=(angle0, z0_mm) adds a
    laser-etched micro 'SOUL' on the cylindrical side (object space, axis z)."""
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', (*col, 1))
    set_in(p, 'Metallic', 1.0)
    set_in(p, 'Roughness', rough)
    tc, bp = _noise_bump(nt, p, 25000.0, 0.12)
    if etch:
        a0, z0 = etch
        sep = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(tc.outputs['Object'], sep.inputs[0])
        at = nt.nodes.new('ShaderNodeMath')
        at.operation = 'ARCTAN2'
        nt.links.new(sep.outputs[1], at.inputs[0])
        nt.links.new(sep.outputs[0], at.inputs[1])
        u = nt.nodes.new('ShaderNodeMath')
        u.operation = 'MULTIPLY_ADD'           # u = (ang - a0) * k + 0.5 ; letters ~ 9 mm wide on R30
        u.inputs[1].default_value = -1.0 / 0.30
        u.inputs[2].default_value = 0.5 + a0 / 0.30
        nt.links.new(at.outputs[0], u.inputs[0])
        v = nt.nodes.new('ShaderNodeMath')
        v.operation = 'MULTIPLY_ADD'           # 2.2 mm tall band
        v.inputs[1].default_value = 1.0 / 0.0022
        v.inputs[2].default_value = 0.5 - z0 * MM / 0.0022
        nt.links.new(sep.outputs[2], v.inputs[0])
        cmb = nt.nodes.new('ShaderNodeCombineXYZ')
        nt.links.new(u.outputs[0], cmb.inputs[0])
        nt.links.new(v.outputs[0], cmb.inputs[1])
        img = nt.nodes.new('ShaderNodeTexImage')
        img.image = bpy.data.images.load(os.path.join(TEX, 'micro_soul.png'), check_existing=True)
        img.image.colorspace_settings.name = 'Non-Color'
        img.extension = 'CLIP'
        nt.links.new(cmb.outputs[0], img.inputs[0])
        mc = nt.nodes.new('ShaderNodeMix')
        mc.data_type = 'RGBA'
        nt.links.new(img.outputs['Color'], mc.inputs['Factor'])
        mc.inputs['A'].default_value = (*col, 1)
        mc.inputs['B'].default_value = (col[0] * 0.35, col[1] * 0.35, col[2] * 0.35, 1)
        nt.links.new(mc.outputs['Result'], p.inputs['Base Color'])
        mr = nt.nodes.new('ShaderNodeMix')
        mr.data_type = 'FLOAT'
        nt.links.new(img.outputs['Color'], mr.inputs['Factor'])
        mr.inputs['A'].default_value = rough
        mr.inputs['B'].default_value = 0.6
        nt.links.new(mr.outputs['Result'], p.inputs['Roughness'])
    return m


def mat_polish(name, col=(0.62, 0.60, 0.57), rough=0.035):
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', (*col, 1))
    set_in(p, 'Metallic', 1.0)
    set_in(p, 'Roughness', rough)
    return m


def mat_ceramic(name, col='#F2F1EE', rough=0.12, coat=1.0):
    """Polished zirconia / porcelain: dense white body under a glassy coat."""
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', srgb(col))
    set_in(p, 'Roughness', rough)
    set_in(p, 'Subsurface Weight', 0.15)
    set_in(p, 'Subsurface Scale', 0.0006)
    set_in(p, 'Coat Weight', coat)
    set_in(p, 'Coat Roughness', 0.015)
    set_in(p, 'Coat IOR', 1.6)
    return m


def mat_clear_glass(name, tint=(0.97, 0.99, 1.0), rough=0.0):
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', (*tint, 1))
    set_in(p, 'Roughness', rough)
    set_in(p, 'IOR', 1.52)
    set_in(p, 'Transmission Weight', 1.0)
    return m


def mat_glow_frost(name, col_rgb, strength, tint='#F4F4F2', dens=10.0, rough=0.45):
    m = mat_frosted(name, tint, rough=rough, dens=dens)
    p = m.node_tree.nodes['Principled BSDF']
    set_in(p, 'Emission Color', (*col_rgb, 1))
    set_in(p, 'Emission Strength', strength)
    return m


# ==========================================================================================
# lathe with per-band materials and a coin-edge knurl
def lathe(name, prof, seg=256, closed=True, knurl_n=0, knurl_amp=0.0, axis='z'):
    """prof: list of (r, h, knurl_weight, mat_index) in mm. Band i (point i -> i+1) gets mat_index of point i.
    closed=True joins the last point back to the first (ring-like solid); otherwise r==0 ends become caps."""
    t = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    rid = np.zeros(seg)
    if knurl_n:
        ph = (knurl_n * t) % (2 * np.pi)
        rid = np.abs(ph - np.pi) / np.pi            # triangle 1..0..1
        rid = np.clip(1.25 - 1.25 * rid, 0, 1) ** 1.2  # sharp V grooves with flats
    verts, faces, mids = [], [], []
    pts = list(prof)
    caps = []
    if not closed:
        if pts[0][0] == 0:
            caps.append(('s', pts.pop(0)))
        if pts[-1][0] == 0:
            caps.append(('e', pts.pop(-1)))
    N = len(pts)
    for (r, h, kw, mi) in pts:
        rr = r - knurl_amp * kw * rid
        for j in range(seg):
            x, y = rr[j] * math.cos(t[j]), rr[j] * math.sin(t[j])
            verts.append((x * MM, y * MM, h * MM) if axis == 'z' else (x * MM, h * MM, y * MM))
    nb = N if closed else N - 1
    for i in range(nb):
        i2 = (i + 1) % N
        for j in range(seg):
            j2 = (j + 1) % seg
            faces.append((i * seg + j, i * seg + j2, i2 * seg + j2, i2 * seg + j))
            mids.append(pts[i][3])
    for kind, (r, h, kw, mi) in caps:
        c = len(verts)
        verts.append((0, 0, h * MM) if axis == 'z' else (0, h * MM, 0))
        base = 0 if kind == 's' else (N - 1) * seg
        for j in range(seg):
            faces.append((c, base + (j + 1) % seg, base + j))
            mids.append(mi)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for p, mi in zip(me.polygons, mids):
        p.use_smooth = True
        p.material_index = mi
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def set_mats(ob, mats):
    ob.data.materials.clear()
    for m in mats:
        ob.data.materials.append(m)


def arc(cx, cz, r, a0, a1, n=6, kw=0, mi=0):
    return [(cx + r * math.cos(a), cz + r * math.sin(a), kw, mi) for a in np.linspace(a0, a1, n)]


def glass_eye(tag, r_glass, z_edge, z_top, z_floor, eyes='cream_look', strength=2.6, r_screen=22.0, seg=256):
    """Black domed cover glass over the emissive round AMOLED (eyes from eyes.py)."""
    h = z_top - z_edge
    Rs = (r_glass ** 2 + h ** 2) / (2 * h)
    prof = [(0, z_top)]
    for rr in np.linspace(0, r_glass - 0.35, 44)[1:]:
        prof.append((rr, z_top - (Rs - math.sqrt(Rs * Rs - rr * rr))))
    ze = prof[-1][1]
    for a in np.linspace(math.pi / 2, 0, 6)[1:]:
        prof.append((r_glass - 0.35 + 0.35 * math.cos(a), ze - 0.35 + 0.35 * math.sin(a)))
    prof += [(r_glass, z_floor + 0.3), (r_glass - 0.3, z_floor), (0, z_floor)]
    ob = revolve(tag + '_glass', prof, seg=seg)
    assign(ob, mat_screen('screen_' + tag, os.path.join(TEX, 'eyes_%s.png' % eyes), strength, r_screen=r_screen))
    return ob


def parent_all(par, obs):
    for ob in obs:
        ob.parent = par


def new_par(name):
    par = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(par)
    return par


# ==========================================================================================
# A · LENS  (Ø60 × 16, bead-blasted Ti, knurled rotating bezel, razor halo line, strap lug)
def build_lens(tag='A', eyes='cream_look', ti=(0.50, 0.49, 0.47), glow=(1.0, 0.78, 0.52), glow_k=1.0,
               lug=True, r_glass=24.5, halo_w=0.55, back='glass', orange_dot=False, halo_frost=False):
    blast = mat_blast('blast_' + tag, ti, etch=(-0.55, -1.2))
    if tag.startswith('A'):
        pass
    pol = mat_polish('polish_' + tag, ti)
    par = new_par('lens_' + tag)
    obs = []
    R = 30.2 if r_glass > 25 else 30.0
    rb_in = r_glass + halo_w + 0.05          # bezel inner radius
    # mid-case: rounded back edge, straight side, flat seat for the bezel
    case = [(0, -6.0, 0, 0), (23.2, -6.0, 0, 0), (23.2, -7.05, 0, 0), (24.0, -7.15, 0, 0)]
    case += arc(R - 2.2, -5.0, 2.2, -math.pi / 2, 0, 10)
    case += [(R, 2.2, 0, 0), (R - 0.35, 2.55, 0, 1), (R - 0.7, 2.6, 0, 0), (rb_in, 2.6, 0, 0), (rb_in, 0.0, 0, 0),
             (0, 0.0, 0, 0)]
    c = lathe(tag + '_case', case, seg=256, closed=False)
    set_mats(c, [blast, pol])
    obs.append(c)
    # rotating bezel: coin-edge knurl on the side, mirror-polished inner top chamfer
    zb0, zb1 = 2.75, 6.35
    bez = [(rb_in, zb0, 0, 0), (R - 0.25, zb0, 0, 0), (R, zb0 + 0.25, 0, 0)]
    for z in np.linspace(zb0 + 0.45, zb1 - 0.9, 10):
        bez.append((R, z, 1, 0))
    bez += [(R, zb1 - 0.65, 0, 0), (R - 0.25, zb1 - 0.2, 0, 0), (R - 0.7, zb1, 0, 0), (rb_in + 1.5, zb1, 0, 1),
            (rb_in + 0.15, zb1 - 1.25, 0, 1), (rb_in, zb1 - 1.35, 0, 0)]
    b = lathe(tag + '_bezel', bez, seg=960, closed=True, knurl_n=180, knurl_amp=0.32)
    set_mats(b, [blast, pol])
    obs.append(b)
    # halo light line between glass and bezel
    hz0, hz1 = 1.0, zb1 - 1.45
    hl = revolve_closed(tag + '_halo', [(r_glass + 0.03, hz0), (rb_in - 0.03, hz0), (rb_in - 0.03, hz1),
                                         (r_glass + 0.03, hz1)], seg=256)
    if halo_frost:
        assign(hl, mat_glow_frost('halo_' + tag, glow, 1.2 * glow_k, dens=8))
    else:
        assign(hl, mat_emit('halo_' + tag, glow, 6.0 * glow_k))
    obs.append(hl)
    # the eye
    g = glass_eye(tag, r_glass, zb1 - 0.25, 8.0, 0.4, eyes)
    obs.append(g)
    # back
    if back == 'zirconia':
        bk = revolve(tag + '_back', [(0, -8.1), (12, -7.95), (20, -7.6), (22.8, -7.3), (23.15, -7.05), (23.15, -6.1),
                                     (0, -6.1)], seg=192)
        assign(bk, mat_zirconia_back(tag))
    else:
        bk = revolve(tag + '_back', [(0, -8.0), (22.8, -7.3), (23.15, -7.05), (23.15, -6.1), (0, -6.1)], seg=192)
        assign(bk, mat_diffuse('backglass_' + tag, (0.01, 0.01, 0.012, 1), 0.08, 0.5))
    obs.append(bk)
    if orange_dot:
        dot = revolve(tag + '_dot', [(0, zb1 + 0.03), (0.75, zb1 + 0.02), (0.8, zb1 - 0.3), (0, zb1 - 0.3)], seg=32)
        dot.location = (0, (R - 1.6) * MM, 0)
        m, nt, p, out = new_mat('orange')
        set_in(p, 'Base Color', ORANGE)
        set_in(p, 'Roughness', 0.25)
        set_in(p, 'Coat Weight', 1.0)
        assign(dot, m)
        obs.append(dot)
    if lug:
        # small detachable Ti lug at 12 o'clock: a flat D-loop hinged on two pins in the case side
        pts = []
        for a in np.linspace(math.pi, 0, 40):
            pts.append((5.2 * math.cos(a), R + 2.2 + 3.2 * math.sin(a), -2.0))
        pts = [(-5.2, R - 0.6, -2.0)] + pts + [(5.2, R - 0.6, -2.0)]
        cu = bpy.data.curves.new(tag + '_lug', 'CURVE')
        cu.dimensions = '3D'
        cu.bevel_depth = 1.25 * MM
        cu.bevel_resolution = 6
        cu.use_fill_caps = True
        sp = cu.splines.new('POLY')
        sp.points.add(len(pts) - 1)
        for p_, q in zip(sp.points, pts):
            p_.co = (q[0] * MM, q[1] * MM, q[2] * MM, 1)
        lg = bpy.data.objects.new(tag + '_lug', cu)
        bpy.context.scene.collection.objects.link(lg)
        assign(lg, blast)
        obs.append(lg)
        for sx in (-1, 1):
            pin = revolve(tag + '_pin', [(0, -1.5), (1.5, -1.5), (1.7, -1.2), (1.7, 1.2), (1.5, 1.5), (0, 1.5)],
                          seg=48, axis='y')
            pin.rotation_euler = (0, 0, math.radians(90))
            pin.location = (sx * 5.2 * MM, (R - 0.8) * MM, -2.0 * MM)
            assign(pin, pol)
            obs.append(pin)
    parent_all(par, obs)
    par['R'] = R
    par['z_top'] = 8.0
    par['z_bot'] = -8.1
    return par


def mat_zirconia_back(tag):
    """White polished zirconia caseback with the laser-etched birth ring (reuses caseback_engrave.png)."""
    m, nt, p, out = new_mat('zback_' + tag)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    s = 1.0 / (2 * 20.0 * MM)
    mp.inputs['Scale'].default_value = (-s, s, 1)
    mp.inputs['Location'].default_value = (0.5, 0.5, 0)
    img = nt.nodes.new('ShaderNodeTexImage')
    img.image = bpy.data.images.load(os.path.join(TEX, 'caseback_engrave.png'), check_existing=True)
    img.image.colorspace_settings.name = 'Non-Color'
    img.extension = 'CLIP'
    nt.links.new(tc.outputs['Object'], mp.inputs[0])
    nt.links.new(mp.outputs[0], img.inputs[0])
    cm = nt.nodes.new('ShaderNodeMix')
    cm.data_type = 'RGBA'
    nt.links.new(img.outputs['Color'], cm.inputs['Factor'])
    cm.inputs['A'].default_value = srgb('#F3F2EF')
    cm.inputs['B'].default_value = srgb('#8E8B86')
    nt.links.new(cm.outputs['Result'], p.inputs['Base Color'])
    rm = nt.nodes.new('ShaderNodeMix')
    rm.data_type = 'FLOAT'
    nt.links.new(img.outputs['Color'], rm.inputs['Factor'])
    rm.inputs['A'].default_value = 0.08
    rm.inputs['B'].default_value = 0.55
    nt.links.new(rm.outputs['Result'], p.inputs['Roughness'])
    cw = nt.nodes.new('ShaderNodeMath')
    cw.operation = 'SUBTRACT'
    cw.inputs[0].default_value = 1.0
    nt.links.new(img.outputs['Color'], cw.inputs[1])
    nt.links.new(cw.outputs[0], p.inputs['Coat Weight'])
    set_in(p, 'Coat Roughness', 0.015)
    set_in(p, 'Subsurface Weight', 0.12)
    set_in(p, 'Subsurface Scale', 0.0006)
    return m


# ==========================================================================================
# B · ORB  (Ø60 × 23 optical glass dome, glowing inside, polished steel spine)
def build_orb(tag='B', eyes='cream_look', glow=(1.0, 0.80, 0.56), glow_k=1.0):
    """Clear optical-glass puck (Ø62 × 23): the black eye floats in it; through the clear flank you see
    the designed inner plates and a ring of light; the back is lit from inside; thin polished steel spine."""
    par = new_par('orb_' + tag)
    obs = []
    R = 31.0
    steel = mat_polish('steel_' + tag, (0.82, 0.82, 0.84), 0.03)
    clear = mat_clear_glass('clear_' + tag, (0.96, 0.985, 1.0))
    # solid clear body: domed front (z 14), rounded flank, domed back (z -9)
    prof = [(0, -9.0)]
    for a in np.linspace(-math.pi / 2, 0, 24)[1:]:
        prof.append((R * math.cos(a) ** 0.55, -9.0 * math.sin(-a) ** 1.6 if a < 0 else 0.0))
    for a in np.linspace(0, math.pi / 2, 40)[1:]:
        prof.append((R * math.cos(a) ** 0.55, 14.0 * math.sin(a) ** 1.35))
    prof[-1] = (0, 14.0)
    dm = revolve(tag + '_body', prof, seg=256)
    assign(dm, clear)
    obs.append(dm)
    # thin polished steel spine at the equator (a flat band sitting in the flank)
    sp = revolve_closed(tag + '_spine', [(R - 0.9, -0.55), (R + 0.12, -0.55), (R + 0.12, 0.55), (R - 0.9, 0.55)],
                        seg=256)
    assign(sp, steel)
    obs.append(sp)
    # the black eye module (Ø49 domed black glass + Ø44 screen) floating in the glass
    eye = glass_eye(tag, 24.5, 4.0, 5.6, 2.6, eyes, strength=2.4)
    obs.append(eye)
    bz = revolve_closed(tag + '_ebz', [(24.5, 2.5), (25.0, 2.5), (25.0, 4.2), (24.5, 4.2)], seg=192)
    assign(bz, steel)
    obs.append(bz)
    # designed internals (Nothing-style cover plates), visible through the clear flank
    dark = mat_blast('plate_' + tag, (0.16, 0.16, 0.17), 0.35)
    pl = revolve_closed(tag + '_plate', [(4.0, 1.2), (25.5, 1.2), (25.5, 2.4), (4.0, 2.4)], seg=192)
    assign(pl, dark)
    obs.append(pl)
    ring = revolve_closed(tag + '_ring', [(27.2, -0.25), (27.7, -0.25), (27.7, 0.25), (27.2, 0.25)], seg=192)
    assign(ring, mat_emit('lring_' + tag, glow, 12.0 * glow_k))
    obs.append(ring)
    for i in range(12):
        a = 2 * math.pi * i / 12 + 0.26
        bx = rounded_box(tag + '_cell%d' % i, 4.2 * MM, 2.4 * MM, 1.6 * MM, 0.4 * MM, 2)
        bx.location = (22.5 * math.cos(a) * MM, 22.5 * math.sin(a) * MM, -1.2 * MM)
        bx.rotation_euler = (0, 0, a)
        assign(bx, steel if i % 3 == 0 else dark)
        obs.append(bx)
    # battery / board stack as a graphite puck with machined rings
    st = revolve(tag + '_stack', [(0, -5.2), (20.5, -5.2), (21.0, -4.7), (21.0, 0.8), (0, 0.8)], seg=192)
    assign(st, dark)
    obs.append(st)
    for rr in (9.0, 14.0, 18.5):
        rg = revolve_closed(tag + '_mr', [(rr, -5.35), (rr + 0.5, -5.35), (rr + 0.5, -5.15), (rr, -5.15)], seg=192)
        assign(rg, steel)
        obs.append(rg)
    # frosted diffuser disc at the back, glowing (the whole body glows softly from within)
    df = revolve(tag + '_diff', [(0, -7.6), (24.0, -7.1), (24.0, -6.5), (0, -6.5)], seg=192)
    assign(df, mat_glow_frost('diff_' + tag, glow, 0.5 * glow_k, dens=6))
    obs.append(df)
    parent_all(par, obs)
    par['R'] = R
    par['z_top'] = 14.0
    par['z_bot'] = -9.0
    return par


# ==========================================================================================
# C · EVE  (62 W × 72 H × 48 D glossy white zirconia egg, black glass visor, weighted base + light ring)
EGG = dict(R=31.0, H=72.0, hc=40.0, a_lo=40.0, a_hi=32.5, depth=48.0 / 62.0, h0=3.0)


def egg_r(h):
    e = EGG
    a = e['a_lo'] if h < e['hc'] else e['a_hi']
    q = 1 - ((h - e['hc']) / a) ** 2
    return e['R'] * math.sqrt(max(q, 0.0)) ** 0.92 if q > 0 else 0.0


def egg_point(h, phi, off=0.0):
    """phi = 0 -> front (+z local), measured towards +x."""
    r = egg_r(h)
    x = r * math.sin(phi)
    z = r * math.cos(phi) * EGG['depth']
    # outward normal (approx): radial in the scaled section
    n = Vector((math.sin(phi) / 1.0, 0, math.cos(phi) / EGG['depth'])).normalized()
    return Vector((x, h, z)) + n * off


def build_eve(tag='C', eyes='cream_look', glow=(1.0, 0.82, 0.6), glow_k=1.0):
    par = new_par('eve_' + tag)
    obs = []
    cer = mat_ceramic('zirconia_' + tag, '#F4F3F0')
    # body: revolve around local y, then squash depth
    hs = [EGG['h0']] + list(np.linspace(EGG['h0'] + 0.2, EGG['hc'] + EGG['a_hi'] - 0.05, 120))
    prof = [(0, EGG['h0'])]
    for h in hs[1:]:
        prof.append((max(egg_r(h), 0.5), h))
    r_base = egg_r(EGG['h0'] + 0.2)
    prof.insert(1, (r_base - 1.0, EGG['h0']))
    prof.append((0, EGG['hc'] + EGG['a_hi']))
    body = revolve(tag + '_body', prof, seg=256, axis='y')
    body.scale = (1, 1, EGG['depth'])
    assign(body, cer)
    obs.append(body)
    # visor: black glass on the front, elliptical in (phi, h), a thin solid shell
    hc, hh, pm = 44.0, 18.5, math.radians(66)
    n_r, n_a = 24, 160
    rings_o, rings_i = [], []
    for k in range(1, n_r + 1):
        rho = k / n_r
        ro, ri = [], []
        for j in range(n_a):
            psi = 2 * math.pi * j / n_a
            phi = pm * rho * math.cos(psi)
            h = hc + hh * rho * math.sin(psi)
            ro.append(tuple(egg_point(h, phi, 0.55) * MM - Vector((0, hc * MM, 0))))
            ri.append(tuple(egg_point(h, phi, -0.8) * MM - Vector((0, hc * MM, 0))))
        rings_o.append(np.array(ro))
        rings_i.append(np.array(ri))
    # soften the rim of the visor: last outer ring pulled slightly inward
    rings = rings_o + rings_i[::-1]
    c_o = egg_point(hc, 0, 0.55) * MM - Vector((0, hc * MM, 0))
    c_i = egg_point(hc, 0, -0.8) * MM - Vector((0, hc * MM, 0))
    vis = mesh_from_rings(tag + '_visor', rings, cap_start=np.array(c_o), cap_end=np.array(c_i))
    vis.location = (0, hc * MM, 0)
    assign(vis, mat_screen('screen_' + tag, os.path.join(TEX, 'eyes_%s.png' % eyes), 2.5, r_screen=27.0))
    obs.append(vis)
    # weighted base: satin ceramic disc with a machined seam and a light ring underneath
    base = revolve(tag + '_base', [(0, 0.0), (22.0, 0.0), (23.6, 1.0), (24.2, 2.4), (23.6, 3.1), (0, 3.1)],
                   seg=192, axis='y')
    assign(base, mat_ceramic('base_' + tag, '#E9E7E3', rough=0.25, coat=0.6))
    obs.append(base)
    lr = revolve_closed(tag + '_light', [(23.2, 0.15), (24.6, 0.15), (24.6, 0.45), (23.2, 0.45)], seg=192, axis='y')
    assign(lr, mat_emit('eve_light_' + tag, glow, 60.0 * glow_k))
    obs.append(lr)
    parent_all(par, obs)
    par['H'] = EGG['H']
    return par


# ==========================================================================================
# D · SOUL hybrid  (Ø61 × 17, bead-blasted Ti, knurled bezel, Ø53 infinity black glass, frosted halo,
#                    white zirconia twist-off back, orange 12 o'clock dot)
def build_soul_d(tag='D', eyes='cream_look', glow=(1.0, 0.80, 0.56), glow_k=1.0):
    return build_lens(tag, eyes=eyes, glow=glow, glow_k=glow_k, lug=False, r_glass=26.5, halo_w=1.2,
                      back='zirconia', orange_dot=True, halo_frost=True)


def build_cradle(tag='dock', tilt=15.0):
    """Slip-cast glossy porcelain egg cradle with a slot that holds D upright (75°)."""
    cer = mat_ceramic('porcelain_' + tag, '#F6F4F0', rough=0.1)
    prof = [(0, 0.0), (26.0, 0.0), (29.0, 0.8)]
    for h in np.linspace(1.5, 34, 40):
        q = 1 - ((h - 12.0) / 26.0) ** 2
        prof.append((max(38.0 * math.sqrt(max(q, 0)) ** 0.9, 1.0), h))
    prof.append((0, 34.2))
    eg = revolve(tag + '_egg', prof, seg=192, axis='y')
    eg.rotation_euler = (math.radians(90), 0, 0)   # local y (up) -> world z
    eg.scale = (1.0, 1.0, 0.72)                       # (after rotation, local z = world -y depth)
    assign(eg, cer)
    # slot cutter: a disc like D (Ø62 × 18) tilted back
    bpy.ops.mesh.primitive_cylinder_add(radius=31.0 * MM, depth=18.6 * MM, vertices=128,
                                        location=(0, 0.004, 0.047))
    cut = bpy.context.active_object
    cut.rotation_euler = (math.radians(90 - tilt), 0, 0)
    cut.hide_render = True
    bo = eg.modifiers.new('slot', 'BOOLEAN')
    bo.object = cut
    bo.operation = 'DIFFERENCE'
    return eg, cut


# ==========================================================================================
# scene helpers
def graphite_studio(col='#1F2023', wall_y=0.55):
    world_color((0.03, 0.03, 0.035), 0.3)
    sw = sweep(col, rough=0.55, wall_y=wall_y, height=2.5)
    return sw


def launch_lights(tgt, k=1.0, warm=5200, top=True, top_glossy=True):
    """Apple-style: big soft top, two rim strips behind, faint front fill (glossy strips draw chamfer lines)."""
    if top:
        area_light('top', (tgt.x - 0.05, tgt.y - 0.05, tgt.z + 0.55), tgt, 0.6, 5.0 * k, blackbody_rgb(warm),
                   'RECTANGLE', 0.35, spread=60, glossy=top_glossy)
    area_light('rim_l', (tgt.x - 0.35, tgt.y + 0.25, tgt.z + 0.12), tgt, 0.05, 3.0 * k, blackbody_rgb(6000),
               'RECTANGLE', 0.6, spread=50)
    area_light('rim_r', (tgt.x + 0.35, tgt.y + 0.22, tgt.z + 0.15), tgt, 0.05, 3.0 * k, blackbody_rgb(5600),
               'RECTANGLE', 0.6, spread=50)
    area_light('fill', (tgt.x + 0.3, tgt.y - 0.45, tgt.z + 0.15), tgt, 0.9, 0.35 * k, blackbody_rgb(4800),
               glossy=False)
    area_light('bgspot', (0, 0.15, 0.8), (0, 0.6, 0.18), 0.4, 2.5 * k, blackbody_rgb(5000), spread=30)


def desk_scene(wood='oak'):
    world_color((0.93, 0.95, 1.0), 0.05)
    desk = rounded_box('desk', 1.6, 1.3, 0.03, 0.004)
    desk.location = (0, 0.05, -0.015)
    if wood == 'oak':
        assign(desk, mat_wood('oak', srgb('#BF9C78'), srgb('#977150'), 0.45, 4.0))
    else:
        assign(desk, mat_wood('walnut', srgb('#5A3A24'), srgb('#2E1B10'), 0.35, 4.0))
    plane('wall', (4, 2), (0, 0.75, 0.8), (math.radians(90), 0, 0), mat_diffuse('wall', srgb('#D9D5CF'), 0.9, 0.1))
    return desk


def laptop(loc, rot_deg=-14):
    grey = mat_blast('laptop_al', (0.42, 0.43, 0.45), 0.4)
    lap = rounded_box('laptop', 0.31, 0.215, 0.012, 0.004, 8)
    lap.location = loc
    lap.rotation_euler = (0, 0, math.radians(rot_deg))
    assign(lap, grey)
    kb = rounded_box('keys', 0.27, 0.10, 0.0012, 0.0005, 2)
    kb.parent = lap
    kb.location = (0, 0.035, 0.0062)
    assign(kb, mat_diffuse('keys', srgb('#1A1B1D'), 0.5, 0.3))
    pad = rounded_box('trackpad', 0.12, 0.075, 0.0006, 0.0005, 2)
    pad.parent = lap
    pad.location = (0, -0.06, 0.0060)
    assign(pad, mat_polish('pad', (0.40, 0.41, 0.43), 0.25))
    lid = rounded_box('lid', 0.31, 0.006, 0.21, 0.003, 6)
    lid.parent = lap
    lid.location = (0, 0.127, 0.1)
    lid.rotation_euler = (math.radians(-18), 0, 0)
    assign(lid, grey)
    scr = plane('laptop_screen', (0.29, 0.19), (0, -0.0035, 0.004), (math.radians(90), 0, 0),
                mat_emit('lcd', srgb('#1C212B')[:3], 0.6))
    scr.parent = lid
    return lap


def mug(loc):
    m = revolve('mug', [(0, 4), (36, 4), (40, 8), (41, 90), (37, 93), (35, 12), (0, 12)], seg=96)
    m.location = loc
    assign(m, mat_ceramic('mug', '#EDE9E3', rough=0.3, coat=0.4))
    return m


def upright(par, loc, rz=0.0, tilt=0.0):
    """Stand a round body on its rim: local z (face) -> world -y, rotated rz about z, leaning back by tilt."""
    par.location = loc
    par.rotation_euler = (math.radians(90 - tilt), 0, math.radians(rz))


def flat(par, loc, rz=0.0, tilt=0.0):
    par.location = loc
    par.rotation_euler = (math.radians(tilt), 0, math.radians(rz))


def hero_cam(tgt, off, lens=100, fstop=8.0, focus=None, shift=(0, 0)):
    cam = camera(tgt + Vector(off), tgt, lens=lens, fstop=fstop, focus=focus or tgt, shift=shift)
    return cam


# ==========================================================================================
# shots
def shot_A_lens():
    sc = reset()
    graphite_studio()
    a = build_lens('A')
    upright(a, (0, 0, 0.04), rz=26, tilt=6)
    settle(a)
    tgt = world_point(a, (0, 3, 0))
    cam = hero_cam(tgt, (-0.16, -0.33, 0.05), lens=105, fstop=8.0, focus=world_point(a, (6, 0, 8)))
    protect_screens(cam, tgt, 1.6, -0.012)
    screen_highlight(a, cam, up_deg=10.0, side_deg=-8.5, size=(0.02, 0.3), tilt_deg=30.0, strength=5.0, z_mm=8.0)
    launch_lights(tgt, 0.55)
    POST['exposure'] = 0.0
    return sc


def shot_D_soul():
    sc = reset()
    graphite_studio()
    d = build_soul_d('D')
    upright(d, (0, 0, 0.04), rz=-24, tilt=8)
    settle(d)
    tgt = world_point(d, (0, 0, 0))
    cam = hero_cam(tgt, (0.155, -0.33, 0.045), lens=105, fstop=8.0, focus=world_point(d, (-6, 0, 8)))
    protect_screens(cam, tgt, 1.6, -0.012)
    screen_highlight(d, cam, up_deg=10.0, side_deg=8.5, size=(0.02, 0.3), tilt_deg=-30.0, strength=5.0, z_mm=8.0)
    launch_lights(tgt, 0.6)
    POST['exposure'] = 0.0
    return sc


def shot_D_back():
    sc = reset()
    graphite_studio('#34353A')
    d = build_soul_d('Dback')
    upright(d, (0, 0, 30.2 * MM + 0.004), rz=180 - 30, tilt=6)
    tgt = world_point(d, (0, 4, -8))
    cam = hero_cam(tgt, (-0.20, -0.29, 0.10), lens=100, fstop=4.5, focus=world_point(d, (6, 15, -7.8)))
    flag(cam, tgt, dist=0.06, size=(1.2, 1.0))
    launch_lights(tgt, 0.9)
    area_light('soft_front', (tgt.x - 0.2, tgt.y - 0.3, tgt.z + 0.2), tgt, 0.3, 0.8, blackbody_rgb(5200), spread=60)
    POST['exposure'] = 0.0
    return sc


def shot_B_orb():
    sc = reset()
    graphite_studio('#26272A')
    b = build_orb('B', glow_k=1.0)
    flat(b, (0, 0, 0.02), rz=0, tilt=6)
    settle(b)
    tgt = world_point(b, (0, 0, 3))
    cam = hero_cam(tgt, (0.10, -0.27, 0.13), lens=100, fstop=8.0, focus=world_point(b, (0, -8, 10)))
    flag(cam, tgt, dist=0.08, size=(1.5, 1.2))
    launch_lights(tgt, 0.6, top_glossy=False)
    POST['exposure'] = -0.3
    area_light('strip_top', (tgt.x - 0.15, tgt.y + 0.1, tgt.z + 0.35), tgt, 0.03, 0.8, blackbody_rgb(6000),
               'RECTANGLE', 0.4, spread=40)
    area_light('back_b', (tgt.x + 0.05, tgt.y + 0.3, tgt.z + 0.03), tgt, 0.25, 3.0, blackbody_rgb(6500), spread=40)
    POST['exposure'] = 0.0
    return sc


def shot_C_eve():
    sc = reset()
    world_color((0.1, 0.1, 0.1), 0.3)
    sweep('#8F8983', rough=0.6, wall_y=0.55)
    c = build_eve('C')
    c.location = (0, 0, 0)
    c.rotation_euler = (math.radians(90), 0, math.radians(-22))
    tgt = world_point(c, (0, 38, 0))
    cam = hero_cam(tgt, (0.17, -0.40, 0.06), lens=100, fstop=8.0, focus=world_point(c, (0, 45, 20)))
    protect_screens(cam, tgt, 1.6, 0.02)
    screen_highlight_at(world_point(c, (0, 50, 24)), world_point(c, (0, 0, 1)) - world_point(c, (0, 0, 0)), cam)
    launch_lights(tgt, 1.2, warm=5000)
    POST['exposure'] = -0.1
    return sc


def screen_highlight_at(c, n, cam, up_deg=12.0, side_deg=8.0, size=(0.02, 0.3), tilt_deg=-30.0, strength=5.0):
    n = n.normalized()
    v = (c - Vector(cam.location)).normalized()
    R_ = (v - 2 * v.dot(n) * n).normalized()
    side = R_.cross(Vector((0, 0, 1))).normalized()
    up = side.cross(R_).normalized()
    D = (R_ + up * math.tan(math.radians(up_deg)) + side * math.tan(math.radians(side_deg))).normalized()
    ob = plane('strip', size, c + D * 0.3, (0, 0, 0), mat_emit('strip', (1.0, 0.98, 0.95), strength))
    ob.rotation_euler = (-D).to_track_quat('-Z', 'Y').to_euler()
    ob.rotation_euler.rotate_axis('Z', math.radians(tilt_deg))
    for attr in ('visible_camera', 'visible_diffuse', 'visible_shadow', 'visible_transmission', 'visible_volume_scatter'):
        setattr(ob, attr, False)
    return ob


def desk_lights(tgt, k=1.0):
    area_light('window', (-0.9, -0.2, 0.7), tgt, 1.2, 40 * k, blackbody_rgb(6500), 'RECTANGLE', 0.8)
    area_light('fill', (0.5, -0.6, 0.3), tgt, 1.0, 4 * k, blackbody_rgb(4000), glossy=False)
    area_light('rim', (0.1, 0.5, 0.4), tgt, 0.4, 6 * k, blackbody_rgb(5000))


def shot_A_desk():
    sc = reset()
    desk_scene('walnut')
    laptop((0.17, 0.11, 0.006), -12)
    a = build_lens('Adesk')
    flat(a, (-0.035, -0.01, 0.02), rz=15, tilt=0)
    settle(a)
    tgt = world_point(a, (0, 0, 0))
    cam = camera(tgt + Vector((-0.12, -0.30, 0.14)), tgt + Vector((0.012, 0.01, 0.004)), lens=85, fstop=4.0,
                 focus=world_point(a, (0, 0, 8)))
    flag(cam, tgt, dist=0.08)
    screen_highlight(a, cam, up_deg=9.0, side_deg=9.0, size=(0.02, 0.3), tilt_deg=-35.0, strength=5.0, z_mm=8.0)
    desk_lights(tgt)
    return sc


def shot_B_desk():
    sc = reset()
    desk_scene('oak')
    laptop((0.18, 0.12, 0.006), -12)
    b = build_orb('Bdesk')
    flat(b, (-0.03, -0.005, 0.02), rz=0, tilt=0)
    settle(b)
    tgt = world_point(b, (0, 0, 3))
    cam = camera(tgt + Vector((-0.12, -0.30, 0.13)), tgt + Vector((0.012, 0.01, 0.004)), lens=85, fstop=4.0,
                 focus=world_point(b, (0, 0, 8)))
    flag(cam, tgt, dist=0.08)
    desk_lights(tgt, 0.8)
    return sc


def shot_C_desk():
    sc = reset()
    desk_scene('walnut')
    laptop((0.19, 0.13, 0.006), -12)
    mug((-0.17, 0.17, 0.0))
    c = build_eve('Cdesk')
    c.location = (-0.03, 0.0, 0)
    c.rotation_euler = (math.radians(90), 0, math.radians(18))
    tgt = world_point(c, (0, 36, 0))
    cam = camera(tgt + Vector((-0.15, -0.41, 0.07)), tgt + Vector((0.015, 0.0, 0.003)), lens=85, fstop=4.0,
                 focus=world_point(c, (0, 45, 20)))
    protect_screens(cam, tgt, 0.4, 0.03)
    desk_lights(tgt)
    return sc


def shot_D_dock():
    sc = reset()
    desk_scene('oak')
    laptop((0.19, 0.13, 0.006), -12)
    eg, cut = build_cradle('dock', tilt=15.0)
    eg.location = (-0.03, 0.0, 0.0)
    cut.location = (-0.03, 0.004, 0.047)
    d = build_soul_d('Ddock', eyes='cream_look')
    d.location = (-0.03, 0.004, 0.047)
    d.rotation_euler = (math.radians(90 - 15), 0, 0)
    for o in (eg, cut, d):
        o.rotation_euler.z += math.radians(18)
    # rotate the dock group around its own centre (keep positions)
    bpy.context.view_layer.update()
    tgt = world_point(d, (0, 0, 0))
    cam = camera(tgt + Vector((-0.15, -0.40, 0.08)), tgt + Vector((0.015, 0.0, -0.006)), lens=85, fstop=4.0,
                 focus=world_point(d, (0, 0, 8)))
    protect_screens(cam, tgt, 0.4, 0.04)
    screen_highlight(d, cam, up_deg=10.0, side_deg=8.5, size=(0.02, 0.3), tilt_deg=-30.0, strength=5.0, z_mm=8.0)
    desk_lights(tgt)
    return sc


def shot_lineup():
    sc = reset()
    graphite_studio('#2E2F33', wall_y=0.7)
    gx = 0.08
    xs = [-2 * gx, -gx, 0.0, gx, 2 * gx - 0.02]
    # v1 (Ø52) for size, standing like its hero
    v1 = build_amulet('v1', 'coin', '#F3F5F7', 'cream', eye_strength=2.4, glow_w=0.02, ring_tilt=-35)
    place(v1, (xs[4] + 0.015, 0.0, stand_z(v1['bot_y']) + 0.0002), (90, 0, 0))
    # A on a slim graphite easel block
    blk = mat_blast('graphite_block', (0.12, 0.12, 0.13), 0.45)
    for i, x in enumerate((xs[0],)):
        st = rounded_box('easel%d' % i, 0.05, 0.03, 0.010, 0.003, 4)
        st.location = (x, 0.004, 0.005)
        assign(st, blk)
    a = build_lens('Aline')
    upright(a, (xs[0], 0.0, 30.0 * MM + 0.004), rz=0, tilt=10)
    b = build_orb('Bline')
    b.location = (xs[1], 0.0, -b['z_bot'] * MM + 0.0005)
    b.rotation_euler = (math.radians(55), 0, 0)
    settle(b)
    wedge = rounded_box('wedge', 0.04, 0.022, 0.028, 0.003, 4)
    wedge.location = (xs[1], 0.016, 0.014)
    assign(wedge, blk)
    c = build_eve('Cline')
    c.location = (xs[2], 0.01, 0)
    c.rotation_euler = (math.radians(90), 0, 0)
    eg, cut = build_cradle('dockline', tilt=15.0)
    eg.location = (xs[3], 0.0, 0.0)
    cut.location = (xs[3], 0.004, 0.047)
    d = build_soul_d('Dline')
    d.location = (xs[3], 0.004, 0.047)
    d.rotation_euler = (math.radians(75), 0, 0)
    tgt = Vector((0.0, 0.0, 0.026))
    cam = camera((0.0, -0.72, 0.13), tgt, lens=66, fstop=11.0, focus=Vector((0, -0.01, 0.035)))
    protect_screens(cam, tgt, 1.4, 0.0)
    launch_lights(tgt, 1.3)
    for x, lab in zip(xs, ('A \u00b7 LENS', 'B \u00b7 ORB', 'C \u00b7 EVE', 'D \u00b7 SOUL', 'v1 \u00d852')):
        pnt = Vector((x + (0.015 if lab.startswith('v1') else 0), -0.045, 0.0))
        ANNOT.append(dict(a=pnt, b=pnt, label=lab))
    POST['label_rgba'] = (214, 210, 204, 235)
    POST['exposure'] = 0.0
    return sc


def settle(par, gap=0.0002):
    """Drop a parent so its lowest mesh vertex touches z = 0."""
    bpy.context.view_layer.update()
    lo = min((o.matrix_world @ v.co).z for o in par.children if o.type == 'MESH' and not o.hide_render
             for v in o.data.vertices)
    par.location.z += gap - lo


SHOTS = {
    'A_lens': (shot_A_lens, 1600, 1200, 128),
    'A_desk': (shot_A_desk, 1600, 1200, 96),
    'B_orb': (shot_B_orb, 1600, 1200, 144),
    'B_desk': (shot_B_desk, 1600, 1200, 112),
    'C_eve': (shot_C_eve, 1600, 1200, 112),
    'C_desk': (shot_C_desk, 1600, 1200, 96),
    'D_soul': (shot_D_soul, 1600, 1200, 128),
    'D_dock': (shot_D_dock, 1600, 1200, 112),
    'D_back': (shot_D_back, 1600, 1200, 112),
    'lineup': (shot_lineup, 1600, 1200, 112),
}

main()
