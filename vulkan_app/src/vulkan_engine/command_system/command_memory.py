
# src/vulkan_engine/command_system/command_memory.py
from dataclasses import dataclass, field
from typing import Dict, Optional, List
import time
import logging

logger = logging.getLogger(__name__)

@dataclass
class MemoryAllocation:
    size: int
    timestamp: float
    pool: vk.VkCommandPool
    command_type: CommandType

@dataclass
class MemoryStats:
    total_allocated: int = 0
    peak_allocation: int = 0
    allocation_count: int = 0
    deallocation_count: int = 0
    current_pool_memory: Dict[vk.VkCommandPool, int] = field(default_factory=dict)
    allocations: List[MemoryAllocation] = field(default_factory=list)

    def add_allocation(self, allocation: MemoryAllocation) -> None:
        self.allocations.append(allocation)
        self.total_allocated += allocation.size
        self.allocation_count += 1
        self.current_pool_memory[allocation.pool] = (
            self.current_pool_memory.get(allocation.pool, 0) + allocation.size
        )
        self.peak_allocation = max(self.peak_allocation, self.total_allocated)

    def remove_allocation(self, pool: vk.VkCommandPool) -> None:
        size = self.current_pool_memory.pop(pool, 0)
        self.total_allocated -= size
        self.deallocation_count += 1
        self.allocations = [a for a in self.allocations if a.pool != pool]

class MemoryTracker:
    def __init__(self, validation_config: ValidationConfig):
        self.config = validation_config
        self.stats = MemoryStats()
        self._pool_allocations: Dict[vk.VkCommandPool, MemoryAllocation] = {}

    def track_pool_allocation(self, pool: vk.VkCommandPool, size: int, command_type: CommandType) -> None:
        if not self.config.track_memory_usage:
            return

        allocation = MemoryAllocation(
            size=size,
            timestamp=time.time(),
            pool=pool,
            command_type=command_type
        )

        self._pool_allocations[pool] = allocation
        self.stats.add_allocation(allocation)

        if self.stats.total_allocated > self.config.memory_limit_mb * 1024 * 1024:
            logger.warning(
                f"Memory usage ({self.stats.total_allocated} bytes) exceeds "
                f"configured limit ({self.config.memory_limit_mb} MB)"
            )

    def track_pool_deallocation(self, pool: vk.VkCommandPool) -> None:
        if not self.config.track_memory_usage:
            return

        if pool in self._pool_allocations:
            self.stats.remove_allocation(pool)
            del self._pool_allocations[pool]

    def get_stats(self) -> MemoryStats:
        return self.stats

    def reset_stats(self) -> None:
        self.stats = MemoryStats()
        self._pool_allocations.clear()

    def get_pool_age(self, pool: vk.VkCommandPool) -> Optional[float]:
        """Get the age of a pool in seconds."""
        allocation = self._pool_allocations.get(pool)
        if allocation:
            return time.time() - allocation.timestamp
        return None

    def get_oldest_pools(self, count: int) -> List[vk.VkCommandPool]:
        """Get the oldest pools by allocation time."""
        sorted_pools = sorted(
            self._pool_allocations.items(),
            key=lambda x: x[1].timestamp
        )
        return [pool for pool, _ in sorted_pools[:count]]

    def get_memory_usage_by_type(self) -> Dict[CommandType, int]:
        """Get memory usage grouped by command type."""
        usage = {cmd_type: 0 for cmd_type in CommandType}
        for allocation in self._pool_allocations.values():
            usage[allocation.command_type] += allocation.size
        return usage