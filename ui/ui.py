# ui/ui.py
# ============================================================================
# Interfaz de Usuario y Configuración
# ============================================================================
# Maneja el menú de configuración (sliders, pestañas) y el menú de selección
# de micrófonos. Contiene el estado de configuración.
# ============================================================================

import pygame
from OpenGL.GL import *
import time
from .ui_renderer import UIRenderer
from .horizontal_scroll import HorizontalScroll

def hex_to_rgb_float(hex_color):
    """Convierte un color hexadecimal #RRGGBB a una tupla (r, g, b) de floats 0.0-1.0."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        raise ValueError("El color hexadecimal debe tener el formato #RRGGBB")
    return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))

# Presets definidos en formato hexadecimal para mayor legibilidad
PALETAS_HEX = [
    ("Amarillo", "#FFFFFF", "#FFE600"),
    ("Verde", "#FFFFFF", "#15FF00"), 
    ("Cian", "#FFFFFF", "#00FFFF"), 
    ("Azul", "#FFFFFF", "#0011FF"),
    ("Rosa", "#FFFFFF", "#F700FF"),
    ("Rojo", "#FFFFFF", "#FF0000"),
    ("Naranja", "#FFFFFF", "#FF9100"),
]
# Convertimos los colores hexadecimales a tuplas de floats (0.0-1.0)
# que es el formato que OpenGL entiende.
PALETAS = [
    (nombre, hex_to_rgb_float(color1), hex_to_rgb_float(color2))
    for nombre, color1, color2 in PALETAS_HEX
]

PRESET_RABBIT_HOLE = {
    "gain_min": 0.3, "gain_max": 2.0,
    "tunel_vueltas": 50, "z_near": 10.0, "z_far": -20, "num_dots": 50,
    "NUM_PARTICULAS": 200, "TAMANO_BASE_PARTICULA": 10, "ESCALA_POR_INTENSIDAD": 100,
    "FACTOR_BRILLO_PARTICULAS": 5.0, "UMBRAL_INTENSIDAD_tamaño_particulas": 70,
    "MAX_SIZE_PARTICULA": 10,
    "velmin_particulas": 30, "velmax_particulas": 50,
    #platos
    "NUM_PLATOS": 200, "TAMANO_BASE_PLATO": 10, "ESCALA_INTENSIDAD_PLATO": 100,
    "FACTOR_BRILLO_PLATO": 20.0, "UMBRAL_INTENSIDAD_PLATO": 4.81,
    "MAX_SIZE_PLATO": 10, "velmin_platos": 40, "velmax_platos": 70,
    # bloom
    "bloom_threshold": 0.0, "bloom_intensity": 5.0, "bloom_iterations": 20, "bloom_enabled": 1.0,
    # paleta
    "palette_index": 0,
    "palette_auto": 1.0, # Interpolacion activada por defecto
    # modelo
    "model_attack": 0.1, "model_decay": 0.1, "model_threshold": 0.0,
}

PRESET_SOFT = {
    "gain_min": 0.5, "gain_max": 1.5,
    "tunel_vueltas": 30, "z_near": 5.0, "z_far": -5, "num_dots": 30,
    "NUM_PARTICULAS": 50, "TAMANO_BASE_PARTICULA": 15, "ESCALA_POR_INTENSIDAD": 50,
    "FACTOR_BRILLO_PARTICULAS": 3.0, "UMBRAL_INTENSIDAD_tamaño_particulas": 40,
    "MAX_SIZE_PARTICULA": 100,
    "velmin_particulas": 10, "velmax_particulas": 30,
    "NUM_PLATOS": 20, "TAMANO_BASE_PLATO": 10, "ESCALA_INTENSIDAD_PLATO": 60,
    "FACTOR_BRILLO_PLATO": 4.0, "UMBRAL_INTENSIDAD_PLATO": 50,
    "MAX_SIZE_PLATO": 100, "velmin_platos": 20, "velmax_platos": 40,
    # bloom
    "bloom_threshold": 0.8, "bloom_intensity": 1.2, "bloom_iterations": 6, "bloom_enabled": 1.0,
    # paleta
    "palette_index": 2, # Calma por defecto en Soft
    "palette_auto": 1.0,
    # modelo
    "model_attack": 0.05, "model_decay": 0.02, "model_threshold": 10.0,
}

class TextureCache:
    """
    Gestiona la creación y caché de texturas de texto.
    Evita recrear texturas idénticas en cada frame.
    """
    def __init__(self):
        self.cache = {} # Clave: (texto, tamaño, color) -> Valor: (tex_id, w, h)
        self.font_cache = {} # Clave: tamaño -> objeto Font

    def get_font(self, size):
        if size not in self.font_cache:
            self.font_cache[size] = pygame.font.SysFont("Segoe UI", size, bold=True)
        return self.font_cache[size]

    def get_texture(self, text, size, color):
        # Normalizar color a tupla de enteros 0-255 para clave de caché
        color_key = (int(color[0]*255), int(color[1]*255), int(color[2]*255))
        key = (text, size, color_key)
        
        if key not in self.cache:
            # Crear textura si no existe
            font = self.get_font(size)
            # Renderizar texto en superficie pygame
            surf = font.render(text, True, color_key)
            
            # Convertir a textura OpenGL
            w, h = surf.get_size()
            data = pygame.image.tostring(surf, "RGBA", True)
            
            tex_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, tex_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
            
            self.cache[key] = (tex_id, w, h)
            
        return self.cache[key]

class UILayout:
    """
    Sistema de Layout Relativo.
    Calcula posiciones y dimensiones basadas en porcentajes de la pantalla (0.0 a 1.0)
    para garantizar que la UI escale correctamente en cualquier resolución.
    """
    def __init__(self, ctx):
        self.ctx = ctx
        
        # Constantes de diseño (en porcentajes)
        self.MARGIN_X = 0.05      # Margen izquierdo
        self.Y_START = 0.15       # Inicio vertical del contenido
        self.Y_SPACING = 0.1      # Espaciado entre opciones
        self.SLIDER_W = 0.3       # Ancho del slider
        self.SLIDER_H = 0.025     # Alto del slider
        self.TAB_W = 0.15         # Ancho de pestaña
        self.TAB_H = 0.05         # Alto de pestaña
        self.TAB_Y = 0.05         # Posición Y de pestañas

    def get_pos(self, x_pct, y_pct):
        """Convierte coordenadas relativas a absolutas (píxeles)."""
        return x_pct * self.ctx.W, y_pct * self.ctx.H

    def get_rect(self, x_pct, y_pct, w_pct, h_pct):
        """Devuelve un rectángulo (x, y, w, h) en píxeles."""
        return (
            x_pct * self.ctx.W,
            y_pct * self.ctx.H,
            w_pct * self.ctx.W,
            h_pct * self.ctx.H
        )

    def dim(self, w_pct, h_pct):
        """Devuelve dimensiones (w, h) en píxeles."""
        return w_pct * self.ctx.W, h_pct * self.ctx.H

class UIManager:
    def __init__(self, ctx):
        self.ctx = ctx
        self.layout = UILayout(ctx)
        self.modo_seleccion = True # True = Seleccionando Mic, False = Config/Visualizador
        self.menu_config_activo = False
        self.paletas = PALETAS # Referencia para acceso externo
        
        # Estado de configuración (copiado de configuracion.py)
        self.config = {
            "opcion_seleccionada": 0,
            "pestana_activa": 0,
            "mantener_derecha": False,
            "mantener_izquierda": False,
            "arrastrando": False,
            "slider_activo": None,
            # Valores por defecto
            **PRESET_RABBIT_HOLE,
            "FPS_MENU": 60,
            "FPS_NORMAL": 60,
        }
        
        self._ultimo_update = time.time()
        self.botones_mic = []
        self.seleccionado_idx = -1
        
        # Definición de opciones (simplificada para brevedad, estructura igual)
        self.opciones = [
            {"nombre": "Bajas", "clave": "gain_min", "min": 0.0, "max": 5.0, "paso": 0.1},
            {"nombre": "Altas", "clave": "gain_max", "min": 0.0, "max": 5.0, "paso": 0.1},
            # Pestaña Colores
            {"nombre": "Paleta", "clave": "palette_index", "min": 0, "max": len(PALETAS)-1, "paso": 1},
            {"nombre": "Interpolacion", "clave": "palette_auto", "min": 0, "max": 1, "paso": 1},
            # Pestaña Tunel
            {"nombre": "Vueltas", "clave": "tunel_vueltas", "min": 2, "max": 100, "paso": 1},
            {"nombre": "Z Near", "clave": "z_near", "min": -20, "max": 15, "paso": 1},
            {"nombre": "Z Far", "clave": "z_far", "min": -20, "max": 15, "paso": 1},
            {"nombre": "Puntos Tunel", "clave": "num_dots", "min": 1, "max": 100, "paso": 1},
            {"nombre": "FPS Menu", "clave": "FPS_MENU", "min": 10, "max": 60, "paso": 1},
            {"nombre": "FPS Visual", "clave": "FPS_NORMAL", "min": 10, "max": 120, "paso": 1},
            {"nombre": "Num Estrellas", "clave": "NUM_PARTICULAS", "min": 1, "max": 2000, "paso": 10},
            {"nombre": "Tam Base", "clave": "TAMANO_BASE_PARTICULA", "min": 1, "max": 800, "paso": 10},
            {"nombre": "Reactividad", "clave": "ESCALA_POR_INTENSIDAD", "min": 0, "max": 100, "paso": 0.5},
            {"nombre": "Brillo", "clave": "FACTOR_BRILLO_PARTICULAS", "min": 1, "max": 20, "paso": 0.5},
            {"nombre": "Umbral Audio", "clave": "UMBRAL_INTENSIDAD_tamaño_particulas", "min": 0, "max": 100, "paso": 1},
            {"nombre": "Max Tam", "clave": "MAX_SIZE_PARTICULA", "min": 10, "max": 1000, "paso": 10},
            {"nombre": "Vel Min", "clave": "velmin_particulas", "min": 1, "max": 100, "paso": 1},
            {"nombre": "Vel Max", "clave": "velmax_particulas", "min": 1, "max": 100, "paso": 1},
            # Opciones Estrellas Plato
            {"nombre": "Num Platos", "clave": "NUM_PLATOS", "min": 1, "max": 2000, "paso": 10},
            {"nombre": "Tam Plato", "clave": "TAMANO_BASE_PLATO", "min": 1, "max": 800, "paso": 10},
            {"nombre": "React Plato", "clave": "ESCALA_INTENSIDAD_PLATO", "min": 0, "max": 100, "paso": 0.5},
            {"nombre": "Brillo Plato", "clave": "FACTOR_BRILLO_PLATO", "min": 1, "max": 20, "paso": 0.5},
            {"nombre": "Umbral Plato", "clave": "UMBRAL_INTENSIDAD_PLATO", "min": 0, "max": 100, "paso": 1},
            {"nombre": "Max Tam P", "clave": "MAX_SIZE_PLATO", "min": 10, "max": 1000, "paso": 10},
            {"nombre": "Vel Min P", "clave": "velmin_platos", "min": 1, "max": 100, "paso": 1},
            {"nombre": "Vel Max P", "clave": "velmax_platos", "min": 1, "max": 100, "paso": 1},
            # Opciones Bloom
            {"nombre": "Bloom On/Off", "clave": "bloom_enabled", "min": 0, "max": 1, "paso": 1},
            {"nombre": "Bloom Thresh", "clave": "bloom_threshold", "min": 0.0, "max": 5.0, "paso": 0.1},
            {"nombre": "Bloom Inten", "clave": "bloom_intensity", "min": 0.0, "max": 5.0, "paso": 0.1},
            {"nombre": "Blur Iter", "clave": "bloom_iterations", "min": 2, "max": 20, "paso": 2},
            # Opciones Modelo
            {"nombre": "Ataque", "clave": "model_attack", "min": 0.01, "max": 1.0, "paso": 0.01},
            {"nombre": "Decaimiento", "clave": "model_decay", "min": 0.001, "max": 0.5, "paso": 0.001},
            {"nombre": "Umbral", "clave": "model_threshold", "min": 0.0, "max": 100.0, "paso": 1.0},
        ]
        self.claves_por_pestana = {
            0: ["gain_min", "gain_max", "FPS_MENU", "FPS_NORMAL"],
            1: ["palette_index", "palette_auto"],
            2: ["tunel_vueltas", "z_near", "z_far", "num_dots"],
            3: ["NUM_PARTICULAS", "TAMANO_BASE_PARTICULA", "ESCALA_POR_INTENSIDAD", "FACTOR_BRILLO_PARTICULAS", "UMBRAL_INTENSIDAD_tamaño_particulas", "MAX_SIZE_PARTICULA", "velmin_particulas", "velmax_particulas"],
            4: ["NUM_PLATOS", "TAMANO_BASE_PLATO", "ESCALA_INTENSIDAD_PLATO", "FACTOR_BRILLO_PLATO", "UMBRAL_INTENSIDAD_PLATO", "MAX_SIZE_PLATO", "velmin_platos", "velmax_platos"],
            5: ["bloom_enabled", "bloom_threshold", "bloom_intensity", "bloom_iterations"],
            6: ["model_attack", "model_decay", "model_threshold"],
        }
        
        # Inicialización del Renderizador Moderno
        self.renderer = UIRenderer(ctx)
        self.tex_cache = TextureCache()
        self.tab_scroll = HorizontalScroll()
        
        print("UIManager: Sistema de UI en GPU inicializado.")

    def obtener_opciones_pagina(self):
        claves = self.claves_por_pestana.get(self.config["pestana_activa"], [])
        return [op for op in self.opciones if op["clave"] in claves]

    def procesar_evento(self, evt):
        # Lógica de eventos para configuración y selección
        if self.modo_seleccion:
            self._procesar_seleccion(evt)
        elif self.menu_config_activo:
            self._procesar_config(evt)
        else:
            # Teclas globales
            if evt.type == pygame.KEYDOWN:
                if evt.key == pygame.K_m:
                    self.modo_seleccion = True
                    self.ctx.activo = False
                    self._crear_botones_mic()
                elif evt.key == pygame.K_ESCAPE:
                    self.menu_config_activo = True
                elif evt.key == pygame.K_p: # Alternar presets
                    # Lógica simple de toggle
                    if self.config["palette_index"] == PRESET_RABBIT_HOLE["palette_index"]:
                        self.config.update(PRESET_SOFT)
                        print("Preset: SOFT")
                    else:
                        self.config.update(PRESET_RABBIT_HOLE)
                        print("Preset: RABBIT HOLE")

    def _procesar_seleccion(self, evt):
        if evt.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            for boton in self.botones_mic:
                x, y, w, h = boton["rect"]
                if x <= mx <= x + w and y <= my <= y + h:
                    mics = self.ctx.audio.selected_mics
                    if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                        if boton["mic"] not in mics:
                            mics.append(boton["mic"])
                    else:
                        self.ctx.audio.set_devices([boton["mic"]])
                    
                    self.modo_seleccion = False
                    self.ctx.activo = True
                    # Limpiar texturas de botones
                    for b in self.botones_mic:
                        pass # glDeleteTextures([b["tex_id"]]) # Re-enable with texture renderer
                    self.botones_mic = []

    def _procesar_config(self, evt):
        if evt.type == pygame.KEYDOWN and evt.key == pygame.K_ESCAPE:
            self.menu_config_activo = False
            self.config["arrastrando"] = False
            self.config["slider_activo"] = None
            return
        
        # Lógica de navegación (simplificada)
        opciones = self.obtener_opciones_pagina()
        
        # Layout helpers
        L = self.layout
        
        idx = self.config["opcion_seleccionada"]
        if opciones:
            opcion = opciones[idx]
            clave = opcion["clave"]
        
        if evt.type == pygame.KEYDOWN:
            if evt.key == pygame.K_TAB:
                self.config["pestana_activa"] = (self.config["pestana_activa"] + 1) % 7
                self.config["opcion_seleccionada"] = 0
            elif not opciones: return
            elif evt.key == pygame.K_DOWN:
                self.config["opcion_seleccionada"] = (idx + 1) % len(opciones)
            elif evt.key == pygame.K_UP:
                self.config["opcion_seleccionada"] = (idx - 1) % len(opciones)
            elif evt.key == pygame.K_LEFT:
                self.config[clave] = max(opcion["min"], self.config[clave] - opcion["paso"])
            elif evt.key == pygame.K_RIGHT:
                self.config[clave] = min(opcion["max"], self.config[clave] + opcion["paso"])
            elif evt.key == pygame.K_a: self.config["mantener_izquierda"] = True
            elif evt.key == pygame.K_d: self.config["mantener_derecha"] = True
        elif evt.type == pygame.KEYUP:
            if evt.key in (pygame.K_a, pygame.K_d):
                self.config["mantener_izquierda"] = False
                self.config["mantener_derecha"] = False
        
        elif evt.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            
            # Layout helpers
            L = self.layout
            
            # Verificar clic en pestañas
            tabs = ["General", "Colores", "Tunel", "Estrellas", "Platos", "Bloom", "Modelo"]
            scroll_offset = self.tab_scroll.get_render_offset()
            
            for i in range(len(tabs)):
                tx, ty, tw, th = L.get_rect(L.MARGIN_X + i * L.TAB_W, L.TAB_Y, L.TAB_W, L.TAB_H)
                # Aplicar el offset del scroll a la detección de colisiones
                tx += scroll_offset
                if tx <= mx <= tx + tw and ty <= my <= ty + th:
                    self.config["pestana_activa"] = i
                    self.config["opcion_seleccionada"] = 0
                    return

            # Verificar clic en sliders
            for i, op in enumerate(opciones):
                y_pct = L.Y_START + i * L.Y_SPACING
                # Zona de interacción amplia
                sx, sy, sw, sh = L.get_rect(L.MARGIN_X, y_pct, 0.5, 0.08) 
                if sx <= mx <= sx + sw and sy <= my <= sy + sh:
                    self.config["opcion_seleccionada"] = i
                    self.config["arrastrando"] = True
                    self.config["slider_activo"] = i
                    self._actualizar_slider_mouse(mx, i)
                    break

        elif evt.type == pygame.MOUSEBUTTONUP:
            self.config["arrastrando"] = False
            self.config["slider_activo"] = None

        elif evt.type == pygame.MOUSEMOTION:
            if self.config["arrastrando"] and self.config["slider_activo"] is not None:
                mx, _ = pygame.mouse.get_pos()
                self._actualizar_slider_mouse(mx, self.config["slider_activo"])

        elif evt.type == pygame.MOUSEWHEEL:
            _, my = pygame.mouse.get_pos()
            # Si el mouse está en la zona superior (pestañas), aplicamos scroll
            if my < self.ctx.H * 0.2:
                self.tab_scroll.scroll(evt.y)

    def _actualizar_slider_mouse(self, mx, idx):
        opciones = self.obtener_opciones_pagina()
        if idx >= len(opciones): return
        op = opciones[idx]
        sx, _, sw, _ = self.layout.get_rect(self.layout.MARGIN_X, 0, self.layout.SLIDER_W, 0)
        frac = max(0.0, min(1.0, (mx - sx) / sw))
        self.config[op["clave"]] = op["min"] + frac * (op["max"] - op["min"])

    def actualizar_continuo(self):
        # Actualización continua de valores con teclas
        ahora = time.time()
        if ahora - self._ultimo_update < 0.05: return
        self._ultimo_update = ahora
        
        if not self.menu_config_activo: return
        opciones = self.obtener_opciones_pagina()
        if not opciones: return
        
        idx = self.config["opcion_seleccionada"]
        opcion = opciones[idx]
        clave = opcion["clave"]
        
        if self.config["mantener_izquierda"]:
            self.config[clave] = max(opcion["min"], self.config[clave] - opcion["paso"])
        if self.config["mantener_derecha"]:
            self.config[clave] = min(opcion["max"], self.config[clave] + opcion["paso"])

    def _crear_botones_mic(self):
        self.botones_mic = []
        mics = self.ctx.audio.get_devices()
        # Usar layout relativo para el menú de selección también
        _, _, boton_w, boton_h = self.layout.get_rect(0, 0, 0.6, 0.08)
        h_pantalla = self.ctx.H # Píxeles reales para cálculo vertical centrado
        espaciado = boton_h * 1.3
        inicio_y = (h_pantalla - len(mics) * espaciado) // 2
        
        for i, mic in enumerate(mics):
            x = (self.ctx.W - boton_w) // 2
            y = inicio_y + i * espaciado
            nombre = f"{mic.name} {'Loop' if mic.isloopback else ''}"
            # Guardamos el nombre para generar la textura al renderizar
            self.botones_mic.append({
                "mic": mic, "rect": [x, y, boton_w, boton_h],
                "nombre": nombre
            })

    def render(self):
        if self.modo_seleccion:
            self._render_seleccion()
        elif self.menu_config_activo:
            self._render_config()
        
        # Dibujar todo lo acumulado en este frame
        self.renderer.render()

    def _render_seleccion(self):
        # Dibujar botones
        if not self.botones_mic: self._crear_botones_mic()
        
        for boton in self.botones_mic:
            x, y, w, h = boton["rect"]
            self.renderer.add_rect(x, y, w, h, (0.4, 0.4, 0.4, 1.0))
            # Centrar texto (aproximado)
            # Usamos la caché para obtener la textura
            tex_id, tw, th = self.tex_cache.get_texture(boton["nombre"], 20, (1.0, 1.0, 1.0))
            # Dibujamos centrado verticalmente
            self.renderer.draw_texture_rect(tex_id, x + 10, y + (h - th)/2, tw, th, (1.0, 1.0, 1.0, 1.0))

    def _render_config(self):
        w, h = self.ctx.W, self.ctx.H
        L = self.layout
        
        # 1. Fondo semitransparente
        self.renderer.add_rect(0, 0, w, h, (0.0, 0.0, 0.0, 0.6))
        
        # 2. Pestañas
        tabs = ["General", "Colores", "Tunel", "Estrellas", "Platos", "Bloom", "Modelo"]
        
        # Calcular ancho total del contenido para el scroll
        tab_w_px = w * L.TAB_W
        margin_px = w * L.MARGIN_X
        total_width = margin_px + len(tabs) * tab_w_px + margin_px # Margen extra al final
        
        # Actualizar límites del scroll
        self.tab_scroll.update_limits(total_width, w)
        offset_x = self.tab_scroll.get_render_offset()

        for i, nombre in enumerate(tabs):
            tx, ty, tw, th = L.get_rect(L.MARGIN_X + i * L.TAB_W, L.TAB_Y, L.TAB_W, L.TAB_H)
            tx += offset_x # Aplicar desplazamiento visual
            
            # Optimización: No dibujar si está fuera de pantalla
            if tx + tw < 0 or tx > w: continue

            color = (0.0, 0.8, 1.0, 1.0) if i == self.config["pestana_activa"] else (0.4, 0.4, 0.4, 1.0)
            self.renderer.add_rect(tx, ty, tw, th, color)
            
            # Texto de pestaña
            tex_id, tw, th = self.tex_cache.get_texture(nombre, 18, (0.0, 0.0, 0.0))
            self.renderer.draw_texture_rect(tex_id, tx + (tw - tw)/2 + 10, ty + (th - th)/2 + 5, tw, th, (0.0, 0.0, 0.0, 1.0))

        # 2.1 Indicadores de Scroll (< >)
        if self.tab_scroll.should_show_left_arrow():
            tex_id, aw, ah = self.tex_cache.get_texture("<", 30, (1.0, 1.0, 0.0))
            self.renderer.add_rect(0, h * L.TAB_Y, 40, h * L.TAB_H, (0.0, 0.0, 0.0, 0.8)) # Fondo oscuro
            self.renderer.draw_texture_rect(tex_id, 10, h * L.TAB_Y + (h * L.TAB_H - ah)/2, aw, ah, (1.0, 1.0, 0.0, 1.0))

        if self.tab_scroll.should_show_right_arrow():
            tex_id, aw, ah = self.tex_cache.get_texture(">", 30, (1.0, 1.0, 0.0))
            self.renderer.add_rect(w - 40, h * L.TAB_Y, 40, h * L.TAB_H, (0.0, 0.0, 0.0, 0.8)) # Fondo oscuro
            self.renderer.draw_texture_rect(tex_id, w - 30, h * L.TAB_Y + (h * L.TAB_H - ah)/2, aw, ah, (1.0, 1.0, 0.0, 1.0))

        # 3. Sliders y Opciones
        opciones = self.obtener_opciones_pagina()
        for i, op in enumerate(opciones):
            y_pct = L.Y_START + i * L.Y_SPACING
            
            # Coordenadas base
            bx, by = L.get_pos(L.MARGIN_X, y_pct)
            sw, sh = L.dim(L.SLIDER_W, L.SLIDER_H)
            
            # Resaltar selección
            if i == self.config["opcion_seleccionada"]:
                # Borde (simulado con quad más grande detrás)
                pad = 4
                self.renderer.add_rect(bx - pad, by - pad, sw + 2*pad, sh + 30 + 2*pad, (1.0, 1.0, 0.0, 0.5))

            # Fondo del slider
            slider_y = by + 25
            self.renderer.add_rect(bx, slider_y, sw, sh, (0.3, 0.3, 0.3, 1.0))
            
            # Barra de valor
            val = self.config[op["clave"]]
            frac = (val - op["min"]) / (op["max"] - op["min"])
            self.renderer.add_rect(bx, slider_y, sw * frac, sh, (0.0, 0.8, 1.0, 1.0))

            # Texto del slider
            if op["clave"] == "palette_index":
                # Mostrar nombre de la paleta en lugar del número
                idx_paleta = int(val)
                texto = f"{op['nombre']}: {self.paletas[idx_paleta][0]}"
            else:
                texto = f"{op['nombre']}: {val:.2f}"
            
            tex_id, tw, th = self.tex_cache.get_texture(texto, 16, (1.0, 1.0, 1.0))
            self.renderer.draw_texture_rect(tex_id, bx, by, tw, th, (1.0, 1.0, 1.0, 1.0))
