import vulkan as vk
import glfw

class VulkanRenderer:
    def __init__(self, window):
        self.window = window

        # Vulkan Instance creation
        self.instance, self.enabled_layers = self.create_instance()

        # Vulkan Device creation
        self.device, self.physical_device, self.graphics_queue_family_index = self.create_device()

        # Create window surface
        self.surface = glfw.create_window_surface(self.instance, window, None, None)

        # Swapchain creation (requires window surface)
        self.swapchain, self.swapchain_extent = self.create_swapchain() # Getting swapchain extent
        self.render_pass = self.create_render_pass()
        self.pipeline, self.pipeline_layout = self.create_pipeline() # Getting pipeline and layout
        self.framebuffers = self.create_framebuffers()
        self.create_command_pool() # New: create command pool
        self.create_command_buffers() # New: create command buffers
        self.create_sync_objects() # New: create synchronization objects
        self.create_vertex_buffer()

        self.current_frame = 0
        self.graphics_queue = vk.vkGetDeviceQueue(self.device, self.graphics_queue_family_index, 0)
        self.present_queue = vk.vkGetDeviceQueue(self.device, self.graphics_queue_family_index, 0) # Using graphics queue for present for now

        glfw.set_framebuffer_size_callback(self.window, self.framebuffer_resize_callback)

    def framebuffer_resize_callback(self, window, width, height):
        self.recreate_swapchain()

    def create_instance(self):
        from vulkan_engine.instance import create_instance as create_vk_instance
        return create_vk_instance()

    def create_device(self):
        from vulkan_engine.device import create_device as create_vk_device
        return create_vk_device(self.instance, self.enabled_layers)

    def create_swapchain(self):
        from vulkan_engine.swapchain import create_swapchain as create_vk_swapchain
        swapchain, extent = create_vk_swapchain(self.instance, self.device, self.physical_device, self.surface, self.graphics_queue_family_index, self.graphics_queue_family_index) # Using graphics queue for present for now
        return swapchain, extent

    def create_render_pass(self):
        from vulkan_engine.swapchain import create_render_pass as create_vk_render_pass
        swapchain_image_format = vk.vkGetSwapchainImagesKHR(self.device, self.swapchain)[0].format # Getting format from first image
        return create_vk_render_pass(self.device, swapchain_image_format)

    def create_pipeline(self):
        from vulkan_engine.pipeline import create_pipeline as create_vk_pipeline
        return create_vk_pipeline(self.device, self.swapchain_extent, self.render_pass)

    def create_framebuffers(self):
        from vulkan_engine.swapchain import create_framebuffers as create_vk_framebuffers
        return create_vk_framebuffers(self.device, self.swapchain, self.render_pass, self.swapchain_extent)

    def create_command_pool(self): # New function
        from vulkan_engine.command_buffer import create_command_pool as create_vk_command_pool
        self.command_pool = create_vk_command_pool(self.device, self.graphics_queue_family_index)

    def create_command_buffers(self): # New function
        from vulkan_engine.command_buffer import create_command_buffers as create_vk_command_buffers
        self.command_buffers = create_vk_command_buffers(self.device, self.command_pool, len(self.framebuffers))

    def create_sync_objects(self): # New function
        from vulkan_engine.synchronization import create_sync_objects as create_vk_sync_objects
        self.image_available_semaphores, self.render_finished_semaphores, self.in_flight_fences = create_vk_sync_objects(self.device, len(self.framebuffers))

    def recreate_swapchain(self):
        vk.vkDeviceWaitIdle(self.device)

        # Destroy old swapchain and related resources
        for framebuffer in self.framebuffers:
            vk.vkDestroyFramebuffer(self.device, framebuffer, None)
        vk.vkDestroySwapchainKHR(self.device, self.swapchain, None)

        # Recreate swapchain and related resources
        self.swapchain, self.swapchain_extent = self.create_swapchain()
        self.render_pass = self.create_render_pass()
        self.framebuffers = self.create_framebuffers()

        # Recreate command buffers
        self.create_command_buffers()


    def render(self):
        try:
            image_index = vk.vkAcquireNextImageKHR(self.device, self.swapchain, 1000000000, self.image_available_semaphores[self.current_frame], vk.VK_NULL_HANDLE)
        except vk.VkErrorOutOfDateKHR:
            self.recreate_swapchain()
            return

        vk.vkResetFences(self.device, 1, [self.in_flight_fences[self.current_frame]])

        vk.vkResetCommandBuffer(self.command_buffers[self.current_frame], 0)
        self.record_command_buffer(self.command_buffers[self.current_frame], image_index)

        submit_info = vk.VkSubmitInfo(
            sType=vk.VK_STRUCTURE_TYPE_SUBMIT_INFO,
            waitSemaphoreCount=1,
            pWaitSemaphores=[self.image_available_semaphores[self.current_frame]],
            pWaitDstStageMask=[vk.VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT],
            commandBufferCount=1,
            pCommandBuffers=[self.command_buffers[self.current_frame]],
            signalSemaphoreCount=1,
            pSignalSemaphores=[self.render_finished_semaphores[self.current_frame]],
        )

        try:
            vk.vkQueueSubmit(self.graphics_queue, 1, [submit_info], self.in_flight_fences[self.current_frame])
        except vk.VkErrorOutOfDateKHR:
            self.recreate_swapchain()
            return

        present_info = vk.VkPresentInfoKHR(
            sType=vk.VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,
            waitSemaphoreCount=1,
            pWaitSemaphores=[self.render_finished_semaphores[self.current_frame]],
            swapchainCount=1,
            pSwapchains=[self.swapchain],
            pImageIndices=[image_index],
        )

        try:
            vk.vkQueuePresentKHR(self.present_queue, present_info)
        except vk.VkErrorOutOfDateKHR:
            self.recreate_swapchain()
            return

        self.current_frame = (self.current_frame + 1) % len(self.framebuffers)

    def record_command_buffer(self, command_buffer, image_index):
        begin_info = vk.VkCommandBufferBeginInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
        )

        try:
            vk.vkBeginCommandBuffer(command_buffer, begin_info)
        except vk.VkError as e:
            raise Exception(f"Failed to begin recording command buffer: {e}")

        render_pass_begin_info = vk.VkRenderPassBeginInfo(
            sType=vk.VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO,
            renderPass=self.render_pass,
            framebuffer=self.framebuffers[image_index],
            renderArea=vk.VkRect2D(
                offset=vk.VkOffset2D(x=0, y=0),
                extent=self.swapchain_extent,
            ),
            clearValueCount=1,
            pClearValues=[vk.VkClearValue(color=vk.VkClearColorValue(float32=[0.0, 0.0, 0.0, 1.0]))],
        )

        vk.vkCmdBeginRenderPass(command_buffer, render_pass_begin_info, vk.VK_SUBPASS_CONTENTS_INLINE)
        vk.vkCmdBindPipeline(command_buffer, vk.VK_PIPELINE_BIND_POINT_GRAPHICS, self.pipeline)

        viewport = vk.VkViewport(
            x=0.0,
            y=0.0,
            width=float(self.swapchain_extent.width),
            height=float(self.swapchain_extent.height),
            minDepth=0.0,
            maxDepth=1.0,
        )
        vk.vkCmdSetViewport(command_buffer, 0, 1, [viewport])

        scissor = vk.VkRect2D(
            offset=vk.VkOffset2D(x=0, y=0),
            extent=self.swapchain_extent,
        )
        vk.vkCmdSetScissor(command_buffer, 0, 1, [scissor])

        vk.vkCmdBindVertexBuffers(command_buffer, 0, 1, [self.vertex_buffer], [0])
        vk.vkCmdDraw(command_buffer, 3, 1, 0, 0)
        vk.vkCmdEndRenderPass(command_buffer)

        try:
            vk.vkEndCommandBuffer(command_buffer)
        except vk.VkError as e:
            raise Exception(f"Failed to end recording command buffer: {e}")

    def create_vertex_buffer(self):
        from src.vertex import Vertex
        vertices = [
            Vertex([-0.5, -0.5, 0.0], [1.0, 0.0, 0.0]),
            Vertex([0.5, -0.5, 0.0], [0.0, 1.0, 0.0]),
            Vertex([0.0, 0.5, 0.0], [0.0, 0.0, 1.0]),
        ]
        buffer_size = len(vertices) * 2 * 4 * 3 # Number of vertices * 2 attributes (pos, color) * 4 bytes/float * 3 floats/attribute

        staging_buffer, staging_buffer_memory = self.create_buffer(
            buffer_size, vk.VK_BUFFER_USAGE_TRANSFER_SRC_BIT, vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT
        )

        data_ptr = vk.vkMapMemory(self.device, staging_buffer_memory, 0, buffer_size, 0)
        for i, vertex in enumerate(vertices):
            byte_offset = i * 2 * 4 * 3
            vk.ffi.memmove(data_ptr + byte_offset, vertex.pos.buffer_info()[0], 3 * 4) # Copy position data
            vk.ffi.memmove(data_ptr + byte_offset + 3 * 4, vertex.color.buffer_info()[0], 3 * 4) # Copy color data
        vk.vkUnmapMemory(self.device, staging_buffer_memory)

        self.vertex_buffer, self.vertex_buffer_memory = self.create_buffer(
            buffer_size, vk.VK_BUFFER_USAGE_TRANSFER_DST_BIT | vk.VK_BUFFER_USAGE_VERTEX_BUFFER_BIT, vk.VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT
        )

        self.copy_buffer(staging_buffer, self.vertex_buffer, buffer_size)

        vk.vkDestroyBuffer(self.device, staging_buffer, None)
        vk.vkFreeMemory(self.device, staging_buffer_memory, None)

    def create_buffer(self, size, usage, properties):
        from vulkan_engine.buffer import create_buffer as create_vk_buffer
        return create_vk_buffer(self.device, self.physical_device, size, usage, properties)

    def copy_buffer(self, src_buffer, dst_buffer, size):
        command_buffer = self.begin_single_time_commands()

        copy_region = vk.VkBufferCopy(srcOffset=0, dstOffset=0, size=size)
        vk.vkCmdCopyBuffer(command_buffer, src_buffer, dst_buffer, 1, [copy_region])

        self.end_single_time_commands(command_buffer)

    def begin_single_time_commands(self):
        allocate_info = vk.VkCommandBufferAllocateInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
            level=vk.VK_COMMAND_BUFFER_LEVEL_PRIMARY,
            commandPool=self.command_pool,
            commandBufferCount=1,
        )
        command_buffer = vk.vkAllocateCommandBuffers(self.device, allocate_info)[0]

        begin_info = vk.VkCommandBufferBeginInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
            flags=vk.VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT,
        )
        vk.vkBeginCommandBuffer(command_buffer, begin_info)

        return command_buffer

    def end_single_time_commands(self, command_buffer):
        vk.vkEndCommandBuffer(command_buffer)

        submit_info = vk.VkSubmitInfo(
            sType=vk.VK_STRUCTURE_TYPE_SUBMIT_INFO,
            commandBufferCount=1,
            pCommandBuffers=[command_buffer],
        )
        vk.vkQueueSubmit(self.graphics_queue, 1, [submit_info], vk.VK_NULL_HANDLE)
        vk.vkQueueWaitIdle(self.graphics_queue)

        vk.vkFreeCommandBuffers(self.device, self.command_pool, 1, [command_buffer])

    def destroy_sync_objects(self):
        for fence in self.in_flight_fences:
            vk.vkWaitForFences(self.device, 1, [fence], vk.VK_TRUE, 1000000000) # Wait for fence before destroying it
            vk.vkDestroyFence(self.device, fence, None)

        for semaphore in self.image_available_semaphores:
            vk.vkDestroySemaphore(self.device, semaphore, None)

        for semaphore in self.render_finished_semaphores:
            vk.vkDestroySemaphore(self.device, semaphore, None)


    def cleanup(self):
        vk.vkDeviceWaitIdle(self.device) # Wait for device to be idle before destroying resources

        for fence in self.in_flight_fences:
            vk.vkDestroyFence(self.device, fence, None)

        for semaphore in self.image_available_semaphores:
            vk.vkDestroySemaphore(self.device, semaphore, None)

        for semaphore in self.render_finished_semaphores:
            vk.vkDestroySemaphore(self.device, semaphore, None)

        vk.vkDestroyCommandPool(self.device, self.command_pool, None)

        if self.pipeline is not None: # Check for None before destroying
            vk.vkDestroyPipeline(self.device, self.pipeline, None)
        if self.pipeline_layout is not None: # Check for None before destroying
            vk.vkDestroyPipelineLayout(self.device, self.pipeline_layout, None)
        if self.render_pass is not None: # Check for None before destroying
            vk.vkDestroyRenderPass(self.device, self.render_pass, None)

        for framebuffer in self.framebuffers or []: # Handle potential empty list
            vk.vkDestroyFramebuffer(self.device, framebuffer, None)

        vk.vkDestroySwapchainKHR(self.device, self.swapchain, None)
        vk.vkDestroySurfaceKHR(self.instance, self.surface, None)
        vk.vkDestroyDevice(self.device, None)
        vk.vkDestroyBuffer(self.device, self.vertex_buffer, None)
        vk.vkFreeMemory(self.device, self.vertex_buffer_memory, None)
        self.destroy_sync_objects()
            vk.vkDestroyFence(self.device, fence, None)

        for semaphore in self.image_available_semaphores:
            vk.vkDestroySemaphore(self.device, semaphore, None)

        for semaphore in self.render_finished_semaphores:
            vk.vkDestroySemaphore(self.device, semaphore, None)

        vk.vkDestroyCommandPool(self.device, self.command_pool, None)

        vk.vkDestroyPipeline(self.device, self.pipeline, None)
        vk.vkDestroyPipelineLayout(self.device, self.pipeline_layout, None)
        vk.vkDestroyRenderPass(self.device, self.render_pass, None)

        for framebuffer in self.framebuffers:
            vk.vkDestroyFramebuffer(self.device, framebuffer, None)

        vk.vkDestroySwapchainKHR(self.device, self.swapchain, None)
        vk.vkDestroySurfaceKHR(self.instance, self.surface, None)
        vk.vkDestroyDevice(self.device, None)
        vk.vkDestroyInstance(self.instance, None)
            vk.vkDestroyFence(self.device, fence, None)

        for semaphore in self.image_available_semaphores:
            vk.vkDestroySemaphore(self.device, semaphore, None)

        for semaphore in self.render_finished_semaphores:
            vk.vkDestroySemaphore(self.device, semaphore, None)

        vk.vkDestroyCommandPool(self.device, self.command_pool, None)

        vk.vkDestroyPipeline(self.device, self.pipeline, None)
        vk.vkDestroyPipelineLayout(self.device, self.pipeline_layout, None)
        vk.vkDestroyRenderPass(self.device, self.render_pass, None)

        for framebuffer in self.framebuffers:
            vk.vkDestroyFramebuffer(self.device, framebuffer, None)

        vk.vkDestroySwapchainKHR(self.device, self.swapchain, None)
        vk.vkDestroySurfaceKHR(self.instance, self.surface, None)
        vk.vkDestroyDevice(self.device, None)
        vk.vkDestroyInstance(self.instance, None)
