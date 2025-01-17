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


    def render(self):
        # Acquire next image from swapchain
        # Record command buffer
        # Submit command buffer to graphics queue
        # Present image to screen
        pass  # Placeholder for rendering logic

    def cleanup(self):
        for fence in self.in_flight_fences:
            vk.vkWaitForFences(self.device, 1, [fence], vk.VK_TRUE, 1000000000)
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
        for fence in self.in_flight_fences:
            vk.vkWaitForFences(self.device, 1, [fence], vk.VK_TRUE, 1000000000) # Wait for fence before destroying it
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
