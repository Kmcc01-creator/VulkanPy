from typing import Dict, List, Optional, Set, Tuple
import vulkan as vk
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from .base import BaseValidator, ValidationContext, ValidationResult, ValidationSeverity
from ..error_codes import ValidationErrorCode
from ..exceptions import ValidationError, VulkanValidationError

logger = logging.getLogger(__name__)

class DescriptorType(Enum):
    SAMPLER = auto()
    COMBINED_IMAGE_SAMPLER = auto()
    SAMPLED_IMAGE = auto()
    STORAGE_IMAGE = auto()
    UNIFORM_TEXEL_BUFFER = auto()
    STORAGE_TEXEL_BUFFER = auto()
    UNIFORM_BUFFER = auto()
    STORAGE_BUFFER = auto()
    UNIFORM_BUFFER_DYNAMIC = auto()
    STORAGE_BUFFER_DYNAMIC = auto()
    INPUT_ATTACHMENT = auto()

@dataclass
class DescriptorValidationConfig:
    """Configuration for descriptor validation."""
    max_descriptor_sets: int = 4096
    max_descriptor_pools: int = 64
    max_bindings_per_layout: int = 32
    max_descriptors_per_pool: int = 10000
    validate_descriptor_updates: bool = True
    track_descriptor_usage: bool = True
    enable_dynamic_state_validation: bool = True
    max_dynamic_uniform_buffers: int = 8
    max_dynamic_storage_buffers: int = 4

@dataclass
class DescriptorStats:
    """Track descriptor usage statistics."""
    total_sets_allocated: int = 0
    current_active_sets: int = 0
    current_active_pools: int = 0
    total_updates_performed: int = 0
    descriptor_types: Dict[DescriptorType, int] = field(default_factory=dict)
    bindings_per_set: Dict[int, int] = field(default_factory=dict)

class DescriptorValidator(BaseValidator):
    """Validator for Vulkan descriptor operations."""
    
    def __init__(self, context: ValidationContext, config: Optional[DescriptorValidationConfig] = None):
        super().__init__(context)
        self.config = config or DescriptorValidationConfig()
        self.stats = DescriptorStats()
        self._descriptor_pools: Set[vk.VkDescriptorPool] = set()
        self._descriptor_sets: Dict[vk.VkDescriptorSet, vk.VkDescriptorPool] = {}
        self._layout_bindings: Dict[vk.VkDescriptorSetLayout, List[vk.VkDescriptorSetLayoutBinding]] = {}
        self._pool_sizes: Dict[vk.VkDescriptorPool, Dict[int, int]] = {}
        self._pool_allocations: Dict[vk.VkDescriptorPool, Dict[int, int]] = {}
        
    def validate_descriptor_set_layout(
        self,
        create_info: vk.VkDescriptorSetLayoutCreateInfo
    ) -> ValidationResult:
        """Validate descriptor set layout creation parameters."""
        try:
            self.begin_validation("descriptor_set_layout")
            
            if not create_info.bindingCount:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.NO_BINDINGS,
                    message="Descriptor set layout must have at least one binding"
                )
                
            if create_info.bindingCount > self.config.max_bindings_per_layout:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.TOO_MANY_BINDINGS,
                    message=f"Number of bindings ({create_info.bindingCount}) exceeds maximum ({self.config.max_bindings_per_layout})"
                )
                
            # Validate bindings
            bindings = create_info.pBindings[:create_info.bindingCount]
            dynamic_uniform_count = 0
            dynamic_storage_count = 0
            
            for binding in bindings:
                # Check for duplicate binding numbers
                binding_numbers = [b.binding for b in bindings]
                if binding_numbers.count(binding.binding) > 1:
                    return ValidationResult(
                        success=False,
                        severity=ValidationSeverity.ERROR,
                        error_code=ValidationErrorCode.DUPLICATE_BINDING,
                        message=f"Duplicate binding number {binding.binding}"
                    )
                    
                # Track dynamic buffer usage
                if binding.descriptorType == vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER_DYNAMIC:
                    dynamic_uniform_count += binding.descriptorCount
                elif binding.descriptorType == vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER_DYNAMIC:
                    dynamic_storage_count += binding.descriptorCount
                    
            # Validate dynamic buffer limits
            if dynamic_uniform_count > self.config.max_dynamic_uniform_buffers:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.TOO_MANY_DYNAMIC_UNIFORM_BUFFERS,
                    message=f"Too many dynamic uniform buffers ({dynamic_uniform_count})"
                )
                
            if dynamic_storage_count > self.config.max_dynamic_storage_buffers:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.TOO_MANY_DYNAMIC_STORAGE_BUFFERS,
                    message=f"Too many dynamic storage buffers ({dynamic_storage_count})"
                )
                
            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Descriptor set layout is valid",
                details={
                    "binding_count": create_info.bindingCount,
                    "dynamic_uniform_count": dynamic_uniform_count,
                    "dynamic_storage_count": dynamic_storage_count
                }
            )
            
        finally:
            self.end_validation("descriptor_set_layout")
            
    def validate_descriptor_pool_create(
        self,
        create_info: vk.VkDescriptorPoolCreateInfo
    ) -> ValidationResult:
        """Validate descriptor pool creation parameters."""
        try:
            self.begin_validation("descriptor_pool_create")
            
            if len(self._descriptor_pools) >= self.config.max_descriptor_pools:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.TOO_MANY_DESCRIPTOR_POOLS,
                    message=f"Maximum number of descriptor pools ({self.config.max_descriptor_pools}) exceeded"
                )
                
            if create_info.maxSets > self.config.max_descriptor_sets:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.TOO_MANY_DESCRIPTOR_SETS,
                    message=f"Maximum sets ({create_info.maxSets}) exceeds limit ({self.config.max_descriptor_sets})"
                )
                
            total_descriptors = 0
            for pool_size in create_info.pPoolSizes[:create_info.poolSizeCount]:
                total_descriptors += pool_size.descriptorCount
                
            if total_descriptors > self.config.max_descriptors_per_pool:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.TOO_MANY_DESCRIPTORS,
                    message=f"Total descriptor count ({total_descriptors}) exceeds maximum ({self.config.max_descriptors_per_pool})"
                )
                
            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Descriptor pool creation parameters are valid",
                details={
                    "max_sets": create_info.maxSets,
                    "total_descriptors": total_descriptors
                }
            )
            
        finally:
            self.end_validation("descriptor_pool_create")
            
    def validate_descriptor_set_allocate(
        self,
        pool: vk.VkDescriptorPool,
        alloc_info: vk.VkDescriptorSetAllocateInfo
    ) -> ValidationResult:
        """Validate descriptor set allocation parameters."""
        try:
            self.begin_validation("descriptor_set_allocate")
            
            if pool not in self._descriptor_pools:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INVALID_DESCRIPTOR_POOL,
                    message="Descriptor pool is not valid or has been destroyed"
                )
                
            # Check if pool has enough space
            if pool in self._pool_allocations:
                current_sets = len(self._pool_allocations[pool])
                if current_sets + alloc_info.descriptorSetCount > self.config.max_descriptor_sets:
                    return ValidationResult(
                        success=False,
                        severity=ValidationSeverity.ERROR,
                        error_code=ValidationErrorCode.POOL_OUT_OF_SPACE,
                        message="Descriptor pool does not have enough space for allocation"
                    )
                    
            # Validate layouts
            for layout in alloc_info.pSetLayouts[:alloc_info.descriptorSetCount]:
                if layout not in self._layout_bindings:
                    return ValidationResult(
                        success=False,
                        severity=ValidationSeverity.ERROR,
                        error_code=ValidationErrorCode.INVALID_LAYOUT,
                        message="Invalid descriptor set layout"
                    )
                    
            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Descriptor set allocation parameters are valid",
                details={"set_count": alloc_info.descriptorSetCount}
            )
            
        finally:
            self.end_validation("descriptor_set_allocate")
            
    def validate_descriptor_set_update(
        self,
        write_descriptor_sets: List[vk.VkWriteDescriptorSet]
    ) -> ValidationResult:
        """Validate descriptor set update parameters."""
        try:
            self.begin_validation("descriptor_set_update")
            
            if not self.config.validate_descriptor_updates:
                return ValidationResult(
                    success=True,
                    severity=ValidationSeverity.INFO,
                    message="Descriptor update validation disabled"
                )
                
            for write in write_descriptor_sets:
                descriptor_set = write.dstSet
                
                if descriptor_set not in self._descriptor_sets:
                    return ValidationResult(
                        success=False,
                        severity=ValidationSeverity.ERROR,
                        error_code=ValidationErrorCode.INVALID_DESCRIPTOR_SET,
                        message="Invalid descriptor set in update"
                    )
                    
                # Validate binding exists in layout
                pool = self._descriptor_sets[descriptor_set]
                if not self._validate_binding_update(pool, write):
                    return ValidationResult(
                        success=False,
                        severity=ValidationSeverity.ERROR,
                        error_code=ValidationErrorCode.INVALID_BINDING_UPDATE,
                        message=f"Invalid update to binding {write.dstBinding}"
                    )
                    
            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Descriptor set updates are valid",
                details={"update_count": len(write_descriptor_sets)}
            )
            
        finally:
            self.end_validation("descriptor_set_update")
            
    def _validate_binding_update(
        self,
        pool: vk.VkDescriptorPool,
        write: vk.VkWriteDescriptorSet
    ) -> bool:
        """Validate a single binding update."""
        if pool not in self._pool_sizes:
            return False
            
        pool_sizes = self._pool_sizes[pool]
        if write.descriptorType not in pool_sizes:
            return False
            
        current_count = self._pool_allocations.get(pool, {}).get(write.descriptorType, 0)
        if current_count + write.descriptorCount > pool_sizes[write.descriptorType]:
            return False
            
        return True
        
    def track_descriptor_pool_creation(
        self,
        pool: vk.VkDescriptorPool,
        create_info: vk.VkDescriptorPoolCreateInfo
    ) -> None:
        """Track descriptor pool creation."""
        if not self.config.track_descriptor_usage:
            return
            
        self._descriptor_pools.add(pool)
        self._pool_sizes[pool] = {
            size.type: size.descriptorCount
            for size in create_info.pPoolSizes[:create_info.poolSizeCount]
        }
        self._pool_allocations[pool] = {}
        self.stats.current_active_pools += 1
        
    def track_descriptor_set_allocation(
        self,
        pool: vk.VkDescriptorPool,
        descriptor_set: vk.VkDescriptorSet
    ) -> None:
        """Track descriptor set allocation."""
        if not self.config.track_descriptor_usage:
            return
            
        self._descriptor_sets[descriptor_set] = pool
        self.stats.total_sets_allocated += 1
        self.stats.current_active_sets += 1
        
    def track_descriptor_update(self, write: vk.VkWriteDescriptorSet) -> None:
        """Track descriptor update."""
        if not self.config.track_descriptor_usage:
            return
            
        descriptor_type = DescriptorType(write.descriptorType)
        self.stats.descriptor_types[descriptor_type] = \
            self.stats.descriptor_types.get(descriptor_type, 0) + write.descriptorCount
        self.stats.total_updates_performed += 1
        
    def track_descriptor_pool_destruction(self, pool: vk.VkDescriptorPool) -> None:
        """Track descriptor pool destruction."""
        if pool in self._descriptor_pools:
            self._descriptor_pools.remove(pool)
            if pool in self._pool_sizes:
                del self._pool_sizes[pool]
            if pool in self._pool_allocations:
                del self._pool_allocations[pool]
            self.stats.current_active_pools -= 1
            
    def get_descriptor_stats(self) -> DescriptorStats:
        """Get current descriptor usage statistics."""
        return self.stats
        
    def reset_stats(self) -> None:
        """Reset descriptor usage statistics."""
        self.stats = DescriptorStats()
        
    def cleanup(self) -> None:
        """Clean up validator resources."""
        self._descriptor_pools.clear()
        self._descriptor_sets.clear()
        self._layout_bindings.clear()
        self._pool_sizes.clear()
        self._pool_allocations.clear()
        self.reset_stats()