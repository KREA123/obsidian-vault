"""film_v9.py -- the Blender shots of the SOUL launch film (renders/v9/film). Every frame is a CGI concept.

Loads soul_v9.py (MĂRGĂRITAR, size M) and adds the film shots; one Blender run = one frame / key state, the
string options come from the environment (FILM_EYES), the numbers from --set:
  f_rise    night desk, Graphite SOUL rises out of the OU liner (--set lift=<mm sunk, v6 scale>), eyes FILM_EYES
            ('off' = dark glass)
  f_orbit   silver SOUL, close 3/4 orbit about the crown shoulders (--set orb_az=<deg>)
  f_hand    the v8 hand shot, eyes FILM_EYES
  f_laptop  on the oak desk beside a generic laptop showing a chat box, eyes FILM_EYES
    blender -b --factory-startup --python film_v9.py -- --shot f_rise --set lift=40 --tag k3 --w 1920 --h 1080
"""
import os
import sys

_F9 = os.path.dirname(os.path.abspath(__file__))
_me_film = __file__
__file__ = os.path.join(_F9, 'soul_v9.py')
_src9 = open(__file__).read()
exec(compile(_src9[:_src9.rindex('\nmain()')], __file__, 'exec'), globals())
__file__ = _me_film
_F9 = os.path.dirname(os.path.abspath(_me_film))
FILM_TEX = os.path.join(_F9, '..', 'film', 'tex')


def _eyes():
    return os.environ.get('FILM_EYES', 'soul_front')


def shot_f_rise():
    TUNE.setdefault('win', 9.0)
    sc = reset()
    night_room()
    e = _eyes()
    s = build_soul('ou', os.environ.get('FILM_CW', 'graphite'), eyes=('soul_closed' if e == 'off' else e),
                   strength=0.8, glass_on=(e != 'off'))
    ou = build_ou('night', 'perla', lid_open=True, night=True, soul=s)
    ou.location = V((0, 0, 0.5))
    bpy.context.view_layer.update()
    foc = eye_point(s)
    lift = TUNE.get('lift', 0.0)
    s.matrix_basis = M_POSE_OU @ Matrix.Translation((0, 0, (LAND_Z - lift) * MM))
    level_eyes(s)
    T = Vector((0, 0, 45 * MM))
    cam_aed(T, TUNE.get('r_az', -24.0), TUNE.get('r_el', 16.0), TUNE.get('r_d', 440.0), 50, 2.8, focus=foc)
    POST['exposure'] = 0.4
    return sc


def shot_f_orbit():
    sc = reset()
    T = Vector((0, 2 * MM, TUNE.get('orb_tz', 50.0) * MM))
    TUNE.setdefault('mcard', 0.16)
    day_studio(T)
    s = build_soul('orb', os.environ.get('FILM_CW', 'silver'), eyes=_eyes())
    pose_soul(s, (0, 0, 0), yaw=0.0)
    cam = cam_aed(T, TUNE.get('orb_az', -40.0), TUNE.get('orb_el', 14.0), TUNE.get('orb_d', 250.0), 100, 8.0,
                  focus=eye_point(s))
    black_glass(cam, T, [s])
    metalise(cam, T, [s])
    chamfer_kick(s, cam, TUNE.get('kick_ang', 128.0), power=TUNE.get('kick', 1.2))
    return sc


def shot_f_hand():
    TUNE['hd_eyes'] = _eyes()
    return shot_hand8()


def laptop(yaw):
    """A generic laptop (304 x 212 mm, no brand): dark aluminium base and lid opened to 110 deg, the screen shows
    the chat box texture. True size, origin at the front centre of the base on the table."""
    par = new_par('laptop_par')
    alu = mat_simple('laptop_alu', '#4A4B4F', 0.38, metal=1.0)
    base = rounded_box('lap_base', 304 * MM, 212 * MM, 9 * MM, 4 * MM, 6)
    base.location = (0, 106 * MM, 4.5 * MM)
    assign(base, alu)
    kb = rounded_box('lap_kb', 270 * MM, 110 * MM, 0.6 * MM, 2 * MM, 4)
    kb.location = (0, 150 * MM, 9.1 * MM)
    assign(kb, mat_simple('lap_keys', '#141416', 0.6))
    hinge = new_par('lap_hinge')
    hinge.location = (0, 210 * MM, 9 * MM)
    lid = rounded_box('lap_lid', 304 * MM, 212 * MM, 6 * MM, 4 * MM, 6)
    lid.location = (0, -106 * MM, 3 * MM)
    assign(lid, alu)
    scr = rounded_box('lap_screen', 290 * MM, 190 * MM, 0.4 * MM, 1 * MM, 4)
    scr.location = (0, -104 * MM, -0.1 * MM)
    m, nt, p, out = new_mat('lap_screen')
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(os.path.join(FILM_TEX, 'laptop_chat.png'), check_existing=True)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1.0 / (290 * MM), -1.0 / (190 * MM), 1)   # lid -y = screen up
    mp.inputs['Location'].default_value = (0.5, 0.5, 0)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    nt.links.new(mp.outputs[0], tex.inputs['Vector'])
    set_in(p, 'Base Color', (0.01, 0.01, 0.01, 1))
    set_in(p, 'Roughness', 0.08)
    nt.links.new(tex.outputs['Color'], p.inputs['Emission Color'])
    set_in(p, 'Emission Strength', TUNE.get('lap_emit', 1.2))
    assign(scr, m)
    lid.parent = hinge
    scr.parent = hinge
    # lid local: its inner face (-z) toward the keyboard when closed; open by rotating about x
    for o in (lid, scr):
        o.matrix_parent_inverse = Matrix.Identity(4)
    scr.location = (0, -104 * MM, -0.2 * MM)
    scr.rotation_euler = (0, 0, 0)
    hinge.rotation_euler = (-R(TUNE.get('lap_open', 110.0)), 0, 0)
    parent_all(par, [base, kb, hinge])
    par.rotation_euler = (0, 0, R(yaw))
    return par


def shot_f_laptop():
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    root = props_root()
    sw = sweep('#D9CDBE', wall_y=TUNE.get('dk_wall', 0.95))
    sw.location = (0, 0, -0.0302)
    under(root, sw)
    dt = desk_top()
    dt.location = (0, 0.20, -0.015)
    under(root, dt)
    s = build_soul('lap', os.environ.get('FILM_CW', 'silver'), eyes=_eyes())
    pose_soul(s, (0, 0, 0), yaw=TUNE.get('lp_yaw', 22.0))
    lp = laptop(TUNE.get('lap_yaw', 12.0))
    under(root, lp, (TUNE.get('lap_x', -250.0), TUNE.get('lap_y', 40.0), 0.0))
    T = pk((TUNE.get('lp_tx', -60.0) * MM, TUNE.get('lp_ty', 40.0) * MM, TUNE.get('lp_tz', 60.0) * MM))
    cam = cam_aed(T, TUNE.get('lp_az', 18.0), TUNE.get('lp_el', 12.0), TUNE.get('lp_d', 900.0) / K, 60, 5.6,
                  focus=eye_point(s))
    black_glass(cam, T, [s], glint=True)
    metalise(cam, T, [s])
    chamfer_kick(s, cam, TUNE.get('kick_ang', 128.0), power=TUNE.get('kick', 1.1))
    studio(T, TUNE.get('dk_k', 1.5))
    POST['bloom'] = 0.03
    POST['exposure'] = -0.35
    return sc


SHOTS = {
    'f_rise': (_v8(shot_f_rise), 1920, 1080, 32),
    'f_orbit': (_v8(shot_f_orbit), 1920, 1080, 32),
    'f_hand': (_v8(shot_f_hand), 1920, 1080, 32),
    'f_laptop': (_v8(shot_f_laptop), 1920, 1080, 32),
}

main()
