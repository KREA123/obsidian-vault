"""film2_v9.py -- SOUL launch film v2: real animated shots in a dark studio (CGI concept). One Blender run renders
one shot as an animation (24 fps timeline, every 2nd frame rendered; film_assemble2.py interpolates to 24 fps).
Camera and object moves are keyframed with ease in/out, motion blur on, DOF on, the eyes play the v6 'alive'
sequence (blink, glance, look back at the camera).
  s_reveal   Graphite rotates in from darkness, rim lights trace the MĂRGĂRITAR silhouette, the eyes light up
  s_macro    Silver, slow macro arc over the crown shoulders and the chamfer, f/2.8
  s_eyes     Graphite 3/4, slow push-in, the eyes blink and look at the camera
  s_family   the 5 colours in a row, slow lateral dolly
    blender -b --factory-startup --python film2_v9.py -- --shot s_reveal --tmp DIR [--frames a:b] [--samples N]
"""
import os
import sys

_F2 = os.path.dirname(os.path.abspath(__file__))
_me_f2 = __file__
__file__ = os.path.join(_F2, 'soul_v9.py')
_src9 = open(__file__).read()
exec(compile(_src9[:_src9.rindex('\nmain()')], __file__, 'exec'), globals())
__file__ = _me_f2

ALIVE = '/tmp/soul_v6_cache/alive_eyes/eyes_alive_0001.png'
NF = 120                      # 5 s at 24 fps


def ez(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def dark_studio(T, rim=1.0, key=1.0):
    world_color((0.012, 0.012, 0.014), 0.003)
    fl = plane('floor', (6, 6), (0, 0, 0), (0, 0, 0), mat_simple('floor_dark', '#0A0A0B', TUNE.get('floor_r', 0.32)))
    L = []
    # two strip rims behind the body: they trace the silhouette and slide along the anodised roll as it turns
    L.append(area_light('rimL', T + Vector((-0.22, 0.26, 0.10)), T, 0.03, 5.0 * rim, blackbody_rgb(5600), 'RECTANGLE',
                        size_y=0.55))
    L.append(area_light('rimR', T + Vector((0.24, 0.22, 0.07)), T, 0.03, 4.0 * rim, blackbody_rgb(3800), 'RECTANGLE',
                        size_y=0.55))
    # soft top key and a very faint warm front fill
    L.append(area_light('top', T + Vector((0.0, 0.02, 0.50)), T, 0.55, 1.1 * key, blackbody_rgb(5000)))
    L.append(area_light('fill', T + Vector((-0.35, -0.35, 0.06)), T, 0.4, 0.12 * key, blackbody_rgb(3200),
                        glossy=False))
    # a long thin strip only the glass and the metal see: the glint that slides across as things move
    g = area_light('glint', T + Vector((-0.10, -0.30, 0.30)), T, 0.012, 1.4, blackbody_rgb(6000), 'RECTANGLE',
                   size_y=0.5)
    g.visible_diffuse = False
    L.append(g)
    POST['exposure'] = TUNE.get('f2_exp', -0.1)
    POST['bloom'] = 0.04
    POST['anim'] = True
    return fl, L


def cam_track(T, lens, fstop, focus_pt):
    cam = camera(Vector((0, -0.4, 0.05)), T, lens=lens, fstop=fstop, focus=focus_pt)
    tgt = bpy.data.objects.new('cam_target', None)
    bpy.context.scene.collection.objects.link(tgt)
    tgt.location = T
    c = cam.constraints.new('TRACK_TO')
    c.target = tgt
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    cam.data.dof.focus_object = None
    return cam, tgt


def aed(T, A, E, D):
    return Vector(T) + Vector((math.sin(R(A)) * math.cos(R(E)), -math.cos(R(A)) * math.cos(R(E)), math.sin(R(E)))) * D


def anim_cam(cam, tgt, T, path, n=NF):
    """path(t) -> (A, E, D_m, T_offset Vector) in the SCALED world; keyframe every 4 frames (smooth Bezier)"""
    for f in range(1, n + 1, 4):
        t = (f - 1) / (n - 1)
        A, E, D, dT = path(t)
        cam.location = aed(T + dT, A, E, D)
        cam.keyframe_insert('location', frame=f)
        tgt.location = T + dT
        tgt.keyframe_insert('location', frame=f)
    f = n
    A, E, D, dT = path(1.0)
    cam.location = aed(T + dT, A, E, D)
    cam.keyframe_insert('location', frame=f)
    tgt.location = T + dT
    tgt.keyframe_insert('location', frame=f)


def eyes_sequence(par, offset=0, strength_keys=None):
    g = SOULS[par.name]['glass']
    nt = g.active_material.node_tree
    node = next(n for n in nt.nodes if n.type == 'TEX_IMAGE')
    img = bpy.data.images.load(ALIVE, check_existing=False)
    img.source = 'SEQUENCE'
    node.image = img
    iu = node.image_user
    iu.frame_duration = 120
    iu.frame_start = 1
    iu.frame_offset = offset
    iu.use_cyclic = True
    iu.use_auto_refresh = True
    if strength_keys:
        p = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        sock = p.inputs['Emission Strength']
        for f, v in strength_keys:
            sock.default_value = v
            sock.keyframe_insert('default_value', frame=f)


def _setup_anim(sc, n=NF):
    sc.render.fps = 24
    sc.frame_start, sc.frame_end = 1, n
    sc.frame_step = int(TUNE.get('fstep', 2))
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = 0.5


def shot_s_reveal():
    sc = reset()
    T0 = Vector((0, 0, 38 * MM))
    dark_studio(T0, rim=1.2, key=0.8)
    s = build_soul('rv', 'graphite', eyes='soul_front', strength=2.6)
    pose_soul(s, (0, 0, 0), yaw=0.0)
    cam = camera(aed(T0, -8.0, 6.0, 0.44), T0, lens=85, fstop=4.0, focus=eye_point(s))
    scale_scene(K)
    _setup_anim(sc)
    # the body turns in from the dark: yaw -115 -> -12 over 4.2 s (ease), then holds
    base = s.matrix_world.copy()
    for f in range(1, NF + 1, 4):
        t = ez((f - 1) / 100.0)
        yaw = -115.0 + 103.0 * t
        s.matrix_world = base @ Matrix.Rotation(R(yaw), 4, 'Z')
        s.keyframe_insert('rotation_euler', frame=f)
        s.keyframe_insert('location', frame=f)
    s.matrix_world = base @ Matrix.Rotation(R(-12.0), 4, 'Z')
    s.keyframe_insert('rotation_euler', frame=NF)
    s.keyframe_insert('location', frame=NF)
    # rims fade up first, the eyes light up at ~3.2 s
    for nm, v0 in (('rimL', 0.0), ('rimR', 0.0)):
        ob = bpy.data.objects[nm]
        e1 = ob.data.energy
        ob.data.energy = e1 * 0.02
        ob.data.keyframe_insert('energy', frame=1)
        ob.data.energy = e1
        ob.data.keyframe_insert('energy', frame=40)
    eyes_sequence(s, offset=0, strength_keys=[(1, 0.0), (72, 0.0), (86, 2.6)])
    cam.location = cam.location * 1.0
    # slow dolly in
    T = T0 * K
    c0 = Vector(cam.location)
    for f in (1, NF):
        t = (f - 1) / (NF - 1)
        cam.location = T + (c0 - T) * (1.0 - 0.10 * t)
        cam.keyframe_insert('location', frame=f)
    cam.data.dof.focus_distance = (Vector(cam.location) - eye_point(s)).length
    return sc


def shot_s_macro():
    sc = reset()
    T0 = Vector((0, 0, 58 * MM))
    dark_studio(T0, rim=1.3, key=1.0)
    s = build_soul('mc', os.environ.get('F2_CW', 'silver'), eyes='soul_front', strength=2.6)
    pose_soul(s, (0, 0, 0), yaw=0.0)
    foc = s.matrix_world @ V(G_MM + np.array([-18.0, 0.0, 22.0]))      # the upper-left shoulder at the chamfer
    cam, tgt = cam_track(T0, 100, 2.8, foc)
    scale_scene(K)
    _setup_anim(sc)
    T = T0 * K
    anim_cam(cam, tgt, T, lambda t: (-58.0 + 40.0 * ez(t), 22.0 - 6.0 * ez(t), 0.23 * K, Vector((0, 0, 0))))
    cam.data.dof.focus_distance = (Vector(aed(T, -38.0, 19.0, 0.23 * K)) - Vector(foc) * K).length
    eyes_sequence(s, offset=0)
    return sc


def shot_s_eyes():
    sc = reset()
    T0 = Vector((0, -2 * MM, 40 * MM))
    dark_studio(T0, rim=1.1, key=1.1)
    s = build_soul('ey', 'graphite', eyes='soul_front', strength=2.6)
    pose_soul(s, (0, 0, 0), yaw=-6.0)
    foc = eye_point(s)
    cam, tgt = cam_track(T0, 100, 4.0, foc)
    scale_scene(K)
    _setup_anim(sc)
    T = T0 * K
    anim_cam(cam, tgt, T, lambda t: (-16.0 + 8.0 * ez(t), 5.0, (0.52 - 0.10 * ez(t)) * K, Vector((0, 0, 0))))
    cam.data.dof.focus_distance = (Vector(aed(T, -12.0, 5.0, 0.47 * K)) - Vector(foc) * K).length
    eyes_sequence(s, offset=0)
    return sc


def shot_s_family():
    sc = reset()
    T0 = Vector((0, 0, 36 * MM))
    dark_studio(T0, rim=1.2, key=1.0)
    pitch = 63.0 + 16.0
    pars = []
    for i, cw in enumerate(('graphite', 'ember', 'silver', 'midnight', 'champagne')):
        p = build_soul('fm%d' % i, cw, eyes='soul_front', strength=2.6)
        pose_soul(p, ((i - 2) * pitch, abs(i - 2) * 12.0, 0), yaw=-(i - 2) * 6.0)
        pars.append(p)
    # the rims sit behind the whole row: widen them
    for nm in ('rimL', 'rimR'):
        ob = bpy.data.objects[nm]
        ob.location.x *= 2.4
        ob.data.size_y = 0.8
        aim(ob, T0)
    cam, tgt = cam_track(T0, 50, 5.6, pars[2].matrix_world @ V(G_MM))
    scale_scene(K)
    _setup_anim(sc)
    T = T0 * K
    anim_cam(cam, tgt, T, lambda t: (-12.0 + 18.0 * ez(t), 7.0, 0.72 * K,
                                     Vector(((-0.02 + 0.04 * ez(t)) * K, 0, 0))))
    cam.data.dof.focus_distance = 0.72 * K
    for i, p in enumerate(pars):
        eyes_sequence(p, offset=0)
    return sc


SHOTS = {
    's_reveal': (shot_s_reveal, 1920, 1080, 24),
    's_macro': (shot_s_macro, 1920, 1080, 24),
    's_eyes': (shot_s_eyes, 1920, 1080, 24),
    's_family': (shot_s_family, 1920, 1080, 24),
}

main()
