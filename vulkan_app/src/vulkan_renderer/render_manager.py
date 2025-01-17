import vulkan as vk

class RenderManager:
    def __init__(self, vulkan_engine):
        self.vulkan_engine = vulkan_engine
        self.device = vulkan_engine.device
        self.command_pool = None # Initialize command_pool
        self.command_buffers = [] # Initialize command_buffers
        self.image_available_semaphores = [] # Initialize semaphores
        self.render_finished_semaphores = [] # Initialize semaphores
        self.in_flight_fences = [] # Initialize fences

    def render(self, renderer):
        try:
            image_index = vk.vkAcquireNextImageKHR(self.device, renderer.swapchain.swapchain, vk.UINT64_MAX, self.image_available_semaphores[renderer.current_frame], vk.VK_NULL_HANDLE) # Use renderer.current_frame
            renderer.current_frame = (image_index + 1) % len(renderer.swapchain.swapchain_images) # Update current_frame
        except vk.VkErrorOutOfDateKHR:
            renderer.recreate_swapchain() # Call recreate_swapchain on renderer
            return

        vk.vkWaitForFences(self.device, 1, [self.in_flight_fences[renderer.current_frame]], vk.VK_TRUE, vk.UINT64_MAX) # Wait for fence
        vk.vkResetFences(self.device, 1, [self.in_flight_fences[renderer.current_frame]]) # Reset fence

        vk.vkResetCommandBuffer(self.command_buffers[renderer.current_frame], 0) # Reset command buffer
        renderer.record_command_buffer(self.command_buffers[renderer.current_frame], image_index) # Call record_command_buffer on renderer

        submit_info = vk.VkSubmitInfo(
            sType=vk.VK_STRUCTURE_TYPE_SUBMIT_INFO,
            waitSemaphoreCount=1,
            pWaitSemaphores=[self.image_available_semaphores[renderer.current_frame]], # Use renderer.current_frame
            pWaitDstStageMask=[vk.VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT],
            commandBufferCount=1,
            pCommandBuffers=[self.command_buffers[renderer.current_frame]], # Use renderer.current_frame
            signalSemaphoreCount=1,
            pSignalSemaphores=[self.render_finished_semaphores[renderer.current_frame]], # Use renderer.current_frame
        )

        vk.vkQueueSubmit(self.vulkan_engine.graphics_queue, 1, [submit_info], self.in_flight_fences[renderer.current_frame]) # Submit to graphics queue

        present_info = vk.VkPresentInfoKHR(
            sType=vk.VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,
            waitSemaphoreCount=1,
            pWaitSemaphores=[self.render_finished_semaphores[renderer.current_frame]], # Use renderer.current_frame
            swapchainCount=1,
            pSwapchains=[renderer.swapchain.swapchain], # Access swapchain from renderer
            pImageIndices=[image_index],
            pResults=None,
        )

        try:
            vk.vkQueuePresentKHR(self.vulkan_engine.present_queue, present_info) # Present to present queue
        except vk.VkErrorOutOfDateKHR:
            renderer.recreate_swapchain() # Call recreate_swapchain on renderer
            return
    def __init__(self, vulkan_engine):
        self.vulkan_engine = vulkan_engine
        self.device = vulkan_engine.device

    def init_rendering(self, renderer):
        self.create_command_pool()
        self.create_command_buffers(renderer.swapchain.framebuffers)
        self.create_sync_objects(len(renderer.swapchain.swapchain_images))

    def create_command_pool(self):
        from vulkan_engine.command_buffer import create_command_pool as create_vk_command_pool
        self.command_pool = create_vk_command_pool(self.device, self.vulkan_engine.graphics_queue_family_index)
        self.vulkan_engine.resource_manager.add_resource(self.command_pool, "command_pool", self.vulkan_engine.resource_manager.destroy_command_pool)

    def create_command_buffers(self, framebuffers):
        from vulkan_engine.command_buffer import create_command_buffers as create_vk_command_buffers
        self.command_buffers = create_vk_command_buffers(self.device, self.command_pool, len(framebuffers))

    def create_sync_objects(self, swapchain_image_count):
        from vulkan_engine.synchronization import create_sync_objects as create_vk_sync_objects
        self.image_available_semaphores, self.render_finished_semaphores, self.in_flight_fences = create_vk_sync_objects(self.device, swapchain_image_count, self.vulkan_engine.resource_manager)

