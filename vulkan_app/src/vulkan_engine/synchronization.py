import vulkan as vk

def create_sync_objects(device, num_images, resource_manager):
    semaphore_create_info = vk.VkSemaphoreCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO
    )
    fence_create_info = vk.VkFenceCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_FENCE_CREATE_INFO,
        flags=vk.VK_FENCE_CREATE_SIGNALED_BIT,
    )

    image_available_semaphores = []
    render_finished_semaphores = []
    in_flight_fences = []

    for _ in range(num_images):
        try:
            image_available_semaphores.append(vk.vkCreateSemaphore(device, semaphore_create_info, None))
            render_finished_semaphores.append(vk.vkCreateSemaphore(device, semaphore_create_info, None))
            image_available_semaphores.append(vk.vkCreateSemaphore(device, semaphore_create_info, None))
            resource_manager.add_resource(image_available_semaphores[-1], "semaphore", resource_manager.destroy_semaphore) # Add to resource manager

            render_finished_semaphores.append(vk.vkCreateSemaphore(device, semaphore_create_info, None))
            resource_manager.add_resource(render_finished_semaphores[-1], "semaphore", resource_manager.destroy_semaphore) # Add to resource manager

            in_flight_fences.append(vk.vkCreateFence(device, fence_create_info, None))
            resource_manager.add_resource(in_flight_fences[-1], "fence", resource_manager.destroy_fence) # Add to resource manager
        except vk.VkError as e:
            raise Exception(f"Failed to create synchronization objects: {e}")

    return image_available_semaphores, render_finished_semaphores, in_flight_fences
