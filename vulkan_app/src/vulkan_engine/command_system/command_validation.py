
# src/vulkan_engine/command_system/command_validation.py
import logging
from dataclasses import dataclass
from typing import Dict, Set, Optional
from .command_types import CommandType
from .command_errors import ValidationError

logger = logging.getLogger(__name__)

@dataclass
class ValidationConfig:
    enable_validation: bool = True
    track_memory_usage: bool = True
    memory_limit_mb: float = 256  # Default 256MB limit
    max_pools_per_type: int = 10
    max_buffers_per_pool: int = 100
    enable_debug_markers: bool = True
    pool_reuse_threshold: int = 5  # Number of pools to trigger cleanup
    buffer_reuse_threshold: int = 50  # Number of buffers to trigger cleanup

class CommandValidator:
    def __init__(self, config: ValidationConfig):
        self.config = config
        self.total_memory_used = 0
        self.pool_counts: Dict[CommandType, int] = {
            CommandType.GRAPHICS: 0,
            CommandType.COMPUTE: 0,
            CommandType.TRANSFER: 0
        }
        self.buffer_counts: Dict[vk.VkCommandPool, int] = {}
        self._active_markers: Set[str] = set()
        self._last_cleanup_memory = 0

    def validate_pool_creation(self, command_type: CommandType) -> None:
        if not self.config.enable_validation:
            return

        if self.pool_counts[command_type] >= self.config.max_pools_per_type:
            raise ValidationError(
                f"Maximum number of pools ({self.config.max_pools_per_type}) "
                f"reached for type {command_type.name}"
            )

        self.pool_counts[command_type] += 1

    def validate_buffer_allocation(self, pool: vk.VkCommandPool) -> None:
        if not self.config.enable_validation:
            return

        current_count = self.buffer_counts.get(pool, 0)
        if current_count >= self.config.max_buffers_per_pool:
            raise ValidationError(
                f"Maximum number of buffers ({self.config.max_buffers_per_pool}) "
                f"reached for pool {pool}"
            )

        self.buffer_counts[pool] = current_count + 1

    def track_memory_deallocated(self, pool: vk.VkCommandPool) -> None:
        if not self.config.enable_validation:
            return

        if pool in self.buffer_counts:
            del self.buffer_counts[pool]

        for cmd_type, count in self.pool_counts.items():
            if count > 0:
                self.pool_counts[cmd_type] -= 1

    def check_memory_threshold(self) -> bool:
        """Check if memory usage has crossed cleanup threshold."""
        if not self.config.track_memory_usage:
            return False

        memory_threshold = self.config.memory_limit_mb * 1024 * 1024 * 0.8  # 80% of limit
        return self.total_memory_used > memory_threshold

    def begin_debug_marker(self, name: str, color: Optional[tuple] = None) -> None:
        if not self.config.enable_debug_markers:
            return

        if name in self._active_markers:
            logger.warning(f"Debug marker '{name}' is already active")
            return

        self._active_markers.add(name)
        # Here you would call VK_EXT_debug_marker extension
        # Implementation depends on whether extension is available

    def end_debug_marker(self, name: str) -> None:
        if not self.config.enable_debug_markers:
            return

        if name not in self._active_markers:
            logger.warning(f"Attempting to end inactive debug marker '{name}'")
            return

        self._active_markers.remove(name)
        # Here you would call VK_EXT_debug_marker extension

    def should_cleanup_pools(self, command_type: CommandType) -> bool:
        """Check if pool cleanup should be triggered."""
        return self.pool_counts[command_type] >= self.config.pool_reuse_threshold

    def should_cleanup_buffers(self, pool: vk.VkCommandPool) -> bool:
        """Check if buffer cleanup should be triggered."""
        return self.buffer_counts.get(pool, 0) >= self.config.buffer_reuse_threshold
