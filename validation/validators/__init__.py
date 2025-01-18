# validation/validators/__init__.py

from .base import (
    BaseValidator,
    ValidationContext,
    ValidationResult,
    ValidationSeverity
)
from .buffer import (
    BufferValidator,
    BufferValidationConfig,
    BufferStats,
    BufferType,
    BufferUsage
)
from .command import (
    CommandValidator,
    CommandValidationConfig,
    CommandBufferStats,
    CommandState,
    CommandScope
)
from .descriptor import (
    DescriptorValidator,
    DescriptorValidationConfig,
    DescriptorStats,
    DescriptorType
)
from .device import (
    DeviceValidator,
    DeviceValidationConfig,
    DeviceStats,
    DeviceRequirements
)
from .memory import (
    MemoryValidator,
    MemoryValidationConfig,
    MemoryStats,
    MemoryType,
    MemoryBlock,
    MemoryRange,
    MemoryAllocationScope
)
from .pipeline import (
    PipelineValidator,
    PipelineValidationConfig,
    PipelineStats,
    PipelineType
)
from .shader import (
    ShaderValidator,
    ShaderValidationConfig,
    ShaderStats,
    ShaderStage,
    ShaderResource,
    ShaderResourceLimits
)

__all__ = [
    # Base validation
    'BaseValidator',
    'ValidationContext',
    'ValidationResult',
    'ValidationSeverity',
    
    # Buffer validation
    'BufferValidator',
    'BufferValidationConfig',
    'BufferStats',
    'BufferType',
    'BufferUsage',
    
    # Command validation
    'CommandValidator',
    'CommandValidationConfig',
    'CommandBufferStats',
    'CommandState',
    'CommandScope',
    
    # Descriptor validation
    'DescriptorValidator',
    'DescriptorValidationConfig',
    'DescriptorStats',
    'DescriptorType',
    
    # Device validation
    'DeviceValidator',
    'DeviceValidationConfig',
    'DeviceStats',
    'DeviceRequirements',
    
    # Memory validation
    'MemoryValidator',
    'MemoryValidationConfig',
    'MemoryStats',
    'MemoryType',
    'MemoryBlock',
    'MemoryRange',
    'MemoryAllocationScope',
    
    # Pipeline validation
    'PipelineValidator',
    'PipelineValidationConfig',
    'PipelineStats',
    'PipelineType',
    
    # Shader validation
    'ShaderValidator',
    'ShaderValidationConfig',
    'ShaderStats',
    'ShaderStage',
    'ShaderResource',
    'ShaderResourceLimits'
]

# Version info
__version__ = '1.0.0'
__author__ = 'Your Name'
__all__ += ['__version__', '__author__']

# Optional debugging tools for development
def enable_validation_debug():
    """Enable debug logging for all validators."""
    import logging
    logging.getLogger('validation').setLevel(logging.DEBUG)

def disable_validation_debug():
    """Disable debug logging for all validators."""
    import logging
    logging.getLogger('validation').setLevel(logging.INFO)

__all__ += ['enable_validation_debug', 'disable_validation_debug']