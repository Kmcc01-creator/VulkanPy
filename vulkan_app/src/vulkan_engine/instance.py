import vulkan as vk
import glfw
import logging
from typing import Tuple, List
from .debug_utils import ValidationLayers

logger = logging.getLogger(__name__)

class VulkanInstance:
    def __init__(self, app_name: str, engine_name: str = "No Engine"):
        self.instance = None
        self.validation = ValidationLayers()
        self.app_name = app_name
        self.engine_name = engine_name

    def create_instance(self) -> None:
        """Create the Vulkan instance with validation layers if enabled."""
        if self.validation.enabled_validation_layers and not self.validation.check_validation_layer_support():
            raise RuntimeError("Validation layers requested but not available!")

        app_info = vk.VkApplicationInfo(
            sType=vk.VK_STRUCTURE_TYPE_APPLICATION_INFO,
            pApplicationName=self.app_name,
            applicationVersion=vk.VK_MAKE_VERSION(1, 0, 0),
            pEngineName=self.engine_name,
            engineVersion=vk.VK_MAKE_VERSION(1, 0, 0),
            apiVersion=vk.VK_API_VERSION_1_2
        )

        extensions = self._get_required_extensions()
        
        create_info = vk.VkInstanceCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
            pApplicationInfo=app_info,
            enabledExtensionCount=len(extensions),
            ppEnabledExtensionNames=extensions,
            enabledLayerCount=len(self.validation.enabled_validation_layers),
            ppEnabledLayerNames=self.validation.enabled_validation_layers if self.validation.enabled_validation_layers else None
        )

        try:
            self.instance = vk.vkCreateInstance(create_info, None)
            logger.info("Vulkan instance created successfully")
            
            if self.validation.enabled_validation_layers:
                self.validation.setup_debug_messenger(self.instance)
                
        except vk.VkError as e:
            logger.error(f"Failed to create Vulkan instance: {e}")
            raise

    def _get_required_extensions(self) -> List[str]:
        """Get required instance extensions."""
        glfw_extensions = glfw.get_required_instance_extensions()
        return self.validation.get_required_extensions(glfw_extensions)

    def cleanup(self) -> None:
        """Clean up instance resources."""
        if self.validation:
            self.validation.cleanup()
        
        if self.instance:
            try:
                vk.vkDestroyInstance(self.instance, None)
                logger.info("Vulkan instance destroyed successfully")
            except vk.VkError as e:
                logger.error(f"Failed to destroy Vulkan instance: {e}")