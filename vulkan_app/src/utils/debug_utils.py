import vulkan as vk
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

def _debug_callback(severity: int, message_type: int, callback_data: vk.VkDebugUtilsMessengerCallbackDataEXT, user_data: object) -> bool:
    """Handle debug messages from validation layers."""
    severity_str = {
        vk.VK_DEBUG_UTILS_MESSAGE_SEVERITY_VERBOSE_BIT_EXT: "VERBOSE",
        vk.VK_DEBUG_UTILS_MESSAGE_SEVERITY_INFO_BIT_EXT: "INFO",
        vk.VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT: "WARNING",
        vk.VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT: "ERROR"
    }.get(severity, "UNKNOWN")

    type_str = {
        vk.VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT: "GENERAL",
        vk.VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT: "VALIDATION",
        vk.VK_DEBUG_UTILS_MESSAGE_TYPE_PERFORMANCE_BIT_EXT: "PERFORMANCE"
    }.get(message_type, "UNKNOWN")

    msg = f"[{severity_str}][{type_str}] {callback_data.pMessage}"
    
    if severity >= vk.VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT:
        logger.error(msg)
    elif severity >= vk.VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT:
        logger.warning(msg)
    elif severity >= vk.VK_DEBUG_UTILS_MESSAGE_SEVERITY_INFO_BIT_EXT:
        logger.info(msg)
    else:
        logger.debug(msg)
    
    return False

class ValidationLayers:
    def __init__(self):
        self.enabled_validation_layers = ["VK_LAYER_KHRONOS_validation"]
        self.debug_messenger = None
        self.instance = None

    def check_validation_layer_support(self) -> bool:
        """Check if requested validation layers are available."""
        try:
            available_layers = vk.vkEnumerateInstanceLayerProperties()
            available_layer_names = {layer.layerName for layer in available_layers}
            
            return all(layer in available_layer_names for layer in self.enabled_validation_layers)
        except vk.VkError as e:
            logger.error(f"Failed to enumerate instance layer properties: {e}")
            return False

    def setup_debug_messenger(self, instance: vk.VkInstance) -> None:
        """Set up the debug messenger for validation layers."""
        self.instance = instance
        
        create_info = vk.VkDebugUtilsMessengerCreateInfoEXT(
            sType=vk.VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT,
            messageSeverity=(
                vk.VK_DEBUG_UTILS_MESSAGE_SEVERITY_VERBOSE_BIT_EXT |
                vk.VK_DEBUG_UTILS_MESSAGE_SEVERITY_INFO_BIT_EXT |
                vk.VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT |
                vk.VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT
            ),
            messageType=(
                vk.VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT |
                vk.VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT |
                vk.VK_DEBUG_UTILS_MESSAGE_TYPE_PERFORMANCE_BIT_EXT
            ),
            pfnUserCallback=_debug_callback
        )

        try:
            self.debug_messenger = vk.vkCreateDebugUtilsMessengerEXT(instance, create_info, None)
            logger.info("Debug messenger created successfully")
        except vk.VkError as e:
            logger.error(f"Failed to create debug messenger: {e}")
            raise

    def get_required_extensions(self, base_extensions: List[str]) -> List[str]:
        """Get required instance extensions including debug utils if validation is enabled."""
        extensions = list(base_extensions)
        extensions.append(vk.VK_EXT_DEBUG_UTILS_EXTENSION_NAME)
        return extensions

    def cleanup(self) -> None:
        """Clean up validation layer resources."""
        if self.debug_messenger and self.instance:
            try:
                vk.vkDestroyDebugUtilsMessengerEXT(self.instance, self.debug_messenger, None)
                logger.info("Debug messenger destroyed successfully")
            except vk.VkError as e:
                logger.error(f"Failed to destroy debug messenger: {e}")