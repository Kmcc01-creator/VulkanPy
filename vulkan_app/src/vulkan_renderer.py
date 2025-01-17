import vulkan as vk
import glfw

class VulkanRenderer:
    def __init__(self, window):
        self.window = window

        # Vulkan Instance creation
        self.instance = self.create_instance()

        # Vulkan Device creation
        self.device, self.physical_device, self.graphics_queue_family_index = self.create_device()

        # Create window surface
        self.surface = glfw.create_window_surface(self.instance, window, None, None)

        # Swapchain creation (requires window surface)
        self.swapchain = self.create_swapchain()

    def create_instance(self):
        from vulkan_engine.instance import create_instance as create_vk_instance
        return create_vk_instance()

    def create_device(self):
        from vulkan_engine.device import create_device as create_vk_device
        return create_vk_device(self.instance)

    def create_swapchain(self):
        from vulkan_engine.swapchain import create_swapchain as create_vk_swapchain
        return create_vk_swapchain(self.instance, self.device, self.physical_device, self.surface, self.graphics_queue_family_index, self.graphics_queue_family_index) # Using graphics queue for present for now


    def render(self):
        pass  # ... Rendering commands ...

    def cleanup(self):
        vk.vkDestroySwapchainKHR(self.device, self.swapchain, None)
        vk.vkDestroySurfaceKHR(self.instance, self.surface, None)
        vk.vkDestroyDevice(self.device, None)
        vk.vkDestroyInstance(self.instance, None)
