import vulkan as vk
import glfw
import logging
from vulkan_engine.swapchain import Swapchain
from vulkan_app.src.resource_manager.resource_manager import ResourceManager
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
        self.physical_device = None
        self.surface = None
        self.swapchain = None
        self.render_pass = None
        self.pipeline_layout = None
        self.graphics_pipeline = None
        self.compute_pipeline = None
        self.resource_manager = None
        self.graphics_queue = None
        self.present_queue = None
        self.graphics_queue_family_index = None
        self.present_queue_family_index = None
        self.descriptor_set_layout = None
        logger.info("Initializing VulkanEngine")
        self.initialize()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup()

    def initialize(self):
        try:
            self.create_instance()
            self.create_surface()
            self.select_physical_device()
            self.create_logical_device()
            self.setup_queues()
            self.resource_manager = ResourceManager(self)
            self.swapchain = Swapchain(self)
            self.create_render_pass()
            self.create_descriptor_set_layout()
            self.create_pipeline_layout()
            self.create_graphics_pipeline()
            self.create_compute_pipeline()
            logger.info("VulkanEngine initialized successfully")
        except vk.VkError as e:
            logger.error(f"Vulkan error during initialization: {str(e)}")
            self.cleanup()
            raise
        except Exception as e:
            logger.error(f"Failed to initialize VulkanEngine: {str(e)}")
            self.cleanup()
            raise

    def create_instance(self):
        app_info = vk.VkApplicationInfo(
            sType=vk.VK_STRUCTURE_TYPE_APPLICATION_INFO,
            pApplicationName="Vulkan App",
            applicationVersion=vk.VK_MAKE_VERSION(1, 0, 0),
            pEngineName="No Engine",
            engineVersion=vk.VK_MAKE_VERSION(1, 0, 0),
            apiVersion=vk.VK_API_VERSION_1_0
        )

        extensions = glfw.get_required_instance_extensions()
        create_info = vk.VkInstanceCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
            pApplicationInfo=app_info,
            enabledExtensionCount=len(extensions),
            ppEnabledExtensionNames=extensions
        )

        try:
            self.instance = vk.vkCreateInstance(create_info, None)
            logger.info("Vulkan instance created successfully")
        except vk.VkError as e:
            logger.error(f"Failed to create Vulkan instance: {str(e)}")
            raise

    def create_surface(self):
        try:
            self.surface = glfw.create_window_surface(self.instance, self.window, None)
            logger.info("Vulkan surface created successfully")
        except Exception as e:
            logger.error(f"Failed to create window surface: {str(e)}")
            raise

    def select_physical_device(self):
        physical_devices = vk.vkEnumeratePhysicalDevices(self.instance)
        if not physical_devices:
            raise RuntimeError("Failed to find GPUs with Vulkan support")

        for device in physical_devices:
            if self.is_device_suitable(device):
                self.physical_device = device
                break

        if self.physical_device is None:
            raise RuntimeError("Failed to find a suitable GPU")

        logger.info("Physical device selected successfully")

    def is_device_suitable(self, device):
        # Implement device suitability checks here
        return True

    def create_logical_device(self):
        indices = self.find_queue_families(self.physical_device)

        unique_queue_families = set([indices.graphics_family, indices.present_family])
        queue_create_infos = []
        for queue_family in unique_queue_families:
            queue_create_info = vk.VkDeviceQueueCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
                queueFamilyIndex=queue_family,
                queueCount=1,
                pQueuePriorities=[1.0]
            )
            queue_create_infos.append(queue_create_info)

        device_features = vk.VkPhysicalDeviceFeatures()
        create_info = vk.VkDeviceCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
            pQueueCreateInfos=queue_create_infos,
            queueCreateInfoCount=len(queue_create_infos),
            pEnabledFeatures=device_features,
            enabledExtensionCount=0
        )

        try:
            self.device = vk.vkCreateDevice(self.physical_device, create_info, None)
            logger.info("Logical device created successfully")
        except vk.VkError as e:
            logger.error(f"Failed to create logical device: {str(e)}")
            raise

    def find_queue_families(self, device):
        # Implement queue family selection logic here
        pass

    def setup_queues(self):
        queue_family_properties = vk.vkGetPhysicalDeviceQueueFamilyProperties(self.physical_device)
        
        for i, properties in enumerate(queue_family_properties):
            if properties.queueFlags & vk.VK_QUEUE_GRAPHICS_BIT:
                self.graphics_queue_family_index = i
                self.graphics_queue = vk.vkGetDeviceQueue(self.device, i, 0)
                break

        for i, properties in enumerate(queue_family_properties):
            if vk.vkGetPhysicalDeviceSurfaceSupportKHR(self.physical_device, i, self.surface):
                self.present_queue_family_index = i
                self.present_queue = vk.vkGetDeviceQueue(self.device, i, 0)
                break

        if self.graphics_queue is None or self.present_queue is None:
            raise RuntimeError("Failed to find suitable queue families")

        logger.info("Queues set up successfully")

    def create_render_pass(self):
        color_attachment = vk.VkAttachmentDescription(
            format=self.swapchain.image_format,
            samples=vk.VK_SAMPLE_COUNT_1_BIT,
            loadOp=vk.VK_ATTACHMENT_LOAD_OP_CLEAR,
            storeOp=vk.VK_ATTACHMENT_STORE_OP_STORE,
            stencilLoadOp=vk.VK_ATTACHMENT_LOAD_OP_DONT_CARE,
            stencilStoreOp=vk.VK_ATTACHMENT_STORE_OP_DONT_CARE,
            initialLayout=vk.VK_IMAGE_LAYOUT_UNDEFINED,
            finalLayout=vk.VK_IMAGE_LAYOUT_PRESENT_SRC_KHR
        )

        color_attachment_ref = vk.VkAttachmentReference(
            attachment=0,
            layout=vk.VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL
        )

        subpass = vk.VkSubpassDescription(
            pipelineBindPoint=vk.VK_PIPELINE_BIND_POINT_GRAPHICS,
            colorAttachmentCount=1,
            pColorAttachments=[color_attachment_ref]
        )

        render_pass_info = vk.VkRenderPassCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO,
            attachmentCount=1,
            pAttachments=[color_attachment],
            subpassCount=1,
            pSubpasses=[subpass]
        )

        try:
            self.render_pass = vk.vkCreateRenderPass(self.device, render_pass_info, None)
            logger.info("Render pass created successfully")
        except vk.VkError as e:
            logger.error(f"Failed to create render pass: {str(e)}")
            raise

    def create_pipeline_layout(self):
        layout_info = vk.VkPipelineLayoutCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
            setLayoutCount=0,
            pushConstantRangeCount=0
        )

        try:
            self.pipeline_layout = vk.vkCreatePipelineLayout(self.device, layout_info, None)
            logger.info("Pipeline layout created successfully")
        except vk.VkError as e:
            logger.error(f"Failed to create pipeline layout: {str(e)}")
            raise

    def create_graphics_pipeline(self):
        # Implement graphics pipeline creation here
        pass

    def create_compute_pipeline(self):
        # Implement compute pipeline creation here
        pass

    def cleanup(self):
        logger.info("Cleaning up VulkanEngine resources")
        if self.resource_manager:
            self.resource_manager.cleanup()
        if self.swapchain:
            self.swapchain.cleanup()
        if self.pipeline_layout:
            vk.vkDestroyPipelineLayout(self.device, self.pipeline_layout, None)
        if self.render_pass:
            vk.vkDestroyRenderPass(self.device, self.render_pass, None)
        if self.surface:
            vk.vkDestroySurfaceKHR(self.instance, self.surface, None)
        if self.device:
            vk.vkDestroyDevice(self.device, None)
        if self.instance:
            vk.vkDestroyInstance(self.instance, None)
        logger.info("VulkanEngine cleanup completed")

    def recreate_swapchain(self):
        vk.vkDeviceWaitIdle(self.device)
        self.swapchain.recreate()
        self.create_render_pass()
        self.create_pipeline_layout()
        self.create_graphics_pipeline()
        self.create_compute_pipeline()

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
        vk.vkDeviceWaitIdle(self.device)
        self.swapchain.cleanup()
        self.swapchain = Swapchain(self)
        self.create_render_pass()
        self.create_descriptor_set_layout()
        self.create_pipeline_layout()
        self.create_graphics_pipeline()
        self.create_compute_pipeline()
        self.render_manager.recreate_command_buffers()

    def create_descriptor_set_layout(self):
        bindings = [
            vk.VkDescriptorSetLayoutBinding(
                binding=0,
                descriptorType=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
                descriptorCount=1,
                stageFlags=vk.VK_SHADER_STAGE_VERTEX_BIT,
            ),
            vk.VkDescriptorSetLayoutBinding(
                binding=1,
                descriptorType=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
                descriptorCount=1,
                stageFlags=vk.VK_SHADER_STAGE_FRAGMENT_BIT,
            )
        ]
        self.descriptor_set_layout = self.resource_manager.create_descriptor_set_layout(bindings)

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


