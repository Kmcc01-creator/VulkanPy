import vulkan as vk
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass
from .vulkan_resources import VulkanResource, Image

logger = logging.getLogger(__name__)

@dataclass
class SwapChainSupportDetails:
    capabilities: vk.VkSurfaceCapabilitiesKHR
    formats: List[vk.VkSurfaceFormatKHR]
    present_modes: List[vk.VkPresentModeKHR]

class Swapchain(VulkanResource):
    def __init__(self, vulkan_engine):
        self.engine = vulkan_engine
        super().__init__(vulkan_engine.device.device)
        
        self.handle: Optional[vk.VkSwapchainKHR] = None
        self.images: List[vk.VkImage] = []
        self.image_views: List[vk.VkImageView] = []
        self.framebuffers: List[vk.VkFramebuffer] = []
        self.depth_image: Optional[Image] = None
        
        self.image_format: Optional[int] = None
        self.extent: Optional[vk.VkExtent2D] = None
        self.support_details: Optional[SwapChainSupportDetails] = None
        
        self.create()

    def create(self) -> None:
        """Create the swapchain and associated resources."""
        try:
            self.support_details = self._query_swapchain_support()
            surface_format = self._choose_surface_format()
            present_mode = self._choose_present_mode()
            self.extent = self._choose_extent()
            
            # Decide how many images in the swapchain
            image_count = self.support_details.capabilities.minImageCount + 1
            if (self.support_details.capabilities.maxImageCount > 0 and 
                image_count > self.support_details.capabilities.maxImageCount):
                image_count = self.support_details.capabilities.maxImageCount

            # Create swapchain
            create_info = vk.VkSwapchainCreateInfoKHR(
                sType=vk.VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR,
                surface=self.engine.surface,
                minImageCount=image_count,
                imageFormat=surface_format.format,
                imageColorSpace=surface_format.colorSpace,
                imageExtent=self.extent,
                imageArrayLayers=1,
                imageUsage=vk.VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT,
                preTransform=self.support_details.capabilities.currentTransform,
                compositeAlpha=vk.VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR,
                presentMode=present_mode,
                clipped=vk.VK_TRUE,
                oldSwapchain=self.handle
            )

            # Handle queue family sharing
            queue_families = [
                self.engine.device.queue_family_indices.graphics_family,
                self.engine.device.queue_family_indices.present_family
            ]
            
            if queue_families[0] != queue_families[1]:
                create_info.imageSharingMode = vk.VK_SHARING_MODE_CONCURRENT
                create_info.queueFamilyIndexCount = 2
                create_info.pQueueFamilyIndices = queue_families
            else:
                create_info.imageSharingMode = vk.VK_SHARING_MODE_EXCLUSIVE

            old_swapchain = self.handle
            self.handle = vk.vkCreateSwapchainKHR(self.device, create_info, None)
            
            if old_swapchain:
                vk.vkDestroySwapchainKHR(self.device, old_swapchain, None)

            # Get swapchain images and create image views
            self.images = vk.vkGetSwapchainImagesKHR(self.device, self.handle)
            self.image_format = surface_format.format
            self._create_image_views()
            self._create_depth_resources()
            self._create_framebuffers()
            
            logger.info(f"Created swapchain with {len(self.images)} images")
            
        except Exception as e:
            logger.error(f"Failed to create swapchain: {e}")
            self.cleanup()
            raise

    def _query_swapchain_support(self) -> SwapChainSupportDetails:
        """Query the device for swapchain support details."""
        support = SwapChainSupportDetails(
            capabilities=vk.vkGetPhysicalDeviceSurfaceCapabilitiesKHR(
                self.engine.device.physical_device,
                self.engine.surface
            ),
            formats=vk.vkGetPhysicalDeviceSurfaceFormatsKHR(
                self.engine.device.physical_device,
                self.engine.surface
            ),
            present_modes=vk.vkGetPhysicalDeviceSurfacePresentModesKHR(
                self.engine.device.physical_device,
                self.engine.surface
            )
        )
        return support

    def _choose_surface_format(self) -> vk.VkSurfaceFormatKHR:
        """Choose the best surface format."""
        for available_format in self.support_details.formats:
            if (available_format.format == vk.VK_FORMAT_B8G8R8A8_SRGB and
                available_format.colorSpace == vk.VK_COLOR_SPACE_SRGB_NONLINEAR_KHR):
                return available_format
        return self.support_details.formats[0]

    def _choose_present_mode(self) -> int:
        """Choose the best presentation mode."""
        preferred_modes = [
            vk.VK_PRESENT_MODE_MAILBOX_KHR,
            vk.VK_PRESENT_MODE_IMMEDIATE_KHR
        ]
        
        for mode in preferred_modes:
            if mode in self.support_details.present_modes:
                return mode
                
        return vk.VK_PRESENT_MODE_FIFO_KHR

    def _choose_extent(self) -> vk.VkExtent2D:
        """Choose the swapchain extent."""
        if self.support_details.capabilities.currentExtent.width != 0xFFFFFFFF:
            return self.support_details.capabilities.currentExtent
        else:
            width, height = self.engine.window.get_framebuffer_size()
            
            extent = vk.VkExtent2D(
                width=max(
                    self.support_details.capabilities.minImageExtent.width,
                    min(self.support_details.capabilities.maxImageExtent.width, width)
                ),
                height=max(
                    self.support_details.capabilities.minImageExtent.height,
                    min(self.support_details.capabilities.maxImageExtent.height, height)
                )
            )
            return extent

    def _create_image_views(self) -> None:
        """Create image views for swapchain images."""
        self.image_views = []
        
        for image in self.images:
            view_info = vk.VkImageViewCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
                image=image,
                viewType=vk.VK_IMAGE_VIEW_TYPE_2D,
                format=self.image_format,
                components=vk.VkComponentMapping(
                    r=vk.VK_COMPONENT_SWIZZLE_IDENTITY,
                    g=vk.VK_COMPONENT_SWIZZLE_IDENTITY,
                    b=vk.VK_COMPONENT_SWIZZLE_IDENTITY,
                    a=vk.VK_COMPONENT_SWIZZLE_IDENTITY
                ),
                subresourceRange=vk.VkImageSubresourceRange(
                    aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT,
                    baseMipLevel=0,
                    levelCount=1,
                    baseArrayLayer=0,
                    layerCount=1
                )
            )
            
            self.image_views.append(vk.vkCreateImageView(self.device, view_info, None))

    def _create_depth_resources(self) -> None:
        """Create depth buffer resources."""
        depth_format = self._find_depth_format()
        
        self.depth_image = Image(
            self.device,
            self.extent.width,
            self.extent.height,
            depth_format,
            vk.VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT,
            vk.VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,
            self.engine.resource_manager.memory_allocator
        )
        self.depth_image.create_view(vk.VK_IMAGE_ASPECT_DEPTH_BIT)

    def _find_depth_format(self) -> int:
        """Find a supported depth format."""
        candidates = [
            vk.VK_FORMAT_D32_SFLOAT,
            vk.VK_FORMAT_D32_SFLOAT_S8_UINT,
            vk.VK_FORMAT_D24_UNORM_S8_UINT
        ]
        
        for format in candidates:
            props = vk.vkGetPhysicalDeviceFormatProperties(
                self.engine.device.physical_device,
                format
            )
            
            if (props.optimalTilingFeatures &
                vk.VK_FORMAT_FEATURE_DEPTH_STENCIL_ATTACHMENT_BIT):
                return format
                
        raise RuntimeError("Failed to find supported depth format")

    def _create_framebuffers(self) -> None:
        """Create framebuffers for the swapchain images."""
        self.framebuffers = []
        
        for image_view in self.image_views:
            attachments = [image_view, self.depth_image.view]
            
            create_info = vk.VkFramebufferCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO,
                renderPass=self.engine.render_pass.handle,
                attachmentCount=len(attachments),
                pAttachments=attachments,
                width=self.extent.width,
                height=self.extent.height,
                layers=1
            )
            
            self.framebuffers.append(
                vk.vkCreateFramebuffer(self.device, create_info, None)
            )

    def cleanup(self) -> None:
        """Clean up swapchain resources."""
        for framebuffer in self.framebuffers:
            vk.vkDestroyFramebuffer(self.device, framebuffer, None)
        self.framebuffers.clear()
        
        if self.depth_image:
            self.depth_image.cleanup()
            self.depth_image = None
        
        for image_view in self.image_views:
            vk.vkDestroyImageView(self.device, image_view, None)
        self.image_views.clear()
        
        if self.handle:
            vk.vkDestroySwapchainKHR(self.device, self.handle, None)
            self.handle = None
            
        logger.info("Cleaned up swapchain resources")

    def recreate(self) -> None:
        """Recreate the swapchain and associated resources."""
        logger.info("Recreating swapchain")
        
        vk.vkDeviceWaitIdle(self.device)
        self.cleanup()
        self.create()

    @property
    def image_count(self) -> int:
        """Get the number of images in the swapchain."""
        return len(self.images)