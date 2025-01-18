import vulkan as vk
import logging
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from contextlib import contextmanager
from .command_types import CommandType, CommandLevel
from .command_errors import BufferError, ValidationError

logger = logging.getLogger(__name__)

@dataclass
class CommandBufferAllocation:
    """Represents an allocated command buffer and its metadata."""
    buffer: vk.VkCommandBuffer
    pool: vk.VkCommandPool
    type: CommandType
    level: CommandLevel
    debug_name: str

class CommandBufferManager:
    """Manages command buffers with efficient recycling and memory tracking."""
    
    def __init__(self, device: vk.VkDevice, pool_manager: 'CommandPoolManager'):
        self.device = device
        self.pool_manager = pool_manager
        self.validation_config = pool_manager.validation_config
        self.validator = pool_manager.validator
        
        # Initialize buffer pools for each combination of type and level
        self.available_buffers: Dict[Tuple[CommandType, CommandLevel], List[CommandBufferAllocation]] = {
            (cmd_type, level): []
            for cmd_type in CommandType
            for level in CommandLevel
        }
        
        # Keep track of active buffers
        self.active_buffers: Set[vk.VkCommandBuffer] = set()
        self._buffer_debug_names: Dict[vk.VkCommandBuffer, str] = {}
        self._buffer_usage_count: Dict[vk.VkCommandBuffer, int] = {}

    def get_command_buffer(self,
                          command_type: CommandType,
                          queue_family_index: int,
                          level: CommandLevel = CommandLevel.PRIMARY,
                          begin_immediately: bool = True) -> CommandBufferAllocation:
        """
        Get a command buffer, either recycled or newly allocated.
        
        Args:
            command_type: Type of command buffer (GRAPHICS, COMPUTE, TRANSFER)
            queue_family_index: Index of the queue family
            level: Command buffer level (PRIMARY or SECONDARY)
            begin_immediately: Whether to begin the command buffer immediately
            
        Returns:
            CommandBufferAllocation object containing the buffer and its metadata
            
        Raises:
            BufferError: If buffer allocation fails
            ValidationError: If validation constraints are violated
        """
        try:
            # Try to reuse an available buffer
            key = (command_type, level)
            allocation = None
            
            if self.available_buffers[key]:
                allocation = self.available_buffers[key].pop()
                vk.vkResetCommandBuffer(allocation.buffer, 0)
                logger.debug(f"Reusing command buffer {allocation.debug_name}")
            else:
                # Get a pool and allocate new buffer
                pool = self.pool_manager.get_pool(command_type, queue_family_index)
                self.validator.validate_buffer_allocation(pool)
                
                buffer = self._allocate_command_buffer(pool, level)
                debug_name = f"cmd_{id(buffer)}_{command_type.name}"
                allocation = CommandBufferAllocation(
                    buffer=buffer,
                    pool=pool,
                    type=command_type,
                    level=level,
                    debug_name=debug_name
                )
                self._buffer_debug_names[buffer] = debug_name
                self._buffer_usage_count[buffer] = 0
                logger.debug(f"Allocated new command buffer {debug_name}")

            if begin_immediately:
                self._begin_command_buffer(allocation)

            self.active_buffers.add(allocation.buffer)
            self._buffer_usage_count[allocation.buffer] += 1

            if self.validator.config.enable_debug_markers:
                self.validator.begin_debug_marker(allocation.debug_name)

            return allocation

        except Exception as e:
            logger.error(f"Failed to get command buffer: {e}")
            self._handle_buffer_allocation_error(e)
            raise

    def _allocate_command_buffer(self,
                               pool: vk.VkCommandPool,
                               level: CommandLevel) -> vk.VkCommandBuffer:
        """
        Allocate a new command buffer from a pool.
        
        Args:
            pool: Command pool to allocate from
            level: Command buffer level
            
        Returns:
            Newly allocated command buffer
            
        Raises:
            BufferError: If allocation fails
        """
        alloc_info = vk.VkCommandBufferAllocateInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
            commandPool=pool,
            level=level.to_vk_level(),
            commandBufferCount=1
        )
        
        try:
            return vk.vkAllocateCommandBuffers(self.device, alloc_info)[0]
        except Exception as e:
            logger.error(f"Failed to allocate command buffer: {e}")
            raise BufferError(f"Command buffer allocation failed: {str(e)}")

    def _begin_command_buffer(self, allocation: CommandBufferAllocation) -> None:
        """
        Begin recording a command buffer.
        
        Args:
            allocation: Command buffer allocation to begin
            
        Raises:
            BufferError: If beginning the command buffer fails
        """
        begin_info = vk.VkCommandBufferBeginInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
            flags=vk.VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT
        )
        
        try:
            vk.vkBeginCommandBuffer(allocation.buffer, begin_info)
            logger.debug(f"Started recording command buffer {allocation.debug_name}")
        except Exception as e:
            logger.error(f"Failed to begin command buffer: {e}")
            raise BufferError(f"Failed to begin command buffer: {str(e)}")

    @contextmanager
    def command_buffer_scope(self,
                           command_type: CommandType,
                           queue_family_index: int,
                           queue: Optional[vk.VkQueue] = None,
                           level: CommandLevel = CommandLevel.PRIMARY) -> CommandBufferAllocation:
        """
        Context manager for automatic command buffer lifecycle management.
        
        Args:
            command_type: Type of command buffer
            queue_family_index: Index of the queue family
            queue: Optional queue for automatic submission
            level: Command buffer level
            
        Yields:
            CommandBufferAllocation object
        """
        allocation = self.get_command_buffer(command_type, queue_family_index, level)
        try:
            yield allocation
        finally:
            if queue:
                self.end_and_submit_command_buffer(allocation, queue)
            else:
                self.recycle_command_buffer(allocation)

    def end_and_submit_command_buffer(self,
                                    allocation: CommandBufferAllocation,
                                    queue: vk.VkQueue,
                                    wait_semaphores: List[vk.VkSemaphore] = None,
                                    signal_semaphores: List[vk.VkSemaphore] = None,
                                    fence: Optional[vk.VkFence] = None) -> None:
        """
        End and submit a command buffer with optional synchronization.
        
        Args:
            allocation: Command buffer allocation to submit
            queue: Queue to submit to
            wait_semaphores: Optional list of semaphores to wait on
            signal_semaphores: Optional list of semaphores to signal
            fence: Optional fence to signal
            
        Raises:
            BufferError: If ending or submitting the command buffer fails
        """
        try:
            vk.vkEndCommandBuffer(allocation.buffer)
            
            submit_info = vk.VkSubmitInfo(
                sType=vk.VK_STRUCTURE_TYPE_SUBMIT_INFO,
                waitSemaphoreCount=len(wait_semaphores or []),
                pWaitSemaphores=wait_semaphores,
                pWaitDstStageMask=[vk.VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT] * (len(wait_semaphores or [])),
                commandBufferCount=1,
                pCommandBuffers=[allocation.buffer],
                signalSemaphoreCount=len(signal_semaphores or []),
                pSignalSemaphores=signal_semaphores
            )
            
            vk.vkQueueSubmit(queue, 1, [submit_info], fence)
            logger.debug(f"Submitted command buffer {allocation.debug_name}")
            
            self.recycle_command_buffer(allocation)
            
        except Exception as e:
            logger.error(f"Failed to end and submit command buffer: {e}")
            raise BufferError(f"Failed to end and submit command buffer: {str(e)}")

    def recycle_command_buffer(self, allocation: CommandBufferAllocation) -> None:
        """
        Recycle a command buffer for reuse.
        
        Args:
            allocation: Command buffer allocation to recycle
        """
        if allocation.buffer in self.active_buffers:
            self.active_buffers.remove(allocation.buffer)
            key = (allocation.type, allocation.level)
            self.available_buffers[key].append(allocation)

            if self.validator.config.enable_debug_markers:
                self.validator.end_debug_marker(allocation.debug_name)

            logger.debug(f"Recycled command buffer {allocation.debug_name}")

    def _handle_buffer_allocation_error(self, error: Exception) -> None:
        """
        Handle errors during buffer allocation.
        
        Args:
            error: The exception that occurred
        """
        if isinstance(error, ValidationError):
            logger.error(f"Buffer allocation constraint violation: {error}")
            self._recycle_unused_buffers()
        else:
            logger.error(f"Unexpected error during buffer allocation: {error}")

    def _recycle_unused_buffers(self) -> None:
        """Force recycling of unused buffers."""
        try:
            recycled_count = 0
            for key, buffers in self.available_buffers.items():
                # Keep only recently used buffers
                recent_buffers = [
                    alloc for alloc in buffers
                    if self._buffer_usage_count.get(alloc.buffer, 0) > 0
                ]
                recycled_count += len(buffers) - len(recent_buffers)
                self.available_buffers[key] = recent_buffers

            if recycled_count > 0:
                logger.debug(f"Recycled {recycled_count} unused command buffers")
        except Exception as e:
            logger.error(f"Error during buffer recycling: {e}")

    def cleanup(self) -> None:
        """
        Clean up all command buffer resources.
        
        This method should be called when shutting down or recreating the command buffer system.
        """
        try:
            # Wait for device to be idle before cleanup
            vk.vkDeviceWaitIdle(self.device)

            # Clear all buffers
            self.active_buffers.clear()
            for buffers in self.available_buffers.values():
                buffers.clear()

            # Clear tracking maps
            self._buffer_debug_names.clear()
            self._buffer_usage_count.clear()

            logger.info("Command buffer manager cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during command buffer manager cleanup: {e}")
            raise

    def get_buffer_stats(self) -> Dict[str, int]:
        """
        Get statistics about buffer usage.
        
        Returns:
            Dictionary containing buffer statistics
        """
        return {
            "active_buffers": len(self.active_buffers),
            "available_buffers": sum(len(buffers) for buffers in self.available_buffers.values()),
            "total_allocations": len(self._buffer_usage_count)
        }