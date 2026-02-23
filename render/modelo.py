#modelo.py
from OpenGL.GL import *
import numpy as np
import ctypes
import pyrr
import os
from . import shaders
from GestorDeRecursos import resource_path

# Intentamos importar trimesh para cargar el GLB
try:
    import trimesh
    from PIL import Image
except ImportError:
    trimesh = None
    Image = None
    print("⚠️ Error: Librería 'trimesh' no encontrada. Instala con: pip install trimesh")

class Model3D:
    def __init__(self, ctx, filename="elfa.obj"):
        self.ctx = ctx
        self.filename = filename
        self.loaded = False
        
        # Transformaciones base (ajusta según necesites)
        self.position = [0.0, -0.5, 2.0] # Z = -2.0 para asegurar que esté frente a la cámara
        self.scale = [1.0, 1.0, 1.0]     # Escala 1.0 porque normalizamos la geometría
        self.rotation = [0.0, 0.0, 0.0]

        # Variable para suavizar el movimiento Z
        self.smoothed_bass_energy = 0.0

        # Cargar Shaders
        self.program = shaders.load_shader_program("render/model.vert", "render/model.frag")
        if not self.program:
            print("❌ No se pudieron cargar los shaders del modelo.")
            return

        # Obtener ubicaciones de Uniforms
        self.u_proj_loc = glGetUniformLocation(self.program, "u_projection")
        self.u_view_loc = glGetUniformLocation(self.program, "u_view")
        self.u_model_loc = glGetUniformLocation(self.program, "u_model")
        self.u_tex_loc = glGetUniformLocation(self.program, "u_texture")
        self.u_use_tex_loc = glGetUniformLocation(self.program, "u_use_texture")

        # Recursos OpenGL
        self.meshes = [] # Lista de sub-mallas: {vao, index_count, texture_id}

        # --- FASE 1: Mapeo explícito de sub-mallas -> texturas ---
        # Definimos manualmente qué archivo PNG usa cada parte del modelo.
        # Las claves son los nombres que trimesh asigna a las sub-mallas.
        self.TEXTURE_MAP = {
            # Nombre interno (Trimesh)          : Archivo en raíz
            "ssjgohan_ssjgohan_ssjgohanface.bmp": "modelo 3d/gohan/ssjgohanface.png",
            "ssjgohan_ssjgohan_GohanSkin.bmp"   : "modelo 3d/gohan/GohanSkin.png",
            "ssjgohan_ssjgohan_GohanClothes.bmp": "modelo 3d/gohan/GohanClothes.png",
            # Variaciones por si Trimesh usa el nombre del material directo
            "ssjgohanface.bmp": "modelo 3d/gohan/ssjgohanface.png",
            "GohanSkin.bmp": "modelo 3d/gohan/GohanSkin.png",
            "GohanClothes.bmp": "modelo 3d/gohan/GohanClothes.png",
            # Variaciones detectadas en consola (Trimesh split por orden)
            "ssjgohan": "modelo 3d/gohan/GohanClothes.png",   # Ajuste manual: Ropa
            "ssjgohan_1": "modelo 3d/gohan/GohanSkin.png",    # 2º en OBJ: Piel
            "ssjgohan_2": "modelo 3d/gohan/ssjgohanface.png"  # Ajuste manual: Cabeza
        }

        # Cargar geometría si trimesh está disponible
        if trimesh:
            self.load_glb(filename)

    def load_glb(self, filename):
        filepath = resource_path(filename)
        if not os.path.exists(filepath):
            print(f"⚠️ Archivo de modelo no encontrado: {filepath}")
            return

        print(f"📂 Cargando modelo 3D: {filepath}...")
        try:
            # Cargar escena
            scene = trimesh.load(filepath)
            
            # Obtener la primera geometría disponible
            geometries = []
            geometry_names = []
            if isinstance(scene, trimesh.Scene):
                for name, geom in scene.geometry.items():
                    geometries.append(geom)
                    geometry_names.append(name)
            else:
                geometries = [scene]
                geometry_names.append("mesh_0")

            if not geometries:
                print("⚠️ El archivo GLB no contiene geometría válida.")
                return

            print(f" Sub-mallas encontradas: {len(geometries)}")
            print(f"🔹 Nombres detectados: {geometry_names}")

            # --- NORMALIZACIÓN DE GEOMETRÍA (CRÍTICO) ---
            # 1. Centrar en (0,0,0)
            # Calculamos el centroide global si es una escena
            if isinstance(scene, trimesh.Scene):
                centroid = scene.centroid
                bounds = scene.bounds
            else:
                centroid = scene.centroid
                bounds = scene.bounds
            
            print(f"📏 Bounds Globales: {bounds}")
            
            # Normalizar todas las geometrías relativas al centro global
            # Primero centrar
            for g in geometries:
                g.vertices -= centroid
            
            # Calcular escala global
            max_dist = 0
            for g in geometries:
                d = np.max(np.linalg.norm(g.vertices, axis=1))
                if d > max_dist: max_dist = d
            
            if max_dist > 0:
                scale = 1.0 / max_dist
                for g in geometries:
                    g.vertices *= scale
                print(f"📏 Geometría normalizada (Escala aplicada: 1/{max_dist:.2f})")

            # --- Expandir Vértices (Geometry Expansion) ---
            self.meshes = []
            
            for i, geometry in enumerate(geometries):
                mesh_name = geometry_names[i]
                # --- Procesar Geometría ---
                verts = geometry.vertices
                faces = geometry.faces
                uvs = getattr(geometry.visual, 'uv', None)
                
                if not hasattr(geometry, 'vertex_normals') or geometry.vertex_normals is None:
                    try: geometry.compute_vertex_normals()
                    except: pass
                normals = getattr(geometry, 'vertex_normals', None)
                
                if uvs is None:
                    uvs = np.zeros((len(verts), 2), dtype=np.float32)
                # Debug UVs para asegurar que no sean todos ceros
                # print(f"   📊 Malla '{mesh_name}': {len(uvs)} UVs. Rango: {uvs.min():.2f} a {uvs.max():.2f}")

                final_vertices_list = []
                final_indices_list = []
                
                idx = 0
                for face in faces:
                    for vert_idx in face:
                        pos = verts[vert_idx]
                        uv = uvs[vert_idx]
                        if normals is not None and len(normals) > vert_idx:
                            norm = normals[vert_idx]
                        else:
                            norm = [0.0, 0.0, 1.0]
                        
                        final_vertices_list.extend([
                            pos[0], pos[1], pos[2], 
                            norm[0], norm[1], norm[2], 
                            uv[0], uv[1]
                        ])
                        final_indices_list.append(idx)
                        idx += 1

                final_vertices = np.array(final_vertices_list, dtype=np.float32)
                final_indices = np.array(final_indices_list, dtype=np.uint32)
                
                # --- Cargar Textura Específica ---
                tex_id = self._load_texture_for_mesh(geometry, mesh_name)
                
                # --- Configurar VAO/VBO ---
                vao = glGenVertexArrays(1)
                glBindVertexArray(vao)
                
                vbo = glGenBuffers(1)
                glBindBuffer(GL_ARRAY_BUFFER, vbo)
                glBufferData(GL_ARRAY_BUFFER, final_vertices.nbytes, final_vertices, GL_STATIC_DRAW)
                
                ebo = glGenBuffers(1)
                glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
                glBufferData(GL_ELEMENT_ARRAY_BUFFER, final_indices.nbytes, final_indices, GL_STATIC_DRAW)
                
                stride = 8 * 4 
                glEnableVertexAttribArray(0)
                glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
                glEnableVertexAttribArray(2)
                glVertexAttribPointer(2, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
                glEnableVertexAttribArray(1)
                glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(24))
                
                glBindVertexArray(0)
                
                self.meshes.append({
                    'vao': vao,
                    'vbo': vbo,
                    'ebo': ebo,
                    'count': len(final_indices),
                    'texture_id': tex_id
                })
                print(f"✅ Sub-malla {i} cargada. Textura ID: {tex_id}")

            self.loaded = True
            print("✅ Modelo completo cargado en GPU.")

        except Exception as e:
            print(f"❌ Error crítico cargando GLB: {e}")
            import traceback
            traceback.print_exc()

    def _load_texture_for_mesh(self, geometry, mesh_name):
        """Carga la textura correspondiente a una sub-malla."""
        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        
        # --- FASE 2: Carga directa desde raíz (Sin búsquedas) ---
        filename = self.TEXTURE_MAP.get(mesh_name)
        image = None
        
        if filename:
            # Intentar cargar archivo exacto desde la raíz
            filepath = resource_path(filename)
            if os.path.exists(filepath):
                print(f"   🎯 Mapeo explícito: '{mesh_name}' -> '{filepath}'")
                try:
                    image = Image.open(filepath)
                except Exception as e:
                    print(f"   ❌ Error abriendo textura '{filepath}': {e}")
            else:
                print(f"   ⚠️ Archivo no encontrado en ruta: '{filepath}'")
        else:
            print(f"   ⚠️ Malla sin mapeo definido: '{mesh_name}'")
            # Aquí podrías imprimir mesh_name para copiarlo al diccionario si falta
        
        # 3. Fallback a Ajedrez
        if image is None:
            print("   ⚠️ Textura no encontrada. Usando Ajedrez.")
            self._create_checkerboard_texture(tex_id)
            return tex_id
            
        # Procesar imagen encontrada
        try:
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            image = image.transpose(Image.FLIP_TOP_BOTTOM)
            img_data = image.tobytes()
            w, h = image.size
            
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
            glGenerateMipmap(GL_TEXTURE_2D)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        except Exception as e:
            print(f"   ❌ Error procesando textura: {e}")
            self._create_checkerboard_texture(tex_id)
            
        return tex_id

    def _create_checkerboard_texture(self, tex_id=None):
        """Genera una textura de ajedrez rojo/azul para debug."""
        if tex_id: glBindTexture(GL_TEXTURE_2D, tex_id)
        w, h = 64, 64
        checker = np.zeros((h, w, 4), dtype=np.uint8)
        for y in range(h):
            for x in range(w):
                if (x // 8 + y // 8) % 2 == 0:
                    checker[y, x] = [255, 50, 50, 255] # Rojo
                else:
                    checker[y, x] = [50, 50, 255, 255] # Azul
        
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, checker.tobytes())
        glGenerateMipmap(GL_TEXTURE_2D)

    def render(self, projection, view):
        if not self.loaded or not self.meshes: return

        glUseProgram(self.program)
        
        # Reactivamos Depth Test y Blending estándar para que se vea sólido pero correcto
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # Animación: Rotación desactivada (estático)
        # self.rotation[1] = self.ctx.time.get_time() * 0.0005

        # --- Suavizado de Movimiento Z (Independiente de las estrellas) ---
        # Configuración desde UI
        cfg = self.ctx.ui.config
        attack_factor = cfg.get("model_attack", 0.1)
        decay_factor = cfg.get("model_decay", 0.05)
        threshold = cfg.get("model_threshold", 0.0) / 100.0 # Escala 0-100 -> 0.0-1.0

        # Lógica de Umbral (Gate)
        raw_energy = self.ctx.bass_energy
        if raw_energy < threshold:
            target_energy = 0.0
        else:
            target_energy = raw_energy
        
        if target_energy > self.smoothed_bass_energy:
            # Lerp rápido hacia el pico de energía
            self.smoothed_bass_energy = self.smoothed_bass_energy * (1.0 - attack_factor) + target_energy * attack_factor
        else:
            # Lerp lento de vuelta a cero
            self.smoothed_bass_energy = self.smoothed_bass_energy * (1.0 - decay_factor) + target_energy * decay_factor

        # Si la energía suavizada es muy baja, no renderizamos (ahorra recursos y cumple "no se vea")
        if self.smoothed_bass_energy < 0.001:
            return

        # Animación Z: Gohan se aleja con los bajos (Reactividad)
        # Rango: 2.0 (Reposo) a -8.0 (Máxima energía)
        base_z = 6.0
        target_z = -15.0
        reactivity = self.ctx.ui.config.get("ESCALA_POR_INTENSIDAD", 100.0) / 100.0
        self.position[2] = base_z + (target_z - base_z) * self.smoothed_bass_energy * reactivity

        # Construir matriz de modelo (Orden corregido: Identity -> Scale -> Rot -> Trans)
        scale_mat = pyrr.matrix44.create_from_scale(self.scale)
        rot_mat = pyrr.matrix44.create_from_eulers(self.rotation)
        trans_mat = pyrr.matrix44.create_from_translation(self.position)
        
        model_mat = pyrr.matrix44.create_identity()
        model_mat = pyrr.matrix44.multiply(model_mat, scale_mat)
        model_mat = pyrr.matrix44.multiply(model_mat, rot_mat)
        model_mat = pyrr.matrix44.multiply(model_mat, trans_mat)
        
        glUniformMatrix4fv(self.u_proj_loc, 1, GL_FALSE, projection)
        glUniformMatrix4fv(self.u_view_loc, 1, GL_FALSE, view)
        glUniformMatrix4fv(self.u_model_loc, 1, GL_FALSE, model_mat)
        
        # Renderizar cada sub-malla
        for mesh in self.meshes:
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, mesh['texture_id'])
            glUniform1i(self.u_tex_loc, 0)
            glUniform1i(self.u_use_tex_loc, 1) # Asumimos que siempre hay textura (o ajedrez)
            
            glBindVertexArray(mesh['vao'])
            glDrawElements(GL_TRIANGLES, mesh['count'], GL_UNSIGNED_INT, None)
            glBindVertexArray(0)