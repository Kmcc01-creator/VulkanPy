import vulkan as vk
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RenderTargetConfig:
    width: int
    height: int
    format: int
    sample_count: int = vk.VK_SAMPLE_COUNT_1_BIT
    usage: int = vk.VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT
    clear_value: Optional[vk.VkClearValue] = None
    
    def __post_init__(self):
        if self.clear_value is None:
            self.clear_value = vk.VkClearValue(
                color=vk.VkClearColorValue(float32=[0.0, 0.0, 0.0, 1.0])
            )

class RenderTarget:
    """
    Manages render target images and attachments.
    """
    def __init__(self, device: vk.VkDevice, memory_allocator: 'MemoryAllocator',
                 config: RenderTargetConfig):
        self.device = device
        self.memory_allocator = memory_allocator
        self.config = config
        
        self.image: Optional[vk.VkImage] = None
        self.image_memory: Optional[vk.VkDeviceMemory] = None
        self.view: Optional[vk.VkImageView] = None
        self.current_layout: int = vk.VK_IMAGE_LAYOUT_UNDEFINED
        
        self.create()

    def create(self) -> None:
        """Create render target resources."""
        try:
            self._create_image()
            self._allocate_memory()
            self._create_image_view()
            logger.info(f"Created render target {self.config.width}x{self.config.height}")
        except Exception as e:
            logger.error(f"Failed to create render target: {e}")
            self.cleanup()
            raise

    def _create_image(self) -> None:
        """Create the render target image."""
        image_info = vk.VkImageCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
            imageType=vk.VK_IMAGE_TYPE_2D,
            format=self.config.format,
            extent=vk.VkExtent3D(
                width=self.config.width,
                height=self.config.height,
                depth=1
            ),
            mipLevels=1,
            arrayLayers=1,
            samples=self.config.sample_count,
            tiling=vk.VK_IMAGE_TILING_OPTIMAL,
            usage=self.config.usage,
            sharingMode=vk.VK_SHARING_MODE_EXCLUSIVE,
            initialLayout=vk.VK_IMAGE_LAYOUT_UNDEFINED
        )
        
        self.image = vk.vkCreateImage(self.device, image_info, None)

    def _allocate_memory(self) -> None:
        """Allocate memory for the render target image."""
        memory_requirements = vk.vkGetImageMemoryRequirements(self.device, self.image)
        
        # Use device local memory for render targets
        self.image_memory = self.memory_allocator.allocate_memory(
            memory_requirements,
            vk.VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT
        )
        
        vk.vkBindImageMemory(self.device, self.image, self.image_memory, 0)

    def _create_image_view(self) -> None:
        """Create image view for the render target."""
        aspect_flags = vk.VK_IMAGE_ASPECT_COLOR_BIT
        if self._is_depth_format(self.config.format):
            aspect_flags = vk.VK_IMAGE_ASPECT_DEPTH_BIT
            if self._has_stencil_component(self.config.format):
                aspect_flags |= vk.VK_IMAGE_ASPECT_STENCIL_BIT

        view_info = vk.VkImageViewCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
            image=self.image,
            viewType=vk.VK_IMAGE_VIEW_TYPE_2D,
            format=self.config.format,
            subresourceRange=vk.VkImageSubresourceRange(
                aspectMask=aspect_flags,
                baseMipLevel=0,
                levelCount=1,
                baseArrayLayer=0,
                layerCount=1
            )
        )
        
        self.view = vk.vkCreateImageView(self.device, view_info, None)

    def transition_layout(self, command_buffer: vk.VkCommandBuffer,
                        new_layout: int,
                        src_stage: int = None,
                        dst_stage: int = None,
                        src_access: int = None,
                        dst_access: int = None) -> None:
        """Transition the image layout."""
        if not src_stage:
            src_stage, dst_stage, src_access, dst_access = \
                self._get_layout_transition_masks(self.current_layout, new_layout)

        barrier = vk.VkImageMemoryBarrier(
            sType=vk.VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER,
            oldLayout=self.current_layout,
            newLayout=new_layout,
            srcQueueFamilyIndex=vk.VK_QUEUE_FAMILY_IGNORED,
            dstQueueFamilyIndex=vk.VK_QUEUE_FAMILY_IGNORED,
            image=self.image,
            subresourceRange=vk.VkImageSubresourceRange(
                aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT,
                baseMipLevel=0,
                levelCount=1,
                baseArrayLayer=0,
                layerCount=1
            ),
            srcAccessMask=src_access,
            dstAccessMask=dst_access
        )

        vk.vkCmdPipelineBarrier(
            command_buffer,
            src_stage,
            dst_stage,
            0,
            0, None,
            0, None,
            1, [barrier]
        )

        self.current_layout = new_layout

    def _get_layout_transition_masks(self, old_layout: int, new_layout: int) -> Tuple[int, int, int, int]:
        """Get pipeline stages and access masks for layout transition."""
        src_stage = vk.VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT
        dst_stage = vk.VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT
        src_access = 0
        dst_access = 0

        if old_layout == vk.VK_IMAGE_LAYOUT_UNDEFINED and \
           new_layout == vk.VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL:
            dst_stage = vk.VK_PIPELINE_STAGE_TRANSFER_BIT
            dst_access = vk.VK_ACCESS_TRANSFER_WRITE_BIT

        elif old_layout == vk.VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL and \
             new_layout == vk.VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL:
            src_stage = vk.VK_PIPELINE_STAGE_TRANSFER_BIT
            dst_stage = vk.VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT
            src_access = vk.VK_ACCESS_TRANSFER_WRITE_BIT
            dst_access = vk.VK_ACCESS_SHADER_READ_BIT

        elif old_layout == vk.VK_IMAGE_LAYOUT_UNDEFINED and \
             new_layout == vk.VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL:
            dst_stage = vk.VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT
            dst_access = vk.VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT

        else:
            raise ValueError(f"Unsupported layout transition: {old_layout} -> {new_layout}")

        return src_stage, dst_stage, src_access, dst_access

    @staticmethod
    def _is_depth_format(format: int) -> bool:
        """Check if the format is a depth format."""
        depth_formats = [
            vk.VK_FORMAT_D16_UNORM,
            vk.VK_FORMAT_D16_UNORM_S8_UINT,
            vk.VK_FORMAT_D24_UNORM_S8_UINT,
            vk.VK_FORMAT_D32_SFLOAT,
            vk.VK_FORMAT_D32_SFLOAT_S8_UINT
        ]
        return format in depth_formats

    @staticmethod
    def _has_stencil_component(format: int) -> bool:
        """Check if the format has a stencil component."""
        stencil_formats = [
            vk.VK_FORMAT_D16_UNORM_S8_UINT,
            vk.VK_FORMAT_D24_UNORM_S8_UINT,
            vk.VK_FORMAT_D32_SFLOAT_S8_UINT
        ]
        return format in stencil_formats

    def cleanup(self) -> None:
        """Clean up render target resources."""
        if self.view:
            vk.vkDestroyImageView(self.device, self.view, None)
            self.view = None

        if self.image:
            vk.vkDestroyImage(self.device, self.image, None)
            self.image = None

        if self.image_memory:
            self.memory_allocator.free_memory(self.image_memory)
            self.image_memory = None

        logger.info("Cleaned up render target resources")

    def get_clear_value(self) -> vk.VkClearValue:
        """Get the clear value for this render target."""
        return self.config.clear_value