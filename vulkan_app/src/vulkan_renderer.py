import vulkan as vk
import glfw

from src.ecs.world import World
from src.ecs.systems import RenderSystem
from src.ecs.components import Transform, Mesh, Material
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
        from src.vertex import Vertex
        vertices = [
            Vertex(np.array([-0.5, -0.5, 0.0]), np.array([1.0, 0.0, 0.0])),
            Vertex(np.array([0.5, -0.5, 0.0]), np.array([0.0, 1.0, 0.0])),
            Vertex(np.array([0.0, 0.5, 0.0]), np.array([0.0, 0.0, 1.0])),
        ]
        mesh = Mesh(vertices=vertices, indices=[])
        mesh.create_vertex_buffer(self) # Pass renderer to create_vertex_buffer
        self.world.add_component(entity, mesh) # Now with vertices
        self.world.add_component(entity, Material(color=np.array([1.0, 0.0, 0.0])))


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
        self.current_frame = 0
        self.render_system.init_rendering(self) # Initialize rendering resources
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
        width = int(glfw.get_framebuffer_size(self.window)[0])
        height = int(glfw.get_framebuffer_size(self.window)[1])
        while width == 0 or height == 0: # Handle window minimization
            width = int(glfw.get_framebuffer_size(self.window)[0])
            height = int(glfw.get_framebuffer_size(self.window)[1])
            glfw.wait_events()

        vk.vkDeviceWaitIdle(self.device)

        # Destroy old swapchain and related resources
        for framebuffer in self.framebuffers:
            vk.vkDestroyFramebuffer(self.device, framebuffer, None)
        vk.vkDestroySwapchainKHR(self.device, self.swapchain, None)

        # Recreate swapchain and related resources
        self.swapchain, self.swapchain_extent = self.create_swapchain()
        self.create_uniform_buffers() # Recreate uniform buffers
        self.create_descriptor_pool()
        self.create_descriptor_sets()
        self.framebuffers = self.create_framebuffers()
        self.pipeline, self.pipeline_layout, self.descriptor_set_layout = self.create_pipeline() # Recreate pipeline, layout, and descriptor set layout

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

    def create_descriptor_pool(self):
        from vulkan_engine.descriptors import create_descriptor_pool as create_vk_descriptor_pool
        self.descriptor_pool = create_vk_descriptor_pool(self.device, self.descriptor_set_layout.layout) # Access layout attribute

    def create_uniform_buffers(self):
        from vulkan_engine.descriptors import create_uniform_buffers as create_vk_uniform_buffers
        self.uniform_buffers = create_vk_uniform_buffers(self, len(self.swapchain_images))

        pool_sizes = []
        pool_sizes.append(vk.VkDescriptorPoolSize(type=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, descriptorCount=1))

        pool_create_info = vk.VkDescriptorPoolCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
            maxSets=1,
            poolSizeCount=len(pool_sizes),
            pPoolSizes=pool_sizes
        )

        self.descriptor_pool = vk.vkCreateDescriptorPool(self.device, pool_create_info, None)


    def create_descriptor_sets(self):
        layout_info = vk.VkDescriptorSetAllocateInfo(
            sType=vk.VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
            descriptorPool=self.descriptor_pool,
            descriptorSetCount=1,
            pSetLayouts=[self.descriptor_set_layout],
        )
        self.descriptor_sets = vk.vkAllocateDescriptorSets(self.device, layout_info)

        buffer_info = vk.VkDescriptorBufferInfo(
                buffer=uniform_buffer.buffer,
            offset=0,
            range=4 * 4 * 4, # Size of mat4
        )

        write_descriptor_sets = []
        for i, uniform_buffer in enumerate(self.uniform_buffers):
            buffer_info = vk.VkDescriptorBufferInfo(
                buffer=uniform_buffer.buffer,
                offset=0,
                range=uniform_buffer.size,
            )
                write_descriptor_sets.append(vk.VkWriteDescriptorSet(
                sType=vk.VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
                dstSet=self.descriptor_sets[i],
            dstBinding=0,
            dstArrayElement=0,
            descriptorCount=1,
            descriptorType=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
            pBufferInfo=[buffer_info],
        ))



    def copy_buffer(self, src_buffer, dst_buffer, size): # Helper function remains unchanged
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
        copy_region = vk.VkBufferCopy(srcOffset=0, dstOffset=0, size=size)
        vk.vkCmdCopyBuffer(command_buffer, src_buffer, dst_buffer, 1, [copy_region])


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
        if self.swapchain is not None: # Check for None before destroying
            vk.vkDestroySwapchainKHR(self.device, self.swapchain, None)
        if self.surface is not None: # Check for None before destroying
            vk.vkDestroySurfaceKHR(self.instance, self.surface, None)
        if self.device is not None: # Check for None before destroying
            vk.vkDestroyDevice(self.device, None)
        if self.instance is not None: # Check for None before destroying
            vk.vkDestroyInstance(self.instance, None)
