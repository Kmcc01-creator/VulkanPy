from typing import Dict, List, Optional, Set, Tuple, NamedTuple
import vulkan as vk
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from .base import BaseValidator, ValidationContext, ValidationResult, ValidationSeverity
from ..error_codes import ValidationErrorCode
from ..exceptions import ValidationError, VulkanValidationError

logger = logging.getLogger(__name__)

class MemoryType(Enum):
    DEVICE_LOCAL = auto()
    HOST_VISIBLE = auto()
    HOST_COHERENT = auto()
    HOST_CACHED = auto()
    LAZILY_ALLOCATED = auto()

class MemoryAllocationScope(Enum):
    COMMAND = auto()
    OBJECT = auto()
    CACHE = auto()
    DEVICE = auto()

@dataclass
class MemoryBlock:
    """Represents a block of allocated memory."""
    size: int
    offset: int
    memory_type_index: int
    is_mapped: bool = False
    allocation_scope: MemoryAllocationScope = MemoryAllocationScope.OBJECT
    references: int = 0

class MemoryRange(NamedTuple):
    """Represents a range of memory."""
    offset: int
    size: int

@dataclass
class MemoryValidationConfig:
    """Configuration for memory validation."""
    max_allocations: int = 4096
    max_allocation_size: int = 1024 * 1024 * 1024  # 1GB
    min_allocation_alignment: int = 256
    track_memory_leaks: bool = True
    validate_memory_mapping: bool = True
    enable_defragmentation: bool = True
    max_concurrent_mappings: int = 64
    preferred_block_size: int = 64 * 1024 * 1024  # 64MB
    enable_memory_tracking: bool = True

@dataclass
class MemoryStats:
    """Track memory usage statistics."""
    total_allocated: int = 0
    peak_allocated: int = 0
    total_allocations: int = 0
    current_mappings: int = 0
    allocation_by_type: Dict[MemoryType, int] = field(default_factory=dict)
    fragmentation_ratio: float = 0.0
    leaked_allocations: int = 0

class MemoryValidator(BaseValidator):
    """Validator for Vulkan memory operations."""
    
    def __init__(self, context: ValidationContext, config: Optional[MemoryValidationConfig] = None):
        super().__init__(context)
        self.config = config or MemoryValidationConfig()
        self.stats = MemoryStats()
        self._allocations: Dict[vk.VkDeviceMemory, MemoryBlock] = {}
        self._mapped_ranges: Dict[vk.VkDeviceMemory, List[MemoryRange]] = {}
        self._type_properties: Dict[int, vk.VkMemoryType] = {}
        self._initialize_memory_types()

    def _initialize_memory_types(self) -> None:
        """Initialize memory type information."""
        try:
            memory_properties = vk.vkGetPhysicalDeviceMemoryProperties(self.context.physical_device)
            for i in range(memory_properties.memoryTypeCount):
                self._type_properties[i] = memory_properties.memoryTypes[i]
        except Exception as e:
            logger.error(f"Failed to initialize memory types: {e}")
            raise

    def validate_memory_allocation(
        self,
        alloc_info: vk.VkMemoryAllocateInfo,
        scope: MemoryAllocationScope = MemoryAllocationScope.OBJECT
    ) -> ValidationResult:
        """Validate memory allocation parameters."""
        try:
            self.begin_validation("memory_allocation")
            
            if len(self._allocations) >= self.config.max_allocations:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.TOO_MANY_ALLOCATIONS,
                    message=f"Maximum number of allocations ({self.config.max_allocations}) exceeded"
                )

            if alloc_info.allocationSize > self.config.max_allocation_size:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.ALLOCATION_TOO_LARGE,
                    message=f"Allocation size {alloc_info.allocationSize} exceeds maximum {self.config.max_allocation_size}"
                )

            if alloc_info.allocationSize % self.config.min_allocation_alignment != 0:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INVALID_ALIGNMENT,
                    message=f"Allocation size must be aligned to {self.config.min_allocation_alignment}"
                )

            # Validate memory type index
            if alloc_info.memoryTypeIndex not in self._type_properties:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INVALID_MEMORY_TYPE,
                    message=f"Invalid memory type index {alloc_info.memoryTypeIndex}"
                )

            memory_type = self._type_properties[alloc_info.memoryTypeIndex]
            type_flags = memory_type.propertyFlags

            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Memory allocation parameters are valid",
                details={
                    "size": alloc_info.allocationSize,
                    "type_index": alloc_info.memoryTypeIndex,
                    "type_flags": type_flags,
                    "scope": scope.name
                }
            )

        finally:
            self.end_validation("memory_allocation")

    def validate_memory_map(
        self,
        memory: vk.VkDeviceMemory,
        offset: int,
        size: int
    ) -> ValidationResult:
        """Validate memory mapping parameters."""
        try:
            self.begin_validation("memory_map")

            if not self.config.validate_memory_mapping:
                return ValidationResult(
                    success=True,
                    severity=ValidationSeverity.INFO,
                    message="Memory mapping validation disabled"
                )

            if memory not in self._allocations:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INVALID_MEMORY_OBJECT,
                    message="Invalid memory object"
                )

            block = self._allocations[memory]
            if block.is_mapped:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.ALREADY_MAPPED,
                    message="Memory is already mapped"
                )

            if self.stats.current_mappings >= self.config.max_concurrent_mappings:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.TOO_MANY_MAPPINGS,
                    message=f"Maximum number of concurrent mappings ({self.config.max_concurrent_mappings}) exceeded"
                )

            if offset + size > block.size:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INVALID_MAP_RANGE,
                    message="Mapping range exceeds allocation size"
                )

            # Check if memory type is host visible
            memory_type = self._type_properties[block.memory_type_index]
            if not (memory_type.propertyFlags & vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT):
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.NOT_HOST_VISIBLE,
                    message="Memory type is not host visible"
                )

            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Memory mapping parameters are valid",
                details={"offset": offset, "size": size}
            )

        finally:
            self.end_validation("memory_map")

    def validate_memory_bind(
        self,
        memory: vk.VkDeviceMemory,
        resource_size: int,
        offset: int
    ) -> ValidationResult:
        """Validate memory binding parameters."""
        try:
            self.begin_validation("memory_bind")
            
            if memory not in self._allocations:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INVALID_MEMORY_OBJECT,
                    message="Invalid memory object"
                )

            block = self._allocations[memory]
            if offset + resource_size > block.size:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INVALID_BIND_RANGE,
                    message="Binding range exceeds allocation size"
                )

            # Check for overlapping bindings
            range_to_bind = MemoryRange(offset, resource_size)
            if memory in self._mapped_ranges:
                for existing_range in self._mapped_ranges[memory]:
                    if self._ranges_overlap(range_to_bind, existing_range):
                        return ValidationResult(
                            success=False,
                            severity=ValidationSeverity.ERROR,
                            error_code=ValidationErrorCode.OVERLAPPING_BIND,
                            message="Memory binding overlaps with existing binding"
                        )

            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Memory binding parameters are valid",
                details={"size": resource_size, "offset": offset}
            )

        finally:
            self.end_validation("memory_bind")

    def _ranges_overlap(self, a: MemoryRange, b: MemoryRange) -> bool:
        """Check if two memory ranges overlap."""
        return not (a.offset + a.size <= b.offset or b.offset + b.size <= a.offset)

    def track_memory_allocation(
        self,
        memory: vk.VkDeviceMemory,
        size: int,
        type_index: int,
        scope: MemoryAllocationScope
    ) -> None:
        """Track memory allocation."""
        if not self.config.enable_memory_tracking:
            return

        block = MemoryBlock(
            size=size,
            offset=0,
            memory_type_index=type_index,
            allocation_scope=scope
        )
        
        self._allocations[memory] = block
        self.stats.total_allocated += size
        self.stats.total_allocations += 1
        self.stats.peak_allocated = max(
            self.stats.peak_allocated,
            self.stats.total_allocated
        )

        # Track allocation by memory type
        memory_type = self._type_properties[type_index]
        for mem_type in MemoryType:
            if memory_type.propertyFlags & getattr(vk, f'VK_MEMORY_PROPERTY_{mem_type.name}_BIT'):
                self.stats.allocation_by_type[mem_type] = \
                    self.stats.allocation_by_type.get(mem_type, 0) + size

    def track_memory_free(self, memory: vk.VkDeviceMemory) -> None:
        """Track memory deallocation."""
        if memory in self._allocations:
            block = self._allocations.pop(memory)
            self.stats.total_allocated -= block.size
            
            if memory in self._mapped_ranges:
                del self._mapped_ranges[memory]

            # Update allocation by type stats
            memory_type = self._type_properties[block.memory_type_index]
            for mem_type in MemoryType:
                if memory_type.propertyFlags & getattr(vk, f'VK_MEMORY_PROPERTY_{mem_type.name}_BIT'):
                    self.stats.allocation_by_type[mem_type] = \
                        self.stats.allocation_by_type.get(mem_type, 0) - block.size

    def track_memory_map(self, memory: vk.VkDeviceMemory, offset: int, size: int) -> None:
        """Track memory mapping."""
        if memory in self._allocations:
            block = self._allocations[memory]
            block.is_mapped = True
            self.stats.current_mappings += 1
            
            if memory not in self._mapped_ranges:
                self._mapped_ranges[memory] = []
            self._mapped_ranges[memory].append(MemoryRange(offset, size))

    def track_memory_unmap(self, memory: vk.VkDeviceMemory) -> None:
        """Track memory unmapping."""
        if memory in self._allocations:
            block = self._allocations[memory]
            block.is_mapped = False
            self.stats.current_mappings -= 1
            
            if memory in self._mapped_ranges:
                del self._mapped_ranges[memory]

    def track_memory_reference(self, memory: vk.VkDeviceMemory) -> None:
        """Track memory object reference."""
        if memory in self._allocations:
            self._allocations[memory].references += 1

    def track_memory_release(self, memory: vk.VkDeviceMemory) -> None:
        """Track memory object release."""
        if memory in self._allocations:
            block = self._allocations[memory]
            block.references -= 1
            
            if block.references == 0 and self.config.track_memory_leaks:
                self.stats.leaked_allocations += 1

    def calculate_fragmentation(self) -> float:
        """Calculate current memory fragmentation ratio."""
        if not self._allocations:
            return 0.0

        total_allocated = sum(block.size for block in self._allocations.values())
        total_used = sum(block.size for block in self._allocations.values() if block.references > 0)
        
        if total_allocated == 0:
            return 0.0
            
        self.stats.fragmentation_ratio = 1.0 - (total_used / total_allocated)
        return self.stats.fragmentation_ratio

    def get_memory_stats(self) -> MemoryStats:
        """Get current memory usage statistics."""
        return self.stats

    def reset_stats(self) -> None:
        """Reset memory usage statistics."""
        self.stats = MemoryStats()

    def cleanup(self) -> None:
        """Clean up validator resources."""
        self._allocations.clear()
        self._mapped_ranges.clear()
        self.reset_stats()