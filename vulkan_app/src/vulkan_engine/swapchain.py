import vulkan as vk
import logging
from vulkan_engine.pipeline import create_pipeline
from vulkan_engine.descriptors import create_uniform_buffers, create_descriptor_pool, create_descriptor_sets

logger = logging.getLogger(__name__)



import vulkan as vk
import logging

logger = logging.getLogger(__name__)

class Swapchain:
    def __init__(self, vulkan_engine):
        self.vulkan_engine = vulkan_engine
        self.device = vulkan_engine.device
        self.physical_device = vulkan_engine.physical_device
        self.surface = vulkan_engine.surface
        self.swapchain = None
        self.swapchain_images = []
        self.swapchain_image_views = []
        self.swapchain_image_format = None
        self.swapchain_extent = None
        self.create_swapchain()

    def create_swapchain(self):
        swap_chain_support = self.query_swap_chain_support(self.physical_device)
        surface_format = self.choose_swap_surface_format(swap_chain_support.formats)
        present_mode = self.choose_swap_present_mode(swap_chain_support.present_modes)
        extent = self.choose_swap_extent(swap_chain_support.capabilities)

        image_count = swap_chain_support.capabilities.minImageCount + 1
        if swap_chain_support.capabilities.maxImageCount > 0 and image_count > swap_chain_support.capabilities.maxImageCount:
            image_count = swap_chain_support.capabilities.maxImageCount

        create_info = vk.VkSwapchainCreateInfoKHR(
            sType=vk.VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR,
            surface=self.surface,
            minImageCount=image_count,
            imageFormat=surface_format.format,
            imageColorSpace=surface_format.colorSpace,
            imageExtent=extent,
            imageArrayLayers=1,
            imageUsage=vk.VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT,
            preTransform=swap_chain_support.capabilities.currentTransform,
            compositeAlpha=vk.VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR,
            presentMode=present_mode,
            clipped=vk.VK_TRUE,
            oldSwapchain=None
        )

        indices = self.vulkan_engine.find_queue_families(self.physical_device)
        queue_family_indices = [indices.graphics_family, indices.present_family]

        if indices.graphics_family != indices.present_family:
            create_info.imageSharingMode = vk.VK_SHARING_MODE_CONCURRENT
            create_info.queueFamilyIndexCount = 2
            create_info.pQueueFamilyIndices = queue_family_indices
        else:
            create_info.imageSharingMode = vk.VK_SHARING_MODE_EXCLUSIVE

        try:
            self.swapchain = vk.vkCreateSwapchainKHR(self.device, create_info, None)
            self.swapchain_images = vk.vkGetSwapchainImagesKHR(self.device, self.swapchain)
            self.swapchain_image_format = surface_format.format
            self.swapchain_extent = extent
            self.create_image_views()
            logger.info("Swapchain created successfully")
        except vk.VkError as e:
            logger.error(f"Failed to create swap chain: {str(e)}")
            raise

    def create_image_views(self):
        self.swapchain_image_views = []
        for image in self.swapchain_images:
            create_info = vk.VkImageViewCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
                image=image,
                viewType=vk.VK_IMAGE_VIEW_TYPE_2D,
                format=self.swapchain_image_format,
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
            try:
                self.swapchain_image_views.append(vk.vkCreateImageView(self.device, create_info, None))
            except vk.VkError as e:
                logger.error(f"Failed to create image views: {str(e)}")
                raise

    def recreate(self):
        vk.vkDeviceWaitIdle(self.device)

        self.cleanup_swapchain()

        self.create_swapchain()
        self.vulkan_engine.create_render_pass()
        self.vulkan_engine.create_graphics_pipeline()
        self.vulkan_engine.create_framebuffers()
        self.vulkan_engine.create_uniform_buffers()
        self.vulkan_engine.create_descriptor_pool()
        self.vulkan_engine.create_descriptor_sets()
        self.vulkan_engine.create_command_buffers()

        logger.info("Swapchain recreated successfully")

    def cleanup_swapchain(self):
        for image_view in self.swapchain_image_views:
            vk.vkDestroyImageView(self.device, image_view, None)
        vk.vkDestroySwapchainKHR(self.device, self.swapchain, None)

    def cleanup(self):
        self.cleanup_swapchain()

    def query_swap_chain_support(self, device):
        support_details = SwapChainSupportDetails()
        support_details.capabilities = vk.vkGetPhysicalDeviceSurfaceCapabilitiesKHR(device, self.surface)
        support_details.formats = vk.vkGetPhysicalDeviceSurfaceFormatsKHR(device, self.surface)
        support_details.present_modes = vk.vkGetPhysicalDeviceSurfacePresentModesKHR(device, self.surface)
        return support_details

    def choose_swap_surface_format(self, available_formats):
        for available_format in available_formats:
            if available_format.format == vk.VK_FORMAT_B8G8R8A8_SRGB and available_format.colorSpace == vk.VK_COLOR_SPACE_SRGB_NONLINEAR_KHR:
                return available_format
        return available_formats[0]

    def choose_swap_present_mode(self, available_present_modes):
        for available_present_mode in available_present_modes:
            if available_present_mode == vk.VK_PRESENT_MODE_MAILBOX_KHR:
                return available_present_mode
        return vk.VK_PRESENT_MODE_FIFO_KHR

    def choose_swap_extent(self, capabilities):
        if capabilities.currentExtent.width != 0xFFFFFFFF:
            return capabilities.currentExtent
        else:
            width, height = self.vulkan_engine.window.get_framebuffer_size()
            extent = vk.VkExtent2D(width, height)
            extent.width = max(capabilities.minImageExtent.width, min(capabilities.maxImageExtent.width, extent.width))
            extent.height = max(capabilities.minImageExtent.height, min(capabilities.maxImageExtent.height, extent.height))
            return extent

class SwapChainSupportDetails:
    def __init__(self):
        self.capabilities = None
        self.formats = None
        self.present_modes = None

def create_swapchain(vulkan_engine): # New function to create swapchain
    try:
        surface_capabilities = vk.vkGetPhysicalDeviceSurfaceCapabilitiesKHR(vulkan_engine.physical_device, vulkan_engine.surface)
        surface_format = choose_surface_format(vulkan_engine.physical_device, vulkan_engine.surface)
        present_mode = choose_present_mode(vulkan_engine.physical_device, vulkan_engine.surface)
        image_count = choose_image_count(surface_capabilities)
        swapchain_extent = choose_swapchain_extent(surface_capabilities, vulkan_engine.window.width, vulkan_engine.window.height) # Access window dimensions through vulkan_engine.window

        swapchain_create_info = vk.VkSwapchainCreateInfoKHR(
            sType=vk.VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR,
            surface=vulkan_engine.surface,
            minImageCount=image_count,
            imageFormat=surface_format.format,
            imageColorSpace=surface_format.colorSpace,
            imageExtent=swapchain_extent,
            imageArrayLayers=1,
            imageUsage=vk.VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT,
            imageSharingMode=vk.VK_SHARING_MODE_EXCLUSIVE,
            queueFamilyIndexCount=0,
            pQueueFamilyIndices=None,
            preTransform=surface_capabilities.currentTransform,
            compositeAlpha=vk.VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR,
            presentMode=present_mode,
            clipped=vk.VK_TRUE,
            oldSwapchain=None,
        )

        if vulkan_engine.graphics_queue_family_index != vulkan_engine.present_queue_family_index:
            swapchain_create_info.imageSharingMode = vk.VK_SHARING_MODE_CONCURRENT
            swapchain_create_info.queueFamilyIndexCount = 2
            swapchain_create_info.pQueueFamilyIndices = [vulkan_engine.graphics_queue_family_index, vulkan_engine.present_queue_family_index]

        swapchain = vk.vkCreateSwapchainKHR(vulkan_engine.device, swapchain_create_info, None)
        swapchain_images = vk.vkGetSwapchainImagesKHR(vulkan_engine.device, swapchain)
        return swapchain, swapchain_extent, swapchain_images
    except vk.VkError as e:
        raise Exception(f"Failed to create swapchain: {e}")

def choose_present_mode(physical_device, surface):
    present_modes = vk.vkGetPhysicalDeviceSurfacePresentModesKHR(physical_device, surface)
    
    preferred_modes = [vk.VK_PRESENT_MODE_MAILBOX_KHR, vk.VK_PRESENT_MODE_IMMEDIATE_KHR]
    for mode in preferred_modes:
        if mode in present_modes:
            return mode

    return vk.VK_PRESENT_MODE_FIFO_KHR

def choose_image_count(surface_capabilities):
    desired_count = surface_capabilities.minImageCount + 1
    if surface_capabilities.maxImageCount > 0:
        return min(desired_count, surface_capabilities.maxImageCount)
    return desired_count

def choose_swapchain_extent(surface_capabilities, window_width, window_height):
    if surface_capabilities.currentExtent.width != 0xFFFFFFFF:
        return surface_capabilities.currentExtent
    else:
        width = max(surface_capabilities.minImageExtent.width,
                    min(surface_capabilities.maxImageExtent.width, window_width))
        height = max(surface_capabilities.minImageExtent.height,
                        min(surface_capabilities.maxImageExtent.height, window_height))
        return vk.VkExtent2D(width=width, height=height)

def choose_surface_format(physical_device, surface):
    formats = vk.vkGetPhysicalDeviceSurfaceFormatsKHR(physical_device, surface)
    if not formats:
        raise Exception("No surface formats available.")

    # For simplicity, select the first available format.
    # In a real application, you might want to add format selection logic here.
    return formats[0]


def choose_image_count(surface_capabilities):
    desired_count = surface_capabilities.minImageCount + 1
    if surface_capabilities.maxImageCount > 0:
        return min(desired_count, surface_capabilities.maxImageCount)
    return desired_count


def choose_swapchain_extent(surface_capabilities, window_width, window_height): # Modified function signature
    if surface_capabilities.currentExtent.width != 0xFFFFFFFF:
        return surface_capabilities.currentExtent
    else:
        width = max(surface_capabilities.minImageExtent.width,
                    min(surface_capabilities.maxImageExtent.width, window_width))
        height = max(surface_capabilities.minImageExtent.height,
                        min(surface_capabilities.maxImageExtent.height, window_height))
        return vk.VkExtent2D(width=width, height=height)

    def choose_swapchain_extent(self, surface_capabilities): # No changes here
        if surface_capabilities.currentExtent.width != 0xFFFFFFFF:
            return surface_capabilities.currentExtent
        else:
            width = max(surface_capabilities.minImageExtent.width,
                        min(surface_capabilities.maxImageExtent.width, self.window_width))
            height = max(surface_capabilities.minImageExtent.height,
                         min(surface_capabilities.maxImageExtent.height, self.window_height))
            return vk.VkExtent2D(width=width, height=height)


    def recreate_swapchain(self):
        vk.vkDeviceWaitIdle(self.device)

        # Destroy old swapchain and related resources
        for framebuffer in self.framebuffers:
            self.resource_manager.destroy_framebuffer(self.device, framebuffer, None) # Use resource manager to destroy framebuffer
        self.resource_manager.destroy_swapchain(self.swapchain) # Use resource manager to destroy swapchain

        # Recreate swapchain and related resources
        self.create_swapchain()
        self.create_image_views() # Recreate image views
        self.create_render_pass()
        self.create_pipeline()
        self.create_framebuffers()
        self.create_uniform_buffers()
        self.create_descriptor_pool()
        self.create_descriptor_sets()

        self.renderer.create_command_buffers() # Recreate command buffers

    def choose_surface_format(self):
        formats = vk.vkGetPhysicalDeviceSurfaceFormatsKHR(self.physical_device, self.surface)
        if not formats:
            raise Exception("No surface formats available.")

        for fmt in formats:
            if fmt.format == vk.VK_FORMAT_B8G8R8A8_SRGB and fmt.colorSpace == vk.VK_COLOR_SPACE_SRGB_NONLINEAR_KHR:
                return fmt

        return formats[0]

    def choose_present_mode(self):
        present_modes = vk.vkGetPhysicalDeviceSurfacePresentModesKHR(self.physical_device, self.surface)
        
        preferred_modes = [vk.VK_PRESENT_MODE_MAILBOX_KHR, vk.VK_PRESENT_MODE_IMMEDIATE_KHR]
        for mode in preferred_modes:
            if mode in present_modes:
                return mode

        return vk.VK_PRESENT_MODE_FIFO_KHR

    def create_image_views(self):
        for image in self.swapchain_images:
            image_view_create_info = vk.VkImageViewCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
                image=image,
                viewType=vk.VK_IMAGE_VIEW_TYPE_2D,
                format=self.choose_surface_format().format,
                components=vk.VkComponentMapping(),  # Default component mapping
                subresourceRange=vk.VkImageSubresourceRange(
                    aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT,
                    baseMipLevel=0,
                    levelCount=1,
                    baseArrayLayer=0,
                    layerCount=1,
                )
            )
            image_view = vk.vkCreateImageView(self.device, image_view_create_info, None)
            self.resource_manager.add_resource(image_view, "image_view", self.resource_manager.destroy_image_view)
            self.image_views.append(image_view)

    def create_render_pass(self):
        format = self.choose_surface_format().format
        color_attachment = vk.VkAttachmentDescription(
            format=format,  # Use chosen surface format
            samples=vk.VK_SAMPLE_COUNT_1_BIT,
            loadOp=vk.VK_ATTACHMENT_LOAD_OP_CLEAR,
            storeOp=vk.VK_ATTACHMENT_STORE_OP_STORE,
            stencilLoadOp=vk.VK_ATTACHMENT_LOAD_OP_DONT_CARE,
            stencilStoreOp=vk.VK_ATTACHMENT_STORE_OP_DONT_CARE,
            initialLayout=vk.VK_IMAGE_LAYOUT_UNDEFINED,
            finalLayout=vk.VK_IMAGE_LAYOUT_PRESENT_SRC_KHR,
        )

        color_attachment_ref = vk.VkAttachmentReference(
            attachment=0,
            layout=vk.VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
        )

        subpass = vk.VkSubpassDescription(
            pipelineBindPoint=vk.VK_PIPELINE_BIND_POINT_GRAPHICS,
            colorAttachmentCount=1,
            pColorAttachments=[color_attachment_ref],
        )

        render_pass_create_info = vk.VkRenderPassCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO,
            attachmentCount=1,
            pAttachments=[color_attachment],
            subpassCount=1,
            pSubpasses=[subpass],
        )

        try:
            self.render_pass = vk.vkCreateRenderPass(self.device, render_pass_create_info, None)
            self.resource_manager.add_resource(self.render_pass, "render_pass", self.resource_manager.destroy_render_pass)
        except vk.VkError as e:
            raise Exception(f"Failed to create render pass: {e}")

    def create_pipeline(self):
        self.pipeline, self.pipeline_layout, self.descriptor_set_layout = create_pipeline(  # noqa: E501
            self.device, self.extent, self.render_pass, self.resource_manager
        )
        self.resource_manager.add_resource(self.pipeline, "pipeline", self.resource_manager.destroy_pipeline)  # noqa: E501
        self.resource_manager.add_resource(self.pipeline_layout, "pipeline_layout", self.resource_manager.destroy_pipeline_layout)  # noqa: E501
        self.resource_manager.add_resource(self.descriptor_set_layout.layout, "descriptor_set_layout", self.resource_manager.destroy_descriptor_set_layout)  # noqa: E501

    def create_framebuffers(self):
        format = vk.vkGetSwapchainImagesKHR(self.device, self.swapchain)[0].format  # noqa: E501
        for image in self.swapchain_images:
            image_view_create_info = vk.VkImageViewCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
                image=image,
                viewType=vk.VK_IMAGE_VIEW_TYPE_2D,
                format=format,  # Getting format from first image
                components=vk.VkComponentMapping(),
                subresourceRange=vk.VkImageSubresourceRange(
                    aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT,
                    baseMipLevel=0,
                    levelCount=1,
                    baseArrayLayer=0,
                    layerCount=1,
                )
            )
            image_view = vk.vkCreateImageView(self.device, image_view_create_info, None)  # noqa: E501
            framebuffer_create_info = vk.VkFramebufferCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO,
                renderPass=self.render_pass,
                attachmentCount=1,
                pAttachments=[image_view],
                width=self.extent.width,
                height=self.extent.height,
                layers=1,
            )

            framebuffer = vk.vkCreateFramebuffer(self.device, framebuffer_create_info, None)  # noqa: E501
            self.resource_manager.add_resource(framebuffer, "framebuffer", self.resource_manager.destroy_framebuffer)  # noqa: E501
            self.framebuffers.append(framebuffer)

    def create_uniform_buffers(self):
        self.uniform_buffers = create_uniform_buffers(self.resource_manager, len(self.swapchain_images))

    def create_descriptor_pool(self):
        self.descriptor_pool = create_descriptor_pool(self.device, self.descriptor_set_layout, self.resource_manager)
        self.resource_manager.add_resource(self.descriptor_pool, "descriptor_pool", self.resource_manager.destroy_descriptor_pool)

    def create_descriptor_sets(self):
        self.descriptor_sets = create_descriptor_sets(self.device, self.descriptor_pool, self.descriptor_set_layout, self.uniform_buffers)

    def recreate_swapchain(self):
        vk.vkDeviceWaitIdle(self.device)

        # Destroy old swapchain and related resources
        for framebuffer in self.framebuffers:
            self.resource_manager.destroy_framebuffer(framebuffer)
        self.resource_manager.destroy_swapchain(self.swapchain)

        # Recreate swapchain and related resources
        self.create_swapchain()
        self.create_image_views()
        self.create_render_pass()
        self.create_pipeline()
        self.create_framebuffers()
        self.create_uniform_buffers()
        self.create_descriptor_pool()
        self.create_descriptor_sets()

        self.renderer.create_command_buffers()

