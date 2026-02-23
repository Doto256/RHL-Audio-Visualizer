// --- ui/ui.vert ---

#version 330 core

// Atributo de entrada para la posición del vértice (2D)
layout (location = 0) in vec2 a_pos;
// Atributo de entrada para el color del vértice
layout (location = 1) in vec4 a_color;
// Atributo de entrada para coordenadas de textura (UV). Location 2 coincide con glVertexAttribPointer(2...)
layout (location = 2) in vec2 a_uv;

// Matriz de proyección ortográfica enviada desde Python
uniform mat4 u_proj;

// Variable de salida para pasar el color al fragment shader
out vec4 v_color;
// Variable de salida para pasar UV al fragment shader
out vec2 v_uv;

void main()
{
    // La posición final en el espacio de recorte se calcula multiplicando la matriz por la posición.
    // Se usa vec4 porque las matrices de transformación son 4x4.
    gl_Position = u_proj * vec4(a_pos.x, a_pos.y, 0.0, 1.0);
    
    // Pasamos el color del vértice directamente al fragment shader.
    v_color = a_color;
    // Pasamos las coordenadas UV interpoladas al fragment shader.
    v_uv = a_uv;
}