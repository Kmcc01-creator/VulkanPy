import vulkan as vk

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
