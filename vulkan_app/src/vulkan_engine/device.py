import vulkan as vk

def create_device(instance):
    physical_devices = vk.vkEnumeratePhysicalDevices(instance)
    if not physical_devices:
        raise Exception("No Vulkan-capable GPUs found.")

    # For simplicity, select the first suitable device.
    # In a real application, you might want to add device selection logic here.
    physical_device = physical_devices[0]

    queue_families = vk.vkGetPhysicalDeviceQueueFamilyProperties(physical_device)
    graphics_queue_family_index = -1
    for i, queue_family in enumerate(queue_families):
        if queue_family.queueFlags & vk.VK_QUEUE_GRAPHICS_BIT:
            graphics_queue_family_index = i
            break

    if graphics_queue_family_index == -1:
        raise Exception("No graphics queue family found.")

    queue_create_info = vk.VkDeviceQueueCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
        queueFamilyIndex=graphics_queue_family_index,
        queueCount=1,
        pQueuePriorities=[1.0],  # Queue priority (0.0 - 1.0)
    )

    # Get supported extensions
    supported_extensions = [
        ext.extensionName
        for ext in vk.vkEnumerateDeviceExtensionProperties(physical_device, None)
    ]
    enabled_extensions = [vk.VK_KHR_SWAPCHAIN_EXTENSION_NAME] # Enabling the swapchain extension
    # Check if required extensions are supported
    if vk.VK_KHR_SWAPCHAIN_EXTENSION_NAME not in supported_extensions:
        raise Exception("Swapchain extension not supported")

    enabled_features = vk.VkPhysicalDeviceFeatures() # Enable desired device features
    device_create_info = vk.VkDeviceCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
        queueCreateInfoCount=1,
        pQueueCreateInfos=[queue_create_info],
        enabledExtensionCount=len(enabled_extensions),  # Enabling the swapchain extension
        ppEnabledExtensionNames=enabled_extensions, # Enabling the swapchain extension
        pEnabledFeatures=enabled_features,
        enabledLayerCount=len(enabled_layers),
        ppEnabledLayerNames=enabled_layers
    )

    try:
        device = vk.vkCreateDevice(physical_device, device_create_info, None)

        return device, physical_device, graphics_queue_family_index
    except vk.VkError as e:
        raise Exception(f"Failed to create Vulkan device: {e}")
