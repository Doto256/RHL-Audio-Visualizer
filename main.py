# main.py
# ============================================================================
# Punto de Entrada Principal
# ============================================================================
# Orquesta los módulos (Core, Audio, Render, UI) y ejecuta el loop principal.
# ============================================================================

import pygame
from pygame.locals import DOUBLEBUF, OPENGL, RESIZABLE, VIDEORESIZE, QUIT
import time

# Importar módulos propios
from core.context import Context
from core.time import TimeManager
from audio.engine import AudioEngine
from render.renderer import ModernRenderer
from ui.ui import UIManager

def main():
    # Inicialización básica
    pygame.init()
    
    # Solicitar un contexto OpenGL 3.3 Core Profile
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_STENCIL_SIZE, 8)

    # Crear contexto central
    ctx = Context()
    
    # Configurar ventana
    pygame.display.set_caption("RHL")
    pygame.display.set_mode((ctx.W, ctx.H), DOUBLEBUF | OPENGL | RESIZABLE)
    
    # Inicializar subsistemas inyectando el contexto
    ctx.time = TimeManager()
    ctx.ui = UIManager(ctx)
    ctx.audio = AudioEngine(ctx)
    
    # El único renderizador es el moderno
    ctx.renderer = ModernRenderer(ctx)
    
    # Iniciar motor de audio
    ctx.audio.start()
    
    # Variables para debug
    ultimo_print_debug = time.time()
    
    # Loop Principal
    while ctx.running:
        # 1. Gestión de Tiempo
        # Usamos FPS del menú o normal según estado
        fps_target = ctx.ui.config["FPS_MENU"] if (ctx.ui.modo_seleccion or ctx.ui.menu_config_activo) else ctx.ui.config["FPS_NORMAL"]
        dt = ctx.time.tick(fps_target)
        
        # 2. Procesamiento de Eventos
        for evt in pygame.event.get():
            if evt.type == QUIT:
                ctx.running = False
            elif evt.type == VIDEORESIZE:
                ctx.W, ctx.H = evt.w, evt.h
                pygame.display.set_mode((evt.w, evt.h), DOUBLEBUF | OPENGL | RESIZABLE)
                ctx.renderer.resize(evt.w, evt.h)
            else:
                # Delegar eventos a UI
                ctx.ui.procesar_evento(evt)
        
        # Actualización continua de UI (teclas mantenidas)
        ctx.ui.actualizar_continuo()
        
        # 3. Renderizado
        # Limpiamos la pantalla una sola vez al inicio del ciclo de renderizado
        from OpenGL.GL import glClear, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        if not ctx.ui.modo_seleccion:
            with ctx.profiler.region("render_3d"):
                # Renderizar escena 3D. El renderer ya no limpia la pantalla.
                ctx.renderer.render()

        with ctx.profiler.region("render_ui"):
            # Renderizar escena 3D
            ctx.ui.render()
        
        pygame.display.flip()
        
        # 4. Profiling
        ahora = time.time()
        if ahora - ultimo_print_debug >= 1.0:
            fps = ctx.time.get_fps()
            res = ctx.profiler.get_results()
            print(f"FPS: {fps:<5.1f} | 3D: {res.get('render_3d', 0):<5.2f}ms | UI: {res.get('render_ui', 0):<5.2f}ms | Bloom: {res.get('post_bloom', 0):<5.2f}ms")
            ultimo_print_debug = ahora

    # Limpieza
    if hasattr(ctx.ui.renderer, 'cleanup'):
        ctx.ui.renderer.cleanup()
    pygame.quit()
    print("🛑 Sistema finalizado.")

if __name__ == "__main__":
    main()
