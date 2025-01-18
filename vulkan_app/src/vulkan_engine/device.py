import vulkan as vk
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict

logger = logging.getLogger(__name__)

@dataclass
class QueueFamilyIndices:
    graphics_family: Optional[int] = None
    present_family: Optional[int] = None
    compute_family: Optional[int] = None
    
    def is_complete(self) -> bool:
        return (self.graphics_family is not None and 
                self.present_family is not None and 
                self.compute_family is not None)

class VulkanDevice:
    def __init__(self, instance: vk.VkInstance, surface: vk.VkSurfaceKHR, validation_layers: List[str]):
        self.instance = instance
        self.surface = surface
        self.validation_layers = validation_layers
        
        # Device handles
        self.physical_device: Optional[vk.VkPhysicalDevice] = None
        self.device: Optional[vk.VkDevice] = None
        
        # Queues
        self.graphics_queue: Optional[vk.VkQueue] = None
        self.present_queue: Optional[vk.VkQueue] = None
        self.compute_queue: Optional[vk.VkQueue] = None
        
        # Queue family indices
        self.queue_family_indices: Optional[QueueFamilyIndices] = None
        
        # Device features and properties
        self.device_features: Optional[vk.VkPhysicalDeviceFeatures] = None
        self.device_properties: Optional[vk.VkPhysicalDeviceProperties] = None
        
        # Required device extensions
        self.device_extensions = [
            vk.VK_KHR_SWAPCHAIN_EXTENSION_NAME
        ]

    def pick_physical_device(self) -> None:
        """Select the most suitable physical device (GPU)."""
        devices = vk.vkEnumeratePhysicalDevices(self.instance)
        if not devices:
            raise RuntimeError("Failed to find GPUs with Vulkan support")

        # Score and rank available devices
        device_ratings: Dict[vk.VkPhysicalDevice, int] = {}
        for device in devices:
            score = self._rate_physical_device(device)
            device_ratings[device] = score

        # Select the highest rated device
        selected_device = max(device_ratings.items(), key=lambda x: x[1])[0]
        if device_ratings[selected_device] <= 0:
            raise RuntimeError("Failed to find a suitable GPU")

        self.physical_device = selected_device
        self.device_properties = vk.vkGetPhysicalDeviceProperties(self.physical_device)
        self.device_features = vk.vkGetPhysicalDeviceFeatures(self.physical_device)
        
        logger.info(f"Selected physical device: {self.device_properties.deviceName}")

    def _rate_physical_device(self, device: vk.VkPhysicalDevice) -> int:
        """Rate the suitability of a physical device."""
        properties = vk.vkGetPhysicalDeviceProperties(device)
        features = vk.vkGetPhysicalDeviceFeatures(device)
        
        score = 0

        # Prefer discrete GPUs
        if properties.deviceType == vk.VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU:
            score += 1000

        # Add score for max image dimension
        score += properties.limits.maxImageDimension2D

        # Check required features
        if not features.geometryShader:
            return 0
        
        # Check queue family support
        indices = self._find_queue_families(device)
        if not indices.is_complete():
            return 0

        # Check extension support
        if not self._check_device_extension_support(device):
            return 0

        # Check swapchain support
        try:
            swapchain_support = self._query_swapchain_support(device)
            if not swapchain_support.formats or not swapchain_support.present_modes:
                return 0
        except Exception:
            return 0

        return score

    def create_logical_device(self) -> None:
        """Create the logical device and initialize queues."""
        self.pick_physical_device()
        self.queue_family_indices = self._find_queue_families(self.physical_device)

        # Create list of unique queue families needed
        queue_create_infos = []
        queue_families = set([
            self.queue_family_indices.graphics_family,
            self.queue_family_indices.present_family,
            self.queue_family_indices.compute_family
        ])

        queue_priority = float(1.0)
        for queue_family in queue_families:
            queue_create_info = vk.VkDeviceQueueCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
                queueFamilyIndex=queue_family,
                queueCount=1,
                pQueuePriorities=[queue_priority]
            )
            queue_create_infos.append(queue_create_info)

        # Specify device features
        device_features = vk.VkPhysicalDeviceFeatures()
        device_features.samplerAnisotropy = vk.VK_TRUE
        device_features.sampleRateShading = vk.VK_TRUE

        # Create the logical device
        create_info = vk.VkDeviceCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
            pQueueCreateInfos=queue_create_infos,
            queueCreateInfoCount=len(queue_create_infos),
            pEnabledFeatures=device_features,
            enabledExtensionCount=len(self.device_extensions),
            ppEnabledExtensionNames=self.device_extensions,
            enabledLayerCount=len(self.validation_layers),
            ppEnabledLayerNames=self.validation_layers
        )

        try:
            self.device = vk.vkCreateDevice(self.physical_device, create_info, None)
            logger.info("Logical device created successfully")

            # Get queue handles
            self.graphics_queue = vk.vkGetDeviceQueue(
                self.device,
                self.queue_family_indices.graphics_family,
                0
            )
            self.present_queue = vk.vkGetDeviceQueue(
                self.device,
                self.queue_family_indices.present_family,
                0
            )
            self.compute_queue = vk.vkGetDeviceQueue(
                self.device,
                self.queue_family_indices.compute_family,
                0
            )
            
        except vk.VkError as e:
            logger.error(f"Failed to create logical device: {e}")
            raise

    def _find_queue_families(self, device: vk.VkPhysicalDevice) -> QueueFamilyIndices:
        """Find all required queue families."""
        indices = QueueFamilyIndices()
        
        queue_families = vk.vkGetPhysicalDeviceQueueFamilyProperties(device)
        
        for i, queue_family in enumerate(queue_families):
            # Check for graphics support
            if queue_family.queueFlags & vk.VK_QUEUE_GRAPHICS_BIT:
                indices.graphics_family = i
                
            # Check for compute support
            if queue_family.queueFlags & vk.VK_QUEUE_COMPUTE_BIT:
                indices.compute_family = i
                
            # Check for present support
            if vk.vkGetPhysicalDeviceSurfaceSupportKHR(device, i, self.surface):
                indices.present_family = i
                
            if indices.is_complete():
                break
                
        return indices

    def _check_device_extension_support(self, device: vk.VkPhysicalDevice) -> bool:
        """Check if the device supports all required extensions."""
        available_extensions = vk.vkEnumerateDeviceExtensionProperties(device, None)
        available_extension_names = {ext.extensionName for ext in available_extensions}
        
        return all(ext in available_extension_names for ext in self.device_extensions)

    def _query_swapchain_support(self, device: vk.VkPhysicalDevice) -> 'SwapChainSupportDetails':
        """Query swapchain support details."""
        support_details = SwapChainSupportDetails()
        
        support_details.capabilities = vk.vkGetPhysicalDeviceSurfaceCapabilitiesKHR(
            device, self.surface)
        support_details.formats = vk.vkGetPhysicalDeviceSurfaceFormatsKHR(
            device, self.surface)
        support_details.present_modes = vk.vkGetPhysicalDeviceSurfacePresentModesKHR(
            device, self.surface)
            
        return support_details

    def wait_idle(self) -> None:
        """Wait for the device to finish all operations."""
        vk.vkDeviceWaitIdle(self.device)

    def cleanup(self) -> None:
        """Clean up the logical device."""
        if self.device:
            vk.vkDestroyDevice(self.device, None)
            self.device = None
            logger.info("Logical device destroyed")

@dataclass
class SwapChainSupportDetails:
    capabilities: Optional[vk.VkSurfaceCapabilitiesKHR] = None
    formats: List[vk.VkSurfaceFormatKHR] = None
    present_modes: List[vk.VkPresentModeKHR] = None