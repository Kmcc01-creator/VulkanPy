# validation/error_codes.py

from enum import Enum, auto
from typing import Dict, Optional

class ValidationErrorCode(Enum):
    """Error codes for validation failures."""

    # General errors (0-99)
    SUCCESS = 0
    UNKNOWN_ERROR = 1
    INVALID_PARAMETER = 2
    OUT_OF_MEMORY = 3
    INVALID_OPERATION = 4
    NOT_IMPLEMENTED = 5
    VALIDATION_ERROR = 6
    INTERNAL_ERROR = 7

    # Memory errors (100-199)
    INVALID_MEMORY_ALLOCATION = 100
    MEMORY_LEAK = 101
    INVALID_MEMORY_TYPE = 102
    INVALID_ALIGNMENT = 103
    MEMORY_MAP_FAILED = 104
    INVALID_MEMORY_RANGE = 105
    MEMORY_ALREADY_MAPPED = 106
    MEMORY_NOT_MAPPED = 107
    MEMORY_OVERFLOW = 108
    MEMORY_UNDERFLOW = 109

    # Buffer errors (200-299)
    INVALID_BUFFER_CREATE = 200
    BUFFER_TOO_SMALL = 201
    BUFFER_TOO_LARGE = 202
    INVALID_BUFFER_USAGE = 203
    BUFFER_ALREADY_BOUND = 204
    INVALID_BUFFER_OFFSET = 205
    BUFFER_NOT_BOUND = 206
    BUFFER_MEMORY_OVERLAP = 207
    TOO_MANY_BUFFERS = 208

    # Command errors (300-399)
    INVALID_COMMAND_BUFFER = 300
    COMMAND_BUFFER_RECORDING = 301
    COMMAND_BUFFER_NOT_RECORDING = 302
    INVALID_COMMAND_POOL = 303
    TOO_MANY_COMMAND_POOLS = 304
    COMMAND_BUFFER_INCOMPLETE = 305
    COMMAND_BUFFER_ALREADY_SUBMITTED = 306
    INVALID_COMMAND_SEQUENCE = 307
    NESTED_RENDER_PASS = 308

    # Descriptor errors (400-499)
    INVALID_DESCRIPTOR_SET = 400
    DESCRIPTOR_SET_NOT_BOUND = 401
    TOO_MANY_DESCRIPTOR_SETS = 402
    INVALID_DESCRIPTOR_TYPE = 403
    DESCRIPTOR_POOL_EMPTY = 404
    DESCRIPTOR_UPDATE_ERROR = 405
    INVALID_DESCRIPTOR_LAYOUT = 406
    INCOMPATIBLE_DESCRIPTOR = 407

    # Pipeline errors (500-599)
    INVALID_PIPELINE_CREATE = 500
    INVALID_SHADER_STAGE = 501
    TOO_MANY_SHADER_STAGES = 502
    INVALID_VERTEX_INPUT = 503
    INVALID_PIPELINE_LAYOUT = 504
    PIPELINE_LAYOUT_INCOMPATIBLE = 505
    TOO_MANY_PIPELINES = 506
    INVALID_RENDER_PASS = 507
    PIPELINE_CACHE_MISS = 508

    # Shader errors (600-699)
    INVALID_SHADER_CODE = 600
    SHADER_COMPILATION_ERROR = 601
    INVALID_SPIRV = 602
    INVALID_SHADER_INTERFACE = 603
    SHADER_RESOURCE_LIMIT = 604
    INVALID_SHADER_STAGE_COMBINATION = 605
    MISSING_ENTRY_POINT = 606
    INVALID_UNIFORM_BUFFER = 607
    TOO_MANY_UNIFORMS = 608

    # Device errors (700-799)
    UNSUPPORTED_FEATURE = 700
    MISSING_EXTENSION = 701
    INVALID_QUEUE_FAMILY = 702
    DEVICE_LOST = 703
    OUT_OF_DEVICE_MEMORY = 704
    INITIALIZATION_FAILED = 705
    INVALID_PHYSICAL_DEVICE = 706

    # Performance warnings (800-899)
    INEFFICIENT_BUFFER_SIZE = 800
    SUBOPTIMAL_IMAGE_LAYOUT = 801
    MEMORY_FRAGMENTATION = 802
    PIPELINE_CACHE_INEFFICIENT = 803
    COMMAND_BUFFER_SIZE_CONCERN = 804
    DESCRIPTOR_POOL_FRAGMENTATION = 805
    QUEUE_SUBMISSION_OVERHEAD = 806

    @classmethod
    def get_category(cls, code: 'ValidationErrorCode') -> str:
        """Get the category for an error code."""
        code_value = code.value
        if code_value < 100:
            return "General"
        elif code_value < 200:
            return "Memory"
        elif code_value < 300:
            return "Buffer"
        elif code_value < 400:
            return "Command"
        elif code_value < 500:
            return "Descriptor"
        elif code_value < 600:
            return "Pipeline"
        elif code_value < 700:
            return "Shader"
        elif code_value < 800:
            return "Device"
        else:
            return "Performance"

    @classmethod
    def is_error(cls, code: 'ValidationErrorCode') -> bool:
        """Determine if a code represents an error (vs warning)."""
        return code.value < 800

class ErrorCodeFormatter:
    """Formats error codes into human-readable messages."""

    _messages: Dict[ValidationErrorCode, str] = {
        ValidationErrorCode.SUCCESS: "Operation completed successfully",
        ValidationErrorCode.UNKNOWN_ERROR: "An unknown error occurred",
        ValidationErrorCode.OUT_OF_MEMORY: "Out of memory",
        # Add more messages for each error code...
    }

    @classmethod
    def get_message(cls, code: ValidationErrorCode, **kwargs) -> str:
        """Get a formatted message for an error code."""
        base_message = cls._messages.get(
            code,
            f"Error code {code.name} ({code.value})"
        )
        
        try:
            return base_message.format(**kwargs)
        except KeyError as e:
            return f"{base_message} (Missing format parameter: {e})"
        except Exception as e:
            return f"{base_message} (Format error: {e})"

class ValidationMessage:
    """Represents a validation message with context."""
    
    def __init__(
        self,
        code: ValidationErrorCode,
        message: Optional[str] = None,
        context: Optional[Dict] = None
    ):
        self.code = code
        self.message = message or ErrorCodeFormatter.get_message(code)
        self.context = context or {}
        self.category = ValidationErrorCode.get_category(code)
        self.is_error = ValidationErrorCode.is_error(code)

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} (Context: {self.context})"
        return self.message

    def to_dict(self) -> Dict:
        """Convert the message to a dictionary format."""
        return {
            'code': self.code.value,
            'name': self.code.name,
            'message': self.message,
            'category': self.category,
            'is_error': self.is_error,
            'context': self.context
        }