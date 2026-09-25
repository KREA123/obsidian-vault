"""soul_v7.py -- SOUL v7: size study. The v6 aluminium SOUL (natural silver) around three real round panels:

  S  1.75" AMOLED  466x466  active dia 43.8 mm   (today: Waveshare ESP32-S3-Touch-AMOLED-1.75)  body 63 x 72 x 27
  M  2.8"  IPS     480x480  active dia 71.1 mm   (Waveshare ESP32-S3-Touch-LCD-2.8C, ST7701 RGB)  body ~93 x 106 x 31
  L  3.4"  IPS     800x800  active dia 86.4 mm   (Waveshare ESP32-P4-WIFI6-Touch-LCD-3.4C, JD9365 MIPI) ~113 x 129 x 34

Every image is a CGI concept. The v6 pipeline (renders/v6/src/soul_v6.py -> v5 -> concepts/soul_scene) is loaded by
exec; nothing is duplicated. v7 only:
  * scales the whole SOUL: x/z (width, height) by k, depth by kd (a bigger body does not need to be proportionally
    thicker: the battery grows in plan, the stack grows ~3-7 mm)
  * M and L: the glass keeps the v6 proportions but the black ring around the active area is thinner
    (IPS panels: ~1.8 mm local ring instead of v6's 4.1 mm), so active/body = 0.77 instead of 0.70
  * M and L are IPS: black is never true black -> a faint backlight glow inside the active circle
  * shots: hands_S/M/L (same hand, same camera), lineup (S/M/L + phone slab + mug), typing (M, keyboard, thumb)

    blender -b --factory-startup --python soul_v7.py -- --shot hands_M [--preview] [--samples N] [--tmp DIR]
"""
import os
import sys

_V7 = os.path.dirname(os.path.abspath(__file__))
_V6 = os.path.abspath(os.path.join(_V7, '..', '..', 'v6', 'src'))
_me7 = __file__
__file__ = os.path.join(_V6, 'soul_v6.py')
_src6 = open(__file__).read()
exec(compile(_src6[:_src6.rindex('\nmain()')], __file__, 'exec'), globals())
__file__ = _me7
_V7 = os.path.dirname(os.path.abspath(_me7))
TEX7 = os.path.join(_V7, 'tex')

from mathutils.bvhtree import BVHTree  # noqa: E402

BODY = (63.0, 72.2, 27.0)          # v6 width, height, depth (mm)
ACT_V6 = 21.88                     # v6 active radius (local mm)
ACT_THIN = 24.2                    # M/L: active radius inside the same 26.0 glass (1.8 mm black ring)
SIZES = {
    'S': dict(dia=43.76, act=ACT_V6, depth=27.0, ips=False, panel='1,75″ AMOLED 466×466'),
    'M': dict(dia=71.1, act=ACT_THIN, depth=31.0, ips=True, panel='2,8″ IPS 480×480'),
    'L': dict(dia=86.4, act=ACT_THIN, depth=34.0, ips=True, panel='3,4″ IPS 800×800'),
}
for _k, _s in SIZES.items():
    _s['k'] = (_s['dia'] / 2) / _s['act']
    _s['kd'] = _s['depth'] / BODY[2]
    _s['W'] = BODY[0] * _s['k']
    _s['H'] = BODY[1] * _s['k']
    print('  size %s: k %.3f kd %.3f -> body %.1f x %.1f x %.1f mm, active dia %.1f' % (
        _k, _s['k'], _s['kd'], _s['W'], _s['H'], _s['depth'], _s['dia']))


def screen_setup(par, size, img_path=None, strength=None):
    """Re-map the screen texture to the size's active radius; IPS -> faint backlight glow inside the circle."""
    sz = SIZES[size]
    g = SOULS[par.name]['glass']
    m = g.active_material
    nt = m.node_tree
    mp = next(n for n in nt.nodes if n.type == 'MAPPING')
    img = next(n for n in nt.nodes if n.type == 'TEX_IMAGE')
    p = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    s = 1.0 / (2 * sz['act'] * MM)
    mp.inputs['Scale'].default_value = (s, s, 1)
    if img_path:
        img.image = bpy.data.images.load(img_path, check_existing=True)
    if strength is not None:
        set_in(p, 'Emission Strength', strength)
    if sz['ips']:
        # IPS black = backlight leaking through the crossed polarisers (~1/1000 of white head-on, more off-axis)
        glow = TUNE.get('ips_glow', 0.0035)
        dist = nt.nodes.new('ShaderNodeVectorMath')
        dist.operation = 'DISTANCE'
        dist.inputs[1].default_value = (0.5, 0.5, 0.0)
        nt.links.new(mp.outputs[0], dist.inputs[0])
        lt = nt.nodes.new('ShaderNodeMath')
        lt.operation = 'LESS_THAN'
        lt.inputs[1].default_value = 0.5
        nt.links.new(dist.outputs['Value'], lt.inputs[0])
        mul = nt.nodes.new('ShaderNodeMath')
        mul.operation = 'MULTIPLY'
        mul.inputs[1].default_value = glow
        nt.links.new(lt.outputs[0], mul.inputs[0])
        tint = nt.nodes.new('ShaderNodeCombineColor')
        # cool-grey glow (white LED backlight)
        mr = nt.nodes.new('ShaderNodeMath')
        mr.operation = 'MULTIPLY'
        mr.inputs[1].default_value = 0.85
        nt.links.new(mul.outputs[0], mr.inputs[0])
        nt.links.new(mr.outputs[0], tint.inputs[0])
        nt.links.new(mul.outputs[0], tint.inputs[1])
        mb = nt.nodes.new('ShaderNodeMath')
        mb.operation = 'MULTIPLY'
        mb.inputs[1].default_value = 1.15
        nt.links.new(mul.outputs[0], mb.inputs[0])
        nt.links.new(mb.outputs[0], tint.inputs[2])
        add = nt.nodes.new('ShaderNodeMix')
        add.data_type = 'RGBA'
        add.blend_type = 'ADD'
        add.inputs['Factor'].default_value = 1.0
        nt.links.new(img.outputs['Color'], add.inputs['A'])
        nt.links.new(tint.outputs[0], add.inputs['B'])
        nt.links.new(add.outputs['Result'], p.inputs['Emission Color'])


def scale_mat(size):
    sz = SIZES[size]
    return Matrix.Diagonal((sz['k'], sz['kd'], sz['k'], 1.0))


def soul_on_table(tag, size, loc_mm, yaw, eyes='soul_front'):
    s = build_soul(tag, 'silver', eyes=eyes)
    pose_soul(s, loc_mm, yaw=yaw, settle_=False)
    s.matrix_world = s.matrix_world @ scale_mat(size)
    settle(s, 0.00002)
    level_eyes(s)
    screen_setup(s, size)
    return s


# ==========================================================================================
# props
def build_hand7(pose):
    """The v7 re-posed hand (hand_sdf_v7.py), same material and smoothing as v4/v5's build_hand_v4."""
    global TEX
    d = os.path.join(TEX7, pose)
    os.makedirs(d, exist_ok=True)
    if not os.path.exists(os.path.join(d, 'hand.npz')):
        import subprocess
        extra = [kv for kv in os.environ.get('HAND_ARGS', '').split(',') if kv]
        subprocess.run(['python3', os.path.join(_V7, 'hand_sdf_v7.py'), pose, os.path.join(d, 'hand.npz')] + extra,
                       check=True)
    t0, TEX = TEX, d
    try:
        ob = build_hand_v4('hand', (0.0, 0.0, 0.030), 18.0)
    finally:
        TEX = t0
    return ob


def rest_on(dev, support, gap=0.25, axis=Vector((0, 0, 1))):
    """Translate `dev` along `axis` so it just rests on `support` (ray-cast every device vertex down onto it)."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(support, dg)
    Mi = support.matrix_world.inverted()
    Mi3 = Mi.to_3x3()
    dn = (Mi3 @ (-axis)).normalized()
    best = None
    for o in dev.children:
        if o.type != 'MESH' or o.hide_render:
            continue
        me = o.data
        Mw = o.matrix_world
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3)
        step = max(1, len(co) // 6000)
        for c in co[::step]:
            pw = Mw @ Vector(c.tolist())
            pl = Mi @ (pw + axis * 0.3)
            hit = bvh.ray_cast(pl, dn, 1.0)
            if hit[0] is None:
                continue
            hw = support.matrix_world @ hit[0]
            g = (pw - hw).dot(axis)
            best = g if best is None else min(best, g)
    if best is not None:
        dev.matrix_world = Matrix.Translation(axis * (gap * MM - best)) @ dev.matrix_world
        bpy.context.view_layer.update()
    return best


def phone_slab(loc_mm, yaw, lying=True):
    """A generic phone-sized slab (71.5 x 147 x 7.8 mm): black glass front, satin grey aluminium frame. No brand."""
    ob = rounded_box('phone', 71.5 * MM, 147.0 * MM, 7.8 * MM, 3.6 * MM, 8)
    assign(ob, mat_simple('phone_frame', '#8E9094', 0.32, metal=1.0))
    gl = rounded_box('phone_glass', 70.6 * MM, 146.1 * MM, 0.6 * MM, 0.28 * MM, 4)
    gl.location = (0, 0, 3.65 * MM)
    m, nt, p, out = new_mat('phone_glass')
    set_in(p, 'Base Color', srgb('#050506'))
    set_in(p, 'Roughness', TUNE.get('ph_rough', 0.16))
    set_in(p, 'Specular IOR Level', 0.35)
    assign(gl, m)
    par = new_par('phone_par')
    parent_all(par, [ob, gl])
    par.location = V((loc_mm[0], loc_mm[1], 3.9))
    par.rotation_euler = (0, 0, R(yaw))
    return par


def mug(loc_mm, yaw):
    """A plain matte-glazed ceramic mug, dia 82 x 95 mm, with coffee. Handle = a swept tube."""
    R0, H = 41.0, 95.0
    prof = [(0, 0.0), (R0 - 4, 0.0), (R0 - 1.2, 0.6), (R0, 3.0), (R0 + 0.4, H - 1.5), (R0, H), (R0 - 3.2, H),
            (R0 - 3.6, H - 2.0), (R0 - 3.6, 8.0), (0, 7.0)]
    body = revolve('mug', prof, seg=160)
    m, nt, p, out = new_mat('glaze')
    set_in(p, 'Base Color', srgb('#EDE7DD'))
    set_in(p, 'Roughness', 0.34)
    set_in(p, 'Coat Weight', 0.5)
    set_in(p, 'Coat Roughness', 0.12)
    _noise_bump(nt, p, 400.0, 0.04, 0.0003)
    assign(body, m)
    cof = revolve('coffee', [(0, H - 14.0), (R0 - 3.6, H - 14.0), (R0 - 3.6, H - 15.0), (0, H - 15.0)], seg=96)
    cm, cnt, cp, _ = new_mat('coffee')
    set_in(cp, 'Base Color', srgb('#2A170C'))
    set_in(cp, 'Roughness', 0.08)
    assign(cof, cm)
    # handle: a D-loop on +x
    t = np.linspace(-1.15, 1.15, 40)
    pts = [((R0 - 1.5 + 26.0 * np.cos(a) ** 0.8) * MM, 0.0, (H * 0.5 + 30.0 * np.sin(a)) * MM) for a in t]
    hd = curve_obj('mug_handle', pts, 5.2 * MM, res=6)
    hd.data.bevel_mode = 'ROUND'
    assign(hd, m)
    par = new_par('mug_par')
    parent_all(par, [body, cof, hd])
    par.location = V((loc_mm[0], loc_mm[1], 0.0))
    par.rotation_euler = (0, 0, R(yaw))
    return par


def desk_top():
    """Light oak desk top (the lineup)."""
    top = rounded_box('desk', 1.6, 1.0, 0.03, 0.003, 3)
    top.location = (0, 0.25, -0.015)
    assign(top, mat_wood('oak', srgb('#C9A57A'), srgb('#A9834F'), 0.42, 5.0))
    return top


# ==========================================================================================
# shots
HAND_T = Vector((0.004, 0.012, 0.050))


def shot_hands(size):
    """One SOUL of `size` lying face-up in the open right palm. Same hand, same camera and light for S/M/L."""
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#CDBFAE', wall_y=0.55)
    hand = build_hand7('open')
    s = build_soul('hand', 'silver', eyes=TUNE.get('hand_eyes', 'soul_front'))
    ctr = Vector((0, -1.0 * MM, 37.0 * MM))
    Rm = Euler((R(TUNE.get('h_rx', 14.0)), R(TUNE.get('h_ry', -4.0)), R(TUNE.get('h_rz', 12.0)))).to_matrix().to_4x4() \
        @ Matrix.Rotation(R(-90), 4, 'X')
    loc = Vector((TUNE.get('h_x', 3.0) * MM, TUNE.get('h_y', 8.0) * MM, 0.08))
    s.matrix_world = Matrix.Translation(loc) @ Rm @ scale_mat(size) @ Matrix.Translation(-ctr)
    gap = rest_on(s, hand, gap=0.3)
    print('  rest gap', gap)       # face-up: the screen keeps its own 'up' (toward the crown), no level_eyes
    screen_setup(s, size)
    T = HAND_T
    cam = camera(T + Vector((TUNE.get('hc_x', 0.05), TUNE.get('hc_y', -0.22), TUNE.get('hc_z', 0.38))), T,
                 lens=TUNE.get('h_lens', 60.0), fstop=TUNE.get('h_f', 8.0), focus=eye_point(s))
    flag(cam, T)
    mirror_card(s, cam)
    metal_front_card(cam, T, col=TUNE.get('fc_col', 0.5))
    POST['bloom'] = 0.03
    studio3(T, 1.1, bg=7.0)
    POST['exposure'] = -0.35
    return sc


def shot_lineup():
    """S / M / L standing on a light-oak desk, a phone-sized slab lying in front-left, a mug at the right."""
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#D9CDBE')
    gapx = TUNE.get('lu_gap', 22.0)
    xs, x = [], TUNE.get('lu_x0', -150.0)
    pars = []
    eyes = {'S': 'soul_front', 'M': 'cream_look', 'L': 'soul_wide'}
    for size in ('S', 'M', 'L'):
        w = SIZES[size]['W']
        cx = x + w / 2
        s = soul_on_table('lu' + size, size, (cx, 0.0, 0.0), TUNE.get('lu_yaw', -6.0), eyes=eyes[size])
        pars.append(s)
        xs.append(cx)
        x += w + gapx
    phone_slab((TUNE.get('ph_x', -215.0), TUNE.get('ph_y', -55.0)), TUNE.get('ph_yaw', 82.0))
    mug((x + TUNE.get('mug_dx', 45.0), TUNE.get('mug_y', 30.0)), TUNE.get('mug_yaw', -50.0))
    T = Vector((TUNE.get('lu_tx', 12.0) * MM, 0.0, TUNE.get('lu_tz', 45.0) * MM))
    cam = cam_aed(T, TUNE.get('lu_az', -3.0), TUNE.get('lu_el', 20.0), TUNE.get('lu_d', 950.0),
                  TUNE.get('lu_lens', 55.0), 11.0, focus=Vector((0, 0, 0.05)))
    black_glass(cam, T, pars, glint=False)
    metalise(cam, T, pars)
    studio(T, 1.6)
    POST['bloom'] = 0.03
    POST['exposure'] = -0.35
    for size, s in zip(('S', 'M', 'L'), pars):
        sz = SIZES[size]
        base = s.matrix_world @ Vector((0, -BODY[2] * 0.5 * MM, 0))
        ANNOT.append(dict(label='%s|%s|%.0f × %.0f × %.0f mm' % (size, sz['panel'], sz['W'], sz['H'], sz['depth']),
                          a=Vector((base.x, base.y - 0.04, 0.0)), b=base))
    return sc


def shot_typing():
    """M held like a phone in the right hand: its base in the heel of the palm, its back leaning on the curled
    fingers, face tilted toward the viewer; the SoulOS keyboard on screen and the thumb (IK in hand_sdf_v7.py)
    hovering over the lower-right keys."""
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#CDBFAE', wall_y=0.55)
    size = 'M'
    sz = SIZES[size]
    HM = Matrix.Translation((0.0, 0.0, 0.030)) @ Matrix.Rotation(R(18.0), 4, 'Z')      # build_hand_v4's placement
    rest = build_hand7('hold')
    s = build_soul('ty', 'silver', eyes='soul_front')
    ctr = Vector((0, -1.0 * MM, 37.0 * MM))
    a = TUNE.get('t_tilt', 40.0)
    Rh = Matrix.Rotation(R(TUNE.get('t_rz', -6.0)), 4, 'Z') @ Matrix.Rotation(R(a - 90.0), 4, 'X')
    loc_h = Vector((TUNE.get('t_x', -14.0) * MM, TUNE.get('t_y', 34.0) * MM, 0.09))
    s.matrix_world = HM @ Matrix.Translation(loc_h) @ Rh @ scale_mat(size) @ Matrix.Translation(-ctr)
    rest_on(s, rest, gap=0.3)
    screen_setup(s, size, os.path.join(TEX7, 'kbd_hello.png'), strength=TUNE.get('kbd_str', 2.2))
    # thumb target: a point hovering above key 'n' (screen px (321, 314) on the 466 layout), in hand coordinates
    info = SOULS[s.name]
    Mg = s.matrix_world @ info['M_gl']
    px, py = TUNE.get('key_px', 321.0), TUNE.get('key_py', 314.0)
    u = (px - 233.0) / 233.0 * sz['act']
    v = -(py - 233.0) / 233.0 * sz['act']
    hover = TUNE.get('hover', 3.0) + 8.8           # gap above the glass + the thumb-tip radius
    tgt_w = Mg @ Vector((u * MM, v * MM, 0.0))
    nrm_w = (Mg.to_3x3() @ Vector((0, 0, 1))).normalized()
    # the glass object carries the body scale; move off the face in world mm
    tgt_w = tgt_w + nrm_w * hover * MM
    tgt_h = HM.inverted() @ tgt_w
    print('  thumb target (hand mm)', tuple(round(c / MM, 1) for c in tgt_h))
    bpy.data.objects.remove(rest)
    # the device as an oriented box in hand coordinates (the thumb must go around it)
    Mh = HM.inverted() @ s.matrix_world
    bc = Mh @ Vector((0, -1.0 * MM, 37.0 * MM))          # body centre (local)
    ax = [(Mh.to_3x3() @ Vector(e)).normalized() for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
    hw = (BODY[0] / 2 * sz['k'], BODY[2] / 2 * sz['kd'], BODY[1] / 2 * sz['k'])
    args = ['tx=%.2f' % (tgt_h.x / MM), 'ty=%.2f' % (tgt_h.y / MM), 'tz=%.2f' % (tgt_h.z / MM),
            'bx_cx=%.2f' % (bc.x / MM), 'bx_cy=%.2f' % (bc.y / MM), 'bx_cz=%.2f' % (bc.z / MM),
            'bx_hw=%.2f' % hw[0], 'bx_hd=%.2f' % hw[1], 'bx_hh=%.2f' % hw[2]]
    for i, a_ in enumerate(ax):
        args += ['bx_x%d=%.4f' % (i, a_.x), 'bx_y%d=%.4f' % (i, a_.y), 'bx_z%d=%.4f' % (i, a_.z)]
    os.environ['HAND_ARGS'] = ','.join(args)
    print('  hand args', os.environ['HAND_ARGS'])
    p = os.path.join(TEX7, 'type', 'hand.npz')
    if os.path.exists(p):
        os.remove(p)
    build_hand7('type')
    T = Vector((TUNE.get('ty_tx', 0.0) * MM, TUNE.get('ty_ty', 0.0) * MM, TUNE.get('ty_tz', 45.0) * MM))
    cam = camera(T + Vector((TUNE.get('tc_x', 0.22), TUNE.get('tc_y', -0.28), TUNE.get('tc_z', 0.24))), T,
                 lens=TUNE.get('t_lens', 55.0), fstop=TUNE.get('t_f', 8.0), focus=glass_world(s)[0])
    flag(cam, T)
    mirror_card(s, cam)
    metal_front_card(cam, T, col=TUNE.get('fc_col', 0.5))
    POST['bloom'] = 0.03
    studio3(T, 1.1, bg=7.0)
    POST['exposure'] = -0.35
    return sc


SHOTS = {
    'hands_S': (lambda: shot_hands('S'), 800, 1000, 128),
    'hands_M': (lambda: shot_hands('M'), 800, 1000, 128),
    'hands_L': (lambda: shot_hands('L'), 800, 1000, 128),
    'lineup': (shot_lineup, 2000, 1000, 128),
    'typing': (shot_typing, 1600, 1200, 128),
}

main()
