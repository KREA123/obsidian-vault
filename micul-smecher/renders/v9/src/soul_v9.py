"""soul_v9.py -- SOUL v9: the final shape is MĂRGĂRITAR (founder, 2026-09-26), at size M. Every image is a CGI concept.

Everything but the shape stays as v8: size M (glass Ø74.3, 2.8" round screen), 6061 aluminium bead-blasted and
anodised in Silver / Graphite / Midnight / Ember / Champagne, black glass with the machined 45 deg chamfer, nothing
on the front, flat polymer foot, the fine speaker slot in the +x girdle seam, charging contacts under the foot (OU
capsule), no loop. Same shots, same cameras, same studio.

How: v8 is loaded by exec (v8 -> v7 -> v6 -> v5, nothing duplicated), then the body is swapped:
  * the hull is MĂRGĂRITAR (renders/v5/src/alt_geo.py) at the v6 design scale -- its glass is already Ø52 like
    HOPA's, so v8's uniform scale K = 90 / 63 gives glass Ø74.3 again (marg_geo.py);
  * its back half is compressed in the section tables (not in the mesh as v8 did), so the depth is 31.5 mm at M;
  * the v6 machining is applied to it: chamfered glass seat, 0.6 mm speaker slot on the +x seam, 2 mic pinholes on
    the -x seam, flat cut at Z_CUT closed by the tone-matched polymer base plate, the oval polymer foot, contacts;
  * the OU liner is re-shaped for the flat foot: the SOUL stands upright on the liner floor and the liner hugs the
    lower body (+1 mm) instead of the old rocker-sole ellipsoid.

    blender -b --factory-startup --python soul_v9.py -- --shot hero [--preview] [--samples N] [--tmp DIR]
"""
import os
import sys

_V9 = os.path.dirname(os.path.abspath(__file__))
_V8S = os.path.abspath(os.path.join(_V9, '..', '..', 'v8', 'src'))
_me9 = __file__
__file__ = os.path.join(_V8S, 'soul_v8.py')
_src8 = open(__file__).read()
exec(compile(_src8[:_src8.rindex('\nmain()')], __file__, 'exec'), globals())
__file__ = _me9
_V9 = os.path.dirname(os.path.abspath(_me9))
TEX8 = os.path.join(_V9, 'tex')                      # hand meshes + the keyboard texture live in v9/src/tex
sys.path.insert(0, _V9)
import marg_geo as MG  # noqa: E402

CACHE9 = os.environ.get('SOUL_V9_CACHE', '/tmp/soul_v9_cache')
os.makedirs(CACHE9, exist_ok=True)
MB = MG.geo()
G_MM = MB.G().copy()                                 # glass centre of MĂRGĂRITAR (v6-scale mm)
Z_CUT, FOOT_H, Z_FOOT = MG.Z_CUT, MG.FOOT_H, MG.Z_FOOT
FOOT_A, FOOT_B, FOOT_P = 14.0, 6.9, 2.6              # 28 x 13.8 oval foot (the base is 37.8 x 16.1 here)
print('  v9 MARGARITAR: s_back %.3f dy %.2f G %s' % (MB.s_back, MB.dy, tuple(round(float(v), 2) for v in G_MM)))

# the slot / pin cutters of alt_v5.py (swept along an alternate's seam), taken from its source
_srcA = open(os.path.join(_V5, 'alt_v5.py')).read()
exec(compile(_srcA[_srcA.index('def alt_slot_cutter'):_srcA.index('ALT_SPEC = ')], os.path.join(_V5, 'alt_v5.py'),
             'exec'), globals())


def body_mesh(name):
    """MĂRGĂRITAR body with the v6 machining (cached). Roles: shell, sole, gap, chamfer (as v6's body_mesh)."""
    path = os.path.join(CACHE9, 'soul_body_v9_%d_%.4f_%g.npz' % (NU_BODY, MB.s_back, Z_CUT))
    if os.path.exists(path):
        ob, roles = load_mesh_cache(path, name)
    else:
        t0 = time.time()
        rows, bc, pole = MB.rows(NU=NU_BODY, n_shell=N_SHELL)
        Rn, N = rows.shape[:2]
        verts = np.vstack([rows.reshape(-1, 3), [bc], [pole]])
        quads = grid_quads(Rn, N)
        tris = np.vstack([fan(Rn * N, 0, N, top=False), fan(Rn * N + 1, (Rn - 1) * N, N, top=True)])
        ob = build_mesh(name, verts, quads, tris)
        orient_outward(ob, (0, 2, 35))
        for role in ('shell', 'sole'):
            ob.data.materials.append(bpy.data.materials.new('ROLE_' + role))
        gap_m = bpy.data.materials.new('ROLE_gap')
        ch_m = bpy.data.materials.new('ROLE_chamfer')
        seat = seat_cutter6('cut_seat')
        assign(seat, ch_m)
        cutters = [seat, alt_slot_cutter(MB, 'cut_slot', +1, 42.0, 54.0, width=TUNE.get('slot_w', 0.6)),
                   alt_pin_cutter(MB, 'cut_mic_a', -1, 46.0), alt_pin_cutter(MB, 'cut_mic_b', -1, 20.0)]
        for c in cutters[1:]:
            assign(c, gap_m)
        boolean(ob, cutters)
        roles = [m.name.replace('ROLE_', '').split('.')[0] for m in ob.data.materials]
        _truncate(ob, roles)
        save_mesh_cache(path, ob, roles)
        print('  v9 body mesh built + booleans %.1fs, %d faces, roles %s' % (time.time() - t0,
                                                                           len(ob.data.polygons), roles))
    _sharp_cap(ob)
    set_auto_smooth(ob, 35.0)
    _GEO['roles6'] = list(roles)
    return ob, [('gap' if r == 'chamfer' else r) for r in roles]


def seam_points(side, g=None, n=260):
    P, nrm = MB.seam(side, z0=Z_CUT + 1.2, n=n)
    return P, nrm


def split_groove_points():
    """No rocker sole: v6's build_soul removes the split groove; give v5 a tiny dummy loop."""
    t = np.linspace(0, 2 * math.pi, 16, endpoint=False)
    A = np.stack([np.cos(t), np.sin(t), np.full_like(t, 30.0)], 1)
    return A, np.zeros_like(A) + np.array([0, 0, 1.0])


# v8 compressed the finished mesh; v9 bakes the back compression into the sections -> plain v6 build_soul
build_soul = _build_soul6


# ==========================================================================================
# OU capsule: the liner for the flat foot
OU_CLR = 1.0          # liner clearance around the lower body (mm)
OU_RECESS = 1.0      # the foot sits in a 1 mm recess of the liner floor (foot outline + 0.5): it locates on the contacts
M_POSE_OU = Matrix.Translation((0, TUNE.get('ou_dy', -2.0) * MM, (9.0 - OU_RECESS - Z_FOOT - LAND_Z) * MM))


def _body_polar(z, n=720):
    """Body section at local z as radius(phi) about the foot centre (origin), + OU_CLR."""
    ring = MB.ring(max(z, Z_CUT), 2048)
    ph = np.arctan2(ring[:, 1], ring[:, 0])
    rr = np.hypot(ring[:, 0], ring[:, 1]) + OU_CLR
    o = np.argsort(ph)
    ph, rr = ph[o], rr[o]
    ph = np.concatenate([ph - 2 * math.pi, ph, ph + 2 * math.pi])
    rr = np.concatenate([rr, rr, rr])

    def f(q):
        return np.interp(q, ph, rr)
    return f


_BP = {}


def body_r(z, phi):
    zk = round(float(z) * 4) / 4
    if zk not in _BP:
        _BP[zk] = _body_polar(zk)
    return _BP[zk](phi)


def liner_mesh(tag):
    """Liner for the flat-foot SOUL: 2 mm lip at the rim -> inset wall (4.2) down until it meets the lower body
    + OU_CLR -> a pocket hugging the body down to the base -> the flat floor (z 9) the foot stands on."""
    ts = np.linspace(-math.pi / 2, 3 * math.pi / 2, OU_NU, endpoint=False)
    n_wall, n_bowl, n_floor = 26, 24, 8
    lip_o, lip_i = [], []
    walls = np.zeros((n_wall, OU_NU, 3))
    bowls = np.zeros((n_bowl, OU_NU, 3))
    z_floor_s = Z_FOOT + OU_RECESS   # soul-frame z of the liner floor (the foot sits 1 mm lower, in the recess)
    for j, t in enumerate(ts):
        tco = th_cut(t, 2.05)
        tci = th_cut(t, 4.2)
        po = ou_point(t, tco, 2.05) - PART_N * 0.05
        pi_ = ou_point(t, tci, 4.2) - PART_N * 0.05
        lip_o.append(po)
        lip_i.append(pi_)
        ths = np.linspace(tci, TH_MIN, 700)
        P = ou_point(t, ths, 4.2)
        Ps = _to_soul(P)
        hit = np.zeros(len(Ps), bool)
        for i, q in enumerate(Ps):
            if q[2] <= z_floor_s + 0.01:
                hit[i] = True
                break
            ph = math.atan2(q[1], q[0])
            if math.hypot(q[0], q[1]) <= body_r(q[2], ph):
                hit[i] = True
                break
        k = int(np.argmax(hit)) if hit.any() else len(ths) - 1
        thm = ths[max(k, 1)]
        walls[:, j] = ou_point(t, np.linspace(tci, thm, n_wall), 4.2)
        M = _to_soul(walls[-1, j])
        phi = math.atan2(M[1], M[0])
        zs = np.linspace(max(M[2], z_floor_s), z_floor_s, n_bowl)
        pts = []
        for zq in zs:
            rq = body_r(max(zq, Z_CUT), phi)
            rq = min(rq, math.hypot(M[0], M[1]))
            pts.append([rq * math.cos(phi), rq * math.sin(phi), zq])
        pts = np.array(pts)
        # blend the first pocket points from the wall end so the join is continuous
        pts[0] = M
        bowls[:, j] = _to_ou(pts)
    lip_o = np.array(lip_o)
    lip_i = np.array(lip_i)
    # floor: from the wall foot inward (z 9) to the foot outline + 0.5, down OU_RECESS, then in to the centre
    fs = _to_ou(np.array([[0.0, 0.0, Z_FOOT]]))[0]          # foot centre on the recess floor (OU frame)
    b = bowls[-1]
    ang = np.arctan2(b[:, 1] - fs[1], b[:, 0] - fs[0])
    c_, s_ = np.cos(ang), np.sin(ang)
    # superellipse radius of the foot outline (+0.5) along each direction
    A_, B_ = FOOT_A + 0.5, FOOT_B + 0.5
    rf = (np.abs(c_ / A_) ** FOOT_P + np.abs(s_ / B_) ** FOOT_P) ** (-1.0 / FOOT_P)
    rec = np.stack([fs[0] + rf * c_, fs[1] + rf * s_, np.full_like(c_, 9.0)], 1)
    n1 = n_floor
    top = np.array([b + (rec - b) * f for f in np.linspace(0, 1, n1)])
    top[:, :, 2] = 9.0
    wall_r = rec.copy()
    wall_r[:, 2] = 9.0 - OU_RECESS
    fc = np.array([fs[0], fs[1], 9.0 - OU_RECESS])
    inner = np.array([fc + (wall_r - fc) * f for f in np.linspace(1, 0.06, 6)])
    floor = np.concatenate([top, inner], 0)
    allrows = np.concatenate([lip_o[None], lip_i[None], walls[1:], bowls[1:], floor[1:]], 0)
    Rn = allrows.shape[0]
    verts = np.vstack([allrows.reshape(-1, 3), [fc]])
    quads = grid_quads(Rn, OU_NU)
    i_floor = 2 + (n_wall - 1) + (n_bowl - 1) - 1
    mq = np.repeat(np.where(np.arange(Rn - 1) >= i_floor, 1, 0), OU_NU)
    tris = fan(Rn * OU_NU, (Rn - 1) * OU_NU, OU_NU, top=True)
    ob = build_mesh(tag + '_liner', verts, quads, tris, mq, np.ones(OU_NU, int))
    orient_outward(ob, (0, 0, -60))
    print('  v9 liner: floor z %.2f, pocket depth %.1f..%.1f mm' % (
        fc[2], float((bowls[0, :, 2] - bowls[-1, :, 2]).min()), float((bowls[0, :, 2] - bowls[-1, :, 2]).max())))
    return ob, lip_i


# ==========================================================================================
# comparison: v9 dead front (the v8 'front' camera: same scale as soul_v8_front)
def shot_ou_check():
    """Check only: the empty OU liner from above (the foot recess)."""
    sc = reset()
    T = Vector((0, 0, 10 * MM))
    day_studio(T)
    build_ou('chk', 'perla', lid_open=True, night=False)
    cam_aed(T, TUNE.get('chk_az', 0.0), TUNE.get('chk_el', 70.0), 300.0, 100, 11.0, focus=T)
    return sc


# ==========================================================================================
# founder review (2026-10-01): no mug in desk / typing (its handle read as broken / floating), and the side view
# shows the screen dark (edge-on, the eyes read as a ghost on the glass edge).
_mug7 = mug


def mug(loc_mm, yaw):
    if TUNE.get('mug', 0) > 0:
        return _mug7(loc_mm, yaw)
    return new_par('mug_par')                # an empty: desk / typing keep their framing, no prop


def screen_off(par):
    g = SOULS[par.name]['glass']
    p = next(n for n in g.active_material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    set_in(p, 'Emission Strength', 0.0)


def shot_side9():
    sc = shot_side6()
    if TUNE.get('side_eyes', 0) <= 0:
        for k in list(SOULS):
            screen_off(bpy.data.objects[k])
    return sc


SHOTS['side'] = (_v8(shot_side9), 1600, 1200, 96)
SHOTS['ou_check'] = (shot_ou_check, 1000, 800, 64)
SHOTS['front'] = (_v8(_wrap(shot_front8, _post_generic)), 1600, 1600, 96)


# ==========================================================================================
# trailer v4 cut-outs (2026-10-02): transparent renders of the product for compositing in HTML.
#   film_transparent, the studio (sweep, cards, flags) kept for the reflections but hidden from camera rays, no DOF,
#   screen BLACK (the eyes / UI are drawn live in the trailer on top of the glass). Next to each render's EXR the
#   <stem>_glass.json gives the glass outline projected into the image (normalised 0..1, y down): the active
#   screen circle (r 21.88 mm v6 = 31.26 mm at M) and the glass edge (r 26), 96 points each, plus the eyes-up
#   direction, so the trailer can map a canvas exactly onto the glass. post_cut.py turns the EXR into an RGBA PNG.
#     blender -b --factory-startup --python soul_v9.py -- --shot cut_front --tmp DIR
CUT_KEEP = ('soul_', 'ou_')


def _cut_finish(sc, pars, W, H, glass_pars):
    """After a shot is built + scaled: transparent film, hide everything but the product from the camera,
    no DOF, black screens, and the projected glass outlines."""
    import json
    from bpy_extras.object_utils import world_to_camera_view
    sc.render.film_transparent = True
    try:
        sc.cycles.film_transparent_glass = False
    except Exception:
        pass

    def top(ob):
        while ob.parent is not None:
            ob = ob.parent
        return ob
    keep = set(p.name for p in pars)
    for ob in bpy.data.objects:
        if ob.type != 'MESH' and ob.type != 'CURVE':
            continue
        if top(ob).name in keep:
            continue
        ob.visible_camera = False          # sweep / cards / flags: still seen in reflections and as light
    cam = sc.camera
    cam.data.dof.use_dof = False
    cam.data.sensor_fit = 'VERTICAL' if H >= W else 'HORIZONTAL'
    cam.data.sensor_height = cam.data.sensor_width = 36.0
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 100
    for par in glass_pars:
        screen_off(par)
    bpy.context.view_layer.update()
    out = {}
    for par in glass_pars:
        g = SOULS[par.name]['glass']
        Mw = g.matrix_world
        rec = {}
        for key, r in (('screen', 21.88), ('glass', 26.0)):
            pts = []
            for i in range(96):
                a = 2 * math.pi * i / 96
                q = world_to_camera_view(sc, cam, Mw @ Vector((r * MM * math.cos(a), r * MM * math.sin(a), 0.15 * MM)))
                pts.append((round(q.x, 6), round(1 - q.y, 6)))
            rec[key] = pts
        for key, v in (('c', (0, 0)), ('ux', (21.88, 0)), ('uy', (0, 21.88))):
            q = world_to_camera_view(sc, cam, Mw @ Vector((v[0] * MM, v[1] * MM, 0.15 * MM)))
            rec[key] = (round(q.x, 6), round(1 - q.y, 6))
        out[par.name] = rec
    base = os.path.join(ARGS.tmp, ARGS.shot + ('_preview' if ARGS.preview else '') + (('_' + ARGS.tag) if ARGS.tag else ''))
    json.dump(dict(w=W, h=H, souls=out), open(base + '_glass.json', 'w'), indent=0)
    print('  v9 cut: glass outline ->', base + '_glass.json')
    return sc


def _cut_soul(cw, az, el, W, H, fov_mm, yaw=0.0, lens=135.0):
    """One SOUL of colour `cw`, seen from azimuth az / elevation el, framed so `fov_mm` (true size, vertical for
    a portrait frame) fills the frame."""
    sc = reset()
    T = Vector((0, -2 * MM, 35.5 * MM))
    TUNE.setdefault('mcard', 0.16)
    day_studio(T)
    s = build_soul('cut', cw, eyes='soul_front')
    pose_soul(s, (0, 0, 0), yaw=yaw)
    D = fov_mm * lens / 36.0 / K                      # pre-scale distance: the post-scale FOV is fov_mm
    cam = cam_aed(T, az, el, D, lens, 16.0, focus=eye_point(s))
    black_glass(cam, T, [s], glint=False)       # the glass sheen is drawn in the trailer, over the live eyes
    metalise(cam, T, [s])
    chamfer_kick(s, cam, TUNE.get('kick_ang', 128.0 if az <= 0 else 52.0), power=TUNE.get('kick', 1.2))
    scale_scene(K)
    return _cut_finish(sc, [s], W, H, [s])


def shot_cut_ou():
    """The OU capsule, lid open, a Silver SOUL standing in it (screen black), 3/4 from the left."""
    sc = reset()
    T = Vector((0, 0, 40 * MM))
    TUNE.setdefault('mcard', 0.16)
    day_studio(T)
    s = build_soul('ou', 'silver', eyes='soul_front')
    ou = build_ou('cut', 'perla', lid_open=True, night=False, soul=s)
    ou.location = V((0, 0, 0.5))
    ou.rotation_euler = (0, 0, R(TUNE.get('ou_yaw', 0.0)))
    bpy.context.view_layer.update()
    level_eyes(s)
    lens = 100.0
    D = TUNE.get('ou_fov', 150.0) * lens / 36.0 / K
    cam = cam_aed(T, TUNE.get('ou_az', -24.0), TUNE.get('ou_el', 14.0), D, lens, 16.0, focus=eye_point(s))
    black_glass(cam, T, [s], glint=False)
    metalise(cam, T, [s])
    scale_scene(K)
    return _cut_finish(sc, [ou], 1800, 1800, [s])


_CW_ALL = ('silver', 'graphite', 'midnight', 'ember', 'champagne')
SHOTS['cut_front'] = (lambda: _cut_soul('silver', 0.0, TUNE.get('front_el', 5.0), 2200, 2400, 112.0, lens=200.0),
                      2200, 2400, 96)
SHOTS['cut_l'] = (lambda: _cut_soul('silver', -32.0, 8.0, 1800, 2000, 118.0), 1800, 2000, 96)
SHOTS['cut_r'] = (lambda: _cut_soul('silver', 32.0, 8.0, 1800, 2000, 118.0), 1800, 2000, 96)
for _cw in _CW_ALL:
    SHOTS['cut_c_' + _cw] = ((lambda c=_cw: _cut_soul(c, -22.0, 7.0, 1400, 1600, 116.0)), 1400, 1600, 96)
SHOTS['cut_ou'] = (shot_cut_ou, 1800, 1800, 128)


def _setup_compositor_rgba(sc, base):
    fo = _setup_compositor5(sc, base)
    fo.format.color_mode = 'RGBA'
    return fo


_setup_compositor5 = setup_compositor
setup_compositor = _setup_compositor_rgba

main()
