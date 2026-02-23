// --- ui/ui.frag ---

#version 330 core

// Color de entrada interpolado desde el vertex shader
in vec4 v_color;
// Coordenadas UV interpoladas
in vec2 v_uv;

// Variable de salida para el color final del fragmento
out vec4 FragColor;

// Uniforms para texturizado
uniform sampler2D u_texture;
uniform bool u_use_texture;

void main()
{
    if (u_use_texture) {
        // Si hay textura activa, multiplicamos el color base (v_color) por el color muestreado de la textura.
        // texture(sampler, uv) devuelve el color en la posición UV.
        
        // Invertimos el eje Y de las coordenadas UV (1.0 - v_uv.y) para corregir la orientación
        // vertical, ya que las texturas de Pygame vienen invertidas respecto al sistema de OpenGL.
        vec2 flipped_uv = vec2(v_uv.x, 1.0 - v_uv.y);
        FragColor = v_color * texture(u_texture, flipped_uv); 
    } else {
        FragColor = v_color;
    }
}