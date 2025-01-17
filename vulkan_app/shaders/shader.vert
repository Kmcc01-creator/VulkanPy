#version 450

layout(binding = 0) uniform UniformBufferObject {
    mat4 model;
    mat4 view;
    mat4 proj;
} ubo;

layout(location = 0) in vec3 a_position;
layout(location = 1) in vec3 a_color; // Added color input

void main() {
    gl_Position = ubo.proj * ubo.view * ubo.model * vec4(a_position, 1.0);
}
