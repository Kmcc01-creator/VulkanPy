import vulkan as vk
import glfw

from src.ecs.world import World
from src.ecs.systems import RenderSystem
from src.ecs.components import Transform, Mesh, Material
from vulkan_engine.resource_manager import ResourceManager # Importing ResourceManager
import numpy as np

class VulkanRenderer:
    def __init__(self, window):
        self.window = window
        self.world = World()
        self.render_system = RenderSystem(self)
        self.world.add_system(self.render_system)

        # Test entity
        entity = self.world.create_entity()
        self.world.add_component(entity, Transform(position=np.array([0.0, 0.0, 0.0]), rotation=np.array([0.0, 0.0, 0.0]), scale=np.array([1.0, 1.0, 1.0])))

        mesh = Mesh(vertices=[], indices=[]) # Initialize empty mesh
        mesh.create_vertex_buffer(self, "vulkan_app/models/triangle.obj") # Load from file
        self.world.add_component(entity, mesh) # Now with vertices
        self.world.add_component(entity, Material(color=np.array([1.0, 0.0, 0.0])))


        # Vulkan Instance creation
        self.instance, self.enabled_layers = self.create_instance()

        # Vulkan Device creation
        self.device, self.physical_device, self.graphics_queue_family_index = self.create_device()

        # Create window surface
        self.surface = glfw.create_window_surface(self.instance, window, None, None)

        # Swapchain creation (requires window surface)
        from vulkan_engine.swapchain import Swapchain
        self.resource_manager = ResourceManager(self)
        self.swapchain = Swapchain(self, self.resource_manager)
        self.swapchain_extent = self.swapchain.extent # Access extent from Swapchain object
        self.render_pass = self.swapchain.render_pass # Access render_pass from Swapchain object
        self.pipeline = self.swapchain.pipeline # Access pipeline from Swapchain object
        self.pipeline_layout = self.swapchain.pipeline_layout # Access pipeline_layout from Swapchain object
        self.framebuffers = self.swapchain.framebuffers # Access framebuffers from Swapchain object
        self.create_command_pool() # New: create command pool

        self.current_frame = 0
        self.render_manager.init_rendering(self) # Initialize rendering resources
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

        from vulkan_engine.synchronization import create_sync_objects as create_vk_sync_objects
        self.image_available_semaphores, self.render_finished_semaphores, self.in_flight_fences = create_vk_sync_objects(self.device, len(self.swapchain.swapchain_images), self.resource_manager)

    def recreate_swapchain(self):
        vk.vkDeviceWaitIdle(self.device) # Wait for device to be idle

        width = int(glfw.get_framebuffer_size(self.window)[0]) # Define width
        height = int(glfw.get_framebuffer_size(self.window)[1])
        while width == 0 or height == 0: # Handle window minimization
            width = int(glfw.get_framebuffer_size(self.window)[0])
            height = int(glfw.get_framebuffer_size(self.window)[1])
            glfw.wait_events()

        vk.vkDeviceWaitIdle(self.device)

        self.swapchain.recreate_swapchain()

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
        vk.vkCmdBindDescriptorSets(command_buffer, vk.VK_PIPELINE_BIND_POINT_GRAPHICS, self.pipeline_layout, 0, 1, self.descriptor_sets, 0, None)

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

        self.render_system.render(command_buffer, self.world) # Delegate rendering to RenderSystem
        vk.vkCmdEndRenderPass(command_buffer)

        try:
            vk.vkEndCommandBuffer(command_buffer)
        except vk.VkError as e:
            raise Exception(f"Failed to end recording command buffer: {e}")

        pool_sizes = []
        pool_sizes.append(vk.VkDescriptorPoolSize(type=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, descriptorCount=1))

        pool_create_info = vk.VkDescriptorPoolCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
            maxSets=1,
            poolSizeCount=len(pool_sizes),
            pPoolSizes=pool_sizes
        )

        self.descriptor_pool = vk.vkCreateDescriptorPool(self.device, pool_create_info, None)



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
    def copy_buffer(self, src_buffer, dst_buffer, size):
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

        copy_region = vk.VkBufferCopy(srcOffset=0, dstOffset=0, size=size)
        vk.vkCmdCopyBuffer(command_buffer, src_buffer, dst_buffer, 1, [copy_region])

        vk.vkEndCommandBuffer(command_buffer)

        submit_info = vk.VkSubmitInfo(
            sType=vk.VK_STRUCTURE_TYPE_SUBMIT_INFO,
            commandBufferCount=1,
            pCommandBuffers=[command_buffer],
        )
        vk.vkQueueSubmit(self.graphics_queue, 1, [submit_info], vk.VK_NULL_HANDLE)
        vk.vkQueueWaitIdle(self.graphics_queue)

        vk.vkFreeCommandBuffers(self.device, self.command_pool, 1, [command_buffer])


        vk.vkEndCommandBuffer(command_buffer)

        submit_info = vk.VkSubmitInfo(
            sType=vk.VK_STRUCTURE_TYPE_SUBMIT_INFO,
            commandBufferCount=1,
            pCommandBuffers=[command_buffer],
        )
        vk.vkQueueSubmit(self.graphics_queue, 1, [submit_info], vk.VK_NULL_HANDLE)
        vk.vkQueueWaitIdle(self.graphics_queue)

        vk.vkFreeCommandBuffers(self.device, self.command_pool, 1, [command_buffer])

        for fence in self.in_flight_fences:
            vk.vkWaitForFences(self.device, 1, [fence], vk.VK_TRUE, 1000000000) # Wait for fence before destroying it
            vk.vkDestroyFence(self.device, fence, None)

        for semaphore in self.image_available_semaphores:
            vk.vkDestroySemaphore(self.device, semaphore, None)

        for semaphore in self.render_finished_semaphores:
            vk.vkDestroySemaphore(self.device, semaphore, None)


    def cleanup(self):
        self.resource_manager.cleanup() # Cleanup resources

        if self.surface is not None:
            vk.vkDestroySurfaceKHR(self.instance, self.surface, None)
        if self.device is not None:
            vk.vkDestroyDevice(self.device, None)
        if self.instance is not None:
            vk.vkDestroyInstance(self.instance, None)
