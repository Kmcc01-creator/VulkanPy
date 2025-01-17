import vulkan as vk

def check_instance_extensions(layer_properties):
    available_extensions = vk.vkEnumerateInstanceExtensionProperties(None, None)

    glfw_extensions = set(glfw.get_required_instance_extensions())
    required_extensions = glfw_extensions | {vk.VK_KHR_SURFACE_EXTENSION_NAME}

    for extension in required_extensions:
        found = False
        for available_ext in available_extensions:
            if available_ext.extensionName == extension:
                found = True
                break
        if not found:
            raise Exception(f"Required Vulkan extension not found: {extension}")

    return required_extensions

def create_instance():
    layer_properties = vk.vkEnumerateInstanceLayerProperties()
    enabled_layers = []  # Add desired validation layers here if needed

    enabled_extensions = check_instance_extensions(layer_properties)

    app_info = vk.VkApplicationInfo(
        sType=vk.VK_STRUCTURE_TYPE_APPLICATION_INFO,
        pApplicationName="Vulkan App",
        applicationVersion=vk.VK_MAKE_VERSION(1, 0, 0),
        pEngineName="No Engine",
        engineVersion=vk.VK_MAKE_VERSION(1, 0, 0),
        apiVersion=vk.VK_API_VERSION_1_0,
    )

    create_info = vk.VkInstanceCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
        pApplicationInfo=app_info,
        enabledLayerCount=len(enabled_layers),
        ppEnabledLayerNames=enabled_layers,
        enabledExtensionCount=len(enabled_extensions),
        ppEnabledExtensionNames=list(enabled_extensions),  # Convert set to list
    )

    try:
        instance = vk.vkCreateInstance(create_info, None)
        return instance
    except vk.VkError as e:
        raise Exception(f"Failed to create Vulkan instance: {e}")
