# command_pool.py
import vulkan as vk
import logging
from typing import Dict, List, Set, Tuple, Optional
from contextlib import contextmanager
from .command_types import CommandType, CommandPoolCreateInfo
from .command_validation import ValidationConfig, CommandValidator
from .command_memory import MemoryTracker
from .command_errors import CommandError, PoolError, ValidationError

logger = logging.getLogger(__name__)

class CommandPoolManager:
    """Manages Vulkan command pools with validation and memory tracking."""
    
    def __init__(self, device: vk.VkDevice, validation_config: Optional[ValidationConfig] = None):
        self.device = device
        self.validation_config = validation_config or ValidationConfig()
        self.validator = CommandValidator(self.validation_config)
        self.memory_tracker = MemoryTracker(self.validation_config)
        self.pools: Dict[Tuple[int, CommandType], List[vk.VkCommandPool]] = {}
        self._active_pools: Set[vk.VkCommandPool] = set()
        self._pool_types: Dict[vk.VkCommandPool, CommandType] = {}
        self._debug_names: Dict[vk.VkCommandPool, str] = {}

    def create_pool(self, create_info: CommandPoolCreateInfo) -> vk.VkCommandPool:
        """Create a new command pool with validation and memory tracking."""
        try:
            self.validator.validate_pool_creation(create_info.command_type)

            pool_info = vk.VkCommandPoolCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
                queueFamilyIndex=create_info.queue_family_index,
                flags=create_info.to_vk_flags()
            )

            pool = vk.vkCreateCommandPool(self.device, pool_info, None)
            key = (create_info.queue_family_index, create_info.command_type)

            if key not in self.pools:
                self.pools[key] = []
            self.pools[key].append(pool)
            self._active_pools.add(pool)
            self._pool_types[pool] = create_info.command_type

            # Track memory allocation (estimation)
            estimated_size = 4096  # Base size estimation
            self.memory_tracker.track_pool_allocation(pool, estimated_size, create_info.command_type)

            debug_name = f"pool_{id(pool)}_{create_info.command_type.name}"
            self._debug_names[pool] = debug_name
            if self.validator.config.enable_debug_markers:
                self.validator.begin_debug_marker(debug_name)

            logger.debug(f"Created command pool {debug_name}")
            return pool

        except Exception as e:
            logger.error(f"Failed to create command pool: {e}")
            self._handle_pool_creation_error(e)
            raise

    def get_pool(self, command_type: CommandType, queue_family_index: int) -> vk.VkCommandPool:
        """Get an existing pool or create a new one."""
        key = (queue_family_index, command_type)
        
        # Try to reuse an existing pool
        if key in self.pools and self.pools[key]:
            return self.pools[key][0]
        
        # Create new pool if none exists
        create_info = CommandPoolCreateInfo(
            queue_family_index=queue_family_index,
            command_type=command_type
        )
        return self.create_pool(create_info)

    def reset_pool(self, pool: vk.VkCommandPool, release_resources: bool = False) -> None:
        """Reset a command pool."""
        if pool not in self._active_pools:
            raise PoolError("Attempting to reset an unmanaged pool")
            
        flags = vk.VK_COMMAND_POOL_RESET_RELEASE_RESOURCES_BIT if release_resources else 0
        try:
            vk.vkResetCommandPool(self.device, pool, flags)
            debug_name = self._debug_names.get(pool, str(pool))
            logger.debug(f"Reset command pool {debug_name}")
        except Exception as e:
            logger.error(f"Failed to reset command pool: {e}")
            raise

    def trim_pool(self, pool: vk.VkCommandPool) -> None:
        """Trim a command pool to potentially free memory."""
        if pool not in self._active_pools:
            raise PoolError("Attempting to trim an unmanaged pool")
            
        try:
            vk.vkTrimCommandPool(self.device, pool, 0)
            debug_name = self._debug_names.get(pool, str(pool))
            logger.debug(f"Trimmed command pool {debug_name}")
        except Exception as e:
            logger.error(f"Failed to trim command pool: {e}")
            raise

    def _cleanup_unused_pools(self) -> None:
        """Clean up old or unused pools."""
        try:
            # Get oldest pools that might be candidates for cleanup
            oldest_pools = self.memory_tracker.get_oldest_pools(
                self.validation_config.pool_reuse_threshold
            )

            for pool in oldest_pools:
                if pool in self._active_pools:
                    cmd_type = self._pool_types.get(pool)
                    if cmd_type and self.validator.pool_counts[cmd_type] > 1:
                        self._destroy_pool(pool)

        except Exception as e:
            logger.error(f"Error during pool cleanup: {e}")

    def _destroy_pool(self, pool: vk.VkCommandPool) -> None:
        """Destroy a specific command pool."""
        try:
            if pool in self._active_pools:
                debug_name = self._debug_names.get(pool, str(pool))
                if self.validator.config.enable_debug_markers:
                    self.validator.end_debug_marker(debug_name)

                vk.vkDestroyCommandPool(self.device, pool, None)
                self._active_pools.remove(pool)
                cmd_type = self._pool_types.pop(pool, None)
                self._debug_names.pop(pool, None)

                if cmd_type:
                    for key, pools in self.pools.items():
                        if pool in pools:
                            pools.remove(pool)
                            break

                self.memory_tracker.track_pool_deallocation(pool)
                self.validator.track_memory_deallocated(pool)
                logger.debug(f"Destroyed command pool {debug_name}")

        except Exception as e:
            logger.error(f"Error destroying command pool: {e}")
            raise

    def cleanup(self) -> None:
        """Clean up all command pools."""
        try:
            vk.vkDeviceWaitIdle(self.device)
            
            for pool in list(self._active_pools):
                self._destroy_pool(pool)
                
            self.pools.clear()
            self._active_pools.clear()
            self._pool_types.clear()
            self._debug_names.clear()
            
            self.memory_tracker.reset_stats()
            logger.info("Command pool manager cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during command pool manager cleanup: {e}")
            raise

    def get_memory_stats(self):
        """Get current memory statistics."""
        return self.memory_tracker.get_stats()
