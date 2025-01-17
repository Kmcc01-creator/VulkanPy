from dataclasses import dataclass
import numpy as np
from src.vertex import Vertex

@dataclass
class Transform:
    position: np.ndarray
    rotation: np.ndarray
    scale: np.ndarray

import vulkan as vk

@dataclass
class Mesh:
    vertices: np.ndarray
    indices: np.ndarray

    def __post_init__(self):
        # This will be called after the object is created. We'll defer vertex buffer creation.
        pass

    def create_vertex_buffer(self, renderer):
        buffer_size = Vertex.sizeof() * len(self.vertices)

        staging_buffer, staging_buffer_memory = renderer.create_buffer(buffer_size, vk.VK_BUFFER_USAGE_TRANSFER_SRC_BIT, vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)

        data_ptr = vk.vkMapMemory(renderer.device, staging_buffer_memory, 0, buffer_size, 0)
        vk.ffi.memmove(data_ptr, Vertex.as_bytes(self.vertices), buffer_size)
        vk.vkUnmapMemory(renderer.device, staging_buffer_memory)

        self.vertex_buffer, self.vertex_buffer_memory = renderer.create_buffer(buffer_size, vk.VK_BUFFER_USAGE_TRANSFER_DST_BIT | vk.VK_BUFFER_USAGE_VERTEX_BUFFER_BIT, vk.VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT)

        renderer.copy_buffer(staging_buffer, self.vertex_buffer, buffer_size)

        vk.vkDestroyBuffer(renderer.device, staging_buffer, None)
        vk.vkFreeMemory(renderer.device, staging_buffer_memory, None)

        self.vertex_count = len(self.vertices)

@dataclass
class Material:
    color: np.ndarray # For now, just a simple color
