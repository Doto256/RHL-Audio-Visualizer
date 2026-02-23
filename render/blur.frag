#version 330 core
out vec4 FragColor;
in vec2 v_uv;

uniform sampler2D u_image;
uniform bool u_horizontal;

// Pesos gaussianos para 5 muestras (optimizados para curva de campana)
uniform float weight[5] = float[] (0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);

void main()
{             
    vec2 tex_offset = 1.0 / textureSize(u_image, 0); // Tamaño de un texel
    vec3 result = texture(u_image, v_uv).rgb * weight[0]; // Contribución del centro
    
    if(u_horizontal)
    {
        for(int i = 1; i < 5; ++i)
        {
            result += texture(u_image, v_uv + vec2(tex_offset.x * i, 0.0)).rgb * weight[i];
            result += texture(u_image, v_uv - vec2(tex_offset.x * i, 0.0)).rgb * weight[i];
        }
    }
    else
    {
        for(int i = 1; i < 5; ++i)
        {
            result += texture(u_image, v_uv + vec2(0.0, tex_offset.y * i)).rgb * weight[i];
            result += texture(u_image, v_uv - vec2(0.0, tex_offset.y * i)).rgb * weight[i];
        }
    }
    FragColor = vec4(result, 1.0);
}
