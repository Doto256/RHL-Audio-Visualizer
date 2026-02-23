#version 330 core

// FASE 1: Atributos de entrada
layout(location = 0) in vec3 a_pos;
layout(location = 1) in vec2 a_uv;
layout(location = 2) in vec3 a_normal; // Nueva entrada de normales

uniform mat4 u_projection;
uniform mat4 u_view;
uniform mat4 u_model;

out vec2 v_uv;
out vec3 v_normal;

void main() {
    // Transformación estándar de posición
    gl_Position = u_projection * u_view * u_model * vec4(a_pos, 1.0);
    
    v_uv = a_uv;
    
    // FASE 3: Normalización correcta
    // Usamos mat3(u_model) asumiendo escalado uniforme.
    // Para escalado no uniforme, usaríamos: mat3(transpose(inverse(u_model)))
    v_normal = mat3(u_model) * a_normal;
}
