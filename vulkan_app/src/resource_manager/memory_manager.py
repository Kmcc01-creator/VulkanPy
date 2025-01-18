import vulkan as vk
import logging
from typing import Dict, Optional, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MemoryAllocation:
    memory: vk.VkDeviceMemory
    size: int
    offset: int
    mapped_ptr: Optional[int] = None
    is_persistent: bool = False

class MemoryManager:
    """Manages Vulkan memory allocations with support for suballocation."""
    
    def __init__(self, device: vk.VkDevice, physical_device: vk.VkPhysicalDevice):
        self.device = device
        self.physical_device = physical_device
        self.memory_properties = vk.vkGetPhysicalDeviceMemoryProperties(physical_device)
        self.allocations: Dict[int, MemoryAllocation] = {}
        self.allocation_counter = 0
        
    def find_memory_type(self, type_filter: int, properties: int) -> int:
        """Find a suitable memory type index."""
        for i in range(self.memory_properties.memoryTypeCount):
            if (type_filter & (1 << i)) and \
               (self.memory_properties.memoryTypes[i].propertyFlags & properties) == properties:
                return i
        raise RuntimeError("Failed to find suitable memory type")

    def allocate(self, size: int, memory_type_index: int,
                alignment: int = 1, persistent_map: bool = False) -> int:
        """Allocate memory and return allocation ID."""
        try:
            alloc_info = vk.VkMemoryAllocateInfo(
                sType=vk.VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
                allocationSize=size,
                memoryTypeIndex=memory_type_index
            )
            
            memory = vk.vkAllocateMemory(self.device, alloc_info, None)
            mapped_ptr = None
            
            if persistent_map:
                mapped_ptr = vk.vkMapMemory(self.device, memory, 0, size, 0)
            
            allocation = MemoryAllocation(
                memory=memory,
                size=size,
                offset=0,
                mapped_ptr=mapped_ptr,
                is_persistent=persistent_map
            )
            
            self.allocation_counter += 1
            self.allocations[self.allocation_counter] = allocation
            
            logger.debug(f"Allocated memory: id={self.allocation_counter}, size={size}")
            return self.allocation_counter
            
        except Exception as e:
            logger.error(f"Failed to allocate memory: {e}")
            raise

    def free(self, allocation_id: int) -> None:
        """Free a memory allocation."""
        if allocation_id not in self.allocations:
            logger.warning(f"Attempting to free non-existent allocation: {allocation_id}")
            return
            
        allocation = self.allocations[allocation_id]
        
        try:
            if allocation.is_persistent:
                vk.vkUnmapMemory(self.device, allocation.memory)
                
            vk.vkFreeMemory(self.device, allocation.memory, None)
            del self.allocations[allocation_id]
            
            logger.debug(f"Freed memory allocation: {allocation_id}")
            
        except Exception as e:
            logger.error(f"Failed to free memory allocation {allocation_id}: {e}")
            raise

    def map(self, allocation_id: int, offset: int = 0, size: Optional[int] = None) -> int:
        """Map memory for CPU access."""
        if allocation_id not in self.allocations:
            raise RuntimeError(f"Invalid allocation ID: {allocation_id}")
            
        allocation = self.allocations[allocation_id]
        if allocation.is_persistent:
            return allocation.mapped_ptr + offset
            
        if size is None:
            size = allocation.size - offset
            
        try:
            ptr = vk.vkMapMemory(
                self.device,
                allocation.memory,
                allocation.offset + offset,
                size,
                0
            )
            return ptr
            
        except Exception as e:
            logger.error(f"Failed to map memory: {e}")
            raise

    def unmap(self, allocation_id: int) -> None:
        """Unmap memory."""
        if allocation_id not in self.allocations:
            raise RuntimeError(f"Invalid allocation ID: {allocation_id}")
            
        allocation = self.allocations[allocation_id]
        if not allocation.is_persistent:
            vk.vkUnmapMemory(self.device, allocation.memory)

    def flush(self, allocation_id: int, offset: int = 0, size: Optional[int] = None) -> None:
        """Flush mapped memory."""
        if allocation_id not in self.allocations:
            raise RuntimeError(f"Invalid allocation ID: {allocation_id}")
            
        allocation = self.allocations[allocation_id]
        if size is None:
            size = allocation.size - offset
            
        mapped_range = vk.VkMappedMemoryRange(
            sType=vk.VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE,
            memory=allocation.memory,
            offset=allocation.offset + offset,
            size=size
        )
        
        vk.vkFlushMappedMemoryRanges(self.device, 1, [mapped_range])

    def invalidate(self, allocation_id: int, offset: int = 0, size: Optional[int] = None) -> None:
        """Invalidate mapped memory."""
        if allocation_id not in self.allocations:
            raise RuntimeError(f"Invalid allocation ID: {allocation_id}")
            
        allocation = self.allocations[allocation_id]
        if size is None:
            size = allocation.size - offset
            
        mapped_range = vk.VkMappedMemoryRange(
            sType=vk.VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE,
            memory=allocation.memory,
            offset=allocation.offset + offset,
            size=size
        )
        
        vk.vkInvalidateMappedMemoryRanges(self.device, 1, [mapped_range])

    def cleanup(self) -> None:
        """Clean up all allocations."""
        for allocation_id in list(self.allocations.keys()):
            self.free(allocation_id)
        logger.info("Cleaned up all memory allocations")