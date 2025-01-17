import vulkan as vk
import numpy as np
from pyglm import mat4



class UniformBuffer:
    def __init__(self, resource_manager, size):
        self.resource_manager = resource_manager
        self.size = size
        self.buffer, self.buffer_memory = self.create_buffer()


    def create_buffer(self):
        return self.resource_manager.create_buffer(self.size, vk.VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT, vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)

    def update(self, data):
        data_ptr = vk.vkMapMemory(self.resource_manager.device, self.buffer_memory, 0, self.size, 0)
        vk.ffi.memmove(data_ptr, data.astype(np.float32).tobytes(), self.size)
        vk.vkUnmapMemory(self.resource_manager.device, self.buffer_memory)
