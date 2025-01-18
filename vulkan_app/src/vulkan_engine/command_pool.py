import vulkan as vk
import logging
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum, auto
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class CommandPoolType(Enum):
    GRAPHICS = auto()
    COMPUTE = auto()
    TRANSFER = auto()

@dataclass
class CommandPoolCreateInfo:
    queue_family_index: int
    pool_type: CommandPoolType
    flags: int = 0
    
    @staticmethod
    def create_transient(queue_family_index: int, pool_type: CommandPoolType) -> 'CommandPoolCreateInfo':
        """Create info for a transient command pool (short-lived command buffers)."""
        return CommandPoolCreateInfo(
            queue_family_index=queue_family_index,
            pool_type=pool_type,
            flags=vk.VK_COMMAND_POOL_CREATE_TRANSIENT_BIT
        )
    
    @staticmethod
    def create_resetable(queue_family_index: int, pool_type: CommandPoolType) -> 'CommandPoolCreateInfo':
        """Create info for a command pool with resetable command buffers."""
        return CommandPoolCreateInfo(
            queue_family_index=queue_family_index,
            pool_type=pool_type,
            flags=vk.VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT
        )

class CommandPool:
    """Manages a single Vulkan command pool and its buffers."""
    
    def __init__(self, device: vk.VkDevice, create_info: CommandPoolCreateInfo):
        self.device = device
        self.create_info = create_info
        self.handle: Optional[vk.VkCommandPool] = None
        self.allocated_buffers: Set[vk.VkCommandBuffer] = set()
        self._create_pool()

    def _create_pool(self) -> None:
        """Create the Vulkan command pool."""
        create_info = vk.VkCommandPoolCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
            queueFamilyIndex=self.create_info.queue_family_index,
            flags=self.create_info.flags
        )
        
        try:
            self.handle = vk.vkCreateCommandPool(self.device, create_info, None)
            logger.debug(
                f"Created {self.create_info.pool_type.name} command pool "
                f"for queue family {self.create_info.queue_family_index}"
            )
        except Exception as e:
            logger.error(f"Failed to create command pool: {e}")
            raise

    def allocate_buffers(self, level: vk.VkCommandBufferLevel, count: int) -> List[vk.VkCommandBuffer]:
        """Allocate command buffers from the pool."""
        alloc_info = vk.VkCommandBufferAllocateInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
            commandPool=self.handle,
            level=level,
            commandBufferCount=count
        )
        
        try:
            buffers = vk.vkAllocateCommandBuffers(self.device, alloc_info)
            self.allocated_buffers.update(buffers)
            logger.debug(f"Allocated {count} command buffers")
            return buffers
        except Exception as e:
            logger.error(f"Failed to allocate command buffers: {e}")
            raise

    def free_buffers(self, buffers: List[vk.VkCommandBuffer]) -> None:
        """Free command buffers back to the pool."""
        if not buffers:
            return
            
        try:
            vk.vkFreeCommandBuffers(self.device, self.handle, len(buffers), buffers)
            self.allocated_buffers.difference_update(buffers)
            logger.debug(f"Freed {len(buffers)} command buffers")
        except Exception as e:
            logger.error(f"Failed to free command buffers: {e}")
            raise

    def reset(self, release_resources: bool = False) -> None:
        """Reset the command pool."""
        if not self.handle:
            return
            
        flags = vk.VK_COMMAND_POOL_RESET_RELEASE_RESOURCES_BIT if release_resources else 0
        try:
            vk.vkResetCommandPool(self.device, self.handle, flags)
            self.allocated_buffers.clear()
            logger.debug("Reset command pool")
        except Exception as e:
            logger.error(f"Failed to reset command pool: {e}")
            raise

    def cleanup(self) -> None:
        """Destroy the command pool and free all resources."""
        if self.handle:
            try:
                vk.vkDestroyCommandPool(self.device, self.handle, None)
                self.handle = None
                self.allocated_buffers.clear()
                logger.debug("Destroyed command pool")
            except Exception as e:
                logger.error(f"Failed to destroy command pool: {e}")
                raise

class CommandPoolManager:
    """Manages multiple command pools for different purposes."""
    
    def __init__(self, device: vk.VkDevice):
        self.device = device
        self.pools: Dict[Tuple[int, CommandPoolType], CommandPool] = {}
        
    def get_or_create_pool(self, create_info: CommandPoolCreateInfo) -> CommandPool:
        """Get an existing pool or create a new one."""
        key = (create_info.queue_family_index, create_info.pool_type)
        
        if key not in self.pools:
            self.pools[key] = CommandPool(self.device, create_info)
        return self.pools[key]

    def allocate_command_buffers(
        self,
        queue_family_index: int,
        pool_type: CommandPoolType,
        level: vk.VkCommandBufferLevel,
        count: int,
        transient: bool = False
    ) -> List[vk.VkCommandBuffer]:
        """Allocate command buffers from an appropriate pool."""
        create_info = (
            CommandPoolCreateInfo.create_transient(queue_family_index, pool_type)
            if transient
            else CommandPoolCreateInfo.create_resetable(queue_family_index, pool_type)
        )
        
        pool = self.get_or_create_pool(create_info)
        return pool.allocate_buffers(level, count)

    def free_command_buffers(
        self,
        queue_family_index: int,
        pool_type: CommandPoolType,
        buffers: List[vk.VkCommandBuffer]
    ) -> None:
        """Free command buffers back to their pool."""
        key = (queue_family_index, pool_type)
        if key in self.pools:
            self.pools[key].free_buffers(buffers)

    def reset_pool(
        self,
        queue_family_index: int,
        pool_type: CommandPoolType,
        release_resources: bool = False
    ) -> None:
        """Reset a specific command pool."""
        key = (queue_family_index, pool_type)
        if key in self.pools:
            self.pools[key].reset(release_resources)

    def cleanup(self) -> None:
        """Clean up all command pools."""
        for pool in self.pools.values():
            pool.cleanup()
        self.pools.clear()
        logger.info("Cleaned up all command pools")

class CommandBufferAllocator:
    """Helper class for managing command buffer allocation and recording."""
    
    def __init__(self, pool_manager: CommandPoolManager):
        self.pool_manager = pool_manager
        
    def allocate_buffers(
        self,
        queue_family_index: int,
        pool_type: CommandPoolType,
        level: vk.VkCommandBufferLevel,
        count: int,
        transient: bool = False
    ) -> List[vk.VkCommandBuffer]:
        """Allocate command buffers with specific properties."""
        return self.pool_manager.allocate_command_buffers(
            queue_family_index=queue_family_index,
            pool_type=pool_type,
            level=level,
            count=count,
            transient=transient
        )

    def begin_single_time_command(
        self,
        queue_family_index: int,
        pool_type: CommandPoolType
    ) -> vk.VkCommandBuffer:
        """Create and begin a single-use command buffer."""
        command_buffer = self.allocate_buffers(
            queue_family_index=queue_family_index,
            pool_type=pool_type,
            level=vk.VK_COMMAND_BUFFER_LEVEL_PRIMARY,
            count=1,
            transient=True
        )[0]
        
        begin_info = vk.VkCommandBufferBeginInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
            flags=vk.VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT
        )
        
        vk.vkBeginCommandBuffer(command_buffer, begin_info)
        return command_buffer

    def end_single_time_command(
        self,
        command_buffer: vk.VkCommandBuffer,
        queue: vk.VkQueue,
        queue_family_index: int,
        pool_type: CommandPoolType
    ) -> None:
        """End and submit a single-use command buffer."""
        vk.vkEndCommandBuffer(command_buffer)
        
        submit_info = vk.VkSubmitInfo(
            sType=vk.VK_STRUCTURE_TYPE_SUBMIT_INFO,
            commandBufferCount=1,
            pCommandBuffers=[command_buffer]
        )
        
        try:
            vk.vkQueueSubmit(queue, 1, [submit_info], vk.VK_NULL_HANDLE)
            vk.vkQueueWaitIdle(queue)
        finally:
            self.pool_manager.free_command_buffers(
                queue_family_index=queue_family_index,
                pool_type=pool_type,
                buffers=[command_buffer]
            )