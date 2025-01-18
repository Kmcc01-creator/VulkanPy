import vulkan as vk
from typing import Dict, Optional
from dataclasses import dataclass
from .render_target import RenderTarget, RenderTargetConfig

@dataclass
class ColorAttachmentConfig(RenderTargetConfig):
    """Configuration for color attachments."""
    def __init__(self, width: int, height: int, format: int = vk.VK_FORMAT_B8G8R8A8_UNORM,
                 sample_count: int = vk.VK_SAMPLE_COUNT_1_BIT):
        super().__init__(
            width=width,
            height=height,
            format=format,
            sample_count=sample_count,
            usage=vk.VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | vk.VK_IMAGE_USAGE_SAMPLED_BIT
        )

@dataclass
class DepthStencilAttachmentConfig(RenderTargetConfig):
    """Configuration for depth/stencil attachments."""
    def __init__(self, width: int, height: int, format: int = vk.VK_FORMAT_D24_UNORM_S8_UINT,
                 sample_count: int = vk.VK_SAMPLE_COUNT_1_BIT):
        super().__init__(
            width=width,
            height=height,
            format=format,
            sample_count=sample_count,
            usage=vk.VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT,
            clear_value=vk.VkClearValue(
                depthStencil=vk.VkClearDepthStencilValue(depth=1.0, stencil=0)
            )
        )

class RenderTargetFactory:
    """Factory for creating different types of render targets."""
    
    def __init__(self, device: vk.VkDevice, memory_allocator: 'MemoryAllocator'):
        self.device = device
        self.memory_allocator = memory_allocator
        self._cache: Dict[str, RenderTarget] = {}

    def create_color_attachment(self, width: int, height: int,
                              format: int = vk.VK_FORMAT_B8G8R8A8_UNORM,
                              sample_count: int = vk.VK_SAMPLE_COUNT_1_BIT,
                              cache_key: Optional[str] = None) -> RenderTarget:
        """Create a color attachment render target."""
        if cache_key and cache_key in self._cache:
            return self._cache[cache_key]

        config = ColorAttachmentConfig(width, height, format, sample_count)
        target = RenderTarget(self.device, self.memory_allocator, config)

        if cache_key:
            self._cache[cache_key] = target

        return target

    def create_depth_stencil_attachment(self, width: int, height: int,
                                      format: int = vk.VK_FORMAT_D24_UNORM_S8_UINT,
                                      sample_count: int = vk.VK_SAMPLE_COUNT_1_BIT,
                                      cache_key: Optional[str] = None) -> RenderTarget:
        """Create a depth/stencil attachment render target."""
        if cache_key and cache_key in self._cache:
            return self._cache[cache_key]

        config = DepthStencilAttachmentConfig(width, height, format, sample_count)
        target = RenderTarget(self.device, self.memory_allocator, config)

        if cache_key:
            self._cache[cache_key] = target

        return target

    def create_custom_target(self, config: RenderTargetConfig,
                           cache_key: Optional[str] = None) -> RenderTarget:
        """Create a render target with custom configuration."""
        if cache_key and cache_key in self._cache:
            return self._cache[cache_key]

        target = RenderTarget(self.device, self.memory_allocator, config)

        if cache_key:
            self._cache[cache_key] = target

        return target

    def get_cached_target(self, cache_key: str) -> Optional[RenderTarget]:
        """Get a cached render target by key."""
        return self._cache.get(cache_key)

    def cleanup(self) -> None:
        """Clean up all cached render targets."""
        for target in self._cache.values():
            target.cleanup()
        self._cache.clear()