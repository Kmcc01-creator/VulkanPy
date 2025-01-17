import vulkan as vk
import glfw

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
    """Creates a Vulkan instance.

    Raises:
        Exception: If instance creation fails.

    Returns:
        Tuple[vk.Instance, List[str]]: The created Vulkan instance and a list of enabled layers.
    """
    try:
        layer_properties = vk.vkEnumerateInstanceLayerProperties()
    except vk.VkError as e:
        raise Exception(f"Failed to enumerate instance layer properties: {e}")

    # Validation Layers
    try:
        available_layers = vk.vkEnumerateInstanceLayerProperties()
    except vk.VkError as e:
        raise Exception(f"Failed to enumerate instance layer properties: {e}")

    validation_layers = ["VK_LAYER_KHRONOS_validation"]
    enabled_layers = [layer.layerName for layer in available_layers if layer.layerName in validation_layers]

    try:
        enabled_extensions = check_instance_extensions(layer_properties)
    except Exception as e:  # check_instance_extensions raises its own exceptions
        raise

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
        return instance, enabled_layers
    except vk.VkError as e:
        raise Exception(f"Failed to create Vulkan instance: {e}")
