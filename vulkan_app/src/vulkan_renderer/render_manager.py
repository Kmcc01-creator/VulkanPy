import vulkan as vk
import logging
from typing import List, Tuple
from vulkan_engine.command_buffer import create_command_pool, create_command_buffers
from vulkan_engine.synchronization import create_sync_objects
from src.ecs.components import Mesh, Transform, Material
from src.ecs.world import World
from vulkan_engine.vulkan_engine import VulkanEngine
from src.shader_manager import ShaderManager

logger = logging.getLogger(__name__)

class RenderManager:
    def __init__(self, vulkan_engine: VulkanEngine, shader_manager: ShaderManager) -> None:
        self.vulkan_engine = vulkan_engine
        self.shader_manager = shader_manager
        self.device = vulkan_engine.device
        self.command_pool: vk.VkCommandPool = None
        self.command_buffers: List[vk.VkCommandBuffer] = []
        self.image_available_semaphores: List[vk.VkSemaphore] = []
        self.render_finished_semaphores: List[vk.VkSemaphore] = []
        self.in_flight_fences: List[vk.VkFence] = []
        self.current_frame = 0
        self.uniform_buffers = []
        self.descriptor_sets = []
        logger.info("Initializing RenderManager")
        try:
            self.init_rendering()
            logger.info("RenderManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RenderManager: {str(e)}")
            raise

    def init_rendering(self) -> None:
        self.create_command_pool()
        self.create_command_buffers()
        self.create_sync_objects()
        self.create_uniform_buffers()
        self.create_descriptor_sets()

    def create_command_pool(self) -> None:
        self.command_pool = create_command_pool(self.device, self.vulkan_engine.graphics_queue_family_index)
        self.vulkan_engine.resource_manager.add_resource(self.command_pool, "command_pool", self.vulkan_engine.resource_manager.destroy_command_pool)

    def create_command_buffers(self) -> None:
        self.command_buffers = create_command_buffers(self.device, self.command_pool, len(self.vulkan_engine.swapchain.framebuffers))

    def create_sync_objects(self) -> None:
        self.image_available_semaphores, self.render_finished_semaphores, self.in_flight_fences = self.vulkan_engine.resource_manager.create_sync_objects(len(self.vulkan_engine.swapchain.swapchain_images))

    def render(self, world: World) -> None:
        try:
            image_index = self.acquire_next_image()
            self.wait_for_fences()
            self.reset_fences()
            self.reset_command_buffer()
            self.record_command_buffer(self.command_buffers[self.current_frame], image_index, world)
            self.submit_command_buffer(image_index)
            self.present_image(image_index)
        except vk.VkErrorOutOfDateKHR:
            self.vulkan_engine.recreate_swapchain()
        except vk.VkError as e:
            logger.error(f"Render failed: {str(e)}")
            raise RuntimeError(f"Render failed: {str(e)}")

        self.current_frame = (self.current_frame + 1) % len(self.vulkan_engine.swapchain.swapchain_images)

    def acquire_next_image(self) -> int:
        return vk.vkAcquireNextImageKHR(
            self.device,
            self.vulkan_engine.swapchain.swapchain,
            vk.UINT64_MAX,
            self.image_available_semaphores[self.current_frame],
            vk.VK_NULL_HANDLE
        )

    def wait_for_fences(self) -> None:
        vk.vkWaitForFences(self.device, 1, [self.in_flight_fences[self.current_frame]], vk.VK_TRUE, vk.UINT64_MAX)

    def reset_fences(self) -> None:
        vk.vkResetFences(self.device, 1, [self.in_flight_fences[self.current_frame]])

    def reset_command_buffer(self) -> None:
        vk.vkResetCommandBuffer(self.command_buffers[self.current_frame], 0)

    def submit_command_buffer(self, image_index: int) -> None:
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

    def present_image(self, image_index: int) -> None:
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

    def record_command_buffer(self, command_buffer: vk.VkCommandBuffer, image_index: int, world: World) -> None:
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
            vk.vkCmdBindIndexBuffer(command_buffer, mesh.index_buffer, 0, vk.VK_INDEX_TYPE_UINT32)
            vk.vkCmdDrawIndexed(command_buffer, mesh.index_count, 1, 0, 0, 0)

        vk.vkCmdEndRenderPass(command_buffer)
        vk.vkEndCommandBuffer(command_buffer)

    def cleanup(self) -> None:
        logger.info("Cleaning up RenderManager resources")
        vk.vkDeviceWaitIdle(self.device)
        
        for fence in self.in_flight_fences:
            self.vulkan_engine.resource_manager.destroy_fence(fence)
        
        for semaphore in self.image_available_semaphores + self.render_finished_semaphores:
            self.vulkan_engine.resource_manager.destroy_semaphore(semaphore)
        
        self.vulkan_engine.resource_manager.destroy_command_pool(self.command_pool)

