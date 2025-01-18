from typing import Dict, List, Optional, Set, Tuple
import vulkan as vk
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from .base import BaseValidator, ValidationContext, ValidationResult, ValidationSeverity
from ..error_codes import ValidationErrorCode
from ..exceptions import ValidationError, VulkanValidationError

logger = logging.getLogger(__name__)

class ShaderStage(Enum):
    """Supported shader stages."""
    VERTEX = auto()
    FRAGMENT = auto()
    COMPUTE = auto()
    GEOMETRY = auto()
    TESSELLATION_CONTROL = auto()
    TESSELLATION_EVALUATION = auto()
    MESH = auto()
    TASK = auto()

@dataclass
class ShaderResourceLimits:
    """Resource limits for shader validation."""
    max_push_constants_size: int = 128
    max_uniform_buffers: int = 8
    max_storage_buffers: int = 4
    max_sampled_images: int = 16
    max_storage_images: int = 8
    max_input_attachments: int = 4
    max_output_attachments: int = 4

@dataclass
class ShaderValidationConfig:
    """Configuration for shader validation."""
    validate_spirv: bool = True
    validate_resource_usage: bool = True
    validate_entry_points: bool = True
    enable_debug_info: bool = True
    track_shader_usage: bool = True
    max_shader_modules: int = 1024
    resource_limits: ShaderResourceLimits = field(default_factory=ShaderResourceLimits)

@dataclass
class ShaderResource:
    """Represents a shader resource."""
    binding: int
    descriptor_type: int
    array_size: int = 1
    stages: int = 0
    name: Optional[str] = None

@dataclass
class ShaderStats:
    """Track shader usage statistics."""
    total_modules: int = 0
    current_modules: int = 0
    module_sizes: Dict[ShaderStage, int] = field(default_factory=dict)
    resource_usage: Dict[str, int] = field(default_factory=dict)
    compilation_errors: int = 0
    validation_errors: int = 0

class ShaderValidator(BaseValidator):
    """Validator for shader operations."""
    
    def __init__(self, context: ValidationContext, config: Optional[ShaderValidationConfig] = None):
        super().__init__(context)
        self.config = config or ShaderValidationConfig()
        self.stats = ShaderStats()
        self._active_modules: Dict[vk.VkShaderModule, ShaderStage] = {}
        self._module_resources: Dict[vk.VkShaderModule, List[ShaderResource]] = {}
        self._module_entry_points: Dict[vk.VkShaderModule, Set[str]] = {}
        self._module_sizes: Dict[vk.VkShaderModule, int] = {}

    def validate_shader_module_create(
        self,
        create_info: vk.VkShaderModuleCreateInfo,
        stage: ShaderStage
    ) -> ValidationResult:
        """Validate shader module creation parameters."""
        try:
            self.begin_validation("shader_module_create")
            
            if len(self._active_modules) >= self.config.max_shader_modules:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.TOO_MANY_SHADER_MODULES,
                    message=f"Maximum number of shader modules ({self.config.max_shader_modules}) exceeded"
                )

            # Validate SPIR-V code
            if self.config.validate_spirv:
                result = self._validate_spirv_code(create_info.pCode, create_info.codeSize)
                if not result.success:
                    self.stats.validation_errors += 1
                    return result

            # Validate shader resources
            if self.config.validate_resource_usage:
                result = self._validate_shader_resources(create_info.pCode, create_info.codeSize, stage)
                if not result.success:
                    self.stats.validation_errors += 1
                    return result

            # Validate entry points
            if self.config.validate_entry_points:
                result = self._validate_entry_points(create_info.pCode, create_info.codeSize)
                if not result.success:
                    self.stats.validation_errors += 1
                    return result

            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Shader module creation parameters are valid",
                details={
                    "stage": stage.name,
                    "code_size": create_info.codeSize
                }
            )

        finally:
            self.end_validation("shader_module_create")

    def _validate_spirv_code(self, code: bytes, size: int) -> ValidationResult:
        """Validate SPIR-V code format and structure."""
        # Basic SPIR-V validation
        if size % 4 != 0:
            return ValidationResult(
                success=False,
                severity=ValidationSeverity.ERROR,
                error_code=ValidationErrorCode.INVALID_SPIRV_SIZE,
                message="SPIR-V code size must be a multiple of 4"
            )

        # Check SPIR-V magic number
        if len(code) < 4 or int.from_bytes(code[:4], byteorder='little') != 0x07230203:
            return ValidationResult(
                success=False,
                severity=ValidationSeverity.ERROR,
                error_code=ValidationErrorCode.INVALID_SPIRV_MAGIC,
                message="Invalid SPIR-V magic number"
            )

        return ValidationResult(
            success=True,
            severity=ValidationSeverity.INFO,
            message="SPIR-V code validation passed"
        )

    def _validate_shader_resources(
        self,
        code: bytes,
        size: int,
        stage: ShaderStage
    ) -> ValidationResult:
        """Validate shader resource usage."""
        try:
            # Parse SPIR-V resource declarations
            resources = self._parse_shader_resources(code)
            
            # Check resource limits
            resource_counts = {
                vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER: 0,
                vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER: 0,
                vk.VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER: 0,
                vk.VK_DESCRIPTOR_TYPE_STORAGE_IMAGE: 0,
                vk.VK_DESCRIPTOR_TYPE_INPUT_ATTACHMENT: 0
            }

            for resource in resources:
                resource_counts[resource.descriptor_type] += resource.array_size

            # Validate against limits
            if resource_counts[vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER] > self.config.resource_limits.max_uniform_buffers:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.TOO_MANY_UNIFORM_BUFFERS,
                    message=f"Too many uniform buffers ({resource_counts[vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER]})"
                )

            if resource_counts[vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER] > self.config.resource_limits.max_storage_buffers:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.TOO_MANY_STORAGE_BUFFERS,
                    message=f"Too many storage buffers ({resource_counts[vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER]})"
                )

            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Shader resource validation passed",
                details={"resource_counts": resource_counts}
            )

        except Exception as e:
            logger.error(f"Error validating shader resources: {e}")
            return ValidationResult(
                success=False,
                severity=ValidationSeverity.ERROR,
                error_code=ValidationErrorCode.RESOURCE_VALIDATION_ERROR,
                message=f"Error validating shader resources: {str(e)}"
            )

    def _validate_entry_points(self, code: bytes, size: int) -> ValidationResult:
        """Validate shader entry points."""
        try:
            # Parse SPIR-V entry points
            entry_points = self._parse_entry_points(code)
            
            if not entry_points:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.NO_ENTRY_POINT,
                    message="No entry point found in shader module"
                )

            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Entry point validation passed",
                details={"entry_points": list(entry_points)}
            )

        except Exception as e:
            logger.error(f"Error validating entry points: {e}")
            return ValidationResult(
                success=False,
                severity=ValidationSeverity.ERROR,
                error_code=ValidationErrorCode.ENTRY_POINT_VALIDATION_ERROR,
                message=f"Error validating entry points: {str(e)}"
            )

    def _parse_shader_resources(self, code: bytes) -> List[ShaderResource]:
        """Parse shader resources from SPIR-V code."""
        # This would be implemented using a SPIR-V parser
        # For now, return a placeholder implementation
        return []

    def _parse_entry_points(self, code: bytes) -> Set[str]:
        """Parse entry points from SPIR-V code."""
        # This would be implemented using a SPIR-V parser
        # For now, return a placeholder implementation
        return {"main"}

    def track_shader_module_creation(
        self,
        module: vk.VkShaderModule,
        stage: ShaderStage,
        code_size: int,
        resources: Optional[List[ShaderResource]] = None
    ) -> None:
        """Track shader module creation."""
        if not self.config.track_shader_usage:
            return

        self._active_modules[module] = stage
        self._module_sizes[module] = code_size
        if resources:
            self._module_resources[module] = resources

        self.stats.total_modules += 1
        self.stats.current_modules += 1
        self.stats.module_sizes[stage] = self.stats.module_sizes.get(stage, 0) + code_size

    def track_shader_module_destruction(
        self,
        module: vk.VkShaderModule
    ) -> None:
        """Track shader module destruction."""
        if module in self._active_modules:
            stage = self._active_modules[module]
            size = self._module_sizes.get(module, 0)
            
            del self._active_modules[module]
            self._module_sizes.pop(module, None)
            self._module_resources.pop(module, None)
            self._module_entry_points.pop(module, None)

            self.stats.current_modules -= 1
            self.stats.module_sizes[stage] -= size

    def track_compilation_error(self) -> None:
        """Track shader compilation error."""
        self.stats.compilation_errors += 1

    def track_resource_usage(self, resource_type: str) -> None:
        """Track shader resource usage."""
        self.stats.resource_usage[resource_type] = \
            self.stats.resource_usage.get(resource_type, 0) + 1

    def get_shader_stats(self) -> ShaderStats:
        """Get current shader usage statistics."""
        return self.stats

    def reset_stats(self) -> None:
        """Reset shader usage statistics."""
        self.stats = ShaderStats()

    def cleanup(self) -> None:
        """Clean up validator resources."""
        self._active_modules.clear()
        self._module_resources.clear()
        self._module_entry_points.clear()
        self._module_sizes.clear()
        self.reset_stats()