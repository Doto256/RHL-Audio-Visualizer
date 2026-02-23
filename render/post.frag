#version 330 core
out vec4 FragColor;
in vec2 v_uv;

uniform sampler2D u_scene;
uniform sampler2D u_bloom;
uniform float u_bloom_intensity;

void main()
{ 
    vec3 scene = texture(u_scene, v_uv).rgb;
    vec3 bloom = texture(u_bloom, v_uv).rgb;
    
    // Mezcla aditiva: Escena + Bloom
    // (Opcional: Aquí se podría agregar Tone Mapping para controlar la exposición HDR)
    FragColor = vec4(scene + bloom * u_bloom_intensity, 1.0);
}
