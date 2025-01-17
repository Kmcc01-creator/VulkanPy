import vulkan as vk
import glfw

class VulkanRenderer:
    def __init__(self, window):
        from vulkan_engine.vulkan_engine import VulkanEngine
        from vulkan_renderer.render_manager import RenderManager
        self.window = window
        self.vulkan_engine = VulkanEngine(window)
        self.render_manager = RenderManager(self.vulkan_engine)

        # Swapchain creation
        from vulkan_engine.swapchain import Swapchain

        self.swapchain = Swapchain(self.vulkan_engine, self.vulkan_engine.resource_manager) # Pass vulkan_engine instead of self
        self.framebuffers = self.swapchain.framebuffers
        self.current_frame = 0

        glfw.set_framebuffer_size_callback(self.window, self.framebuffer_resize_callback)

    def framebuffer_resize_callback(self, window, width, height):
        self.recreate_swapchain()

    def recreate_swapchain(self):
        vk.vkDeviceWaitIdle(self.vulkan_engine.device) # Wait for device to be idle before destroying resources

        width = int(glfw.get_framebuffer_size(self.window)[0]) # Define width
        height = int(glfw.get_framebuffer_size(self.window)[1])
        while width == 0 or height == 0: # Handle window minimization
            width = int(glfw.get_framebuffer_size(self.window)[0])
            height = int(glfw.get_framebuffer_size(self.window)[1])
            glfw.wait_events()

        self.swapchain.recreate_swapchain()
        self.framebuffers = self.swapchain.framebuffers # Update framebuffers after swapchain recreation
        self.render_manager.create_command_buffers(self.framebuffers) # Recreate command buffers

    def cleanup(self):
        vk.vkDeviceWaitIdle(self.vulkan_engine.device) # Wait for device to be idle before destroying resources
        self.render_manager.cleanup()
        self.swapchain.cleanup()
        self.vulkan_engine.cleanup()
