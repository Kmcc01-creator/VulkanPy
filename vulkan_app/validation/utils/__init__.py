# validation/__init__.py

from .config import ValidationConfig
from .error_codes import ValidationErrorCode
from .error_handlers import ValidationErrorHandler
from .exceptions import ValidationError, VulkanValidationError
from .messages import get_validation_message
from .validators import (
    BaseValidator,
    BufferValidator,
    CommandValidator,
    DescriptorValidator,
    DeviceValidator,
    MemoryValidator,
    PipelineValidator,
    ShaderValidator
)

class ValidationSystem:
    """Main entry point for the validation system."""
    
    def __init__(self, validation_config: Optional[ValidationConfig] = None):
        self.config = validation_config or ValidationConfig()
        self.error_handler = ValidationErrorHandler()
        
        # Initialize all validators
        self.buffer_validator = None
        self.command_validator = None
        self.descriptor_validator = None
        self.device_validator = None
        self.memory_validator = None
        self.pipeline_validator = None
        self.shader_validator = None
        
    def initialize(self, context: ValidationContext) -> None:
        """Initialize the validation system with a Vulkan context."""
        self.buffer_validator = BufferValidator(context, self.config.buffer_config)
        self.command_validator = CommandValidator(context, self.config.command_config)
        self.descriptor_validator = DescriptorValidator(context, self.config.descriptor_config)
        self.device_validator = DeviceValidator(context, self.config.device_config)
        self.memory_validator = MemoryValidator(context, self.config.memory_config)
        self.pipeline_validator = PipelineValidator(context, self.config.pipeline_config)
        self.shader_validator = ShaderValidator(context, self.config.shader_config)
        
    def cleanup(self) -> None:
        """Clean up validation system resources."""
        for validator in [
            self.buffer_validator,
            self.command_validator,
            self.descriptor_validator,
            self.device_validator,
            self.memory_validator,
            self.pipeline_validator,
            self.shader_validator
        ]:
            if validator is not None:
                validator.cleanup()
                
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get combined validation statistics from all validators."""
        stats = {}
        if self.buffer_validator:
            stats['buffer'] = self.buffer_validator.get_buffer_stats()
        if self.command_validator:
            stats['command'] = self.command_validator.get_command_stats()
        if self.descriptor_validator:
            stats['descriptor'] = self.descriptor_validator.get_descriptor_stats()
        if self.device_validator:
            stats['device'] = self.device_validator.get_device_stats()
        if self.memory_validator:
            stats['memory'] = self.memory_validator.get_memory_stats()
        if self.pipeline_validator:
            stats['pipeline'] = self.pipeline_validator.get_pipeline_stats()
        if self.shader_validator:
            stats['shader'] = self.shader_validator.get_shader_stats()
        return stats
        
    def reset_stats(self) -> None:
        """Reset statistics for all validators."""
        for validator in [
            self.buffer_validator,
            self.command_validator,
            self.descriptor_validator,
            self.device_validator,
            self.memory_validator,
            self.pipeline_validator,
            self.shader_validator
        ]:
            if validator is not None:
                validator.reset_stats()

__all__ = [
    'ValidationSystem',
    'ValidationConfig',
    'ValidationErrorCode',
    'ValidationError',
    'VulkanValidationError',
    'get_validation_message',
    'BaseValidator',
    'BufferValidator',
    'CommandValidator',
    'DescriptorValidator',
    'DeviceValidator',
    'MemoryValidator',
    'PipelineValidator',
    'ShaderValidator'
]