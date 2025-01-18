import vulkan as vk
import logging
from typing import Dict, Optional, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MemoryAllocation:
    memory: vk.VkDeviceMemory
    size: int
    memory_type_index: int
    is_free: bool = False

class MemoryAllocator:
    def __init__(self, device: vk.VkDevice, physical_device: vk.VkPhysicalDevice):
        self.device = device
        self.physical_device = physical_device
        self.memory_properties = vk.vkGetPhysicalDeviceMemoryProperties(physical_device)
        self.allocations: Dict[vk.VkDeviceMemory, MemoryAllocation] = {}
        self.total_allocated = 0
        self.active_allocations: Set[vk.VkDeviceMemory] = set()
        
    def find_memory_type(self, type_filter: int, properties: int) -> int:
        """Find a suitable memory type index."""
        for i in range(self.memory_properties.memoryTypeCount):
            type_supported = type_filter & (1 << i)
            properties_supported = (
                self.memory_properties.memoryTypes[i].propertyFlags & properties
            ) == properties
            
            if type_supported and properties_supported:
                return i
                
        raise RuntimeError("Failed to find suitable memory type")
        
    def allocate_memory(self, requirements: vk.VkMemoryRequirements, 
                       properties: int) -> vk.VkDeviceMemory:
        """Allocate device memory."""
        try:
            memory_type_index = self.find_memory_type(
                requirements.memoryTypeBits,
                properties
            )
            
            # Check if we can reuse any freed memory
            for memory, allocation in self.allocations.items():
                if (allocation.is_free and 
                    allocation.size >= requirements.size and
                    allocation.memory_type_index == memory_type_index):
                    allocation.is_free = False
                    self.active_allocations.add(memory)
                    return memory
            
            # Allocate new memory if no suitable freed memory found
            alloc_info = vk.VkMemoryAllocateInfo(
                sType=vk.VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
                allocationSize=requirements.size,
                memoryTypeIndex=memory_type_index
            )
            
            memory = vk.vkAllocateMemory(self.device, alloc_info, None)
            self.allocations[memory] = MemoryAllocation(
                memory=memory,
                size=requirements.size,
                memory_type_index=memory_type_index
            )
            self.active_allocations.add(memory)
            self.total_allocated += requirements.size
            
            logger.debug(
                f"Allocated {requirements.size} bytes of memory "
                f"(total: {self.total_allocated} bytes)"
            )
            return memory
            
        except Exception as e:
            raise RuntimeError(f"Failed to allocate memory: {str(e)}")
            
    def free_memory(self, memory: vk.VkDeviceMemory):
        """Free device memory."""
        if memory not in self.allocations:
            logger.warning("Attempted to free untracked memory")
            return
            
        allocation = self.allocations[memory]
        if not allocation.is_free:
            allocation.is_free = True
            self.active_allocations.remove(memory)
            logger.debug(
                f"Freed {allocation.size} bytes of memory "
                f"(total allocated: {self.total_allocated} bytes)"
            )
            
    def cleanup(self):
        """Clean up all allocated memory."""
        try:
            for memory in self.allocations.keys():
                if memory in self.active_allocations:
                    vk.vkFreeMemory(self.device, memory, None)
            
            self.allocations.clear()
            self.active_allocations.clear()
            self.total_allocated = 0
            logger.info("Memory allocator cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during memory allocator cleanup: {str(e)}")
            
    def get_stats(self) -> dict:
        """Get memory allocation statistics."""
        return {
            "total_allocated": self.total_allocated,
            "active_allocations": len(self.active_allocations),
            "total_allocations": len(self.allocations),
            "freed_allocations": len(self.allocations) - len(self.active_allocations)
        }