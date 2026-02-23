#version 330 core

in vec2 v_uv;
in vec3 v_normal;

uniform sampler2D u_texture;
uniform int u_use_texture;

out vec4 FragColor;

void main() {
    // --- FASE 2: Iluminación Difusa (Lambert) ---
    
    // 1. Color Base
    vec4 base_color;
    if (u_use_texture == 1) {
        base_color = texture(u_texture, v_uv);
    } else {
        base_color = vec4(1.0, 0.0, 1.0, 1.0); // Rosa debug
    }
    
    // 2. Cálculo de Luz
    vec3 light_dir = normalize(vec3(0.5, 1.0, 0.8)); // Luz desde arriba-derecha
    vec3 norm = normalize(v_normal);
    
    float diff = max(dot(norm, light_dir), 0.0);
    float ambient = 0.4;
    
    // 3. Composición (Clamp para evitar blanco absoluto)
    vec3 lighting = min(vec3(ambient + diff), vec3(1.0));
    FragColor = vec4(base_color.rgb * lighting, base_color.a);
}
