"""soul_v8.py -- SOUL v8: the approved v6 SOUL at size M (2.8" round IPS, active dia ~70-71 mm). Every image is a
CGI concept.

The founder chose M and rejected the v7 size-study look (shape stretched, black ring thin, grey IPS glow). v8 is the
v6 design, unchanged, made bigger:

  * FRONT: the whole v6 body is scaled UNIFORMLY by K = 90 / 63 = 1.4286 in width and height -> 90.0 x 103.1 mm.
    Same outline, same glass-to-body ratio (glass dia 52 -> 74.3 mm), same black ring ratio (the screen image keeps
    v6's 21.88 / 26 mapping), same 45 deg chamfer (0.45 -> 0.64 mm), same seam, same CMF and colours.
  * DEPTH: 27 x K would be 38.6 mm. To land at ~31.5 mm without flattening the domed front (the v7 mistake was a
    uniform 0.80 squash of the whole depth), everything in front of the girdle seam (the domed face, the glass, the
    chamfer, the side roll) is scaled by exactly K, and only the back dome behind the seam is compressed, with a
    smooth C1 transition (compress_depth below).
  * The glass is true black when the pixels are black (no IPS glow: this is a concept render).

How: every v6 shot is built at v6 size by the unchanged v6/v5 code (so the glints, chamfer kicks, mirror cards and
studio are placed exactly as in v6), then the WHOLE scene is scaled by K about the origin (scale_scene): meshes by
their matrices, cameras and lights by position (area-light sizes x K, powers x K^2 so irradiance is unchanged,
focus distance x K). The only thing that does not scale is the aperture, so the depth of field reads like a bigger
object, as it should. New shots (hand, desk, typing) are built the same way, with the props (hand, phone, mug,
desk) modelled at their true size and shrunk by 1/K before the final scale.

    blender -b --factory-startup --python soul_v8.py -- --shot hero [--preview] [--samples N] [--tmp DIR]
"""
import os
import sys

_V8 = os.path.dirname(os.path.abspath(__file__))
_V7S = os.path.abspath(os.path.join(_V8, '..', '..', 'v7', 'src'))
_me8 = __file__
__file__ = os.path.join(_V7S, 'soul_v7.py')          # v7 -> v6 -> v5 resolve their own folders
_src7 = open(__file__).read()
exec(compile(_src7[:_src7.rindex('\nmain()')], __file__, 'exec'), globals())
__file__ = _me8
_V8 = os.path.dirname(os.path.abspath(_me8))
TEX8 = os.path.join(_V8, 'tex')

import hashlib  # noqa: E402

K = 90.0 / 63.0                                     # uniform front-view scale (63 x 72.2 -> 90 x 103.1 mm)
DEPTH8 = TUNE.get('depth', 31.5)                     # target overall depth (mm)
Y0 = TUNE.get('y0', -4.0)                           # local y (v6 mm) where the back compression starts (the seam)
YW = TUNE.get('yw', 6.0)                            # width of the smooth transition (v6 mm)
_H = {}


# ==========================================================================================
# geometry: the v6 body, back dome compressed so that K * depth = DEPTH8
def _hmap(y, s):
    """y -> y for y <= Y0; behind Y0 the slope eases from 1 to s over YW (smoothstep), C1-continuous."""
    y = np.asarray(y, float)
    t = np.clip((y - Y0) / YW, 0.0, 1.0)
    # integral of 1 - (1 - s) * smoothstep(t) dt from Y0: (y - Y0) - (1 - s) * YW * I(t)
    I = np.where(y - Y0 <= YW, t ** 3 - 0.5 * t ** 4, 0.5 + (y - Y0 - YW) / YW)
    out = Y0 + (y - Y0) - (1.0 - s) * YW * I
    return np.where(y <= Y0, y, out)


def _depth_setup(body):
    if 's' in _H:
        return _H['s']
    n = len(body.data.vertices)
    co = np.empty(n * 3, np.float32)
    body.data.vertices.foreach_get('co', co)
    y = co[1::3] / MM
    ymin, ymax = float(y.min()), float(y.max())
    target = DEPTH8 / K
    lo, hi = 0.05, 1.0
    for _ in range(60):
        s = 0.5 * (lo + hi)
        d = float(_hmap(ymax, s)) - ymin
        if d > target:
            hi = s
        else:
            lo = s
    _H.update(s=s, ymin=ymin, ymax=ymax)
    print('  v8 depth: v6 local y %.2f .. %.2f (%.2f mm) -> back slope %.3f -> %.2f mm x K = %.2f mm' % (
        ymin, ymax, ymax - ymin, s, float(_hmap(ymax, s)) - ymin, (float(_hmap(ymax, s)) - ymin) * K))
    return s


def compress_depth(par):
    """Apply the y-map to every part of a freshly built SOUL (par-local coordinates), except the glass and its gap
    ring, which sit wholly in front of Y0."""
    info = SOULS[par.name]
    s = _depth_setup(info['body'])
    for ob in par.children:
        if ob is info['glass'] or ob.name.endswith('_gapring'):
            continue
        Mb = np.array(ob.matrix_basis)
        A, t = Mb[:3, :3], Mb[:3, 3]
        Ai = np.linalg.inv(A)

        def fx(P):
            W = P @ A.T + t
            W[:, 1] = _hmap(W[:, 1] / MM, s) * MM
            return (W - t) @ Ai.T
        if ob.type == 'MESH':
            me = ob.data
            co = np.empty(len(me.vertices) * 3, np.float64)
            me.vertices.foreach_get('co', co)
            me.vertices.foreach_set('co', fx(co.reshape(-1, 3)).ravel())
            me.update()
        elif ob.type == 'CURVE':
            for sp in ob.data.splines:
                if len(sp.points):
                    P = np.array([p.co[:3] for p in sp.points])
                    Q = fx(P)
                    for p, q in zip(sp.points, Q):
                        p.co = (q[0], q[1], q[2], p.co[3])
                for bp in sp.bezier_points:
                    for attr in ('co', 'handle_left', 'handle_right'):
                        q = fx(np.array([getattr(bp, attr)[:]]))[0]
                        setattr(bp, attr, tuple(q))


_build_soul6 = build_soul


def build_soul(tag, cw='silver', sole=None, eyes='soul_front', strength=2.6, details=True, glass_on=True):
    par = _build_soul6(tag, cw, sole, eyes, strength, details, glass_on)
    compress_depth(par)
    return par


def set_screen(par, path, strength=None):
    g = SOULS[par.name]['glass']
    nt = g.active_material.node_tree
    node = next(n for n in nt.nodes if n.type == 'TEX_IMAGE')
    node.image = bpy.data.images.load(path, check_existing=True)
    if strength is not None:
        p = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        set_in(p, 'Emission Strength', strength)


def body_box_local(par):
    """Axis-aligned bounds of the (compressed) body, v6 local mm: centre and half sizes."""
    ob = SOULS[par.name]['body']
    co = np.empty(len(ob.data.vertices) * 3, np.float64)
    ob.data.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3) / MM
    lo, hi = co.min(0), co.max(0)
    return (lo + hi) / 2, (hi - lo) / 2


# ==========================================================================================
# the final uniform scale of the whole scene
ENV_TRUE = ('walnut',)


def scale_scene(k=K):
    bpy.context.view_layer.update()
    S = Matrix.Diagonal((k, k, k, 1.0))
    seen = set()
    for ob in list(bpy.data.objects):
        if ob.parent is not None:
            continue
        if ob.type == 'LIGHT':
            ob.location = ob.location * k
            ld = ob.data
            if ld.name in seen:
                continue
            seen.add(ld.name)
            if ld.type == 'AREA':
                ld.size *= k
                ld.size_y *= k
                ld.energy *= k * k
            elif ld.type in ('POINT', 'SPOT'):
                ld.shadow_soft_size *= k
                ld.energy *= k * k
        elif ob.type == 'CAMERA':
            ob.location = ob.location * k
            cd = ob.data
            cd.dof.focus_distance *= k
            cd.clip_start *= k
            cd.clip_end *= k
        elif ob.type == 'MESH' and ob.name.startswith(ENV_TRUE):
            # room surfaces with an Object-space texture (walnut): grow the mesh, not the object, so the grain
            # keeps its true size (a K-times coarser grain would shrink the SOUL back to v6 size by eye)
            ob.data.transform(Matrix.Diagonal((k, k, k, 1.0)))
            ob.location = ob.location * k
        else:
            ob.matrix_world = S @ ob.matrix_world
    bpy.context.view_layer.update()


def props_root(name='props8'):
    """Empty that shrinks true-size props by 1/K (scale_scene brings them back to their true size)."""
    r = new_par(name)
    r.scale = (1.0 / K,) * 3
    return r


def under(root, par, loc_mm=None):
    """Parent a true-size prop to the 1/K root; loc_mm is its true position."""
    if loc_mm is not None:
        par.location = V(loc_mm)
    par.parent = root
    par.matrix_parent_inverse = Matrix.Identity(4)
    return par


def pk(v_true_m):
    """A true-scale world position (metres) -> the pre-scale scene."""
    return Vector(v_true_m) / K


# ==========================================================================================
# shots
def _v8(fn):
    def run():
        sc = fn()
        scale_scene(K)
        return sc
    return run


def shot_front8():
    """Check: straight-on front at eye height (the v5 front_00 set-up)."""
    return shot_front(0.0)


def phone8(yaw):
    """A generic phone (71.5 x 147 x 7.8 mm), no brand: black glass front with a thin black border, a dark
    graphite frame. True size, local origin at its centre on the table."""
    ob = rounded_box('phone', 71.5 * MM, 147.0 * MM, 7.8 * MM, 3.6 * MM, 8)
    assign(ob, mat_simple('phone_frame', TUNE.get('ph_col', '#3B3C40'), 0.30, metal=1.0))
    gl = rounded_box('phone_glass', 70.4 * MM, 145.9 * MM, 0.6 * MM, 0.3 * MM, 4)
    gl.location = (0, 0, 3.65 * MM)
    m, nt, p, out = new_mat('phone_glass')
    set_in(p, 'Base Color', srgb('#030304'))
    set_in(p, 'Roughness', TUNE.get('ph_rough', 0.06))
    set_in(p, 'Specular IOR Level', 0.35)
    assign(gl, m)
    par = new_par('phone_par')
    parent_all(par, [ob, gl])
    par.rotation_euler = (0, 0, R(yaw))
    return par


def shot_desk():
    """SOUL M standing on a light-oak desk, a generic phone lying beside it and a mug behind, for scale."""
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    root = props_root()
    sw = sweep('#D9CDBE', wall_y=TUNE.get('dk_wall', 0.95))
    sw.location = (0, 0, -0.0302)
    under(root, sw)
    dt = desk_top()
    dt.location = (0, 0.20, -0.015)
    under(root, dt)
    s = build_soul('desk', 'silver', eyes=TUNE.get('dk_eyes', 'cream_look'))
    pose_soul(s, (TUNE.get('dk_x', 0.0) / K, TUNE.get('dk_y', 0.0) / K, 0), yaw=TUNE.get('dk_yaw', -18.0))
    ph = phone8(TUNE.get('ph_yaw', 74.0))
    under(root, ph, (TUNE.get('ph_x', -118.0), TUNE.get('ph_y', -40.0), 3.9))
    mg = mug((0, 0), TUNE.get('mug_yaw', -40.0))
    under(root, mg, (TUNE.get('mug_x', 118.0), TUNE.get('mug_y', 70.0), 0.0))
    T = pk((TUNE.get('dk_tx', 0.0) * MM, TUNE.get('dk_ty', 10.0) * MM, TUNE.get('dk_tz', 38.0) * MM))
    cam = cam_aed(T, TUNE.get('dk_az', -24.0), TUNE.get('dk_el', 17.0), TUNE.get('dk_d', 780.0) / K,
                  TUNE.get('dk_lens', 60.0), TUNE.get('dk_f', 5.6), focus=eye_point(s))
    black_glass(cam, T, [s], glint=True)
    metalise(cam, T, [s])
    chamfer_kick(s, cam, TUNE.get('kick_ang', 128.0), power=TUNE.get('kick', 1.1))
    studio(T, TUNE.get('dk_k', 1.5))
    POST['bloom'] = 0.03
    POST['exposure'] = -0.35
    return sc


def shot_typing8():
    """SOUL M standing on the desk, the SoulOS keyboard (soulos3) on the glass; seen from the typing position."""
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    root = props_root()
    sw = sweep('#D9CDBE', wall_y=TUNE.get('dk_wall', 0.95))
    sw.location = (0, 0, -0.0302)
    under(root, sw)
    dt = desk_top()
    dt.location = (0, 0.20, -0.015)
    under(root, dt)
    s = build_soul('ty', 'silver', eyes='soul_front')
    pose_soul(s, (0, 0, 0), yaw=TUNE.get('ty_yaw', -10.0))
    set_screen(s, os.path.join(TEX8, 'kbd_soulos3.png'), TUNE.get('kbd_str', 2.4))
    mg = mug((0, 0), TUNE.get('mug_yaw', -60.0))
    under(root, mg, (TUNE.get('mug_x', 150.0), TUNE.get('mug_y', 150.0), 0.0))
    T = pk((0.0, TUNE.get('ty_ty', -4.0) * MM, TUNE.get('ty_tz', 50.0) * MM))
    cam = cam_aed(T, TUNE.get('ty_az', -14.0), TUNE.get('ty_el', 24.0), TUNE.get('ty_d', 470.0) / K,
                  TUNE.get('ty_lens', 85.0), TUNE.get('ty_f', 5.6), focus=eye_point(s))
    black_glass(cam, T, [s], glint=TUNE.get('ty_glint', 1) > 0, d=TUNE.get('ty_gd', 0.80))
    metalise(cam, T, [s])
    chamfer_kick(s, cam, TUNE.get('kick_ang', 128.0), power=TUNE.get('kick', 1.1))
    studio(T, TUNE.get('dk_k', 1.5))
    POST['bloom'] = 0.03
    POST['exposure'] = -0.35
    return sc


def _hand_npz(args):
    key = hashlib.md5(','.join(args).encode()).hexdigest()[:10]
    d = os.path.join(TEX8, 'hand_' + key)
    p = os.path.join(d, 'hand.npz')
    if not os.path.exists(p):
        import subprocess
        os.makedirs(d, exist_ok=True)
        subprocess.run(['python3', os.path.join(_V8, 'hand_sdf_v8.py'), p] + args, check=True)
    return d


_LIFT = {}


def shot_hand8():
    """SOUL M lying face-up in the same stylised right hand as v4-v6, which now cradles it like a large pebble.
    The device pose is chosen in hand coordinates; the hand mesh is generated with the device carved out of it."""
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    root = props_root()
    sw = sweep('#CDBFAE', wall_y=0.55)
    under(root, sw)
    s = build_soul('hand', 'silver', eyes=TUNE.get('hd_eyes', 'cream_down'))
    ctr, half = body_box_local(s)
    # device pose in hand coordinates (true mm): face up, crown toward the fingers
    Rot = (Euler((R(TUNE.get('hd_rx', 20.0)), R(TUNE.get('hd_ry', -6.0)), R(TUNE.get('hd_rz', 8.0)))).to_matrix()
           @ Matrix.Rotation(R(-90), 3, 'X'))
    hK = half * K
    c_h = Vector((TUNE.get('hd_cx', 2.0), TUNE.get('hd_cy', 2.0), TUNE.get('hd_cz', 14.0 + hK[1])))
    ax = [Rot @ Vector(e) for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
    args = ['bx_cx=%.2f' % c_h.x, 'bx_cy=%.2f' % c_h.y, 'bx_cz=%.2f' % c_h.z,
            'bx_hw=%.2f' % hK[0], 'bx_hd=%.2f' % hK[1], 'bx_hh=%.2f' % hK[2], 'bx_r=%.2f' % TUNE.get('hd_br', 13.0)]
    for i, a_ in enumerate(ax):
        args += ['bx_x%d=%.4f' % (i, a_.x), 'bx_y%d=%.4f' % (i, a_.y), 'bx_z%d=%.4f' % (i, a_.z)]
    for kk in ('fk', 'f0', 'cup_z', 'cup_r', 't_yaw', 't_f1', 't_f2', 't_f3', 't_side', 'carve_k'):
        if 'hd_' + kk in TUNE:
            args.append('%s=%g' % (kk, TUNE['hd_' + kk]))
    global TEX
    hd = _hand_npz(args)
    _LIFT['v'] = float(np.load(os.path.join(hd, 'hand.npz'))['lift'])
    t0, TEX = TEX, hd
    try:
        hand = build_hand_v4('hand', (0.0, 0.0, 0.030), TUNE.get('hd_yaw', 18.0))
    finally:
        TEX = t0
    lift = _LIFT.get('v', 0.0)
    c_h = c_h - ax[1] * lift
    print('  hand: device lifted %.2f mm along its face normal' % lift)
    HM = Matrix.Translation((0.0, 0.0, 0.030)) @ Matrix.Rotation(R(TUNE.get('hd_yaw', 18.0)), 4, 'Z')
    under(root, hand)
    hand.matrix_basis = HM
    # the SOUL (pre-scale scene): S(1/K) @ HM @ T(c_h) @ Rot @ S(K) @ T(-ctr)
    D = Matrix.Translation(c_h * MM) @ Rot.to_4x4() @ Matrix.Diagonal((K, K, K, 1.0)) @ Matrix.Translation(-V(ctr))
    s.matrix_world = Matrix.Diagonal((1 / K, 1 / K, 1 / K, 1.0)) @ HM @ D
    bpy.context.view_layer.update()
    level_eyes(s)
    T = pk(HM @ (c_h * MM))
    cam = camera(T + Vector((TUNE.get('hc_x', 0.13), TUNE.get('hc_y', -0.30), TUNE.get('hc_z', 0.15))), T,
                 lens=TUNE.get('hd_lens', 70.0), fstop=TUNE.get('hd_f', 5.6), focus=eye_point(s))
    flag(cam, T)
    mirror_card(s, cam)
    glint_strip(s, cam)
    POST['bloom'] = 0.03
    studio3(T, 1.1, bg=7.0)
    POST['exposure'] = -0.35
    metal_front_card(cam, None, col=TUNE.get('fc_col', 0.5))
    return sc


SHOTS = {
    'hero': (_v8(shot_hero6), 1600, 1200, 128),
    'family': (_v8(_wrap(shot_family6, _post_family)), 2000, 1125, 96),
    'side': (_v8(shot_side6), 1600, 1200, 96),
    'ou_night': (_v8(shot_ou_night6), 1600, 1200, 128),
    'hand': (_v8(shot_hand8), 1600, 1200, 128),
    'desk': (_v8(shot_desk), 1600, 1200, 128),
    'typing': (_v8(shot_typing8), 1600, 1200, 128),
    'alive': (_v8(shot_alive), 720, 720, 64),
    'front': (_v8(_wrap(shot_front8, _post_generic)), 1600, 1600, 96),
}

main()
