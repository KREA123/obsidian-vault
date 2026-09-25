"""soul_v4.py -- SOUL family v4: the v1 silhouettes (PEBBLE, CLOUD, DROP, AMULET) brought back BIGGER,
without any loop or bail, standing upright on a small flat base.

Front = only the glossy body + the big black domed glass (Ø49, true-black border ink so the whole glass reads
as screen; Ø44 active AMOLED with the living eyes of eyes.py) and one hair-thin polished ring. Speaker = a fine
slot on the right side edge; charging = two gold pogo contacts on the flat bottom. Body: glossy injection-moulded
PC with a pearl sheen, in pearl white / sage / sand / peach / lilac.

Reuses concepts.py -> soul_scene.py (the v1 scene evolved: materials, studio lights, black flags for the screen,
EXR + post.py OIDN/AgX pipeline). Outlines of CLOUD / DROP / AMULET come from ../../../cad/gen_shapes.py (v1).

    blender -b --factory-startup --python soul_v4.py -- --shot family [--preview] [--samples N] [--tmp DIR]
Shots: family pebble cloud drop amulet hand scale capsule
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(_HERE, 'concepts.py')).read()
exec(compile(_src[:_src.rindex('\nmain()')], os.path.join(_HERE, 'concepts.py'), 'exec'), globals())

H4 = 9.0            # half thickness (18 mm body)
R_GL = 24.5         # black glass radius (Ø49)
R_RING = 24.9       # hair-thin polished ring outer radius
R_REC4 = 25.0       # recess radius in the body
FIL4 = 0.7
TINTS = {'pearl': '#EEEEEC', 'sage': '#B9C7B3', 'sand': '#E0D0B6', 'peach': '#F2D2C2', 'lilac': '#D5CCE6'}


# ------------------------------------------------------------------------------------------
# outlines (mm, screen centre at the origin, +y up), all star-shaped around the screen centre
def _resample(P, n=360):
    P = np.asarray(P, float)
    Q = np.vstack([P, P[:1]])
    seg = np.linalg.norm(np.diff(Q, axis=0), axis=1)
    L = np.concatenate([[0], np.cumsum(seg)])
    s = np.linspace(0, L[-1], n, endpoint=False)
    return np.stack([np.interp(s, L, Q[:, 0]), np.interp(s, L, Q[:, 1])], 1)


def _smooth(P, it=3, w=0.5):
    P = np.asarray(P, float)
    for _ in range(it):
        P = P * (1 - w) + w * 0.5 * (np.roll(P, 1, 0) + np.roll(P, -1, 0))
    return P


def _flat_base(P, cut):
    """Flatten the bottom: clamp y to ymin + cut, then soften the two corners."""
    P = np.array(P, float)
    y0 = P[:, 1].min() + cut
    P[:, 1] = np.maximum(P[:, 1], y0)
    P = _resample(P)
    P = _smooth(P, 6, 0.5)
    return P


def outline_v4(name):
    if name == 'amulet':
        t = np.linspace(0, 2 * np.pi, 360, endpoint=False)
        P = np.stack([32.0 * np.cos(t), 32.0 * np.sin(t)], 1)
        P = _flat_base(P, 1.6)
    elif name == 'pebble':
        # upright egg 64 x 72, wider at the top, screen centre 6 mm above the egg centre
        t = np.linspace(0, 2 * np.pi, 360, endpoint=False)
        yc = -6.0
        y = 36.0 * np.sin(t)
        x = 32.0 * np.cos(t) * (1 + 0.045 * np.sin(t))
        P = np.stack([x, y + yc], 1)
        P = _flat_base(P, 2.2)
    else:
        S = G.build()
        cfg = {'cloud': (84.0, 66.0, 40, 4.0), 'drop': (64.0, 80.0, 6, 2.0)}[name]
        W, Hh, sm, dy = cfg
        P = list(S[name]['P'])
        if sm:
            P = G.smooth(P, sm)
        P = np.array(P, float)
        P[:, 1] *= -1 if False else 1
        sx = W / np.ptp(P[:, 0])
        sy = Hh / np.ptp(P[:, 1])
        P = np.stack([P[:, 0] * sx, P[:, 1] * sy - dy], 1)
        P = _resample(P)
        P = _flat_base(P, 1.8 if name == 'drop' else 0.6)
    P = _resample(P, 360)
    ang = np.arctan2(P[:, 1], P[:, 0])
    if np.any(np.diff(np.unwrap(ang)) <= 0):
        P = P[::-1]
    r = np.hypot(P[:, 0], P[:, 1])
    if r.min() < R_REC4 + 1.6:
        print('WARNING: %s outline too tight around the glass (rmin %.1f)' % (name, r.min()))
    return P


def build_body_v4(name, O):
    """Loft like v1's build_body: recess for the glass, soft lip, quarter-ellipse rim front and back."""
    r_o = np.hypot(O[:, 0], O[:, 1])
    d = O / r_o[:, None]
    r_lip = R_REC4 + FIL4
    L = d * r_lip

    def ring(xy, z):
        return np.column_stack([xy, np.full(len(xy), z)]) * MM

    z_floor = H4 - 2.6
    rings = []
    for f in (0.5, 1.0):
        rings.append(ring(d * R_REC4 * f, z_floor))
    for t in np.linspace(math.pi, math.pi / 2, 7):
        rings.append(ring(d * (r_lip + FIL4 * math.cos(t)), H4 - FIL4 + FIL4 * math.sin(t)))
    phis = np.linspace(math.pi / 2, 0, 30)[1:]
    for ph in phis:
        k = (1 - math.cos(ph))
        rings.append(ring(O + (L - O) * k, H4 * math.sin(ph) ** 0.9))
    for ph in phis[::-1][1:]:
        k = (1 - math.cos(ph))
        rings.append(ring(O + (L - O) * k, -H4 * math.sin(ph) ** 0.9))
    for f in (1.0, 0.66, 0.33):
        rings.append(ring(d * r_lip * f, -H4 - 0.8 * (1 - f * f)))
    return mesh_from_rings(name + '_body', rings, cap_start=np.array([0, 0, z_floor]) * MM,
                           cap_end=np.array([0, 0, -H4 - 0.8]) * MM)


def mat_pearl(name, tint):
    """Glossy injection-moulded PC with a soft pearl sheen (cooler, lighter at grazing angles)."""
    m, nt, p, out = new_mat(name)
    c = srgb(tint)
    lw = nt.nodes.new('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.45
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    nt.links.new(lw.outputs['Facing'], mix.inputs['Factor'])
    mix.inputs['A'].default_value = c
    mix.inputs['B'].default_value = (min(1, c[0] * 0.9 + 0.1), min(1, c[1] * 0.92 + 0.1), min(1, c[2] * 0.95 + 0.12), 1)
    nt.links.new(mix.outputs['Result'], p.inputs['Base Color'])
    set_in(p, 'Roughness', 0.22)
    set_in(p, 'Metallic', 0.08)
    set_in(p, 'Specular IOR Level', 0.5)
    set_in(p, 'Coat Weight', 1.0)
    set_in(p, 'Coat Roughness', 0.035)
    set_in(p, 'Coat IOR', 1.55)
    set_in(p, 'Sheen Weight', 0.35)
    set_in(p, 'Sheen Roughness', 0.35)
    set_in(p, 'Subsurface Weight', 0.12)
    set_in(p, 'Subsurface Scale', 0.0015)
    return m


def _surface_hit(ob, origin, direction):
    from mathutils.bvhtree import BVHTree
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(ob, dg)
    return bvh.ray_cast(Vector(origin), Vector(direction))


def build_v4(tag, shape, tint='pearl', eyes='cream_look', strength=2.6):
    """One SOUL v4 body. Local frame like v1: x right, y up, z towards the viewer; bottom = flat base."""
    par = new_par('v4_' + tag)
    obs = []
    O = outline_v4(shape)
    body = build_body_v4(tag, O)
    assign(body, mat_pearl('pearl_' + tag, TINTS.get(tint, tint)))
    obs.append(body)
    pol = mat_polish('ring_' + tag, (0.86, 0.86, 0.87), 0.04)
    rg = revolve_closed(tag + '_ring', [(R_GL + 0.02, H4 - 1.6), (R_RING, H4 - 1.6), (R_RING, H4 + 0.12),
                                        (R_RING - 0.12, H4 + 0.22), (R_GL + 0.02, H4 + 0.22)], seg=256)
    assign(rg, pol)
    obs.append(rg)
    g = glass_eye(tag, R_GL, H4 + 0.25, H4 + 2.0, H4 - 2.4, eyes, strength=strength)
    obs.append(g)
    # speaker: fine slot on the right side edge (3 o'clock), charging: 2 gold pogo pins on the flat base
    i_r = int(np.argmax(O[:, 0]))
    pr = O[i_r]
    dark = mat_diffuse('slot_' + tag, (0.02, 0.02, 0.022, 1), 0.6, 0.2)
    for k in range(7):          # a fine micro-perforation, 7 holes Ø0.6 at 1.3 mm pitch
        hole = revolve(tag + '_spk', [(0, -0.6), (0.3, -0.6), (0.3, 0.6), (0, 0.6)], seg=16, axis='y')
        hole.rotation_euler = (0, 0, math.radians(90))
        hole.location = ((pr[0] - 0.45) * MM, (pr[1] + (k - 3) * 1.3) * MM, 0)
        assign(hole, dark)
        obs.append(hole)
    ymin = O[:, 1].min()
    gold = mat_polish('gold_' + tag, METAL['gold']['col'], 0.12)
    for sx in (-1, 1):
        ct = revolve(tag + '_pogo', [(0, -0.3), (1.1, -0.3), (1.25, 0.0), (1.25, 1.2), (0, 1.2)], seg=32, axis='y')
        ct.location = (sx * 4.0 * MM, (ymin + 0.02) * MM, 0)
        assign(ct, gold)
        obs.append(ct)
    parent_all(par, obs)
    par['ymin'] = float(ymin)
    par['ymax'] = float(O[:, 1].max())
    par['xmin'] = float(O[:, 0].min())
    par['xmax'] = float(O[:, 0].max())
    return par


def stand_v4(par, x, y, rz=0.0, tilt=0.0):
    """Upright on its flat base: local y -> world z."""
    par.location = (x, y, -par['ymin'] * MM + 0.0001)
    par.rotation_euler = (math.radians(90 - tilt), 0, math.radians(rz))


def v1_studio(sweep_col='#E4DBCF'):
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep(sweep_col)


def v4_highlight(par, cam, side=8.5, strength=6.0):
    return screen_highlight(par, cam, up_deg=11.0, side_deg=side, size=(0.022, 0.3), tilt_deg=-30.0 if side > 0 else 30.0,
                            strength=strength, z_mm=H4 + 2.0)


# ------------------------------------------------------------------------------------------
# shots
def _hero(shape, tint, eyes='cream_look', rz=-16, cam_off=(0.17, -0.40, 0.07), lens=105):
    sc = reset()
    v1_studio()
    a = build_v4(shape, shape, tint, eyes)
    stand_v4(a, 0, 0, rz)
    mid = 0.5 * (a['ymin'] + a['ymax'])
    tgt = world_point(a, (0, mid, 0))
    focus = world_point(a, (-4, 2, H4 + 1))
    cam = camera(tgt + Vector(cam_off), tgt, lens=lens, fstop=11.0, focus=focus)
    protect_screens(cam, tgt, 1.6, -0.05)
    v4_highlight(a, cam)
    studio3(tgt, bg=8.0)
    POST['exposure'] = -0.35
    return sc


def shot_pebble():
    return _hero('pebble', 'pearl')


def shot_cloud():
    return _hero('cloud', 'sage', cam_off=(0.18, -0.44, 0.075))


def shot_drop():
    return _hero('drop', 'peach', cam_off=(0.19, -0.47, 0.08))


def shot_amulet():
    return _hero('amulet', 'sand')


FAMILY = [('cloud', 'sage', 'mint'), ('pebble', 'pearl', 'cream_look'), ('drop', 'peach', 'peach'),
          ('amulet', 'lilac', 'lilac')]


def shot_family():
    sc = reset()
    v1_studio()
    gap = 0.012
    objs = []
    for shape, tint, eyes in FAMILY:
        a = build_v4('f_' + shape, shape, tint, eyes if eyes != 'mint' else 'cream_lu')
        objs.append(a)
    total = sum((a['xmax'] - a['xmin']) * MM for a in objs) + gap * (len(objs) - 1)
    x = -total / 2
    dys = [0.01, -0.004, 0.006, -0.006]
    for a, dy in zip(objs, dys):
        stand_v4(a, x - a['xmin'] * MM, dy, rz=0)
        x += (a['xmax'] - a['xmin']) * MM + gap
    tgt = Vector((0, 0.002, 0.036))
    cam = camera((0.0, -0.66, 0.11), tgt, lens=72, fstop=11.0, focus=Vector((0, -0.004, 0.035)))
    protect_screens(cam, tgt, 1.8, -0.06)
    studio(tgt, 1.6)
    POST['exposure'] = -0.35
    return sc


def shot_hand():
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#CDBFAE', wall_y=0.55)
    build_hand_v4('hand', (0.0, 0.0, 0.030), 18.0)
    a = build_v4('hand', 'pebble', 'pearl', 'cream_look')
    # lying in the palm, top towards the fingers, tilted up towards the camera
    a.location = (0.003, 0.010, 0.030 + 0.0125)
    a.rotation_euler = (math.radians(18), math.radians(-6), math.radians(14))
    tgt = world_point(a, (0, 0, 0))
    cam = camera(tgt + Vector((0.13, -0.30, 0.15)), tgt + Vector((-0.004, 0.022, 0.0)), lens=70, fstop=5.6,
                 focus=world_point(a, (0, -6, H4)))
    flag(cam, tgt)
    v4_highlight(a, cam)
    studio3(tgt, 1.1, bg=7.0)
    POST['exposure'] = -0.35
    return sc


def build_hand_v4(name, loc, yaw_deg=0.0):
    path = os.path.join(TEX, 'hand.npz')
    if not os.path.exists(path):
        import subprocess
        subprocess.run(['python3', os.path.join(_HERE, 'hand_sdf.py'), path], check=True)
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
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    sm = ob.modifiers.new('smooth', 'SMOOTH')
    sm.factor = 0.5
    sm.iterations = 6
    ob.location = loc
    ob.rotation_euler = (0, 0, math.radians(yaw_deg))
    m, nt, p, out = new_mat('skin')
    set_in(p, 'Base Color', srgb('#D2B39C'))
    set_in(p, 'Roughness', 0.55)
    set_in(p, 'Subsurface Weight', 0.3)
    set_in(p, 'Subsurface Radius', (1.0, 0.5, 0.3))
    set_in(p, 'Subsurface Scale', 0.003)
    set_in(p, 'Specular IOR Level', 0.35)
    _noise_bump(nt, p, 900.0, 0.05, 0.0002)
    assign(ob, m)
    return ob


def build_card4(name):
    c = rounded_box(name, 85.6 * MM, 54.0 * MM, 0.76 * MM, 0.35 * MM, 3)
    m, nt, p, out = new_mat('card')
    set_in(p, 'Base Color', srgb('#3A5673'))
    set_in(p, 'Roughness', 0.55)
    assign(c, m)
    chip = rounded_box(name + '_chip', 11 * MM, 9 * MM, 0.2 * MM, 1.0 * MM, 2)
    chip.parent = c
    chip.location = (-26 * MM, 4 * MM, 0.45 * MM)
    assign(chip, mat_polish('chip_gold', METAL['gold']['col'], 0.25))
    return c


def shot_scale():
    """Top-down-ish: the family lying face-up, v1 coin (Ø52) and a payment card for scale; labels in post."""
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#E6DDD1', wall_y=0.9)
    items = []
    v1 = build_amulet('v1', 'coin', '#F3F5F7', 'cream_look', eye_strength=2.6, glow_w=0.02, ring_tilt=-90.0)
    items.append((v1, 26.0, 26.0, -26.0, 26.0, 'SOUL v1 Ø52'))
    labels = {'pebble': 'PEBBLE 64 × 72', 'cloud': 'CLOUD 84 × 66', 'drop': 'DROP 64 × 80',
              'amulet': 'AMULET Ø64'}
    for shape, tint, eyes in [('pebble', 'pearl', 'cream_look'), ('cloud', 'sage', 'cream_lu'),
                              ('drop', 'peach', 'peach'), ('amulet', 'lilac', 'lilac')]:
        a = build_v4('s_' + shape, shape, tint, eyes)
        items.append((a, -a['xmin'], a['xmax'], a['ymin'], a['ymax'], labels[shape]))
    gap = 0.012
    fam = items[1:]
    total = sum((i[1] + i[2]) * MM for i in fam) + gap * (len(fam) - 1)
    x = -total / 2
    rows = []
    for it in fam:
        rows.append((it, x + it[1] * MM, 0.035))
        x += (it[1] + it[2]) * MM + gap
    rows.append((items[0], -0.050, -0.055))
    for (ob, wl, wr, ylo, yhi, lab), cx, cy in rows:
        if ob.name.startswith('amulet_'):
            ob.location = (cx, cy, (H_HALF + 0.35) * MM)
        else:
            ob.location = (cx, cy - (ylo + yhi) / 2 * MM, H4 * MM + 0.8 * MM)
        ob.rotation_euler = (0, 0, 0)
        ly = cy - (47.0 if cy > 0 else 33.0) * MM
        ANNOT.append(dict(a=Vector((cx, ly, 0)), b=Vector((cx, ly, 0)), label=lab))
    card = build_card4('card')
    card.location = (0.055, -0.055, 0.38 * MM)
    card.rotation_euler = (0, 0, 0)
    ANNOT.append(dict(a=Vector((0.055, -0.055 - 34 * MM, 0)), b=Vector((0.055, -0.055 - 34 * MM, 0)),
                      label='card 85.6 \u00d7 54'))
    tgt = Vector((0.0, -0.012, 0.006))
    cam = camera((0.0, -0.20, 0.60), tgt, lens=58, fstop=11.0, focus=Vector((0.0, 0, 0.010)))
    flag(cam, tgt, dist=0.1, size=(4.0, 3.0))
    studio3(tgt, 1.2)
    for ob in bpy.data.objects:
        if ob.type == 'LIGHT' and ob.name in ('key', 'top', 'fill'):
            ob.visible_glossy = False
    POST['exposure'] = -0.3
    return sc


def shot_capsule():
    """The PEBBLE standing in a sculpted glossy charging cradle (contacts at the bottom), warm studio."""
    sc = reset()
    v1_studio('#E1D6C9')
    a = build_v4('cap', 'pebble', 'pearl', 'cream_look')
    stand_v4(a, 0, 0, rz=-16)
    ymin = a['ymin']
    # cradle: an oval glossy dish that hugs the lower third, slot for the body
    cer = mat_pearl('cradle', '#F4F2EE')
    prof = [(0, 0.0), (30.0, 0.0), (33.0, 1.0)]
    for h in np.linspace(1.5, 17.0, 20):
        prof.append((34.0 - 6.0 * ((h - 1.5) / 15.5) ** 2.2, h))
    prof += [(26.5, 18.2), (0, 18.2)]
    cr = revolve('cradle', prof, seg=192, axis='y')
    cr.rotation_euler = (math.radians(90), 0, math.radians(-16))
    cr.scale = (1.0, 1.0, 0.62)
    assign(cr, cer)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.011))
    cut = bpy.context.active_object
    cut.scale = (0.070, 0.0195, 0.03)
    cut.rotation_euler = (0, 0, math.radians(-16))
    cut.hide_render = True
    bo = cr.modifiers.new('slot', 'BOOLEAN')
    bo.object = cut
    bo.operation = 'DIFFERENCE'
    a.location.z += 0.005
    mid = 0.5 * (a['ymin'] + a['ymax'])
    tgt = world_point(a, (0, mid - 6, 0))
    cam = camera(tgt + Vector((0.18, -0.42, 0.09)), tgt, lens=100, fstop=11.0, focus=world_point(a, (-4, 2, H4 + 1)))
    protect_screens(cam, tgt, 1.6, -0.012)
    v4_highlight(a, cam)
    studio3(tgt, bg=8.0)
    POST['exposure'] = -0.35
    return sc


SHOTS = {
    'family': (shot_family, 1600, 1200, 128),
    'pebble': (shot_pebble, 1600, 1200, 128),
    'cloud': (shot_cloud, 1600, 1200, 128),
    'drop': (shot_drop, 1600, 1200, 128),
    'amulet': (shot_amulet, 1600, 1200, 128),
    'hand': (shot_hand, 1600, 1200, 112),
    'scale': (shot_scale, 1600, 1200, 96),
    'capsule': (shot_capsule, 1600, 1200, 128),
}

main()
