from typing import Dict, List, Optional, Set, Tuple
import vulkan as vk
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from .base import BaseValidator, ValidationContext, ValidationResult, ValidationSeverity
from ..error_codes import ValidationErrorCode
from ..exceptions import ValidationError, VulkanValidationError

logger = logging.getLogger(__name__)

@dataclass
class DeviceRequirements:
    """Requirements for physical device selection."""
    required_features: List[str] = field(default_factory=list)
    required_extensions: List[str] = field(default_factory=list)
    required_queue_flags: List[int] = field(default_factory=list)
    min_memory_size: int = 0
    preferred_gpu_type: Optional[int] = None
    required_api_version: Tuple[int, int, int] = (1, 0, 0)

@dataclass
class DeviceValidationConfig:
    """Configuration for device validation."""
    validate_queue_creation: bool = True
    validate_memory_allocation: bool = True
    track_queue_usage: bool = True
    track_memory_allocation: bool = True
    max_queue_families: int = 16
    max_queues_per_family: int = 16
    min_memory_alignment: int = 256
    enable_debug_markers: bool = True
    validate_feature_support: bool = True

@dataclass
class DeviceStats:
    """Track device usage statistics."""
    total_memory_allocated: int = 0
    peak_memory_allocated: int = 0
    active_queue_families: int = 0
    queues_created: Dict[int, int] = field(default_factory=dict)
    extension_usage: Dict[str, int] = field(default_factory=dict)
    feature_usage: Dict[str, int] = field(default_factory=dict)

class DeviceValidator(BaseValidator):
    """Validator for Vulkan device operations."""
    
    def __init__(self, context: ValidationContext, config: Optional[DeviceValidationConfig] = None):
        super().__init__(context)
        self.config = config or DeviceValidationConfig()
        self.stats = DeviceStats()
        self._active_queues: Dict[int, Set[int]] = {}  # family -> set of queue indices
        self._supported_extensions: Set[str] = set()
        self._supported_features: Set[str] = set()
        self._memory_allocations: Dict[int, int] = {}  # handle -> size
        
    def validate_physical_device(
        self,
        physical_device: vk.VkPhysicalDevice,
        requirements: DeviceRequirements
    ) -> ValidationResult:
        """Validate physical device against requirements."""
        try:
            self.begin_validation("physical_device")
            
            # Check API version
            properties = vk.vkGetPhysicalDeviceProperties(physical_device)
            device_version = (
                vk.VK_VERSION_MAJOR(properties.apiVersion),
                vk.VK_VERSION_MINOR(properties.apiVersion),
                vk.VK_VERSION_PATCH(properties.apiVersion)
            )
            
            if device_version < requirements.required_api_version:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.UNSUPPORTED_API_VERSION,
                    message=f"Device API version {device_version} does not meet required version {requirements.required_api_version}",
                    details={"device_version": device_version}
                )
                
            # Check device type preference
            if (requirements.preferred_gpu_type is not None and 
                properties.deviceType != requirements.preferred_gpu_type):
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.WARNING,
                    error_code=ValidationErrorCode.NONPREFERRED_DEVICE_TYPE,
                    message=f"Device type {properties.deviceType} does not match preferred type {requirements.preferred_gpu_type}"
                )
                
            # Validate memory requirements
            memory_properties = vk.vkGetPhysicalDeviceMemoryProperties(physical_device)
            total_memory = sum(
                heap.size
                for heap in memory_properties.memoryHeaps[:memory_properties.memoryHeapCount]
                if heap.flags & vk.VK_MEMORY_HEAP_DEVICE_LOCAL_BIT
            )
            
            if total_memory < requirements.min_memory_size:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INSUFFICIENT_MEMORY,
                    message=f"Device memory {total_memory} is less than required {requirements.min_memory_size}"
                )
                
            # Validate extensions
            available_extensions = {
                ext.extensionName
                for ext in vk.vkEnumerateDeviceExtensionProperties(physical_device, None)
            }
            self._supported_extensions = available_extensions
            
            missing_extensions = set(requirements.required_extensions) - available_extensions
            if missing_extensions:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.MISSING_EXTENSIONS,
                    message="Missing required extensions",
                    details={"missing_extensions": list(missing_extensions)}
                )
                
            # Validate features
            features = vk.vkGetPhysicalDeviceFeatures(physical_device)
            supported_features = {
                name for name, value in vars(features).items()
                if value and not name.startswith('_')
            }
            self._supported_features = supported_features
            
            missing_features = set(requirements.required_features) - supported_features
            if missing_features:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.MISSING_FEATURES,
                    message="Missing required features",
                    details={"missing_features": list(missing_features)}
                )
                
            # Validate queue families
            queue_families = vk.vkGetPhysicalDeviceQueueFamilyProperties(physical_device)
            supported_queue_flags = set()
            
            for family in queue_families:
                supported_queue_flags.update(
                    flag for flag in requirements.required_queue_flags
                    if family.queueFlags & flag
                )
                
            missing_queue_flags = set(requirements.required_queue_flags) - supported_queue_flags
            if missing_queue_flags:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.MISSING_QUEUE_SUPPORT,
                    message="Missing required queue support",
                    details={"missing_queue_flags": list(missing_queue_flags)}
                )
                
            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Physical device meets all requirements",
                details={
                    "device_name": properties.deviceName,
                    "device_type": properties.deviceType,
                    "api_version": device_version
                }
            )
            
        finally:
            self.end_validation("physical_device")
            
    def validate_logical_device_create(
        self,
        create_info: vk.VkDeviceCreateInfo
    ) -> ValidationResult:
        """Validate logical device creation parameters."""
        try:
            self.begin_validation("logical_device_create")
            
            # Validate queue create infos
            total_queues = 0
            queue_families_seen = set()
            
            for queue_info in create_info.pQueueCreateInfos[:create_info.queueCreateInfoCount]:
                if queue_info.queueFamilyIndex in queue_families_seen:
                    return ValidationResult(
                        success=False,
                        severity=ValidationSeverity.ERROR,
                        error_code=ValidationErrorCode.DUPLICATE_QUEUE_FAMILY,
                        message=f"Duplicate queue family index {queue_info.queueFamilyIndex}"
                    )
                    
                queue_families_seen.add(queue_info.queueFamilyIndex)
                total_queues += queue_info.queueCount
                
                if self.config.validate_queue_creation:
                    if queue_info.queueCount > self.config.max_queues_per_family:
                        return ValidationResult(
                            success=False,
                            severity=ValidationSeverity.ERROR,
                            error_code=ValidationErrorCode.TOO_MANY_QUEUES,
                            message=f"Too many queues requested for family {queue_info.queueFamilyIndex}"
                        )
                        
            # Validate enabled features
            if self.config.validate_feature_support:
                if create_info.pEnabledFeatures:
                    unsupported_features = {
                        name for name, value in vars(create_info.pEnabledFeatures).items()
                        if value and not name.startswith('_') and name not in self._supported_features
                    }
                    
                    if unsupported_features:
                        return ValidationResult(
                            success=False,
                            severity=ValidationSeverity.ERROR,
                            error_code=ValidationErrorCode.UNSUPPORTED_FEATURES,
                            message="Attempting to enable unsupported features",
                            details={"unsupported_features": list(unsupported_features)}
                        )
                        
            # Validate extensions
            unsupported_extensions = [
                ext for ext in create_info.ppEnabledExtensionNames
                if ext not in self._supported_extensions
            ]
            
            if unsupported_extensions:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.UNSUPPORTED_EXTENSIONS,
                    message="Attempting to enable unsupported extensions",
                    details={"unsupported_extensions": unsupported_extensions}
                )
                
            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Logical device creation parameters are valid",
                details={
                    "queue_families": len(queue_families_seen),
                    "total_queues": total_queues
                }
            )
            
        finally:
            self.end_validation("logical_device_create")
            
    def validate_memory_allocation(
        self,
        alloc_info: vk.VkMemoryAllocateInfo
    ) -> ValidationResult:
        """Validate memory allocation parameters."""
        try:
            self.begin_validation("memory_allocation")
            
            if not self.config.validate_memory_allocation:
                return ValidationResult(
                    success=True,
                    severity=ValidationSeverity.INFO,
                    message="Memory allocation validation disabled"
                )
                
            if alloc_info.allocationSize == 0:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INVALID_ALLOCATION_SIZE,
                    message="Memory allocation size cannot be zero"
                )
                
            # Check memory type index is valid
            memory_properties = vk.vkGetPhysicalDeviceMemoryProperties(self.context.physical_device)
            if alloc_info.memoryTypeIndex >= memory_properties.memoryTypeCount:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INVALID_MEMORY_TYPE,
                    message=f"Invalid memory type index {alloc_info.memoryTypeIndex}"
                )
                
            # Check alignment requirements
            if alloc_info.allocationSize % self.config.min_memory_alignment != 0:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INVALID_ALIGNMENT,
                    message=f"Allocation size must be aligned to {self.config.min_memory_alignment} bytes"
                )
                
            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Memory allocation parameters are valid",
                details={"size": alloc_info.allocationSize}
            )
            
        finally:
            self.end_validation("memory_allocation")
            
    def track_queue_creation(self, family_index: int, queue_index: int) -> None:
        """Track queue creation."""
        if not self.config.track_queue_usage:
            return
            
        if family_index not in self._active_queues:
            self._active_queues[family_index] = set()
            self.stats.active_queue_families += 1
            
        self._active_queues[family_index].add(queue_index)
        self.stats.queues_created[family_index] = \
            self.stats.queues_created.get(family_index, 0) + 1
            
    def track_memory_allocation(self, memory: vk.VkDeviceMemory, size: int) -> None:
        """Track memory allocation."""
        if not self.config.track_memory_allocation:
            return
            
        self._memory_allocations[memory] = size
        self.stats.total_memory_allocated += size
        self.stats.peak_memory_allocated = max(
            self.stats.peak_memory_allocated,
            self.stats.total_memory_allocated
        )
        
    def track_memory_free(self, memory: vk.VkDeviceMemory) -> None:
        """Track memory deallocation."""
        if memory in self._memory_allocations:
            size = self._memory_allocations.pop(memory)
            self.stats.total_memory_allocated -= size
            
    def get_device_stats(self) -> DeviceStats:
        """Get current device usage statistics."""
        return self.stats
        
    def reset_stats(self) -> None:
        """Reset device usage statistics."""
        self.stats = DeviceStats()
        
    def cleanup(self) -> None:
        """Clean up validator resources."""
        self._active_queues.clear()
        self._supported_extensions.clear()
        self._supported_features.clear()
        self._memory_allocations.clear()
        self.reset_stats()