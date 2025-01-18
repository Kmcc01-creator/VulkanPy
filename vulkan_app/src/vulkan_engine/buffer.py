import vulkan as vk
import logging
from typing import Optional, Any, Dict, Union
from dataclasses import dataclass
from enum import Enum, auto
import ctypes
import numpy as np

logger = logging.getLogger(__name__)

class BufferType(Enum):
    VERTEX = auto()
    INDEX = auto()
    UNIFORM = auto()
    STAGING = auto()
    STORAGE = auto()

@dataclass
class BufferCreateInfo:
    size: int
    buffer_type: BufferType
    sharing_mode: int = vk.VK_SHARING_MODE_EXCLUSIVE
    queue_family_indices: list = None
    memory_properties: int = None
    
    def __post_init__(self):
        if self.memory_properties is None:
            self.memory_properties = self._default_memory_properties()
            
    def _default_memory_properties(self) -> int:
        """Get default memory properties based on buffer type."""
        if self.buffer_type == BufferType.STAGING:
            return (vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | 
                   vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)
        elif self.buffer_type == BufferType.UNIFORM:
            return (vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | 
                   vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)
        else:
            return vk.VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT

class Buffer:
    def __init__(self, device: vk.VkDevice, memory_allocator: Any, create_info: BufferCreateInfo):
        self.device = device
        self.memory_allocator = memory_allocator
        self.create_info = create_info
        
        self.handle: Optional[vk.VkBuffer] = None
        self.memory: Optional[vk.VkDeviceMemory] = None
        self.size = create_info.size
        self.mapped_memory: Optional[Any] = None
        
        self._create_buffer()
        
    def _create_buffer(self) -> None:
        """Create the buffer and allocate memory."""
        usage = self._get_buffer_usage()
        
        buffer_info = vk.VkBufferCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
            size=self.size,
            usage=usage,
            sharingMode=self.create_info.sharing_mode,
            queueFamilyIndexCount=len(self.create_info.queue_family_indices or []),
            pQueueFamilyIndices=self.create_info.queue_family_indices
        )
        
        try:
            self.handle = vk.vkCreateBuffer(self.device, buffer_info, None)
            memory_reqs = vk.vkGetBufferMemoryRequirements(self.device, self.handle)
            self.memory = self.memory_allocator.allocate_memory(
                memory_reqs,
                self.create_info.memory_properties
            )
            vk.vkBindBufferMemory(self.device, self.handle, self.memory, 0)
            logger.debug(f"Created {self.create_info.buffer_type.name} buffer of size {self.size}")
            
        except Exception as e:
            self.cleanup()
            raise RuntimeError(f"Failed to create buffer: {str(e)}")

    def _get_buffer_usage(self) -> int:
        """Get buffer usage flags based on buffer type."""
        usage_map = {
            BufferType.VERTEX: vk.VK_BUFFER_USAGE_VERTEX_BUFFER_BIT | vk.VK_BUFFER_USAGE_TRANSFER_DST_BIT,
            BufferType.INDEX: vk.VK_BUFFER_USAGE_INDEX_BUFFER_BIT | vk.VK_BUFFER_USAGE_TRANSFER_DST_BIT,
            BufferType.UNIFORM: vk.VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT,
            BufferType.STAGING: vk.VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
            BufferType.STORAGE: vk.VK_BUFFER_USAGE_STORAGE_BUFFER_BIT
        }
        return usage_map[self.create_info.buffer_type]

    def map(self, offset: int = 0, size: Optional[int] = None) -> None:
        """Map buffer memory for CPU access."""
        if size is None:
            size = self.size
            
        if self.mapped_memory is not None:
            logger.warning("Buffer is already mapped")
            return
            
        self.mapped_memory = vk.vkMapMemory(self.device, self.memory, offset, size, 0)

    def unmap(self) -> None:
        """Unmap buffer memory."""
        if self.mapped_memory is not None:
            vk.vkUnmapMemory(self.device, self.memory)
            self.mapped_memory = None

    def copy_to(self, data: Union[bytes, np.ndarray, ctypes.Array], offset: int = 0) -> None:
        """Copy data to the buffer."""
        was_mapped = self.mapped_memory is not None
        if not was_mapped:
            self.map()
            
        try:
            if isinstance(data, np.ndarray):
                data_ptr = data.ctypes.data_as(ctypes.c_void_p)
                ctypes.memmove(self.mapped_memory, data_ptr, data.nbytes)
            elif isinstance(data, ctypes.Array):
                ctypes.memmove(self.mapped_memory, ctypes.addressof(data), ctypes.sizeof(data))
            else:
                ctypes.memmove(self.mapped_memory, data, len(data))
        finally:
            if not was_mapped:
                self.unmap()

    def copy_from_buffer(self, src_buffer: 'Buffer', size: Optional[int] = None,
                        src_offset: int = 0, dst_offset: int = 0,
                        command_pool: vk.VkCommandPool = None,
                        queue: vk.VkQueue = None) -> None:
        """Copy data from another buffer."""
        if size is None:
            size = min(self.size - dst_offset, src_buffer.size - src_offset)
            
        copy_region = vk.VkBufferCopy(
            srcOffset=src_offset,
            dstOffset=dst_offset,
            size=size
        )
        
        # Create temporary command buffer for transfer
        command_buffer = self._begin_single_time_commands(command_pool)
        
        vk.vkCmdCopyBuffer(command_buffer, src_buffer.handle, self.handle, 1, [copy_region])
        
        self._end_single_time_commands(command_buffer, command_pool, queue)

    def _begin_single_time_commands(self, command_pool: vk.VkCommandPool) -> vk.VkCommandBuffer:
        """Begin single time command buffer."""
        alloc_info = vk.VkCommandBufferAllocateInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
            level=vk.VK_COMMAND_BUFFER_LEVEL_PRIMARY,
            commandPool=command_pool,
            commandBufferCount=1
        )
        
        command_buffer = vk.vkAllocateCommandBuffers(self.device, alloc_info)[0]
        
        begin_info = vk.VkCommandBufferBeginInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
            flags=vk.VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT
        )
        
        vk.vkBeginCommandBuffer(command_buffer, begin_info)
        return command_buffer

    def _end_single_time_commands(self, command_buffer: vk.VkCommandBuffer,
                                command_pool: vk.VkCommandPool,
                                queue: vk.VkQueue) -> None:
        """End and submit single time command buffer."""
        vk.vkEndCommandBuffer(command_buffer)
        
        submit_info = vk.VkSubmitInfo(
            sType=vk.VK_STRUCTURE_TYPE_SUBMIT_INFO,
            commandBufferCount=1,
            pCommandBuffers=[command_buffer]
        )
        
        vk.vkQueueSubmit(queue, 1, [submit_info], vk.VK_NULL_HANDLE)
        vk.vkQueueWaitIdle(queue)
        
        vk.vkFreeCommandBuffers(self.device, command_pool, 1, [command_buffer])

    def cleanup(self) -> None:
        """Clean up buffer resources."""
        if self.mapped_memory is not None:
            self.unmap()
            
        if self.handle:
            vk.vkDestroyBuffer(self.device, self.handle, None)
            self.handle = None
            
        if self.memory:
            self.memory_allocator.free_memory(self.memory)
            self.memory = None
            
class VertexBuffer(Buffer):
    def __init__(self, device: vk.VkDevice, memory_allocator: Any, size: int,
                 use_staging: bool = True):
        create_info = BufferCreateInfo(
            size=size,
            buffer_type=BufferType.VERTEX
        )
        super().__init__(device, memory_allocator, create_info)
        self.staging_buffer = None
        
        if use_staging:
            staging_info = BufferCreateInfo(
                size=size,
                buffer_type=BufferType.STAGING
            )
            self.staging_buffer = Buffer(device, memory_allocator, staging_info)

class IndexBuffer(Buffer):
    def __init__(self, device: vk.VkDevice, memory_allocator: Any, size: int,
                 use_staging: bool = True):
        create_info = BufferCreateInfo(
            size=size,
            buffer_type=BufferType.INDEX
        )
        super().__init__(device, memory_allocator, create_info)
        self.staging_buffer = None
        
        if use_staging:
            staging_info = BufferCreateInfo(
                size=size,
                buffer_type=BufferType.STAGING
            )
            self.staging_buffer = Buffer(device, memory_allocator, staging_info)

class UniformBuffer(Buffer):
    def __init__(self, device: vk.VkDevice, memory_allocator: Any, size: int):
        create_info = BufferCreateInfo(
            size=size,
            buffer_type=BufferType.UNIFORM
        )
        super().__init__(device, memory_allocator, create_info)

class StorageBuffer(Buffer):
    def __init__(self, device: vk.VkDevice, memory_allocator: Any, size: int):
        create_info = BufferCreateInfo(
            size=size,
            buffer_type=BufferType.STORAGE
        )
        super().__init__(device, memory_allocator, create_info)