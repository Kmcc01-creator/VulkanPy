import vulkan as vk
import logging
from typing import List, Optional, Dict, Set, Callable
from dataclasses import dataclass
from enum import Enum, auto
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class CommandBufferLevel(Enum):
    PRIMARY = auto()
    SECONDARY = auto()

@dataclass
class CommandBufferAllocateInfo:
    level: CommandBufferLevel
    count: int = 1

    def to_vulkan_info(self, command_pool: vk.VkCommandPool) -> vk.VkCommandBufferAllocateInfo:
        level_map = {
            CommandBufferLevel.PRIMARY: vk.VK_COMMAND_BUFFER_LEVEL_PRIMARY,
            CommandBufferLevel.SECONDARY: vk.VK_COMMAND_BUFFER_LEVEL_SECONDARY
        }
        
        return vk.VkCommandBufferAllocateInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
            commandPool=command_pool,
            level=level_map[self.level],
            commandBufferCount=self.count
        )

class CommandBufferUsage(Enum):
    ONE_TIME = auto()
    REUSABLE = auto()
    SIMULTANEOUS = auto()

class CommandPool:
    """Manages command pools and their associated command buffers."""
    
    def __init__(self, device: vk.VkDevice, queue_family_index: int, 
                 transient: bool = False, reset_command_buffer: bool = True):
        self.device = device
        self.queue_family_index = queue_family_index
        self.handle: Optional[vk.VkCommandPool] = None
        self.allocated_buffers: Set[vk.VkCommandBuffer] = set()
        
        # Create the command pool
        flags = 0
        if transient:
            flags |= vk.VK_COMMAND_POOL_CREATE_TRANSIENT_BIT
        if reset_command_buffer:
            flags |= vk.VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT
            
        create_info = vk.VkCommandPoolCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
            queueFamilyIndex=queue_family_index,
            flags=flags
        )
        
        try:
            self.handle = vk.vkCreateCommandPool(device, create_info, None)
            logger.debug(f"Created command pool for queue family {queue_family_index}")
        except Exception as e:
            raise RuntimeError(f"Failed to create command pool: {str(e)}")

    def allocate_buffers(self, allocate_info: CommandBufferAllocateInfo) -> List[vk.VkCommandBuffer]:
        """Allocate command buffers from the pool."""
        try:
            vulkan_info = allocate_info.to_vulkan_info(self.handle)
            command_buffers = vk.vkAllocateCommandBuffers(self.device, vulkan_info)
            self.allocated_buffers.update(command_buffers)
            return command_buffers
        except Exception as e:
            raise RuntimeError(f"Failed to allocate command buffers: {str(e)}")

    def free_buffers(self, command_buffers: List[vk.VkCommandBuffer]) -> None:
        """Free command buffers back to the pool."""
        if not command_buffers:
            return
            
        try:
            vk.vkFreeCommandBuffers(self.device, self.handle, len(command_buffers), command_buffers)
            self.allocated_buffers.difference_update(command_buffers)
        except Exception as e:
            logger.error(f"Failed to free command buffers: {str(e)}")

    def reset(self, release_resources: bool = False) -> None:
        """Reset the command pool."""
        flags = vk.VK_COMMAND_POOL_RESET_RELEASE_RESOURCES_BIT if release_resources else 0
        try:
            vk.vkResetCommandPool(self.device, self.handle, flags)
            self.allocated_buffers.clear()
        except Exception as e:
            logger.error(f"Failed to reset command pool: {str(e)}")

    def cleanup(self) -> None:
        """Clean up the command pool and its resources."""
        if self.handle:
            vk.vkDestroyCommandPool(self.device, self.handle, None)
            self.handle = None
            self.allocated_buffers.clear()

class CommandBuffer:
    """Manages command buffer recording and submission."""
    
    def __init__(self, device: vk.VkDevice, command_buffer: vk.VkCommandBuffer):
        self.device = device
        self.handle = command_buffer
        self.is_recording = False

    def begin(self, usage: CommandBufferUsage = CommandBufferUsage.ONE_TIME) -> None:
        """Begin command buffer recording."""
        if self.is_recording:
            logger.warning("Command buffer is already in recording state")
            return

        usage_map = {
            CommandBufferUsage.ONE_TIME: vk.VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT,
            CommandBufferUsage.REUSABLE: 0,
            CommandBufferUsage.SIMULTANEOUS: vk.VK_COMMAND_BUFFER_USAGE_SIMULTANEOUS_USE_BIT
        }

        begin_info = vk.VkCommandBufferBeginInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
            flags=usage_map[usage]
        )

        try:
            vk.vkBeginCommandBuffer(self.handle, begin_info)
            self.is_recording = True
        except Exception as e:
            raise RuntimeError(f"Failed to begin command buffer: {str(e)}")

    def end(self) -> None:
        """End command buffer recording."""
        if not self.is_recording:
            logger.warning("Command buffer is not in recording state")
            return

        try:
            vk.vkEndCommandBuffer(self.handle)
            self.is_recording = False
        except Exception as e:
            raise RuntimeError(f"Failed to end command buffer: {str(e)}")

    def reset(self, release_resources: bool = False) -> None:
        """Reset the command buffer."""
        flags = vk.VK_COMMAND_BUFFER_RESET_RELEASE_RESOURCES_BIT if release_resources else 0
        try:
            vk.vkResetCommandBuffer(self.handle, flags)
            self.is_recording = False
        except Exception as e:
            logger.error(f"Failed to reset command buffer: {str(e)}")

    @contextmanager
    def record(self, usage: CommandBufferUsage = CommandBufferUsage.ONE_TIME):
        """Context manager for recording commands."""
        self.begin(usage)
        try:
            yield self
        finally:
            self.end()

    def copy_buffer(self, src_buffer: vk.VkBuffer, dst_buffer: vk.VkBuffer,
                   regions: List[vk.VkBufferCopy]) -> None:
        """Record a buffer copy command."""
        if not self.is_recording:
            raise RuntimeError("Command buffer must be in recording state")
            
        vk.vkCmdCopyBuffer(self.handle, src_buffer, dst_buffer, len(regions), regions)

    def copy_image(self, src_image: vk.VkImage, src_layout: int,
                  dst_image: vk.VkImage, dst_layout: int,
                  regions: List[vk.VkImageCopy]) -> None:
        """Record an image copy command."""
        if not self.is_recording:
            raise RuntimeError("Command buffer must be in recording state")
            
        vk.vkCmdCopyImage(
            self.handle, src_image, src_layout,
            dst_image, dst_layout,
            len(regions), regions
        )

    def pipeline_barrier(self, src_stage_mask: int, dst_stage_mask: int,
                        dependency_flags: int,
                        memory_barriers: List[vk.VkMemoryBarrier] = None,
                        buffer_barriers: List[vk.VkBufferMemoryBarrier] = None,
                        image_barriers: List[vk.VkImageMemoryBarrier] = None) -> None:
        """Record a pipeline barrier command."""
        if not self.is_recording:
            raise RuntimeError("Command buffer must be in recording state")

        vk.vkCmdPipelineBarrier(
            self.handle,
            src_stage_mask,
            dst_stage_mask,
            dependency_flags,
            len(memory_barriers or []),
            memory_barriers or [],
            len(buffer_barriers or []),
            buffer_barriers or [],
            len(image_barriers or []),
            image_barriers or []
        )

    def begin_render_pass(self, render_pass_begin: vk.VkRenderPassBeginInfo,
                         contents: int = vk.VK_SUBPASS_CONTENTS_INLINE) -> None:
        """Begin a render pass."""
        if not self.is_recording:
            raise RuntimeError("Command buffer must be in recording state")
            
        vk.vkCmdBeginRenderPass(self.handle, render_pass_begin, contents)

    def end_render_pass(self) -> None:
        """End the current render pass."""
        if not self.is_recording:
            raise RuntimeError("Command buffer must be in recording state")
            
        vk.vkCmdEndRenderPass(self.handle)

    def bind_pipeline(self, pipeline_bind_point: int, pipeline: vk.VkPipeline) -> None:
        """Bind a pipeline."""
        if not self.is_recording:
            raise RuntimeError("Command buffer must be in recording state")
            
        vk.vkCmdBindPipeline(self.handle, pipeline_bind_point, pipeline)

    def bind_descriptor_sets(self, pipeline_bind_point: int,
                           layout: vk.VkPipelineLayout,
                           first_set: int,
                           descriptor_sets: List[vk.VkDescriptorSet],
                           dynamic_offsets: List[int] = None) -> None:
        """Bind descriptor sets."""
        if not self.is_recording:
            raise RuntimeError("Command buffer must be in recording state")
            
        vk.vkCmdBindDescriptorSets(
            self.handle,
            pipeline_bind_point,
            layout,
            first_set,
            len(descriptor_sets),
            descriptor_sets,
            len(dynamic_offsets or []),
            dynamic_offsets or []
        )

class CommandBufferManager:
    """Manages command pools and provides command buffer allocation."""
    
    def __init__(self, device: vk.VkDevice):
        self.device = device
        self.command_pools: Dict[int, CommandPool] = {}

    def create_pool(self, queue_family_index: int, transient: bool = False,
                   reset_command_buffer: bool = True) -> CommandPool:
        """Create a command pool for the specified queue family."""
        pool = CommandPool(self.device, queue_family_index, transient, reset_command_buffer)
        self.command_pools[queue_family_index] = pool
        return pool

    def get_command_buffers(self, queue_family_index: int,
                          allocate_info: CommandBufferAllocateInfo) -> List[CommandBuffer]:
        """Get command buffers from the specified pool."""
        pool = self.command_pools.get(queue_family_index)
        if not pool:
            raise RuntimeError(f"No command pool exists for queue family {queue_family_index}")

        vulkan_buffers = pool.allocate_buffers(allocate_info)
        return [CommandBuffer(self.device, buffer) for buffer in vulkan_buffers]

    def cleanup(self) -> None:
        """Clean up all command pools."""
        for pool in self.command_pools.values():
            pool.cleanup()
        self.command_pools.clear()