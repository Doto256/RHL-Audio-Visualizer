# render/renderer.py
# ============================================================================
# Renderizador Moderno (OpenGL Core Profile)
# ============================================================================
# Implementación base para renderizado usando Shaders, VAOs y VBOs.
# Prepara el terreno para abandonar el pipeline fijo (glBegin/glEnd).
# ============================================================================

from OpenGL.GL import *
import numpy as np
import ctypes
import pyrr
import math
from . import shaders
from .postprocess import PostProcessor
import random
from .modelo import Model3D

class ModernRenderer:
    def __init__(self, ctx):
        self.ctx = ctx
        
        # --- Carga de Shaders ---
        # Usamos nuestro nuevo módulo para cargar y compilar los shaders.
        self.program = shaders.load_shader_program(
            "render/tunnel.vert", 
            "render/tunnel.frag"
        )
        if not self.program:
            raise RuntimeError("No se pudieron cargar los shaders. La aplicación no puede continuar.")

        # --- Obtención de Ubicación de Uniforms ---
        # Guardamos las ubicaciones para no tener que buscarlas en cada frame, es más eficiente.
        self.u_projection_loc = glGetUniformLocation(self.program, "u_projection")
        self.u_view_loc = glGetUniformLocation(self.program, "u_view")
        self.u_time_loc = glGetUniformLocation(self.program, "u_time")
        self.u_energy_loc = glGetUniformLocation(self.program, "u_energy")

        # --- Buffers (VAO/VBO) ---
        # El VAO (Vertex Array Object) almacena la configuración de los atributos de vértice.
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        
        # El VBO (Vertex Buffer Object) es la memoria donde se guardan los datos de los vértices.
        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        
        # --- Configuración de Atributos de Vértice ---
        # Le decimos a OpenGL cómo interpretar los datos del VBO.
        # El 'stride' es el tamaño total de un vértice en bytes (6 floats * 4 bytes/float = 24).
        stride = 6 * 4 
        
        # Atributo 0: Posición (vec3) -> layout (location = 0) en el shader
        # Son 3 floats, y empiezan en el byte 0 de cada vértice.
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        
        # Atributo 1: Datos de Color (vec3: hue_base, t, intensity) -> layout (location = 1)
        # Son 3 floats, y empiezan después de la posición (en el byte 12).
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
        glEnableVertexAttribArray(1)
        
        # --- Matrices de Cámara ---
        # Creamos las matrices de proyección y vista que reemplazan a gluPerspective y glTranslatef.
        self.projection_matrix = pyrr.matrix44.create_perspective_projection_matrix(
            60.0, self.ctx.W / self.ctx.H, 0.1, 100.0
        )
        # Vista simple, mirando al origen desde z=5 (equivalente a glTranslatef(0,0,-5)).
        self.view_matrix = pyrr.matrix44.create_look_at(
            pyrr.Vector3([0.0, 0.0, 5.0]), # Posición de la cámara
            pyrr.Vector3([0.0, 0.0, 0.0]), # Punto al que mira
            pyrr.Vector3([0.0, 1.0, 0.0])  # Vector "arriba"
        )

        # --- Inicializar Campos Estelares ---
        # 1. Estrellas Graves (Azuladas)
        self.stars_bass = StarField(ctx, {
            "num": "NUM_PARTICULAS",
            "size": "TAMANO_BASE_PARTICULA",
            "scale": "ESCALA_POR_INTENSIDAD",
            "bright": "FACTOR_BRILLO_PARTICULAS",
            "thresh": "UMBRAL_INTENSIDAD_tamaño_particulas",
            "max_size": "MAX_SIZE_PARTICULA",
            "vmin": "velmin_particulas",
            "vmax": "velmax_particulas"
        }, 0, "bass_energy") # 0 = Primer color de la paleta

        # 2. Estrellas Agudos/Platos (Cian Glacial)
        self.stars_high = StarField(ctx, {
            "num": "NUM_PLATOS",
            "size": "TAMANO_BASE_PLATO",
            "scale": "ESCALA_INTENSIDAD_PLATO",
            "bright": "FACTOR_BRILLO_PLATO",
            "thresh": "UMBRAL_INTENSIDAD_PLATO",
            "max_size": "MAX_SIZE_PLATO",
            "vmin": "velmin_platos",
            "vmax": "velmax_platos"
        }, 1, "high_energy") # 1 = Segundo color de la paleta

        # --- Modelo 3D (Elfa) ---
        self.model = Model3D(ctx, "modelo 3d/gohan/elfa.obj")

        # --- Post-Procesamiento (Fase 1: FBO Base) ---
        self.post = PostProcessor(ctx)

        # Acumulador para cambio automático de paleta
        self.energy_accumulator = 0.0

        self.vertex_data = np.array([], dtype=np.float32)
        self.point_count = 0

    def resize(self, w, h):
        """Actualiza el viewport y la matriz de proyección al cambiar tamaño de ventana."""
        glViewport(0, 0, w, h)
        if h > 0:
            self.projection_matrix = pyrr.matrix44.create_perspective_projection_matrix(
                60.0, w / h, 0.1, 100.0
            )
        self.post.resize(w, h)

    def update(self, espectro):
        """Genera los vértices del túnel y los sube al VBO."""
        cfg = self.ctx.ui.config
        capas = int(cfg["tunel_vueltas"])
        num_dots = min(int(cfg["num_dots"]), len(espectro))
        z_near, z_far = cfg["z_near"], cfg["z_far"]
        
        if num_dots == 0 or capas < 2:
            self.point_count = 0
            return

        points = []
        for layer in range(capas):
            t = layer / (capas - 1)
            z = z_near * (1 - t) + z_far * t
            for j in range(num_dots):
                idx = int(j * len(espectro) / num_dots)
                v = espectro[idx]
                ang = (j / num_dots) * 2 * math.pi + self.ctx.giro
                r = v * 4.0 * (0.3 + 0.7 * t) + 0.2
                if r < 0.3: continue
                
                x, y = math.cos(ang) * r, math.sin(ang) * r
                hue_base = j / num_dots
                points.extend([x, y, z, hue_base, t, v])

        self.vertex_data = np.array(points, dtype=np.float32)
        self.point_count = len(points) // 6

        # Subir datos al VBO
        # No se recrea el buffer (VBO) en cada frame. Solo se actualiza su contenido
        # con los nuevos vértices del túnel, usando GL_DYNAMIC_DRAW para una
        # actualización eficiente.
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, self.vertex_data.nbytes, self.vertex_data, GL_DYNAMIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def render(self):
        """Ciclo de dibujo principal."""
        # La limpieza de pantalla (glClear) ahora se gestiona en main.py
        self.ctx.giro += 0.008

        # --- Lógica de Cambio Automático de Paleta ---
        # Si la opción "Interpolacion" está activada (1.0)
        if self.ctx.ui.config.get("palette_auto", 1.0) > 0.5:
            self.energy_accumulator += self.ctx.bass_energy
            if self.energy_accumulator > 200.0: # Umbral de energía acumulada
                self.energy_accumulator = 0.0
                num_paletas = len(self.ctx.ui.paletas)
                current = int(self.ctx.ui.config["palette_index"])
                self.ctx.ui.config["palette_index"] = (current + 1) % num_paletas
        
        # Actualizar lógica de estrellas una vez por frame
        self.stars_bass.update()
        self.stars_high.update()

        # --- FASE 1: Renderizar a FBO ---
        self.post.bind()
        # Limpiamos el FBO (necesario porque es un buffer nuevo)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # 1. Renderizar Estrellas "Fuera" (Fondo) - Radio > 5.0
        self.stars_bass.render(self.projection_matrix, self.view_matrix, min_r=5.0, max_r=1000.0)
        self.stars_high.render(self.projection_matrix, self.view_matrix, min_r=5.0, max_r=1000.0)
        
        # 2. Renderizar Túnel (Medio)
        self.update(self.ctx.espectro)
        
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE) # Modo aditivo para brillos
        glEnable(GL_PROGRAM_POINT_SIZE) # Permite al shader controlar el tamaño del punto
        
        if self.point_count > 0:
            glUseProgram(self.program)
            glUniformMatrix4fv(self.u_projection_loc, 1, GL_FALSE, self.projection_matrix)
            glUniformMatrix4fv(self.u_view_loc, 1, GL_FALSE, self.view_matrix)
            glUniform1f(self.u_time_loc, self.ctx.time.get_time() / 1000.0)
            glUniform1f(self.u_energy_loc, np.mean(self.ctx.espectro))

            glBindVertexArray(self.vao)
            glDrawArrays(GL_POINTS, 0, self.point_count)
            glBindVertexArray(0)
        
        # 3. Renderizar Estrellas "Dentro" (Frente) - Radio <= 5.0
        self.stars_bass.render(self.projection_matrix, self.view_matrix, min_r=0.0, max_r=5.0)
        self.stars_high.render(self.projection_matrix, self.view_matrix, min_r=0.0, max_r=5.0)

        # --- FASE 1.5: Calcular Bloom (SOLO Túnel + Estrellas) ---
        # Calculamos el brillo antes de dibujar el modelo, así el modelo no contribuye al glow.
        self.post.calculate_bloom()

        # --- FASE 1.8: Renderizar Modelo 3D (Sin Bloom) ---
        # Volvemos a bindear el FBO para dibujar el modelo sobre la escena existente.
        self.post.bind()
        glClear(GL_DEPTH_BUFFER_BIT)
        glEnable(GL_DEPTH_TEST)
        self.model.render(self.projection_matrix, self.view_matrix)

        # --- FASE 2: Volcar a Pantalla ---
        self.post.unbind()
        self.post.render()

class StarField:
    """
    Gestiona un campo de estrellas que viajan hacia la cámara.
    """
    def __init__(self, ctx, keys, palette_slot, energy_attr):
        self.ctx = ctx
        self.keys = keys # Diccionario con las claves de configuración
        self.palette_slot = palette_slot # 0 o 1, índice dentro de la paleta
        self.energy_attr = energy_attr # Nombre del atributo en ctx ('bass_energy' o 'high_energy')
        
        # Inicializar color actual para transiciones suaves
        idx_paleta = int(self.ctx.ui.config.get("palette_index", 0))
        self.current_color = self.ctx.ui.paletas[idx_paleta][self.palette_slot + 1]
        
        # Leer número inicial de estrellas
        self.num_stars = int(self.ctx.ui.config[self.keys["num"]])

        # Cargar shaders específicos para estrellas
        self.program = shaders.load_shader_program("render/stars.vert", "render/stars.frag")
        if not self.program:
            print("⚠️ Advertencia: No se pudieron cargar los shaders de estrellas.")
            return

        # Ubicaciones de uniforms
        self.u_proj_loc = glGetUniformLocation(self.program, "u_projection")
        self.u_view_loc = glGetUniformLocation(self.program, "u_view")
        self.u_bass_loc = glGetUniformLocation(self.program, "u_bass_energy")
        
        # Nuevos uniforms para control desde UI
        self.u_base_size_loc = glGetUniformLocation(self.program, "u_base_size")
        self.u_audio_scale_loc = glGetUniformLocation(self.program, "u_audio_scale")
        self.u_brightness_loc = glGetUniformLocation(self.program, "u_brightness")
        self.u_threshold_loc = glGetUniformLocation(self.program, "u_threshold")
        self.u_max_size_loc = glGetUniformLocation(self.program, "u_max_size")
        self.u_min_r_loc = glGetUniformLocation(self.program, "u_min_radius")
        self.u_max_r_loc = glGetUniformLocation(self.program, "u_max_radius")
        self.u_color_loc = glGetUniformLocation(self.program, "u_color")
        
        # Rango de generación
        # X e Y cubren un área amplia para que al acercarse pasen por los lados
        self.range_x = 60.0 
        self.range_y = 40.0
        self.min_z = -150.0 # Muy lejos
        self.max_z = -5.0   # Un poco lejos

        # --- Configuración OpenGL (VAO/VBO) ---
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        
        self.vbo = glGenBuffers(1)

        # Inicialización de datos
        self._init_star_data()
        
        # IMPORTANTE: _init_star_data desvincula el buffer al terminar.
        # Debemos volver a vincularlo para que glVertexAttribPointer sepa a qué buffer referirse.
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        
        # Atributo 0: Posición (vec3). 
        # NOTA: Ahora enviamos 4 floats (x,y,z,speed) pero el shader lee vec3 (x,y,z).
        # El stride cambia a 4 * 4 bytes = 16 bytes.
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 4 * 4, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        
        glBindVertexArray(0)

    def _init_star_data(self):
        """Genera o regenera el array de estrellas."""
        # Array numpy: [x, y, z, speed]
        self.stars = np.zeros((self.num_stars, 4), dtype=np.float32)
        
        cfg = self.ctx.ui.config
        v_min = cfg[self.keys["vmin"]] * 0.01 # Escalar valores de UI
        v_max = cfg[self.keys["vmax"]] * 0.01

        for i in range(self.num_stars):
            self.stars[i] = [
                random.uniform(-self.range_x, self.range_x),
                random.uniform(-self.range_y, self.range_y),
                random.uniform(self.min_z, self.max_z),
                random.uniform(v_min, v_max) # Velocidad individual
            ]
        
        # Subir datos iniciales al buffer
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, self.stars.nbytes, self.stars, GL_DYNAMIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def update(self):
        """Mueve las estrellas y recicla las que salen de cámara."""
        cfg = self.ctx.ui.config
        
        # Verificar si cambió el número de partículas
        target_num = int(cfg[self.keys["num"]])
        if target_num != self.num_stars:
            self.num_stars = target_num
            self._init_star_data()
            return # Salir por este frame

        # Mover todas las estrellas en Z usando su velocidad individual (columna 3)
        self.stars[:, 2] += self.stars[:, 3]
        
        # Detectar estrellas que pasaron la cámara
        # Usamos una máscara booleana de Numpy para eficiencia
        out_of_bounds = self.stars[:, 2] > 1.0
        
        # Contar cuántas hay que reciclar
        count = np.sum(out_of_bounds)
        
        if count > 0:
            v_min = cfg[self.keys["vmin"]] * 0.01
            v_max = cfg[self.keys["vmax"]] * 0.01
            
            # Generar nuevas posiciones aleatorias solo para las que salieron
            self.stars[out_of_bounds, 0] = np.random.uniform(-self.range_x, self.range_x, count) # X
            self.stars[out_of_bounds, 1] = np.random.uniform(-self.range_y, self.range_y, count) # Y
            self.stars[out_of_bounds, 2] = np.random.uniform(self.min_z, self.min_z + 10.0, count) # Z (Fondo)
            
            # Asignar nueva velocidad aleatoria
            self.stars[out_of_bounds, 3] = np.random.uniform(v_min, v_max, count)

        # Actualizar VBO en GPU
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        # glBufferSubData es más rápido para actualizaciones parciales, 
        # pero aquí actualizamos todo el array por simplicidad y porque Numpy es rápido.
        glBufferSubData(GL_ARRAY_BUFFER, 0, self.stars.nbytes, self.stars)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def render(self, proj_matrix, view_matrix, min_r=0.0, max_r=1000.0):
        if not self.program: return
        
        cfg = self.ctx.ui.config
        
        # Obtener color objetivo de la paleta activa
        idx_paleta = int(cfg.get("palette_index", 0))
        target_color = self.ctx.ui.paletas[idx_paleta][self.palette_slot + 1]

        # Interpolación lineal (Lerp) para suavizar el cambio de color
        lerp_speed = 0.020
        self.current_color = (
            self.current_color[0] + (target_color[0] - self.current_color[0]) * lerp_speed,
            self.current_color[1] + (target_color[1] - self.current_color[1]) * lerp_speed,
            self.current_color[2] + (target_color[2] - self.current_color[2]) * lerp_speed
        )

        glUseProgram(self.program)
        glUniformMatrix4fv(self.u_proj_loc, 1, GL_FALSE, proj_matrix)
        glUniformMatrix4fv(self.u_view_loc, 1, GL_FALSE, view_matrix)
        
        # Pasar la energía correcta (graves o agudos)
        energy_val = getattr(self.ctx, self.energy_attr)
        glUniform1f(self.u_bass_loc, energy_val)
        
        # Pasar uniforms de configuración
        glUniform1f(self.u_base_size_loc, float(cfg[self.keys["size"]]))
        glUniform1f(self.u_audio_scale_loc, float(cfg[self.keys["scale"]]))
        glUniform1f(self.u_brightness_loc, float(cfg[self.keys["bright"]]))
        glUniform1f(self.u_threshold_loc, float(cfg[self.keys["thresh"]]) / 100.0)
        glUniform1f(self.u_max_size_loc, float(cfg[self.keys["max_size"]]))
        glUniform1f(self.u_min_r_loc, min_r)
        glUniform1f(self.u_max_r_loc, max_r)
        glUniform3f(self.u_color_loc, *self.current_color)

        # Habilitar Point Size para que el shader pueda cambiar el tamaño
        glEnable(GL_PROGRAM_POINT_SIZE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE) # Aditivo para brillo
        
        glBindVertexArray(self.vao)
        glDrawArrays(GL_POINTS, 0, self.num_stars)
        glBindVertexArray(0)