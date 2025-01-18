from typing import Dict, List, Optional, Set, Tuple
import vulkan as vk
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from .base import BaseValidator, ValidationContext, ValidationResult, ValidationSeverity
from ..error_codes import ValidationErrorCode
from ..exceptions import ValidationError, VulkanValidationError

logger = logging.getLogger(__name__)

class CommandBufferState(Enum):
    INITIAL = auto()
    RECORDING = auto()
    EXECUTABLE = auto()
    PENDING = auto()
    INVALID = auto()

@dataclass
class CommandValidationConfig:
    """Configuration for command validation."""
    max_command_pools: int = 64
    max_command_buffers_per_pool: int = 1024
    max_active_command_buffers: int = 256
    track_command_buffer_usage: bool = True
    validate_command_buffer_state: bool = True
    validate_render_pass_scope: bool = True
    max_command_buffer_size: int = 1024 * 1024  # 1MB default max size
    enable_usage_tracking: bool = True

@dataclass
class CommandBufferUsageStats:
    """Track command buffer usage statistics."""
    total_allocations: int = 0
    current_active_pools: int = 0
    current_active_buffers: int = 0
    resets_performed: int = 0
    submissions_performed: int = 0
    command_pool_types: Dict[int, int] = field(default_factory=dict)

class CommandValidator(BaseValidator):
    """Validator for Vulkan command operations."""
    
    def __init__(self, context: ValidationContext, config: Optional[CommandValidationConfig] = None):
        super().__init__(context)
        self.config = config or CommandValidationConfig()
        self.stats = CommandBufferUsageStats()
        self._command_pools: Set[vk.VkCommandPool] = set()
        self._command_buffers: Dict[vk.VkCommandBuffer, CommandBufferState] = {}
        self._pool_buffer_map: Dict[vk.VkCommandPool, Set[vk.VkCommandBuffer]] = {}
        self._render_pass_scope: Dict[vk.VkCommandBuffer, bool] = {}
        self._command_buffer_families: Dict[vk.VkCommandBuffer, int] = {}
        
    def validate_command_pool_create(self, create_info: vk.VkCommandPoolCreateInfo) -> ValidationResult:
        """Validate command pool creation parameters."""
        try:
            self.begin_validation("command_pool_create")
            
            if len(self._command_pools) >= self.config.max_command_pools:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.TOO_MANY_COMMAND_POOLS,
                    message=f"Maximum number of command pools ({self.config.max_command_pools}) exceeded",
                    details={"current_pools": len(self._command_pools)}
                )
                
            # Validate queue family index
            queue_families = vk.vkGetPhysicalDeviceQueueFamilyProperties(self.context.physical_device)
            if create_info.queueFamilyIndex >= len(queue_families):
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INVALID_QUEUE_FAMILY,
                    message="Invalid queue family index",
                    details={"queue_family_index": create_info.queueFamilyIndex}
                )
                
            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Command pool creation parameters are valid",
                details={
                    "queue_family_index": create_info.queueFamilyIndex,
                    "flags": create_info.flags
                }
            )
            
        finally:
            self.end_validation("command_pool_create")
            
    def validate_command_buffer_allocate(
        self,
        pool: vk.VkCommandPool,
        alloc_info: vk.VkCommandBufferAllocateInfo
    ) -> ValidationResult:
        """Validate command buffer allocation parameters."""
        try:
            self.begin_validation("command_buffer_allocate")
            
            if pool not in self._command_pools:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INVALID_COMMAND_POOL,
                    message="Command pool is not valid or has been destroyed",
                    details={"pool_handle": pool}
                )
                
            pool_buffers = self._pool_buffer_map.get(pool, set())
            if len(pool_buffers) + alloc_info.commandBufferCount > self.config.max_command_buffers_per_pool:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.TOO_MANY_COMMAND_BUFFERS,
                    message=f"Maximum number of command buffers per pool ({self.config.max_command_buffers_per_pool}) would be exceeded",
                    details={
                        "current_buffers": len(pool_buffers),
                        "requested_buffers": alloc_info.commandBufferCount
                    }
                )
                
            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Command buffer allocation parameters are valid",
                details={
                    "level": alloc_info.level,
                    "count": alloc_info.commandBufferCount
                }
            )
            
        finally:
            self.end_validation("command_buffer_allocate")
            
    def validate_command_buffer_begin(
        self,
        command_buffer: vk.VkCommandBuffer,
        begin_info: vk.VkCommandBufferBeginInfo
    ) -> ValidationResult:
        """Validate command buffer recording begin."""
        try:
            self.begin_validation("command_buffer_begin")
            
            if command_buffer not in self._command_buffers:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INVALID_COMMAND_BUFFER,
                    message="Command buffer is not valid or has been destroyed"
                )
                
            current_state = self._command_buffers[command_buffer]
            if current_state == CommandBufferState.RECORDING:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.COMMAND_BUFFER_ALREADY_RECORDING,
                    message="Command buffer is already in recording state"
                )
                
            if current_state == CommandBufferState.PENDING:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.COMMAND_BUFFER_PENDING,
                    message="Command buffer is pending execution"
                )
                
            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Command buffer can begin recording",
                details={"flags": begin_info.flags}
            )
            
        finally:
            self.end_validation("command_buffer_begin")
            
    def validate_render_pass_scope(
        self,
        command_buffer: vk.VkCommandBuffer,
        in_render_pass: bool
    ) -> ValidationResult:
        """Validate render pass scope for command buffer operations."""
        try:
            self.begin_validation("render_pass_scope")
            
            if not self.config.validate_render_pass_scope:
                return ValidationResult(
                    success=True,
                    severity=ValidationSeverity.INFO,
                    message="Render pass scope validation disabled"
                )
                
            current_in_render_pass = self._render_pass_scope.get(command_buffer, False)
            
            if in_render_pass and current_in_render_pass:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.NESTED_RENDER_PASS,
                    message="Cannot begin render pass while already in render pass"
                )
                
            if not in_render_pass and not current_in_render_pass:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.NOT_IN_RENDER_PASS,
                    message="Command must be recorded within a render pass"
                )
                
            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Render pass scope is valid"
            )
            
        finally:
            self.end_validation("render_pass_scope")
            
    def track_command_pool_creation(self, pool: vk.VkCommandPool, flags: int) -> None:
        """Track command pool creation for statistics."""
        if not self.config.enable_usage_tracking:
            return
            
        self._command_pools.add(pool)
        self._pool_buffer_map[pool] = set()
        self.stats.current_active_pools += 1
        
        for flag in [1 << i for i in range(32)]:
            if flags & flag:
                self.stats.command_pool_types[flag] = \
                    self.stats.command_pool_types.get(flag, 0) + 1
                    
    def track_command_buffer_allocation(
        self,
        pool: vk.VkCommandPool,
        command_buffer: vk.VkCommandBuffer,
        queue_family_index: int
    ) -> None:
        """Track command buffer allocation."""
        if not self.config.enable_usage_tracking:
            return
            
        self._command_buffers[command_buffer] = CommandBufferState.INITIAL
        self._pool_buffer_map[pool].add(command_buffer)
        self._command_buffer_families[command_buffer] = queue_family_index
        self.stats.total_allocations += 1
        self.stats.current_active_buffers += 1
        
    def update_command_buffer_state(
        self,
        command_buffer: vk.VkCommandBuffer,
        new_state: CommandBufferState
    ) -> None:
        """Update command buffer state."""
        if not self.config.validate_command_buffer_state:
            return
            
        self._command_buffers[command_buffer] = new_state
        
        if new_state == CommandBufferState.EXECUTABLE:
            self.stats.submissions_performed += 1
            
        if new_state == CommandBufferState.INITIAL:
            self.stats.resets_performed += 1
            
    def track_command_buffer_destruction(self, command_buffer: vk.VkCommandBuffer) -> None:
        """Track command buffer destruction."""
        if command_buffer in self._command_buffers:
            del self._command_buffers[command_buffer]
            del self._command_buffer_families[command_buffer]
            self._render_pass_scope.pop(command_buffer, None)
            self.stats.current_active_buffers -= 1
            
    def track_command_pool_destruction(self, pool: vk.VkCommandPool) -> None:
        """Track command pool destruction."""
        if pool in self._command_pools:
            self._command_pools.remove(pool)
            if pool in self._pool_buffer_map:
                for cmd_buffer in self._pool_buffer_map[pool]:
                    self.track_command_buffer_destruction(cmd_buffer)
                del self._pool_buffer_map[pool]
            self.stats.current_active_pools -= 1
            
    def get_command_stats(self) -> CommandBufferUsageStats:
        """Get current command buffer usage statistics."""
        return self.stats
        
    def reset_stats(self) -> None:
        """Reset command buffer usage statistics."""
        self.stats = CommandBufferUsageStats()
        
    def cleanup(self) -> None:
        """Clean up validator resources."""
        self._command_pools.clear()
        self._command_buffers.clear()
        self._pool_buffer_map.clear()
        self._render_pass_scope.clear()
        self._command_buffer_families.clear()
        self.reset_stats()