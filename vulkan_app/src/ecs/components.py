from dataclasses import dataclass
import numpy as np
from src.vertex import Vertex
from src.object_loader import load_obj
import vulkan as vk

@dataclass
class Transform:
    position: np.ndarray
    rotation: np.ndarray
    scale: np.ndarray

@dataclass
class Mesh:
    vertices: np.ndarray
    indices: np.ndarray
    vertex_buffer: vk.VkBuffer = None
    vertex_buffer_memory: vk.VkDeviceMemory = None
    vertex_count: int = 0

    def create_vertex_buffer(self, resource_manager, filepath):
        self.vertices, self.indices = load_obj(filepath)
        self.vertex_buffer, self.vertex_buffer_memory, self.vertex_count = resource_manager.create_vertex_buffer(self.vertices)

@dataclass
class Material:
    albedo: np.ndarray  # RGB color
    metallic: float
    roughness: float
    ao: float  # Ambient Occlusion

@dataclass
class Camera:
    position: np.ndarray = np.array([0.0, 0.0, -2.0])
    target: np.ndarray = np.array([0.0, 0.0, 0.0])
    up: np.ndarray = np.array([0.0, 1.0, 0.0])
    fov: float = 45.0
    aspect: float = 16.0 / 9.0
    near: float = 0.1
    far: float = 100.0

@dataclass
class Light:
    position: np.ndarray
    color: np.ndarray
    intensity: float

@dataclass
class Shader:
    vertex_shader: str
    fragment_shader: str
    pipeline: vk.VkPipeline = None
