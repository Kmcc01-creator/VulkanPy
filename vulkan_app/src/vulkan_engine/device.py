import vulkan as vk

def create_device(instance, enabled_layers):
    """Creates a Vulkan device.

    Args:
        instance (vk.Instance): The Vulkan instance.
        enabled_layers (List[str]): A list of enabled layers.

    Raises:
        Exception: If no suitable physical device is found or device creation fails.

    Returns:
        Tuple[vk.Device, vk.PhysicalDevice, int]: The created device, the selected physical device, and the graphics queue family index.
    """
    try:
        physical_devices = vk.vkEnumeratePhysicalDevices(instance)
    except vk.VkError as e:
        raise Exception(f"Failed to enumerate physical devices: {e}")
    if not physical_devices:
        raise Exception("No Vulkan-capable GPUs found.")

    # TODO: Implement proper device selection based on features and capabilities.
    physical_device = physical_devices[0]  # Weak point: Selecting the first device without checking capabilities.

    try:
        queue_families = vk.vkGetPhysicalDeviceQueueFamilyProperties(physical_device)
    except vk.VkError as e:
        raise Exception(f"Failed to get physical device queue family properties: {e}")
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
        ppEnabledLayerNames=enabled_layers,

    )

    try:
        device = vk.vkCreateDevice(physical_device, device_create_info, None)

        return device, physical_device, graphics_queue_family_index
    except vk.VkError as e:
        raise Exception(f"Failed to create Vulkan device: {e}")
