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


class Swapchain:
    def __init__(self, renderer, resource_manager):
        self.renderer = renderer
        self.resource_manager = resource_manager
        self.renderer = renderer
        self.instance = renderer.instance
        self.device = renderer.device
        self.physical_device = renderer.physical_device
        self.surface = renderer.surface
        self.graphics_queue_family_index = renderer.graphics_queue_family_index
        self.present_queue_family_index = renderer.present_queue_family_index

        self.swapchain = None
        self.swapchain_images = []
        self.image_views = []
        self.extent = None
        self.render_pass = None
        self.pipeline = None
        self.pipeline_layout = None
        self.framebuffers = []
        self.uniform_buffers = []
        self.descriptor_pool = None
        self.descriptor_sets = []
        self.descriptor_set_layout = None

        self.create_swapchain()
        self.create_render_pass()
        self.create_pipeline()
        self.create_framebuffers()
        self.create_uniform_buffers()
        self.create_descriptor_pool()
        self.create_descriptor_sets()
        glfw.set_framebuffer_size_callback(self.renderer.window, self.framebuffer_resize_callback) # Set callback here

    def framebuffer_resize_callback(self, window, width, height):
        self.recreate_swapchain()


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
            imageExtent=vk.VkExtent2D(
                width=max(surface_capabilities.minImageExtent.width, min(surface_capabilities.maxImageExtent.width, surface_capabilities.currentExtent.width)),
                height=max(surface_capabilities.minImageExtent.height, min(surface_capabilities.maxImageExtent.height, surface_capabilities.currentExtent.height))
            ),
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
            p_queue_family_indices = [self.graphics_queue_family_index, self.present_queue_family_index]
            swapchain_create_info.pQueueFamilyIndices = p_queue_family_indices

        try:
            self.swapchain = vk.vkCreateSwapchainKHR(self.device, swapchain_create_info, None)
            self.resource_manager.add_resource(self.swapchain, "swapchain", self.resource_manager.destroy_swapchain)  # noqa: E501
            self.extent = surface_capabilities.currentExtent
            swapchain_images = vk.vkGetSwapchainImagesKHR(self.device, self.swapchain)  # noqa: E501
            self.swapchain_images = swapchain_images
            self.create_image_views()
        except vk.VkError as e:
            raise Exception(f"Failed to create swapchain: {e}")

    def choose_surface_format(self):
        formats = vk.vkGetPhysicalDeviceSurfaceFormatsKHR(self.physical_device, self.surface)
        if not formats:
            raise Exception("No surface formats available.")

        # For simplicity, select the first available format.
        # In a real application, you might want to add format selection logic here.
        return formats[0]

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
            vk.vkDestroyFramebuffer(self.device, framebuffer, None)
        vk.vkDestroySwapchainKHR(self.device, self.swapchain, None)

        # Recreate swapchain and related resources
        self.create_swapchain()
        self.create_render_pass()
        self.create_pipeline()
        self.create_framebuffers()
        self.create_uniform_buffers()
        self.create_descriptor_pool()
        self.create_descriptor_sets()

        self.renderer.create_command_buffers()

