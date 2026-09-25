"""soul_v6.py -- SOUL v6: the HOPA design (63 x 74 x 27.1 mm, rocker sole) in CNC-machined, bead-blasted, anodised
ALUMINIUM. Every image is a CGI concept.

Geometry, poses, OU capsule, studio and shots are the v5 pipeline (renders/v5/src/soul_v5.py), loaded here by exec
(nothing duplicated). v6 only changes the CMF and two machining details:
  * body   = 6061 aluminium, CNC from billet, very fine uniform bead-blast (~50 um), Type II anodise
             (metallic 1, roughness ~0.34, slight anisotropy, a thin sealed-oxide coat; colour from the dye)
  * one crisp 45 deg machined chamfer (0.45 mm) around the glass seat, cut after blasting -> satin-bright, same colour
  * speaker = one fine laser-cut slot (12 x 0.6 mm) in the +x girdle seam (v5: 0.9 mm)
  * rocker sole = matte polymer, tone-matched (it is also the antenna window); 5 gold contacts as in v5
  * colourways: silver (natural), graphite, midnight, ember, champagne. The OU capsule stays as designed.

    blender -b --factory-startup --python soul_v6.py -- --shot hero [--preview] [--samples N] [--tmp DIR]
Shots: hero family side back bottom ou_night hand macro hopa   (see SHOTS at the end)
"""
import os
import sys

_V6 = os.path.dirname(os.path.abspath(__file__))
_V5 = os.path.abspath(os.path.join(_V6, '..', '..', 'v5', 'src'))
_me = __file__
__file__ = os.path.join(_V5, 'soul_v5.py')          # v5 resolves its tex/, caches and helpers from its own folder
_src5 = open(__file__).read()
exec(compile(_src5[:_src5.rindex('\nmain()')], __file__, 'exec'), globals())
__file__ = _me

CACHE6 = os.environ.get('SOUL_V6_CACHE', '/tmp/soul_v6_cache')
os.makedirs(CACHE6, exist_ok=True)

# ==========================================================================================
# CMF
# anodised colours (sRGB of the metallic base = what the dyed oxide lets the aluminium reflect) and the
# tone-matched polymer soles
ALU = {
    'silver':    dict(col='#CBCDCF', sole='#B4B6B8', rough=0.34, coat=0.10, name='Argint natural'),
    'graphite':  dict(col='#55575B', sole='#3C3E41', rough=0.36, coat=0.22, name='Grafit'),
    'midnight':  dict(col='#26324C', sole='#1D2435', rough=0.36, coat=0.22, name='Albastru noapte'),
    'ember':     dict(col='#C75A2A', sole='#A44A22', rough=0.35, coat=0.18, name='Jar'),
    'champagne': dict(col='#D8C3A2', sole='#BDAA8A', rough=0.34, coat=0.12, name='Șampanie'),
}
CW_ALIAS = {'perla': 'silver', 'onix': 'graphite', 'lapis': 'midnight', 'chihlimbar': 'ember', 'fum': 'champagne'}
_CHAMF = {}
_SOLE_MAT = {}
TEX6 = os.path.join(_V6, 'tex')


def _bead_blast(nt, p, scale=None, strength=None):
    """Very fine uniform bead-blast: overlapping dimples (Voronoi F1, ~50 um cells) + a finer noise, on the base
    normal only (the sealed oxide coat on top stays smoother)."""
    scale = scale or TUNE.get('bb_scale', 19000.0)
    strength = strength if strength is not None else TUNE.get('bb_str', 0.35)
    tc = _tc(nt)
    vo = nt.nodes.new('ShaderNodeTexVoronoi')
    vo.feature = 'SMOOTH_F1' if hasattr(vo, 'feature') else vo.feature
    vo.inputs['Scale'].default_value = scale
    try:
        vo.inputs['Smoothness'].default_value = 0.6
    except Exception:
        pass
    nt.links.new(tc.outputs['Object'], vo.inputs['Vector'])
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = scale * 2.3
    nz.inputs['Detail'].default_value = 2.0
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    mx = nt.nodes.new('ShaderNodeMath')
    mx.operation = 'MULTIPLY_ADD'
    mx.inputs[1].default_value = 0.35
    nt.links.new(nz.outputs['Fac'], mx.inputs[0])
    nt.links.new(vo.outputs['Distance'], mx.inputs[2])
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = strength
    bp.inputs['Distance'].default_value = 0.000012
    nt.links.new(mx.outputs[0], bp.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], p.inputs['Normal'])
    return tc, bp, nz


def _mottle(nt, tc, col, amt=0.035, scale=260.0):
    """Anodising is never perfectly even: a very low-frequency +-3 % value drift across the part."""
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = scale
    nz.inputs['Detail'].default_value = 1.5
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['To Min'].default_value = 1.0 - amt
    mr.inputs['To Max'].default_value = 1.0 + amt
    nt.links.new(nz.outputs['Fac'], mr.inputs['Value'])
    mc = nt.nodes.new('ShaderNodeMix')
    mc.data_type = 'RGBA'
    mc.blend_type = 'MULTIPLY'
    mc.inputs['Factor'].default_value = 1.0
    mc.inputs['A'].default_value = col
    nt.links.new(mr.outputs['Result'], mc.inputs['B'])
    return mc


def mat_alu(name, cw):
    a = ALU[cw]
    m, nt, p, out = new_mat(name)
    col = srgb(a['col'])
    set_in(p, 'Metallic', 1.0)
    set_in(p, 'Roughness', a['rough'] * TUNE.get('rough_k', 1.0))
    set_in(p, 'Anisotropic', TUNE.get('aniso', 0.15))
    tg = nt.nodes.new('ShaderNodeTangent')
    tg.direction_type = 'RADIAL'
    tg.axis = 'Z'
    nt.links.new(tg.outputs[0], p.inputs['Tangent'])
    # sealed anodic oxide (n ~ 1.6): a faint neutral sheen that desaturates grazing reflections -- reads as
    # anodised metal rather than paint or bare chrome
    set_in(p, 'Coat Weight', a['coat'] * TUNE.get('coat_k', 1.0))
    set_in(p, 'Coat Roughness', 0.30)
    set_in(p, 'Coat IOR', 1.6)
    tc, bp, nz = _bead_blast(nt, p)
    mc = _mottle(nt, tc, col)
    nt.links.new(mc.outputs['Result'], p.inputs['Base Color'])
    # roughness jitter from the grain (+-0.03)
    rr = nt.nodes.new('ShaderNodeMapRange')
    base_r = a['rough'] * TUNE.get('rough_k', 1.0)
    rr.inputs['To Min'].default_value = base_r - 0.03
    rr.inputs['To Max'].default_value = base_r + 0.03
    nt.links.new(nz.outputs['Fac'], rr.inputs['Value'])
    nt.links.new(rr.outputs['Result'], p.inputs['Roughness'])
    return m


def mat_chamfer(name, cw):
    """The machined 45 deg chamfer at the glass: cut after blasting, then anodised with the part -> same colour,
    satin-bright, with circumferential tool marks (anisotropy around the glass axis)."""
    a = ALU[cw]
    m, nt, p, out = new_mat(name)
    c = srgb(a['col'])
    lift = TUNE.get('ch_lift', 1.10)
    set_in(p, 'Base Color', (min(c[0] * lift, 1), min(c[1] * lift, 1), min(c[2] * lift, 1), 1))
    set_in(p, 'Metallic', 1.0)
    set_in(p, 'Roughness', TUNE.get('ch_rough', 0.09))
    set_in(p, 'Anisotropic', 0.55)
    tg = nt.nodes.new('ShaderNodeTangent')
    tg.direction_type = 'RADIAL'
    tg.axis = 'Y'
    nt.links.new(tg.outputs[0], p.inputs['Tangent'])
    set_in(p, 'Coat Weight', a['coat'])
    set_in(p, 'Coat Roughness', 0.08)
    set_in(p, 'Coat IOR', 1.6)
    return m


def mat_sole_poly(name, cw):
    """Matte tone-matched polymer (PC/ABS, VDI-27 texture): the antenna window. Laser marking as in v5."""
    global TEX
    t5, TEX = TEX, TEX6                                 # the v6 marking layout (tex_v6.py)
    try:
        m = mat_solid_sole(name, ALU[cw]['sole'], rough=TUNE.get('sole_rough', 0.58), coat_r=0.5, engrave=True,
                           coat_w=0.0, spec=0.42)
    finally:
        TEX = t5
    return m


def colourway_mats(cw, sole=None):
    """v6: every SOUL colourway is anodised aluminium on a tone-matched polymer sole (the v5 names map across)."""
    cw = CW_ALIAS.get(cw.lower(), cw.lower())
    body = mat_alu('alu_' + cw, cw)
    sm = mat_sole_poly('sole_poly_' + cw, cw)
    _SOLE_MAT['cur'] = sm
    _CHAMF['cur'] = mat_chamfer('chamfer_' + cw, cw)
    return body, sm


# ==========================================================================================
# body: the v5 body with a machined chamfer on the glass seat and a finer speaker slot (cached separately)
CH_W = 0.45         # chamfer leg (mm), 45 deg


def seat_cutter6(name):
    r0 = 26.15
    prof = [(0, -0.8), (r0, -0.8), (r0, -CH_W), (r0 + CH_W + 0.15, 0.15), (r0 + CH_W + 0.15, 1.8), (0, 1.8)]
    ob = revolve(name, prof, seg=512)
    for p in ob.data.polygons:
        p.use_smooth = False
    ob.data.transform(Matrix.Translation(V(G_MM)) @ basis(N_FACE, UP_FACE))
    return ob


# flat stable base (lead's decision, 2026-09-25): no rocking. The HOPA shell is cut flat at Z_CUT; a matte polymer
# base plate closes it (the antenna window) and a slightly inset 30 x 14 oval foot, FOOT_H tall, is the only contact.
Z_CUT = 3.0          # mm, in the v5 body frame (the section there is ~33 x 25 mm)
FOOT_H = 1.2         # foot height (the body therefore stands 1.8 mm lower than v5: 63 x 72.2 x 27 mm)
FOOT_A, FOOT_B, FOOT_P = 15.0, 7.0, 2.4      # foot semi-axes (30 x 14) and superellipse exponent
Z_FOOT = Z_CUT - FOOT_H


def _truncate(ob, roles):
    """Cut the body flat at Z_CUT (bisect + fill). Faces of the old rocker sole above the cut become aluminium;
    the new cap is the polymer base plate (role 'sole')."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, Z_CUT * MM), plane_no=(0, 0, 1), clear_inner=True)
    cut_edges = [e for e in res['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
    i_shell, i_sole = roles.index('shell'), roles.index('sole')
    for f in bm.faces:
        if f.material_index == i_sole:
            f.material_index = i_shell
    new = bmesh.ops.contextual_create(bm, geom=cut_edges)
    for f in new['faces']:
        f.material_index = i_sole
        f.smooth = False
        if f.normal.z > 0:
            f.normal_flip()
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def _sharp_cap(ob):
    """Split the normals at the cap outline (the cache does not keep sharp flags)."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for e in bm.edges:
        if len(e.link_faces) == 2:
            a, b = e.link_faces
            if (abs(a.normal.z) > 0.999) != (abs(b.normal.z) > 0.999) and \
                    abs(e.verts[0].co.z - Z_CUT * MM) < 1e-6 and abs(e.verts[1].co.z - Z_CUT * MM) < 1e-6:
                e.smooth = False
    bm.to_mesh(ob.data)
    bm.free()


def body_mesh(name):
    """Closed SOUL body: chamfered glass seat, fine speaker slot, mic pinholes, cut flat at Z_CUT (cached).
    Material roles: shell, sole (= the flat base plate), gap, chamfer. The v5 build_soul() only knows
    shell/sole/gap, so the chamfer is reported to it as 'gap' and re-assigned afterwards (build_soul below)."""
    path = os.path.join(CACHE6, 'soul_body_v6f_%d_%d_%g.npz' % (NU_BODY, N_SHELL, Z_CUT))
    if os.path.exists(path):
        ob, roles = load_mesh_cache(path, name)
    else:
        t0 = time.time()
        ob = body_mesh_raw(name)
        for role in ('shell', 'sole'):
            ob.data.materials.append(bpy.data.materials.new('ROLE_' + role))
        gap_m = bpy.data.materials.new('ROLE_gap')
        ch_m = bpy.data.materials.new('ROLE_chamfer')
        seat = seat_cutter6('cut_seat')
        assign(seat, ch_m)
        cutters = [seat, stadium_cutter('cut_slot', +1, 46.0, 58.0, width=TUNE.get('slot_w', 0.6)),
                   pin_cutter('cut_mic50', -1, 50.0), pin_cutter('cut_mic22', -1, 22.0)]
        for c in cutters[1:]:
            assign(c, gap_m)
        boolean(ob, cutters)
        roles = [m.name.replace('ROLE_', '').split('.')[0] for m in ob.data.materials]
        _truncate(ob, roles)
        save_mesh_cache(path, ob, roles)
        print('  v6 body mesh built + booleans %.1fs, %d faces, roles %s' % (time.time() - t0, len(ob.data.polygons),
                                                                           roles))
    _sharp_cap(ob)
    set_auto_smooth(ob, 35.0)
    _GEO['roles6'] = list(roles)
    return ob, [('gap' if r == 'chamfer' else r) for r in roles]


def _sel(a, b, p, n):
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    return np.stack([a * np.sign(c) * np.abs(c) ** (2 / p), b * np.sign(s) * np.abs(s) ** (2 / p)], 1)


def foot_mesh(tag, n=192):
    """The 30 x 14 oval foot, FOOT_H tall, R0.3 lower edge, with the elliptical opening for the contact coin."""
    rows = []
    for a in np.linspace(0, math.pi / 2, 6):           # R0.3 round from the bottom face up the wall
        k = 0.3 * (1 - math.sin(a))
        z = Z_FOOT + 0.3 * (1 - math.cos(a))
        o = _sel(FOOT_A - k, FOOT_B - k, FOOT_P, n)
        rows.append(np.column_stack([o, np.full(n, z)]))
    o = _sel(FOOT_A, FOOT_B, FOOT_P, n)
    rows.append(np.column_stack([o, np.full(n, Z_CUT + 0.05)]))
    rows = rows[::-1]                                  # top -> bottom (outer wall)
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    hole = np.stack([6.8 * np.cos(t), 6.25 * np.sin(t)], 1)
    rows.append(np.column_stack([hole, np.full(n, Z_FOOT)]))
    rows.append(np.column_stack([hole, np.full(n, Z_CUT + 0.05)]))
    rows.append(rows[0].copy())                        # close the top annulus back onto the outer rim
    Rn = len(rows)
    verts = np.vstack(rows)
    quads = grid_quads(Rn, n) % ((Rn - 1) * n)       # the last row is welded onto the first
    ob = build_mesh(tag + '_foot', verts[: (Rn - 1) * n], quads)
    orient_outward(ob, (FOOT_A * 0.7, 0, (Z_FOOT + Z_CUT) / 2))
    set_auto_smooth(ob, 50.0)
    return ob


def bottom_details(tag):
    """v6 underside: the polymer foot, the FR4 coin with the 5 gold contacts (centre pad + 4 arc pads) flush in the
    foot inside the TPU ring, two Torx T5 heads on the foot, and a dark parting line around the base plate."""
    obs = []
    foot = foot_mesh(tag)
    assign(foot, _SOLE_MAT['cur'])
    obs.append(foot)
    dz = Z_FOOT + 0.16
    ea, eb = 6.0, 5.45
    pads = [circle(0.9, 48)] + [arc_pad(4.0, 1.2, R(a), R(60)) for a in (0, 90, 180, 270)]
    coin = extrude_loops(tag + '_coin', [ellipse(ea, eb, 160)] + pads, -0.16 + dz, 1.0 + dz)
    assign(coin, mat_simple('fr4', '#121212', 0.55, spec=0.4))
    obs.append(coin)
    for i, pl in enumerate(pads):
        pd = extrude_loops(tag + '_pad%d' % i, [pl], -0.012 + dz, 0.6 + dz)
        assign(pd, mat_simple('gold', '#E3C07A', 0.18, metal=1.0))
        obs.append(pd)
    ring = extrude_loops(tag + '_tpu', [ellipse(6.8, 6.25, 160), ellipse(6.0, 5.45, 160)], Z_FOOT + 0.02, Z_FOOT + 0.5)
    assign(ring, mat_simple('tpu_clear', '#F2F2F2', 0.3, trans=0.9, ior=1.5))
    obs.append(ring)
    for sx in (-1, 1):
        p = np.array([sx * 11.2, 0.0, Z_FOOT])
        head = revolve(tag + '_torx%d' % sx, [(0, 0.0), (1.22, 0.0), (1.3, 0.07), (1.3, 0.6), (0, 0.6)], seg=48)
        head.matrix_basis = Matrix.Translation(V(p + np.array([0, 0, -0.005])))
        assign(head, mat_simple('screw', '#BDB8B0', 0.30, metal=1.0))
        obs.append(head)
        st = extrude_loops(tag + '_torxs%d' % sx, [torx(0.72, 0.5)], -0.03, 0.0)
        st.matrix_basis = Matrix.Translation(V(p + np.array([0, 0, 0.02])))
        assign(st, gap_dark())
        obs.append(st)
    # parting line between the aluminium shell and the polymer base plate: the cap outline, 0.35 mm inside
    import bmesh  # noqa: F401
    body = bpy.data.objects.get('body_' + tag)
    if body is not None:
        me = body.data
        co = np.array([(v.co.x / MM, v.co.y / MM, v.co.z / MM) for v in me.vertices])
        on = co[np.abs(co[:, 2] - Z_CUT) < 1e-3]
        if len(on) > 16:
            ang = np.arctan2(on[:, 1], on[:, 0])
            on = on[np.argsort(ang)]
            cen = on[:, :2].mean(0)
            ctr = on.copy()
            d = on[:, :2] - cen
            ln = np.linalg.norm(d, axis=1, keepdims=True)
            ctr[:, :2] = cen + d * (1 - 0.35 / ln)
            ctr[:, 2] = Z_CUT - 0.02
            gl = curve_obj(tag + '_baseline', [tuple(p * MM) for p in ctr[::2]], 0.07 * MM, closed=True, res=2)
            assign(gl, gap_dark())
            obs.append(gl)
    return obs


_build_soul5 = build_soul


def build_soul(tag, cw='silver', sole=None, eyes='soul_front', strength=2.6, details=True, glass_on=True):
    cw6 = CW_ALIAS.get(cw.lower(), cw.lower())
    par = _build_soul5(tag, cw6, sole, eyes, strength, details, glass_on)
    ob = SOULS[par.name]['body']
    sp = bpy.data.objects.get(tag + '_split')          # v5's sole split groove: there is no rocker sole any more
    if sp is not None:
        bpy.data.objects.remove(sp)
    for i, r in enumerate(_GEO['roles6']):
        if r == 'chamfer':
            ob.data.materials[i] = _CHAMF['cur']
    return par


# ==========================================================================================
# light helpers for metal
def chamfer_kick(par, cam, ang_deg, dist=0.22, power=None, size=(0.012, 0.16), temp=5600, name='kick'):
    """A thin strip seen only in reflections, placed where the 45 deg chamfer at glass angle `ang_deg` (0 = +x of
    the face, 90 = up) mirrors the camera: one crisp highlight along that part of the ring."""
    bpy.context.view_layer.update()
    c, n = glass_world(par)
    up = Vector((0, 0, 1)) - Vector((0, 0, 1)).dot(n) * n
    ey = up.normalized()
    ex = ey.cross(n).normalized()
    a = R(ang_deg)
    rad = (ex * math.cos(a) + ey * math.sin(a)).normalized()
    P = c + rad * (26.15 + CH_W / 2) * MM + n * (-CH_W / 2) * MM
    nc = (n + rad).normalized()
    v = (Vector(cam.location) - P).normalized()
    r = (2 * v.dot(nc) * nc - v).normalized()
    L = area_light(name, P + r * dist, P, size[0], power or TUNE.get('kick', 1.2), blackbody_rgb(temp),
                   'RECTANGLE', size_y=size[1])
    # long side along the ring tangent
    tang = n.cross(rad).normalized()
    zax = (P - L.location).normalized()
    yax = tang - tang.dot(zax) * zax
    yax.normalize()
    xax = yax.cross(zax)
    from mathutils import Matrix as _M
    L.matrix_world = _M((
        (xax.x, yax.x, -zax.x, L.location.x), (xax.y, yax.y, -zax.y, L.location.y),
        (xax.z, yax.z, -zax.z, L.location.z), (0, 0, 0, 1)))
    L.visible_diffuse = False
    return L


def metal_front_card(cam, T, col=0.55, size=(1.4, 1.0), dist=0.10):
    """Replace the black flag behind the camera with a warm-grey diffuse card: the aluminium front mirrors a soft
    grey instead of a black hole. The flat glass is kept black by mirror_card() + its AR coating."""
    for ob in list(bpy.data.objects):
        if ob.name.startswith('flag'):
            ob.data.materials[0] = mat_diffuse('frontcard', (col, col * 0.985, col * 0.96, 1), 0.9, 0.0)
            ob.scale = (size[0] / 3.0, size[1] / 2.2, 1)
    return None


def metalise(cam, T, par_list, card=0.14):
    """After a v5 shot has set its studio: soften the flag, shrink the glass-only mirror card."""
    TUNE.setdefault('mcard', card)
    bpy.context.view_layer.update()
    if TUNE.get('floor_card', 0) <= 0:
        # the long glossy-black floor card of protect_screens() would be mirrored by the whole lower body
        for ob in list(bpy.data.objects):
            if ob.name.startswith('card') and ob.matrix_world.translation.z < 0.002 and max(ob.dimensions) > 0.3:
                bpy.data.objects.remove(ob)
    if TUNE.get('front_card', 1) > 0:
        metal_front_card(cam, T, col=TUNE.get('fc_col', 0.5))


# ==========================================================================================
# shots
def _cam():
    return bpy.context.scene.camera


def shot_hero6():
    """Natural-silver SOUL, 3/4 from the left, OU (as designed) soft behind-right. 1600 x 1200."""
    sc = reset()
    T = Vector((0, -2 * MM, 36 * MM))
    TUNE.setdefault('mcard', 0.16)
    day_studio(T)
    s = build_soul('hero', 'silver', eyes='cream_look')
    pose_soul(s, (0, 0, 0), yaw=TUNE.get('hero_yaw', -10.0))
    TUNE['lid_tr'] = TUNE.get('hero_lid_tr', 0.15)
    ou = build_ou('bg', 'perla', lid_open=True, night=False)
    ou.location = V((TUNE.get('ou_x', 105), TUNE.get('ou_y', 150), 0.5))
    ou.rotation_euler = (0, 0, R(-24.0))
    cam = cam_aed(T, TUNE.get('hero_az', -30.0), TUNE.get('hero_el', 9.0), TUNE.get('hero_d', 470.0), 100, 5.6,
                  focus=eye_point(s))
    black_glass(cam, T, [s])
    metalise(cam, T, [s])
    chamfer_kick(s, cam, TUNE.get('kick_ang', 128.0), power=TUNE.get('kick', 1.2))
    return sc


def shot_family6():
    return shot_family()


FAMILY = [('graphite', 'soul_smug', dict(roll=-5.0)), ('ember', 'soul_left', dict(pitch=6.0)),
          ('perla', 'soul_front', dict()), ('midnight', 'cream_look', dict(roll=6.0)),
          ('champagne', 'soul_wide', dict(roll=-3.0))]


def _post_family():
    cam = _cam()
    metal_front_card(cam, Vector((0, 0.002, 0.036)), col=TUNE.get('fc_col', 0.5))


def shot_side6():
    """From the +x (speaker) side, 3/4-ish: the laser-cut slot on the seam, the chamfer catching light at the glass
    edge, the wedge and the rocker sole."""
    sc = reset()
    T = Vector((0, 0, 37 * MM))
    TUNE.setdefault('mcard', 0.16)
    day_studio(T, rot=TUNE.get('side_rot', 60.0))
    s = build_soul('side', 'silver', eyes='soul_left')
    pose_soul(s, (0, 0, 0), yaw=0.0)
    cam = cam_aed(T, TUNE.get('side_az', 62.0), TUNE.get('side_el', 8.0), TUNE.get('side_d', 330.0), 100, 8.0,
                  focus=V((25, -6, 45)))
    black_glass(cam, T, [s], glint=False)
    metalise(cam, T, [s])
    chamfer_kick(s, cam, TUNE.get('kick_ang', 20.0), power=TUNE.get('kick', 1.0))
    return sc


def shot_back6():
    sc = shot_back()
    return sc


def shot_macro():
    """Close-up: the bead-blast grain and the machined chamfer meeting the black glass (upper-left of the face)."""
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#D9CDBE')
    s = build_soul('mac', 'silver', eyes='cream_look')
    pose_soul(s, (0, 0, 0), yaw=0.0)
    bpy.context.view_layer.update()
    c, n = glass_world(s)
    up = Vector((0, 0, 1)) - Vector((0, 0, 1)).dot(n) * n
    ey = up.normalized()
    ex = ey.cross(n).normalized()
    a = R(TUNE.get('mac_ang', 125.0))
    rad = (ex * math.cos(a) + ey * math.sin(a)).normalized()
    tang = n.cross(rad).normalized()
    P = c + rad * TUNE.get('mac_r', 27.5) * MM
    # camera: in front and outward, looking back across the edge toward the glass centre
    el = R(TUNE.get('mac_el', 38.0))      # angle away from the face normal
    sw = R(TUNE.get('mac_sw', 25.0))      # swing along the ring tangent
    d = (n * math.cos(el) + rad * math.sin(el) * math.cos(sw) + tang * math.sin(el) * math.sin(sw)).normalized()
    D = TUNE.get('mac_d', 70.0) * MM
    cam = camera(P + d * D, P - rad * TUNE.get('mac_look', 6.0) * MM, lens=100, fstop=TUNE.get('mac_f', 4.0),
                 focus=P)
    cam.data.clip_start = 0.002
    studio3(Vector(c), 1.0, bg=7.5)
    black_glass(cam, Vector(c), [s], glint=False, card=True)
    metalise(cam, Vector(c), [s])
    chamfer_kick(s, cam, TUNE.get('mac_ang', 125.0) + TUNE.get('mac_kick_off', 6.0), dist=0.12,
                 power=TUNE.get('kick', 0.6), size=(0.006, 0.05))
    POST['exposure'] = -0.35 + TUNE.get('mac_exp', 0.0)
    POST['bloom'] = 0.02
    return sc


def shot_bottom6():
    return shot_bottom()


def shot_ou_night6():
    return shot_ou(False)


def shot_hand6():
    return shot_hand()


def shot_hopa6():
    return shot_hopa()


def shot_alive():
    """5 s 'alive' clip, one frame per call (render_v6.sh renders each unique eye state once): SOUL stands still on
    its flat foot, only the eyes blink and glance. Silver, 3/4, the OU soft behind."""
    f = int(TUNE.get('alive_frame', 1))
    sc = shot_hero6()
    s = bpy.data.objects['soul_hero']
    g = SOULS[s.name]['glass']
    node = next(n for n in g.active_material.node_tree.nodes if n.type == 'TEX_IMAGE')
    node.image = bpy.data.images.load('/tmp/soul_v6_cache/alive_eyes/eyes_alive_%04d.png' % f)
    cam = sc.camera
    cam.data.lens = TUNE.get('alive_lens', 100.0)
    return sc


def shot_test6():
    sc = reset()
    T = Vector((0, 0, 36 * MM))
    TUNE.setdefault('mcard', 0.16)
    day_studio(T)
    s = build_soul('t', TUNE.get('test_cw_s', 'silver'), eyes='soul_front')
    pose_soul(s, (0, 0, 0))
    cam = cam_aed(T, TUNE.get('t_az', 0.0), TUNE.get('t_el', 4.0), 560.0, 100, 11.0, focus=eye_point(s))
    black_glass(cam, T, [s])
    metalise(cam, T, [s])
    return sc


def _wrap(fn, post=None):
    def run():
        sc = fn()
        if post:
            post()
        return sc
    return run


def _post_generic():
    """v5 shots (back, bottom, hand, hopa): the flag behind the camera becomes a grey card for the metal."""
    cam = _cam()
    if cam is not None and TUNE.get('front_card', 1) > 0:
        metal_front_card(cam, None, col=TUNE.get('fc_col', 0.5))


SHOTS = {
    'hero': (shot_hero6, 1600, 1200, 160),
    'family': (_wrap(shot_family6, _post_family), 2000, 1125, 128),
    'side': (shot_side6, 1600, 1200, 128),
    'back': (_wrap(shot_back6, _post_generic), 1600, 1200, 128),
    'bottom': (_wrap(shot_bottom6, _post_generic), 1600, 1200, 128),
    'ou_night': (shot_ou_night6, 1600, 1200, 192),
    'hand': (_wrap(shot_hand6, _post_generic), 1600, 1200, 128),
    'macro': (shot_macro, 1600, 1200, 192),
    'alive': (shot_alive, 720, 720, 64),
    'test': (shot_test6, 1200, 1200, 48),
}

main()
