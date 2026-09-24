"""concept_e.py -- SOUL concept E: the clean lens-pebble (no loop), plus its accessories.

Ø64 mm, 18 mm at the centre, ~9 mm at the edge. Front: slightly domed black glass Ø56 (border ink = true
black, so the whole glass reads as screen); a thin bead-blasted aluminium ring with ONE polished chamfer;
the body flows in one soft curve into a domed high-gloss PC back (white, graphite, sage, sand, lilac).
Accessories: silicone sleeve with a loop tab, tan leather sleeve with a short lanyard, magnetic desk stand.

Reuses concepts.py (which reuses soul_scene.py): same materials, lights, EXR + post.py pipeline.
    blender -b --factory-startup --python concept_e.py -- --shot E_hero [--preview] [--samples N] [--tmp DIR]
Shots: E_hero E_hand E_back E_colours E_case E_dock E_scale
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(_HERE, 'concepts.py')).read()
exec(compile(_src[:_src.rindex('\nmain()')], os.path.join(_HERE, 'concepts.py'), 'exec'), globals())

E = dict(R=32.0, R_GLASS=28.0, Z_TOP=5.4, Z_GLASS=3.95, Z_BACK=-12.6, ZC=-1.5, N=2.2, RING_OUT=31.3)
COLOURS = {  # name: (PC back colour, ring colour, ring roughness)
    'white': ('#F1F0EC', (0.86, 0.86, 0.87), 0.34),
    'graphite': ('#2F3134', (0.30, 0.31, 0.33), 0.38),
    'sage': ('#9DAE98', (0.80, 0.82, 0.80), 0.34),
    'sand': ('#D7C6AA', (0.86, 0.82, 0.76), 0.34),
    'lilac': ('#C4BADB', (0.84, 0.82, 0.88), 0.34),
}


def back_z(r):
    """Domed back (superellipse), z of the back surface at radius r (mm)."""
    x = min(abs(r) / E['R'], 1.0)
    return E['ZC'] - (E['Z_BACK'] * -1 + E['ZC']) * (1 - x ** E['N']) ** (1 / E['N'])


def e_body_profile():
    prof = [(0, E['Z_BACK'])]
    for t in np.linspace(0, 1, 60)[1:]:
        r = E['R'] * math.sin(t * math.pi / 2) ** 0.8
        prof.append((r, back_z(r)))
    prof[-1] = (E['R'], E['ZC'])
    # soft shoulder up into the ring seam
    for a in np.linspace(0, 1, 10)[1:]:
        prof.append((E['R'] - 0.7 * a ** 1.6, E['ZC'] + 2.35 * math.sin(a * math.pi / 2)))
    prof += [(E['RING_OUT'] - 0.05, 0.85), (0, 0.85)]
    return prof


def mat_pc(name, col, mark=True):
    """High-gloss injection-moulded PC (AirTag-like), with a faint printed SOUL mark on the back."""
    m, nt, p, out = new_mat(name)
    c = srgb(col)
    set_in(p, 'Base Color', c)
    set_in(p, 'Roughness', 0.18)
    set_in(p, 'Specular IOR Level', 0.5)
    set_in(p, 'Coat Weight', 1.0)
    set_in(p, 'Coat Roughness', 0.03)
    set_in(p, 'Coat IOR', 1.55)
    set_in(p, 'Subsurface Weight', 0.08 if min(c[:3]) > 0.5 else 0.0)
    set_in(p, 'Subsurface Scale', 0.0008)
    if mark:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        mp = nt.nodes.new('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (-1 / (24 * MM), 1 / (12 * MM), 1)
        mp.inputs['Location'].default_value = (0.5, 0.5, 0)
        img = nt.nodes.new('ShaderNodeTexImage')
        img.image = bpy.data.images.load(os.path.join(TEX, 'back_mark.png'), check_existing=True)
        img.image.colorspace_settings.name = 'Non-Color'
        img.extension = 'CLIP'
        nt.links.new(tc.outputs['Object'], mp.inputs[0])
        nt.links.new(mp.outputs[0], img.inputs[0])
        # only on the back half (z < -8 mm)
        sep = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(tc.outputs['Object'], sep.inputs[0])
        lt = nt.nodes.new('ShaderNodeMath')
        lt.operation = 'LESS_THAN'
        lt.inputs[1].default_value = -8 * MM
        nt.links.new(sep.outputs[2], lt.inputs[0])
        mk = nt.nodes.new('ShaderNodeMath')
        mk.operation = 'MULTIPLY'
        nt.links.new(img.outputs['Color'], mk.inputs[0])
        nt.links.new(lt.outputs[0], mk.inputs[1])
        cm = nt.nodes.new('ShaderNodeMix')
        cm.data_type = 'RGBA'
        nt.links.new(mk.outputs[0], cm.inputs['Factor'])
        cm.inputs['A'].default_value = c
        lum = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
        k = 0.55 if lum > 0.2 else 2.6
        cm.inputs['B'].default_value = (min(1, c[0] * k), min(1, c[1] * k), min(1, c[2] * k), 1)
        nt.links.new(cm.outputs['Result'], p.inputs['Base Color'])
    return m


def build_e(tag='E', colour='white', eyes='cream_look', strength=2.6, contacts=True):
    col, ring_col, ring_rough = COLOURS[colour]
    par = new_par('E_' + tag)
    obs = []
    body = revolve(tag + '_body', e_body_profile(), seg=256)
    assign(body, mat_pc('pc_' + tag, col))
    obs.append(body)
    blast = mat_blast('alu_' + tag, ring_col, ring_rough)
    pol = mat_polish('alu_pol_' + tag, ring_col, 0.03)
    rg = E['R_GLASS']
    ro = E['RING_OUT']
    ring = [(rg + 0.05, 0.95, 0, 0), (ro - 0.05, 0.95, 0, 0), (ro + 0.05, 1.15, 0, 0), (ro + 0.05, 2.9, 0, 0),
            (ro - 0.1, 3.2, 0, 1), (ro - 0.8, 3.95, 0, 0), (rg + 0.45, 4.05, 0, 0), (rg + 0.15, 3.9, 0, 0),
            (rg + 0.05, 3.6, 0, 0)]
    r_ = lathe(tag + '_ring', ring, seg=256, closed=True)
    set_mats(r_, [blast, pol])
    obs.append(r_)
    g = glass_eye(tag, rg, E['Z_GLASS'], E['Z_TOP'], 1.0, eyes, strength=strength)
    obs.append(g)
    if contacts:
        gold = mat_polish('gold_' + tag, METAL['gold']['col'], 0.1)
        for sx in (-1, 1):
            x, y = sx * 3.6, -9.0
            zc = back_z(math.hypot(x, y))
            ct = revolve(tag + '_pogo', [(0, zc - 0.06), (0.85, zc - 0.05), (1.0, zc + 0.02), (1.0, zc + 0.5),
                                         (0, zc + 0.5)], seg=40)
            ct.location = (x * MM, y * MM, 0)
            assign(ct, gold)
            obs.append(ct)
    parent_all(par, obs)
    par['R'] = E['R']
    return par


def build_sleeve(tag, mat, loop=True, loop_mat=None, stitch=False):
    """Soft sleeve that wraps the domed back and the edge up to the ring; a loop tab at 12 o'clock."""
    obs = []
    t_in, t_out = 0.05, 1.5
    outer, inner = [], []
    prof = e_body_profile()[:-2]
    for (r, z) in prof:
        outer.append((r, z))
    # offset along the 2D normal of the profile
    P = np.array(outer)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None] + 1e-9
    Nn = np.stack([T[:, 1], -T[:, 0]], 1)      # outward (profile runs back apex -> front)
    Po = P + Nn * t_out
    Pi = P + Nn * t_in
    Po[0] = (0, P[0][1] - t_out)
    Pi[0] = (0, P[0][1] - t_in)
    top_o = (Po[-1][0], Po[-1][1])
    shell = [(0, Po[0][1])] + [tuple(v) for v in Po[1:]]
    # lip: round over the top edge back to the inner surface
    zt = 1.9
    shell = [s for s in shell if s[1] < zt] + [(E['R'] + t_out - 0.1, zt), (E['R'] + 0.6, zt + 0.55),
                                               (E['RING_OUT'] + 0.1, zt + 0.5)]
    inner_ = [tuple(v) for v in Pi[1:] if v[1] < zt][::-1]
    shell += inner_ + [(0, Pi[0][1])]
    sl = revolve(tag + '_sleeve', shell, seg=192)
    assign(sl, mat)
    obs.append(sl)
    if loop:
        # a flat loop tab rising from the sleeve at 12 o'clock (in the plane of the face)
        cu = bpy.data.curves.new(tag + '_tab', 'CURVE')
        cu.dimensions = '3D'
        cu.bevel_depth = 1.0 * MM
        cu.bevel_resolution = 4
        cu.use_fill_caps = True
        sp = cu.splines.new('POLY')
        pts = []
        for a in np.linspace(math.pi, 0, 40):
            pts.append((6.0 * math.cos(a), E['R'] + 7.5 + 7.0 * math.sin(a), -4.0))
        pts = [(-6.0, E['R'] - 1.0, -4.0), (-6.0, E['R'] + 4.0, -4.0)] + pts + [(6.0, E['R'] + 4.0, -4.0),
                                                                              (6.0, E['R'] - 1.0, -4.0)]
        sp.points.add(len(pts) - 1)
        for p_, q in zip(sp.points, pts):
            p_.co = (q[0] * MM, q[1] * MM, q[2] * MM, 1)
        tab = bpy.data.objects.new(tag + '_tab', cu)
        bpy.context.scene.collection.objects.link(tab)
        tab.scale = (1, 1, 2.0)   # flattened strap (wider in depth)
        assign(tab, loop_mat or mat)
        obs.append(tab)
        # a web joining the tab to the sleeve
        web = rounded_box(tag + '_web', 16 * MM, 7 * MM, 6 * MM, 2.0 * MM, 4)
        web.location = (0, (E['R'] + 1.8) * MM, -4.0 * MM)
        assign(web, loop_mat or mat)
        obs.append(web)
    return obs


def mat_silicone(name, col):
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', srgb(col))
    set_in(p, 'Roughness', 0.62)
    set_in(p, 'Specular IOR Level', 0.35)
    set_in(p, 'Sheen Weight', 0.25)
    set_in(p, 'Subsurface Weight', 0.1)
    set_in(p, 'Subsurface Scale', 0.001)
    _noise_bump(nt, p, 3000.0, 0.05)
    return m


def e_screen_hl(par, cam, **kw):
    return screen_highlight(par, cam, z_mm=E['Z_TOP'], **kw)


def warm_studio(col='#8E8882'):
    world_color((0.1, 0.1, 0.1), 0.3)
    return sweep(col, rough=0.6, wall_y=0.55, height=2.5)


# ------------------------------------------------------------------------------------------
# shots
def shot_E_hero():
    sc = reset()
    graphite_studio('#24252A')
    e = build_e('hero', 'white')
    flat(e, (0, 0, 0.03), rz=-20, tilt=40)
    settle(e)
    tgt = world_point(e, (0, 0, 0))
    cam = hero_cam(tgt, (0.13, -0.28, 0.085), lens=100, fstop=7.1, focus=world_point(e, (0, -8, 5)))
    flag(cam, tgt, dist=0.08, size=(1.6, 1.2))
    protect_screens(cam, tgt, 1.2, 0.02)
    e_screen_hl(e, cam, up_deg=10.0, side_deg=8.5, size=(0.02, 0.3), tilt_deg=-30.0, strength=5.0)
    launch_lights(tgt, 0.7, top_glossy=False)
    area_light('top_soft', (tgt.x + 0.1, tgt.y + 0.05, tgt.z + 0.5), tgt, 0.5, 1.5, blackbody_rgb(5200), spread=60,
               glossy=False)
    POST['exposure'] = 0.0
    return sc


def shot_E_back():
    sc = reset()
    warm_studio('#9A938C')
    e = build_e('back', 'sage')
    flat(e, (0, 0, 0.03), rz=160, tilt=180 - 26)
    settle(e)
    tgt = world_point(e, (0, 0, -6))
    cam = hero_cam(tgt, (0.18, -0.38, 0.15), lens=100, fstop=5.6, focus=world_point(e, (0, 0, -12)))
    flag(cam, tgt, dist=0.08, size=(1.6, 1.2), col=(0.2, 0.2, 0.2))
    launch_lights(tgt, 0.9, warm=5000)
    POST['exposure'] = -0.1
    return sc


def shot_E_colours():
    sc = reset()
    warm_studio('#A39B93')
    names = ['white', 'graphite', 'sage', 'sand', 'lilac']
    gap = 0.076
    for i, n in enumerate(names):
        e = build_e('c_' + n, n, eyes=['cream_look', 'cream_front', 'mint', 'peach', 'lilac'][i])
        x = (i - 2) * gap
        flat(e, (x, 0.0, 0.03), rz=(i - 2) * -6, tilt=24)
        settle(e)
    tgt = Vector((0.0, 0.0, 0.012))
    cam = camera((0.0, -0.62, 0.30), tgt, lens=56, fstop=11.0, focus=Vector((0, -0.01, 0.012)))
    flag(cam, tgt, dist=0.2, size=(3.0, 2.0))
    protect_screens(cam, tgt, 1.6, 0.0)
    launch_lights(tgt, 1.0, warm=5000, top_glossy=False)
    area_light('top_soft', (tgt.x, tgt.y + 0.1, tgt.z + 0.6), tgt, 0.8, 3.0, blackbody_rgb(5200), spread=60, glossy=False)
    POST['exposure'] = -0.1
    return sc


def build_bag_strap():
    """A vertical leather bag strap coming down from out of frame, with a steel D-ring (generic)."""
    leather = mat_leather('strap', srgb('#3E2A1E'), 0.45)
    st = rounded_box('strap', 0.032, 0.004, 0.40, 0.0015, 3)
    st.location = (0, 0.012, 0.30)
    assign(st, leather)
    ring_pts = [(0.010 * math.cos(t), 0.0, 0.010 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 64, endpoint=False)]
    dr = curve_obj('dring', np.array(ring_pts), 0.0013, closed=True, res=4)
    return st, dr


def shot_E_case():
    sc = reset()
    warm_studio('#A0978E')
    sil = mat_silicone('silicone', '#C8663F')
    leather = mat_leather('tan', srgb('#A8683A'), 0.42)
    # (a) silicone sleeve, hanging by its loop from a steel ring on a leather bag strap
    st, dr = build_bag_strap()
    st.location = (-0.045, 0.02, 0.30)
    e1 = build_e('case1', 'white')
    obs = build_sleeve('s1', sil)
    for o in obs:
        o.parent = e1
    e1.rotation_euler = (math.radians(90 - 6), 0, math.radians(-10))
    e1.location = (-0.045, 0.0, 0.058)
    bpy.context.view_layer.update()
    tab_top = world_point(e1, (0, E['R'] + 14.0, -4.0))
    dr.location = tab_top + Vector((0, 0.002, 0.004))
    dr.rotation_euler = (0, math.radians(90), 0)
    assign(dr, metal_mats()['steel'])
    dr.rotation_euler = (math.radians(90), 0, math.radians(80))
    # (b) tan leather sleeve lying on the floor with a short lanyard
    e2 = build_e('case2', 'graphite', eyes='cream_front')
    obs2 = build_sleeve('s2', leather, loop=True, loop_mat=leather)
    for o in obs2:
        o.parent = e2
    flat(e2, (0.045, -0.012, 0.03), rz=-35, tilt=14)
    settle(e2)
    bpy.context.view_layer.update()
    a0 = world_point(e2, (0.0, E['R'] + 13.0, -4.0))
    dirv = (world_point(e2, (0, E['R'] + 20, -4.0)) - a0)
    dirv.z = 0
    dirv.normalize()
    side = Vector((-dirv.y, dirv.x, 0))
    pts = [a0, a0 + dirv * 0.006 + Vector((0, 0, -0.002))]
    base = Vector((a0.x, a0.y, 0.0016)) + dirv * 0.014
    for k in range(0, 25):
        t = k / 24 * 2 * math.pi
        pts.append(base + dirv * (0.028 * (1 - math.cos(t)) / 2 * 1.9) + side * (0.016 * math.sin(t)))
    pts.append(a0 + dirv * 0.006 + side * 0.004 + Vector((0, 0, -0.002)))
    for p_ in pts[2:-1]:
        p_.z = 0.0016
    cord_obj('lanyard', [tuple(v) for v in pts], 1.6, '#A8683A', 0.5)
    tgt = Vector((0.0, 0.0, 0.045))
    cam = camera((0.05, -0.42, 0.12), tgt, lens=70, fstop=7.1, focus=Vector((0, 0, 0.04)))
    protect_screens(cam, tgt, 0.8, 0.02)
    launch_lights(tgt, 1.0, warm=5000)
    POST['exposure'] = -0.1
    return sc


def build_stand(tag, tilt=15.0):
    """Magnetic desk stand: a weighted bead-blasted aluminium puck with a tilted round pad."""
    dark = mat_blast('stand_' + tag, (0.20, 0.20, 0.21), 0.4)
    pol = mat_polish('stand_pol_' + tag, (0.25, 0.25, 0.26), 0.05)
    base = lathe(tag + '_base', [(0, 0, 0, 0), (27.0, 0, 0, 0), (28.0, 0.8, 0, 0), (28.0, 6.4, 0, 0),
                                 (27.4, 7.0, 0, 1), (0, 7.0, 0, 0)], seg=192, closed=False)
    set_mats(base, [dark, pol])
    # tilted pad with a spine
    arm = rounded_box(tag + '_arm', 0.012, 0.006, 0.030, 0.0025, 4)
    arm.location = (0, 0.009, 0.020)
    arm.rotation_euler = (math.radians(-tilt), 0, 0)
    assign(arm, dark)
    return base, arm


def shot_E_dock():
    sc = reset()
    desk_scene('oak')
    laptop((0.19, 0.12, 0.006), -12)
    base, arm = build_stand('st', 15.0)
    base.location = (-0.03, 0.0, 0.0)
    arm.location = (-0.03, 0.012, 0.024)
    e = build_e('dock', 'white')
    e.rotation_euler = (math.radians(90 - 15), 0, 0)
    e.location = (-0.03, 0.0, 0.0)
    bpy.context.view_layer.update()
    # rest the back apex on the pad, bottom edge just above the base top
    apex = world_point(e, (0, -3.0, E['Z_BACK']))
    target = Vector((-0.03, 0.0125, 0.034))
    e.location = Vector(e.location) + (target - apex)
    bpy.context.view_layer.update()
    for o in (base, arm, e):
        o.rotation_euler.z += math.radians(20)
    base.location = Vector((-0.03, 0.0, 0.0))
    tgt = world_point(e, (0, 0, 0))
    cam = camera(tgt + Vector((-0.15, -0.40, 0.07)), tgt + Vector((0.015, 0.0, -0.008)), lens=85, fstop=4.0,
                 focus=world_point(e, (0, 0, 5)))
    protect_screens(cam, tgt, 0.4, 0.04)
    e_screen_hl(e, cam, up_deg=10.0, side_deg=8.5, size=(0.02, 0.3), tilt_deg=-30.0, strength=5.0)
    desk_lights(tgt)
    return sc


def build_card(name):
    """Generic payment-card-sized card (85.6 × 54 × 0.76 mm), plain, with a contact chip; no brand."""
    c = rounded_box(name, 85.6 * MM, 54.0 * MM, 0.76 * MM, 0.35 * MM, 3)
    # rounded corners (r 3.2 mm) via bevel on vertical edges is enough visually at this scale
    m, nt, p, out = new_mat('card')
    set_in(p, 'Base Color', srgb('#2E4A6B'))
    set_in(p, 'Roughness', 0.55)
    assign(c, m)
    chip = rounded_box(name + '_chip', 11 * MM, 9 * MM, 0.2 * MM, 1.0 * MM, 2)
    chip.parent = c
    chip.location = (-26 * MM, 4 * MM, 0.45 * MM)
    assign(chip, mat_polish('chip_gold', METAL['gold']['col'], 0.25))
    return c


def shot_E_scale():
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#E2D9CD', wall_y=0.8)
    v1 = build_amulet('v1', 'coin', '#F3F5F7', 'cream_look', eye_strength=2.6, glow_w=0.02, ring_tilt=-90.0)
    v1.location = (-0.082, 0.004, (H_HALF + 0.35) * MM)
    v1.rotation_euler = (0, 0, math.radians(0))
    e = build_e('scale', 'white')
    flat(e, (0.0, 0.004, 0.03), rz=0, tilt=0)
    settle(e)
    card = build_card('card')
    card.location = (0.092, 0.004, 0.38 * MM)
    card.rotation_euler = (0, 0, math.radians(90))
    tgt = Vector((0.004, -0.004, 0.006))
    cam = camera((0.0, -0.16, 0.50), tgt, lens=70, fstop=11.0, focus=Vector((0.0, 0, 0.010)), shift=(0, -0.01))
    flag(cam, tgt)
    y0 = -0.052
    for x, half, lab in ((-0.082, 26.0, 'SOUL v1 Ø52'), (0.0, E['R'], 'SOUL Ø64'),
                         (0.092, 27.0, 'card 85.6 × 54')):
        ANNOT.append(dict(a=Vector((x - half * MM, y0, 0)), b=Vector((x + half * MM, y0, 0)), label=lab))
    launch_lights(tgt, 0.0, top=False)
    studio3(tgt, 1.1)
    POST['exposure'] = -0.25
    return sc


def build_hand_v2(name, loc, yaw_deg=0.0):
    """Stylised right hand, palm up (mesh from hand_sdf.py -> tex/hand.npz, mm), as in v2."""
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
    sm.iterations = 4
    ob.location = loc
    ob.rotation_euler = (0, 0, math.radians(yaw_deg))
    m, nt, p, out = new_mat('skin')
    set_in(p, 'Base Color', srgb('#D8CABD'))
    set_in(p, 'Roughness', 0.62)
    set_in(p, 'Subsurface Weight', 0.25)
    set_in(p, 'Subsurface Radius', (1.0, 0.45, 0.25))
    set_in(p, 'Subsurface Scale', 0.004)
    set_in(p, 'Specular IOR Level', 0.35)
    _noise_bump(nt, p, 900.0, 0.06, 0.0002)
    assign(ob, m)
    return ob


def shot_E_hand():
    sc = reset()
    warm_studio('#8C857E')
    build_hand_v2('hand', (0.0, 0.0, 0.030), 18.0)
    e = build_e('hand', 'white')
    e.location = (0.004, 0.012, 0.030 + 0.0140)
    e.rotation_euler = (math.radians(16), math.radians(-6), math.radians(12))
    tgt = world_point(e, (0, 0, 0))
    cam = camera(tgt + Vector((0.12, -0.27, 0.13)), tgt + Vector((-0.004, 0.018, 0.002)), lens=70, fstop=5.6,
                 focus=world_point(e, (0, -6, 5)))
    flag(cam, tgt)
    e_screen_hl(e, cam, up_deg=10.0, side_deg=8.5, size=(0.02, 0.3), tilt_deg=-30.0, strength=5.0)
    studio3(tgt, 1.2)
    POST['exposure'] = -0.3
    return sc


SHOTS = {
    'E_hero': (shot_E_hero, 1600, 1200, 128),
    'E_hand': (shot_E_hand, 1600, 1200, 112),
    'E_back': (shot_E_back, 1600, 1200, 112),
    'E_colours': (shot_E_colours, 1600, 1200, 112),
    'E_case': (shot_E_case, 1600, 1200, 112),
    'E_dock': (shot_E_dock, 1600, 1200, 112),
    'E_scale': (shot_E_scale, 1600, 1200, 96),
}

main()
