// --- render/tunnel.frag ---

#version 330 core

// --- Entradas ---
// Datos que vienen del Vertex Shader, interpolados para este fragmento específico.
in vec3 v_color_info; // (hue_base, t, intensidad)

// --- Uniforms ---
// Variables globales desde Python.
uniform float u_time;   // Tiempo global para animaciones.
uniform float u_energy; // Energía media del audio.

// --- Salida ---
// El color final del fragmento que se escribirá en la pantalla.
out vec4 FragColor;

// --- Función para convertir HSV a RGB ---
// GLSL no tiene una función nativa para esto, así que la implementamos.
vec3 hsv2rgb(vec3 c)
{
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main()
{
    // --- Cálculo del Color ---
    // Recreamos la lógica de color del renderizador legacy.
    
    // 1. Extraemos los datos que nos pasó el vertex shader.
    float hue_base = v_color_info.x; // Base del matiz (depende de la posición en el espectro).
    float t = v_color_info.y;        // Posición en la profundidad del túnel (0=lejos, 1=cerca).
    float intensity = v_color_info.z; // Intensidad del audio para este punto.

    // 2. Calculamos el matiz final, animándolo con el tiempo y la profundidad.
    float hue = mod(hue_base + t * 0.5 + u_time * 0.05, 1.0);

    // 3. Definimos la saturación y el brillo. El brillo aumenta con la intensidad del punto y la energía general.
    float saturation = 1.0;
    float value = clamp(0.5 + intensity * 1.5 + u_energy * 0.5, 0.5, 1.0);

    // 4. Convertimos de HSV a RGB.
    vec3 rgb_color = hsv2rgb(vec3(hue, saturation, value));

    // --- Forma Circular ---
    // gl_PointCoord nos da la coordenada (0,0 a 1,1) dentro del punto actual.
    // Calculamos la distancia desde el centro (0.5, 0.5).
    float dist = distance(gl_PointCoord, vec2(0.5));

    // Si estamos fuera del radio 0.5, descartamos el fragmento para recortar el cuadrado en un círculo.
    if (dist > 0.5) discard;

    // Suavizado (Anti-aliasing): Desvanecemos suavemente el borde del círculo entre el radio 0.3 y 0.5.
    float circle_alpha = 1.0 - smoothstep(0.3, 0.5, dist);

    // 5. Calculamos la opacidad (alpha). Los puntos más lejanos son más transparentes.
    // Combinamos la transparencia por profundidad (1.0 - t) con la forma circular suavizada.
    float alpha = circle_alpha;

    // 6. Asignamos el color final al fragmento.
    FragColor = vec4(rgb_color, alpha);
}