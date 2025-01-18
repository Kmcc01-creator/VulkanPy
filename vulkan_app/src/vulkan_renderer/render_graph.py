import logging
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
from enum import Enum, auto

logger = logging.getLogger(__name__)

class ResourceType(Enum):
    BUFFER = auto()
    IMAGE = auto()
    ATTACHMENT = auto()

@dataclass
class ResourceNode:
    name: str
    resource_type: ResourceType
    format: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    dependencies: Set[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = set()

class RenderGraph:
    """
    Manages render pass dependencies and resource transitions.
    """
    def __init__(self):
        self.nodes: Dict[str, ResourceNode] = {}
        self.passes: List[str] = []
        self.current_frame_resources: Set[str] = set()
        
    def add_resource(self, name: str, resource_type: ResourceType, 
                    format: Optional[int] = None,
                    width: Optional[int] = None, 
                    height: Optional[int] = None) -> None:
        """Add a resource node to the graph."""
        if name in self.nodes:
            logger.warning(f"Resource {name} already exists in the graph")
            return
            
        node = ResourceNode(
            name=name,
            resource_type=resource_type,
            format=format,
            width=width,
            height=height
        )
        self.nodes[name] = node
        logger.debug(f"Added resource node: {name}")
        
    def add_dependency(self, resource: str, depends_on: str) -> None:
        """Add a dependency between resources."""
        if resource not in self.nodes or depends_on not in self.nodes:
            raise ValueError("Both resources must exist in the graph")
            
        self.nodes[resource].dependencies.add(depends_on)
        logger.debug(f"Added dependency: {resource} -> {depends_on}")
        
    def add_render_pass(self, name: str) -> None:
        """Add a render pass to the execution sequence."""
        self.passes.append(name)
        logger.debug(f"Added render pass: {name}")
        
    def validate(self) -> bool:
        """Validate the render graph for cyclic dependencies."""
        visited = set()
        recursion_stack = set()
        
        def has_cycle(node: str) -> bool:
            visited.add(node)
            recursion_stack.add(node)
            
            for dependency in self.nodes[node].dependencies:
                if dependency not in visited:
                    if has_cycle(dependency):
                        return True
                elif dependency in recursion_stack:
                    return True
                    
            recursion_stack.remove(node)
            return False
            
        try:
            for node in self.nodes:
                if node not in visited:
                    if has_cycle(node):
                        logger.error("Cyclic dependency detected in render graph")
                        return False
            return True
        except Exception as e:
            logger.error(f"Error validating render graph: {e}")
            return False
            
    def begin_frame(self) -> None:
        """Begin a new frame, clearing previous frame resources."""
        self.current_frame_resources.clear()
        logger.debug("Begin new render graph frame")
        
    def execute(self, command_buffer) -> None:
        """Execute the render graph for the current frame."""
        if not self.validate():
            raise RuntimeError("Invalid render graph")
            
        try:
            for pass_name in self.passes:
                # Execute render passes in order
                # This would be implemented by the specific render pass
                logger.debug(f"Executing render pass: {pass_name}")
                
        except Exception as e:
            logger.error(f"Error executing render graph: {e}")
            raise
            
    def cleanup(self) -> None:
        """Clean up render graph resources."""
        self.nodes.clear()
        self.passes.clear()
        self.current_frame_resources.clear()
        logger.info("Render graph cleaned up")