import vulkan as vk

from vulkan_engine.buffer import UniformBuffer

def create_descriptor_pool(device, descriptor_set_layout):
    pool_sizes = []
    pool_sizes.append(vk.VkDescriptorPoolSize(type=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, descriptorCount=1))

    pool_create_info = vk.VkDescriptorPoolCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        maxSets=1,  # One set for now
        poolSizeCount=len(pool_sizes),
        pPoolSizes=pool_sizes
    )

    return vk.vkCreateDescriptorPool(device, pool_create_info, None)


def create_descriptor_sets(device, descriptor_pool, descriptor_set_layout, uniform_buffers):
    layouts = [descriptor_set_layout] * len(uniform_buffers)
    alloc_info = vk.VkDescriptorSetAllocateInfo(
        sType=vk.VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        descriptorPool=descriptor_pool,
        descriptorSetCount=len(uniform_buffers),
        pSetLayouts=layouts,
    )
    descriptor_sets = vk.vkAllocateDescriptorSets(device, alloc_info)

    for i, uniform_buffer in enumerate(uniform_buffers):
        buffer_info = vk.VkDescriptorBufferInfo(
            buffer=uniform_buffer.buffer,
            offset=0,
            range=uniform_buffer.size,
        )

        write_descriptor_sets = [vk.VkWriteDescriptorSet(
            sType=vk.VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
            dstSet=descriptor_sets[i],
            dstBinding=0,
            dstArrayElement=0,
            descriptorCount=1,
            descriptorType=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
            pBufferInfo=[buffer_info],
        )]

        vk.vkUpdateDescriptorSets(device, len(write_descriptor_sets), write_descriptor_sets, 0, None)

    return descriptor_sets


def create_uniform_buffers(renderer, num_buffers):
    uniform_buffers = []
    for _ in range(num_buffers):
        uniform_buffers.append(UniformBuffer(renderer, 4 * 4 * 4)) # mat4 size
    return uniform_buffers
