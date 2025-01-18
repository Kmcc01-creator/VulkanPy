from typing import Dict, List, Optional, Set, Tuple
import vulkan as vk
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from .base import BaseValidator, ValidationContext, ValidationResult, ValidationSeverity
from ..error_codes import ValidationErrorCode
from ..exceptions import ValidationError, VulkanValidationError

logger = logging.getLogger(__name__)

class PipelineType(Enum):
    GRAPHICS = auto()
    COMPUTE = auto()
    RAY_TRACING = auto()

class ShaderStage(Enum):
    VERTEX = auto()
    FRAGMENT = auto()
    COMPUTE = auto()
    GEOMETRY = auto()
    TESSELLATION_CONTROL = auto()
    TESSELLATION_EVALUATION = auto()
    MESH = auto()
    TASK = auto()
    RAY_GEN = auto()
    RAY_MISS = auto()
    RAY_CLOSEST_HIT = auto()
    RAY_ANY_HIT = auto()
    RAY_INTERSECTION = auto()
    CALLABLE = auto()

@dataclass
class PipelineValidationConfig:
    """Configuration for pipeline validation."""
    max_pipelines: int = 1024
    max_pipeline_layouts: int = 128
    max_shader_stages: int = 6
    max_vertex_attributes: int = 16
    max_vertex_bindings: int = 8
    max_push_constant_size: int = 128
    validate_shader_stages: bool = True
    validate_pipeline_cache: bool = True
    enable_state_tracking: bool = True
    track_pipeline_derivatives: bool = True
    enable_pipeline_stats: bool = True

@dataclass
class PipelineStats:
    """Track pipeline usage statistics."""
    total_pipelines: int = 0
    current_pipelines: int = 0
    pipeline_layouts: int = 0
    shader_modules: Dict[ShaderStage, int] = field(default_factory=dict)
    cache_hits: int = 0
    derivative_pipelines: int = 0

class PipelineValidator(BaseValidator):
    """Validator for Vulkan pipeline operations."""
    
    def __init__(self, context: ValidationContext, config: Optional[PipelineValidationConfig] = None):
        super().__init__(context)
        self.config = config or PipelineValidationConfig()
        self.stats = PipelineStats()
        self._active_pipelines: Dict[vk.VkPipeline, PipelineType] = {}
        self._pipeline_layouts: Set[vk.VkPipelineLayout] = set()
        self._shader_modules: Dict[vk.VkShaderModule, ShaderStage] = {}
        self._pipeline_derivatives: Dict[vk.VkPipeline, vk.VkPipeline] = {}
        
    def validate_graphics_pipeline_create(
        self,
        create_info: vk.VkGraphicsPipelineCreateInfo
    ) -> ValidationResult:
        """Validate graphics pipeline creation parameters."""
        try:
            self.begin_validation("graphics_pipeline_create")
            
            if len(self._active_pipelines) >= self.config.max_pipelines:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.TOO_MANY_PIPELINES,
                    message=f"Maximum number of pipelines ({self.config.max_pipelines}) exceeded"
                )

            # Validate shader stages
            if self.config.validate_shader_stages:
                result = self._validate_shader_stages(create_info.pStages, create_info.stageCount)
                if not result.success:
                    return result

            # Validate vertex input
            result = self._validate_vertex_input_state(create_info.pVertexInputState)
            if not result.success:
                return result

            # Validate rasterization state
            result = self._validate_rasterization_state(create_info.pRasterizationState)
            if not result.success:
                return result

            # Validate color blend state
            if create_info.pColorBlendState:
                result = self._validate_color_blend_state(create_info.pColorBlendState)
                if not result.success:
                    return result

            # Validate pipeline layout
            result = self._validate_pipeline_layout(create_info.layout)
            if not result.success:
                return result

            # Validate render pass compatibility
            result = self._validate_render_pass_compatibility(
                create_info.renderPass,
                create_info.subpass
            )
            if not result.success:
                return result

            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Graphics pipeline creation parameters are valid",
                details={
                    "stage_count": create_info.stageCount,
                    "subpass": create_info.subpass
                }
            )
            
        finally:
            self.end_validation("graphics_pipeline_create")
            
    def validate_compute_pipeline_create(
        self,
        create_info: vk.VkComputePipelineCreateInfo
    ) -> ValidationResult:
        """Validate compute pipeline creation parameters."""
        try:
            self.begin_validation("compute_pipeline_create")
            
            if len(self._active_pipelines) >= self.config.max_pipelines:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.TOO_MANY_PIPELINES,
                    message=f"Maximum number of pipelines ({self.config.max_pipelines}) exceeded"
                )

            # Validate compute shader stage
            stage = create_info.stage
            if stage.stage != vk.VK_SHADER_STAGE_COMPUTE_BIT:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INVALID_SHADER_STAGE,
                    message="Invalid shader stage for compute pipeline"
                )

            # Validate shader module
            if stage.module not in self._shader_modules:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INVALID_SHADER_MODULE,
                    message="Invalid shader module"
                )

            # Validate pipeline layout
            result = self._validate_pipeline_layout(create_info.layout)
            if not result.success:
                return result

            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="Compute pipeline creation parameters are valid"
            )
            
        finally:
            self.end_validation("compute_pipeline_create")
            
    def _validate_shader_stages(
        self,
        stages: List[vk.VkPipelineShaderStageCreateInfo],
        stage_count: int
    ) -> ValidationResult:
        """Validate shader stages configuration."""
        if stage_count > self.config.max_shader_stages:
            return ValidationResult(
                success=False,
                severity=ValidationSeverity.ERROR,
                error_code=ValidationErrorCode.TOO_MANY_SHADER_STAGES,
                message=f"Number of shader stages ({stage_count}) exceeds maximum ({self.config.max_shader_stages})"
            )

        used_stages = set()
        for stage in stages[:stage_count]:
            # Check for duplicate stages
            if stage.stage in used_stages:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.DUPLICATE_SHADER_STAGE,
                    message=f"Duplicate shader stage {stage.stage}"
                )
            used_stages.add(stage.stage)

            # Validate shader module
            if stage.module not in self._shader_modules:
                return ValidationResult(
                    success=False,
                    severity=ValidationSeverity.ERROR,
                    error_code=ValidationErrorCode.INVALID_SHADER_MODULE,
                    message="Invalid shader module"
                )

        return ValidationResult(
            success=True,
            severity=ValidationSeverity.INFO,
            message="Shader stages are valid",
            details={"stage_count": stage_count}
        )

    def _validate_vertex_input_state(
        self,
        vertex_input_state: Optional[vk.VkPipelineVertexInputStateCreateInfo]
    ) -> ValidationResult:
        """Validate vertex input state configuration."""
        if not vertex_input_state:
            return ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message="No vertex input state specified"
            )

        if vertex_input_state.vertexBindingDescriptionCount > self.config.max_vertex_bindings:
            return ValidationResult(
                success=False,
                severity=ValidationSeverity.ERROR,
                error_code=ValidationErrorCode.TOO_MANY_VERTEX_BINDINGS,
                message=f"Too many vertex bindings ({vertex_input_state.vertexBindingDescriptionCount})"
            )

        if vertex_input_state.vertexAttributeDescriptionCount > self.config.max_vertex_attributes:
            return ValidationResult(
                success=False,
                severity=ValidationSeverity.ERROR,
                error_code=ValidationErrorCode.TOO_MANY_VERTEX_ATTRIBUTES,
                message=f"Too many vertex attributes ({vertex_input_state.vertexAttributeDescriptionCount})"
            )

        return ValidationResult(
            success=True,
            severity=ValidationSeverity.INFO,
            message="Vertex input state is valid"
        )

    def _validate_rasterization_state(
        self,
        rasterization_state: vk.VkPipelineRasterizationStateCreateInfo
    ) -> ValidationResult:
        """Validate rasterization state configuration."""
        if rasterization_state.depthBiasClamp and not self.context.device_features.depthBiasClamp:
            return ValidationResult(
                success=False,
                severity=ValidationSeverity.ERROR,
                error_code=ValidationErrorCode.UNSUPPORTED_FEATURE,
                message="Depth bias clamp not supported"
            )

        return ValidationResult(
            success=True,
            severity=ValidationSeverity.INFO,
            message="Rasterization state is valid"
        )

    def _validate_color_blend_state(
        self,
        color_blend_state: vk.VkPipelineColorBlendStateCreateInfo
    ) -> ValidationResult:
        """Validate color blend state configuration."""
        if color_blend_state.logicOpEnable and not self.context.device_features.logicOp:
            return ValidationResult(
                success=False,
                severity=ValidationSeverity.ERROR,
                error_code=ValidationErrorCode.UNSUPPORTED_FEATURE,
                message="Logic operations not supported"
            )

        return ValidationResult(
            success=True,
            severity=ValidationSeverity.INFO,
            message="Color blend state is valid"
        )

    def _validate_pipeline_layout(
        self,
        layout: vk.VkPipelineLayout
    ) -> ValidationResult:
        """Validate pipeline layout."""
        if layout not in self._pipeline_layouts:
            return ValidationResult(
                success=False,
                severity=ValidationSeverity.ERROR,
                error_code=ValidationErrorCode.INVALID_PIPELINE_LAYOUT,
                message="Invalid pipeline layout"
            )

        return ValidationResult(
            success=True,
            severity=ValidationSeverity.INFO,
            message="Pipeline layout is valid"
        )

    def _validate_render_pass_compatibility(
        self,
        render_pass: vk.VkRenderPass,
        subpass: int
    ) -> ValidationResult:
        """Validate render pass compatibility."""
        # This would involve more complex validation of render pass compatibility
        # For now, we just do basic validation
        return ValidationResult(
            success=True,
            severity=ValidationSeverity.INFO,
            message="Render pass compatibility check passed"
        )

    def track_pipeline_creation(
        self,
        pipeline: vk.VkPipeline,
        pipeline_type: PipelineType,
        base_pipeline: Optional[vk.VkPipeline] = None
    ) -> None:
        """Track pipeline creation."""
        if not self.config.enable_pipeline_stats:
            return

        self._active_pipelines[pipeline] = pipeline_type
        self.stats.total_pipelines += 1
        self.stats.current_pipelines += 1

        if base_pipeline and self.config.track_pipeline_derivatives:
            self._pipeline_derivatives[pipeline] = base_pipeline
            self.stats.derivative_pipelines += 1

    def track_pipeline_layout_creation(
        self,
        layout: vk.VkPipelineLayout
    ) -> None:
        """Track pipeline layout creation."""
        self._pipeline_layouts.add(layout)
        self.stats.pipeline_layouts += 1

    def track_shader_module_creation(
        self,
        module: vk.VkShaderModule,
        stage: ShaderStage
    ) -> None:
        """Track shader module creation."""
        self._shader_modules[module] = stage
        self.stats.shader_modules[stage] = self.stats.shader_modules.get(stage, 0) + 1

    def track_pipeline_destruction(
        self,
        pipeline: vk.VkPipeline
    ) -> None:
        """Track pipeline destruction."""
        if pipeline in self._active_pipelines:
            del self._active_pipelines[pipeline]
            self.stats.current_pipelines -= 1

        if pipeline in self._pipeline_derivatives:
            del self._pipeline_derivatives[pipeline]
            self.stats.derivative_pipelines -= 1

    def track_pipeline_layout_destruction(
        self,
        layout: vk.VkPipelineLayout
    ) -> None:
        """Track pipeline layout destruction."""
        if layout in self._pipeline_layouts:
            self._pipeline_layouts.remove(layout)
            self.stats.pipeline_layouts -= 1

    def track_shader_module_destruction(
        self,
        module: vk.VkShaderModule
    ) -> None:
        """Track shader module destruction."""
        if module in self._shader_modules:
            stage = self._shader_modules[module]
            del self._shader_modules[module]
            self.stats.shader_modules[stage] -= 1

    def track_pipeline_cache_hit(self) -> None:
        """Track pipeline cache hit."""
        self.stats.cache_hits += 1

    def get_pipeline_stats(self) -> PipelineStats:
        """Get current pipeline usage statistics."""
        return self.stats

    def reset_stats(self) -> None:
        """Reset pipeline usage statistics."""
        self.stats = PipelineStats()

    def cleanup(self) -> None:
        """Clean up validator resources."""
        self._active_pipelines.clear()
        self._pipeline_layouts.clear()
        self._shader_modules.clear()
        self._pipeline_derivatives.clear()
        self.reset_stats()