# ui/ui_renderer.py
# ============================================================================
# Renderizador de UI (Modern OpenGL)
# ============================================================================
# Maneja el dibujo de primitivas 2D (rectángulos) usando shaders y buffers.
# Reemplaza completamente a glBegin/glEnd y glOrtho.
# ============================================================================

from OpenGL.GL import *
import numpy as np
import ctypes
import pyrr
from render import shaders # Reutilizamos el cargador de shaders

class UIRenderer:
    def __init__(self, ctx):
        self.ctx = ctx
        
        # Cargar shaders de UI
        self.rect_program = shaders.load_shader_program("ui/ui.vert", "ui/ui.frag")
        if not self.rect_program:
            raise RuntimeError("Error crítico: No se pudieron cargar los shaders de UI.")
        
        # Obtener la ubicación del uniform de la matriz de proyección
        self.u_proj_rect_loc = glGetUniformLocation(self.rect_program, "u_proj")
        self.u_texture_loc = glGetUniformLocation(self.rect_program, "u_texture")
        self.u_use_texture_loc = glGetUniformLocation(self.rect_program, "u_use_texture")
        
        # --- Configuración de Buffers (VAO/VBO) ---
        self.rect_vao = glGenVertexArrays(1)
        glBindVertexArray(self.rect_vao)
        
        self.rect_vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.rect_vbo)
        
        # Formato de vértice: [x, y, r, g, b, a, u, v] (8 floats)
        # Agregamos u, v para coordenadas de textura
        stride = 8 * 4 # 32 bytes (8 floats * 4 bytes)
        
        # Atributo 0: Posición (vec2)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        
        # Atributo 1: Color (vec4)
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(2 * ctypes.sizeof(GLfloat)))
        
        # Atributo 2: UV (vec2)
        # Offset = 6 floats (2 pos + 4 color) * 4 bytes = 24 bytes. Location = 2 en shader.
        glEnableVertexAttribArray(2)
        glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(6 * ctypes.sizeof(GLfloat)))

        # Desvincular para seguridad
        glBindVertexArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        
        # Lista temporal para acumular los vértices de un frame
        self.rect_vertices = []
        
        # Lista para elementos texturizados (texto, iconos)
        # Cada elemento es una tupla: (texture_id, vertices_list)
        self.textured_rects = []

    def add_rect(self, x, y, w, h, color):
        """
        Agrega un rectángulo (compuesto por dos triángulos) a la cola de renderizado.
        """
        r, g, b, a = color
        # UVs en 0.0 para rectángulos planos (no se usan en el shader si u_use_texture es false)
        u, v = 0.0, 0.0
        
        # Vértices: x, y, r, g, b, a, u, v
        v = [ 
            x, y, r, g, b, a, u, v,
            x + w, y, r, g, b, a, u, v,
            x, y + h, r, g, b, a, u, v,
            
            x + w, y, r, g, b, a, u, v,
            x + w, y + h, r, g, b, a, u, v,
            x, y + h, r, g, b, a, u, v 
        ]
        self.rect_vertices.extend(v)

    def draw_texture_rect(self, texture_id, x, y, w, h, color=(1.0, 1.0, 1.0, 1.0)):
        """
        Agrega un rectángulo texturizado a la cola.
        """
        r, g, b, a = color
        # Coordenadas UV completas (0,0 a 1,1) para mapear la textura entera al rectángulo.
        # (0,0) es la esquina superior izquierda de la textura en OpenGL (usualmente),
        # pero depende de cómo se cargue la imagen. Pygame carga de arriba a abajo.
        
        # Vértices: x, y, r, g, b, a, u, v
        v = [
            x, y,         r, g, b, a, 0.0, 0.0,  # Arriba-Izquierda
            x + w, y,     r, g, b, a, 1.0, 0.0,  # Arriba-Derecha
            x, y + h,     r, g, b, a, 0.0, 1.0,  # Abajo-Izquierda
            
            x + w, y,     r, g, b, a, 1.0, 0.0,  # Arriba-Derecha
            x + w, y + h, r, g, b, a, 1.0, 1.0,  # Abajo-Derecha
            x, y + h,     r, g, b, a, 0.0, 1.0   # Abajo-Izquierda
        ]
        
        # Agregamos a la lista de texturizados
        self.textured_rects.append((texture_id, v))

    def render(self):
        """Dibuja toda la geometría de UI acumulada en el frame."""
        # --- Configuración general de renderizado 2D ---
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_DEPTH_TEST)
        
        proj_matrix = pyrr.matrix44.create_orthogonal_projection(0, self.ctx.W, self.ctx.H, 0, -1, 1, dtype=np.float32)

        # Usamos el programa único de UI
        glUseProgram(self.rect_program)
        glUniformMatrix4fv(self.u_proj_rect_loc, 1, GL_FALSE, proj_matrix)
        
        # --- FASE 1: Dibujar Rectángulos Planos (Sin Textura) ---
        if self.rect_vertices:
            # Desactivar uso de textura en shader
            glUniform1i(self.u_use_texture_loc, 0)
            
            glBindVertexArray(self.rect_vao)
            glBindBuffer(GL_ARRAY_BUFFER, self.rect_vbo)
            vertex_data = np.array(self.rect_vertices, dtype=np.float32)
            glBufferData(GL_ARRAY_BUFFER, vertex_data.nbytes, vertex_data, GL_DYNAMIC_DRAW)
            # 8 floats por vértice
            glDrawArrays(GL_TRIANGLES, 0, len(vertex_data) // 8)

        # --- FASE 2: Dibujar Elementos Texturizados (Texto) ---
        if self.textured_rects:
            # Activar uso de textura
            glUniform1i(self.u_use_texture_loc, 1)
            # Indicar que usamos la unidad de textura 0
            glUniform1i(self.u_texture_loc, 0)
            glActiveTexture(GL_TEXTURE0)
            
            # Reutilizamos el mismo VAO/VBO porque el formato es idéntico
            glBindVertexArray(self.rect_vao)
            glBindBuffer(GL_ARRAY_BUFFER, self.rect_vbo)
            
            for tex_id, vertices in self.textured_rects:
                glBindTexture(GL_TEXTURE_2D, tex_id)
                v_data = np.array(vertices, dtype=np.float32)
                # Subimos y dibujamos uno por uno (simple batching)
                glBufferData(GL_ARRAY_BUFFER, v_data.nbytes, v_data, GL_DYNAMIC_DRAW)
                glDrawArrays(GL_TRIANGLES, 0, len(v_data) // 8)

        # --- Limpieza del frame ---
        glBindVertexArray(0)
        self.rect_vertices = []
        self.textured_rects = []

    def cleanup(self):
        """Libera los recursos de OpenGL."""
        glDeleteProgram(self.rect_program)
        glDeleteVertexArrays(1, [self.rect_vao])
        glDeleteBuffers(1, [self.rect_vbo])