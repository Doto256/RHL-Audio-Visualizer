// --- render/stars.vert ---

#version 330 core

// Atributos de entrada
layout (location = 0) in vec3 a_pos;

// Uniforms (Variables globales)
uniform mat4 u_projection;
uniform mat4 u_view;
uniform float u_bass_energy; // Energía de graves (0.0 a 1.0)
uniform float u_base_size;   // Tamaño base desde UI
uniform float u_audio_scale; // Factor de escala por audio
uniform float u_threshold;   // Umbral mínimo de energía para reaccionar
uniform float u_min_radius;  // Radio mínimo para visibilidad
uniform float u_max_radius;  // Radio máximo para visibilidad
uniform float u_max_size;    // Tamaño máximo permitido

// Salida al Fragment Shader
out float v_bass_energy;
out float v_visible;

void main() {
    // Calcular posición en espacio de clip
    gl_Position = u_projection * u_view * vec4(a_pos, 1.0);

    // --- Cálculo de Tamaño Dinámico ---
    // 1. Tamaño base
    float base_size = u_base_size; 
    // 2. Perspectiva: Inversamente proporcional a la profundidad (gl_Position.w)
    float perspective_scale = base_size / gl_Position.w;
    // 3. Reactividad al Audio: Crece con los graves
    float energy_reaction = max(0.0, u_bass_energy - u_threshold);
    float audio_scale = 1.0 + energy_reaction * u_audio_scale;

    float calculated_size = perspective_scale * audio_scale;
    gl_PointSize = min(calculated_size, u_max_size);

    // Pasar la energía al fragment shader para el brillo
    v_bass_energy = u_bass_energy;
    
    // Filtrado por radio (Cilindro) para separar capas
    float radius = length(a_pos.xy);
    v_visible = (radius >= u_min_radius && radius <= u_max_radius) ? 1.0 : 0.0;
}