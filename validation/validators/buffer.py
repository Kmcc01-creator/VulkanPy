from typing import Dict, List, Optional, Set, Tuple
import vulkan as vk
import logging
from dataclasses import dataclass, field
from .base import BaseValidator, ValidationContext, ValidationResult, ValidationSeverity
from ..error_codes import ValidationErrorCode
from ..exceptions import ValidationError, VulkanValidationError

logger = logging.getLogger(__name__)

@dataclass
class BufferValidationConfig:
    """Configuration for buffer validation."""
    max_buffer_size: int = 1024 * 1024 * 1024  # 1GB default max buffer size
    min_buffer_size: int = 4  # Minimum buffer size
    required_alignment: int = 4  # Default alignment requirement
    max_active_buffers: int = 1024  # Maximum number of active buffers
    validate_memory_allocations: bool = True
    track_buffer_usage: bool = True
    verify_buffer_barriers: bool = True

@dataclass
class BufferUsageStats:
    """Track buffer usage statistics."""
    total_allocations: int = 0
    current_active_buffers: int = 0
    total_memory_allocated: int = 0
    buffer_types: Dict[int, int] = field(default_factory=dict)  # Usage type -> count
    memory_types: Dict[int, int] = field(default_factory=dict)  # Memory type -> bytes

class BufferValidator(BaseValidator):
    """Validator for Vulkan buffer operations."""
    
    def __init__(self, context: ValidationContext, config: Optional[BufferValidationConfig] = None):
        super().__init__(context)
        self.config = config or BufferValidationConfig()
        self.stats = BufferUsageStats()
        self._active_buffers: Set[vk.VkBuffer] = set()
        self._buffer_memory_map: Dict[vk.VkBuffer, vk.VkDeviceMemory] = {}
        self._memory_ranges: List[Tuple[int, int]] = []  # List of (offset, size) tuples
        
    def validate_buffer_create_info(self, create_info: vk.VkBufferCreateInfo) -> ValidationResult:
        """Validate buffer creation parameters."""
        try:
            self.begin_validation("buffer_create_info")
            
            if not create_info.size:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INVALID_BUFFER_SIZE,
                    message="Buffer size cannot be zero",
                    details={"size": create_info.size}
                )
                
            if create_info.size > self.config.max_buffer_size:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.BUFFER_TOO_LARGE,
                    message=f"Buffer size exceeds maximum allowed size of {self.config.max_buffer_size}",
                    details={"size": create_info.size, "max_size": self.config.max_buffer_size}
                )
                
            if create_info.size < self.config.min_buffer_size:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.BUFFER_TOO_SMALL,
                    message=f"Buffer size is below minimum allowed size of {self.config.min_buffer_size}",
                    details={"size": create_info.size, "min_size": self.config.min_buffer_size}
                )
                
            # Validate usage flags
            if not create_info.usage:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INVALID_BUFFER_USAGE,
                    message="Buffer usage flags cannot be zero"
                )
                
            # Check buffer capacity
            if len(self._active_buffers) >= self.config.max_active_buffers:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.TOO_MANY_BUFFERS,
                    message=f"Maximum number of active buffers ({self.config.max_active_buffers}) exceeded",
                    details={"active_buffers": len(self._active_buffers)}
                )
                
            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Buffer creation parameters are valid",
                details={"size": create_info.size, "usage": create_info.usage}
            )
            
        finally:
            self.end_validation("buffer_create_info")
            
    def validate_buffer_memory_requirements(
        self, 
        buffer: vk.VkBuffer, 
        memory_requirements: vk.VkMemoryRequirements
    ) -> ValidationResult:
        """Validate buffer memory requirements."""
        try:
            self.begin_validation("buffer_memory_requirements")
            
            if memory_requirements.size < self.config.min_buffer_size:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INVALID_MEMORY_REQUIREMENTS,
                    message="Memory requirements size is too small",
                    details={"size": memory_requirements.size}
                )
                
            if memory_requirements.alignment % self.config.required_alignment != 0:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INVALID_ALIGNMENT,
                    message=f"Memory alignment {memory_requirements.alignment} is not a multiple of required alignment {self.config.required_alignment}",
                    details={
                        "alignment": memory_requirements.alignment,
                        "required_alignment": self.config.required_alignment
                    }
                )
                
            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Buffer memory requirements are valid",
                details={
                    "size": memory_requirements.size,
                    "alignment": memory_requirements.alignment,
                    "memory_type_bits": memory_requirements.memoryTypeBits
                }
            )
            
        finally:
            self.end_validation("buffer_memory_requirements")
            
    def validate_buffer_memory_bind(
        self, 
        buffer: vk.VkBuffer, 
        memory: vk.VkDeviceMemory, 
        offset: int
    ) -> ValidationResult:
        """Validate buffer memory binding."""
        try:
            self.begin_validation("buffer_memory_bind")
            
            if buffer in self._buffer_memory_map:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.BUFFER_ALREADY_BOUND,
                    message="Buffer is already bound to memory",
                    details={"existing_memory": self._buffer_memory_map[buffer]}
                )
                
            # Check for overlapping memory ranges
            if self.config.validate_memory_allocations:
                for range_offset, range_size in self._memory_ranges:
                    if (offset >= range_offset and offset < range_offset + range_size) or \
                       (range_offset >= offset and range_offset < offset + range_size):
                        return ValidationResult(
                            success=False,
                            severity=ValidationSeverity.ERROR,
                            error_code=ValidationErrorCode.MEMORY_RANGE_OVERLAP,
                            message="Memory range overlaps with existing allocation",
                            details={
                                "new_offset": offset,
                                "existing_offset": range_offset,
                                "existing_size": range_size
                            }
                        )
                        
            # Track the binding
            self._buffer_memory_map[buffer] = memory
            
            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Buffer memory binding is valid",
                details={"offset": offset}
            )
            
        finally:
            self.end_validation("buffer_memory_bind")
            
    def track_buffer_creation(self, buffer: vk.VkBuffer, usage: int) -> None:
        """Track buffer creation for statistics."""
        if not self.config.track_buffer_usage:
            return
            
        self._active_buffers.add(buffer)
        self.stats.current_active_buffers += 1
        self.stats.total_allocations += 1
        
        # Track usage types
        for usage_flag in [1 << i for i in range(32)]:
            if usage & usage_flag:
                self.stats.buffer_types[usage_flag] = \
                    self.stats.buffer_types.get(usage_flag, 0) + 1
                    
    def track_buffer_destruction(self, buffer: vk.VkBuffer) -> None:
        """Track buffer destruction."""
        if buffer in self._active_buffers:
            self._active_buffers.remove(buffer)
            self.stats.current_active_buffers -= 1
            
        if buffer in self._buffer_memory_map:
            del self._buffer_memory_map[buffer]
            
    def validate_buffer_barrier(
        self,
        buffer: vk.VkBuffer,
        src_access_mask: int,
        dst_access_mask: int,
        src_queue_family: int,
        dst_queue_family: int
    ) -> ValidationResult:
        """Validate buffer memory barrier parameters."""
        try:
            self.begin_validation("buffer_barrier")
            
            if not self.config.verify_buffer_barriers:
                return ValidationResult(
                    success=True,
                    severity=ValidationSeverity.INFO,
                    message="Buffer barrier validation disabled"
                )
                
            if buffer not in self._active_buffers:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INVALID_BUFFER,
                    message="Buffer is not active or has been destroyed",
                    details={"buffer_handle": buffer}
                )
                
            # Validate queue family indices
            if src_queue_family != vk.VK_QUEUE_FAMILY_IGNORED and \
               dst_queue_family != vk.VK_QUEUE_FAMILY_IGNORED and \
               src_queue_family == dst_queue_family:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.WARNING,
                    error_code=ValidationErrorCode.UNNECESSARY_BARRIER,
                    message="Queue family transition to same queue family",
                    details={
                        "src_queue_family": src_queue_family,
                        "dst_queue_family": dst_queue_family
                    }
                )
                
            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Buffer barrier parameters are valid",
                details={
                    "src_access_mask": src_access_mask,
                    "dst_access_mask": dst_access_mask,
                    "src_queue_family": src_queue_family,
                    "dst_queue_family": dst_queue_family
                }
            )
            
        finally:
            self.end_validation("buffer_barrier")
            
    def get_buffer_stats(self) -> BufferUsageStats:
        """Get current buffer usage statistics."""
        return self.stats
        
    def reset_stats(self) -> None:
        """Reset buffer usage statistics."""
        self.stats = BufferUsageStats()
        
    def cleanup(self) -> None:
        """Clean up validator resources."""
        self._active_buffers.clear()
        self._buffer_memory_map.clear()
        self._memory_ranges.clear()
        self.reset_stats()