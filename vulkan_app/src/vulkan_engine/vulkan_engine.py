import vulkan as vk
import glfw

class VulkanEngine:
    def __init__(self, window):
        self.window = window

        # Instance creation
        self.instance, self.enabled_layers = self.create_instance()

        # Device creation
        self.device, self.physical_device, self.graphics_queue_family_index = self.create_device()

        # Surface creation
        self.surface = glfw.create_window_surface(self.instance, window, None, None)

        # Resource manager
        from vulkan_engine.resource_manager import ResourceManager
        self.resource_manager = ResourceManager(self)

        # Find graphics and present queues
        self.graphics_queue = vk.vkGetDeviceQueue(self.device, self.graphics_queue_family_index, 0)
        self.present_queue_family_index = self.find_present_queue_family()
        if self.present_queue_family_index is not None:
            self.present_queue = vk.vkGetDeviceQueue(self.device, self.present_queue_family_index, 0)
        else:
            self.present_queue = self.graphics_queue  # Use graphics queue for present if no dedicated present queue

    def create_instance(self):
        from vulkan_engine.instance import create_instance as create_vk_instance
        return create_vk_instance()

    def create_device(self):
        from vulkan_engine.device import create_device as create_vk_device
        return create_vk_device(self.instance, self.enabled_layers)

    def find_present_queue_family(self):
        queue_families = vk.vkGetPhysicalDeviceQueueFamilyProperties(self.physical_device)
        for i, queue_family in enumerate(queue_families):
            if vk.vkGetPhysicalDeviceSurfaceSupportKHR(self.physical_device, i, self.surface):
                return i
        return None

    def cleanup(self):
        self.resource_manager.cleanup()

