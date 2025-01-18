from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional
import vulkan as vk

class ImageType(Enum):
    TEXTURE_2D = auto()
    TEXTURE_3D = auto()
    TEXTURE_CUBE = auto()
    RENDER_TARGET = auto()
    DEPTH_STENCIL = auto()

@dataclass
class ImageCreateInfo:
    width: int
    height: int
    format: int
    usage: List[int]
    type: ImageType
    mip_levels: int = 1
    array_layers: int = 1
    depth: int = 1
    samples: int = vk.VK_SAMPLE_COUNT_1_BIT
    tiling: int = vk.VK_IMAGE_TILING_OPTIMAL
    memory_properties: int = vk.VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT
    sharing_mode: int = vk.VK_SHARING_MODE_EXCLUSIVE
    queue_family_indices: Optional[List[int]] = None

class ImageBase:
    """Base class for all image types."""
    def __init__(self, device: vk.VkDevice, memory_manager: 'MemoryManager',
                 create_info: ImageCreateInfo):
        self.device = device
        self.memory_manager = memory_manager
        self.create_info = create_info
        self.handle: Optional[vk.VkImage] = None
        self.view: Optional[vk.VkImageView] = None
        self.memory_allocation_id: Optional[int] = None
        self.current_layout: int = vk.VK_IMAGE_LAYOUT_UNDEFINED

    def cleanup(self) -> None:
        """Clean up image resources."""
        if self.view:
            vk.vkDestroyImageView(self.device, self.view, None)
            self.view = None
        if self.handle:
            vk.vkDestroyImage(self.device, self.handle, None)
            self.handle = None
        if self.memory_allocation_id:
            self.memory_manager.free(self.memory_allocation_id)
            self.memory_allocation_id = None