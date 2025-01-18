from typing import Dict, List, Optional, Callable, Any
import logging
from enum import Enum, auto
from dataclasses import dataclass, field
import traceback
import threading
from queue import Queue
from .error_codes import ValidationErrorCode, ValidationMessage
from .exceptions import ValidationError, VulkanValidationError

logger = logging.getLogger(__name__)

class ErrorHandlingStrategy(Enum):
    """Defines how errors should be handled."""
    RAISE = auto()  # Raise exceptions immediately
    COLLECT = auto()  # Collect errors for later processing
    LOG_ONLY = auto()  # Only log errors
    CALLBACK = auto()  # Call error callback function
    HYBRID = auto()  # Combination of strategies based on error severity

@dataclass
class ErrorContext:
    """Context information for validation errors."""
    component: str
    operation: str
    timestamp: float
    call_stack: str
    validation_context: Dict[str, Any] = field(default_factory=dict)
    object_handles: Dict[str, int] = field(default_factory=dict)

@dataclass
class ValidationError:
    """Detailed validation error information."""
    code: ValidationErrorCode
    message: str
    context: ErrorContext
    severity: str
    is_warning: bool = False
    error_count: int = 1  # For aggregating similar errors

class ErrorCollector:
    """Collects and manages validation errors."""
    
    def __init__(self, max_errors: int = 1000):
        self.max_errors = max_errors
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []
        self._error_counts: Dict[ValidationErrorCode, int] = {}
        self._lock = threading.Lock()
        
    def add_error(self, error: ValidationError) -> None:
        """Add an error to the collection."""
        with self._lock:
            if error.is_warning:
                self.warnings.append(error)
            else:
                if len(self.errors) < self.max_errors:
                    self.errors.append(error)
                self._error_counts[error.code] = self._error_counts.get(error.code, 0) + 1
                
    def clear(self) -> None:
        """Clear all collected errors."""
        with self._lock:
            self.errors.clear()
            self.warnings.clear()
            self._error_counts.clear()
            
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return bool(self.errors)
        
    def get_error_summary(self) -> Dict[ValidationErrorCode, int]:
        """Get a summary of error counts by error code."""
        return dict(self._error_counts)

class ErrorCallback:
    """Manages error callback functions."""
    
    def __init__(self):
        self._callbacks: Dict[str, Callable] = {}
        self._error_queue: Queue = Queue()
        self._is_processing = False
        self._lock = threading.Lock()
        
    def register_callback(self, name: str, callback: Callable) -> None:
        """Register an error callback function."""
        with self._lock:
            self._callbacks[name] = callback
            
    def unregister_callback(self, name: str) -> None:
        """Unregister an error callback function."""
        with self._lock:
            self._callbacks.pop(name, None)
            
    def notify_error(self, error: ValidationError) -> None:
        """Notify all registered callbacks of an error."""
        self._error_queue.put(error)
        self._process_queue()
        
    def _process_queue(self) -> None:
        """Process queued errors."""
        if self._is_processing:
            return
            
        with self._lock:
            self._is_processing = True
            
        try:
            while not self._error_queue.empty():
                error = self._error_queue.get_nowait()
                for callback in self._callbacks.values():
                    try:
                        callback(error)
                    except Exception as e:
                        logger.error(f"Error in callback: {e}")
        finally:
            self._is_processing = False

class ValidationErrorHandler:
    """Main error handler for the validation system."""
    
    def __init__(self, strategy: ErrorHandlingStrategy = ErrorHandlingStrategy.HYBRID):
        self.strategy = strategy
        self.collector = ErrorCollector()
        self.callback_manager = ErrorCallback()
        self.error_threshold = ValidationErrorCode.VALIDATION_ERROR
        self._enabled = True
        
    def handle_error(
        self,
        code: ValidationErrorCode,
        message: str,
        context: Dict[str, Any],
        component: str,
        operation: str
    ) -> None:
        """Handle a validation error."""
        if not self._enabled:
            return
            
        error_context = ErrorContext(
            component=component,
            operation=operation,
            timestamp=time.time(),
            call_stack=traceback.format_stack(),
            validation_context=context
        )
        
        error = ValidationError(
            code=code,
            message=message,
            context=error_context,
            severity=self._get_severity(code),
            is_warning=not ValidationErrorCode.is_error(code)
        )
        
        self._handle_error_by_strategy(error)
        
    def _handle_error_by_strategy(self, error: ValidationError) -> None:
        """Handle error according to the current strategy."""
        if self.strategy == ErrorHandlingStrategy.RAISE:
            if not error.is_warning:
                raise ValidationError(error.message, error.code, error.context)
                
        elif self.strategy == ErrorHandlingStrategy.COLLECT:
            self.collector.add_error(error)
            
        elif self.strategy == ErrorHandlingStrategy.LOG_ONLY:
            self._log_error(error)
            
        elif self.strategy == ErrorHandlingStrategy.CALLBACK:
            self.callback_manager.notify_error(error)
            
        elif self.strategy == ErrorHandlingStrategy.HYBRID:
            self._handle_hybrid(error)
            
    def _handle_hybrid(self, error: ValidationError) -> None:
        """Handle error using hybrid strategy."""
        # Always collect the error
        self.collector.add_error(error)
        
        # Log all errors
        self._log_error(error)
        
        # Notify callbacks
        self.callback_manager.notify_error(error)
        
        # Raise exception for severe errors
        if not error.is_warning and error.code.value <= self.error_threshold.value:
            raise ValidationError(error.message, error.code, error.context)
            
    def _log_error(self, error: ValidationError) -> None:
        """Log an error with appropriate severity."""
        log_message = f"{error.severity}: {error.message}"
        if error.is_warning:
            logger.warning(log_message, extra={"context": error.context})
        else:
            logger.error(log_message, extra={"context": error.context})
            
    def _get_severity(self, code: ValidationErrorCode) -> str:
        """Get the severity level for an error code."""
        if code.value < 100:
            return "CRITICAL"
        elif code.value < 500:
            return "ERROR"
        elif code.value < 800:
            return "WARNING"
        else:
            return "INFO"
            
    def register_error_callback(self, name: str, callback: Callable) -> None:
        """Register an error callback function."""
        self.callback_manager.register_callback(name, callback)
        
    def unregister_error_callback(self, name: str) -> None:
        """Unregister an error callback function."""
        self.callback_manager.unregister_callback(name)
        
    def get_collected_errors(self) -> List[ValidationError]:
        """Get all collected errors."""
        return self.collector.errors.copy()
        
    def get_collected_warnings(self) -> List[ValidationError]:
        """Get all collected warnings."""
        return self.collector.warnings.copy()
        
    def clear_errors(self) -> None:
        """Clear all collected errors and warnings."""
        self.collector.clear()
        
    def set_strategy(self, strategy: ErrorHandlingStrategy) -> None:
        """Set the error handling strategy."""
        self.strategy = strategy
        
    def enable(self) -> None:
        """Enable error handling."""
        self._enabled = True
        
    def disable(self) -> None:
        """Disable error handling."""
        self._enabled = False
        
    def set_error_threshold(self, threshold: ValidationErrorCode) -> None:
        """Set the error threshold for the hybrid strategy."""
        self.error_threshold = threshold
        
    def get_error_summary(self) -> Dict[str, Any]:
        """Get a summary of all errors and warnings."""
        return {
            'total_errors': len(self.collector.errors),
            'total_warnings': len(self.collector.warnings),
            'error_counts': self.collector.get_error_summary(),
            'strategy': self.strategy.name,
            'enabled': self._enabled,
            'threshold': self.error_threshold.name
        }