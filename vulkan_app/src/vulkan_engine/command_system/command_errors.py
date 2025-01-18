
# src/vulkan_engine/command_system/command_errors.py
from typing import Optional

class CommandError(Exception):
    """Base exception for command management errors."""
    def __init__(self, message: str, error_code: Optional[int] = None):
        super().__init__(message)
        self.error_code = error_code

class PoolError(CommandError):
    """Errors related to command pool operations."""
    pass

class BufferError(CommandError):
    """Errors related to command buffer operations."""
    pass

class MemoryError(CommandError):
    """Errors related to command memory operations."""
    pass

class ValidationError(CommandError):
    """Errors related to validation checks."""
    pass