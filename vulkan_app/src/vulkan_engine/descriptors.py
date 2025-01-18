import vulkan as vk
import logging
from typing import List, Dict, Optional, Union, Set
from dataclasses import dataclass
from enum import Enum, auto
from .buffer import Buffer

logger = logging.getLogger(__name__)

class DescriptorType(Enum):
    UNIFORM_BUFFER = auto()
    STORAGE_BUFFER = auto()
    COMBINED_IMAGE_SAMPLER = auto()
    STORAGE_IMAGE = auto()
    INPUT_ATTACHMENT = auto()

@dataclass
class DescriptorSetLayoutBinding:
    binding: int
    descriptor_type: DescriptorType
    stage_flags: int
    count: int = 1
    
    def to_vulkan_binding(self) -> vk.VkDescriptorSetLayoutBinding:
        descriptor_type_map = {
            DescriptorType.UNIFORM_BUFFER: vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
            DescriptorType.STORAGE_BUFFER: vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
            DescriptorType.COMBINED_IMAGE_SAMPLER: vk.VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
            DescriptorType.STORAGE_IMAGE: vk.VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,
            DescriptorType.INPUT_ATTACHMENT: vk.VK_DESCRIPTOR_TYPE_INPUT_ATTACHMENT
        }
        
        return vk.VkDescriptorSetLayoutBinding(
            binding=self.binding,
            descriptorType=descriptor_type_map[self.descriptor_type],
            descriptorCount=self.count,
            stageFlags=self.stage_flags,
            pImmutableSamplers=None
        )

class DescriptorSetLayout:
    """Manages descriptor set layouts."""
    
    def __init__(self, device: vk.VkDevice):
        self.device = device
        self.handle: Optional[vk.VkDescriptorSetLayout] = None
        self.bindings: Dict[int, DescriptorSetLayoutBinding] = {}

    def add_binding(self, binding: DescriptorSetLayoutBinding) -> None:
        """Add a new binding to the layout."""
        self.bindings[binding.binding] = binding

    def create(self) -> None:
        """Create the descriptor set layout."""
        vulkan_bindings = [
            binding.to_vulkan_binding()
            for binding in sorted(self.bindings.values(), key=lambda x: x.binding)
        ]

        create_info = vk.VkDescriptorSetLayoutCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
            bindingCount=len(vulkan_bindings),
            pBindings=vulkan_bindings
        )

        try:
            self.handle = vk.vkCreateDescriptorSetLayout(self.device, create_info, None)
            logger.debug(f"Created descriptor set layout with {len(vulkan_bindings)} bindings")
        except Exception as e:
            raise RuntimeError(f"Failed to create descriptor set layout: {str(e)}")

    def cleanup(self) -> None:
        """Clean up the descriptor set layout."""
        if self.handle:
            vk.vkDestroyDescriptorSetLayout(self.device, self.handle, None)
            self.handle = None

class DescriptorPool:
    """Manages descriptor pools with automatic resizing."""
    
    def __init__(self, device: vk.VkDevice, max_sets: int):
        self.device = device
        self.max_sets = max_sets
        self.handle: Optional[vk.VkDescriptorPool] = None
        self.pool_sizes: Dict[DescriptorType, int] = {}
        self.allocated_sets: Set[vk.VkDescriptorSet] = set()

    def add_size(self, descriptor_type: DescriptorType, count: int) -> None:
        """Add or update pool size for a descriptor type."""
        current = self.pool_sizes.get(descriptor_type, 0)
        self.pool_sizes[descriptor_type] = current + count

    def create(self) -> None:
        """Create the descriptor pool."""
        descriptor_type_map = {
            DescriptorType.UNIFORM_BUFFER: vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
            DescriptorType.STORAGE_BUFFER: vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
            DescriptorType.COMBINED_IMAGE_SAMPLER: vk.VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
            DescriptorType.STORAGE_IMAGE: vk.VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,
            DescriptorType.INPUT_ATTACHMENT: vk.VK_DESCRIPTOR_TYPE_INPUT_ATTACHMENT
        }

        pool_sizes = [
            vk.VkDescriptorPoolSize(
                type=descriptor_type_map[dtype],
                descriptorCount=count
            )
            for dtype, count in self.pool_sizes.items()
        ]

        create_info = vk.VkDescriptorPoolCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
            maxSets=self.max_sets,
            poolSizeCount=len(pool_sizes),
            pPoolSizes=pool_sizes,
            flags=vk.VK_DESCRIPTOR_POOL_CREATE_FREE_DESCRIPTOR_SET_BIT
        )

        try:
            self.handle = vk.vkCreateDescriptorPool(self.device, create_info, None)
            logger.debug(f"Created descriptor pool with {len(pool_sizes)} pool sizes")
        except Exception as e:
            raise RuntimeError(f"Failed to create descriptor pool: {str(e)}")

    def allocate_descriptor_sets(self, 
                               layouts: List[vk.VkDescriptorSetLayout], 
                               count: int = 1) -> List[vk.VkDescriptorSet]:
        """Allocate descriptor sets from the pool."""
        try:
            alloc_info = vk.VkDescriptorSetAllocateInfo(
                sType=vk.VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
                descriptorPool=self.handle,
                descriptorSetCount=count,
                pSetLayouts=layouts * count
            )

            descriptor_sets = vk.vkAllocateDescriptorSets(self.device, alloc_info)
            self.allocated_sets.update(descriptor_sets)
            return descriptor_sets

        except vk.VkError as e:
            if e.result == vk.VK_ERROR_OUT_OF_POOL_MEMORY:
                # Could implement pool resizing here if needed
                raise RuntimeError("Descriptor pool out of memory")
            raise

    def free_descriptor_sets(self, descriptor_sets: List[vk.VkDescriptorSet]) -> None:
        """Free descriptor sets back to the pool."""
        if not descriptor_sets:
            return

        try:
            vk.vkFreeDescriptorSets(self.device, self.handle, len(descriptor_sets), descriptor_sets)
            self.allocated_sets.difference_update(descriptor_sets)
        except Exception as e:
            logger.error(f"Failed to free descriptor sets: {str(e)}")

    def cleanup(self) -> None:
        """Clean up the descriptor pool."""
        if self.handle:
            vk.vkDestroyDescriptorPool(self.device, self.handle, None)
            self.handle = None
            self.allocated_sets.clear()

class DescriptorSetUpdater:
    """Helper class for updating descriptor sets."""
    
    def __init__(self, device: vk.VkDevice):
        self.device = device
        self.writes: List[vk.VkWriteDescriptorSet] = []
        self.buffer_infos: List[vk.VkDescriptorBufferInfo] = []
        self.image_infos: List[vk.VkDescriptorImageInfo] = []

    def write_buffer(self, 
                    descriptor_set: vk.VkDescriptorSet,
                    binding: int,
                    buffer: Buffer,
                    offset: int = 0,
                    range: int = vk.VK_WHOLE_SIZE,
                    descriptor_type: DescriptorType = DescriptorType.UNIFORM_BUFFER) -> None:
        """Add a buffer write operation."""
        descriptor_type_map = {
            DescriptorType.UNIFORM_BUFFER: vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
            DescriptorType.STORAGE_BUFFER: vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER
        }

        buffer_info = vk.VkDescriptorBufferInfo(
            buffer=buffer.handle,
            offset=offset,
            range=range
        )
        self.buffer_infos.append(buffer_info)

        write = vk.VkWriteDescriptorSet(
            sType=vk.VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
            dstSet=descriptor_set,
            dstBinding=binding,
            dstArrayElement=0,
            descriptorCount=1,
            descriptorType=descriptor_type_map[descriptor_type],
            pBufferInfo=[buffer_info]
        )
        self.writes.append(write)

    def write_image(self,
                   descriptor_set: vk.VkDescriptorSet,
                   binding: int,
                   image_view: vk.VkImageView,
                   sampler: vk.VkSampler,
                   layout: int,
                   descriptor_type: DescriptorType = DescriptorType.COMBINED_IMAGE_SAMPLER) -> None:
        """Add an image write operation."""
        descriptor_type_map = {
            DescriptorType.COMBINED_IMAGE_SAMPLER: vk.VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
            DescriptorType.STORAGE_IMAGE: vk.VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,
            DescriptorType.INPUT_ATTACHMENT: vk.VK_DESCRIPTOR_TYPE_INPUT_ATTACHMENT
        }

        image_info = vk.VkDescriptorImageInfo(
            sampler=sampler,
            imageView=image_view,
            imageLayout=layout
        )
        self.image_infos.append(image_info)

        write = vk.VkWriteDescriptorSet(
            sType=vk.VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
            dstSet=descriptor_set,
            dstBinding=binding,
            dstArrayElement=0,
            descriptorCount=1,
            descriptorType=descriptor_type_map[descriptor_type],
            pImageInfo=[image_info]
        )
        self.writes.append(write)

    def update(self) -> None:
        """Perform all queued descriptor updates."""
        if self.writes:
            vk.vkUpdateDescriptorSets(self.device, len(self.writes), self.writes, 0, None)
            self.writes.clear()
            self.buffer_infos.clear()
            self.image_infos.clear()