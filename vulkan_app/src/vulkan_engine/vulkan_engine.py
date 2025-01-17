import vulkan as vk
import glfw
import logging
from vulkan_engine.swapchain import Swapchain
from vulkan_engine.resource_manager import ResourceManager
from vulkan_engine.descriptors import DescriptorSetLayout
from utils.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

class VulkanEngine:
    def __init__(self, window):
        self.window = window
        logger.info("Initializing VulkanEngine")
        try:
            self.instance, self.enabled_layers = self.create_instance()
            self.device, self.physical_device, self.graphics_queue_family_index = self.create_device()
            self.surface = glfw.create_window_surface(self.instance, window, None, None)
            self.resource_manager = ResourceManager(self)
            self.setup_queues()
            self.swapchain = Swapchain(self, self.resource_manager)
            self.create_descriptor_set_layout()
            logger.info("VulkanEngine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize VulkanEngine: {str(e)}")
            raise

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

    def copy_buffer(self, src_buffer, dst_buffer, size):
        command_buffer = self.resource_manager.begin_single_time_commands()

        copy_region = vk.VkBufferCopy(srcOffset=0, dstOffset=0, size=size)
        vk.vkCmdCopyBuffer(command_buffer, src_buffer, dst_buffer, 1, [copy_region])

        self.resource_manager.end_single_time_commands(command_buffer)



