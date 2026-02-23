// --- render/stars.frag ---

#version 330 core

in float v_bass_energy;
in float v_visible;
uniform float u_brightness; // Factor de brillo desde UI
uniform vec3 u_color;       // Color base de la estrella
out vec4 FragColor;

void main() {
    // Si la energía es prácticamente nula (silencio), ocultar la estrella completamente.
    if (v_bass_energy < 0.001) discard;

    // Descartar si está fuera del rango de radio definido para esta capa
    if (v_visible < 0.5) discard;

    // --- Forma Redonda ---
    // gl_PointCoord va de (0,0) a (1,1) dentro del punto.
    // Calculamos la distancia al centro (0.5, 0.5).
    vec2 coord = gl_PointCoord - vec2(0.5);
    float dist = length(coord);

    // Descartar píxeles fuera del círculo (radio 0.5)
    if (dist > 0.5) discard;

    // Suavizar bordes (antialiasing simple)
    float alpha = 1.0 - smoothstep(0.4, 0.5, dist);

    // --- Brillo y Resplandor ---
    // Color base blanco azulado
    vec3 base_color = u_color;
    // Factor de brillo: base tenue (0.3) + destello por graves (hasta 5.0x)
    float brightness = 0.3 + v_bass_energy * u_brightness;

    FragColor = vec4(base_color * brightness, alpha);
}