# validation/config.py

from dataclasses import dataclass, field
from typing import Dict, Optional, List
import logging
from enum import Enum, auto

class ValidationLevel(Enum):
    """Validation level for different components."""
    DISABLED = auto()
    BASIC = auto()
    PERFORMANCE = auto()
    FULL = auto()

@dataclass
class ValidationFeatures:
    """Feature flags for validation system."""
    enable_debug_markers: bool = True
    track_object_lifetimes: bool = True
    validate_shader_bindings: bool = True
    enable_memory_tracking: bool = True
    validate_synchronization: bool = True
    track_resource_usage: bool = True
    enable_performance_warnings: bool = True
    validate_api_usage: bool = True

@dataclass
class LoggingConfig:
    """Configuration for validation logging."""
    level: int = logging.INFO
    enable_file_logging: bool = False
    log_file_path: Optional[str] = None
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    include_source_info: bool = True
    max_log_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5

@dataclass
class PerformanceConfig:
    """Configuration for performance validation."""
    track_command_buffer_size: bool = True
    track_descriptor_pool_usage: bool = True
    track_memory_fragmentation: bool = True
    track_pipeline_cache_hits: bool = True
    track_queue_submissions: bool = True
    resource_usage_warning_threshold: float = 0.8
    memory_allocation_warning_threshold: float = 0.9
    max_validation_time_ms: int = 100

@dataclass
class ValidationLimits:
    """Limits for various validation checks."""
    max_memory_allocations: int = 4096
    max_command_pools: int = 64
    max_descriptor_sets: int = 4096
    max_pipeline_layouts: int = 128
    max_shader_modules: int = 1024
    max_vertex_attributes: int = 16
    max_vertex_bindings: int = 8
    max_push_constant_size: int = 128
    max_dynamic_uniform_buffers: int = 8
    max_dynamic_storage_buffers: int = 4

@dataclass
class ComponentConfig:
    """Configuration for a specific validation component."""
    enabled: bool = True
    level: ValidationLevel = ValidationLevel.FULL
    custom_limits: Dict[str, int] = field(default_factory=dict)
    performance_tracking: bool = True
    debug_validation: bool = False

@dataclass
class ValidationConfig:
    """Main configuration class for the validation system."""
    
    # Component-specific configurations
    buffer_config: ComponentConfig = field(default_factory=ComponentConfig)
    command_config: ComponentConfig = field(default_factory=ComponentConfig)
    descriptor_config: ComponentConfig = field(default_factory=ComponentConfig)
    device_config: ComponentConfig = field(default_factory=ComponentConfig)
    memory_config: ComponentConfig = field(default_factory=ComponentConfig)
    pipeline_config: ComponentConfig = field(default_factory=ComponentConfig)
    shader_config: ComponentConfig = field(default_factory=ComponentConfig)

    # Global configuration
    features: ValidationFeatures = field(default_factory=ValidationFeatures)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    limits: ValidationLimits = field(default_factory=ValidationLimits)
    enabled_extensions: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Set up logging configuration."""
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging based on settings."""
        logger = logging.getLogger('validation')
        logger.setLevel(self.logging.level)

        formatter = logging.Formatter(self.logging.log_format)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler if enabled
        if self.logging.enable_file_logging and self.logging.log_file_path:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                self.logging.log_file_path,
                maxBytes=self.logging.max_log_file_size,
                backupCount=self.logging.backup_count
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    @classmethod
    def create_debug_config(cls) -> 'ValidationConfig':
        """Create a configuration optimized for debugging."""
        config = cls()
        for component in [
            config.buffer_config,
            config.command_config,
            config.descriptor_config,
            config.device_config,
            config.memory_config,
            config.pipeline_config,
            config.shader_config
        ]:
            component.debug_validation = True
            component.level = ValidationLevel.FULL

        config.logging.level = logging.DEBUG
        config.logging.include_source_info = True
        return config

    @classmethod
    def create_performance_config(cls) -> 'ValidationConfig':
        """Create a configuration optimized for performance validation."""
        config = cls()
        for component in [
            config.buffer_config,
            config.command_config,
            config.descriptor_config,
            config.device_config,
            config.memory_config,
            config.pipeline_config,
            config.shader_config
        ]:
            component.performance_tracking = True
            component.level = ValidationLevel.PERFORMANCE

        config.performance.track_command_buffer_size = True
        config.performance.track_descriptor_pool_usage = True
        config.performance.track_memory_fragmentation = True
        config.performance.track_pipeline_cache_hits = True
        config.performance.track_queue_submissions = True
        return config

    def update_component_config(self, component: str, updates: dict) -> None:
        """Update configuration for a specific component."""
        component_config = getattr(self, f"{component}_config", None)
        if component_config is None:
            raise ValueError(f"Invalid component: {component}")

        for key, value in updates.items():
            if hasattr(component_config, key):
                setattr(component_config, key, value)
            else:
                raise ValueError(f"Invalid configuration key for {component}: {key}")

    def validate(self) -> bool:
        """Validate the configuration settings."""
        # Validate limits
        if self.limits.max_memory_allocations <= 0:
            return False
        if self.limits.max_command_pools <= 0:
            return False
        if self.limits.max_descriptor_sets <= 0:
            return False

        # Validate component configurations
        for component in [
            self.buffer_config,
            self.command_config,
            self.descriptor_config,
            self.device_config,
            self.memory_config,
            self.pipeline_config,
            self.shader_config
        ]:
            if component.level == ValidationLevel.DISABLED and component.debug_validation:
                return False

        return True