"""soul_v5.py -- SOUL v5: the FINAL design (HOPA, 63 x 74 x 27.1 mm, rocker sole), the OU capsule, the COCON sleeve
and the unboxing props, built to research/design-max/render-brief.md (v5, rev. 2026-09-25). Every image is a CGI concept.

World frame (mm, x MM): origin = SOUL's land centre on the table, +z up, the face looks toward -y, +x = viewer's right.
Body geometry = soul_geo.py (pure numpy: loft L n sole ellipsoid E, done analytically per column, R1.5 rim bevel).
Reuses concepts.py -> soul_scene.py (materials, studio lights, flags, glass_eye, EXR -> post.py OIDN/AgX pipeline).

    blender -b --factory-startup --python soul_v5.py -- --shot hero [--preview] [--samples N] [--tmp DIR]
Shots: hero front_00 front_15 check1_{pearl,ember}_{0,9} side back bottom ou_night ou_closed hand family cocon
       unbox boxback      (see SHOTS at the end)
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(_HERE, 'concepts.py')).read()
exec(compile(_src[:_src.rindex('\nmain()')], os.path.join(_HERE, 'concepts.py'), 'exec'), globals())
sys.path.insert(0, _HERE)
import soul_geo as SG  # noqa: E402
from mathutils import Matrix  # noqa: E402

CACHE = os.path.join(TEX, 'cache')
os.makedirs(CACHE, exist_ok=True)
NU_BODY = 384
N_SHELL = 360
R = math.radians
G_MM = SG.GC.copy()                  # glass centre (mm)
N_FACE = SG.NRM.copy()               # face normal
UP_FACE = SG.UPV.copy()
LAND_Z = 0.2                         # the TPU ring stands 0.2 proud of the land


def V(p_mm):
    return Vector(tuple(float(c) * MM for c in p_mm))


# ==========================================================================================
# mesh helpers
def grid_quads(n_rows, n_cols, off=0):
    i = np.arange(n_rows - 1)[:, None]
    j = np.arange(n_cols)[None, :]
    a = off + i * n_cols + j
    b = off + i * n_cols + (j + 1) % n_cols
    return np.stack([a, b, b + n_cols, a + n_cols], -1).reshape(-1, 4)


def fan(center_idx, ring_off, n, top):
    j = np.arange(n)
    j2 = (j + 1) % n
    if top:
        return np.stack([ring_off + j, ring_off + j2, np.full(n, center_idx)], -1)
    return np.stack([ring_off + j2, ring_off + j, np.full(n, center_idx)], -1)


def build_mesh(name, verts_mm, quads=None, tris=None, mq=None, mt=None, smooth=True, link=True):
    Vv = np.asarray(verts_mm, float) * MM
    parts, sizes, mats = [], [], []
    for arr, m, k in ((quads, mq, 4), (tris, mt, 3)):
        if arr is not None and len(arr):
            arr = np.asarray(arr)
            parts.append(arr.ravel())
            sizes.append(np.full(len(arr), k))
            mats.append(np.zeros(len(arr), int) if m is None else np.asarray(m))
    loops = np.concatenate(parts).astype(np.int32)
    sz = np.concatenate(sizes).astype(np.int32)
    ls = np.concatenate([[0], np.cumsum(sz)[:-1]]).astype(np.int32)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(Vv))
    me.vertices.foreach_set('co', Vv.astype(np.float32).ravel())
    me.loops.add(len(loops))
    me.loops.foreach_set('vertex_index', loops)
    me.polygons.add(len(sz))
    me.polygons.foreach_set('loop_start', ls)
    me.polygons.foreach_set('loop_total', sz)
    me.polygons.foreach_set('material_index', np.concatenate(mats).astype(np.int32))
    me.polygons.foreach_set('use_smooth', np.full(len(sz), bool(smooth)))
    me.update(calc_edges=True)
    ob = bpy.data.objects.new(name, me)
    if link:
        bpy.context.scene.collection.objects.link(ob)
    return ob


def orient_outward(ob, inside_pt_mm):
    """Flip all faces if the mean normal points toward inside_pt (for open or closed surfaces)."""
    me = ob.data
    n = np.zeros(len(me.polygons) * 3)
    c = np.zeros(len(me.polygons) * 3)
    me.polygons.foreach_get('normal', n)
    me.polygons.foreach_get('center', c)
    n = n.reshape(-1, 3)
    c = c.reshape(-1, 3) - np.asarray(inside_pt_mm) * MM
    a = np.zeros(len(me.polygons))
    me.polygons.foreach_get('area', a)
    if np.sum(np.einsum('ij,ij->i', n, c) * a) < 0:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        me.update()


def apply_modifiers(ob):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me2
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return ob


def remove_obj(ob):
    me = ob.data if ob.type == 'MESH' else None
    bpy.data.objects.remove(ob, do_unlink=True)
    if me is not None and me.users == 0:
        bpy.data.meshes.remove(me)


def boolean(ob, cutters, op='DIFFERENCE'):
    coll = bpy.data.collections.new('cutters_' + ob.name)
    bpy.context.scene.collection.children.link(coll)
    for c in cutters:
        for u in list(c.users_collection):
            u.objects.unlink(c)
        coll.objects.link(c)
        c.hide_render = True
    m = ob.modifiers.new('bool', 'BOOLEAN')
    m.operation = op
    m.solver = 'EXACT'
    if len(cutters) == 1:
        m.operand_type = 'OBJECT'
        m.object = cutters[0]
    else:
        m.operand_type = 'COLLECTION'
        m.collection = coll
    try:
        m.material_mode = 'TRANSFER'
    except Exception:
        pass
    apply_modifiers(ob)
    for c in cutters:
        remove_obj(c)
    bpy.data.collections.remove(coll)
    return ob


def save_mesh_cache(path, ob, roles):
    me = ob.data
    nv, npoly = len(me.vertices), len(me.polygons)
    co = np.zeros(nv * 3, np.float32)
    me.vertices.foreach_get('co', co)
    ls = np.zeros(npoly, np.int32)
    lt = np.zeros(npoly, np.int32)
    mi = np.zeros(npoly, np.int32)
    sm = np.zeros(npoly, bool)
    me.polygons.foreach_get('loop_start', ls)
    me.polygons.foreach_get('loop_total', lt)
    me.polygons.foreach_get('material_index', mi)
    me.polygons.foreach_get('use_smooth', sm)
    vi = np.zeros(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', vi)
    np.savez_compressed(path, co=co, ls=ls, lt=lt, mi=mi, sm=sm, vi=vi, roles=np.array(roles))


def load_mesh_cache(path, name):
    D = np.load(path)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(D['co']) // 3)
    me.vertices.foreach_set('co', D['co'])
    me.loops.add(len(D['vi']))
    me.loops.foreach_set('vertex_index', D['vi'])
    me.polygons.add(len(D['ls']))
    me.polygons.foreach_set('loop_start', D['ls'])
    me.polygons.foreach_set('loop_total', D['lt'])
    roles = [str(r) for r in D['roles']]
    for r in roles:                     # slots must exist before the indices are set
        me.materials.append(bpy.data.materials.get('ROLE_' + r) or bpy.data.materials.new('ROLE_' + r))
    me.update(calc_edges=True)
    me.polygons.foreach_set('material_index', D['mi'])
    me.polygons.foreach_set('use_smooth', D['sm'])
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob, roles


def set_auto_smooth(ob, deg=40.0):
    try:
        ob.data.use_auto_smooth = True
        ob.data.auto_smooth_angle = R(deg)
    except AttributeError:
        pass


def basis(z_axis, y_axis):
    z = Vector(z_axis).normalized()
    y = Vector(y_axis).normalized()
    x = y.cross(z).normalized()
    y = z.cross(x).normalized()
    M = Matrix((x, y, z)).transposed()
    return M.to_4x4()


def extrude_loops(name, loops, z0, z1, smooth=False):
    """2D loops (mm, first = outer, later ones inside = holes) extruded between z0 and z1 (mm) -> mesh object."""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '2D'
    cu.fill_mode = 'BOTH'
    cu.extrude = (z1 - z0) / 2 * MM
    cu.resolution_u = 1
    for L in loops:
        sp = cu.splines.new('POLY')
        sp.points.add(len(L) - 1)
        for p, q in zip(sp.points, L):
            p.co = (q[0] * MM, q[1] * MM, 0, 1)
        sp.use_cyclic_u = True
    tmp = bpy.data.objects.new(name + '_c', cu)
    bpy.context.scene.collection.objects.link(tmp)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.curves.remove(cu)
    me.transform(Matrix.Translation((0, 0, (z0 + z1) / 2 * MM)))
    for p in me.polygons:
        p.use_smooth = smooth
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def ellipse(a, b, n=128, cx=0.0, cy=0.0):
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.stack([cx + a * np.cos(t), cy + b * np.sin(t)], 1)


def circle(r, n=64, cx=0.0, cy=0.0):
    return ellipse(r, r, n, cx, cy)


def arc_pad(rc, width, ang_c, span, n=24):
    """Annular-sector pad with round ends (a stadium bent on radius rc)."""
    h = width / 2
    a0, a1 = ang_c - span / 2, ang_c + span / 2
    outer = [(rc + h) * np.array([math.cos(a), math.sin(a)]) for a in np.linspace(a0, a1, n)]
    e1 = rc * np.array([math.cos(a1), math.sin(a1)])
    cap1 = [e1 + h * np.array([math.cos(a1 + t), math.sin(a1 + t)]) for t in np.linspace(0, math.pi, 10)[1:-1]]
    inner = [(rc - h) * np.array([math.cos(a), math.sin(a)]) for a in np.linspace(a1, a0, n)]
    e0 = rc * np.array([math.cos(a0), math.sin(a0)])
    cap0 = [e0 + h * np.array([math.cos(a0 + math.pi + t), math.sin(a0 + math.pi + t)])
            for t in np.linspace(0, math.pi, 10)[1:-1]]
    return np.array(outer + cap1 + inner + cap0)


def torx(r_out, r_in, n=6, k=12):
    t = np.linspace(0, 2 * math.pi, n * k, endpoint=False)
    rr = 0.5 * (r_out + r_in) + 0.5 * (r_out - r_in) * np.cos(n * t)
    return np.stack([rr * np.cos(t), rr * np.sin(t)], 1)


# ==========================================================================================
# materials (brief §7, Blender 4.0 Principled names)
_MC = {}


def _ramp(nt, stops):
    cr = nt.nodes.new('ShaderNodeValToRGB')
    els = cr.color_ramp.elements
    while len(els) < len(stops):
        els.new(0.5)
    for e, (pos, col) in zip(els, stops):
        e.position = pos
        e.color = srgb(col)
    return cr


def _facing_ramp(nt, p, stops, blend=0.45):
    lw = nt.nodes.new('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = blend
    cr = _ramp(nt, stops)
    nt.links.new(lw.outputs['Facing'], cr.inputs['Fac'])
    nt.links.new(cr.outputs['Color'], p.inputs['Base Color'])
    return cr


def _tc(nt):
    return nt.nodes.new('ShaderNodeTexCoord')


def _flake_bump(nt, p, scale=30000.0, strength=0.02, dist=0.00001, chain=None):
    tc = _tc(nt)
    vo = nt.nodes.new('ShaderNodeTexVoronoi')
    vo.inputs['Scale'].default_value = scale
    nt.links.new(tc.outputs['Object'], vo.inputs['Vector'])
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = strength
    bp.inputs['Distance'].default_value = dist
    nt.links.new(vo.outputs['Distance'], bp.inputs['Height'])
    if chain is not None:
        nt.links.new(chain, bp.inputs['Normal'])
    nt.links.new(bp.outputs['Normal'], p.inputs['Normal'])
    return bp


def _flecks(nt, p, scale, frac, col, rough=0.25):
    """Sparse metallic flecks: Voronoi cell colour > 1 - frac -> gold metal."""
    tc = _tc(nt)
    vo = nt.nodes.new('ShaderNodeTexVoronoi')
    vo.inputs['Scale'].default_value = scale
    nt.links.new(tc.outputs['Object'], vo.inputs['Vector'])
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(vo.outputs['Color'], sep.inputs['Color'])
    gt = nt.nodes.new('ShaderNodeMath')
    gt.operation = 'GREATER_THAN'
    gt.inputs[1].default_value = 1.0 - frac
    nt.links.new(sep.outputs[0], gt.inputs[0])
    base_link = p.inputs['Base Color'].links[0].from_socket if p.inputs['Base Color'].links else None
    mc = nt.nodes.new('ShaderNodeMix')
    mc.data_type = 'RGBA'
    nt.links.new(gt.outputs[0], mc.inputs['Factor'])
    if base_link is not None:
        nt.links.new(base_link, mc.inputs['A'])
    else:
        mc.inputs['A'].default_value = p.inputs['Base Color'].default_value
    mc.inputs['B'].default_value = srgb(col)
    nt.links.new(mc.outputs['Result'], p.inputs['Base Color'])
    for key, a, b in (('Metallic', p.inputs['Metallic'].default_value, 1.0),
                      ('Roughness', p.inputs['Roughness'].default_value, rough)):
        mm = nt.nodes.new('ShaderNodeMix')
        mm.data_type = 'FLOAT'
        nt.links.new(gt.outputs[0], mm.inputs['Factor'])
        mm.inputs['A'].default_value = a
        mm.inputs['B'].default_value = b
        nt.links.new(mm.outputs['Result'], p.inputs[key])


def mat_pearl5(name='pearl', coat_r=0.03, rough=0.20, metal=0.06, sheen=0.25, engrave=False):
    m, nt, p, out = new_mat(name)
    _facing_ramp(nt, p, [(0.0, '#F6F1E8'), (0.55, '#F3E7EA'), (1.0, '#E8ECF4')])
    set_in(p, 'Roughness', rough)
    set_in(p, 'Metallic', metal)
    set_in(p, 'Specular IOR Level', 0.5)
    set_in(p, 'Subsurface Weight', 0.12)
    set_in(p, 'Subsurface Radius', (1.0, 0.8, 0.6))
    set_in(p, 'Subsurface Scale', 0.0015)
    set_in(p, 'Coat Weight', 1.0)
    set_in(p, 'Coat Roughness', coat_r)
    set_in(p, 'Coat IOR', 1.5)
    set_in(p, 'Sheen Weight', sheen)
    set_in(p, 'Sheen Roughness', 0.35)
    set_in(p, 'Sheen Tint', srgb('#F6EDFF'))
    bp = _flake_bump(nt, p)
    if engrave:
        _engrave(nt, p, bp, rough, coat_r)
    return m


def _engrave(nt, p, flake_bump, rough, coat_r):
    """Sole engraving mask (plan-projected from below): roughness 0.3 -> 0.55, bump 0.05 mm."""
    tc = _tc(nt)
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1 / 0.060, 1 / 0.060, 1)
    mp.inputs['Location'].default_value = (0.5, 0.5, 0)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    img = nt.nodes.new('ShaderNodeTexImage')
    img.image = bpy.data.images.load(os.path.join(TEX, 'sole_engrave.png'), check_existing=True)
    img.image.colorspace_settings.name = 'Non-Color'
    img.extension = 'CLIP'
    img.interpolation = 'Cubic'
    nt.links.new(mp.outputs['Vector'], img.inputs['Vector'])
    # only on the underside (z < 12 mm): avoid projecting onto the flanks
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], sep.inputs[0])
    lt = nt.nodes.new('ShaderNodeMath')
    lt.operation = 'LESS_THAN'
    lt.inputs[1].default_value = 0.012
    nt.links.new(sep.outputs[2], lt.inputs[0])
    mask = nt.nodes.new('ShaderNodeMath')
    mask.operation = 'MULTIPLY'
    nt.links.new(img.outputs['Color'], mask.inputs[0])
    nt.links.new(lt.outputs[0], mask.inputs[1])
    # laser marking on pearl PC also greys the surface a little: keeps the 0.6 mm caps legible
    bc = p.inputs['Base Color'].links[0].from_socket if p.inputs['Base Color'].links else None
    mcol = nt.nodes.new('ShaderNodeMix')
    mcol.data_type = 'RGBA'
    mcol.blend_type = 'MULTIPLY'
    nt.links.new(mask.outputs[0], mcol.inputs['Factor'])
    if bc is not None:
        nt.links.new(bc, mcol.inputs['A'])
    else:
        mcol.inputs['A'].default_value = p.inputs['Base Color'].default_value
    mcol.inputs['B'].default_value = (0.78, 0.77, 0.76, 1)
    nt.links.new(mcol.outputs['Result'], p.inputs['Base Color'])
    for key, a, b in (('Roughness', max(rough, 0.3), 0.55), ('Coat Roughness', coat_r, 0.55)):
        mm = nt.nodes.new('ShaderNodeMix')
        mm.data_type = 'FLOAT'
        nt.links.new(mask.outputs[0], mm.inputs['Factor'])
        mm.inputs['A'].default_value = a
        mm.inputs['B'].default_value = b
        nt.links.new(mm.outputs['Result'], p.inputs[key])
    bp = nt.nodes.new('ShaderNodeBump')
    bp.invert = True
    bp.inputs['Strength'].default_value = 1.0
    bp.inputs['Distance'].default_value = 0.00005
    nt.links.new(mask.outputs[0], bp.inputs['Height'])
    nt.links.new(flake_bump.outputs['Normal'], bp.inputs['Normal'])
    nt.links.new(bp.outputs['Normal'], p.inputs['Normal'])
    cb = nt.nodes.new('ShaderNodeBump')
    cb.invert = True
    cb.inputs['Strength'].default_value = 1.0
    cb.inputs['Distance'].default_value = 0.00005
    nt.links.new(mask.outputs[0], cb.inputs['Height'])
    nt.links.new(cb.outputs['Normal'], p.inputs['Coat Normal'])


def mat_onyx(name='onyx', coat_r=0.015, engrave=False):
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', srgb('#0A0A0B'))
    set_in(p, 'Roughness', 0.10)
    set_in(p, 'Specular IOR Level', 0.5)
    set_in(p, 'Coat Weight', 1.0)
    set_in(p, 'Coat Roughness', coat_r)
    set_in(p, 'Coat IOR', 1.5)
    _flecks(nt, p, 60000.0, 0.002, '#BFBFBF', 0.2)
    bp = _flake_bump(nt, p)
    if engrave:
        _engrave(nt, p, bp, 0.10, coat_r)
    return m


def mat_lac(name, facing, grazing, metal, rough, coat_tint, fleck_frac, sss=None, coat_ior=1.55):
    m, nt, p, out = new_mat(name)
    _facing_ramp(nt, p, [(0.0, facing), (1.0, grazing)])
    set_in(p, 'Metallic', metal)
    set_in(p, 'Roughness', rough)
    set_in(p, 'Coat Weight', 1.0)
    set_in(p, 'Coat Roughness', 0.012)
    set_in(p, 'Coat IOR', coat_ior)
    set_in(p, 'Coat Tint', srgb(coat_tint))
    if sss:
        set_in(p, 'Subsurface Weight', sss[0])
        set_in(p, 'Subsurface Radius', sss[1])
        set_in(p, 'Subsurface Scale', sss[2])
    _flecks(nt, p, 12000.0, fleck_frac, '#D4AF37', 0.25)
    _flake_bump(nt, p)
    return m


def mat_lapis(name='lapis'):
    # brief ramp #1B3A8F -> #2A4FB0 read L* ~40 on the lit side under the family light; darkened toward the
    # brief's own target (lit side L* ~30)
    return mat_lac(name, '#132B6E', '#1F3F95', 0.20, 0.28, '#C9D6FF', 0.003)


def mat_amber(name='amber'):
    return mat_lac(name, '#7A3A10', '#C98A3A', 0.25, 0.25, '#FFD9A0', 0.0015, sss=(0.05, (1.0, 0.5, 0.2), 0.002))


def mat_ghost(name='ghost'):
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', srgb('#7A7A80'))
    set_in(p, 'Transmission Weight', 0.35)
    set_in(p, 'Roughness', 0.38)
    set_in(p, 'IOR', 1.585)
    set_in(p, 'Coat Weight', 0.3)
    set_in(p, 'Coat Roughness', 0.3)
    va = nt.nodes.new('ShaderNodeVolumeAbsorption')
    va.inputs['Color'].default_value = srgb('#9A9AA0')
    va.inputs['Density'].default_value = 150.0
    nt.links.new(va.outputs[0], out.inputs['Volume'])
    return m


def mat_solid_sole(name, col, rough=0.30, coat_r=0.10, engrave=True, metal=0.0, coat_w=1.0, spec=0.5):
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', srgb(col))
    set_in(p, 'Roughness', rough)
    set_in(p, 'Metallic', metal)
    set_in(p, 'Specular IOR Level', spec)
    set_in(p, 'Coat Weight', coat_w)
    set_in(p, 'Coat Roughness', coat_r)
    set_in(p, 'Coat IOR', 1.5)
    bp = _flake_bump(nt, p, strength=0.01)
    if engrave:
        _engrave(nt, p, bp, rough, coat_r)
    return m


def mat_sole_glow(name='sole_glow'):
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', srgb('#F2EEE7'))
    set_in(p, 'Transmission Weight', 0.9)
    set_in(p, 'Roughness', 0.45)
    set_in(p, 'IOR', 1.585)
    return m


def mat_sole_alu(name='sole_alu'):
    m = mat_metal(name, srgb('#D8C3A0')[:3], 0.28, 0.3, 'Z')
    return m


def mat_glass5(name, eyes, strength):
    """Black AR cover glass over the emissive AMOLED: mask and panel both #020202 so the screen edge vanishes."""
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', srgb('#020202'))
    set_in(p, 'Roughness', 0.02)
    set_in(p, 'IOR', 1.52)
    set_in(p, 'Specular IOR Level', 0.35)
    tc = _tc(nt)
    mp = nt.nodes.new('ShaderNodeMapping')
    s = 1.0 / (2 * 21.88 * MM)
    mp.inputs['Scale'].default_value = (s, s, 1)
    mp.inputs['Location'].default_value = (0.5, 0.5, 0)
    img = nt.nodes.new('ShaderNodeTexImage')
    img.image = bpy.data.images.load(os.path.join(TEX, 'eyes_%s.png' % eyes), check_existing=True)
    img.extension = 'CLIP'
    img.interpolation = 'Cubic'
    nt.links.new(tc.outputs['Object'], mp.inputs[0])
    nt.links.new(mp.outputs[0], img.inputs[0])
    nt.links.new(img.outputs['Color'], p.inputs['Emission Color'])
    set_in(p, 'Emission Strength', strength)
    return m


def mat_simple(name, col, rough, metal=0.0, spec=0.5, trans=0.0, ior=1.5, aniso=0.0, coat=0.0, coat_r=0.1):
    key = (name, col, rough, metal, spec, trans, ior, aniso, coat, coat_r)
    if key in _MC and _MC[key].name in bpy.data.materials:
        return _MC[key]
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', srgb(col))
    set_in(p, 'Roughness', rough)
    set_in(p, 'Metallic', metal)
    set_in(p, 'Specular IOR Level', spec)
    if trans:
        set_in(p, 'Transmission Weight', trans)
        set_in(p, 'IOR', ior)
    if aniso:
        set_in(p, 'Anisotropic', aniso)
    if coat:
        set_in(p, 'Coat Weight', coat)
        set_in(p, 'Coat Roughness', coat_r)
    _MC[key] = m
    return m


def gap_dark():
    return mat_simple('gap_dark', '#030303', 0.8)


def mat_led(name, strength, temp=2200.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes['Principled BSDF'])
    bb = nt.nodes.new('ShaderNodeBlackbody')
    bb.inputs['Temperature'].default_value = temp
    e = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(bb.outputs['Color'], e.inputs['Color'])
    e.inputs['Strength'].default_value = strength
    nt.links.new(e.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    return m


def mat_ou_lid(name, outer=True, dark=False, night=False):
    """Frosted PC lid: gloss outside (r 0.05), VDI-18 frost inside (r 0.45), Transmission 0.9, IOR 1.58; a milky
    volume scatter in the 2.2 mm wall gives the frosted-PC diffusion (and the lantern glow when closed)."""
    m, nt, p, out = new_mat(name)
    base = '#3A3A3F' if dark else '#F4EFE8'
    set_in(p, 'Base Color', srgb(base))
    # brief: Transmission 0.9. Blender 4.0 has no multiple-scatter frost, so 0.9 reads as smoke glass over the dark
    # cavity; 0.6 at night (lantern) and 0.4 by day read as frosted pearl PC
    tr = TUNE.get('lid_tr', 0.6 if night else 0.4)
    set_in(p, 'Transmission Weight', 0.8 if dark else tr)
    set_in(p, 'IOR', 1.58)
    set_in(p, 'Roughness', 0.05 if outer else 0.45)
    vs = nt.nodes.new('ShaderNodeVolumeScatter')
    vs.inputs['Color'].default_value = (0.985, 0.975, 0.96, 1) if not dark else srgb(base)
    vs.inputs['Density'].default_value = TUNE.get('lid_dens', 700.0 if night else 320.0)
    vs.inputs['Anisotropy'].default_value = 0.0
    va = nt.nodes.new('ShaderNodeVolumeAbsorption')
    va.inputs['Color'].default_value = (1.0, 0.95, 0.88, 1) if not dark else (0.5, 0.5, 0.52, 1)
    va.inputs['Density'].default_value = 6.0 if not dark else 250.0
    add = nt.nodes.new('ShaderNodeAddShader')
    nt.links.new(vs.outputs[0], add.inputs[0])
    nt.links.new(va.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs['Volume'])
    return m


def mat_knit(name, col='#E9E2D6'):
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', srgb(col))
    set_in(p, 'Roughness', 0.9)
    set_in(p, 'Sheen Weight', 0.6)
    set_in(p, 'Sheen Roughness', 0.5)
    set_in(p, 'Specular IOR Level', 0.3)
    tc = _tc(nt)
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], sep.inputs[0])
    # ribs: wale lines around the vertical axis (1.1 mm pitch on a ~30 mm radius) with a V stitch per course
    at = nt.nodes.new('ShaderNodeMath')
    at.operation = 'ARCTAN2'
    nt.links.new(sep.outputs[1], at.inputs[0])
    nt.links.new(sep.outputs[0], at.inputs[1])
    ang = nt.nodes.new('ShaderNodeMath')
    ang.operation = 'MULTIPLY'
    ang.inputs[1].default_value = 170.0
    nt.links.new(at.outputs[0], ang.inputs[0])
    zc = nt.nodes.new('ShaderNodeMath')
    zc.operation = 'MULTIPLY'
    zc.inputs[1].default_value = 2 * math.pi / 0.0009
    nt.links.new(sep.outputs[2], zc.inputs[0])
    frac = nt.nodes.new('ShaderNodeMath')      # which half of the rib -> V slant
    frac.operation = 'SINE'
    nt.links.new(ang.outputs[0], frac.inputs[0])
    slant = nt.nodes.new('ShaderNodeMath')
    slant.operation = 'MULTIPLY_ADD'
    slant.inputs[1].default_value = 1.2
    nt.links.new(frac.outputs[0], slant.inputs[0])
    nt.links.new(zc.outputs[0], slant.inputs[2])
    st = nt.nodes.new('ShaderNodeMath')
    st.operation = 'SINE'
    nt.links.new(slant.outputs[0], st.inputs[0])
    rib = nt.nodes.new('ShaderNodeMath')
    rib.operation = 'ABSOLUTE'
    nt.links.new(frac.outputs[0], rib.inputs[0])
    h1 = nt.nodes.new('ShaderNodeMath')
    h1.operation = 'MULTIPLY_ADD'
    h1.inputs[1].default_value = 0.35
    nt.links.new(st.outputs[0], h1.inputs[0])
    nt.links.new(rib.outputs[0], h1.inputs[2])
    vo = nt.nodes.new('ShaderNodeTexVoronoi')
    vo.inputs['Scale'].default_value = 2500.0
    nt.links.new(tc.outputs['Object'], vo.inputs['Vector'])
    h2 = nt.nodes.new('ShaderNodeMath')
    h2.operation = 'MULTIPLY_ADD'
    h2.inputs[1].default_value = 0.25
    nt.links.new(vo.outputs['Distance'], h2.inputs[0])
    nt.links.new(h1.outputs[0], h2.inputs[2])
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.9
    bp.inputs['Distance'].default_value = 0.0003
    nt.links.new(h2.outputs[0], bp.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], p.inputs['Normal'])
    # a touch of tonal variation in the yarn
    cr = nt.nodes.new('ShaderNodeMix')
    cr.data_type = 'RGBA'
    nt.links.new(h2.outputs[0], cr.inputs['Factor'])
    c = srgb(col)
    cr.inputs['A'].default_value = (c[0] * 0.80, c[1] * 0.79, c[2] * 0.77, 1)
    cr.inputs['B'].default_value = c
    nt.links.new(cr.outputs['Result'], p.inputs['Base Color'])
    return m


def mat_pulp(name='pulp'):
    m, nt, p, out = new_mat(name)
    set_in(p, 'Base Color', srgb('#CFC6B6'))
    set_in(p, 'Roughness', 0.95)
    set_in(p, 'Specular IOR Level', 0.2)
    _noise_bump(nt, p, 900.0, 0.6, 0.0004)
    return m


def mat_image(name, img_name, rough=0.85, u_axis='x', flip_u=False, v_axis='z', foil_mask=None, colorspace='sRGB'):
    """Board with a printed image mapped on Generated coordinates (0..1 over the object's bounds)."""
    m, nt, p, out = new_mat(name)
    set_in(p, 'Roughness', rough)
    set_in(p, 'Specular IOR Level', 0.25)
    tc = _tc(nt)
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    ax = {'x': 0, 'y': 1, 'z': 2}
    u = sep.outputs[ax[u_axis]]
    if flip_u:
        inv = nt.nodes.new('ShaderNodeMath')
        inv.operation = 'SUBTRACT'
        inv.inputs[0].default_value = 1.0
        nt.links.new(u, inv.inputs[1])
        u = inv.outputs[0]
    cmb = nt.nodes.new('ShaderNodeCombineXYZ')
    nt.links.new(u, cmb.inputs[0])
    nt.links.new(sep.outputs[ax[v_axis]], cmb.inputs[1])
    img = nt.nodes.new('ShaderNodeTexImage')
    img.image = bpy.data.images.load(os.path.join(TEX, img_name), check_existing=True)
    img.image.colorspace_settings.name = colorspace
    img.extension = 'EXTEND'
    nt.links.new(cmb.outputs[0], img.inputs[0])
    if foil_mask:
        # mask image: board cream where 0, foil where 1
        mixc = nt.nodes.new('ShaderNodeMix')
        mixc.data_type = 'RGBA'
        nt.links.new(img.outputs['Color'], mixc.inputs['Factor'])
        mixc.inputs['A'].default_value = srgb('#F1E9DA')
        mixc.inputs['B'].default_value = srgb('#FFF0C8')
        nt.links.new(mixc.outputs['Result'], p.inputs['Base Color'])
        for key, a, b in (('Metallic', 0.0, 0.55), ('Roughness', rough, 0.32)):
            mm = nt.nodes.new('ShaderNodeMix')
            mm.data_type = 'FLOAT'
            nt.links.new(img.outputs['Color'], mm.inputs['Factor'])
            mm.inputs['A'].default_value = a
            mm.inputs['B'].default_value = b
            nt.links.new(mm.outputs['Result'], p.inputs[key])
    else:
        nt.links.new(img.outputs['Color'], p.inputs['Base Color'])
    return m


# colourways: body material, standard (tone-on-tone) sole
def colourway_mats(cw, sole=None):
    cw = cw.lower()
    if cw == 'perla':
        body = mat_pearl5('pearl')
        std = 'pearl'
    elif cw == 'onix':
        body = mat_onyx('onyx')
        std = 'onyx'
    elif cw == 'lapis':
        body = mat_lapis()
        std = 'lapis'
    elif cw == 'chihlimbar':
        body = mat_amber()
        std = 'amber'
    elif cw == 'fum':
        body = mat_ghost()
        std = 'glow'
    else:
        raise ValueError(cw)
    sole = sole or std
    if sole == 'pearl':
        sm = mat_pearl5('sole_pearl', coat_r=0.10, engrave=True)
    elif sole == 'onyx':
        sm = mat_onyx('sole_onyx', coat_r=0.10, engrave=True)
    elif sole == 'lapis':
        sm = mat_solid_sole('sole_lapis', '#1E3E96')
    elif sole == 'amber':
        sm = mat_solid_sole('sole_amber', '#8A4A18')
    elif sole == 'ember':
        sm = mat_solid_sole('sole_ember', '#D8572A')
    elif sole == 'cream':
        sm = mat_solid_sole('sole_cream', '#FFF0C8')
    elif sole == 'glow':
        sm = mat_sole_glow()
    elif sole == 'alu':
        sm = mat_sole_alu()
    else:
        raise ValueError(sole)
    return body, sm


# ==========================================================================================
# SOUL body
_GEO = {}


def soul_geo():
    if 'g' not in _GEO:
        t0 = time.time()
        _GEO['g'] = SG.SoulGeo(NU=NU_BODY)
        print('  soul_geo %.1fs' % (time.time() - t0))
    return _GEO['g']


def body_rows():
    """All rows bottom (land centre) -> crown, plus the index of the split row A."""
    if 'rows' in _GEO:
        return _GEO['rows'], _GEO['iA']
    g = soul_geo()
    land = g.land_rows(10)[::-1]
    sole = g.sole_rows(34)[::-1]
    fil = g.fillet_rows(8)[::-1]
    shell = g.shell_rows_tau(N_SHELL)
    rows = np.concatenate([land, sole[1:], fil[1:], shell[1:]], 0)
    iA = len(land) + len(sole) - 1 + len(fil) - 1
    _GEO['rows'], _GEO['iA'] = rows, iA
    return rows, iA


def seam_points(side, g=None, n=260):
    """Girdle seam (side*w, y_s, z) from just above the sole rim up to the crown pole."""
    zz = np.linspace(4.0, 74.0, 4000)
    w, yf, yb, ys, c, pf = SG.sections(zz)
    P = np.stack([side * w, ys, zz], 1)
    lv = SG.e_level(P)
    i0 = int(np.argmax(lv < -0.004)) + 12
    z0 = zz[i0] + 0.35
    s = np.linspace(0, 1, n)
    zs = 74.0 - (74.0 - z0) * (1 - s) ** 1.0
    # dense near the crown: map through sqrt
    zs = 74.0 - (74.0 - z0) * (1 - s) ** 2
    zs = np.sort(np.concatenate([np.linspace(z0, 70.0, n // 2), 74.0 - np.linspace(2.0, 0.0, n // 2) ** 2]))
    zs = np.unique(np.clip(zs, z0, 74.0))
    w, yf, yb, ys, c, pf = SG.sections(zs)
    P = np.stack([side * w, ys, zs], 1)
    # outward normal of the seam: n = (side, 0, -w') normalised
    dw = np.gradient(w, zs)
    nrm = np.stack([np.full_like(zs, side), np.zeros_like(zs), -side * side * dw], 1)
    nrm[-1] = (0, 0, 1)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    return P, nrm


def body_mesh_raw(name, mat_roles=('shell', 'sole')):
    rows, iA = body_rows()
    Rn, N = rows.shape[0], rows.shape[1]
    verts = rows.reshape(-1, 3)
    bottom = len(verts)
    top = bottom + 1
    verts = np.vstack([verts, [[0, 0, 0]], [[0.0, -1.0, 74.0]]])
    quads = grid_quads(Rn, N)
    mq = np.repeat(np.where(np.arange(Rn - 1) >= iA, 0, 1), N)
    tris = np.vstack([fan(bottom, 0, N, top=False), fan(top, (Rn - 1) * N, N, top=True)])
    mt = np.concatenate([np.ones(N, int), np.zeros(N, int)])
    ob = build_mesh(name, verts, quads, tris, mq, mt)
    orient_outward(ob, (0, 0, 35))
    return ob


def stadium_cutter(name, side, z0, z1, width=0.9, depth=2.0, out=1.0):
    """Slot cutter swept along the seam curve from z0 to z1 (rounded ends), side = +1/-1."""
    zz = np.linspace(z0 - 0.5, z1 + 0.5, 400)
    w, yf, yb, ys, c, pf = SG.sections(zz)
    P = np.stack([side * w, ys, zz], 1)
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    L = s[-1]
    sc = 0.5 * L
    half = 0.5 * (s[np.argmin(np.abs(zz - z1))] - s[np.argmin(np.abs(zz - z0))])
    k = np.abs(s - sc) <= half
    P, s, zz, w = P[k], s[k], zz[k], w[k]
    dw = np.gradient(w, zz)
    nrm = np.stack([np.full_like(zz, side), np.zeros_like(zz), -dw * side * side], 1)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    hw = width / 2
    d = np.abs(s - sc)
    endr = np.clip(d - (half - hw), 0, None)
    hwid = np.sqrt(np.clip(hw * hw - endr * endr, 0.0004, None))
    yv = np.array([0.0, 1.0, 0.0])
    ring = []
    for i in range(len(P)):
        n = nrm[i]
        a = P[i] + n * out
        b = P[i] - n * depth
        ring.append([a - yv * hwid[i], a + yv * hwid[i], b + yv * hwid[i], b - yv * hwid[i]])
    ring = np.array(ring)
    Rn = len(ring)
    verts = ring.reshape(-1, 3)
    quads = grid_quads(Rn, 4)
    caps = np.array([[0, 1, 2, 3], [(Rn - 1) * 4 + 3, (Rn - 1) * 4 + 2, (Rn - 1) * 4 + 1, (Rn - 1) * 4 + 0]])
    ob = build_mesh(name, verts, np.vstack([quads, caps]), smooth=False)
    orient_outward(ob, P[len(P) // 2] - nrm[len(P) // 2] * depth / 2)
    return ob


def pin_cutter(name, side, z, r=0.35, depth=2.0, out=1.0):
    w, yf, yb, ys, c, pf = SG.sections(np.array([z - 0.05, z, z + 0.05]))
    P = np.array([side * w[1], ys[1], z])
    dw = (w[2] - w[0]) / 0.1
    n = np.array([side, 0.0, -dw])
    n /= np.linalg.norm(n)
    ob = revolve(name, [(0, -depth), (r, -depth), (r, out), (0, out)], seg=24)
    ob.matrix_world = Matrix.Translation(V(P)) @ basis(n, (0, 1, 0))
    bpy.context.view_layer.update()
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)
    return ob


def seat_cutter(name):
    ob = revolve(name, [(0, -0.8), (26.15, -0.8), (26.15, 1.8), (0, 1.8)], seg=384)
    for p in ob.data.polygons:
        p.use_smooth = False
    ob.data.transform(Matrix.Translation(V(G_MM)) @ basis(N_FACE, UP_FACE))
    return ob


def body_mesh(name):
    """Closed SOUL body with the glass seat, speaker slot and mic pinholes cut (cached). Slots: shell, sole, gap."""
    path = os.path.join(CACHE, 'soul_body_v5_%d_%d.npz' % (NU_BODY, N_SHELL))
    if os.path.exists(path):
        ob, roles = load_mesh_cache(path, name)
        set_auto_smooth(ob)
        return ob, roles
    t0 = time.time()
    ob = body_mesh_raw(name)
    for role in ('shell', 'sole'):
        ob.data.materials.append(bpy.data.materials.new('ROLE_' + role))
    cut_mat = bpy.data.materials.new('ROLE_gap')
    cutters = [seat_cutter('cut_seat'), stadium_cutter('cut_slot', +1, 46.0, 58.0),
               pin_cutter('cut_mic50', -1, 50.0), pin_cutter('cut_mic22', -1, 22.0)]
    for c in cutters:
        assign(c, cut_mat)
    boolean(ob, cutters)
    roles = [m.name.replace('ROLE_', '').split('.')[0] for m in ob.data.materials]
    save_mesh_cache(path, ob, roles)
    print('  body mesh built + booleans %.1fs, %d faces, roles %s' % (time.time() - t0, len(ob.data.polygons), roles))
    set_auto_smooth(ob)
    return ob, roles


def split_groove_points():
    g = soul_geo()
    rows, iA = body_rows()
    A = rows[iA]
    up = rows[iA + 1] - A
    tang = np.roll(A, -1, 0) - np.roll(A, 1, 0)
    n = np.cross(tang, up)
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    c = A - np.array([0, 0, 35.0])
    if np.mean(np.einsum('ij,ij->i', n, c)) < 0:
        n = -n
    return A, n


SOULS = {}


def build_soul(tag, cw='perla', sole=None, eyes='soul_front', strength=2.6, details=True, glass_on=True):
    """One SOUL. Returns the parent empty (land centre). The glass child is counter-rotated by level_eyes()."""
    par = new_par('soul_' + tag)
    body_m, sole_m = colourway_mats(cw, sole)
    gd = gap_dark()
    ob, roles = body_mesh('body_' + tag)
    for i, r in enumerate(roles):
        ob.data.materials[i] = {'shell': body_m, 'sole': sole_m, 'gap': gd}[r]
    obs = [ob]
    # glass (flat 2.5D disc, dome R ~4 m), top 0.07 mm below the table
    g = glass_eye(tag, 26.0, 0.0, 0.08, -0.7, 'soul_front', strength=strength, r_screen=21.88)
    assign(g, mat_glass5('glass_' + tag, eyes if glass_on else 'soul_closed', strength if glass_on else 0.0))
    M_gl = Matrix.Translation(V(G_MM - 0.15 * N_FACE)) @ basis(N_FACE, UP_FACE)
    g.matrix_basis = M_gl
    obs.append(g)
    # shadow gap ring between the glass and the seat
    gr = revolve_closed(tag + '_gapring', [(25.98, -0.40), (26.17, -0.40), (26.17, -0.25), (25.98, -0.25)], seg=256)
    gr.matrix_basis = Matrix.Translation(V(G_MM)) @ basis(N_FACE, UP_FACE)
    assign(gr, gd)
    obs.append(gr)
    # girdle seam: one sunk tube from the rim on -x over the crown to the rim on +x
    Pm, nm = seam_points(-1)
    Pp, npp = seam_points(+1)
    pts = np.vstack([Pm - nm * 0.05, (Pp - npp * 0.05)[::-1][1:]])
    sm = curve_obj(tag + '_seam', [tuple(p * MM) for p in pts], 0.1 * MM, res=3)
    assign(sm, gd)
    obs.append(sm)
    # 0.10 mm groove at the sole split
    A, nA = split_groove_points()
    gpts = A - nA * 0.02
    gv = curve_obj(tag + '_split', [tuple(p * MM) for p in gpts], 0.05 * MM, closed=True, res=2)
    assign(gv, gd)
    obs.append(gv)
    if details:
        obs += bottom_details(tag)
    if cw == 'fum':
        obs += ghost_inside(tag)
    parent_all(par, obs)
    SOULS[par.name] = dict(glass=g, M_gl=M_gl.copy(), body=ob)
    par.location = (0, 0, LAND_Z * MM)
    return par


def bottom_details(tag):
    obs = []
    ea, eb = 6.0, 5.45
    pads = [circle(0.9, 48)] + [arc_pad(4.0, 1.2, R(a), R(60)) for a in (0, 90, 180, 270)]
    coin = extrude_loops(tag + '_coin', [ellipse(ea, eb, 160)] + pads, -0.003, 1.0)
    assign(coin, mat_simple('fr4', '#121212', 0.55, spec=0.4))
    obs.append(coin)
    for i, pl in enumerate(pads):
        pd = extrude_loops(tag + '_pad%d' % i, [pl], 0.15, 0.6)
        assign(pd, mat_simple('gold', '#E3C07A', 0.18, metal=1.0))
        obs.append(pd)
    ring = extrude_loops(tag + '_tpu', [ellipse(6.8, 6.25, 160), ellipse(6.0, 5.45, 160)], -LAND_Z, 0.3)
    assign(ring, mat_simple('tpu_clear', '#F2F2F2', 0.3, trans=0.9, ior=1.5))
    obs.append(ring)
    # 2 x Torx T5 heads (dia 2.6) flush on the sole ellipsoid (brief: (+-14, +3); nudged 0.4 mm inward to clear the rim bevel)
    for sx in (-1, 1):
        x, y = sx * 13.8, 2.7
        zq = SG.EZ - SG.EC * math.sqrt(1 - (x / SG.EA) ** 2 - (y / SG.EB) ** 2)
        p = np.array([x, y, zq])
        n = -SG.e_normal(p)          # pointing into the body
        head = revolve(tag + '_torx%d' % sx, [(0, 0.02), (1.22, 0.02), (1.3, -0.05), (1.3, -0.6), (0, -0.6)], seg=48)
        head.matrix_basis = Matrix.Translation(V(p)) @ basis(-n, (1, 0, 0))
        assign(head, mat_simple('screw', '#BDB8B0', 0.30, metal=1.0))
        obs.append(head)
        st = extrude_loops(tag + '_torxs%d' % sx, [torx(0.72, 0.5)], 0.0, 0.03)
        st.matrix_basis = Matrix.Translation(V(p)) @ basis(-n, (1, 0, 0))
        assign(st, gap_dark())
        obs.append(st)
    return obs


def ghost_inside(tag):
    """FUM: an inner pearl liner (the body shrunk ~2.3 mm) and the pearl heart plate behind the glass."""
    rows, iA = body_rows()
    c = np.array([0.0, -0.5, 36.0])
    sc = np.array([(31.5 - 2.3) / 31.5, (20.0 - 4.6) / 20.0, (74.0 - 4.6) / 74.0])
    inner = c + (rows - c) * sc
    Rn, N = inner.shape[:2]
    verts = np.vstack([inner.reshape(-1, 3), [c + (np.array([0, 0, 0]) - c) * sc], [c + (np.array([0, -1, 74]) - c) * sc]])
    quads = grid_quads(Rn, N)
    tris = np.vstack([fan(Rn * N, 0, N, top=False), fan(Rn * N + 1, (Rn - 1) * N, N, top=True)])
    ob = build_mesh(tag + '_liner', verts, quads, tris)
    orient_outward(ob, (0, 0, 35))
    assign(ob, mat_pearl5('ghost_liner', rough=0.4, coat_r=0.3))
    hp = revolve(tag + '_heart', [(0, 0), (23.0, 0), (23.0, -1.0), (0, -1.0)], seg=128)
    hp.matrix_basis = Matrix.Translation(V(G_MM - 3.0 * N_FACE)) @ basis(N_FACE, UP_FACE)
    assign(hp, mat_simple('heart_plate', '#F2EEE7', 0.3))
    return [ob, hp]


# ------------------------------------------------------------------------------------------
# poses (brief §2.3)
def pose_soul(par, loc_mm=(0, 0, 0), yaw=0.0, roll=0.0, pitch=0.0, settle_=True, M_extra=None):
    """roll > 0 tips the top toward +x, pitch > 0 tips it back (+y); small angles pivot on the land edge."""
    Rrp = Matrix.Rotation(R(roll), 4, 'Y') @ Matrix.Rotation(R(-pitch), 4, 'X')
    if abs(roll) > 1e-6 or abs(pitch) > 1e-6:
        a = math.atan2(math.sin(R(pitch)), math.sin(R(roll)))
        e = Vector((6.9 * math.cos(a) * MM, 6.37 * math.sin(a) * MM, 0))
        Rrp = Matrix.Translation(e) @ Rrp @ Matrix.Translation(-e)
    M = Matrix.Translation(V(loc_mm)) @ Matrix.Rotation(R(yaw), 4, 'Z') @ Rrp @ Matrix.Translation((0, 0, LAND_Z * MM))
    if M_extra is not None:
        M = M_extra @ M
    par.matrix_world = M
    bpy.context.view_layer.update()
    if settle_:
        settle(par, 0.00002)
    level_eyes(par)


def level_eyes(par):
    """Counter-rotate the glass about its own axis so the eyes stay level with the horizon."""
    bpy.context.view_layer.update()
    info = SOULS[par.name]
    g, M0 = info['glass'], info['M_gl']
    Mw = par.matrix_world @ M0
    Y = (Mw.to_3x3() @ Vector((0, 1, 0))).normalized()
    Nw = (Mw.to_3x3() @ Vector((0, 0, 1))).normalized()
    Up = Vector((0, 0, 1))
    U = Up - Up.dot(Nw) * Nw
    if U.length < 1e-6:
        return 0.0
    U.normalize()
    psi = math.atan2(Y.cross(U).dot(Nw), Y.dot(U))
    g.matrix_basis = M0 @ Matrix.Rotation(psi, 4, 'Z')
    return math.degrees(psi)


def glass_world(par):
    bpy.context.view_layer.update()
    c = par.matrix_world @ V(G_MM)
    n = (par.matrix_world.to_3x3() @ Vector(N_FACE)).normalized()
    return c, n


def eye_point(par):
    bpy.context.view_layer.update()
    return par.matrix_world @ V(G_MM + np.array([0, 0.3, -2.3]))


# ==========================================================================================
# OU capsule (brief §3)
OU_NU = 256


def ou_theta_z(th):
    """Profile of the super-revolution: th in [TH_MIN, pi/2] -> (z, f) with w = 38.5 f, d = 21 f."""
    th = np.asarray(th, float)
    lo = th < 0
    s = np.abs(np.sin(th))
    c = np.abs(np.cos(th))
    z = np.where(lo, 32.0 - 36.0 * s ** (2 / 3.5), 32.0 + 56.0 * s ** (2 / 2.7))
    f = np.where(lo, c ** (2 / 3.5), c ** (2 / 2.7))
    return z, f


TH_MIN = -math.asin((32.0 / 36.0) ** (3.5 / 2))


def ou_point(t, th, off=0.0):
    """Outer surface (off = 0) or a horizontal inward offset surface, column angle t (front = -pi/2)."""
    z, f = ou_theta_z(th)
    w = np.maximum(38.5 * f - off, 0.0)
    d = np.maximum(21.0 * f - off, 0.0)
    C = np.sign(np.cos(t)) * np.abs(np.cos(t)) ** (2 / 2.3)
    S = np.sign(np.sin(t)) * np.abs(np.sin(t)) ** (2 / 2.3)
    return np.stack(np.broadcast_arrays(w * C, 1.0 + d * S, z), -1)


def z_part(y):
    return 18.0 + (y + 21.0) * 30.0 / 43.0


PART_N = np.array([0.0, -30.0 / 43.0, 1.0]) / math.hypot(30.0 / 43.0, 1.0)


def th_cut(t, off=0.0):
    a, b = TH_MIN, math.pi / 2 - 1e-4
    for _ in range(60):
        m = 0.5 * (a + b)
        p = ou_point(t, m, off)
        if p[2] - z_part(p[1]) < 0:
            a = m
        else:
            b = m
    return 0.5 * (a + b)


def ou_surfaces(off=0.0, n_cup=90, n_lid=110, n_base=10):
    """Rows (bottom -> rim) of the cup and (rim -> top) of the lid for the outline offset `off`."""
    ts = np.linspace(-math.pi / 2, 3 * math.pi / 2, OU_NU, endpoint=False)
    cut = np.array([th_cut(t, off) for t in ts])
    cup = np.zeros((n_cup, OU_NU, 3))
    lid = np.zeros((n_lid, OU_NU, 3))
    for j, t in enumerate(ts):
        u = np.linspace(0, 1, n_cup)
        th = TH_MIN + (cut[j] - TH_MIN) * u
        cup[:, j] = ou_point(t, th, off)
        u = np.linspace(0, 1, n_lid)
        th = cut[j] + (math.pi / 2 - 1e-3 - cut[j]) * (1 - (1 - u) ** 1.15)
        lid[:, j] = ou_point(t, th, off)
    base = np.zeros((n_base, OU_NU, 3))
    for k, f in enumerate(np.linspace(0.05, 1.0, n_base)):
        base[k] = cup[0] * np.array([f, 1, 1]) + np.array([0, 0, 0])
        base[k, :, 1] = 1.0 + (cup[0, :, 1] - 1.0) * f
        base[k, :, 0] = cup[0, :, 0] * f
        base[k, :, 2] = 0.0
    return ts, cut, cup, lid, base


def ou_meshes(tag):
    """Cup (pearl, 2.2 wall) and lid (frosted, 2.2 wall) as solidified closed meshes, cached."""
    path_c = os.path.join(CACHE, 'ou_cup_v5.npz')
    path_l = os.path.join(CACHE, 'ou_lid_v5.npz')
    if os.path.exists(path_c) and os.path.exists(path_l):
        cup, rc = load_mesh_cache(path_c, tag + '_cup')
        lid, rl = load_mesh_cache(path_l, tag + '_lid')
        return cup, rc, lid, rl
    ts, cut, cupr, lidr, base = ou_surfaces()
    rows = np.concatenate([base, cupr[1:]], 0)
    Rn = rows.shape[0]
    verts = np.vstack([rows.reshape(-1, 3), [[0, 1.0, 0]]])
    cup = build_mesh(tag + '_cup', verts, grid_quads(Rn, OU_NU), fan(Rn * OU_NU, 0, OU_NU, top=False))
    orient_outward(cup, (0, 1, 20))
    Rl = lidr.shape[0]
    verts = np.vstack([lidr.reshape(-1, 3), [[0, 1.0, 88.0]]])
    lid = build_mesh(tag + '_lid', verts, grid_quads(Rl, OU_NU), fan(Rl * OU_NU, (Rl - 1) * OU_NU, OU_NU, top=True))
    orient_outward(lid, (0, 1, 50))
    for ob, roles in ((cup, ('cup_out', 'cup_in', 'cup_rim')), (lid, ('lid_out', 'lid_in', 'lid_rim'))):
        for r in roles:
            ob.data.materials.append(bpy.data.materials.new('ROLE_' + r))
        s = ob.modifiers.new('solid', 'SOLIDIFY')
        s.thickness = 2.2 * MM
        s.offset = -1.0
        s.use_even_offset = True
        s.use_quality_normals = True
        s.use_rim = True
        s.material_offset = 1
        s.material_offset_rim = 2
        apply_modifiers(ob)
    # hinge notch at the back (the recessed loop bar lives in it) + USB-C opening + recovery pinhole
    cm = bpy.data.materials.new('ROLE_gap')
    for ob in (cup, lid):
        n1 = rounded_box('notch', 30 * MM, 12 * MM, 6.2 * MM, 1.2 * MM, 3)
        n1.location = (0, 26.0 * MM, 48.3 * MM)
        assign(n1, cm)
        cutters = [n1]
        if ob is cup:
            u = rounded_box('usbc', 9.0 * MM, 12 * MM, 3.2 * MM, 1.5 * MM, 4)
            u.location = (0, 20.0 * MM, 8.0 * MM)
            assign(u, cm)
            ph = revolve('pin', [(0, -8), (0.5, -8), (0.5, 8), (0, 8)], seg=16, axis='y')
            ph.location = (8.0 * MM, 20.0 * MM, 8.0 * MM)
            assign(ph, cm)
            cutters += [u, ph]
        bpy.context.view_layer.update()
        for c in cutters:
            c.data.transform(c.matrix_world)
            c.matrix_world = Matrix.Identity(4)
            for m in c.modifiers:
                pass
            apply_modifiers(c)
        boolean(ob, cutters)
    for ob, path in ((cup, path_c), (lid, path_l)):
        roles = [m.name.replace('ROLE_', '').split('.')[0] for m in ob.data.materials]
        save_mesh_cache(path, ob, roles)
    cup_roles = [m.name.replace('ROLE_', '').split('.')[0] for m in cup.data.materials]
    lid_roles = [m.name.replace('ROLE_', '').split('.')[0] for m in lid.data.materials]
    return cup, cup_roles, lid, lid_roles


M_POSE_OU = (Matrix.Translation((0, -2.0 * MM, 9.0 * MM)) @ Matrix.Rotation(R(-6.0), 4, 'X'))


def _to_soul(p):
    """OU coords (mm, (...,3)) -> SOUL frame of the seated pose."""
    Mi = np.array(M_POSE_OU.inverted())
    q = np.asarray(p, float) * MM
    q = q @ Mi[:3, :3].T + Mi[:3, 3]
    return q / MM


def _to_ou(p):
    M = np.array(M_POSE_OU)
    q = np.asarray(p, float) * MM
    q = q @ M[:3, :3].T + M[:3, 3]
    return q / MM


EO = (SG.EA + 0.5, SG.EB + 0.5, SG.EC + 0.5)


def _eoff_level(p_soul):
    return np.sqrt((p_soul[..., 0] / EO[0]) ** 2 + (p_soul[..., 1] / EO[1]) ** 2 +
                   ((p_soul[..., 2] - SG.EZ) / EO[2]) ** 2) - 1.0


def liner_mesh(tag):
    """Analytic liner: 2 mm lip at the rim -> wall (inset 4.2) -> socket (E + 0.5 in the seated pose) -> floor z 9."""
    ts = np.linspace(-math.pi / 2, 3 * math.pi / 2, OU_NU, endpoint=False)
    n_wall, n_bowl, n_floor = 26, 30, 8
    rows = []
    lip_o, lip_i = [], []
    walls = np.zeros((n_wall, OU_NU, 3))
    bowls = np.zeros((n_bowl, OU_NU, 3))
    for j, t in enumerate(ts):
        tco = th_cut(t, 2.05)
        tci = th_cut(t, 4.2)
        po = ou_point(t, tco, 2.05) - PART_N * 0.05
        pi_ = ou_point(t, tci, 4.2) - PART_N * 0.05
        lip_o.append(po)
        lip_i.append(pi_)
        # walk down the inset wall until it meets the socket's lower surface (or z 9)
        ths = np.linspace(tci, TH_MIN, 600)
        P = ou_point(t, ths, 4.2)
        Ps = _to_soul(P)
        below = (Ps[:, 2] < SG.EZ) & (_eoff_level(Ps) > 0)
        k = np.argmax(below | (P[:, 2] < 9.0))
        thm = ths[max(k, 1)]
        walls[:, j] = ou_point(t, np.linspace(tci, thm, n_wall), 4.2)
        M = _to_soul(walls[-1, j])
        q = np.array([M[0] / EO[0], M[1] / EO[1], (M[2] - SG.EZ) / EO[2]])
        q /= np.linalg.norm(q)
        phi = math.atan2(q[1], q[0])
        th0 = math.acos(np.clip(-q[2], -1, 1))
        thb = np.linspace(th0, 0.0, 400)
        qq = np.stack([np.sin(thb) * math.cos(phi), np.sin(thb) * math.sin(phi), -np.cos(thb)], 1)
        pe = np.stack([qq[:, 0] * EO[0], qq[:, 1] * EO[1], qq[:, 2] * EO[2] + SG.EZ], 1)
        po_ = _to_ou(pe)
        kf = np.argmax(po_[:, 2] <= 9.0)
        kf = kf if kf > 0 else len(thb) - 1
        thf = thb[kf]
        thb2 = np.linspace(th0, thf, n_bowl)
        qq = np.stack([np.sin(thb2) * math.cos(phi), np.sin(thb2) * math.sin(phi), -np.cos(thb2)], 1)
        pe = np.stack([qq[:, 0] * EO[0], qq[:, 1] * EO[1], qq[:, 2] * EO[2] + SG.EZ], 1)
        bowls[:, j] = _to_ou(pe)
        bowls[-1, j, 2] = 9.0
    lip_o = np.array(lip_o)
    lip_i = np.array(lip_i)
    fc = bowls[-1].mean(0)
    floor = np.array([fc + (bowls[-1] - fc) * f for f in np.linspace(1, 0.06, n_floor)])
    allrows = np.concatenate([lip_o[None], lip_i[None], walls[1:], bowls[1:], floor[1:]], 0)
    Rn = allrows.shape[0]
    verts = np.vstack([allrows.reshape(-1, 3), [fc]])
    quads = grid_quads(Rn, OU_NU)
    i_floor = 2 + (n_wall - 1) + (n_bowl - 1) - 1
    mq = np.repeat(np.where(np.arange(Rn - 1) >= i_floor, 1, 0), OU_NU)
    tris = fan(Rn * OU_NU, (Rn - 1) * OU_NU, OU_NU, top=True)
    ob = build_mesh(tag + '_liner', verts, quads, tris, mq, np.ones(OU_NU, int))
    # normals must face up/inward (toward the cavity): reference point high above the floor
    orient_outward(ob, (0, 0, -60))
    return ob, lip_i


def build_ou(tag, cw='perla', lid_open=True, night=False, strip=None, halo=None, slit=None, soul=None):
    """OU capsule. Origin = centre of its base land on the table (cork foot included)."""
    par = new_par('ou_' + tag)
    dark = cw in ('onix', 'fum')
    body = mat_pearl5('ou_pearl', rough=0.22) if cw in ('perla', 'lapis') else mat_onyx('ou_onyx')
    # liner = the colourway accent (Perla: ember) as a satin finish: a full 0.10 coat washes it to salmon under
    # the studio key (reads as a pastel)
    liner_m = {'perla': mat_solid_sole('liner_ember', '#D8572A', rough=0.55, coat_r=0.35, engrave=False, coat_w=0.12,
                                       spec=0.3),
               'onix': mat_solid_sole('liner_cream', '#FFF0C8', engrave=False),
               'lapis': mat_lapis('liner_lapis'),
               'chihlimbar': mat_amber('liner_amber'),
               'fum': mat_solid_sole('liner_smoke', '#6E6E74', engrave=False)}[cw]
    lo = mat_ou_lid('ou_lid_out', True, dark, night)
    li = mat_ou_lid('ou_lid_in', False, dark, night)
    gd = gap_dark()
    cup, rc, lid, rl = ou_meshes(tag)
    for ob, roles in ((cup, rc), (lid, rl)):
        for i, r in enumerate(roles):
            ob.data.materials[i] = {'cup_out': body, 'cup_in': body, 'cup_rim': body, 'lid_out': lo, 'lid_in': li,
                                    'lid_rim': li, 'gap': gd}[r]
        set_auto_smooth(ob, 45)
    obs = [cup]
    lin, lip_i = liner_mesh(tag)
    lin.data.materials.append(liner_m)
    lin.data.materials.append(mat_simple('pom_floor', '#EDEAE4', 0.35))
    obs.append(lin)
    # hinge: lid on an empty at the axis
    hinge = new_par(tag + '_hinge')
    hinge.location = (0, 20.5 * MM, 48.3 * MM)
    lid.parent = hinge
    lid.matrix_parent_inverse = Matrix.Translation((0, -20.5 * MM, -48.3 * MM))
    if not lid_open:
        lid.location = Vector(PART_N * 0.6 * MM)
    hinge.rotation_euler = (R(-100.0) if lid_open else 0.0, 0, 0)
    obs.append(hinge)
    steel = mat_metal('ou_steel', srgb('#C9C7C3')[:3], 0.25, 0.5, 'X')
    for x0, ln, rr in ((-10.0, 8.0, 2.0), (10.0, 8.0, 2.0), (0.0, 14.0, 1.0)):
        k = revolve(tag + '_hk', [(0, -ln / 2), (rr - 0.2, -ln / 2), (rr, -ln / 2 + 0.2), (rr, ln / 2 - 0.2),
                                   (rr - 0.2, ln / 2), (0, ln / 2)], seg=48)
        k.data.transform(Matrix.Rotation(R(90), 4, 'Y'))
        k.location = (x0 * MM, 20.5 * MM, 48.3 * MM)
        assign(k, steel)
        obs.append(k)
    # cork foot ring
    ts, cut, cupr, lidr, base = ou_surfaces(n_cup=4, n_lid=4, n_base=2)
    b0 = cupr[0][:, :2]
    ctr = np.array([0.0, 1.0])
    cork = extrude_loops(tag + '_cork', [ctr + (b0 - ctr) * 0.93, ctr + (b0 - ctr) * 0.80], -0.5, 0.0)
    assign(cork, mat_simple('cork', '#A8845E', 0.9))
    obs.append(cork)
    # lights: rear-rim strip (under the lip, aimed at the lid interior), base slit, halo band
    # emission strengths: the brief's values (strip 1.6 x 20 % by day / 4 at night, slit 1.5, halo 6) are relative;
    # at 1 mm scale they need LED_K to light the walnut and the lid as the brief asks (tuned by eye)
    K = TUNE.get('led_k', 40.0) if night else TUNE.get('led_k_day', 6.0)
    s_str = strip if strip is not None else ((4.0 if night else 1.6 * 0.2) * K)
    if night and not lid_open:
        # closed at night: the whole egg is the lantern -- the rear strip fills the closed cavity (SOUL is asleep,
        # its face is inside and unseen) so the frosted lid glows, not just the halo line
        s_str *= TUNE.get('closed_strip_k', 4.0)
    rear = lip_i[lip_i[:, 1] > 1.0 + 3.0]
    rear = rear[np.argsort(np.arctan2(rear[:, 1] - 1.0, rear[:, 0]))]
    cen = np.array([0.0, 1.0])
    pts = []
    for p in rear:
        v = p[:2] - cen
        v = v / np.linalg.norm(v)
        q = np.array([p[0] - v[0] * 0.75, p[1] - v[1] * 0.75, p[2] - 1.1])   # tucked under the liner lip
        pts.append(q)
    if s_str > 0:
        st = curve_obj(tag + '_strip', [tuple(p * MM) for p in pts], 0.5 * MM, res=2)
        assign(st, mat_led(tag + '_led_strip', s_str))
        st.visible_shadow = False
        obs.append(st)
    sl_str = slit if slit is not None else ((1.5 * K) if night else 0.0)
    if sl_str > 0:
        # 1 x 40 mm slit on the front of the base at z ~1: a thin emissive band just proud of the surface
        ts2 = np.linspace(-math.pi / 2 - 0.62, -math.pi / 2 + 0.62, 60)
        thz = th_for_z(1.0)
        bandA = np.array([ou_point(t, thz - 0.012, -0.05) for t in ts2])
        bandB = np.array([ou_point(t, thz + 0.012, -0.05) for t in ts2])
        verts = np.vstack([bandA, bandB])
        n = len(ts2)
        quads = np.array([[i, i + 1, n + i + 1, n + i] for i in range(n - 1)])
        sl = build_mesh(tag + '_slit', verts, quads)
        assign(sl, mat_led(tag + '_led_slit', sl_str))
        sl.visible_shadow = False
        obs.append(sl)
    if not lid_open:
        h_str = halo if halo is not None else ((6.0 * K) if night else 3.0)
        ts3 = np.linspace(-math.pi / 2, 3 * math.pi / 2, OU_NU + 1)
        ring = []
        for t in ts3:
            tc_ = th_cut(t, 0.9)
            ring.append(ou_point(t, tc_, 0.9))
        ring = np.array(ring)[:-1]
        top = ring + PART_N * 0.55
        bot = ring + PART_N * 0.02
        n = len(ring)
        verts = np.vstack([bot, top])
        quads = np.array([[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)])
        hb = build_mesh(tag + '_halo', verts, quads)
        assign(hb, mat_led(tag + '_led_halo', h_str))
        hb.visible_shadow = False
        obs.append(hb)
    parent_all(par, obs)
    par.location = (0, 0, 0.5 * MM)
    if soul is not None:
        soul.parent = par
        soul.matrix_parent_inverse = Matrix.Identity(4)
        soul.matrix_basis = M_POSE_OU @ Matrix.Translation((0, 0, LAND_Z * MM))
        level_eyes(soul)
    return par


def th_for_z(z):
    a, b = TH_MIN, math.pi / 2
    for _ in range(60):
        m = 0.5 * (a + b)
        if ou_theta_z(m)[0] < z:
            a = m
        else:
            b = m
    return 0.5 * (a + b)


# ==========================================================================================
# lighting (brief §8)
def cam_aed(T, A, E, D_mm, lens, fstop, focus=None, shift=(0, 0)):
    T = Vector(T)
    d = Vector((math.sin(R(A)) * math.cos(R(E)), -math.cos(R(A)) * math.cos(R(E)), math.sin(R(E))))
    cam = camera(T + d * D_mm * MM, T, lens=lens, fstop=fstop, focus=focus, shift=shift)
    cam.data.clip_start = 0.004
    return cam


def day_studio(T, k=1.0, bg=7.5, flank=True, chin=True, sweep_col='#D9CDBE', rot=0.0):
    """The v1 warm studio (brief §8) + the v5 flank strip and chin bounce. rot = rotate the whole rig and the sweep
    about the vertical through T (used for the side and back shots so the sweep stays behind the object)."""
    before = set(bpy.data.objects.keys())
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep(sweep_col)
    studio3(T, k, bg=bg)
    if flank:
        area_light('flank', T + Vector((0.30, 0.30, 0.10)), T, 0.08, 1.2 * k, blackbody_rgb(5000), 'RECTANGLE',
                   size_y=1.0)
    if chin:
        # diffuse only: a glossy 3000 K reflection on the sole would read as an amber contrast band
        area_light('chin', T + Vector((0.0, -0.25, -0.02)), T, 0.3, 0.15 * k, blackbody_rgb(3000), 'RECTANGLE',
                   size_y=0.2, glossy=False)
    if rot:
        bpy.context.view_layer.update()
        Mr = Matrix.Translation((T.x, T.y, 0)) @ Matrix.Rotation(R(rot), 4, 'Z') @ Matrix.Translation((-T.x, -T.y, 0))
        for nm in set(bpy.data.objects.keys()) - before:
            ob = bpy.data.objects[nm]
            ob.matrix_world = Mr @ ob.matrix_world
    POST['exposure'] = -0.35


def glint_strip(par, cam, d=0.72, ang=135.0, width=1.6, dist=0.30, strength=None, name='glint'):
    """ONE clean diagonal glint on the FLAT glass (the brief's screen_highlight angles were tuned for v4's domed
    glass and miss a flat one): a thin emissive strip placed on the mirror rays cam' -> chord, so its reflection
    is a band `width` mm wide along the chord x cos(ang) + y sin(ang) = d * r (glass coords, r = 26 mm).
    Visible to glossy rays only. Band area ~ 4-6 % of the glass (brief: <= 12 %)."""
    bpy.context.view_layer.update()
    c, n = glass_world(par)
    info = SOULS[par.name]
    Mw = par.matrix_world @ info['M_gl']
    ex = (Mw.to_3x3() @ Vector((1, 0, 0))).normalized()
    ey = (Mw.to_3x3() @ Vector((0, 1, 0))).normalized()
    # keep the band in screen terms: re-level the axes (the glass itself is counter-rotated)
    up = Vector((0, 0, 1)) - Vector((0, 0, 1)).dot(n) * n
    if up.length > 1e-6:
        ey = up.normalized()
        ex = ey.cross(n).normalized()
    camp = Vector(cam.location)
    cm = camp - 2 * (camp - c).dot(n) * n          # mirror image of the camera
    r = 26.0 * MM
    a = R(ang)
    nrm2 = math.cos(a) * ex + math.sin(a) * ey
    tan2 = -math.sin(a) * ex + math.cos(a) * ey
    half = math.sqrt(max(1 - d * d, 0.0)) * r * 1.25
    P0 = c + nrm2 * d * r
    quad = []
    for sgn_t, sgn_w in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        P = P0 + tan2 * half * sgn_t + nrm2 * (width * MM / 2) * sgn_w
        v = (P - cm).normalized()
        quad.append(P + v * dist)
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(q) for q in quad], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if strength is None:
        strength = TUNE.get('glint', 22.0)
    # soft ends along the band: emission x gradient
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes['Principled BSDF'])
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = (1.0, 0.985, 0.96, 1)
    e.inputs['Strength'].default_value = strength
    nt.links.new(e.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    me.materials.append(m)
    for attr in ('visible_camera', 'visible_diffuse', 'visible_shadow', 'visible_transmission', 'visible_volume_scatter'):
        setattr(ob, attr, False)
    # light linking: the strip reaches only its own glass (neighbours and bodies never mirror it)
    try:
        coll = bpy.data.collections.new('recv_' + name)
        coll.objects.link(info['glass'])
        ob.light_linking.receiver_collection = coll
    except Exception as ex:
        print('  (light linking unavailable: %s)' % ex)
    return ob


def mirror_card(par, cam, dist=0.40, size=None):
    """Glossy-only black card exactly where the flat glass mirrors the camera's view (keeps the glass L* < 5 when
    the reflection would otherwise see a light, e.g. a face-up SOUL in the hand)."""
    bpy.context.view_layer.update()
    c, n = glass_world(par)
    v = (c - Vector(cam.location)).normalized()
    Rv = (v - 2 * v.dot(n) * n).normalized()
    if Rv.z < -0.05:
        # the glass mirrors the table (camera high above): a glossy-only black card on the floor at the hit point
        t = (c.z - 0.0005) / -Rv.z
        hit = c + Rv * t
        dc = (c - Vector(cam.location)).length
        w = 0.052 * (1 + t / dc) * 1.5
        ob = glossy_card((hit.x, hit.y, 0.0005), (w, w / max(abs(Rv.z), 0.3)), (0, 0, math.atan2(-Rv.x, Rv.y)))
        return ob
    size = size or TUNE.get('mcard', 0.6)
    ob = glossy_card(tuple(c + Rv * dist), (size, size))
    ob.rotation_euler = Rv.to_track_quat('Z', 'Y').to_euler()
    return ob


def black_glass(cam, T, par_list, glint=True, card=True, **kw):
    protect_screens(cam, T, 1.6, -0.012)
    POST['bloom'] = 0.03
    for par in par_list:
        if card:
            mirror_card(par, cam)
        if glint:
            glint_strip(par, cam, **kw)


def walnut_top(size=(0.9, 0.6), loc=(0, 0.1)):
    top = rounded_box('walnut', size[0], size[1], 0.03, 0.004, 4)
    top.location = (loc[0], loc[1], -0.015)
    assign(top, mat_wood('walnut', srgb('#3B2A20'), srgb('#24170F'), 0.35, 4.0))
    return top


def night_room(window_power=None):
    window_power = TUNE.get('win', 6.0) if window_power is None else window_power
    world_color((0.02, 0.025, 0.035), 0.004)
    walnut_top((1.2, 0.8), (0, 0.15))
    wall = plane('wall', (4, 2), (0, 0.42, 0.8), (R(90), 0, 0), mat_diffuse('wall_n', srgb('#3A342E'), 0.9, 0.1))
    # the window (1.0 x 1.5 m, 6500 K) sits behind-right; placed in front of the room wall so it can reach the OU
    area_light('window', (1.05, 0.36, 0.75), (0, 0, 0.05), 1.0, window_power, blackbody_rgb(6500), 'RECTANGLE',
               size_y=1.5)
    POST['exposure'] = 0.4
    return wall


# ==========================================================================================
# COCON sleeve, box, carton, cards (brief §3b)
def grid_normals(rows):
    du = np.roll(rows, -1, 1) - np.roll(rows, 1, 1)
    dv = np.zeros_like(rows)
    dv[1:-1] = rows[2:] - rows[:-2]
    dv[0] = rows[1] - rows[0]
    dv[-1] = rows[-1] - rows[-2]
    n = np.cross(du, dv)
    ln = np.linalg.norm(n, axis=-1, keepdims=True)
    n = n / np.maximum(ln, 1e-9)
    c = rows - np.array([0, 0, 35.0])
    if np.mean(np.einsum('ijk,ijk->ij', n, c)) < 0:
        n = -n
    return n


def half_space_box(name, p0_mm, normal, size=0.4):
    """Big box occupying the half-space on the +normal side of the plane through p0."""
    ob = rounded_box(name, size, size, size, 0.0001, 1)
    n = Vector(normal).normalized()
    ob.matrix_world = Matrix.Translation(V(p0_mm) + n * (size / 2)) @ n.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    bpy.context.view_layer.update()
    apply_modifiers(ob)
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)
    return ob


COC_CUT = ((0, -8.0, 69.0), (0, 8.0, 72.5))      # pouch mouth plane (front low, back high), SOUL coords


def _plane_from(p0, p1):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    d = p1 - p0
    n = np.cross(np.array([1.0, 0, 0]), d)
    n /= np.linalg.norm(n)
    if n[2] < 0:
        n = -n
    return p0, n


def shell_between(name, outer, inner):
    """Closed hollow shell from two closed row-grids (outer and inner surfaces, same topology, poles at both ends)."""
    Rn, N = outer.shape[:2]
    parts_v, quads, tris = [], [], []
    off = 0
    for k, (rows, flip) in enumerate(((outer, False), (inner, True))):
        v = np.vstack([rows.reshape(-1, 3), [rows[0].mean(0)], [rows[-1].mean(0)]])
        q = grid_quads(Rn, N, off)
        t = np.vstack([fan(off + Rn * N, off, N, top=False), fan(off + Rn * N + 1, off + (Rn - 1) * N, N, top=True)])
        if flip:
            q = q[:, ::-1]
            t = t[:, ::-1]
        parts_v.append(v)
        quads.append(q)
        tris.append(t)
        off += len(v)
    ob = build_mesh(name, np.vstack(parts_v), np.vstack(quads), np.vstack(tris))
    # outer part must face outward
    me = ob.data
    n = np.zeros(len(me.polygons) * 3)
    c = np.zeros(len(me.polygons) * 3)
    me.polygons.foreach_get('normal', n)
    me.polygons.foreach_get('center', c)
    n = n.reshape(-1, 3)[:len(quads[0])]
    c = c.reshape(-1, 3)[:len(quads[0])] - np.array([0, 0, 35 * MM])
    if np.sum(np.einsum('ij,ij->i', n, c)) < 0:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
    return ob


def build_cocon(tag, open_=False, lift=35.0, soul=None):
    """COCON knit sleeve. Pouch = body offset 2.25 (1.75 knit wall, 0.5 fit), mouth cut by a tilted plane; flap = 2 mm
    sheet over the crown ending at z ~68 on the front; woven loop hanging from the top of the back seam."""
    par = new_par('cocon_' + tag)
    knit = mat_knit('knit')
    rows, iA = body_rows()
    sub = rows[::2]
    nrm = grid_normals(sub)
    outer = sub + nrm * 2.25
    inner = sub + nrm * 0.5
    if open_:
        outer = _stretch_mouth(outer, lift, 2.25)
        inner = _stretch_mouth(inner, lift, 0.5)
    p0, npl = _plane_from(*COC_CUT)
    pouch = shell_between(tag + '_pouch', outer, inner)
    cut = half_space_box('cut', p0, npl)
    boolean(pouch, [cut])
    assign(pouch, knit)
    set_auto_smooth(pouch, 50)
    obs = [pouch]

    def off_f(z):
        return 2.25 + 1.9 + 3.2 * SG.smoothstep((z - 58.0) / 16.0)
    fo = sub + nrm * off_f(sub[..., 2])[..., None]
    fi = sub + nrm * (off_f(sub[..., 2]) - 2.0)[..., None]
    fl = shell_between(tag + '_flap', fo, fi)
    q0, nq = _plane_from((0, -8.0, 67.8), (0, 8.0, 70.0))
    cut2 = half_space_box('cut2', q0, -nq)
    boolean(fl, [cut2])
    assign(fl, knit)
    set_auto_smooth(fl, 50)
    hinge_y, hinge_z = 9.0, 71.5
    fpar = new_par(tag + '_flaphinge')
    fpar.location = (0, hinge_y * MM, hinge_z * MM)
    fl.parent = fpar
    fl.matrix_parent_inverse = Matrix.Translation((0, -hinge_y * MM, -hinge_z * MM))
    if open_:
        fpar.rotation_euler = (R(TUNE.get('flap_open', 150.0)), 0, 0)
    obs.append(fpar)
    loop = woven_loop(tag, open_)
    obs.append(loop)
    parent_all(par, obs)
    par['lift'] = lift if open_ else 0.0
    return par


_POLAR = {}


def _soul_polar(ctr_y=-0.8):
    """SOUL's plan radius about (0, ctr_y) as a table over (z, angle)."""
    if 'tab' not in _POLAR:
        zs = np.linspace(0.5, 73.9, 300)
        angs = np.linspace(-math.pi, math.pi, 721)
        tab = np.zeros((len(zs), len(angs)))
        for i, z in enumerate(zs):
            ring = SG.ring(z, 720)
            a = np.arctan2(ring[:, 1] - ctr_y, ring[:, 0])
            r = np.hypot(ring[:, 0], ring[:, 1] - ctr_y)
            o = np.argsort(a)
            tab[i] = np.interp(angs, a[o], r[o], period=2 * math.pi)
        _POLAR['tab'] = (zs, angs, tab)
    return _POLAR['tab']


def _stretch_mouth(surf, lift, off, ctr_y=-0.8):
    """Open pose: the heat-set pouch keeps its shape low down and is stretched around the lifted SOUL near the
    mouth (per vertex: never inside SOUL + off)."""
    zs_t, ang_t, tab = _soul_polar(ctr_y)
    P = surf.reshape(-1, 3).copy()
    z = P[:, 2]
    a = np.arctan2(P[:, 1] - ctr_y, P[:, 0])
    rr = np.hypot(P[:, 0], P[:, 1] - ctr_y)
    zs = z - lift
    ok = zs > 0.6
    iz = np.clip(np.interp(zs, zs_t, np.arange(len(zs_t))), 0, len(zs_t) - 1)
    ia = np.interp(a, ang_t, np.arange(len(ang_t)))
    i0 = np.floor(iz).astype(int)
    i1 = np.minimum(i0 + 1, len(zs_t) - 1)
    fz = iz - i0
    j0 = np.floor(ia).astype(int) % len(ang_t)
    j1 = (j0 + 1) % len(ang_t)
    fa = ia - np.floor(ia)
    need = ((1 - fz) * ((1 - fa) * tab[i0, j0] + fa * tab[i0, j1]) + fz * ((1 - fa) * tab[i1, j0] + fa * tab[i1, j1]))
    need = need + off
    # soft ease-in of the stretch below the belly, plus a hard rule: the knit never passes inside SOUL (+ wall)
    k = SG.smoothstep((z - 30.0) / 22.0)
    new = np.maximum(rr, rr + (need - rr) * k * ok)
    new = np.maximum(new, np.where(ok, need, 0.0))
    P[:, 0] = new * np.cos(a)
    P[:, 1] = ctr_y + new * np.sin(a)
    return P.reshape(surf.shape)


def woven_loop(tag, open_):
    """Woven loop 8 x 45 x 1.2: a ribbon folded in half (two layers, round fold at the bottom), both ends sewn into
    the top of the back seam, hanging as a flat U tab down the back."""
    top = np.array([0.0, 5.2, 74.3])
    L = 45.0
    leg = (L - math.pi * 1.4) / 2.0
    pts = []
    for t in np.linspace(0, leg, 26):                       # outer leg, going down
        pts.append([0.0, 1.4, -t])
    for a in np.linspace(0, math.pi, 14)[1:-1]:             # the fold (R 1.4)
        pts.append([0.0, 1.4 * math.cos(a), -leg - 1.4 * math.sin(a)])
    for t in np.linspace(leg, 0, 26):                       # inner leg, back up
        pts.append([0.0, -1.4, -t])
    pts = np.array(pts)
    rot = Matrix.Rotation(R(24.0), 3, 'X')                  # hangs a little away from the back
    P = np.array([rot @ Vector(p) for p in pts]) + top + np.array([0, 2.2, 0])
    tang = np.gradient(P, axis=0)
    tang /= np.linalg.norm(tang, axis=1, keepdims=True)
    wdir = np.tile(np.array([1.0, 0, 0]), (len(P), 1))
    thk = np.cross(tang, wdir)
    thk /= np.linalg.norm(thk, axis=1, keepdims=True)
    ring = np.stack([P - wdir * 4.0 - thk * 0.6, P + wdir * 4.0 - thk * 0.6, P + wdir * 4.0 + thk * 0.6,
                     P - wdir * 4.0 + thk * 0.6], 1)
    Rn = len(P)
    verts = ring.reshape(-1, 3)
    quads = grid_quads(Rn, 4)
    caps = np.array([[0, 1, 2, 3], [(Rn - 1) * 4 + 3, (Rn - 1) * 4 + 2, (Rn - 1) * 4 + 1, (Rn - 1) * 4]])
    ob = build_mesh(tag + '_loop', verts, np.vstack([quads, caps]), smooth=True)
    orient_outward(ob, P.mean(0))
    bv = ob.modifiers.new('bev', 'BEVEL')
    bv.width = 0.3 * MM
    bv.segments = 2
    m2, nt, p, out = new_mat('knit_loop_w')
    # brief colour #D8572A r 0.8; a touch deeper so the directly lit rough ribbon still reads ember after AgX
    set_in(p, 'Base Color', srgb(TUNE.get('loop_col', '#C24A20') if isinstance(TUNE.get('loop_col', 0), str) else '#C24A20'))
    set_in(p, 'Roughness', 0.8)
    set_in(p, 'Specular IOR Level', 0.3)
    _noise_bump(nt, p, 3000.0, 0.5, 0.0002)
    assign(ob, m2)
    return ob


def build_sleeve(tag, W=118.0, D=78.0, H=150.0, t=1.2):
    """The box sleeve: a cloche open at the bottom (front: foil eyes, spine: SOUL, back: legal block)."""
    par = new_par('sleeve_' + tag)
    front = mat_image('box_front', 'box_front.png', 0.85, 'x', False, 'z', foil_mask=True, colorspace='Non-Color')
    back = mat_image('box_back', 'box_back.png', 0.85, 'x', True, 'z')
    spine = mat_image('box_spine', 'box_spine.png', 0.85, 'y', False, 'z')
    plain = mat_simple('board_cream', '#F1E9DA', 0.85, spec=0.25)
    obs = []
    specs = [('front', (W, t, H), (0, -D / 2 + t / 2, H / 2), front),
             ('back', (W, t, H), (0, D / 2 - t / 2, H / 2), back),
             ('spine', (t, D - 2 * t, H), (W / 2 - t / 2, 0, H / 2), spine),
             ('side', (t, D - 2 * t, H), (-W / 2 + t / 2, 0, H / 2), plain),
             ('top', (W - 2 * t, D - 2 * t, t), (0, 0, H - t / 2), plain)]
    for nm, sz, loc, m in specs:
        b = rounded_box(tag + '_' + nm, sz[0] * MM, sz[1] * MM, sz[2] * MM, 0.3 * MM, 2)
        b.location = V(loc)
        assign(b, m)
        obs.append(b)
    # paper seal "No 00417" on the front, lower right
    seal = rounded_box(tag + '_seal', 30 * MM, 0.15 * MM, 12 * MM, 0.05 * MM, 1)
    seal.location = V((W / 2 - 24, -D / 2 - 0.1, 16))
    assign(seal, mat_image('seal', 'seal.png', 0.8, 'x', False, 'z'))
    obs.append(seal)
    parent_all(par, obs)
    return par


def build_carton(tag):
    """Single-cell moulded-pulp egg carton: superegg of revolution |r/44|^2.5 + |(z-40)/52|^2.5 = 1, cut at z 58,
    1.5 mm wall, 6 mm crimped flange at the rim; a flat foot so it stands. Origin = its foot on the table."""
    zb = -6.0
    prof = []
    for z in np.linspace(zb, 58.0, 70):
        r = 44.0 * (1 - abs((z - 40.0) / 52.0) ** 2.5) ** (1 / 2.5)
        prof.append((r, z))
    r58 = prof[-1][0]
    outer = [(0.0, zb)] + prof
    inner = [(max(r - 1.5, 0.0), z) for r, z in prof[::-1]] + [(0.0, zb + 1.5)]
    rim = [(r58 + 6.0, 58.0), (r58 + 6.0, 59.5), (r58 - 1.5, 59.5)]
    full = outer + rim + inner
    ob = revolve(tag + '_carton', full, seg=160)
    # crimp: radial ripple on the flange + the wall (bumps every 12 deg)
    me = ob.data
    for v in me.vertices:
        x, y, z = v.co
        r = math.hypot(x, y)
        if r < 1e-6:
            continue
        a = math.atan2(y, x)
        k = 0.35 * MM * math.cos(30 * a) if z > 20 * MM else 0.0
        v.co.x += k * x / r
        v.co.y += k * y / r
    ob.location = (0, 0, -zb * MM)
    assign(ob, mat_pulp())
    return ob


def build_card(tag, img, loc_mm, rot_deg):
    c = rounded_box(tag, 70 * MM, 100 * MM, 0.45 * MM, 0.8 * MM, 3)
    c.location = V(loc_mm) + Vector((0, 0, 0.23 * MM))
    c.rotation_euler = (0, 0, R(rot_deg))
    assign(c, mat_image('card_' + tag, img, 0.8, 'x', False, 'y'))
    return c


# hand (copied from soul_v4.py, brief §1)
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


# ==========================================================================================
# shots (brief §9)
def soul_T():
    return Vector((0, -0.002, 0.037))


def shot_hero():
    """1: Perla SOUL upright, yaw -8; OU Perla open at (-95, +120), yaw +20, soft in the background."""
    sc = reset()
    T = Vector((0, -2 * MM, 37 * MM))
    day_studio(T)
    s = build_soul('hero', 'perla', eyes='cream_look')
    pose_soul(s, (0, 0, 0), yaw=-8.0)
    # brief: OU at (-95, +120), yaw +20 -- that is 17 deg outside the frame of the -24 deg camera (the rev. moved
    # the camera to -x); mirrored to (+95, +120), yaw -20 so it stays soft in the background, behind-right
    ou = build_ou('bg', 'perla', lid_open=True, night=False)
    ou.location = V((95, 120, 0.5))
    ou.rotation_euler = (0, 0, R(-20.0))
    cam = cam_aed(T, -24.0, 9.0, 375.0, 100, 8.0, focus=eye_point(s))
    black_glass(cam, T, [s])
    return sc


def shot_front(elev):
    sc = reset()
    T = Vector((0, 0, 37 * MM))
    day_studio(T)
    s = build_soul('front', 'perla', eyes='soul_front')
    pose_soul(s, (0, 0, 0))
    cam = cam_aed(T, 0.0, elev, 590.0, 200, 16.0, focus=eye_point(s))
    black_glass(cam, T, [s])
    POST['soul_front'] = True
    return sc


def shot_check1(sole, elev):
    sc = reset()
    if elev == 0:
        T = Vector((0, 0, 5 * MM))
        tgt_frame = 37.0
    else:
        T = Vector((0, 0, 37 * MM))
        tgt_frame = 37.0
    day_studio(Vector((0, 0, 37 * MM)))
    s = build_soul('chk', 'perla', sole=sole, eyes='soul_front')
    pose_soul(s, (0, 0, 0))
    # true 0 deg: camera at z 5 looking level; the frame is shifted up to hold the whole body (same rays)
    lens = 140.0
    if elev == 0:
        cam = cam_aed(T, 0.0, 0.0, 590.0, lens, 16.0, focus=eye_point(s))
        # vertical shift in units of the larger sensor dimension (portrait: height)
        view_h = 590.0 * 36.0 / lens
        cam.data.shift_y = (tgt_frame - 5.0) / view_h
    else:
        cam = cam_aed(T, 0.0, 9.0, 590.0, lens, 16.0, focus=eye_point(s))
    if elev == 0:
        # at table level the floor is seen at grazing: no floor card, and a matte sweep (a glossy one mirrors the
        # black flag behind the camera and turns the foreground floor black)
        flag(cam, Vector((0, 0, 37 * MM)))
        pm = bpy.data.objects['sweep'].data.materials[0].node_tree.nodes['Principled BSDF']
        set_in(pm, 'Specular IOR Level', 0.0)
        set_in(pm, 'Roughness', 1.0)
        # the near floor seen from 5 mm is outside every studio cone: a diffuse-only fill for the floor alone
        fl = area_light('floorfill', (0, -0.42, 0.45), (0, -0.42, 0.0), 0.9, TUNE.get('floorfill', 6.0),
                        blackbody_rgb(5200), 'RECTANGLE', size_y=0.6, spread=30, glossy=False)
        POST['bloom'] = 0.03
        glint_strip(s, cam)
    else:
        black_glass(cam, Vector((0, 0, 37 * MM)), [s])
    POST['check1'] = dict(sole=sole, elev=elev)
    return sc


def shot_side():
    sc = reset()
    T = Vector((0, 0, 37 * MM))
    day_studio(T, rot=90.0)
    # thin rim strip behind (-x) to separate the silhouette from the sweep
    area_light('rim_x', T + Vector((-0.35, 0.15, 0.05)), T, 0.06, 1.6, blackbody_rgb(5000), 'RECTANGLE', size_y=0.9)
    s = build_soul('side', 'perla', eyes='soul_front')
    pose_soul(s, (0, 0, 0))
    cam = cam_aed(T, 90.0, 0.0, 630.0, 150, 16.0, focus=T)
    protect_screens(cam, T, 1.6, -0.012)
    return sc


def shot_back():
    sc = reset()
    T = Vector((0, 2 * MM, 38 * MM))
    day_studio(T, rot=-150.0, k=TUNE.get('back_k', 0.8))
    s = build_soul('back', 'perla', eyes='soul_front', glass_on=False)
    pose_soul(s, (0, 0, 0))
    cam = cam_aed(T, -150.0, 12.0, 420.0, 100, 11.0, focus=T)
    # one clean highlight line down the dome: a tall strip on the camera's right, visible in glossy only
    d = (Vector(cam.location) - T)
    d.z = 0
    d.normalize()
    side = Vector((d.y, -d.x, 0))
    ang = R(TUNE.get('line_ang', 72.0))
    pos = T + (d * math.cos(ang) + side * math.sin(ang)) * 0.32 + Vector((0, 0, 0.06))
    st = area_light('line', pos, T, 0.018, TUNE.get('line_w', 3.0), blackbody_rgb(5600), 'RECTANGLE', size_y=1.2)
    st.visible_diffuse = False
    for nm in ('top',):
        bpy.data.objects[nm].data.energy *= 0.5
    POST['exposure'] = -0.45
    return sc


def shot_bottom():
    """5: plays dead: rotated -90 about x, settled on its back, the sole facing the camera."""
    sc = reset()
    s = build_soul('bot', 'perla', eyes='cream_down')
    s.matrix_world = Matrix.Rotation(R(-90.0), 4, 'X')
    bpy.context.view_layer.update()
    settle(s, 0.00002)
    level_eyes(s)
    bpy.context.view_layer.update()
    T = s.matrix_world @ Vector((0, 0, 0))
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#D9CDBE')
    studio3(T, 0.8, bg=7.5)
    area_light('rake', T + Vector((-0.30 * math.cos(R(10)), -0.05, 0.30 * math.sin(R(10)))), T, 0.15, 0.8,
               blackbody_rgb(5600))
    cam = cam_aed(T, 0.0, 18.0, 260.0, 100, 8.0, focus=T)
    # a soft reflector behind the camera: the gold pads and the glossy sole mirror it, the engraving stays matte
    d = (Vector(cam.location) - T).normalized()
    area_light('reflector', Vector(cam.location) + d * 0.15 + Vector((0, 0, 0.05)), T, 0.5, TUNE.get('refl', 0.28),
               blackbody_rgb(5600), 'RECTANGLE', size_y=0.35)
    POST['exposure'] = -0.35
    POST['bloom'] = 0.03
    return sc


def shot_ou(closed):
    """6a/6b: walnut bedside at night; OU Perla, SOUL seated at 14 deg; light only from the OU."""
    sc = reset()
    night_room()
    s = build_soul('ou', 'perla', eyes='soul_closed' if closed else 'amber_sleepy', strength=0.8)
    ou = build_ou('night', 'perla', lid_open=not closed, night=True, soul=s)
    ou.location = V((0, 0, 0.5))
    bpy.context.view_layer.update()
    T = Vector((0, 0, 45 * MM))
    foc = eye_point(s)
    cam = cam_aed(T, -28.0, 20.0, 420.0, 50, 2.8, focus=foc)
    POST['exposure'] = 0.4
    return sc


def shot_hand():
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#CDBFAE', wall_y=0.55)
    build_hand_v4('hand', (0.0, 0.0, 0.030), 18.0)
    s = build_soul('hand', 'perla', eyes='cream_down')
    # cradled face-up: rotate -90 about x, then (18, -6, 14); SOUL's centre at (0.003, 0.010, 0.042) m
    ctr = Vector((0, -1.0 * MM, 37.0 * MM))
    Rm = Euler((R(18), R(-6), R(14))).to_matrix().to_4x4() @ Matrix.Rotation(R(-90), 4, 'X')
    loc = Vector((0.003, 0.010, 0.042 + TUNE.get('hand_dz', 0.0) * MM))
    s.matrix_world = Matrix.Translation(loc) @ Rm @ Matrix.Translation(-ctr)
    level_eyes(s)
    T = loc
    cam = camera(T + Vector((0.13, -0.30, 0.15)), T, lens=70, fstop=5.6, focus=eye_point(s))
    flag(cam, T)
    mirror_card(s, cam)
    glint_strip(s, cam)
    POST['bloom'] = 0.03
    studio3(T, 1.1, bg=7.0)
    POST['exposure'] = -0.35
    return sc


FAMILY = [('onix', 'soul_smug', dict(roll=-5.0)), ('chihlimbar', 'soul_left', dict(pitch=6.0)),
          ('perla', 'soul_front', dict()), ('lapis', 'cream_look', dict(roll=6.0)),
          ('fum', 'soul_wide', dict(roll=-3.0))]


def shot_family():
    sc = reset()
    T = Vector((0, 2 * MM, 36 * MM))
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#D9CDBE')
    pitch = 63.0 + 14.0
    Rarc = 400.0
    pars = []
    for i, (cw, eyes, pose) in enumerate(FAMILY):
        x = (i - 2) * pitch
        y = Rarc - math.sqrt(Rarc * Rarc - x * x)
        if cw == 'perla':
            y -= 10.0
        s = build_soul('f%d' % i, cw, eyes=eyes)
        pose_soul(s, (x, y, 0), yaw=-math.degrees(math.asin(x / Rarc)) * 0.6, **pose)
        pars.append(s)
    lens = TUNE.get('fam_lens', 58.0)
    cam = camera(Vector((0, -0.66, 0.11)), T, lens=lens, fstop=11.0, focus=Vector((0, -0.004, 0.035)))
    protect_screens(cam, T, 1.8, -0.06)
    for sp in pars:
        glint_strip(sp, cam, name='glint_' + sp.name)
    POST['bloom'] = 0.03
    studio(T, 1.6)
    POST['exposure'] = -0.35
    return sc


def shot_cocon():
    """9: COCON closed and standing (loop hanging) + one open with SOUL half out (lifted 35 mm)."""
    sc = reset()
    T = Vector((0, 0, TUNE.get('coc_Tz', 50.0) * MM))
    day_studio(T)
    closed = build_cocon('closed', open_=False)
    closed.location = V((-44, 16, 2.25))
    closed.rotation_euler = (0, 0, R(TUNE.get('coc_yaw', 128.0)))
    s = build_soul('coc', 'perla', eyes='soul_wide')
    op = build_cocon('open', open_=True, lift=35.0)
    op.location = V((38, -8, 2.25))
    op.rotation_euler = (0, 0, R(-16))
    bpy.context.view_layer.update()
    for ob in (closed, op):
        settle(ob, 0.00002)
    bpy.context.view_layer.update()
    s.matrix_world = op.matrix_world @ Matrix.Translation(V((0, 0, 35.0 + LAND_Z)))
    level_eyes(s)
    cam = cam_aed(T, -20.0, 12.0, TUNE.get('coc_D', 540.0), 100, 8.0, focus=eye_point(s))
    black_glass(cam, T, [s])
    return sc


def shot_unbox():
    """10a: overhead unboxing: sleeve lifted beside, pulp carton with the closed OU, a card, an opened OU with SOUL."""
    sc = reset()
    T = Vector((0, 0, 30 * MM))
    world_color((0.95, 0.92, 0.88), 0.035)
    sweep('#D9CDBE', wall_y=0.9)
    studio3(T, 1.0, bg=7.0)
    area_light('soft_top', T + Vector((-0.12, 0.05, 0.7)), T, 1.2, 2.4, blackbody_rgb(5200))
    sl = build_sleeve('u')
    sl.location = V((-62, 150, 0))
    sl.rotation_euler = (0, 0, R(12))
    ct = build_carton('u')
    ct.location = V((-60, 38, 0))
    s1 = build_soul('ub1', 'perla', eyes='soul_closed', glass_on=False)
    ou1 = build_ou('closed', 'perla', lid_open=False, night=False, halo=0.0, soul=s1)
    ou1.location = V((-60, 38, 9.5))
    ou1.rotation_euler = (0, 0, R(8))
    s = build_soul('ub', 'perla', eyes='soul_wide')
    ou2 = build_ou('open', 'perla', lid_open=True, night=False, soul=s)
    ou2.location = V((48, -18, 0.5))
    ou2.rotation_euler = (0, 0, R(-12))
    build_card('card1', 'card_nudge.png', (40, -118, 0), -8)
    build_card('card2', 'card_ritual.png', (-58, -86, 0), 13)
    bpy.context.view_layer.update()
    level_eyes(s)
    cam = cam_aed(T, 0.0, 62.0, 520.0, 50, 5.6, focus=eye_point(s))
    flag(cam, T)
    mirror_card(s, cam)
    glint_strip(s, cam)
    POST['exposure'] = -0.3
    POST['bloom'] = 0.03
    return sc


def shot_boxback():
    sc = reset()
    world_color((0.95, 0.92, 0.88), 0.03)
    sweep('#D9CDBE')
    sl = build_sleeve('b')
    sl.rotation_euler = (0, 0, R(180))
    T = Vector((0, -0.039, TUNE.get('bb_z', 56.0) * MM))
    studio3(T, 1.0, bg=7.0)
    # straight on, 0 / 0 / 400; a 95 mm lens so the 6 pt legal block is legible (x-height ~ 11 px)
    cam = cam_aed(T, 0.0, 0.0, 400.0, TUNE.get('bb_lens', 95.0), 11.0, focus=T)
    POST['exposure'] = -0.55
    return sc


def shot_ou_day():
    """F (optional): the OU open on a walnut desk by day, SOUL seated at 14 deg, a laptop edge soft behind."""
    sc = reset()
    desk_scene('walnut')
    laptop((0.16, 0.20, 0.006), -18)
    s = build_soul('od', 'perla', eyes='soul_left')
    ou = build_ou('day', 'perla', lid_open=True, night=False, soul=s)
    ou.location = V((0, 0, 0.5))
    bpy.context.view_layer.update()
    level_eyes(s)
    T = Vector((0, 0, 45 * MM))
    cam = cam_aed(T, TUNE.get('oud_A', -30.0), TUNE.get('oud_E', 18.0), TUNE.get('oud_D', 450.0),
                  TUNE.get('oud_lens', 70.0), 4.0, focus=eye_point(s))
    area_light('window', (-0.9, -0.2, 0.7), T, 1.2, 38, blackbody_rgb(6500), 'RECTANGLE', 0.8)
    area_light('fill', (0.5, -0.6, 0.3), T, 1.0, 4, blackbody_rgb(4000), glossy=False)
    area_light('rim', (0.1, 0.5, 0.4), T, 0.4, 6, blackbody_rgb(5000))
    black_glass(cam, T, [s])
    POST['exposure'] = -0.2
    return sc


def shot_ou_inspect():
    """debug: the OU alone in the day studio (TUNE: insp_open, insp_A, insp_E, insp_D, insp_night)."""
    sc = reset()
    T = Vector((0, 0, 44 * MM))
    night = TUNE.get('insp_night', 0) > 0
    if night:
        night_room()
    else:
        day_studio(T)
    s = build_soul('ins', 'perla', eyes='soul_front') if TUNE.get('insp_soul', 1) > 0 else None
    ou = build_ou('ins', 'perla', lid_open=TUNE.get('insp_open', 1) > 0, night=night, soul=s)
    ou.location = V((0, 0, 0.5))
    cam = cam_aed(T, TUNE.get('insp_A', -30.0), TUNE.get('insp_E', 15.0), TUNE.get('insp_D', 480.0), 70, 11.0)
    if s is not None:
        black_glass(cam, T, [s])
    return sc


def shot_test():
    """Quick geometry check: SOUL front on the sweep."""
    return shot_front(0.0)


SHOTS = {
    'hero': (shot_hero, 2000, 2000, 128),
    'front_00': (lambda: shot_front(0.0), 1600, 1600, 128),
    'front_15': (lambda: shot_front(15.0), 1600, 1600, 128),
    'check1_pearl_0': (lambda: shot_check1('pearl', 0), 600, 1200, 96),
    'check1_ember_0': (lambda: shot_check1('ember', 0), 600, 1200, 96),
    'check1_pearl_9': (lambda: shot_check1('pearl', 9), 600, 1200, 96),
    'check1_ember_9': (lambda: shot_check1('ember', 9), 600, 1200, 96),
    'side': (shot_side, 1600, 1200, 128),
    'back': (shot_back, 1600, 1200, 128),
    'bottom': (shot_bottom, 1600, 1200, 128),
    'ou_night': (lambda: shot_ou(False), 1600, 2000, 192),
    'ou_closed': (lambda: shot_ou(True), 1600, 2000, 192),
    'hand': (shot_hand, 1600, 1200, 128),
    'family': (shot_family, 2000, 1125, 128),
    'cocon': (shot_cocon, 1600, 1200, 128),
    'unbox': (shot_unbox, 1600, 2000, 128),
    'boxback': (shot_boxback, 1600, 1200, 96),
    'ou_day': (shot_ou_day, 1600, 1200, 128),
    'ou_inspect': (shot_ou_inspect, 1600, 1200, 64),
    'test': (shot_test, 1600, 1600, 64),
}

main()
