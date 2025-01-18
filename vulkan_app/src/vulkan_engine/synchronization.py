import vulkan as vk
import logging
from typing import Optional, List, Dict, Set
from enum import Enum, auto
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

class SyncObjectType(Enum):
    FENCE = auto()
    BINARY_SEMAPHORE = auto()
    TIMELINE_SEMAPHORE = auto()

@dataclass
class TimelineSemaphoreCreateInfo:
    initial_value: int = 0

class SynchronizationManager:
    """Manages synchronization objects (fences and semaphores)."""
    
    def __init__(self, device: vk.VkDevice):
        self.device = device
        self.fences: Dict[str, vk.VkFence] = {}
        self.semaphores: Dict[str, vk.VkSemaphore] = {}
        self.timeline_values: Dict[str, int] = {}  # For timeline semaphores
        
    def create_fence(self, name: str, signaled: bool = False) -> vk.VkFence:
        """Create a fence with the given name."""
        if name in self.fences:
            raise RuntimeError(f"Fence '{name}' already exists")
            
        flags = vk.VK_FENCE_CREATE_SIGNALED_BIT if signaled else 0
        create_info = vk.VkFenceCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_FENCE_CREATE_INFO,
            flags=flags
        )
        
        try:
            fence = vk.vkCreateFence(self.device, create_info, None)
            self.fences[name] = fence
            logger.debug(f"Created fence '{name}'")
            return fence
        except Exception as e:
            raise RuntimeError(f"Failed to create fence: {str(e)}")
            
    def create_semaphore(self, name: str, 
                        semaphore_type: SyncObjectType = SyncObjectType.BINARY_SEMAPHORE,
                        timeline_info: Optional[TimelineSemaphoreCreateInfo] = None) -> vk.VkSemaphore:
        """Create a semaphore with the given name."""
        if name in self.semaphores:
            raise RuntimeError(f"Semaphore '{name}' already exists")
            
        type_create_info = None
        if semaphore_type == SyncObjectType.TIMELINE_SEMAPHORE:
            if timeline_info is None:
                timeline_info = TimelineSemaphoreCreateInfo()
            type_create_info = vk.VkSemaphoreTypeCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_SEMAPHORE_TYPE_CREATE_INFO,
                semaphoreType=vk.VK_SEMAPHORE_TYPE_TIMELINE,
                initialValue=timeline_info.initial_value
            )
            
        create_info = vk.VkSemaphoreCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO,
            pNext=type_create_info
        )
        
        try:
            semaphore = vk.vkCreateSemaphore(self.device, create_info, None)
            self.semaphores[name] = semaphore
            if semaphore_type == SyncObjectType.TIMELINE_SEMAPHORE:
                self.timeline_values[name] = timeline_info.initial_value
            logger.debug(f"Created semaphore '{name}' of type {semaphore_type.name}")
            return semaphore
        except Exception as e:
            raise RuntimeError(f"Failed to create semaphore: {str(e)}")

    def wait_for_fence(self, name: str, timeout: int = None) -> bool:
        """Wait for a fence to be signaled."""
        fence = self.fences.get(name)
        if fence is None:
            raise RuntimeError(f"Fence '{name}' does not exist")
            
        timeout_ns = timeout if timeout is not None else int(1e9)  # Default 1 second
        try:
            result = vk.vkWaitForFences(self.device, 1, [fence], vk.VK_TRUE, timeout_ns)
            return result == vk.VK_SUCCESS
        except Exception as e:
            logger.error(f"Failed to wait for fence '{name}': {str(e)}")
            return False

    def wait_for_fences(self, names: List[str], wait_all: bool = True, 
                       timeout: int = None) -> bool:
        """Wait for multiple fences."""
        fences = [self.fences.get(name) for name in names]
        if None in fences:
            missing = [name for name, fence in zip(names, fences) if fence is None]
            raise RuntimeError(f"Fences do not exist: {missing}")
            
        timeout_ns = timeout if timeout is not None else int(1e9)
        try:
            result = vk.vkWaitForFences(
                self.device,
                len(fences),
                fences,
                vk.VK_TRUE if wait_all else vk.VK_FALSE,
                timeout_ns
            )
            return result == vk.VK_SUCCESS
        except Exception as e:
            logger.error(f"Failed to wait for fences: {str(e)}")
            return False

    def reset_fence(self, name: str) -> None:
        """Reset a fence to unsignaled state."""
        fence = self.fences.get(name)
        if fence is None:
            raise RuntimeError(f"Fence '{name}' does not exist")
            
        try:
            vk.vkResetFences(self.device, 1, [fence])
        except Exception as e:
            raise RuntimeError(f"Failed to reset fence: {str(e)}")

    def reset_fences(self, names: List[str]) -> None:
        """Reset multiple fences."""
        fences = [self.fences.get(name) for name in names]
        if None in fences:
            missing = [name for name, fence in zip(names, fences) if fence is None]
            raise RuntimeError(f"Fences do not exist: {missing}")
            
        try:
            vk.vkResetFences(self.device, len(fences), fences)
        except Exception as e:
            raise RuntimeError(f"Failed to reset fences: {str(e)}")

    def wait_semaphore(self, name: str, wait_value: int, timeout: int = None) -> bool:
        """Wait for a timeline semaphore to reach a specific value."""
        semaphore = self.semaphores.get(name)
        if semaphore is None:
            raise RuntimeError(f"Semaphore '{name}' does not exist")
            
        if name not in self.timeline_values:
            raise RuntimeError(f"Semaphore '{name}' is not a timeline semaphore")
            
        wait_info = vk.VkSemaphoreWaitInfo(
            sType=vk.VK_STRUCTURE_TYPE_SEMAPHORE_WAIT_INFO,
            semaphoreCount=1,
            pSemaphores=[semaphore],
            pValues=[wait_value]
        )
        
        timeout_ns = timeout if timeout is not None else int(1e9)
        try:
            result = vk.vkWaitSemaphores(self.device, wait_info, timeout_ns)
            return result == vk.VK_SUCCESS
        except Exception as e:
            logger.error(f"Failed to wait for semaphore '{name}': {str(e)}")
            return False

    def signal_semaphore(self, name: str, signal_value: int) -> None:
        """Signal a timeline semaphore with a specific value."""
        semaphore = self.semaphores.get(name)
        if semaphore is None:
            raise RuntimeError(f"Semaphore '{name}' does not exist")
            
        if name not in self.timeline_values:
            raise RuntimeError(f"Semaphore '{name}' is not a timeline semaphore")
            
        signal_info = vk.VkSemaphoreSignalInfo(
            sType=vk.VK_STRUCTURE_TYPE_SEMAPHORE_SIGNAL_INFO,
            semaphore=semaphore,
            value=signal_value
        )
        
        try:
            vk.vkSignalSemaphore(self.device, signal_info)
            self.timeline_values[name] = signal_value
        except Exception as e:
            raise RuntimeError(f"Failed to signal semaphore: {str(e)}")

    def get_semaphore_counter_value(self, name: str) -> int:
        """Get the current value of a timeline semaphore."""
        semaphore = self.semaphores.get(name)
        if semaphore is None:
            raise RuntimeError(f"Semaphore '{name}' does not exist")
            
        if name not in self.timeline_values:
            raise RuntimeError(f"Semaphore '{name}' is not a timeline semaphore")
            
        return vk.vkGetSemaphoreCounterValue(self.device, semaphore)

    def cleanup(self) -> None:
        """Clean up all synchronization objects."""
        for fence in self.fences.values():
            vk.vkDestroyFence(self.device, fence, None)
        self.fences.clear()
        
        for semaphore in self.semaphores.values():
            vk.vkDestroySemaphore(self.device, semaphore, None)
        self.semaphores.clear()
        self.timeline_values.clear()
        
        logger.info("Cleaned up all synchronization objects")