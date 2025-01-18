import vulkan as vk
import logging
from .image_types import ImageBase, ImageCreateInfo, ImageType

logger = logging.getLogger(__name__)

class Texture2D(ImageBase):
    """2D texture image."""
    def __init__(self, device: vk.VkDevice, memory_manager: 'MemoryManager',
                 width: int, height: int, format: int, mip_levels: int = 1):
        create_info = ImageCreateInfo(
            width=width,
            height=height,
            format=format,
            usage=[vk.VK_IMAGE_USAGE_SAMPLED_BIT, vk.VK_IMAGE_USAGE_TRANSFER_DST_BIT],
            type=ImageType.TEXTURE_2D,
            mip_levels=mip_levels
        )
        super().__init__(device, memory_manager, create_info)
        self._create()

    def _create(self) -> None:
        """Create the 2D texture."""
        create_info = vk.VkImageCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
            imageType=vk.VK_IMAGE_TYPE_2D,
            format=self.create_info.format,
            extent=vk.VkExtent3D(
                width=self.create_info.width,
                height=self.create_info.height,
                depth=1
            ),
            mipLevels=self.create_info.mip_levels,
            arrayLayers=1,
            samples=vk.VK_SAMPLE_COUNT_1_BIT,
            tiling=vk.VK_IMAGE_TILING_OPTIMAL,
            usage=vk.VK_IMAGE_USAGE_SAMPLED_BIT | vk.VK_IMAGE_USAGE_TRANSFER_DST_BIT,
            sharingMode=vk.VK_SHARING_MODE_EXCLUSIVE
        )
        self.handle = vk.vkCreateImage(self.device, create_info, None)
        self._allocate_memory()
        self.create_view()

class CubemapTexture(ImageBase):
    """Cubemap texture image."""
    def __init__(self, device: vk.VkDevice, memory_manager: 'MemoryManager',
                 width: int, height: int, format: int, mip_levels: int = 1):
        create_info = ImageCreateInfo(
            width=width,
            height=height,
            format=format,
            usage=[vk.VK_IMAGE_USAGE_SAMPLED_BIT, vk.VK_IMAGE_USAGE_TRANSFER_DST_BIT],
            type=ImageType.TEXTURE_CUBE,
            mip_levels=mip_levels,
            array_layers=6
        )
        super().__init__(device, memory_manager, create_info)
        self._create()

    def _create(self) -> None:
        """Create the cubemap texture."""
        create_info = vk.VkImageCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
            imageType=vk.VK_IMAGE_TYPE_2D,
            format=self.create_info.format,
            extent=vk.VkExtent3D(
                width=self.create_info.width,
                height=self.create_info.height,
                depth=1
            ),
            mipLevels=self.create_info.mip_levels,
            arrayLayers=6,
            samples=vk.VK_SAMPLE_COUNT_1_BIT,
            tiling=vk.VK_IMAGE_TILING_OPTIMAL,
            usage=vk.VK_IMAGE_USAGE_SAMPLED_BIT | vk.VK_IMAGE_USAGE_TRANSFER_DST_BIT,
            sharingMode=vk.VK_SHARING_MODE_EXCLUSIVE,
            flags=vk.VK_IMAGE_CREATE_CUBE_COMPATIBLE_BIT
        )
        self.handle = vk.vkCreateImage(self.device, create_info, None)
        self._allocate_memory()
        self.create_view()

class RenderTarget(ImageBase):
    """Color render target image."""
    def __init__(self, device: vk.VkDevice, memory_manager: 'MemoryManager',
                 width: int, height: int, format: int, 
                 samples: int = vk.VK_SAMPLE_COUNT_1_BIT):
        create_info = ImageCreateInfo(
            width=width,
            height=height,
            format=format,
            usage=[vk.VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT, vk.VK_IMAGE_USAGE_SAMPLED_BIT],
            type=ImageType.RENDER_TARGET,
            samples=samples
        )
        super().__init__(device, memory_manager, create_info)
        self._create()

    def _create(self) -> None:
        """Create the render target."""
        create_info = vk.VkImageCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
            imageType=vk.VK_IMAGE_TYPE_2D,
            format=self.create_info.format,
            extent=vk.VkExtent3D(
                width=self.create_info.width,
                height=self.create_info.height,
                depth=1
            ),
            mipLevels=1,
            arrayLayers=1,
            samples=self.create_info.samples,
            tiling=vk.VK_IMAGE_TILING_OPTIMAL,
            usage=vk.VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | vk.VK_IMAGE_USAGE_SAMPLED_BIT,
            sharingMode=vk.VK_SHARING_MODE_EXCLUSIVE
        )
        self.handle = vk.vkCreateImage(self.device, create_info, None)
        self._allocate_memory()
        self.create_view()

class DepthStencilTarget(ImageBase):
    """Depth/stencil render target image."""
    def __init__(self, device: vk.VkDevice, memory_manager: 'MemoryManager',
                 width: int, height: int, 
                 format: int = vk.VK_FORMAT_D24_UNORM_S8_UINT):
        create_info = ImageCreateInfo(
            width=width,
            height=height,
            format=format,
            usage=[vk.VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT],
            type=ImageType.DEPTH_STENCIL
        )
        super().__init__(device, memory_manager, create_info)
        self._create()

    def _create(self) -> None:
        """Create the depth/stencil target."""
        create_info = vk.VkImageCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
            imageType=vk.VK_IMAGE_TYPE_2D,
            format=self.create_info.format,
            extent=vk.VkExtent3D(
                width=self.create_info.width,
                height=self.create_info.height,
                depth=1
            ),
            mipLevels=1,
            arrayLayers=1,
            samples=vk.VK_SAMPLE_COUNT_1_BIT,
            tiling=vk.VK_IMAGE_TILING_OPTIMAL,
            usage=vk.VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT,
            sharingMode=vk.VK_SHARING_MODE_EXCLUSIVE
        )
        self.handle = vk.vkCreateImage(self.device, create_info, None)
        self._allocate_memory()
        self.create_view()