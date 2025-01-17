import vulkan as vk

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
