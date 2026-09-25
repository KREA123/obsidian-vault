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
    m = mat_solid_sole(name, ALU[cw]['sole'], rough=TUNE.get('sole_rough', 0.58), coat_r=0.5, engrave=True,
                       coat_w=0.0, spec=0.42)
    return m


def colourway_mats(cw, sole=None):
    """v6: every SOUL colourway is anodised aluminium on a tone-matched polymer sole (the v5 names map across)."""
    cw = CW_ALIAS.get(cw.lower(), cw.lower())
    body = mat_alu('alu_' + cw, cw)
    sm = mat_sole_poly('sole_poly_' + cw, cw)
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


def body_mesh(name):
    """Closed SOUL body with the chamfered glass seat, the fine speaker slot and the mic pinholes cut (cached).
    Material roles: shell, sole, gap, chamfer. The v5 build_soul() only knows shell/sole/gap, so the chamfer is
    reported to it as 'gap' and re-assigned afterwards (build_soul below)."""
    path = os.path.join(CACHE6, 'soul_body_v6_%d_%d.npz' % (NU_BODY, N_SHELL))
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
        save_mesh_cache(path, ob, roles)
        print('  v6 body mesh built + booleans %.1fs, %d faces, roles %s' % (time.time() - t0, len(ob.data.polygons),
                                                                           roles))
    set_auto_smooth(ob, 35.0)
    _GEO['roles6'] = list(roles)
    return ob, [('gap' if r == 'chamfer' else r) for r in roles]


_build_soul5 = build_soul


def build_soul(tag, cw='silver', sole=None, eyes='soul_front', strength=2.6, details=True, glass_on=True):
    cw6 = CW_ALIAS.get(cw.lower(), cw.lower())
    par = _build_soul5(tag, cw6, sole, eyes, strength, details, glass_on)
    ob = SOULS[par.name]['body']
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
    'hopa': (_wrap(shot_hopa6, _post_generic), 720, 720, 24),
}

main()
