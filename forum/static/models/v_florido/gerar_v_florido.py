# Gera o "V florido" da Verdigis: Y de blocos arredondados coberto de folhas e flores azuis.
# Rodar no Blender:  exec(open(CAMINHO_DESTE_ARQUIVO).read())
import bpy, bmesh, math, random, os, traceback
from mathutils import Vector, Matrix

OUT = "/Users/jmfcc/Desktop/branch verdigis/forum/static/models/v_florido"
LOG = os.path.join(OUT, "log.txt")

# ---- AJUSTES --------------------------------------------------------------
SEED = 7
LARG = 1.1          # largura de cada bloco
PROF = 1.0          # profundidade de cada bloco
BEVEL = 0.32        # arredondamento dos cantos
N_FOLHAS = 4600
N_FLORES = 230
TAM_FOLHA = (0.17, 0.27)
TAM_FLOR = (0.10, 0.15)
# blocos: (x_centro, z_centro, altura)  -> forma do Y em "escadinha"
BLOCOS = [
    (-1.65, 3.27, 1.75),   # braco esquerdo
    ( 1.65, 3.27, 1.75),   # braco direito
    (-0.85, 1.88, 1.75),   # degrau esquerdo
    ( 0.85, 1.88, 1.75),   # degrau direito
    ( 0.00, 0.35, 1.95),   # haste
]
VERDES = [(0.04, 0.13, 0.02), (0.10, 0.26, 0.04), (0.20, 0.40, 0.07)]
AZUL_FLOR = (0.32, 0.45, 1.0)
MIOLO = (0.95, 0.92, 0.75)
BASE_COR = (0.05, 0.12, 0.03)
# ---------------------------------------------------------------------------

def mat(nome, cor, rough=0.6):
    m = bpy.data.materials.get(nome) or bpy.data.materials.new(nome)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*cor, 1)
    bsdf.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*cor, 1)
    return m

def limpar():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)

def dentro_de_outro(p, i_bloco, folga=0.06):
    for j, (cx, cz, h) in enumerate(BLOCOS):
        if j == i_bloco:
            continue
        if (abs(p.x - cx) < LARG/2 - folga and abs(p.z - cz) < h/2 - folga
                and abs(p.y) < PROF/2 - folga):
            return True
    return False

def criar_base():
    bm = bmesh.new()
    tris = []  # (area, v0, v1, v2, normal, i_bloco)
    for i, (cx, cz, h) in enumerate(BLOCOS):
        b = bmesh.new()
        bmesh.ops.create_cube(b, size=1.0)
        for v in b.verts:
            v.co = Vector((v.co.x*LARG + cx, v.co.y*PROF, v.co.z*h + cz))
        bmesh.ops.bevel(b, geom=b.verts[:] + b.edges[:], offset=BEVEL,
                        segments=4, profile=0.5, affect='EDGES', clamp_overlap=True)
        bmesh.ops.triangulate(b, faces=b.faces[:])
        for f in b.faces:
            vs = [v.co.copy() for v in f.verts]
            tris.append((f.calc_area(), vs[0], vs[1], vs[2], f.normal.copy(), i))
        me_tmp = bpy.data.meshes.new("tmp")
        b.to_mesh(me_tmp); b.free()
        bm.from_mesh(me_tmp); bpy.data.meshes.remove(me_tmp)
    me = bpy.data.meshes.new("V_base")
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("V_base", me)
    bpy.context.collection.objects.link(ob)
    me.materials.append(mat("verdigis_base", BASE_COR, 0.9))
    for p in me.polygons: p.use_smooth = True
    return tris

def amostrar(tris, n):
    pesos = [t[0] for t in tris]
    out = []
    tent = 0
    while len(out) < n and tent < n*4:
        tent += 1
        a, v0, v1, v2, nrm, i = random.choices(tris, pesos)[0]
        r1, r2 = random.random(), random.random()
        if r1 + r2 > 1: r1, r2 = 1-r1, 1-r2
        p = v0 + (v1-v0)*r1 + (v2-v0)*r2
        if dentro_de_outro(p, i):
            continue
        out.append((p, nrm.normalized()))
    return out

def forma_folha():
    # folha apontando para +Y, base na origem, com dobra central e curvatura
    linhas = 6
    vs, fs = [], []
    for k in range(linhas+1):
        t = k/linhas
        w = 0.42*(math.sin(math.pi*t)**0.8) if k < linhas else 0.0
        z = -0.18*t*t
        for s in (-1, 0, 1):
            vs.append((s*w, t, z + (0.0 if s == 0 else 0.10*w)))
    for k in range(linhas):
        a = k*3; b = (k+1)*3
        fs.append((a, a+1, b+1, b)); fs.append((a+1, a+2, b+2, b+1))
    return vs, fs

def forma_flor():
    # disco de 5 petalas levemente em taca; miolo separado
    vs = [(0, 0, -0.15)]
    n = 20
    for k in range(n):
        ang = 2*math.pi*k/n
        r = 1.0 if k % 4 in (0, 1) else 0.78
        if k % 4 == 3: r = 0.62
        vs.append((r*math.cos(ang), r*math.sin(ang), 0.12))
    fs = [(0, 1 + k, 1 + (k+1) % n) for k in range(n)]
    vs_m = [(0, 0, -0.05)] + [(0.22*math.cos(2*math.pi*k/6), 0.22*math.sin(2*math.pi*k/6), 0.0) for k in range(6)]
    fs_m = [(0, 1+k, 1+(k+1) % 6) for k in range(6)]
    return (vs, fs), (vs_m, fs_m)

def base_orto(nrm, inclin):
    # escolhe direcao tangente aleatoria, puxada para baixo (folhas "caem")
    aux = Vector((0, 0, 1)) if abs(nrm.z) < 0.9 else Vector((1, 0, 0))
    t1 = nrm.cross(aux).normalized(); t2 = nrm.cross(t1).normalized()
    ang = random.uniform(0, 2*math.pi)
    tan = (t1*math.cos(ang) + t2*math.sin(ang))
    baixo = Vector((0, 0, -1)); baixo = (baixo - nrm*baixo.dot(nrm))
    if baixo.length > 0.1:
        tan = (tan + baixo.normalized()*0.7).normalized()
    d = (tan*math.cos(inclin) + nrm*math.sin(inclin)).normalized()
    x = d.cross(nrm)
    if x.length < 1e-4: x = t1
    x.normalize()
    z = x.cross(d).normalized()
    return x, d, z

def instanciar(nome, pontos, formas, tam, inclin, afast, mats, escolher_mat):
    vs_all, fs_all, mi_all = [], [], []
    for p, nrm in pontos:
        s = random.uniform(*tam)
        x, y, z = base_orto(nrm, random.uniform(*inclin))
        origem = p + nrm*afast
        m_idx = escolher_mat()
        for f_idx, (vs, fs) in enumerate(formas):
            off = len(vs_all)
            for (a, b, c) in vs:
                vs_all.append(origem + (x*a + y*b + z*c)*s)
            for f in fs:
                fs_all.append(tuple(off+i for i in f))
                mi_all.append(m_idx if f_idx == 0 else len(mats)-1)
    me = bpy.data.meshes.new(nome)
    me.from_pydata([tuple(v) for v in vs_all], [], fs_all)
    me.update()
    for m in mats: me.materials.append(m)
    me.polygons.foreach_set("material_index", mi_all)
    for pg in me.polygons: pg.use_smooth = True
    ob = bpy.data.objects.new(nome, me)
    bpy.context.collection.objects.link(ob)
    return len(vs_all)

def cena_render():
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            sc.render.engine = eng; break
        except Exception:
            pass
    if sc.render.engine == "CYCLES":
        sc.cycles.samples = 48
    sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y = 800, 1000
    if sc.world is None: sc.world = bpy.data.worlds.new("World")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.8, 0.85, 0.9, 1); bg.inputs[1].default_value = 0.45
    cam_d = bpy.data.cameras.new("cam"); cam_d.type = 'ORTHO'; cam_d.ortho_scale = 8.2
    cam = bpy.data.objects.new("cam", cam_d); bpy.context.collection.objects.link(cam)
    ang = math.radians(18)
    cam.location = (14*math.sin(ang), -14*math.cos(ang), 2.3)
    cam.rotation_euler = (math.radians(88), 0, ang)
    sc.camera = cam
    sol_d = bpy.data.lights.new("sol", 'SUN'); sol_d.energy = 2.6
    sol = bpy.data.objects.new("sol", sol_d); bpy.context.collection.objects.link(sol)
    sol.rotation_euler = (math.radians(50), math.radians(-25), math.radians(-30))

def main():
    random.seed(SEED)
    os.makedirs(OUT, exist_ok=True)
    limpar()
    tris = criar_base()
    verdes = [mat(f"verdigis_folha_{i}", c, 0.55) for i, c in enumerate(VERDES)]
    pts = amostrar(tris, N_FOLHAS)
    nv_f = instanciar("V_folhas", pts, [forma_folha()], TAM_FOLHA,
                      (math.radians(20), math.radians(55)), 0.02, verdes + [verdes[0]],
                      lambda: random.choices([0, 1, 2], [3, 5, 3])[0])
    pts_fl = amostrar(tris, N_FLORES)
    petalas, miolo = forma_flor()
    mats_fl = [mat("verdigis_flor", AZUL_FLOR, 0.5), mat("verdigis_miolo", MIOLO, 0.6)]
    nv_fl = instanciar("V_flores", pts_fl, [petalas, miolo], TAM_FLOR,
                       (math.radians(75), math.radians(90)), 0.16, mats_fl, lambda: 0)
    cena_render()
    glb = os.path.join(OUT, "v_florido.glb")
    bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', export_apply=True)
    sc = bpy.context.scene
    sc.render.filepath = os.path.join(OUT, "preview.png")
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "v_florido.blend"))
    with open(LOG, "w") as f:
        f.write(f"OK engine={sc.render.engine} folhas_verts={nv_f} flores_verts={nv_fl} "
                f"glb_bytes={os.path.getsize(glb)} blender={bpy.app.version_string}\n")

try:
    main()
except Exception:
    with open(LOG, "w") as f:
        f.write("ERRO\n" + traceback.format_exc())
    raise
