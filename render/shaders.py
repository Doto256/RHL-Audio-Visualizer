# render/shaders.py
# ============================================================================
# Gestión de Shaders
# ============================================================================
# Carga, compila y enlaza los shaders de GLSL para crear un programa de GPU.
# ============================================================================

from OpenGL.GL import *
from GestorDeRecursos import resource_path

def load_shader_program(vertex_path, fragment_path):
    """
    Carga los shaders, los compila y los enlaza en un programa.
    Args:
        vertex_path (str): Ruta al archivo del vertex shader.
        fragment_path (str): Ruta al archivo del fragment shader.
    Returns:
        int: El ID del programa de shader enlazado.
    """
    # Procesar rutas con GestorDeRecursos para compatibilidad con PyInstaller
    vertex_path = resource_path(vertex_path)
    fragment_path = resource_path(fragment_path)

    # --- Cargar código fuente de los shaders ---
    try:
        with open(vertex_path, 'r') as f:
            vertex_src = f.read()
        with open(fragment_path, 'r') as f:
            fragment_src = f.read()
    except FileNotFoundError as e:
        print(f"Error: No se pudo encontrar el archivo de shader: {e}")
        return None

    # --- Compilar Vertex Shader ---
    vertex_shader = glCreateShader(GL_VERTEX_SHADER)
    glShaderSource(vertex_shader, vertex_src)
    glCompileShader(vertex_shader)
    # Comprobar errores de compilación
    if not glGetShaderiv(vertex_shader, GL_COMPILE_STATUS):
        error = glGetShaderInfoLog(vertex_shader).decode()
        print(f"Error de compilación en Vertex Shader:\n{error}")
        return None

    # --- Compilar Fragment Shader ---
    fragment_shader = glCreateShader(GL_FRAGMENT_SHADER)
    glShaderSource(fragment_shader, fragment_src)
    glCompileShader(fragment_shader)
    # Comprobar errores de compilación
    if not glGetShaderiv(fragment_shader, GL_COMPILE_STATUS):
        error = glGetShaderInfoLog(fragment_shader).decode()
        print(f"Error de compilación en Fragment Shader:\n{error}")
        return None

    # --- Enlazar Shaders en un Programa ---
    shader_program = glCreateProgram()
    glAttachShader(shader_program, vertex_shader)
    glAttachShader(shader_program, fragment_shader)
    glLinkProgram(shader_program)
    # Comprobar errores de enlazado
    if not glGetProgramiv(shader_program, GL_LINK_STATUS):
        error = glGetProgramInfoLog(shader_program).decode()
        print(f"Error de enlazado del programa de shaders:\n{error}")
        return None

    # --- Limpieza ---
    # Una vez enlazados, los shaders individuales ya no son necesarios.
    glDeleteShader(vertex_shader)
    glDeleteShader(fragment_shader)

    print("Shaders compilados y enlazados correctamente.")
    return shader_program