import vulkan as vk
import logging
from typing import Optional, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class VulkanResource:
    """Base class for RAII Vulkan resources."""
    
    def __init__(self, device: vk.VkDevice):
        self.device = device
        self.handle: Any = None
        
    def __del__(self):
        self.cleanup()
        
    def cleanup(self):
        """Clean up the resource. Override in derived classes."""
        pass

class Buffer(VulkanResource):
    def __init__(self, device: vk.VkDevice, size: int, usage: int, memory_properties: int,
                 memory_allocator: 'MemoryAllocator'):
        super().__init__(device)
        self.size = size
        self.memory: Optional[vk.VkDeviceMemory] = None
        self.memory_allocator = memory_allocator
        self._create_buffer(usage, memory_properties)
        
    def _create_buffer(self, usage: int, memory_properties: int):
        create_info = vk.VkBufferCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
            size=self.size,
            usage=usage,
            sharingMode=vk.VK_SHARING_MODE_EXCLUSIVE
        )
        
        try:
            self.handle = vk.vkCreateBuffer(self.device, create_info, None)
            memory_requirements = vk.vkGetBufferMemoryRequirements(self.device, self.handle)
            self.memory = self.memory_allocator.allocate_memory(
                memory_requirements,
                memory_properties
            )
            vk.vkBindBufferMemory(self.device, self.handle, self.memory, 0)
            logger.debug(f"Created buffer of size {self.size}")
        except Exception as e:
            self.cleanup()
            raise RuntimeError(f"Failed to create buffer: {str(e)}")
            
    @contextmanager
    def map_memory(self):
        """Context manager for mapping buffer memory."""
        try:
            data_ptr = vk.vkMapMemory(self.device, self.memory, 0, self.size, 0)
            yield data_ptr
        finally:
            vk.vkUnmapMemory(self.device, self.memory)
            
    def cleanup(self):
        if self.handle:
            try:
                vk.vkDestroyBuffer(self.device, self.handle, None)
                self.handle = None
            except Exception as e:
                logger.error(f"Error destroying buffer: {str(e)}")
                
        if self.memory:
            try:
                self.memory_allocator.free_memory(self.memory)
                self.memory = None
            except Exception as e:
                logger.error(f"Error freeing buffer memory: {str(e)}")

class Image(VulkanResource):
    def __init__(self, device: vk.VkDevice, width: int, height: int, format: int,
                 usage: int, memory_properties: int, memory_allocator: 'MemoryAllocator'):
        super().__init__(device)
        self.width = width
        self.height = height
        self.format = format
        self.memory: Optional[vk.VkDeviceMemory] = None
        self.view: Optional[vk.VkImageView] = None
        self.memory_allocator = memory_allocator
        self._create_image(usage, memory_properties)
        
    def _create_image(self, usage: int, memory_properties: int):
        create_info = vk.VkImageCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
            imageType=vk.VK_IMAGE_TYPE_2D,
            format=self.format,
            extent=vk.VkExtent3D(self.width, self.height, 1),
            mipLevels=1,
            arrayLayers=1,
            samples=vk.VK_SAMPLE_COUNT_1_BIT,
            tiling=vk.VK_IMAGE_TILING_OPTIMAL,
            usage=usage,
            sharingMode=vk.VK_SHARING_MODE_EXCLUSIVE,
            initialLayout=vk.VK_IMAGE_LAYOUT_UNDEFINED
        )
        
        try:
            self.handle = vk.vkCreateImage(self.device, create_info, None)
            memory_requirements = vk.vkGetImageMemoryRequirements(self.device, self.handle)
            self.memory = self.memory_allocator.allocate_memory(
                memory_requirements,
                memory_properties
            )
            vk.vkBindImageMemory(self.device, self.handle, self.memory, 0)
            logger.debug(f"Created image {self.width}x{self.height}")
        except Exception as e:
            self.cleanup()
            raise RuntimeError(f"Failed to create image: {str(e)}")
            
    def create_view(self, aspect_flags: int):
        """Create an image view."""
        if self.view:
            return
            
        create_info = vk.VkImageViewCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
            image=self.handle,
            viewType=vk.VK_IMAGE_VIEW_TYPE_2D,
            format=self.format,
            subresourceRange=vk.VkImageSubresourceRange(
                aspectMask=aspect_flags,
                baseMipLevel=0,
                levelCount=1,
                baseArrayLayer=0,
                layerCount=1
            )
        )
        
        try:
            self.view = vk.vkCreateImageView(self.device, create_info, None)
            logger.debug("Created image view")
        except Exception as e:
            raise RuntimeError(f"Failed to create image view: {str(e)}")
            
    def cleanup(self):
        if self.view:
            try:
                vk.vkDestroyImageView(self.device, self.view, None)
                self.view = None
            except Exception as e:
                logger.error(f"Error destroying image view: {str(e)}")
                
        if self.handle:
            try:
                vk.vkDestroyImage(self.device, self.handle, None)
                self.handle = None
            except Exception as e:
                logger.error(f"Error destroying image: {str(e)}")
                
        if self.memory:
            try:
                self.memory_allocator.free_memory(self.memory)
                self.memory = None
            except Exception as e:
                logger.error(f"Error freeing image memory: {str(e)}")

class CommandPool(VulkanResource):
    def __init__(self, device: vk.VkDevice, queue_family_index: int):
        super().__init__(device)
        self._create_pool(queue_family_index)
        
    def _create_pool(self, queue_family_index: int):
        create_info = vk.VkCommandPoolCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
            flags=vk.VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT,
            queueFamilyIndex=queue_family_index
        )
        
        try:
            self.handle = vk.vkCreateCommandPool(self.device, create_info, None)
            logger.debug("Created command pool")
        except Exception as e:
            raise RuntimeError(f"Failed to create command pool: {str(e)}")
            
    def allocate_buffers(self, level: int, count: int) -> list:
        """Allocate command buffers from the pool."""
        allocate_info = vk.VkCommandBufferAllocateInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
            commandPool=self.handle,
            level=level,
            commandBufferCount=count
        )
        
        try:
            return vk.vkAllocateCommandBuffers(self.device, allocate_info)
        except Exception as e:
            raise RuntimeError(f"Failed to allocate command buffers: {str(e)}")
            
    def cleanup(self):
        if self.handle:
            try:
                vk.vkDestroyCommandPool(self.device, self.handle, None)
                self.handle = None
            except Exception as e:
                logger.error(f"Error destroying command pool: {str(e)}")