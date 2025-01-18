from typing import List, Optional
import vulkan as vk
from .render_state import (
    RenderState, ViewportState, ScissorState,
    RasterizationState, DepthStencilState, BlendState,
    CullMode, FrontFace, CompareOp, BlendFactor
)

class RenderStateBuilder:
    """
    Builder class for creating RenderState objects with a fluent interface.
    """
    def __init__(self):
        self._state = RenderState()
        
    def viewport(self, width: float, height: float, x: float = 0.0, y: float = 0.0,
                min_depth: float = 0.0, max_depth: float = 1.0) -> 'RenderStateBuilder':
        """Configure viewport state."""
        self._state.viewport = ViewportState(
            x=x, y=y,
            width=width, height=height,
            min_depth=min_depth, max_depth=max_depth
        )
        return self

    def scissor(self, width: int, height: int, x: int = 0, y: int = 0) -> 'RenderStateBuilder':
        """Configure scissor state."""
        self._state.scissor = ScissorState(
            x=x, y=y,
            width=width, height=height
        )
        return self

    def cull_mode(self, mode: CullMode) -> 'RenderStateBuilder':
        """Set culling mode."""
        self._state.rasterization.cull_mode = mode
        return self

    def front_face(self, front_face: FrontFace) -> 'RenderStateBuilder':
        """Set front face winding order."""
        self._state.rasterization.front_face = front_face
        return self

    def line_width(self, width: float) -> 'RenderStateBuilder':
        """Set line width for line primitives."""
        self._state.rasterization.line_width = width
        return self

    def depth_bias(self, constant: float, slope: float, clamp: float) -> 'RenderStateBuilder':
        """Configure depth bias."""
        self._state.rasterization.depth_bias_enable = True
        self._state.rasterization.depth_bias_constant = constant
        self._state.rasterization.depth_bias_slope = slope
        self._state.rasterization.depth_bias_clamp = clamp
        return self

    def depth_test(self, enable: bool = True) -> 'RenderStateBuilder':
        """Enable/disable depth testing."""
        self._state.depth_stencil.depth_test = enable
        return self

    def depth_write(self, enable: bool = True) -> 'RenderStateBuilder':
        """Enable/disable depth writing."""
        self._state.depth_stencil.depth_write = enable
        return self

    def depth_compare_op(self, op: CompareOp) -> 'RenderStateBuilder':
        """Set depth comparison operation."""
        self._state.depth_stencil.depth_compare_op = op
        return self

    def stencil_test(self, enable: bool = True,
                    read_mask: int = 0xFF,
                    write_mask: int = 0xFF,
                    reference: int = 0) -> 'RenderStateBuilder':
        """Configure stencil testing."""
        self._state.depth_stencil.stencil_test = enable
        self._state.depth_stencil.stencil_read_mask = read_mask
        self._state.depth_stencil.stencil_write_mask = write_mask
        self._state.depth_stencil.stencil_reference = reference
        return self

    def blend(self, enable: bool = True,
             src_color: BlendFactor = BlendFactor.SRC_ALPHA,
             dst_color: BlendFactor = BlendFactor.ONE_MINUS_SRC_ALPHA,
             src_alpha: BlendFactor = BlendFactor.ONE,
             dst_alpha: BlendFactor = BlendFactor.ZERO) -> 'RenderStateBuilder':
        """Configure blending."""
        self._state.blend.blend_enable = enable
        self._state.blend.src_color_blend_factor = src_color
        self._state.blend.dst_color_blend_factor = dst_color
        self._state.blend.src_alpha_blend_factor = src_alpha
        self._state.blend.dst_alpha_blend_factor = dst_alpha
        return self

    def blend_op(self, color_op: int = vk.VK_BLEND_OP_ADD,
                alpha_op: int = vk.VK_BLEND_OP_ADD) -> 'RenderStateBuilder':
        """Set blend operations."""
        self._state.blend.color_blend_op = color_op
        self._state.blend.alpha_blend_op = alpha_op
        return self

    def dynamic_states(self, states: List[int]) -> 'RenderStateBuilder':
        """Set dynamic states."""
        self._state.dynamic_states = states.copy()
        return self

    def add_dynamic_state(self, state: int) -> 'RenderStateBuilder':
        """Add a dynamic state."""
        if state not in self._state.dynamic_states:
            self._state.dynamic_states.append(state)
        return self

    def build(self) -> RenderState:
        """Build and return the configured RenderState."""
        return self._state

    @classmethod
    def default(cls) -> RenderState:
        """Create a default render state configuration."""
        return (cls()
                .viewport(800, 600)
                .scissor(800, 600)
                .cull_mode(CullMode.BACK)
                .front_face(FrontFace.COUNTER_CLOCKWISE)
                .depth_test(True)
                .depth_write(True)
                .depth_compare_op(CompareOp.LESS)
                .dynamic_states([
                    vk.VK_DYNAMIC_STATE_VIEWPORT,
                    vk.VK_DYNAMIC_STATE_SCISSOR
                ])
                .build())

    @classmethod
    def alpha_blend(cls) -> RenderState:
        """Create a render state configured for alpha blending."""
        return (cls()
                .viewport(800, 600)
                .scissor(800, 600)
                .cull_mode(CullMode.BACK)
                .front_face(FrontFace.COUNTER_CLOCKWISE)
                .depth_test(True)
                .depth_write(False)
                .blend(True,
                      src_color=BlendFactor.SRC_ALPHA,
                      dst_color=BlendFactor.ONE_MINUS_SRC_ALPHA,
                      src_alpha=BlendFactor.ONE,
                      dst_alpha=BlendFactor.ZERO)
                .dynamic_states([
                    vk.VK_DYNAMIC_STATE_VIEWPORT,
                    vk.VK_DYNAMIC_STATE_SCISSOR
                ])
                .build())

    @classmethod
    def additive_blend(cls) -> RenderState:
        """Create a render state configured for additive blending."""
        return (cls()
                .viewport(800, 600)
                .scissor(800, 600)
                .cull_mode(CullMode.BACK)
                .front_face(FrontFace.COUNTER_CLOCKWISE)
                .depth_test(True)
                .depth_write(False)
                .blend(True,
                      src_color=BlendFactor.ONE,
                      dst_color=BlendFactor.ONE,
                      src_alpha=BlendFactor.ONE,
                      dst_alpha=BlendFactor.ONE)
                .dynamic_states([
                    vk.VK_DYNAMIC_STATE_VIEWPORT,
                    vk.VK_DYNAMIC_STATE_SCISSOR
                ])
                .build())

# Example usage:
"""
# Create a basic render state
render_state = (RenderStateBuilder()
                .viewport(800, 600)
                .scissor(800, 600)
                .cull_mode(CullMode.BACK)
                .depth_test(True)
                .build())

# Create a state for transparent objects
transparent_state = (RenderStateBuilder()
                    .viewport(800, 600)
                    .scissor(800, 600)
                    .cull_mode(CullMode.NONE)
                    .depth_test(True)
                    .depth_write(False)
                    .blend(True)  # Default alpha blending
                    .build())

# Create a state with custom depth bias
shadow_state = (RenderStateBuilder()
                .viewport(1024, 1024)
                .scissor(1024, 1024)
                .cull_mode(CullMode.FRONT)
                .depth_test(True)
                .depth_bias(1.25, 1.75, 0.0)
                .build())
"""