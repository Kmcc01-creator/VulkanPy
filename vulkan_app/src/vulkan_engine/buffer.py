import vulkan as vk
import numpy as np
from pyglm import mat4

import vulkan as vk

def create_buffer(device, physical_device, size, usage, properties):
    buffer_create_info = vk.VkBufferCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
        size=size,
        usage=usage,
        sharingMode=vk.VK_SHARING_MODE_EXCLUSIVE,
    )

    buffer = vk.vkCreateBuffer(device, buffer_create_info, None)

    mem_requirements = vk.vkGetBufferMemoryRequirements(device, buffer)

    mem_properties = vk.vkGetPhysicalDeviceMemoryProperties(physical_device)
    memory_type_index = -1
    for i in range(mem_properties.memoryTypeCount):
        if (mem_requirements.memoryTypeBits & (1 << i)) and (mem_properties.memoryTypes[i].propertyFlags & properties) == properties:
            memory_type_index = i
            break

    if memory_type_index == -1:
        raise Exception("Failed to find suitable memory type for buffer.")

    mem_alloc_info = vk.VkMemoryAllocateInfo(
        sType=vk.VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
        allocationSize=mem_requirements.size,
        memoryTypeIndex=memory_type_index,
    )

    buffer_memory = vk.vkAllocateMemory(device, mem_alloc_info, None)
    vk.vkBindBufferMemory(device, buffer, buffer_memory, 0)

    return buffer, buffer_memory


class UniformBuffer:
    def __init__(self, renderer, size):
        self.renderer = renderer
        self.size = size
        self.buffer, self.buffer_memory = self.create_buffer()

    def create_buffer(self):
        return create_buffer(self.renderer.device, self.renderer.physical_device, self.size, vk.VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT, vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)

    def update(self, data):
        data_ptr = vk.vkMapMemory(self.renderer.device, self.buffer_memory, 0, self.size, 0)
        vk.ffi.memmove(data_ptr, data.astype(np.float32).tobytes(), self.size) # Assuming data is a numpy array
        vk.vkUnmapMemory(self.renderer.device, self.buffer_memory)
