import vulkan as vk
import glfw

class VulkanRenderer:
    def __init__(self, window):
        from vulkan_engine.vulkan_engine import VulkanEngine
        from vulkan_renderer.render_manager import RenderManager
        self.window = window
        self.vulkan_engine = VulkanEngine(window)
        self.render_manager = RenderManager(self.vulkan_engine)
        from vulkan_engine.descriptors import create_uniform_buffers

        self.uniform_buffers = create_uniform_buffers(self.vulkan_engine.resource_manager, self.vulkan_engine.swapchain.image_count) # Create uniform buffers

        # Swapchain creation
        from vulkan_engine.swapchain import Swapchain

        self.swapchain = Swapchain(self, self.vulkan_engine.resource_manager) # Pass vulkan_engine instead of self
        self.framebuffers = self.swapchain.framebuffers
        self.current_frame = 0

    def cleanup(self):
        vk.vkDeviceWaitIdle(self.vulkan_engine.device)
        self.render_manager.cleanup()
        self.swapchain.cleanup()
        self.vulkan_engine.cleanup()
        glfw.destroy_window(self.window) # Destroy GLFW window
        glfw.terminate()
