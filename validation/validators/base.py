from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
import logging
from enum import Enum, auto
import vulkan as vk
from ..error_codes import ValidationErrorCode
from ..exceptions import ValidationError, VulkanValidationError

logger = logging.getLogger(__name__)

class ValidationSeverity(Enum):
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    FATAL = auto()

@dataclass
class ValidationContext:
    """Context information for validation operations."""
    device: Optional[vk.VkDevice] = None
    physical_device: Optional[vk.VkPhysicalDevice] = None
    instance: Optional[vk.VkInstance] = None
    validation_layers_enabled: bool = True
    debug_markers_enabled: bool = True
    custom_properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ValidationResult:
    """Result of a validation operation."""
    success: bool
    severity: ValidationSeverity
    error_code: Optional[ValidationErrorCode] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    child_results: List['ValidationResult'] = field(default_factory=list)

class BaseValidator:
    """Base class for all validators in the system."""
    
    def __init__(self, context: ValidationContext):
        self.context = context
        self.validation_stack: List[str] = []
        self._active_validations: Set[str] = set()
        self._validation_results: Dict[str, ValidationResult] = {}
        
    def begin_validation(self, name: str) -> None:
        """Begin a new validation scope."""
        if name in self._active_validations:
            raise ValidationError(f"Validation '{name}' is already active")
        
        self._active_validations.add(name)
        self.validation_stack.append(name)
        logger.debug(f"Beginning validation: {name}")
        
    def end_validation(self, name: str) -> ValidationResult:
        """End a validation scope and return its result."""
        if name not in self._active_validations:
            raise ValidationError(f"Validation '{name}' is not active")
            
        if name != self.validation_stack[-1]:
            raise ValidationError(
                f"Validation end mismatch. Expected {self.validation_stack[-1]}, got {name}"
            )
            
        self._active_validations.remove(name)
        self.validation_stack.pop()
        result = self._validation_results.pop(name, None)
        
        if result is None:
            result = ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message=f"Validation {name} completed with no issues"
            )
            
        logger.debug(f"Ending validation: {name} (success={result.success})")
        return result
        
    def validate(self, validation_name: str) -> bool:
        """Template method for validation implementations."""
        try:
            self.begin_validation(validation_name)
            result = self._perform_validation()
            self._validation_results[validation_name] = result
            return result.success
        except VulkanValidationError as e:
            self._handle_vulkan_error(validation_name, e)
            return False
        except Exception as e:
            self._handle_unexpected_error(validation_name, e)
            return False
        finally:
            if validation_name in self._active_validations:
                self.end_validation(validation_name)
                
    def _perform_validation(self) -> ValidationResult:
        """Override this method in derived validator classes."""
        raise NotImplementedError("Derived validators must implement _perform_validation")
        
    def add_validation_result(self, name: str, result: ValidationResult) -> None:
        """Add a validation result to the current validation scope."""
        if not self.validation_stack:
            raise ValidationError("No active validation scope")
            
        current_validation = self.validation_stack[-1]
        current_result = self._validation_results.get(current_validation)
        
        if current_result is None:
            current_result = ValidationResult(
                success=True,
                severity=ValidationSeverity.INFO,
                message=f"Validation group: {current_validation}"
            )
            self._validation_results[current_validation] = current_result
            
        current_result.child_results.append(result)
        
        # Update parent result based on child result
        if not result.success:
            current_result.success = False
            if result.severity.value > current_result.severity.value:
                current_result.severity = result.severity
                
    def _handle_vulkan_error(self, validation_name: str, error: VulkanValidationError) -> None:
        """Handle Vulkan-specific validation errors."""
        result = ValidationResult(
            success=False,
            severity=ValidationSeverity.ERROR,
            error_code=error.error_code,
            message=str(error),
            details={"vulkan_error": True}
        )
        self._validation_results[validation_name] = result
        logger.error(f"Vulkan validation error in {validation_name}: {error}")
        
    def _handle_unexpected_error(self, validation_name: str, error: Exception) -> None:
        """Handle unexpected errors during validation."""
        result = ValidationResult(
            success=False,
            severity=ValidationSeverity.FATAL,
            error_code=ValidationErrorCode.UNEXPECTED_ERROR,
            message=f"Unexpected error during validation: {str(error)}",
            details={"exception_type": type(error).__name__}
        )
        self._validation_results[validation_name] = result
        logger.error(f"Unexpected error in {validation_name}: {error}", exc_info=True)
        
    @property
    def current_validation(self) -> Optional[str]:
        """Get the name of the currently active validation scope."""
        return self.validation_stack[-1] if self.validation_stack else None
        
    def get_result(self, validation_name: str) -> Optional[ValidationResult]:
        """Get the result of a specific validation."""
        return self._validation_results.get(validation_name)
        
    def has_active_validations(self) -> bool:
        """Check if there are any active validation scopes."""
        return bool(self._active_validations)
        
    def reset(self) -> None:
        """Reset the validator state."""
        self.validation_stack.clear()
        self._active_validations.clear()
        self._validation_results.clear()
        
    @contextmanager
    def validation_scope(self, name: str):
        """Context manager for validation scopes."""
        self.begin_validation(name)
        try:
            yield
        finally:
            self.end_validation(name)