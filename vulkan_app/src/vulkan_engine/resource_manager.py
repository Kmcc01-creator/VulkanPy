import vulkan as vk

class ResourceManager:
    def __init__(self, renderer):
        self.renderer = renderer
        self.device = renderer.device
        self.resources = []

    def add_resource(self, resource, resource_type, cleanup_function):
        self.resources.append((resource, resource_type, cleanup_function))

    def cleanup(self):
        for resource, resource_type, cleanup_function in reversed(self.resources):
            if resource is not None:  # Check if resource is not None
                cleanup_function(self.device, resource, None)

    def destroy_swapchain(self, swapchain):
        vk.vkDestroySwapchainKHR(self.device, swapchain, None)
        self.resources.remove((swapchain, "swapchain", self.destroy_swapchain)) # Remove from resources list

    def destroy_framebuffer(self, framebuffer):
        vk.vkDestroyFramebuffer(self.device, framebuffer, None)

    def destroy_pipeline(self, pipeline):
        vk.vkDestroyPipeline(self.device, pipeline, None)

    def destroy_pipeline_layout(self, pipeline_layout):
        vk.vkDestroyPipelineLayout(self.device, pipeline_layout, None)

    def destroy_render_pass(self, render_pass):
        vk.vkDestroyRenderPass(self.device, render_pass, None)

    def destroy_image_view(self, image_view):
        vk.vkDestroyImageView(self.device, image_view, None)

    def destroy_buffer(self, buffer):
        vk.vkDestroyBuffer(self.device, buffer, None)

    def free_memory(self, memory):
        vk.vkFreeMemory(self.device, memory, None)

    def destroy_descriptor_pool(self, descriptor_pool):
        vk.vkDestroyDescriptorPool(self.device, descriptor_pool, None)

    def destroy_descriptor_set_layout(self, descriptor_set_layout):
        vk.vkDestroyDescriptorSetLayout(self.device, descriptor_set_layout, None)

    def destroy_semaphore(self, semaphore):
        vk.vkDestroySemaphore(self.device, semaphore, None)

    def destroy_fence(self, fence):
        vk.vkDestroyFence(self.device, fence, None)

    def destroy_command_pool(self, command_pool):
        vk.vkDestroyCommandPool(self.device, command_pool, None)

    def create_buffer(self, size, usage, properties):
        buffer_create_info = vk.VkBufferCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
            size=size,
            usage=usage,
            sharingMode=vk.VK_SHARING_MODE_EXCLUSIVE,
        )

        buffer = vk.vkCreateBuffer(self.device, buffer_create_info, None)

        mem_requirements = vk.vkGetBufferMemoryRequirements(self.device, buffer)

        mem_properties = vk.vkGetPhysicalDeviceMemoryProperties(self.renderer.physical_device)
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

        buffer_memory = vk.vkAllocateMemory(self.device, mem_alloc_info, None)
        vk.vkBindBufferMemory(self.device, buffer, buffer_memory, 0)

        self.add_resource(buffer, "buffer", self.destroy_buffer)
        self.add_resource(buffer_memory, "memory", self.free_memory)

        return buffer, buffer_memory

    def create_vertex_buffer(self, vertices):
        buffer_size = Vertex.sizeof() * len(vertices)

        staging_buffer, staging_buffer_memory = self.create_buffer(buffer_size, vk.VK_BUFFER_USAGE_TRANSFER_SRC_BIT, vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)

        data_ptr = vk.vkMapMemory(self.device, staging_buffer_memory, 0, buffer_size, 0)
        vk.ffi.memmove(data_ptr, Vertex.as_bytes(vertices), buffer_size)
        vk.vkUnmapMemory(self.device, staging_buffer_memory)

        vertex_buffer, vertex_buffer_memory = self.create_buffer(buffer_size, vk.VK_BUFFER_USAGE_TRANSFER_DST_BIT | vk.VK_BUFFER_USAGE_VERTEX_BUFFER_BIT, vk.VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT)

        self.renderer.copy_buffer(staging_buffer, vertex_buffer, buffer_size)

        self.destroy_buffer(staging_buffer)
        self.free_memory(staging_buffer_memory)

        return vertex_buffer, vertex_buffer_memory, len(vertices)
