import vulkan as vk

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
        imageExtent=surface_capabilities.currentExtent,
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
        return swapchain
    except vk.VkError as e:
        raise Exception(f"Failed to create swapchain: {e}")


def create_framebuffers(device, swapchain, render_pass, extent):
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

    return framebuffers
