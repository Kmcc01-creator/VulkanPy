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

def begin_command_buffer(command_buffer):
    begin_info = vk.VkCommandBufferBeginInfo(
        sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
    )

    try:
        vk.vkBeginCommandBuffer(command_buffer, begin_info)
    except vk.VkError as e:
        raise Exception(f"Failed to begin recording command buffer: {e}")


def end_command_buffer(command_buffer):
    try:
        vk.vkEndCommandBuffer(command_buffer)
    except vk.VkError as e:
        raise Exception(f"Failed to end recording command buffer: {e}")
