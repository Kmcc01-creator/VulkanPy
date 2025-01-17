import vulkan as vk
from src.vertex import Vertex
from src.vulkan_engine.vulkan_resources import VulkanBuffer, VulkanImage, VulkanCommandPool
from src.vulkan_engine.memory_allocator import MemoryAllocator
import logging

logger = logging.getLogger(__name__)

class ResourceManager:
    def __init__(self, renderer):
        self.renderer = renderer
        self.device = renderer.device
        self.physical_device = renderer.physical_device
        self.resources = {}
        self.memory_allocator = MemoryAllocator(self.physical_device, self.device)
        self.resource_cache = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup()

    def add_resource(self, resource, resource_type):
        if resource_type not in self.resources:
            self.resources[resource_type] = []
        self.resources[resource_type].append(resource)

    def cleanup(self):
        for resource_type, resources in self.resources.items():
            for resource in reversed(resources):
                try:
                    resource.destroy()
                except Exception as e:
                    logger.error(f"Failed to clean up {resource_type}: {e}")
        self.resources.clear()
        self.resource_cache.clear()

    def create_buffer(self, size, usage, memory_properties):
        cache_key = (size, usage, memory_properties)
        if cache_key in self.resource_cache:
            return self.resource_cache[cache_key]

        try:
            buffer = VulkanBuffer(self.device, size, usage, memory_properties, self.memory_allocator)
            self.add_resource(buffer, "buffer")
            self.resource_cache[cache_key] = buffer
            return buffer
        except vk.VkError as e:
            logger.error(f"Failed to create buffer: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during buffer creation: {e}")
            raise

    def create_image(self, width, height, format, usage, memory_properties):
        cache_key = (width, height, format, usage, memory_properties)
        if cache_key in self.resource_cache:
            return self.resource_cache[cache_key]

        try:
            image = VulkanImage(self.device, width, height, format, usage, memory_properties, self.memory_allocator)
            self.add_resource(image, "image")
            self.resource_cache[cache_key] = image
            return image
        except vk.VkError as e:
            logger.error(f"Failed to create image: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during image creation: {e}")
            raise

    def create_vertex_buffer(self, vertices):
        buffer_size = Vertex.sizeof() * len(vertices)

        staging_buffer = self.create_buffer(
            buffer_size, 
            vk.VK_BUFFER_USAGE_TRANSFER_SRC_BIT, 
            vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT
        )

        staging_buffer.map_memory()
        staging_buffer.copy_to_memory(Vertex.as_bytes(vertices))
        staging_buffer.unmap_memory()

        vertex_buffer = self.create_buffer(
            buffer_size, 
            vk.VK_BUFFER_USAGE_TRANSFER_DST_BIT | vk.VK_BUFFER_USAGE_VERTEX_BUFFER_BIT, 
            vk.VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT
        )

        self.copy_buffer(staging_buffer, vertex_buffer, buffer_size)

        # Staging buffer will be automatically cleaned up when no longer needed
        return vertex_buffer

    def copy_buffer(self, src_buffer, dst_buffer, size):
        with self.begin_single_time_commands() as command_buffer:
            copy_region = vk.VkBufferCopy(srcOffset=0, dstOffset=0, size=size)
            vk.vkCmdCopyBuffer(command_buffer, src_buffer.buffer, dst_buffer.buffer, 1, [copy_region])

    def begin_single_time_commands(self):
        command_pool = VulkanCommandPool(self.device, self.renderer.graphics_queue_family_index)
        self.add_resource(command_pool, "command_pool")
        return command_pool.begin_single_time_commands()

    def end_single_time_commands(self, command_buffer):
        submit_info = vk.VkSubmitInfo(
            sType=vk.VK_STRUCTURE_TYPE_SUBMIT_INFO,
            commandBufferCount=1,
            pCommandBuffers=[command_buffer],
        )

        vk.vkQueueSubmit(self.renderer.graphics_queue, 1, [submit_info], vk.VK_NULL_HANDLE)
        vk.vkQueueWaitIdle(self.renderer.graphics_queue)
