import vulkan as vk
from vulkan_engine.buffer import UniformBuffer

class DescriptorSetLayout:
    def __init__(self, device):
        bindings = [
            vk.VkDescriptorSetLayoutBinding(
                binding=0,
                descriptorType=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
                descriptorCount=1,
                stageFlags=vk.VK_SHADER_STAGE_VERTEX_BIT,
            ),
            vk.VkDescriptorSetLayoutBinding(
                binding=1,
                descriptorType=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
                descriptorCount=1,
                stageFlags=vk.VK_SHADER_STAGE_FRAGMENT_BIT,
            )
        ]
        layout_info = vk.VkDescriptorSetLayoutCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
            bindingCount=len(bindings),
            pBindings=bindings,
        )
        self.layout = vk.vkCreateDescriptorSetLayout(device, layout_info, None)

    def destroy(self, device):
        vk.vkDestroyDescriptorSetLayout(device, self.layout, None)

def create_descriptor_pool(device, swapchain_images_count, resource_manager):
    pool_sizes = [
        vk.VkDescriptorPoolSize(type=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, descriptorCount=swapchain_images_count * 2)
    ]

    pool_create_info = vk.VkDescriptorPoolCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        maxSets=swapchain_images_count,
        poolSizeCount=len(pool_sizes),
        pPoolSizes=pool_sizes
    )

    descriptor_pool = vk.vkCreateDescriptorPool(device, pool_create_info, None)
    resource_manager.add_resource(descriptor_pool, "descriptor_pool", resource_manager.destroy_descriptor_pool)
    return descriptor_pool

def create_descriptor_sets(device, descriptor_pool, descriptor_set_layout, uniform_buffers, light_uniform_buffers):
    layouts = [descriptor_set_layout.layout] * len(uniform_buffers)
    alloc_info = vk.VkDescriptorSetAllocateInfo(
        sType=vk.VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        descriptorPool=descriptor_pool,
        descriptorSetCount=len(uniform_buffers),
        pSetLayouts=layouts,
    )
    descriptor_sets = vk.vkAllocateDescriptorSets(device, alloc_info)

    for i, (uniform_buffer, light_uniform_buffer) in enumerate(zip(uniform_buffers, light_uniform_buffers)):
        camera_buffer_info = vk.VkDescriptorBufferInfo(
            buffer=uniform_buffer.buffer,
            offset=0,
            range=uniform_buffer.size,
        )
        light_buffer_info = vk.VkDescriptorBufferInfo(
            buffer=light_uniform_buffer.buffer,
            offset=0,
            range=light_uniform_buffer.size,
        )

        write_descriptor_sets = [
            vk.VkWriteDescriptorSet(
                sType=vk.VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
                dstSet=descriptor_sets[i],
                dstBinding=0,
                dstArrayElement=0,
                descriptorCount=1,
                descriptorType=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
                pBufferInfo=[camera_buffer_info],
            ),
            vk.VkWriteDescriptorSet(
                sType=vk.VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
                dstSet=descriptor_sets[i],
                dstBinding=1,
                dstArrayElement=0,
                descriptorCount=1,
                descriptorType=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
                pBufferInfo=[light_buffer_info],
            )
        ]

        vk.vkUpdateDescriptorSets(device, len(write_descriptor_sets), write_descriptor_sets, 0, None)

    return descriptor_sets

def create_uniform_buffers(resource_manager, num_buffers):
    camera_uniform_buffers = []
    light_uniform_buffers = []
    for _ in range(num_buffers):
        camera_uniform_buffers.append(UniformBuffer(resource_manager, 4 * 4 * 4))  # mat4 model, view, proj
        light_uniform_buffers.append(UniformBuffer(resource_manager, 3 * 4 * 3))  # vec3 lightPos, viewPos, lightColor
    return camera_uniform_buffers, light_uniform_buffers
