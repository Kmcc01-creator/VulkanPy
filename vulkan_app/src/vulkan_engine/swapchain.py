import vulkan as vk
from vulkan_engine.pipeline import create_pipeline
from vulkan_engine.descriptors import create_uniform_buffers, create_descriptor_pool, create_descriptor_sets

def create_render_pass(device, swapchain_image_format):
    color_attachment = vk.VkAttachmentDescription(
        format=swapchain_image_format,
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
        return vk.vkCreateRenderPass(device, render_pass_create_info, None)
    except vk.VkError as e:
        raise Exception(f"Failed to create render pass: {e}")

def choose_surface_format(physical_device, surface):
    formats = vk.vkGetPhysicalDeviceSurfaceFormatsKHR(physical_device, surface)
    if not formats:
        raise Exception("No surface formats available.")

    # For simplicity, select the first available format.
    # In a real application, you might want to add format selection logic here.
    return formats[0]


def create_swapchain(instance, device, physical_device, surface, graphics_queue_family_index, present_queue_family_index):
    surface_capabilities = vk.vkGetPhysicalDeviceSurfaceCapabilitiesKHR(physical_device, surface)
    surface_format = choose_surface_format(physical_device, surface)

    # For simplicity, use FIFO present mode and mailbox image count.
    # In a real application, you might want to add more sophisticated logic here.
    present_mode = vk.VK_PRESENT_MODE_FIFO_KHR
    image_count = surface_capabilities.minImageCount + 1

    swapchain_create_info = vk.VkSwapchainCreateInfoKHR(
        sType=vk.VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR,
        surface=surface,
        minImageCount=image_count,
        imageFormat=surface_format.format,
        imageColorSpace=surface_format.colorSpace,
        imageExtent=vk.VkExtent2D(width=max(surface_capabilities.minImageExtent.width, min(surface_capabilities.maxImageExtent.width, surface_capabilities.currentExtent.width)), height=max(surface_capabilities.minImageExtent.height, min(surface_capabilities.maxImageExtent.height, surface_capabilities.currentExtent.height))),
        imageArrayLayers=1,
        imageUsage=vk.VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT,
        imageSharingMode=vk.VK_SHARING_MODE_EXCLUSIVE,  # For single queue family
        queueFamilyIndexCount=0,
        pQueueFamilyIndices=None,
        preTransform=surface_capabilities.currentTransform,
        compositeAlpha=vk.VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR,
        presentMode=present_mode,
        clipped=vk.VK_TRUE,
        oldSwapchain=None,  # No existing swapchain to replace
    )

    if graphics_queue_family_index != present_queue_family_index:
        swapchain_create_info.imageSharingMode = vk.VK_SHARING_MODE_CONCURRENT
        swapchain_create_info.queueFamilyIndexCount = 2
        swapchain_create_info.pQueueFamilyIndices = [graphics_queue_family_index, present_queue_family_index]

    try:
        swapchain = vk.vkCreateSwapchainKHR(device, swapchain_create_info, None)
        extent = surface_capabilities.currentExtent
        return swapchain, extent # Returning extent as well
    except vk.VkError as e:
        raise Exception(f"Failed to create swapchain: {e}")


class Swapchain:
    def __init__(self, renderer):
        self.renderer = renderer
        self.instance = renderer.instance
        self.device = renderer.device
        self.physical_device = renderer.physical_device
        self.surface = renderer.surface
        self.graphics_queue_family_index = renderer.graphics_queue_family_index
        self.present_queue_family_index = renderer.graphics_queue_family_index # Using graphics queue for present for now

        self.create_swapchain()
        self.create_render_pass()
        self.create_pipeline()
        self.create_framebuffers()
        self.create_uniform_buffers()
        self.create_descriptor_pool()
        self.create_descriptor_sets()


    def create_swapchain(self):
        surface_capabilities = vk.vkGetPhysicalDeviceSurfaceCapabilitiesKHR(self.physical_device, self.surface)
        surface_format = self.choose_surface_format()

        # For simplicity, use FIFO present mode and mailbox image count.
        # In a real application, you might want to add more sophisticated logic here.
        present_mode = vk.VK_PRESENT_MODE_FIFO_KHR
        image_count = surface_capabilities.minImageCount + 1

        swapchain_create_info = vk.VkSwapchainCreateInfoKHR(
            sType=vk.VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR,
            surface=self.surface,
            minImageCount=image_count,
            imageFormat=surface_format.format,
            imageColorSpace=surface_format.colorSpace,
            imageExtent=vk.VkExtent2D(width=max(surface_capabilities.minImageExtent.width, min(surface_capabilities.maxImageExtent.width, surface_capabilities.currentExtent.width)), height=max(surface_capabilities.minImageExtent.height, min(surface_capabilities.maxImageExtent.height, surface_capabilities.currentExtent.height))),
            imageArrayLayers=1,
            imageUsage=vk.VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT,
            imageSharingMode=vk.VK_SHARING_MODE_EXCLUSIVE,  # For single queue family
            queueFamilyIndexCount=0,
            pQueueFamilyIndices=None,
            preTransform=surface_capabilities.currentTransform,
            compositeAlpha=vk.VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR,
            presentMode=present_mode,
            clipped=vk.VK_TRUE,
            oldSwapchain=None,  # No existing swapchain to replace
        )

        if self.graphics_queue_family_index != self.present_queue_family_index:
            swapchain_create_info.imageSharingMode = vk.VK_SHARING_MODE_CONCURRENT
            swapchain_create_info.queueFamilyIndexCount = 2
            swapchain_create_info.pQueueFamilyIndices = [self.graphics_queue_family_index, self.present_queue_family_index]

        try:
            self.swapchain = vk.vkCreateSwapchainKHR(self.device, swapchain_create_info, None)
            self.extent = surface_capabilities.currentExtent
        except vk.VkError as e:
            raise Exception(f"Failed to create swapchain: {e}")

    def choose_surface_format(self):
        formats = vk.vkGetPhysicalDeviceSurfaceFormatsKHR(self.physical_device, self.surface)
        if not formats:
            raise Exception("No surface formats available.")

        # For simplicity, select the first available format.
        # In a real application, you might want to add format selection logic here.
        return formats[0]

    def create_render_pass(self):
        color_attachment = vk.VkAttachmentDescription(
            format=self.choose_surface_format().format, # Use chosen surface format
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
        except vk.VkError as e:
            raise Exception(f"Failed to create render pass: {e}")

    def create_pipeline(self):
        self.pipeline, self.pipeline_layout, self.descriptor_set_layout = create_pipeline(self.device, self.extent, self.render_pass) # Store descriptor_set_layout

    def create_framebuffers(self):
        swapchain_images = vk.vkGetSwapchainImagesKHR(self.device, self.swapchain)
        self.framebuffers = [] # Initialize self.framebuffers

        for image in swapchain_images:
            image_view_create_info = vk.VkImageViewCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
                image=image,
                viewType=vk.VK_IMAGE_VIEW_TYPE_2D,
                format=vk.vkGetSwapchainImagesKHR(self.device, self.swapchain)[0].format, # Getting format from first image, assuming all are same.
                components=vk.VkComponentMapping(), # Default component mapping
                subresourceRange=vk.VkImageSubresourceRange(
                    aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT,
                    baseMipLevel=0,
                    levelCount=1,
                    baseArrayLayer=0,
                    layerCount=1,
                )
            )
            image_view = vk.vkCreateImageView(self.device, image_view_create_info, None)

            framebuffer_create_info = vk.VkFramebufferCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO,
                renderPass=self.render_pass,
                attachmentCount=1,
                pAttachments=[image_view],
                width=self.extent.width,
                height=self.extent.height,
                layers=1,
            )

            framebuffer = vk.vkCreateFramebuffer(self.device, framebuffer_create_info, None)
            self.framebuffers.append(framebuffer)


    def create_uniform_buffers(self):
        self.uniform_buffers = create_uniform_buffers(self.renderer, len(vk.vkGetSwapchainImagesKHR(self.device, self.swapchain)))

    def create_descriptor_pool(self):
        self.descriptor_pool = create_descriptor_pool(self.device, self.descriptor_set_layout)

    def create_descriptor_sets(self):
        self.descriptor_sets = create_descriptor_sets(self.device, self.descriptor_pool, self.descriptor_set_layout, self.uniform_buffers)

def create_framebuffers(device, swapchain, render_pass, extent): # This function is no longer needed
    swapchain_images = vk.vkGetSwapchainImagesKHR(device, swapchain)
    swapchain_images = vk.vkGetSwapchainImagesKHR(device, swapchain)
    framebuffers = []

    for image in swapchain_images:
        image_view_create_info = vk.VkImageViewCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
            image=image,
            viewType=vk.VK_IMAGE_VIEW_TYPE_2D,
            format=vk.vkGetSwapchainImagesKHR(device, swapchain)[0].format, # Getting format from first image, assuming all are same.
            components=vk.VkComponentMapping(), # Default component mapping
            subresourceRange=vk.VkImageSubresourceRange(
                aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT,
                baseMipLevel=0,
                levelCount=1,
                baseArrayLayer=0,
                layerCount=1,
            )
        )
        image_view = vk.vkCreateImageView(device, image_view_create_info, None)

        framebuffer_create_info = vk.VkFramebufferCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO,
            renderPass=render_pass,
            attachmentCount=1,
            pAttachments=[image_view],
            width=extent.width,
            height=extent.height,
            layers=1,
        )

        framebuffer = vk.vkCreateFramebuffer(device, framebuffer_create_info, None)
        framebuffers.append(framebuffer)
    def recreate_swapchain(self):
        vk.vkDeviceWaitIdle(self.device)

        # Destroy old swapchain and related resources
        for framebuffer in self.framebuffers:
            vk.vkDestroyFramebuffer(self.device, framebuffer, None)
        vk.vkDestroySwapchainKHR(self.device, self.swapchain, None)

        # Recreate swapchain and related resources
        self.create_swapchain()
        self.create_uniform_buffers()
        self.create_descriptor_pool()
        self.create_descriptor_sets()
        self.create_framebuffers()
        self.create_pipeline() # Recreate pipeline as well

        # Recreate command buffers
        self.renderer.create_command_buffers()

    def cleanup(self):
        for framebuffer in self.framebuffers:
            vk.vkDestroyFramebuffer(self.device, framebuffer, None)
        vk.vkDestroySwapchainKHR(self.device, self.swapchain, None)

        # Destroy other resources as needed
