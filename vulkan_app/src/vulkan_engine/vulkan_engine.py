import vulkan as vk
import glfw
from vulkan_engine.swapchain import Swapchain
from vulkan_engine.resource_manager import ResourceManager
from vulkan_engine.descriptors import DescriptorSetLayout

class VulkanEngine:
    def __init__(self, window):
        self.window = window
        self.instance, self.enabled_layers = self.create_instance()
        self.device, self.physical_device, self.graphics_queue_family_index = self.create_device()
        self.surface = glfw.create_window_surface(self.instance, window, None, None)
        self.resource_manager = ResourceManager(self)
        self.setup_queues()
        self.swapchain = Swapchain(self, self.resource_manager)
        self.create_descriptor_set_layout()

    def create_instance(self):
        from vulkan_engine.instance import create_instance as create_vk_instance
        return create_vk_instance()

    def create_device(self):
        from vulkan_engine.device import create_device as create_vk_device
        return create_vk_device(self.instance, self.enabled_layers)

    def setup_queues(self):
        self.graphics_queue = vk.vkGetDeviceQueue(self.device, self.graphics_queue_family_index, 0)
        self.present_queue_family_index = self.find_present_queue_family()
        if self.present_queue_family_index is not None:
            self.present_queue = vk.vkGetDeviceQueue(self.device, self.present_queue_family_index, 0)
        else:
            self.present_queue = self.graphics_queue

    def find_present_queue_family(self):
        queue_families = vk.vkGetPhysicalDeviceQueueFamilyProperties(self.physical_device)
        for i, queue_family in enumerate(queue_families):
            if vk.vkGetPhysicalDeviceSurfaceSupportKHR(self.physical_device, i, self.surface):
                return i
        return None

    def recreate_swapchain(self):
        self.swapchain.recreate_swapchain()

    def create_descriptor_set_layout(self):
        bindings = [
            vk.VkDescriptorSetLayoutBinding(
                binding=0,
                descriptorType=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
                descriptorCount=1,
                stageFlags=vk.VK_SHADER_STAGE_VERTEX_BIT,
            )
        ]
        self.descriptor_set_layout = DescriptorSetLayout(self.device, bindings)
        self.resource_manager.add_resource(self.descriptor_set_layout.layout, "descriptor_set_layout", self.resource_manager.destroy_descriptor_set_layout)

    def cleanup(self):
        self.resource_manager.cleanup()
        if self.surface is not None:
            vk.vkDestroySurfaceKHR(self.instance, self.surface, None)
        if self.device is not None:
            vk.vkDestroyDevice(self.device, None)
        if self.instance is not None:
            vk.vkDestroyInstance(self.instance, None)



