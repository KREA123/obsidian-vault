"""soul_v10.py -- SOUL v10: the final product size S (founder decision 2026-10-20). Every image is a CGI concept.

SOUL S = MĂRGĂRITAR (v9) at its native design scale: the marg_geo.py "local" geometry, 62.96 x 70.8 mm (incl. the
1.2 mm polymer foot), flat black glass Ø52, round 1.75" AMOLED 466 x 466 behind it (true black). Depth 23.0 mm
(docs/size-s.json): only the back half behind the seam is compressed, by s_back = 0.807 (the M renders used 0.735;
the uncompressed shape is 25.65 mm). Everything else is v9: the same CMF and 5 colours, the same studio, cameras,
lights and post. The v9 set is built at this scale and then enlarged by K = 90 / 63; v10 simply sets K = 1.

How: marg_geo's cached body is replaced by MargaritarV9(depth 23.0) BEFORE v9 is loaded (v9 -> v8 -> v7 -> v6 -> v5
by exec, nothing duplicated), then K = 1. Props (hand, desk, phone) are modelled at their true size by v8, so with
K = 1 the S reads at its true size next to them. New here:
  * hand: the v8 hand and its carving, with the camera kept at the v9 TRUE distance (an S in the same adult hand,
    so it reads smaller than the M did, as it is);
  * vs_m: S and M side by side on the desk (both MĂRGĂRITAR; M = the v9 body x K with s_back 0.735).

    blender -b --factory-startup --python soul_v10.py -- --shot hero [--preview] [--samples N] [--tmp DIR]
"""
import os
import sys

_V10 = os.path.dirname(os.path.abspath(__file__))
_V9S = os.path.abspath(os.path.join(_V10, '..', '..', 'v9', 'src'))
sys.path.insert(0, _V9S)
import marg_geo as _MG  # noqa: E402

DEPTH_S = 23.0                                        # docs/size-s.json dims_mm.d
_MG._B['b'] = _MG.MargaritarV9(depth_m=DEPTH_S * _MG.K)   # depth() is compared with depth_m / K
_MB_M = _MG.MargaritarV9()                            # the M body (v9, 31.5 mm at K) for the comparison shot

_me10 = __file__
__file__ = os.path.join(_V9S, 'soul_v9.py')
_src9 = open(__file__).read()
exec(compile(_src9[:_src9.rindex('\nmain()')], __file__, 'exec'), globals())
__file__ = _me10
_V10 = os.path.dirname(os.path.abspath(_me10))

K_M = K                                               # 90 / 63: the M scale, kept for the comparison
K = 1.0                                               # size S: the v9 scene at its design scale
TEX8 = os.environ.get('SOUL_V10_TEX', '/tmp/soul_v10_tex')   # hand-mesh cache (not committed)
os.makedirs(TEX8, exist_ok=True)
_kbd = os.path.join(TEX8, 'kbd_soulos3.png')
if not os.path.exists(_kbd) and os.path.exists(os.path.join(_V9S, 'tex', 'kbd_soulos3.png')):
    import shutil
    shutil.copy(os.path.join(_V9S, 'tex', 'kbd_soulos3.png'), _kbd)
_zz = np.linspace(Z_CUT, MB.H, 3000)
_w, _yf, _yb = MB.sections(_zz)[:3]
print('  v10 SOUL S: s_back %.4f  W %.2f  H %.2f  D %.2f  glass Ø%.1f  G %s' % (
    MB.s_back, 2 * _w.max(), MB.H - Z_FOOT, _yb.max() - _yf.min(), 2 * MB.r_glass,
    tuple(round(float(v), 2) for v in G_MM)))


# ==========================================================================================
# hand: same hand / carving as v8-v9; camera offsets kept at the v9 TRUE size (pre-scale offsets x K_M)
def shot_hand10():
    for k, v in (('hc_x', 0.13), ('hc_y', -0.30), ('hc_z', 0.15)):
        TUNE.setdefault(k, v * TUNE.get('hc_k', 0.80 * K_M))
    TUNE.setdefault('hd_br', 9.0)
    return shot_hand8()


# ==========================================================================================
# S next to M, on the desk
def build_soul_m(tag, cw, eyes):
    """A SOUL M (v9 body, s_back 0.735) built at design scale: the body and glass globals are swapped while it is
    built, then restored. Scale it by K_M about its foot with scale_about_foot()."""
    global MB, G_MM
    MB_s, G_s = MB, G_MM
    MB, G_MM = _MB_M, _MB_M.G().copy()
    try:
        par = build_soul(tag, cw, eyes=eyes)
    finally:
        MB, G_MM = MB_s, G_s
    return par


def scale_about_foot(par, k, loc_mm):
    P = V((loc_mm[0], loc_mm[1], 0.0))
    par.matrix_world = Matrix.Translation(P) @ Matrix.Diagonal((k, k, k, 1.0)) @ Matrix.Translation(-P) @ par.matrix_world
    bpy.context.view_layer.update()


def shot_vs_m():
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    root = props_root()
    sw = sweep('#D9CDBE', wall_y=TUNE.get('dk_wall', 0.95))
    sw.location = (0, 0, -0.0302)
    under(root, sw)
    dt = desk_top()
    dt.location = (0, 0.20, -0.015)
    under(root, dt)
    xs, xm = TUNE.get('vs_xs', -42.0), TUNE.get('vs_xm', 40.0)
    s = build_soul('vss', 'silver', eyes=TUNE.get('vs_eyes_s', 'cream_look'))
    pose_soul(s, (xs, 0, 0), yaw=TUNE.get('vs_yaw', -12.0))
    m = build_soul_m('vsm', 'silver', TUNE.get('vs_eyes_m', 'cream_look'))
    pose_soul(m, (xm, 0, 0), yaw=TUNE.get('vs_yaw', -12.0))
    scale_about_foot(m, K_M, (xm, 0))
    level_eyes(m)
    T = V((TUNE.get('vs_tx', 0.0), TUNE.get('vs_ty', 0.0), TUNE.get('vs_tz', 46.0)))
    cam = cam_aed(T, TUNE.get('vs_az', -14.0), TUNE.get('vs_el', 9.0), TUNE.get('vs_d', 640.0),
                  TUNE.get('vs_lens', 75.0), TUNE.get('vs_f', 8.0), focus=T)
    black_glass(cam, T, [s, m], glint=True)
    metalise(cam, T, [s, m])
    chamfer_kick(s, cam, TUNE.get('kick_ang', 128.0), power=TUNE.get('kick', 1.1))
    chamfer_kick(m, cam, TUNE.get('kick_ang', 128.0), power=TUNE.get('kick', 1.1), name='kick_m')
    studio(T, TUNE.get('dk_k', 1.5))
    POST['bloom'] = 0.03
    POST['exposure'] = -0.35
    return sc


def shot_desk10():
    """v9 desk (true-size phone, oak desk), the camera brought in so the 63 mm SOUL fills the frame as the M did."""
    for k, v in (('dk_d', 560.0), ('dk_tz', 30.0), ('ph_x', -90.0), ('ph_y', 34.0), ('ph_yaw', 14.0), ('dk_ty', 4.0)):
        TUNE.setdefault(k, v)
    return shot_desk()


SHOTS['hand'] = (_v8(shot_hand10), 1600, 1200, 128)
SHOTS['desk'] = (_v8(shot_desk10), 1600, 1200, 128)
SHOTS['vs_m'] = (_v8(shot_vs_m), 2000, 1125, 128)

main()
