import vulkan as vk
import logging
import ctypes
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from enum import Enum, auto

logger = logging.getLogger(__name__)

class BufferUsage(Enum):
    VERTEX = vk.VK_BUFFER_USAGE_VERTEX_BUFFER_BIT
    INDEX = vk.VK_BUFFER_USAGE_INDEX_BUFFER_BIT
    UNIFORM = vk.VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT
    STORAGE = vk.VK_BUFFER_USAGE_STORAGE_BUFFER_BIT
    TRANSFER_SRC = vk.VK_BUFFER_USAGE_TRANSFER_SRC_BIT
    TRANSFER_DST = vk.VK_BUFFER_USAGE_TRANSFER_DST_BIT

@dataclass
class BufferCreateInfo:
    size: int
    usage: List[BufferUsage]
    memory_properties: int
    sharing_mode: int = vk.VK_SHARING_MODE_EXCLUSIVE
    queue_family_indices: Optional[List[int]] = None

class Buffer:
    def __init__(self, device: vk.VkDevice, memory_manager: 'MemoryManager',
                 create_info: BufferCreateInfo):
        self.device = device
        self.memory_manager = memory_manager
        self.create_info = create_info
        self.handle: Optional[vk.VkBuffer] = None
        self.memory_allocation_id: Optional[int] = None
        self.size = create_info.size
        self.mapped_memory: Optional[Any] = None
        
        self._create()

    def _create(self) -> None:
        usage_flags = 0
        for usage in self.create_info.usage:
            usage_flags |= usage.value

        buffer_info = vk.VkBufferCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
            size=self.size,
            usage=usage_flags,
            sharingMode=self.create_info.sharing_mode,
            queueFamilyIndexCount=len(self.create_info.queue_family_indices or []),
            pQueueFamilyIndices=self.create_info.queue_family_indices
        )

        try:
            self.handle = vk.vkCreateBuffer(self.device, buffer_info, None)
            memory_requirements = vk.vkGetBufferMemoryRequirements(self.device, self.handle)
            
            memory_type_index = self.memory_manager.find_memory_type(
                memory_requirements.memoryTypeBits,
                self.create_info.memory_properties
            )

            self.memory_allocation_id = self.memory_manager.allocate(
                memory_requirements.size,
                memory_type_index,
                memory_requirements.alignment
            )

            memory = self.memory_manager.get_allocation_memory(self.memory_allocation_id)
            vk.vkBindBufferMemory(self.device, self.handle, memory, 0)
            
            logger.debug(f"Created buffer of size {self.size}")
        except Exception as e:
            self.cleanup()
            raise RuntimeError(f"Failed to create buffer: {str(e)}")

    def map(self, offset: int = 0, size: Optional[int] = None) -> Any:
        if size is None:
            size = self.size - offset
        
        if self.mapped_memory is None:
            self.mapped_memory = self.memory_manager.map(
                self.memory_allocation_id,
                offset,
                size
            )
        return self.mapped_memory

    def unmap(self) -> None:
        if self.mapped_memory is not None:
            self.memory_manager.unmap(self.memory_allocation_id)
            self.mapped_memory = None

    def upload_data(self, data: bytes, offset: int = 0) -> None:
        mapped_memory = self.map(offset, len(data))
        ctypes.memmove(mapped_memory, data, len(data))
        self.unmap()
        
        if not (self.create_info.memory_properties & vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT):
            self.memory_manager.flush(self.memory_allocation_id, offset, len(data))

    def cleanup(self) -> None:
        if self.mapped_memory is not None:
            self.unmap()
        
        if self.handle is not None:
            vk.vkDestroyBuffer(self.device, self.handle, None)
            self.handle = None
            
        if self.memory_allocation_id is not None:
            self.memory_manager.free(self.memory_allocation_id)
            self.memory_allocation_id = None

class BufferManager:
    def __init__(self, device: vk.VkDevice, memory_manager: 'MemoryManager',
                 command_pool: vk.VkCommandPool, transfer_queue: vk.VkQueue):
        self.device = device
        self.memory_manager = memory_manager
        self.command_pool = command_pool
        self.transfer_queue = transfer_queue
        self.buffers: Dict[int, Buffer] = {}
        self.buffer_counter = 0

    def create_buffer(self, create_info: BufferCreateInfo) -> int:
        """Create a buffer and return its ID."""
        try:
            buffer = Buffer(self.device, self.memory_manager, create_info)
            self.buffer_counter += 1
            self.buffers[self.buffer_counter] = buffer
            return self.buffer_counter
        except Exception as e:
            logger.error(f"Failed to create buffer: {e}")
            raise

    def create_vertex_buffer(self, size: int, data: Optional[bytes] = None,
                           shared_queues: Optional[List[int]] = None) -> int:
        """Create a vertex buffer with optional initial data."""
        usage = [BufferUsage.VERTEX]
        if data is not None:
            usage.append(BufferUsage.TRANSFER_DST)

        create_info = BufferCreateInfo(
            size=size,
            usage=usage,
            memory_properties=vk.VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,
            queue_family_indices=shared_queues
        )

        buffer_id = self.create_buffer(create_info)

        if data is not None:
            self._upload_buffer_data(buffer_id, data)

        return buffer_id

    def create_index_buffer(self, size: int, data: Optional[bytes] = None,
                          shared_queues: Optional[List[int]] = None) -> int:
        """Create an index buffer with optional initial data."""
        usage = [BufferUsage.INDEX]
        if data is not None:
            usage.append(BufferUsage.TRANSFER_DST)

        create_info = BufferCreateInfo(
            size=size,
            usage=usage,
            memory_properties=vk.VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,
            queue_family_indices=shared_queues
        )

        buffer_id = self.create_buffer(create_info)

        if data is not None:
            self._upload_buffer_data(buffer_id, data)

        return buffer_id

    def create_uniform_buffer(self, size: int, shared_queues: Optional[List[int]] = None) -> int:
        """Create a uniform buffer."""
        create_info = BufferCreateInfo(
            size=size,
            usage=[BufferUsage.UNIFORM],
            memory_properties=(vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
                             vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT),
            queue_family_indices=shared_queues
        )
        return self.create_buffer(create_info)

    def create_storage_buffer(self, size: int, shared_queues: Optional[List[int]] = None) -> int:
        """Create a storage buffer."""
        create_info = BufferCreateInfo(
            size=size,
            usage=[BufferUsage.STORAGE],
            memory_properties=(vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
                             vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT),
            queue_family_indices=shared_queues
        )
        return self.create_buffer(create_info)

    def _upload_buffer_data(self, buffer_id: int, data: bytes) -> None:
        """Upload data to a buffer using a staging buffer."""
        buffer = self.buffers[buffer_id]
        
        # Create staging buffer
        staging_info = BufferCreateInfo(
            size=len(data),
            usage=[BufferUsage.TRANSFER_SRC],
            memory_properties=(vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
                             vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)
        )
        
        staging_id = self.create_buffer(staging_info)
        staging_buffer = self.buffers[staging_id]
        
        # Upload data to staging buffer
        staging_buffer.upload_data(data)
        
        # Create command buffer for transfer
        command_buffer = self._begin_single_time_commands()
        
        copy_region = vk.VkBufferCopy(
            srcOffset=0,
            dstOffset=0,
            size=len(data)
        )
        
        vk.vkCmdCopyBuffer(
            command_buffer,
            staging_buffer.handle,
            buffer.handle,
            1,
            [copy_region]
        )
        
        self._end_single_time_commands(command_buffer)
        
        # Cleanup staging buffer
        self.destroy_buffer(staging_id)

    def _begin_single_time_commands(self) -> vk.VkCommandBuffer:
        """Begin a single-time-use command buffer."""
        alloc_info = vk.VkCommandBufferAllocateInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
            level=vk.VK_COMMAND_BUFFER_LEVEL_PRIMARY,
            commandPool=self.command_pool,
            commandBufferCount=1
        )

        command_buffer = vk.vkAllocateCommandBuffers(self.device, alloc_info)[0]

        begin_info = vk.VkCommandBufferBeginInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
            flags=vk.VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT
        )

        vk.vkBeginCommandBuffer(command_buffer, begin_info)
        return command_buffer

    def _end_single_time_commands(self, command_buffer: vk.VkCommandBuffer) -> None:
        """End and submit a single-time-use command buffer."""
        vk.vkEndCommandBuffer(command_buffer)

        submit_info = vk.VkSubmitInfo(
            sType=vk.VK_STRUCTURE_TYPE_SUBMIT_INFO,
            commandBufferCount=1,
            pCommandBuffers=[command_buffer]
        )

        vk.vkQueueSubmit(self.transfer_queue, 1, [submit_info], vk.VK_NULL_HANDLE)
        vk.vkQueueWaitIdle(self.transfer_queue)

        vk.vkFreeCommandBuffers(self.device, self.command_pool, 1, [command_buffer])

    def get_buffer(self, buffer_id: int) -> Buffer:
        """Get a buffer by ID."""
        if buffer_id not in self.buffers:
            raise RuntimeError(f"Invalid buffer ID: {buffer_id}")
        return self.buffers[buffer_id]

    def destroy_buffer(self, buffer_id: int) -> None:
        """Destroy a buffer."""
        if buffer_id in self.buffers:
            self.buffers[buffer_id].cleanup()
            del self.buffers[buffer_id]

    def cleanup(self) -> None:
        """Clean up all buffers."""
        for buffer_id in list(self.buffers.keys()):
            self.destroy_buffer(buffer_id)
        logger.info("Cleaned up all buffers")