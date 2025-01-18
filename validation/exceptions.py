# validation/exceptions.py

from typing import Dict, Any, Optional
import traceback
from dataclasses import dataclass, field
from enum import Enum, auto
from .error_codes import ValidationErrorCode

class ValidationSeverity(Enum):
    """Severity levels for validation exceptions."""
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()

@dataclass
class ValidationErrorInfo:
    """Detailed information about a validation error."""
    code: ValidationErrorCode
    component: str
    operation: str
    timestamp: float
    call_stack: str = field(default_factory=lambda: traceback.format_stack())
    validation_context: Dict[str, Any] = field(default_factory=dict)
    object_handles: Dict[str, int] = field(default_factory=dict)
    severity: ValidationSeverity = ValidationSeverity.ERROR

    def to_dict(self) -> Dict[str, Any]:
        """Convert error info to a dictionary."""
        return {
            'code': self.code.value,
            'code_name': self.code.name,
            'component': self.component,
            'operation': self.operation,
            'timestamp': self.timestamp,
            'call_stack': self.call_stack,
            'validation_context': self.validation_context,
            'object_handles': self.object_handles,
            'severity': self.severity.name
        }

class ValidationError(Exception):
    """Base exception for validation errors."""
    
    def __init__(
        self,
        message: str,
        code: ValidationErrorCode,
        error_info: Optional[ValidationErrorInfo] = None,
        **kwargs
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.error_info = error_info
        self.additional_info = kwargs

    def __str__(self) -> str:
        base_message = f"[{self.code.name}] {self.message}"
        if self.error_info:
            return f"{base_message} (in {self.error_info.component}.{self.error_info.operation})"
        return base_message

    def get_details(self) -> Dict[str, Any]:
        """Get detailed error information."""
        details = {
            'message': self.message,
            'code': self.code.value,
            'code_name': self.code.name,
            'additional_info': self.additional_info
        }
        
        if self.error_info:
            details['error_info'] = self.error_info.to_dict()
            
        return details

class VulkanValidationError(ValidationError):
    """Exception for Vulkan-specific validation errors."""
    
    def __init__(
        self,
        message: str,
        code: ValidationErrorCode,
        vk_result: int,
        error_info: Optional[ValidationErrorInfo] = None,
        **kwargs
    ):
        super().__init__(message, code, error_info, **kwargs)
        self.vk_result = vk_result

    def __str__(self) -> str:
        return f"{super().__str__()} (Vulkan result: {self.vk_result})"

class ResourceValidationError(ValidationError):
    """Exception for resource-related validation errors."""
    
    def __init__(
        self,
        message: str,
        code: ValidationErrorCode,
        resource_type: str,
        resource_handle: Optional[int] = None,
        error_info: Optional[ValidationErrorInfo] = None,
        **kwargs
    ):
        super().__init__(message, code, error_info, **kwargs)
        self.resource_type = resource_type
        self.resource_handle = resource_handle

    def __str__(self) -> str:
        handle_info = f" (handle: {hex(self.resource_handle)})" if self.resource_handle else ""
        return f"{super().__str__()} [{self.resource_type}]{handle_info}"

class ShaderValidationError(ValidationError):
    """Exception for shader-related validation errors."""
    
    def __init__(
        self,
        message: str,
        code: ValidationErrorCode,
        shader_stage: str,
        shader_source: Optional[str] = None,
        error_info: Optional[ValidationErrorInfo] = None,
        **kwargs
    ):
        super().__init__(message, code, error_info, **kwargs)
        self.shader_stage = shader_stage
        self.shader_source = shader_source

    def __str__(self) -> str:
        return f"{super().__str__()} [Stage: {self.shader_stage}]"

class MemoryValidationError(ValidationError):
    """Exception for memory-related validation errors."""
    
    def __init__(
        self,
        message: str,
        code: ValidationErrorCode,
        allocation_size: int,
        memory_type: int,
        error_info: Optional[ValidationErrorInfo] = None,
        **kwargs
    ):
        super().__init__(message, code, error_info, **kwargs)
        self.allocation_size = allocation_size
        self.memory_type = memory_type

    def __str__(self) -> str:
        return f"{super().__str__()} [Size: {self.allocation_size}, Type: {self.memory_type}]"

class CommandValidationError(ValidationError):
    """Exception for command-related validation errors."""
    
    def __init__(
        self,
        message: str,
        code: ValidationErrorCode,
        command_type: str,
        queue_family: Optional[int] = None,
        error_info: Optional[ValidationErrorInfo] = None,
        **kwargs
    ):
        super().__init__(message, code, error_info, **kwargs)
        self.command_type = command_type
        self.queue_family = queue_family

    def __str__(self) -> str:
        queue_info = f", Queue Family: {self.queue_family}" if self.queue_family is not None else ""
        return f"{super().__str__()} [Command: {self.command_type}{queue_info}]"

class PipelineValidationError(ValidationError):
    """Exception for pipeline-related validation errors."""
    
    def __init__(
        self,
        message: str,
        code: ValidationErrorCode,
        pipeline_type: str,
        shader_stages: List[str],
        error_info: Optional[ValidationErrorInfo] = None,
        **kwargs
    ):
        super().__init__(message, code, error_info, **kwargs)
        self.pipeline_type = pipeline_type
        self.shader_stages = shader_stages

    def __str__(self) -> str:
        stages = ", ".join(self.shader_stages)
        return f"{super().__str__()} [Pipeline: {self.pipeline_type}, Stages: {stages}]"

class ValidationWarning(ValidationError):
    """Exception for validation warnings."""
    
    def __init__(
        self,
        message: str,
        code: ValidationErrorCode,
        error_info: Optional[ValidationErrorInfo] = None,
        **kwargs
    ):
        error_info = error_info or ValidationErrorInfo(
            code=code,
            component="unknown",
            operation="unknown",
            timestamp=0.0,
            severity=ValidationSeverity.WARNING
        )
        super().__init__(message, code, error_info, **kwargs)

    def __str__(self) -> str:
        return f"Warning: {super().__str__()}"

def create_validation_error(
    code: ValidationErrorCode,
    message: str,
    component: str,
    operation: str,
    **kwargs
) -> ValidationError:
    """Factory function to create appropriate validation exception."""
    error_info = ValidationErrorInfo(
        code=code,
        component=component,
        operation=operation,
        timestamp=time.time(),
        validation_context=kwargs.get('context', {}),
        object_handles=kwargs.get('handles', {})
    )

    category = ValidationErrorCode.get_category(code)
    if category == "Memory":
        return MemoryValidationError(message, code, error_info=error_info, **kwargs)
    elif category == "Shader":
        return ShaderValidationError(message, code, error_info=error_info, **kwargs)
    elif category == "Resource":
        return ResourceValidationError(message, code, error_info=error_info, **kwargs)
    elif category == "Command":
        return CommandValidationError(message, code, error_info=error_info, **kwargs)
    elif category == "Pipeline":
        return PipelineValidationError(message, code, error_info=error_info, **kwargs)
    elif category == "Performance":
        return ValidationWarning(message, code, error_info=error_info, **kwargs)
    else:
        return ValidationError(message, code, error_info=error_info, **kwargs)