import vulkan as vk
from vulkan_engine.command_buffer import create_command_pool, create_command_buffers
from vulkan_engine.synchronization import create_sync_objects

class RenderManager:
    def __init__(self, vulkan_engine):
        self.vulkan_engine = vulkan_engine
        self.device = vulkan_engine.device
        self.command_pool = None
        self.command_buffers = []
        self.image_available_semaphores = []
        self.render_finished_semaphores = []
        self.in_flight_fences = []
        self.current_frame = 0
        self.init_rendering()

    def init_rendering(self):
        self.create_command_pool()
        self.create_command_buffers()
        self.create_sync_objects()

    def create_command_pool(self):
        self.command_pool = create_command_pool(self.device, self.vulkan_engine.graphics_queue_family_index)
        self.vulkan_engine.resource_manager.add_resource(self.command_pool, "command_pool", self.vulkan_engine.resource_manager.destroy_command_pool)

    def create_command_buffers(self):
        self.command_buffers = create_command_buffers(self.device, self.command_pool, len(self.vulkan_engine.swapchain.framebuffers))

    def create_sync_objects(self):
        self.image_available_semaphores, self.render_finished_semaphores, self.in_flight_fences = create_sync_objects(
            self.device, len(self.vulkan_engine.swapchain.swapchain_images), self.vulkan_engine.resource_manager
        )

    def render(self, world):
        try:
            image_index = vk.vkAcquireNextImageKHR(
                self.device,
                self.vulkan_engine.swapchain.swapchain,
                vk.UINT64_MAX,
                self.image_available_semaphores[self.current_frame],
                vk.VK_NULL_HANDLE
            )
        except vk.VkErrorOutOfDateKHR:
            self.vulkan_engine.recreate_swapchain()
            return
        except vk.VkError as e:
            raise RuntimeError(f"Failed to acquire swap chain image: {str(e)}")

        try:
            vk.vkWaitForFences(self.device, 1, [self.in_flight_fences[self.current_frame]], vk.VK_TRUE, vk.UINT64_MAX)
        except vk.VkError as e:
            raise RuntimeError(f"Failed to wait for fence: {str(e)}")

        try:
            vk.vkResetFences(self.device, 1, [self.in_flight_fences[self.current_frame]])
        except vk.VkError as e:
            raise RuntimeError(f"Failed to reset fence: {str(e)}")

        try:
            vk.vkResetCommandBuffer(self.command_buffers[self.current_frame], 0)
        except vk.VkError as e:
            raise RuntimeError(f"Failed to reset command buffer: {str(e)}")

        self.record_command_buffer(self.command_buffers[self.current_frame], image_index, world)

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

        vk.vkQueueSubmit(self.vulkan_engine.graphics_queue, 1, [submit_info], self.in_flight_fences[self.current_frame])

        present_info = vk.VkPresentInfoKHR(
            sType=vk.VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,
            waitSemaphoreCount=1,
            pWaitSemaphores=[self.render_finished_semaphores[self.current_frame]],
            swapchainCount=1,
            pSwapchains=[self.vulkan_engine.swapchain.swapchain],
            pImageIndices=[image_index],
        )

        try:
            vk.vkQueuePresentKHR(self.vulkan_engine.present_queue, present_info)
        except vk.VkErrorOutOfDateKHR:
            self.vulkan_engine.recreate_swapchain()
            return

        self.current_frame = (self.current_frame + 1) % len(self.vulkan_engine.swapchain.swapchain_images)

    def record_command_buffer(self, command_buffer, image_index, world):
        begin_info = vk.VkCommandBufferBeginInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
        )

        vk.vkBeginCommandBuffer(command_buffer, begin_info)

        render_pass_begin_info = vk.VkRenderPassBeginInfo(
            sType=vk.VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO,
            renderPass=self.vulkan_engine.swapchain.render_pass,
            framebuffer=self.vulkan_engine.swapchain.framebuffers[image_index],
            renderArea=vk.VkRect2D(
                offset=vk.VkOffset2D(x=0, y=0),
                extent=self.vulkan_engine.swapchain.swapchain_extent,
            ),
            clearValueCount=1,
            pClearValues=[vk.VkClearValue(color=vk.VkClearColorValue(float32=[0.0, 0.0, 0.0, 1.0]))],
        )

        vk.vkCmdBeginRenderPass(command_buffer, render_pass_begin_info, vk.VK_SUBPASS_CONTENTS_INLINE)
        vk.vkCmdBindPipeline(command_buffer, vk.VK_PIPELINE_BIND_POINT_GRAPHICS, self.vulkan_engine.swapchain.pipeline)

        viewport = vk.VkViewport(
            x=0.0,
            y=0.0,
            width=float(self.vulkan_engine.swapchain.swapchain_extent.width),
            height=float(self.vulkan_engine.swapchain.swapchain_extent.height),
            minDepth=0.0,
            maxDepth=1.0,
        )
        vk.vkCmdSetViewport(command_buffer, 0, 1, [viewport])

        scissor = vk.VkRect2D(
            offset=vk.VkOffset2D(x=0, y=0),
            extent=self.vulkan_engine.swapchain.swapchain_extent,
        )
        vk.vkCmdSetScissor(command_buffer, 0, 1, [scissor])

        # Render entities in the world
        for entity, (mesh, transform) in world.get_components(Mesh, Transform):
            vk.vkCmdBindVertexBuffers(command_buffer, 0, 1, [mesh.vertex_buffer], [0])
            vk.vkCmdDraw(command_buffer, mesh.vertex_count, 1, 0, 0)

        vk.vkCmdEndRenderPass(command_buffer)
        vk.vkEndCommandBuffer(command_buffer)

