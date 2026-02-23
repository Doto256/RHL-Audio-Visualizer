from OpenGL.GL import *
import numpy as np
import ctypes
from . import shaders

class PostProcessor:
    def __init__(self, ctx):
        self.ctx = ctx
        self.downscale = 4 # Resolución 1/4 para Bloom (Optimización)
        self.fbo = 0
        self.color_tex = 0
        self.depth_rbo = 0
        # --- Recursos para Bright Pass ---
        self.bright_fbo = 0
        self.bright_tex = 0
        # --- Recursos para Ping-Pong Blur ---
        self.pingpong_fbo = [0, 0]
        self.pingpong_tex = [0, 0]
        
        self.quad_vao = 0
        self.quad_vbo = 0
        self.program = None
        self.bright_program = None
        self.blur_program = None
        self.bloom_tex = 0 # Almacena el resultado del cálculo de bloom
        
        # Inicializar FBO y Texturas
        self.init_framebuffer(ctx.W, ctx.H)
        
        # Inicializar Quad de pantalla completa
        self.init_quad()
        
        # Cargar shaders de post-proceso
        self.program = shaders.load_shader_program("render/post.vert", "render/post.frag")
        if not self.program:
            raise RuntimeError("No se pudieron cargar los shaders de post-procesamiento.")
            
        self.u_scene_loc = glGetUniformLocation(self.program, "u_scene")
        self.u_bloom_loc = glGetUniformLocation(self.program, "u_bloom")
        self.u_bloom_intensity_loc = glGetUniformLocation(self.program, "u_bloom_intensity")
        
        # Cargar shader de Bright Pass
        self.bright_program = shaders.load_shader_program("render/post.vert", "render/bright_pass.frag")
        if not self.bright_program:
            raise RuntimeError("No se pudieron cargar los shaders de bright pass.")
        self.u_bright_scene_loc = glGetUniformLocation(self.bright_program, "u_scene")
        self.u_threshold_loc = glGetUniformLocation(self.bright_program, "u_threshold")
        
        # Cargar shader de Blur
        self.blur_program = shaders.load_shader_program("render/post.vert", "render/blur.frag")
        if not self.blur_program:
            raise RuntimeError("No se pudieron cargar los shaders de blur.")
        self.u_blur_image_loc = glGetUniformLocation(self.blur_program, "u_image")
        self.u_horizontal_loc = glGetUniformLocation(self.blur_program, "u_horizontal")

    def init_framebuffer(self, width, height):
        # Limpiar recursos si ya existen (para resize)
        if self.fbo:
            glDeleteFramebuffers(1, [self.fbo])
            glDeleteTextures(1, [self.color_tex])
            glDeleteRenderbuffers(1, [self.depth_rbo])
            glDeleteFramebuffers(1, [self.bright_fbo])
            glDeleteTextures(1, [self.bright_tex])
            glDeleteFramebuffers(2, self.pingpong_fbo)
            glDeleteTextures(2, self.pingpong_tex)

        # 1. Crear FBO
        self.fbo = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)

        # 2. Crear Textura de Color (RGBA16F para HDR)
        self.color_tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.color_tex)
        glTexImage2D(
            GL_TEXTURE_2D, 0, GL_RGBA16F,
            width, height, 0,
            GL_RGBA, GL_FLOAT, None
        )
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        
        glFramebufferTexture2D(
            GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
            GL_TEXTURE_2D, self.color_tex, 0
        )

        # 3. Crear Renderbuffer de Profundidad
        self.depth_rbo = glGenRenderbuffers(1)
        glBindRenderbuffer(GL_RENDERBUFFER, self.depth_rbo)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT, width, height)
        glFramebufferRenderbuffer(
            GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT,
            GL_RENDERBUFFER, self.depth_rbo
        )

        # Verificar estado
        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            print("⚠️ Error: Framebuffer no está completo.")
        
        # Dimensiones reducidas para Bloom
        bw = max(1, width // self.downscale)
        bh = max(1, height // self.downscale)
        
        # --- Crear FBO para Bright Pass ---
        self.bright_fbo = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, self.bright_fbo)
        
        self.bright_tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.bright_tex)
        glTexImage2D(
            GL_TEXTURE_2D, 0, GL_RGBA16F,
            bw, bh, 0,
            GL_RGBA, GL_FLOAT, None
        )
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.bright_tex, 0)
        
        # --- Crear FBOs para Ping-Pong ---
        self.pingpong_fbo = glGenFramebuffers(2)
        self.pingpong_tex = glGenTextures(2)
        
        for i in range(2):
            glBindFramebuffer(GL_FRAMEBUFFER, self.pingpong_fbo[i])
            glBindTexture(GL_TEXTURE_2D, self.pingpong_tex[i])
            glTexImage2D(
                GL_TEXTURE_2D, 0, GL_RGBA16F,
                bw, bh, 0,
                GL_RGBA, GL_FLOAT, None
            )
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.pingpong_tex[i], 0)

        glBindFramebuffer(GL_FRAMEBUFFER, 0)

    def init_quad(self):
        # Quad que cubre la pantalla en coordenadas normalizadas (-1 a 1)
        # Formato: x, y, u, v
        vertices = [
            -1.0,  1.0, 0.0, 1.0,
            -1.0, -1.0, 0.0, 0.0,
             1.0, -1.0, 1.0, 0.0,

            -1.0,  1.0, 0.0, 1.0,
             1.0, -1.0, 1.0, 0.0,
             1.0,  1.0, 1.0, 1.0
        ]
        data = np.array(vertices, dtype=np.float32)

        self.quad_vao = glGenVertexArrays(1)
        glBindVertexArray(self.quad_vao)
        
        self.quad_vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.quad_vbo)
        glBufferData(GL_ARRAY_BUFFER, data.nbytes, data, GL_STATIC_DRAW)

        stride = 4 * 4
        # Posición
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        # UV
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(8))
        
        glBindVertexArray(0)

    def resize(self, w, h):
        self.init_framebuffer(w, h)

    def bind(self):
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        glViewport(0, 0, self.ctx.W, self.ctx.H)

    def unbind(self):
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glViewport(0, 0, self.ctx.W, self.ctx.H)

    def calculate_bloom(self):
        """Calcula el mapa de bloom basado en el contenido actual del FBO."""
        glDisable(GL_BLEND)
        glDisable(GL_DEPTH_TEST)

        # Leer configuración de UI
        cfg = self.ctx.ui.config
        enabled = cfg.get("bloom_enabled", 1.0) > 0.5
        threshold = cfg.get("bloom_threshold", 1.0)
        iterations = int(cfg.get("bloom_iterations", 10))

        # Dimensiones
        w, h = self.ctx.W, self.ctx.H
        bw, bh = max(1, w // self.downscale), max(1, h // self.downscale)

        if enabled:
            with self.ctx.profiler.region("post_bloom"):
                # 1. Paso de Extracción de Brillo (Scene -> Bright FBO)
                glBindFramebuffer(GL_FRAMEBUFFER, self.bright_fbo)
                glViewport(0, 0, bw, bh) # Viewport reducido
                glClear(GL_COLOR_BUFFER_BIT)
                
                glUseProgram(self.bright_program)
                glActiveTexture(GL_TEXTURE0)
                glBindTexture(GL_TEXTURE_2D, self.color_tex) # Leemos la escena original
                glUniform1i(self.u_bright_scene_loc, 0)
                glUniform1f(self.u_threshold_loc, threshold)
                
                glBindVertexArray(self.quad_vao)
                glDrawArrays(GL_TRIANGLES, 0, 6)
                
                # 2. Blur Gaussiano (Ping-Pong)
                horizontal = True
                first_iteration = True
                amount = iterations
                
                glUseProgram(self.blur_program)
                glActiveTexture(GL_TEXTURE0)
                glViewport(0, 0, bw, bh) # Asegurar viewport reducido para el blur
                
                for i in range(amount):
                    glBindFramebuffer(GL_FRAMEBUFFER, self.pingpong_fbo[int(horizontal)])
                    glUniform1i(self.u_horizontal_loc, int(horizontal))
                    
                    # En la primera iteración leemos de bright_tex, luego del otro buffer de pingpong
                    if first_iteration:
                        glBindTexture(GL_TEXTURE_2D, self.bright_tex)
                    else:
                        glBindTexture(GL_TEXTURE_2D, self.pingpong_tex[int(not horizontal)])
                    
                    glBindVertexArray(self.quad_vao)
                    glDrawArrays(GL_TRIANGLES, 0, 6)
                    
                    horizontal = not horizontal
                    first_iteration = False
                
                glBindVertexArray(0)
                self.bloom_tex = self.pingpong_tex[int(not horizontal)]
        else:
            self.bloom_tex = self.pingpong_tex[0]

    def render(self):
        """Realiza la composición final a pantalla (Escena + Bloom)."""
        glDisable(GL_BLEND)
        glDisable(GL_DEPTH_TEST)

        cfg = self.ctx.ui.config
        enabled = cfg.get("bloom_enabled", 1.0) > 0.5
        intensity = cfg.get("bloom_intensity", 1.0)
        
        if not enabled:
            intensity = 0.0

        # 3. Composición Final (Scene + Bloom)
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glViewport(0, 0, self.ctx.W, self.ctx.H) # Restaurar viewport completo
        
        glUseProgram(self.program)
        
        # Textura 0: Escena Original
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.color_tex)
        glUniform1i(self.u_scene_loc, 0)
        
        # Textura 1: Bloom (Resultado del Blur)
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, self.bloom_tex)
        glUniform1i(self.u_bloom_loc, 1)
        
        # Intensidad del efecto
        glUniform1f(self.u_bloom_intensity_loc, intensity) 
        
        glBindVertexArray(self.quad_vao)
        glDrawArrays(GL_TRIANGLES, 0, 6)
        glBindVertexArray(0)
