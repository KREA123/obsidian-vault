"""alt_v5.py -- the two ALTERNATES of render brief v5: §4 PIATRA (+ OU nest and frosted dome) and §5 MĂRGĂRITAR
(+ SCRIN casket), plus the FINAL / ALT A / ALT B decision board. Every image is a CGI concept.

Loads soul_v5.py (which loads concepts.py -> soul_scene.py) and reuses its materials, studio, glass, glint and
render pipeline; the alternates' bodies come from alt_geo.py (pure numpy, same section method as soul_geo.py).

    blender -b --factory-startup --python alt_v5.py -- --shot altA_piatra [--preview] [--samples N] [--tmp DIR]
Shots: altA_piatra (hero)  altA_nest (in the OU nest, dome beside)  altB_margaritar (hero, on limestone)
       altB_scrin (in the SCRIN socket, crystal lid inverted beside as a bowl)  choices (FINAL | A | B dead-front)
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_src5 = open(os.path.join(_HERE, 'soul_v5.py')).read()
exec(compile(_src5[:_src5.rindex('\nmain()')], os.path.join(_HERE, 'soul_v5.py'), 'exec'), globals())
import alt_geo as AG  # noqa: E402

ALT_NU = 320


# ==========================================================================================
# glass lookups that also know the alternates (soul_v5's versions assume the FINAL glass centre)
def glass_world(par):
    bpy.context.view_layer.update()
    info = SOULS[par.name]
    G = info.get('G', G_MM)
    N = info.get('N', N_FACE)
    c = par.matrix_world @ V(G)
    n = (par.matrix_world.to_3x3() @ Vector(N)).normalized()
    return c, n


def eye_point(par):
    bpy.context.view_layer.update()
    G = SOULS[par.name].get('G', G_MM)
    return par.matrix_world @ V(np.asarray(G) + np.array([0, 0.3, -2.3]))


# ==========================================================================================
# helpers
def lathe_mi(name, prof, seg=256, plan=None):
    """Closed lathe from a profile [(d, z, mi)]: ring = plan(d) (default circle of radius d) at height z; the face
    between point i and i+1 gets material index mi of point i. d == 0 at an end -> fan cap to the axis."""
    t = np.linspace(0, 2 * math.pi, seg, endpoint=False)
    pts = list(prof)
    cs = pts.pop(0) if pts[0][0] == 0 else None
    ce = pts.pop(-1) if pts[-1][0] == 0 else None
    if plan is None:
        def plan(d):
            return np.stack([d * np.cos(t), d * np.sin(t)], 1)
    rings = [np.column_stack([plan(d), np.full(seg, z)]) for d, z, mi in pts]
    Rn = len(rings)
    verts = np.vstack(rings)
    quads = grid_quads(Rn, seg)
    mq = np.repeat([p[2] for p in pts[:-1]], seg)
    tris, mt = [], []
    extra = []
    if cs is not None:
        extra.append([0, 0, cs[1]])
        tris.append(fan(len(verts), 0, seg, top=False))
        mt.append(np.full(seg, cs[2]))
    if ce is not None:
        extra.append([0, 0, ce[1]])
        tris.append(fan(len(verts) + len(extra) - 1, (Rn - 1) * seg, seg, top=True))
        mt.append(np.full(seg, pts[-1][2]))
    if extra:
        verts = np.vstack([verts, extra])
    ob = build_mesh(name, verts, quads, np.vstack(tris) if tris else None, mq,
                    np.concatenate(mt) if mt else None)
    return ob


def alt_slot_cutter(B, name, side, z0, z1, width=0.9, depth=2.0, out=1.0):
    """Speaker slot swept along the alternate's seam (rounded ends)."""
    zz = np.linspace(z0 - 0.5, z1 + 0.5, 400)
    w, yf, yb, ys, c, pf = B.sections(zz)
    P = np.stack([side * w, ys, zz], 1)
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    sc = 0.5 * s[-1]
    half = 0.5 * (s[np.argmin(np.abs(zz - z1))] - s[np.argmin(np.abs(zz - z0))])
    k = np.abs(s - sc) <= half
    P, s, zz, w = P[k], s[k], zz[k], w[k]
    dw = np.gradient(w, zz)
    nrm = np.stack([np.full_like(zz, side), np.zeros_like(zz), -dw], 1)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    hw = width / 2
    d = np.abs(s - sc)
    endr = np.clip(d - (half - hw), 0, None)
    hwid = np.sqrt(np.clip(hw * hw - endr * endr, 0.0004, None))
    yv = np.array([0.0, 1.0, 0.0])
    ring = []
    for i in range(len(P)):
        a = P[i] + nrm[i] * out
        b = P[i] - nrm[i] * depth
        ring.append([a - yv * hwid[i], a + yv * hwid[i], b + yv * hwid[i], b - yv * hwid[i]])
    ring = np.array(ring)
    Rn = len(ring)
    quads = grid_quads(Rn, 4)
    caps = np.array([[0, 1, 2, 3], [(Rn - 1) * 4 + 3, (Rn - 1) * 4 + 2, (Rn - 1) * 4 + 1, (Rn - 1) * 4 + 0]])
    ob = build_mesh(name, ring.reshape(-1, 3), np.vstack([quads, caps]), smooth=False)
    orient_outward(ob, P[len(P) // 2] - nrm[len(P) // 2] * depth / 2)
    return ob


def alt_pin_cutter(B, name, side, z, r=0.35, depth=2.0, out=1.0):
    w, yf, yb, ys, c, pf = B.sections(np.array([z - 0.05, z, z + 0.05]))
    P = np.array([side * w[1], ys[1], z])
    n = np.array([side, 0.0, -side * (w[2] - w[0]) / 0.1])
    n /= np.linalg.norm(n)
    ob = revolve(name, [(0, -depth), (r, -depth), (r, out), (0, out)], seg=24)
    ob.matrix_world = Matrix.Translation(V(P)) @ basis(n, (0, 1, 0))
    bpy.context.view_layer.update()
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)
    return ob


ALT_SPEC = {
    'piatra': dict(cls=AG.Piatra, slot=(44.0, 56.0), mics=(48.0, 20.0), seam_r=0.10),
    'margaritar': dict(cls=AG.Margaritar, slot=(42.0, 54.0), mics=(46.0, 20.0), seam_r=0.15),   # 0.3 V girdle
}
_ALTB = {}


def alt_geo(kind):
    if kind not in _ALTB:
        _ALTB[kind] = ALT_SPEC[kind]['cls']()
    return _ALTB[kind]


def alt_body_mesh(kind, name):
    """Closed alternate body with the glass seat, the speaker slot (+x seam) and the 2 mic pinholes (-x seam) cut.
    Cached in CACHE (rebuilt automatically when missing). Slots: shell, gap."""
    B = alt_geo(kind)
    sp = ALT_SPEC[kind]
    path = os.path.join(CACHE, 'alt_%s_v5_%d.npz' % (kind, ALT_NU))
    if os.path.exists(path):
        ob, roles = load_mesh_cache(path, name)
        set_auto_smooth(ob)
        return ob, roles
    t0 = time.time()
    rows, bc, pole = B.rows(NU=ALT_NU)
    Rn, N = rows.shape[:2]
    verts = np.vstack([rows.reshape(-1, 3), [bc], [pole]])
    quads = grid_quads(Rn, N)
    tris = np.vstack([fan(Rn * N, 0, N, top=False), fan(Rn * N + 1, (Rn - 1) * N, N, top=True)])
    ob = build_mesh(name, verts, quads, tris)
    orient_outward(ob, (0, 2, 35))
    ob.data.materials.append(bpy.data.materials.new('ROLE_shell'))
    cut_mat = bpy.data.materials.new('ROLE_gap')
    G = B.G()
    rs = B.r_glass + 0.15
    seat = revolve('cut_seat', [(0, -0.8), (rs, -0.8), (rs, 1.8), (0, 1.8)], seg=384)
    for p in seat.data.polygons:
        p.use_smooth = False
    seat.data.transform(Matrix.Translation(V(G)) @ basis(SG.NRM, SG.UPV))
    cutters = [seat, alt_slot_cutter(B, 'cut_slot', +1, *sp['slot']),
               alt_pin_cutter(B, 'cut_mic_a', -1, sp['mics'][0]), alt_pin_cutter(B, 'cut_mic_b', -1, sp['mics'][1])]
    for c in cutters:
        assign(c, cut_mat)
    boolean(ob, cutters)
    roles = [m.name.replace('ROLE_', '').split('.')[0] for m in ob.data.materials]
    save_mesh_cache(path, ob, roles)
    print('  alt %s mesh built + booleans %.1fs, %d faces, roles %s' % (kind, time.time() - t0,
                                                                       len(ob.data.polygons), roles))
    set_auto_smooth(ob)
    return ob, roles


def superellipse(a, b, p, n=160, cx=0.0, cy=0.0):
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    return np.stack([cx + a * np.sign(c) * np.abs(c) ** (2 / p), cy + b * np.sign(s) * np.abs(s) ** (2 / p)], 1)


def build_alt(tag, kind, eyes='soul_front', strength=2.6):
    """PIATRA or MĂRGĂRITAR in Perlă. Returns the parent empty (origin = land centre on the table)."""
    B = alt_geo(kind)
    sp = ALT_SPEC[kind]
    par = new_par('alt_' + tag)
    body_m = mat_pearl5('pearl')
    gd = gap_dark()
    ob, roles = alt_body_mesh(kind, 'body_' + tag)
    for i, r in enumerate(roles):
        ob.data.materials[i] = {'shell': body_m, 'gap': gd}[r]
    obs = [ob]
    G = B.G()
    N = SG.NRM.copy()
    rg = B.r_glass
    # flat 2.5D glass, top 0.07 below the table (no ring: only the 0.15 shadow gap)
    g = glass_eye(tag, rg, 0.0, 0.08, -0.7, 'soul_front', strength=strength, r_screen=21.88)
    assign(g, mat_glass5('glass_' + tag, eyes, strength))
    M_gl = Matrix.Translation(V(G - 0.15 * N)) @ basis(N, SG.UPV)
    g.matrix_basis = M_gl
    obs.append(g)
    gr = revolve_closed(tag + '_gapring', [(rg - 0.02, -0.40), (rg + 0.17, -0.40), (rg + 0.17, -0.25),
                                           (rg - 0.02, -0.25)], seg=256)
    gr.matrix_basis = Matrix.Translation(V(G)) @ basis(N, SG.UPV)
    assign(gr, gd)
    obs.append(gr)
    # the seam (PIATRA) / 0.3 V girdle (MĂRGĂRITAR) on the silhouette, over the crown
    Pm, nm = B.seam(-1)
    Pp, npp = B.seam(+1)
    rr = sp['seam_r']
    pts = np.vstack([Pm - nm * (rr * 0.6), (Pp - npp * (rr * 0.6))[::-1][1:]])
    sm = curve_obj(tag + '_seam', [tuple(p * MM) for p in pts], rr * MM, res=3)
    assign(sm, gd)
    obs.append(sm)
    rows_bc = B.sections(np.array([B.z_bot]))
    bcy = 0.5 * float(rows_bc[1][0] + rows_bc[2][0])
    if kind == 'piatra':
        # Ø25 x 1.2 dark-champagne zinc foot under the hull (the hull ends 1.2 above the table: hover shadow line)
        fx, fy = B.foot_c
        foot = revolve(tag + '_foot', [(0, 0.0), (12.2, 0.0), (12.5, 0.3), (12.5, 1.25), (12.0, 1.45), (0, 1.45)],
                       seg=128)
        foot.location = V((fx, fy, 0))
        zinc = mat_simple('zinc_champ', '#B9A688', 0.35, metal=1.0)
        assign(foot, zinc)
        obs.append(foot)
        gold = mat_simple('gold', '#E3C07A', 0.18, metal=1.0)
        loops = []
        for rad in (4.0, 6.5, 9.0, 11.0):
            o = extrude_loops(tag + '_ring%.0f' % rad, [circle(rad + 0.55, 128), circle(rad - 0.55, 128)], -0.02, 0.02)
            o.location = V((fx, fy, 0))
            assign(o, gold)
            obs.append(o)
        dot = extrude_loops(tag + '_dot', [circle(1.25, 48)], -0.02, 0.02)
        dot.location = V((fx, fy, 0))
        assign(dot, gold)
        obs.append(dot)
    else:
        # the 28 x 17 champagne-gold zamak sole plate, 0.5 reveal (dark neck) up to the pearl hull at z 1.5
        pl = superellipse(14.0, 8.5, 2.6, 160, 0.0, bcy)
        plate = extrude_loops(tag + '_plate', [pl], 0.0, B.plate_t)
        assign(plate, mat_simple('zamak_gold', '#E3C89A', 0.18, metal=1.0))
        obs.append(plate)
        neck = extrude_loops(tag + '_reveal', [superellipse(13.4, 7.9, 2.6, 160, 0.0, bcy)], B.plate_t - 0.01,
                             B.z_bot + 0.2)
        assign(neck, gd)
        obs.append(neck)
    parent_all(par, obs)
    SOULS[par.name] = dict(glass=g, M_gl=M_gl.copy(), body=ob, G=G.copy(), N=N)
    return par


def pose_alt(par, loc_mm=(0, 0, 0), yaw=0.0, M_extra=None):
    M = Matrix.Translation(V(loc_mm)) @ Matrix.Rotation(R(yaw), 4, 'Z')
    if M_extra is not None:
        M = M_extra @ M
    par.matrix_world = M
    bpy.context.view_layer.update()
    if M_extra is None:
        settle(par, 0.00002)
    level_eyes(par)


# ==========================================================================================
# materials of the docks
def mat_dome_frost(name, outer=True):
    """dome_frost: clear outside (IOR 1.47, r 0), frosted inside (r 0.45); a faint milky volume in the 2.5 mm wall so
    Blender 4.0 (no multiple-scatter frost) reads it as frosted PC rather than smoke glass."""
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', srgb('#F7F2EA'))
    set_in(p, 'Transmission Weight', TUNE.get('dome_tr', 0.45))
    set_in(p, 'IOR', 1.47)
    set_in(p, 'Roughness', 0.0 if outer else 0.45)
    vs = nt.nodes.new('ShaderNodeVolumeScatter')
    vs.inputs['Color'].default_value = (0.99, 0.98, 0.965, 1)
    vs.inputs['Density'].default_value = TUNE.get('dome_dens', 320.0)
    va = nt.nodes.new('ShaderNodeVolumeAbsorption')
    va.inputs['Color'].default_value = (1.0, 0.94, 0.86, 1)
    va.inputs['Density'].default_value = 5.0
    add = nt.nodes.new('ShaderNodeAddShader')
    nt.links.new(vs.outputs[0], add.inputs[0])
    nt.links.new(va.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs['Volume'])
    return m


def mat_surlyn(name, outer=True):
    """surlyn crystal lid: IOR 1.51, outer r 0.02 (gloss), inner r 0.45 (frosted)."""
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', srgb('#FBF8F3'))
    set_in(p, 'Transmission Weight', 1.0)
    set_in(p, 'IOR', 1.51)
    set_in(p, 'Roughness', 0.02 if outer else 0.45)
    va = nt.nodes.new('ShaderNodeVolumeAbsorption')
    va.inputs['Color'].default_value = (0.97, 0.985, 1.0, 1)
    va.inputs['Density'].default_value = 8.0
    nt.links.new(va.outputs[0], out.inputs['Volume'])
    return m


def mat_lacquer_pearl(name='lacquer_pearl'):
    """lacquer_pearl approximated in one surface: the inner pearl (metallic 0.15, sheen 0.3) under a 1.0 / 0.01
    clear coat (the brief's 2.2 mm clear outer shell is not modelled separately)."""
    return mat_pearl5(name, coat_r=0.01, rough=0.22, metal=0.15, sheen=0.3)


def mat_limestone(name='limestone'):
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', srgb('#D8CFC2'))
    set_in(p, 'Roughness', 0.6)
    set_in(p, 'Specular IOR Level', 0.35)
    _noise_bump(nt, p, 260.0, 0.25, 0.0003)
    return m


# ==========================================================================================
# OU nest + dome (brief §4): Piet Hein superegg |r/36|^2.5 + |(z-45)/48|^2.5 = 1, flat Ø33.6 base at z 0, top z 93
def egg_r(z, a=36.0, b=48.0, zc=45.0, p=2.5):
    return a * np.clip(1 - np.abs((np.asarray(z, float) - zc) / b) ** p, 0, None) ** (1 / p)


NEST_RIM = 23.0
NEST_FLOOR = 12.0


def build_nest(tag, glow=None):
    """Pearl nest z 0-23, 4 mm wall, socket floor at z 12; a 2 mm frosted 2200 K light-guide ring inside the rim
    (rear half only)."""
    par = new_par('nest_' + tag)
    zs = np.linspace(0.0, NEST_RIM - 0.8, 40)
    prof = [(0, 0.0, 0), (egg_r(0.0) - 0.8, 0.0, 0)]
    prof += [(float(egg_r(z)), float(z), 0) for z in zs[1:]]
    ro, ri = float(egg_r(NEST_RIM)), float(egg_r(NEST_RIM)) - 4.0
    for a in np.linspace(0, math.pi / 2, 6)[1:]:                  # rounded rim (R0.8 outer, R0.8 inner)
        prof.append((ro - 0.8 + 0.8 * math.cos(a), NEST_RIM - 0.8 + 0.8 * math.sin(a), 0))
    for a in np.linspace(math.pi / 2, math.pi, 6):
        prof.append((ri + 0.8 + 0.8 * math.cos(a), NEST_RIM - 0.8 + 0.8 * math.sin(a), 0))
    zi = np.linspace(NEST_RIM - 1.0, NEST_FLOOR + 1.0, 20)
    prof += [(float(egg_r(z)) - 4.0, float(z), 0) for z in zi]
    rf = float(egg_r(NEST_FLOOR)) - 4.0
    prof += [(rf - 1.0, NEST_FLOOR, 1), (0, NEST_FLOOR, 1)]
    nest = lathe_mi(tag + '_nest', prof, seg=256)
    orient_outward(nest, (0, 0, 6))
    nest.data.materials.append(mat_pearl5('ou_pearl', rough=0.22))
    nest.data.materials.append(mat_simple('pom_floor', '#EDEAE4', 0.35))
    set_auto_smooth(nest, 50)
    obs = [nest]
    # light-guide ring: rear half, just inside the rim
    g = TUNE.get('nest_glow', 2.0) if glow is None else glow
    if g > 0:
        ts = np.linspace(R(20), R(160), 60)
        rr = ri + 0.9
        pts = [(rr * math.cos(t) * MM, rr * math.sin(t) * MM, (NEST_RIM - 1.6) * MM) for t in ts]
        st = curve_obj(tag + '_guide', pts, 1.0 * MM, res=2)
        assign(st, mat_led(tag + '_led_guide', g))
        st.visible_shadow = False
        obs.append(st)
    parent_all(par, obs)
    return par


def build_dome(tag, rim_down=True):
    """Frosted dome z 23-93, 2.5 mm wall (outer clear r 0, inner frosted r 0.45). rim_down: stood on its rim."""
    top = 93.0
    zo = np.concatenate([np.linspace(NEST_RIM, 80.0, 40), top - np.linspace(math.sqrt(13.0), 0.0, 30)[1:] ** 2])
    prof = [(float(egg_r(z)), float(z), 0) for z in zo[:-1]] + [(0, top, 0)]
    ai, bi = 33.5, 45.5                                   # inner superegg (wall 2.5)
    zi = np.concatenate([np.linspace(NEST_RIM, 78.0, 40), (45 + bi) - np.linspace(math.sqrt(12.5), 0.0, 30)[1:] ** 2])
    inner = [(float(egg_r(z, ai, bi)), float(z), 1) for z in zi[:-1]]
    # outer surface + inner surface (separate shells, rim closed by a flat annulus)
    outer_ob = lathe_mi(tag + '_dome_o', [(prof[0][0], NEST_RIM, 0)] + prof[1:], seg=256)
    inner_ob = lathe_mi(tag + '_dome_i', [(inner[0][0], NEST_RIM, 1)] + inner[1:] + [(0, 45 + bi, 1)], seg=256)
    rim = extrude_loops(tag + '_dome_rim', [circle(prof[0][0], 256), circle(inner[0][0], 256)], NEST_RIM - 0.01,
                        NEST_RIM + 0.01, smooth=False)
    orient_outward(outer_ob, (0, 0, 40))
    orient_outward(inner_ob, (0, 0, 40))
    # flip the inner shell so its normals point into the cavity (out of the wall material)
    me = inner_ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    mo = mat_dome_frost('dome_out', True)
    mi = mat_dome_frost('dome_in', False)
    j = bpy.data.objects.new(tag + '_dome', bpy.data.meshes.new(tag + '_dome'))
    bpy.context.scene.collection.objects.link(j)
    for o, m in ((outer_ob, mo), (inner_ob, mi), (rim, mi)):
        o.data.materials.clear()
        o.data.materials.append(mo)
        o.data.materials.append(mi)
        for p in o.data.polygons:
            p.material_index = 0 if m is mo else 1
    bpy.ops.object.select_all(action='DESELECT')
    for o in (outer_ob, inner_ob, rim):
        o.select_set(True)
    bpy.context.view_layer.objects.active = outer_ob
    bpy.ops.object.join()
    dome = outer_ob
    dome.name = tag + '_dome'
    bpy.data.objects.remove(j, do_unlink=True)
    set_auto_smooth(dome, 50)
    par = new_par('dome_' + tag)
    dome.parent = par
    if rim_down:
        dome.location = (0, 0, -NEST_RIM * MM)
    return par


# ==========================================================================================
# SCRIN (brief §5): 86 x 60 x 24 oval plinth (R6 top edges), 5 mm socket, 14 mm backrest, 8 x 2200 K points;
# the lid = upper part of an ovoid continuing the plinth outline, 75 tall, walls 3.5 (5 at the crown)
PL_A, PL_B, PL_H = 43.0, 30.0, 24.0
SOCKET_Y = -6.0
SOCKET_D = 5.0


def _ell_plan(a, b, seg):
    t = np.linspace(0, 2 * math.pi, seg, endpoint=False)

    def plan(d):
        return np.stack([max(a - d, 0.01) * np.cos(t), max(b - d, 0.01) * np.sin(t)], 1)
    return plan


def margaritar_bcy():
    B = alt_geo('margaritar')
    q = B.sections(np.array([B.z_bot]))
    return 0.5 * float(q[1][0] + q[2][0])


def socket_loop(clear=0.6, zq=None):
    """Plan outline of MĂRGĂRITAR's lower 5 mm (its widest ring in that band) + clearance, centred at SOCKET_Y."""
    B = alt_geo('margaritar')
    zq = SOCKET_D + B.z_bot if zq is None else zq
    ring = SG.resample_ring(B.ring(zq), 200)
    ctr = ring.mean(0)
    v = ring - ctr
    ln = np.linalg.norm(v, axis=1, keepdims=True)
    ring = ctr + v / ln * (ln + clear)
    return ring + np.array([0.0, SOCKET_Y - margaritar_bcy()])


def build_scrin_plinth(tag, points=None):
    par = new_par('scrin_' + tag)
    seg = 256
    prof = [(0.8, 0.0, 0), (0.0, 0.8, 0), (0.0, PL_H - 6.0, 0)]
    for a in np.linspace(0, math.pi / 2, 12)[1:]:
        prof.append((6.0 - 6.0 * math.cos(a), PL_H - 6.0 + 6.0 * math.sin(a), 0))
    prof += [(20.0, PL_H, 0), (29.2, PL_H, 0)]
    rings = [np.column_stack([_ell_plan(PL_A, PL_B, seg)(d), np.full(seg, z)]) for d, z, m in prof]
    Rn = len(rings)
    verts = np.vstack(rings + [np.array([[0, 0, 0], [0, 0, PL_H]])])
    quads = grid_quads(Rn, seg)
    tris = np.vstack([fan(Rn * seg, 0, seg, top=False), fan(Rn * seg + 1, (Rn - 1) * seg, seg, top=True)])
    pl = build_mesh(tag + '_plinth', verts, quads, tris)
    orient_outward(pl, (0, 0, 12))
    lac = mat_lacquer_pearl()
    pl.data.materials.append(lac)
    cm = bpy.data.materials.new('ROLE_cut')
    cut = extrude_loops('cut_socket', [socket_loop()], PL_H - SOCKET_D, PL_H + 6.0)
    assign(cut, cm)
    boolean(pl, [cut])
    pl.data.materials.clear()
    pl.data.materials.append(lac)
    for p in pl.data.polygons:
        p.material_index = 0
    set_auto_smooth(pl, 40)
    obs = [pl]
    # socket floor: champagne contact plate (the charging contacts meet MĂRGĂRITAR's gold sole here)
    fl = extrude_loops(tag + '_sockfloor', [socket_loop(-1.5)], PL_H - SOCKET_D, PL_H - SOCKET_D + 0.05)
    assign(fl, mat_simple('socket_floor', '#1A1816', 0.5))
    obs.append(fl)
    # 14 mm backrest behind the socket, leaning back 8 deg like the face
    B = alt_geo('margaritar')
    yb = float(B.sections(np.array([B.z_bot + SOCKET_D + 10.0]))[2][0])
    br = rounded_box(tag + '_backrest', 44 * MM, 6.5 * MM, 18 * MM, 2.8 * MM, 4)
    br.location = (0, (SOCKET_Y + yb + 1.2 + 3.25) * MM, (PL_H - 4.0 + 9.0) * MM)
    br.rotation_euler = (R(-8.0), 0, 0)
    assign(br, lac)
    obs.append(br)
    # 8 x 2200 K points on the rear half of the top (light behind SOUL, never on its face)
    g = TUNE.get('scrin_glow', 3.0) if points is None else points
    if g > 0:
        led = mat_led(tag + '_led_pts', g)
        for i, t in enumerate(np.linspace(R(18), R(162), 8)):
            p = revolve(tag + '_pt%d' % i, [(0, 0.0), (0.75, 0.0), (0.75, 0.12), (0, 0.12)], seg=24)
            p.location = ((PL_A - 9.0) * math.cos(t) * MM, (PL_B - 7.0) * math.sin(t) * MM, (PL_H - 0.05) * MM)
            assign(p, led)
            obs.append(p)
    parent_all(par, obs)
    return par


def build_scrin_lid(tag, inverted=True):
    """Ovoid lid: base = the plinth outline (86 x 60), 75 tall; walls 3.5 (5 at the crown). Two shells (outer gloss,
    inner frosted) joined by a flat rim."""
    H = 75.0
    p_ = 2.3
    seg = 256
    zs = np.concatenate([np.linspace(0, 60, 30), H - np.linspace(math.sqrt(15.0), 0, 24)[1:] ** 2])

    def f(z, h):
        return np.clip(1 - (np.asarray(z) / h) ** p_, 0, None) ** (1 / p_)

    def shell(a, b, h, name, flip):
        zz = np.concatenate([np.linspace(0, h * 0.8, 30), h - np.linspace(math.sqrt(h * 0.2), 0, 24)[1:] ** 2])
        t = np.linspace(0, 2 * math.pi, seg, endpoint=False)
        rings = [np.column_stack([a * f(z, h) * np.cos(t), b * f(z, h) * np.sin(t), np.full(seg, z)]) for z in zz[:-1]]
        Rn = len(rings)
        verts = np.vstack(rings + [np.array([[0, 0, h]])])
        ob = build_mesh(name, verts, grid_quads(Rn, seg), fan(Rn * seg, (Rn - 1) * seg, seg, top=True))
        orient_outward(ob, (0, 0, h * 0.3))
        if flip:
            bm = bmesh.new()
            bm.from_mesh(ob.data)
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
            bm.to_mesh(ob.data)
            bm.free()
        return ob

    o = shell(PL_A, PL_B, H, tag + '_lid', False)
    i = shell(PL_A - 3.5, PL_B - 3.5, H - 5.0, tag + '_lid_i', True)
    t = np.linspace(0, 2 * math.pi, seg, endpoint=False)
    rim = extrude_loops(tag + '_lid_rim', [np.stack([PL_A * np.cos(t), PL_B * np.sin(t)], 1),
                                            np.stack([(PL_A - 3.5) * np.cos(t), (PL_B - 3.5) * np.sin(t)], 1)],
                        -0.01, 0.01)
    mo, mi = mat_surlyn('surlyn_out', True), mat_surlyn('surlyn_in', False)
    for ob, k in ((o, 0), (i, 1), (rim, 1)):
        ob.data.materials.clear()
        ob.data.materials.append(mo)
        ob.data.materials.append(mi)
        for p in ob.data.polygons:
            p.material_index = k
    bpy.ops.object.select_all(action='DESELECT')
    for ob in (o, i, rim):
        ob.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.join()
    set_auto_smooth(o, 50)
    par = new_par('lid_' + tag)
    o.parent = par
    if inverted:
        # crown down, a bowl: the 5 mm crown is flattened by the table contact (1 mm)
        o.matrix_basis = Matrix.Translation((0, 0, (H - 0.6) * MM)) @ Matrix.Rotation(R(180), 4, 'X')
    return par


def limestone_slab(tag, loc=(0, 0), yaw=0.0):
    sl = rounded_box(tag + '_slab', 0.200, 0.120, 0.012, 0.0012, 3)
    sl.location = (loc[0] * MM, loc[1] * MM, 0.006)
    sl.rotation_euler = (0, 0, R(yaw))
    assign(sl, mat_limestone())
    return sl


# ==========================================================================================
# shots
HERO_T = Vector((0, -2 * MM, 37 * MM))


def shot_altA_piatra():
    """ALT A hero: PIATRA (Perlă) upright on its zinc foot, same camera / studio as the FINAL hero; the OU nest with
    its dome soft in the background (as the OU is in the FINAL hero)."""
    sc = reset()
    T = HERO_T
    day_studio(T)
    s = build_alt('ah', 'piatra', eyes='cream_look')
    pose_alt(s, (0, 0, 0), yaw=-8.0)
    n = build_nest('bg')
    n.location = V((95, 125, 0))
    n.rotation_euler = (0, 0, R(-20))
    d = build_dome('bg', rim_down=True)
    d.location = V((150, 190, 0))
    cam = cam_aed(T, -24.0, 9.0, 375.0, 100, 8.0, focus=eye_point(s))
    black_glass(cam, T, [s])
    return sc


def shot_altA_nest():
    """ALT A dock (brief shot A): PIATRA upright in its pearl nest; the frosted dome rim-down 90 mm behind-left."""
    sc = reset()
    T = Vector((0, 0, TUNE.get('an_Tz', 45.0) * MM))
    day_studio(T)
    n = build_nest('dock')
    s = build_alt('an', 'piatra', eyes='cream_look')
    # stands on the socket floor (z 12) on its foot: glass bottom edge 2.3 above the rim
    pose_alt(s, (0, 0, NEST_FLOOR + 0.02), M_extra=Matrix.Identity(4))
    s.matrix_world = Matrix.Translation(V((0, 0, NEST_FLOOR + 0.02)))
    level_eyes(s)
    d = build_dome('dock', rim_down=True)
    d.location = V((-78, 60, 0))
    cam = cam_aed(T, 20.0, 8.0, TUNE.get('an_D', 520.0), 100, 8.0, focus=eye_point(s))
    black_glass(cam, T, [s])
    return sc


def shot_altB_margaritar():
    """ALT B hero: MĂRGĂRITAR (Perlă) on a 200 x 120 x 12 limestone slab, same hero camera / studio; the closed
    SCRIN soft in the background."""
    sc = reset()
    T = Vector((0, -2 * MM, (37 + 12) * MM))
    day_studio(T)
    limestone_slab('bh', (0, 10), yaw=-8)
    s = build_alt('bh', 'margaritar', eyes='soul_smug')
    s.matrix_world = Matrix.Translation(V((0, 0, 12.0))) @ Matrix.Rotation(R(-8.0), 4, 'Z')
    level_eyes(s)
    p = build_scrin_plinth('bg')
    p.location = V((110, 150, 0))
    p.rotation_euler = (0, 0, R(-20))
    lid = build_scrin_lid('bg', inverted=False)
    lid.location = V((110, 150, PL_H - 6.0))
    lid.rotation_euler = (0, 0, R(-20))
    cam = cam_aed(T, -24.0, 9.0, 375.0, 100, 8.0, focus=eye_point(s))
    black_glass(cam, T, [s], ang=TUNE.get('b_gang', 135.0))
    return sc


def shot_altB_scrin():
    """ALT B dock: MĂRGĂRITAR in the SCRIN socket (on its gold sole, 5 mm deep), the crystal lid inverted beside it
    as a bowl (the brief's shot pose)."""
    sc = reset()
    T = Vector((TUNE.get('bs_Tx', -40.0) * MM, 0, TUNE.get('bs_Tz', 45.0) * MM))
    day_studio(T)
    p = build_scrin_plinth('dock')
    s = build_alt('bs', 'margaritar', eyes='soul_smug')
    bcy = margaritar_bcy()
    s.matrix_world = Matrix.Translation(V((0, SOCKET_Y - bcy, PL_H - SOCKET_D + 0.05)))
    level_eyes(s)
    lid = build_scrin_lid('dock', inverted=True)
    lid.location = V((-108, 40, 0))
    lid.rotation_euler = (0, 0, R(15))
    cam = cam_aed(T, 22.0, TUNE.get('bs_E', 9.0), TUNE.get('bs_D', 640.0), 100, 8.0, focus=eye_point(s))
    black_glass(cam, T, [s])
    return sc


def shot_choices():
    """Decision board: FINAL (HOPA), ALT A (PIATRA), ALT B (MĂRGĂRITAR) dead-front, same light, same scale, upright."""
    sc = reset()
    T = Vector((0, 0, 37 * MM))
    day_studio(T)
    gap = TUNE.get('ch_gap', 100.0)
    f = build_soul('chF', 'perla', eyes='soul_front')
    pose_soul(f, (-gap, 0, 0))
    a = build_alt('chA', 'piatra', eyes='soul_front')
    pose_alt(a, (0, 0, 0))
    b = build_alt('chB', 'margaritar', eyes='soul_front')
    pose_alt(b, (gap, 0, 0))
    D = TUNE.get('ch_D', 1900.0)
    cam = cam_aed(T, 0.0, TUNE.get('ch_E', 4.0), D, 200, 16.0, focus=T)
    protect_screens(cam, T, 1.6, -0.012)
    POST['bloom'] = 0.03
    for par in (f, a, b):
        mirror_card(par, cam)
        glint_strip(par, cam, name='glint_' + par.name)
    for x, lab in ((-gap, 'SOUL HOPA'), (0.0, 'PIATRA'), (gap, 'MĂRGĂRITAR')):
        pnt = V((x, -30.0, TUNE.get('ch_lab_z', -4.0)))
        ANNOT.append(dict(label=lab, a=pnt, b=pnt))
    return sc


SHOTS = {
    'altA_piatra': (shot_altA_piatra, 1600, 2000, 128),
    'altA_nest': (shot_altA_nest, 1600, 1200, 128),
    'altB_margaritar': (shot_altB_margaritar, 1600, 2000, 128),
    'altB_scrin': (shot_altB_scrin, 1600, 1200, 128),
    'choices': (shot_choices, 2400, 1200, 128),
}

main()
