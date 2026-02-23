// --- render/tunnel.vert ---

#version 330 core

// --- Atributos de Vértice ---
// Datos que vienen del VBO para cada vértice individual.
// 'location = 0' corresponde al primer puntero de atributos configurado en Python (posición).
layout (location = 0) in vec3 a_pos;
// 'location = 1' corresponde al segundo (información para el color).
layout (location = 1) in vec3 a_color_info; // (hue_base, t, intensidad)

// --- Uniforms ---
// Variables globales que se envían desde Python y son iguales para todos los vértices en un ciclo de dibujado.
uniform mat4 u_projection; // Matriz para transformar de coordenadas de vista a coordenadas de recorte (perspectiva).
uniform mat4 u_view;       // Matriz para transformar de coordenadas de mundo a coordenadas de vista (cámara).

// --- Salidas ---
// Variables que se pasan al siguiente paso del pipeline (el Fragment Shader).
// Se interpolarán para cada fragmento.
out vec3 v_color_info;

void main()
{
    // Pasamos la información de color que recibimos como atributo directamente al fragment shader.
    v_color_info = a_color_info;

    // gl_Position es una variable de salida especial que contiene la posición final del vértice
    // en el "espacio de recorte". Se calcula multiplicando las matrices por la posición original.
    // El orden es importante: Posición -> Vista -> Proyección.
    gl_Position = u_projection * u_view * vec4(a_pos, 1.0);

    // gl_PointSize define el tamaño en píxeles de los puntos que se dibujan (si el modo es GL_POINTS).
    // Hacemos que los puntos más lejanos (Z más negativo) se vean más pequeños. Usamos gl_Position.w que contiene la distancia.
    gl_PointSize = max(1.5, 15.0 / gl_Position.w);
}