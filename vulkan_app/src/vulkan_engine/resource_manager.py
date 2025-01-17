import vulkan as vk
from src.vertex import Vertex

import logging

logger = logging.getLogger(__name__)

class ResourceManager:
    def __init__(self, renderer):
        self.renderer = renderer
        self.device = renderer.device
        self.resources = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup()

    def add_resource(self, resource, resource_type, cleanup_function):
        self.resources.append((resource, resource_type, cleanup_function))

    def cleanup(self):
        for resource, resource_type, cleanup_function in reversed(self.resources):
            if resource is not None:
                try:
                    cleanup_function(self.device, resource, None)
                except Exception as e:
                    logger.error(f"Failed to clean up {resource_type}: {e}")
        self.resources.clear()

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
        try:
            buffer_create_info = vk.VkBufferCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
                size=size,
                usage=usage,
                sharingMode=vk.VK_SHARING_MODE_EXCLUSIVE,
            )

            buffer = vk.vkCreateBuffer(self.device, buffer_create_info, None)
            mem_requirements = vk.vkGetBufferMemoryRequirements(self.device, buffer)
            memory_type_index = self.find_memory_type(mem_requirements.memoryTypeBits, properties)

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
        except vk.VkError as e:
            logger.error(f"Failed to create buffer: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during buffer creation: {e}")
            raise

    def find_memory_type(self, type_filter, properties):
        mem_properties = vk.vkGetPhysicalDeviceMemoryProperties(self.renderer.physical_device)
        for i in range(mem_properties.memoryTypeCount):
            if (type_filter & (1 << i)) and (mem_properties.memoryTypes[i].propertyFlags & properties) == properties:
                return i
        raise Exception("Failed to find suitable memory type for buffer.")

    def create_vertex_buffer(self, vertices):
        buffer_size = Vertex.sizeof() * len(vertices)

        staging_buffer, staging_buffer_memory = self.create_buffer(
            buffer_size, 
            vk.VK_BUFFER_USAGE_TRANSFER_SRC_BIT, 
            vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT
        )

        try:
            data_ptr = vk.vkMapMemory(self.device, staging_buffer_memory, 0, buffer_size, 0)
            vk.ffi.memmove(data_ptr, Vertex.as_bytes(vertices), buffer_size)
        finally:
            vk.vkUnmapMemory(self.device, staging_buffer_memory)

        vertex_buffer, vertex_buffer_memory = self.create_buffer(
            buffer_size, 
            vk.VK_BUFFER_USAGE_TRANSFER_DST_BIT | vk.VK_BUFFER_USAGE_VERTEX_BUFFER_BIT, 
            vk.VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT
        )

        self.copy_buffer(staging_buffer, vertex_buffer, buffer_size)

        self.destroy_buffer(staging_buffer)
        self.free_memory(staging_buffer_memory)

        return vertex_buffer, vertex_buffer_memory, len(vertices)

    def copy_buffer(self, src_buffer, dst_buffer, size):
        command_buffer = self.begin_single_time_commands()

        copy_region = vk.VkBufferCopy(srcOffset=0, dstOffset=0, size=size)
        vk.vkCmdCopyBuffer(command_buffer, src_buffer, dst_buffer, 1, [copy_region])

        self.end_single_time_commands(command_buffer)

    def begin_single_time_commands(self):
        command_pool = self.create_command_pool()
        allocate_info = vk.VkCommandBufferAllocateInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
            level=vk.VK_COMMAND_BUFFER_LEVEL_PRIMARY,
            commandPool=command_pool,
            commandBufferCount=1,
        )
        command_buffer = vk.vkAllocateCommandBuffers(self.device, allocate_info)[0]

        begin_info = vk.VkCommandBufferBeginInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
            flags=vk.VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT,
        )
        vk.vkBeginCommandBuffer(command_buffer, begin_info)

        return command_buffer

    def end_single_time_commands(self, command_buffer):
        vk.vkEndCommandBuffer(command_buffer)

        submit_info = vk.VkSubmitInfo(
            sType=vk.VK_STRUCTURE_TYPE_SUBMIT_INFO,
            commandBufferCount=1,
            pCommandBuffers=[command_buffer],
        )

        vk.vkQueueSubmit(self.renderer.graphics_queue, 1, [submit_info], vk.VK_NULL_HANDLE)
        vk.vkQueueWaitIdle(self.renderer.graphics_queue)

        vk.vkFreeCommandBuffers(self.device, self.command_pool, 1, [command_buffer])

    def create_command_pool(self):
        pool_info = vk.VkCommandPoolCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
            queueFamilyIndex=self.renderer.graphics_queue_family_index,
            flags=vk.VK_COMMAND_POOL_CREATE_TRANSIENT_BIT,
        )
        return vk.vkCreateCommandPool(self.device, pool_info, None)
