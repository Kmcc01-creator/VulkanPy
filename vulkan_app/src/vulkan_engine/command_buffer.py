import vulkan as vk

def create_command_pool(device, queue_family_index):
    pool_create_info = vk.VkCommandPoolCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
        queueFamilyIndex=queue_family_index,
        flags=vk.VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT, # Allow resetting individual command buffers
    )
    try:
        return vk.vkCreateCommandPool(device, pool_create_info, None)
    except vk.VkError as e:
        raise Exception(f"Failed to create command pool: {e}")

def create_command_buffers(device, command_pool, count):
    allocate_info = vk.VkCommandBufferAllocateInfo(
        sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
        commandPool=command_pool,
        level=vk.VK_COMMAND_BUFFER_LEVEL_PRIMARY,
        commandBufferCount=count,
    )

    try:
        return vk.vkAllocateCommandBuffers(device, allocate_info)
    except vk.VkError as e:
        raise Exception(f"Failed to allocate command buffers: {e}")
