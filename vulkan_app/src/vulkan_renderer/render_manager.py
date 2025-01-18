import vulkan as vk
import logging
from typing import List, Optional, Dict, Set
from .vulkan_resources import CommandPool, VulkanResource
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class RenderPassConfig:
    color_attachment_format: int
    depth_attachment_format: int
    sample_count: int = vk.VK_SAMPLE_COUNT_1_BIT
    clear_color: List[float] = None

    def __post_init__(self):
        if self.clear_color is None:
            self.clear_color = [0.0, 0.0, 0.0, 1.0]

class RenderManager:
    def __init__(self, vulkan_engine):
        self.engine = vulkan_engine
        self.device = vulkan_engine.device.device
        self.physical_device = vulkan_engine.device.physical_device
        
        # Command pools and buffers
        self.command_pools: Dict[int, CommandPool] = {}
        self.command_buffers: List[vk.VkCommandBuffer] = []
        
        # Synchronization objects
        self.image_available_semaphores: List[vk.VkSemaphore] = []
        self.render_finished_semaphores: List[vk.VkSemaphore] = []
        self.in_flight_fences: List[vk.VkFence] = []
        
        # Frame management
        self.current_frame = 0
        self.max_frames_in_flight = 2
        
        self.initialize()

    def initialize(self) -> None:
        """Initialize render manager resources."""
        try:
            self.create_command_pools()
            self.create_command_buffers()
            self.create_sync_objects()
            logger.info("Render manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize render manager: {e}")
            self.cleanup()
            raise

    def create_command_pools(self) -> None:
        """Create command pools for graphics and compute operations."""
        graphics_pool = CommandPool(
            self.device,
            self.engine.device.queue_family_indices.graphics_family
        )
        self.command_pools[vk.VK_QUEUE_GRAPHICS_BIT] = graphics_pool

        if self.engine.device.queue_family_indices.compute_family is not None:
            compute_pool = CommandPool(
                self.device,
                self.engine.device.queue_family_indices.compute_family
            )
            self.command_pools[vk.VK_QUEUE_COMPUTE_BIT] = compute_pool

    def create_command_buffers(self) -> None:
        """Create command buffers for rendering."""
        graphics_pool = self.command_pools[vk.VK_QUEUE_GRAPHICS_BIT]
        self.command_buffers = graphics_pool.allocate_buffers(
            vk.VK_COMMAND_BUFFER_LEVEL_PRIMARY,
            self.engine.swapchain.image_count
        )

    def create_sync_objects(self) -> None:
        """Create synchronization objects for frame management."""
        try:
            semaphore_info = vk.VkSemaphoreCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO
            )
            fence_info = vk.VkFenceCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_FENCE_CREATE_INFO,
                flags=vk.VK_FENCE_CREATE_SIGNALED_BIT
            )

            for _ in range(self.max_frames_in_flight):
                self.image_available_semaphores.append(
                    vk.vkCreateSemaphore(self.device, semaphore_info, None)
                )
                self.render_finished_semaphores.append(
                    vk.vkCreateSemaphore(self.device, semaphore_info, None)
                )
                self.in_flight_fences.append(
                    vk.vkCreateFence(self.device, fence_info, None)
                )
        except Exception as e:
            logger.error(f"Failed to create synchronization objects: {e}")
            raise

    def begin_frame(self) -> Optional[int]:
        """Begin a new frame."""
        try:
            # Wait for the previous frame
            vk.vkWaitForFences(
                self.device,
                1,
                [self.in_flight_fences[self.current_frame]],
                vk.VK_TRUE,
                np.uint64(-1)
            )

            # Acquire next image
            try:
                image_index = vk.vkAcquireNextImageKHR(
                    self.device,
                    self.engine.swapchain.handle,
                    np.uint64(-1),
                    self.image_available_semaphores[self.current_frame],
                    vk.VK_NULL_HANDLE
                )
            except vk.VkErrorOutOfDateKHR:
                self.engine.recreate_swapchain()
                return None

            # Reset the fence only if we're submitting work
            vk.vkResetFences(self.device, 1, [self.in_flight_fences[self.current_frame]])
            
            # Reset command buffer
            vk.vkResetCommandBuffer(self.command_buffers[image_index], 0)

            return image_index
            
        except Exception as e:
            logger.error(f"Failed to begin frame: {e}")
            raise

    def begin_render_pass(self, command_buffer: vk.VkCommandBuffer, image_index: int) -> None:
        """Begin the render pass for the current frame."""
        render_pass_info = vk.VkRenderPassBeginInfo(
            sType=vk.VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO,
            renderPass=self.engine.render_pass.handle,
            framebuffer=self.engine.swapchain.framebuffers[image_index],
            renderArea=vk.VkRect2D(
                offset=vk.VkOffset2D(x=0, y=0),
                extent=self.engine.swapchain.extent
            ),
            clearValueCount=2,
            pClearValues=[
                vk.VkClearValue(color=vk.VkClearColorValue(float32=[0.0, 0.0, 0.0, 1.0])),
                vk.VkClearValue(depthStencil=vk.VkClearDepthStencilValue(depth=1.0, stencil=0))
            ]
        )

        vk.vkCmdBeginRenderPass(
            command_buffer,
            render_pass_info,
            vk.VK_SUBPASS_CONTENTS_INLINE
        )

    def end_render_pass(self, command_buffer: vk.VkCommandBuffer) -> None:
        """End the current render pass."""
        vk.vkCmdEndRenderPass(command_buffer)

    def end_frame(self, image_index: int) -> None:
        """End the current frame and submit it for presentation."""
        try:
            submit_info = vk.VkSubmitInfo(
                sType=vk.VK_STRUCTURE_TYPE_SUBMIT_INFO,
                waitSemaphoreCount=1,
                pWaitSemaphores=[self.image_available_semaphores[self.current_frame]],
                pWaitDstStageMask=[vk.VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT],
                commandBufferCount=1,
                pCommandBuffers=[self.command_buffers[image_index]],
                signalSemaphoreCount=1,
                pSignalSemaphores=[self.render_finished_semaphores[self.current_frame]]
            )

            # Submit command buffer
            vk.vkQueueSubmit(
                self.engine.device.graphics_queue,
                1,
                [submit_info],
                self.in_flight_fences[self.current_frame]
            )

            # Present the frame
            present_info = vk.VkPresentInfoKHR(
                sType=vk.VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,
                waitSemaphoreCount=1,
                pWaitSemaphores=[self.render_finished_semaphores[self.current_frame]],
                swapchainCount=1,
                pSwapchains=[self.engine.swapchain.handle],
                pImageIndices=[image_index]
            )

            try:
                vk.vkQueuePresentKHR(self.engine.device.present_queue, present_info)
            except vk.VkErrorOutOfDateKHR:
                self.engine.recreate_swapchain()

            self.current_frame = (self.current_frame + 1) % self.max_frames_in_flight

        except Exception as e:
            logger.error(f"Failed to end frame: {e}")
            raise

    def begin_single_time_commands(self) -> vk.VkCommandBuffer:
        """Begin single-time command buffer recording."""
        command_buffer = self.command_pools[vk.VK_QUEUE_GRAPHICS_BIT].allocate_buffers(
            vk.VK_COMMAND_BUFFER_LEVEL_PRIMARY,
            1
        )[0]

        begin_info = vk.VkCommandBufferBeginInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
            flags=vk.VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT
        )

        vk.vkBeginCommandBuffer(command_buffer, begin_info)
        return command_buffer

    def end_single_time_commands(self, command_buffer: vk.VkCommandBuffer) -> None:
        """End and submit single-time command buffer."""
        vk.vkEndCommandBuffer(command_buffer)

        submit_info = vk.VkSubmitInfo(
            sType=vk.VK_STRUCTURE_TYPE_SUBMIT_INFO,
            commandBufferCount=1,
            pCommandBuffers=[command_buffer]
        )

        vk.vkQueueSubmit(self.engine.device.graphics_queue, 1, [submit_info], vk.VK_NULL_HANDLE)
        vk.vkQueueWaitIdle(self.engine.device.graphics_queue)

        # Free the command buffer
        vk.vkFreeCommandBuffers(
            self.device,
            self.command_pools[vk.VK_QUEUE_GRAPHICS_BIT].handle,
            1,
            [command_buffer]
        )

    def cleanup(self) -> None:
        """Clean up render manager resources."""
        vk.vkDeviceWaitIdle(self.device)

        # Clean up synchronization objects
        for i in range(self.max_frames_in_flight):
            if self.image_available_semaphores:
                vk.vkDestroySemaphore(self.device, self.image_available_semaphores[i], None)
            if self.render_finished_semaphores:
                vk.vkDestroySemaphore(self.device, self.render_finished_semaphores[i], None)
            if self.in_flight_fences:
                vk.vkDestroyFence(self.device, self.in_flight_fences[i], None)

        # Clean up command pools
        for pool in self.command_pools.values():
            pool.cleanup()

        self.command_pools.clear()
        self.command_buffers.clear()
        logger.info("Render manager cleaned up successfully")