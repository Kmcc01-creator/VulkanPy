import ctypes
import glm

class UniformBufferObject(ctypes.Structure):
    _fields_ = [
        ("model", glm.mat4),
        ("view", glm.mat4),
        ("proj", glm.mat4),
    ]

class LightUBO(ctypes.Structure):
    _fields_ = [
        ("lightPos", glm.vec3),
        ("viewPos", glm.vec3),
        ("lightColor", glm.vec3),
    ]
