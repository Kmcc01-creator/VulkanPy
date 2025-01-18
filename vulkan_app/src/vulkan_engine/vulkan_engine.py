import vulkan as vk
import glfw
import logging
from vulkan_engine.swapchain import Swapchain
from vulkan_engine.resource_manager import ResourceManager
from vulkan_engine.descriptors import DescriptorSetLayout
from vulkan_engine.pipeline import Pipeline
from utils.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

class VulkanEngine:
    def __init__(self, window):
        self.window = window
        self.instance = None
        self.device = None
        self.surface = None
        self.resource_manager = None
        self.swapchain = None
        self.descriptor_set_layout = None
        self.pipeline = None
        self.graphics_pipeline = None
        self.compute_pipeline = None
        logger.info("Initializing VulkanEngine")
        self.initialize()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup()

    def initialize(self):
        try:
            self.resource_manager = ResourceManager(self)
            self.instance, self.enabled_layers = self.resource_manager.create_instance()
            self.device, self.physical_device, self.graphics_queue_family_index = self.resource_manager.create_device(self.instance, self.enabled_layers)
            self.surface = self.create_surface()
            self.setup_queues()
            self.swapchain = Swapchain(self, self.resource_manager)
            self.create_descriptor_set_layout()
            self.resource_manager.descriptor_pool = self.resource_manager.create_descriptor_pool(len(self.swapchain.swapchain_images), self.descriptor_set_layout)
            self.pipeline = Pipeline(self.resource_manager)
            self.create_pipelines()
            logger.info("VulkanEngine initialized successfully")
        except vk.VkError as e:
            logger.error(f"Vulkan error during initialization: {str(e)}")
            self.cleanup()
            raise
        except Exception as e:
            logger.error(f"Failed to initialize VulkanEngine: {str(e)}")
            self.cleanup()
            raise

    def create_pipelines(self):
        try:
            self.graphics_pipeline, self.pipeline_layout, _ = self.pipeline.create_graphics_pipeline(
                self.swapchain.swapchain_extent,
                self.swapchain.render_pass
            )
            self.compute_pipeline, _ = self.pipeline.create_compute_pipeline(
                "vulkan_app/shaders/compute.spv",
                self.descriptor_set_layout
            )
            logger.info("Pipelines created successfully")
        except Exception as e:
            logger.error(f"Failed to create pipelines: {str(e)}")
            raise

    def create_surface(self):
        try:
            return glfw.create_window_surface(self.instance, self.window, None, None)
        except Exception as e:
            logger.error(f"Failed to create window surface: {str(e)}")
            raise
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
        self.resource_manager.add_resource(self.descriptor_set_layout, "descriptor_set_layout")

    def cleanup(self):
        logger.info("Cleaning up VulkanEngine resources")
        if self.resource_manager:
            self.resource_manager.cleanup()
        if self.swapchain:
            self.swapchain.cleanup()
        if self.surface:
            vk.vkDestroySurfaceKHR(self.instance, self.surface, None)
            self.surface = None
        if self.device:
            vk.vkDestroyDevice(self.device, None)
            self.device = None
        if self.instance:
            vk.vkDestroyInstance(self.instance, None)
            self.instance = None
        logger.info("VulkanEngine cleanup completed")

    def copy_buffer(self, src_buffer, dst_buffer, size):
        self.resource_manager.copy_buffer(src_buffer, dst_buffer, size)


