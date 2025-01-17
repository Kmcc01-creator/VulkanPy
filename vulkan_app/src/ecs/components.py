from dataclasses import dataclass
import numpy as np
from src.vertex import Vertex

@dataclass
class Transform:
    position: np.ndarray
    rotation: np.ndarray
    scale: np.ndarray

from src.object_loader import load_obj # Import the load_obj function
import vulkan as vk

@dataclass
class Mesh:
    vertices: np.ndarray
    indices: np.ndarray

    def __post_init__(self):
        # This will be called after the object is created. We'll defer vertex buffer creation.
        pass

    def create_vertex_buffer(self, resource_manager, filepath): # Add filepath argument
        self.vertices, self.indices = load_obj(filepath) # Load vertices and indices from file

        self.vertex_buffer, self.vertex_buffer_memory, self.vertex_count = resource_manager.create_vertex_buffer(self.vertices)


@dataclass
class Material:
    color: np.ndarray # For now, just a simple color

@dataclass
class Camera:
    position: np.ndarray = np.array([0.0, 0.0, -2.0])
    target: np.ndarray = np.array([0.0, 0.0, 0.0])
    up: np.ndarray = np.array([0.0, 1.0, 0.0])
