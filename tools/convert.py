"""Blender (bpy) converter for MOAI VJ assets.
static : -> <out>/<name>.obj + <name>.mtl + <name>.jpg  (one mesh, one texture, height/size normalised to 2, centred, Y up)
anim   : -> <out>/<name>.fbx (textures embedded, animation baked, normalised) + <out>/<name>.json (duration, fps, seam)
"""
import bpy, sys, os, json, math, glob
from mathutils import Vector, Matrix

args = json.loads(sys.argv[sys.argv.index('--') + 1])
SRC, OUT, NAME, KIND = args['src'], args['out'], args['name'], args['kind']
TEXMAP = args.get('tex', {})          # material name (or '*') -> texture file name
TEXDIR = args.get('texdir', os.path.dirname(SRC))
os.makedirs(OUT, exist_ok=True)
info = {'name': NAME, 'src': os.path.basename(SRC)}

def log(*a): print('[conv]', *a, flush=True)

# ---------------------------------------------------------------- load
bpy.ops.wm.read_factory_settings(use_empty=True)
ext = os.path.splitext(SRC)[1].lower()
if ext == '.fbx': bpy.ops.import_scene.fbx(filepath=SRC, automatic_bone_orientation=True)
elif ext in ('.gltf', '.glb'): bpy.ops.import_scene.gltf(filepath=SRC)
elif ext == '.blend': bpy.ops.wm.open_mainfile(filepath=SRC)
elif ext == '.dae': bpy.ops.wm.collada_import(filepath=SRC)
elif ext in ('.usdz', '.usd', '.usdc'): bpy.ops.wm.usd_import(filepath=SRC)
elif ext == '.obj': bpy.ops.wm.obj_import(filepath=SRC)
sc = bpy.context.scene

for o in list(sc.objects):                         # cameras, lights, probes: not ours
    if o.type in ('CAMERA', 'LIGHT', 'LIGHT_PROBE', 'SPEAKER'):
        bpy.data.objects.remove(o, do_unlink=True)

# ---------------------------------------------------------------- textures
def findtex(fn):
    fn = os.path.basename(fn).lower()
    stem = os.path.splitext(fn)[0]
    hits = [p for p in glob.glob(os.path.join(TEXDIR, '**', '*'), recursive=True) if os.path.basename(p).lower() == fn]
    if not hits:   # same name, other extension (.jpg vs .jpeg)
        hits = [p for p in glob.glob(os.path.join(TEXDIR, '**', '*'), recursive=True)
                if os.path.splitext(os.path.basename(p))[0].lower() == stem and p.lower().endswith(('.png', '.jpg', '.jpeg'))]
    return hits[0] if hits else None

for img in bpy.data.images:                         # relink missing image files by name
    if img.packed_file is None and img.filepath and not os.path.exists(bpy.path.abspath(img.filepath)):
        p = findtex(img.filepath)
        if p: img.filepath = p; img.reload(); log('relinked', os.path.basename(p))

def basecolor(mat):
    if not mat or not mat.node_tree: return None
    b = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if not b: return None
    l = b.inputs['Base Color'].links
    if l and l[0].from_node.type == 'TEX_IMAGE' and l[0].from_node.image: return l[0].from_node.image
    return None

def attach(mat, path):
    mat.use_nodes = True
    nt = mat.node_tree
    b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if b is None:
        b = nt.nodes.new('ShaderNodeBsdfPrincipled')
        outn = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None) or nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(b.outputs[0], outn.inputs[0])
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(path, check_existing=True)
    nt.links.new(t.outputs['Color'], b.inputs['Base Color'])

for m in bpy.data.materials:
    want = TEXMAP.get(m.name) or TEXMAP.get('*')
    if want and basecolor(m) is None:
        p = findtex(want)
        if p: attach(m, p); log('texture', m.name, '<-', os.path.basename(p))
        else: log('MISSING texture', want)

# ---------------------------------------------------------------- bounds (evaluated, at a given frame)
def world_bounds(frame=None):
    if frame is not None: sc.frame_set(int(frame))
    dg = bpy.context.evaluated_depsgraph_get()
    mn = Vector((1e18,) * 3); mx = Vector((-1e18,) * 3)
    for o in sc.objects:
        if o.type != 'MESH' or o.hide_render: continue
        oe = o.evaluated_get(dg); me = oe.to_mesh()
        mw = oe.matrix_world
        for v in me.vertices:
            p = mw @ v.co
            mn = Vector((min(mn[i], p[i]) for i in range(3))); mx = Vector((max(mx[i], p[i]) for i in range(3)))
        oe.to_mesh_clear()
    return mn, mx

# ---------------------------------------------------------------- per-asset repairs
if args.get('fix_normals'):
    # some files carry broken custom normals (TouchDesigner shows the model flat white / black): rebuild them
    for o in sc.objects:
        if o.type != 'MESH': continue
        me = o.data
        if me.has_custom_normals:
            bpy.context.view_layer.objects.active = o
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
        for p in me.polygons: p.use_smooth = False                # hard-edged pieces: flat faces light correctly
        me.update()
    log('normals rebuilt')

if args.get('ferris_spin'):
    # the file's "animation" never moves: build one. Wheel turns once in 15 s around its axle,
    # every cabin turns back by the same amount so it hangs level. Plain object hierarchy, no bones.
    arm = next(o for o in sc.objects if o.type == 'ARMATURE')
    hub = arm.data.bones[args['ferris_spin']['hub']]
    axle = arm.matrix_world @ hub.head_local
    wm = {o.name: o.matrix_world.copy() for o in sc.objects}
    wheel = bpy.data.objects.new('Wheel', None); sc.collection.objects.link(wheel); wheel.location = axle
    seats = {}
    for b in arm.data.bones:
        if b.parent and b.parent.name == hub.name:
            e = bpy.data.objects.new('Seat_' + b.name, None); sc.collection.objects.link(e)
            e.location = arm.matrix_world @ b.head_local; seats[b.name] = e
    bpy.context.view_layer.update()
    # a cabin swings from the top of the cabin itself, not from the bone (which sits near the hub)
    for bn, e in seats.items():
        cab = [o for o in sc.objects if o.type == 'MESH' and o.parent is arm and o.parent_type == 'BONE' and o.parent_bone == bn]
        if cab:
            pts = [cab[0].matrix_world @ Vector(c) for c in cab[0].bound_box]
            e.location = Vector((sum(p.x for p in pts) / 8, sum(p.y for p in pts) / 8, max(p.z for p in pts)))
    bpy.context.view_layer.update()
    for e in seats.values():
        m = e.matrix_world.copy(); e.parent = wheel; e.matrix_world = m
    for o in list(sc.objects):
        if o in (wheel,) or o in seats.values() or o is arm: continue
        if o.parent is arm:
            tgt = None
            if o.parent_type == 'BONE':
                # cabins hang level on their pivots; everything else on a cabin bone (spoke groups) turns with the wheel
                cabin = o.type == 'MESH' and o.parent_bone in seats
                tgt = seats[o.parent_bone] if cabin else wheel
            o.parent = tgt; o.matrix_world = wm[o.name]
    bpy.context.view_layer.update()
    for o in list(sc.objects):
        if o.animation_data: o.animation_data_clear()
    bpy.data.objects.remove(arm, do_unlink=True)
    f0, f1 = 1, 361
    axis = args['ferris_spin'].get('axis', 0)
    for f, ang in ((f0, 0.0), (f1, 2 * math.pi)):
        wheel.rotation_euler[axis] = ang; wheel.keyframe_insert('rotation_euler', index=axis, frame=f)
        for e in seats.values():
            e.rotation_euler[axis] = -ang; e.keyframe_insert('rotation_euler', index=axis, frame=f)
    for o in [wheel] + list(seats.values()):
        for fc in o.animation_data.action.fcurves:
            for k in fc.keyframe_points: k.interpolation = 'LINEAR'
    sc.frame_start, sc.frame_end = f0, f1
    log('ferris: wheel + %d cabins animated' % len(seats))

# ---------------------------------------------------------------- animation range + seam
acts = {}
for o in sc.objects:
    ad = o.animation_data
    if ad and ad.action: acts[ad.action.name] = ad.action.frame_range[:]
    if o.type == 'MESH' and o.data.shape_keys and o.data.shape_keys.animation_data and o.data.shape_keys.animation_data.action:
        a = o.data.shape_keys.animation_data.action; acts[a.name] = a.frame_range[:]
if KIND == 'anim':
    f0 = min(r[0] for r in acts.values()); f1 = max(r[1] for r in acts.values())
    sc.frame_start, sc.frame_end = int(math.floor(f0)), int(math.ceil(f1))
    fps = sc.render.fps / sc.render.fps_base
    info.update(f0=sc.frame_start, f1=sc.frame_end, fps=round(fps, 3), dur=round((sc.frame_end - sc.frame_start) / fps, 4))

    def snap(frame):
        sc.frame_set(int(frame)); dg = bpy.context.evaluated_depsgraph_get(); pts = []
        for o in sc.objects:
            if o.type != 'MESH': continue
            oe = o.evaluated_get(dg); me = oe.to_mesh(); mw = oe.matrix_world
            step = max(1, len(me.vertices) // 400)          # a sample of every mesh is enough
            pts += [mw @ me.vertices[i].co for i in range(0, len(me.vertices), step)]
            oe.to_mesh_clear()
        return pts
    a, b = snap(sc.frame_start), snap(sc.frame_end)
    mid = snap((sc.frame_start + sc.frame_end) // 2)
    mn, mx = world_bounds(sc.frame_start)
    size = max((mx - mn).length, 1e-6)
    seam = max(((p - q).length for p, q in zip(a, b)), default=0.0) / size
    travel = max(((p - q).length for p, q in zip(a, mid)), default=0.0) / size
    info['seam'] = round(seam, 4); info['travel'] = round(travel, 4)
    info['loop'] = 'loop' if seam < max(0.01, 0.08 * travel) else 'bounce'
    log('range', sc.frame_start, sc.frame_end, 'fps', fps, 'seam %.4f travel %.4f -> %s' % (seam, travel, info['loop']))
else:
    mn, mx = world_bounds()

# ---------------------------------------------------------------- normalise: largest side = 2, centred
size = mx - mn; big = max(size)
k = 2.0 / big if big > 0 else 1.0
centre = (mn + mx) * 0.5
info['scale'] = k; info['size'] = [round(x * k, 4) for x in size]

if KIND == 'static':
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in sc.objects if o.type == 'MESH']
    for o in sc.objects:                                   # bake parents / modifiers into plain meshes
        o.hide_set(False); o.hide_viewport = False
    dg = bpy.context.evaluated_depsgraph_get()
    for o in meshes:
        bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    meshes = [o for o in sc.objects if o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in meshes:                                       # one UV map with one name everywhere, so join keeps them
        uvs = o.data.uv_layers
        while len(uvs) > 1: uvs.remove(uvs[-1])
        if len(uvs) == 0: uvs.new(name='UVMap')
        uvs[0].name = 'UVMap'
    if len(meshes) > 1: bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    for o in list(sc.objects):
        if o != ob: bpy.data.objects.remove(o, do_unlink=True)
    me = ob.data
    for v in me.vertices: v.co = (v.co - centre) * k
    me.update()
    mats = [m for m in me.materials if m]
    img = basecolor(mats[0]) if len(mats) == 1 else None
    tex_path = os.path.join(OUT, NAME + '.jpg')
    if img is not None and me.uv_layers:
        # one material with a picture: keep its UVs, just save the picture (max 2048)
        if max(img.size) > 2048:
            s = 2048.0 / max(img.size); img.scale(int(img.size[0] * s), int(img.size[1] * s))
        img.filepath_raw = tex_path; img.file_format = 'JPEG'; img.save()
        info['texture'] = 'kept'
    else:
        # several materials / plain colours: bake everything into one picture on new UVs
        while len(me.uv_layers) > 1: me.uv_layers.remove(me.uv_layers[-1])   # max 8 UV maps: keep the first for the textures
        orig = [u.name for u in me.uv_layers]
        if orig: me.uv_layers.active_index = 0; me.uv_layers[0].active_render = True
        uv = me.uv_layers.new(name='bake')
        me.uv_layers.active = uv
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
        bpy.ops.object.mode_set(mode='OBJECT')
        res = 2048
        bimg = bpy.data.images.new(NAME + '_bake', res, res)
        for m in mats:
            m.use_nodes = True; nt = m.node_tree
            for x in nt.nodes:                         # bake the plain colour: metal / glass have no diffuse colour
                if x.type == 'BSDF_PRINCIPLED':
                    for inp, v in (('Metallic', 0.0), ('Transmission Weight', 0.0), ('Alpha', 1.0)):
                        if inp in x.inputs and not x.inputs[inp].links: x.inputs[inp].default_value = v
                        elif inp in x.inputs:
                            for l in list(x.inputs[inp].links): nt.links.remove(l)
                            x.inputs[inp].default_value = v
            n = nt.nodes.new('ShaderNodeTexImage'); n.image = bimg
            for x in nt.nodes: x.select = False
            n.select = True; nt.nodes.active = n
        sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 1
        sc.render.bake.use_pass_direct = False; sc.render.bake.use_pass_indirect = False; sc.render.bake.use_pass_color = True
        sc.render.bake.margin = 8
        ob.select_set(True); bpy.context.view_layer.objects.active = ob
        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, use_clear=True)
        bimg.filepath_raw = tex_path; bimg.file_format = 'JPEG'; bimg.save()
        for nm in orig: me.uv_layers.remove(me.uv_layers[nm])
        me.uv_layers['bake'].active = True; me.uv_layers['bake'].active_render = True
        info['texture'] = 'baked'
    # one material that points at the picture
    for i in range(len(me.materials)): me.materials[i] = None
    me.materials.clear()
    mm = bpy.data.materials.new(NAME); me.materials.append(mm)
    bpy.ops.object.shade_smooth() if not any(p.use_smooth for p in me.polygons) else None
    bpy.ops.wm.obj_export(filepath=os.path.join(OUT, NAME + '.obj'), export_selected_objects=False, export_uv=True,
                          export_normals=True, export_materials=False, forward_axis='NEGATIVE_Z', up_axis='Y',
                          export_triangulated_mesh=True)
    with open(os.path.join(OUT, NAME + '.mtl'), 'w') as f: f.write('newmtl %s\nKd 1 1 1\nillum 1\nmap_Kd %s.jpg\n' % (NAME, NAME))
    txt = open(os.path.join(OUT, NAME + '.obj')).read()
    if not txt.startswith('mtllib'):
        open(os.path.join(OUT, NAME + '.obj'), 'w').write('mtllib %s.mtl\nusemtl %s\n' % (NAME, NAME) + txt)
    info['verts'] = len(me.vertices); info['faces'] = len(me.polygons)
else:
    # animated: a root empty carries the normalisation, the animation stays untouched underneath
    for img in bpy.data.images:                       # TouchDesigner Non-Commercial caps textures at 1280: 1024 loads faster
        try:
            if img.size[0] and max(img.size) > 1024:
                s_ = 1024.0 / max(img.size); img.scale(max(1, int(img.size[0] * s_)), max(1, int(img.size[1] * s_))); img.pack()
        except Exception as e: log('texture resize failed', img.name, e)
    for img in list(bpy.data.images):                 # TouchDesigner can't read JPEGs embedded in an FBX: re-embed as PNG
        try:
            if not img.size[0] or img.source != 'FILE': continue
            if (img.file_format or '').upper() in ('JPEG', 'JPG') or img.filepath.lower().endswith(('.jpg', '.jpeg')):
                tmp = os.path.join(OUT, '_png_' + bpy.path.clean_name(img.name) + '.png')
                img.filepath_raw = tmp; img.file_format = 'PNG'; img.save()
                img.filepath = tmp; img.reload(); img.pack()
                log('texture -> png', img.name)
        except Exception as e: log('png convert failed', img.name, e)
    # textures that point at files that don't exist: drop them (TouchDesigner would show an error)
    for m in bpy.data.materials:
        if not m.node_tree: continue
        for n in list(m.node_tree.nodes):
            if n.type == 'TEX_IMAGE' and (n.image is None or (n.image.packed_file is None and not os.path.exists(bpy.path.abspath(n.image.filepath)))):
                m.node_tree.nodes.remove(n); log('dropped missing texture in', m.name)
    root = bpy.data.objects.new('ROOT', None); sc.collection.objects.link(root)
    for o in list(sc.objects):
        if o is not root and o.parent is None:
            mw = o.matrix_world.copy(); o.parent = root; o.matrix_world = mw
    root.matrix_world = Matrix.Scale(k, 4) @ Matrix.Translation(-centre)
    if args.get('abc'):
        # Alembic + one baked texture (for files whose FBX materials TouchDesigner can't show)
        meshes = [o for o in sc.objects if o.type == 'MESH']
        sc.frame_set(sc.frame_start)
        for o in meshes:
            uvs = o.data.uv_layers
            while len(uvs): uvs.remove(uvs[0])
            uvs.new(name='bake')
        bpy.ops.object.select_all(action='DESELECT')
        for o in meshes: o.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)   # all pieces share one picture
        bpy.ops.object.mode_set(mode='OBJECT')
        bimg = bpy.data.images.new(NAME + '_bake', 1024, 1024)
        for m in bpy.data.materials:
            if not m.users: continue
            m.use_nodes = True; nt = m.node_tree
            for x in nt.nodes:
                if x.type == 'BSDF_PRINCIPLED':
                    for inp, v in (('Metallic', 0.0), ('Transmission Weight', 0.0), ('Alpha', 1.0)):
                        if inp in x.inputs:
                            for l in list(x.inputs[inp].links): nt.links.remove(l)
                            x.inputs[inp].default_value = v
            n = nt.nodes.new('ShaderNodeTexImage'); n.image = bimg
            for x in nt.nodes: x.select = False
            n.select = True; nt.nodes.active = n
        sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 1; sc.render.bake.margin = 6
        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, use_clear=True)
        bimg.filepath_raw = os.path.join(OUT, NAME + '.jpg'); bimg.file_format = 'JPEG'; bimg.save()
        bpy.ops.wm.alembic_export(filepath=os.path.join(OUT, NAME + '.abc'), start=sc.frame_start, end=sc.frame_end,
                                  selected=False, uvs=True, normals=True, face_sets=False, triangulate=True, global_scale=1.0)
        info['kind'] = 'abc'; info['texture'] = NAME + '.jpg'
    else:
        bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, NAME + '.fbx'), use_selection=False, path_mode='COPY', embed_textures=True,
                                 bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                                 bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0, add_leaf_bones=False,
                                 apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', object_types={'EMPTY', 'MESH', 'ARMATURE'})
    info['verts'] = sum(len(o.data.vertices) for o in sc.objects if o.type == 'MESH')
    info['objects'] = len([o for o in sc.objects if o.type == 'MESH'])
json.dump(info, open(os.path.join(OUT, NAME + '.json'), 'w'), indent=1)
print('[conv] DONE ' + json.dumps(info), flush=True)
