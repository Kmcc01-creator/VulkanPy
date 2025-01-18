import vulkan as vk
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict
from enum import Enum, auto

logger = logging.getLogger(__name__)

class CullMode(Enum):
    NONE = vk.VK_CULL_MODE_NONE
    FRONT = vk.VK_CULL_MODE_FRONT_BIT
    BACK = vk.VK_CULL_MODE_BACK_BIT
    FRONT_AND_BACK = vk.VK_CULL_MODE_FRONT_AND_BACK

class FrontFace(Enum):
    CLOCKWISE = vk.VK_FRONT_FACE_CLOCKWISE
    COUNTER_CLOCKWISE = vk.VK_FRONT_FACE_COUNTER_CLOCKWISE

class CompareOp(Enum):
    NEVER = vk.VK_COMPARE_OP_NEVER
    LESS = vk.VK_COMPARE_OP_LESS
    EQUAL = vk.VK_COMPARE_OP_EQUAL
    LESS_OR_EQUAL = vk.VK_COMPARE_OP_LESS_OR_EQUAL
    GREATER = vk.VK_COMPARE_OP_GREATER
    NOT_EQUAL = vk.VK_COMPARE_OP_NOT_EQUAL
    GREATER_OR_EQUAL = vk.VK_COMPARE_OP_GREATER_OR_EQUAL
    ALWAYS = vk.VK_COMPARE_OP_ALWAYS

class BlendFactor(Enum):
    ZERO = vk.VK_BLEND_FACTOR_ZERO
    ONE = vk.VK_BLEND_FACTOR_ONE
    SRC_COLOR = vk.VK_BLEND_FACTOR_SRC_COLOR
    ONE_MINUS_SRC_COLOR = vk.VK_BLEND_FACTOR_ONE_MINUS_SRC_COLOR
    DST_COLOR = vk.VK_BLEND_FACTOR_DST_COLOR
    ONE_MINUS_DST_COLOR = vk.VK_BLEND_FACTOR_ONE_MINUS_DST_COLOR
    SRC_ALPHA = vk.VK_BLEND_FACTOR_SRC_ALPHA
    ONE_MINUS_SRC_ALPHA = vk.VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA

@dataclass
class ViewportState:
    """Viewport configuration."""
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    min_depth: float = 0.0
    max_depth: float = 1.0

    def to_vulkan(self) -> vk.VkViewport:
        return vk.VkViewport(
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            minDepth=self.min_depth,
            maxDepth=self.max_depth
        )

@dataclass
class ScissorState:
    """Scissor configuration."""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    def to_vulkan(self) -> vk.VkRect2D:
        return vk.VkRect2D(
            offset=vk.VkOffset2D(x=self.x, y=self.y),
            extent=vk.VkExtent2D(width=self.width, height=self.height)
        )

@dataclass
class RasterizationState:
    """Rasterization configuration."""
    cull_mode: CullMode = CullMode.BACK
    front_face: FrontFace = FrontFace.COUNTER_CLOCKWISE
    line_width: float = 1.0
    depth_bias_enable: bool = False
    depth_bias_constant: float = 0.0
    depth_bias_slope: float = 0.0
    depth_bias_clamp: float = 0.0

@dataclass
class DepthStencilState:
    """Depth and stencil configuration."""
    depth_test: bool = True
    depth_write: bool = True
    depth_compare_op: CompareOp = CompareOp.LESS
    stencil_test: bool = False
    stencil_read_mask: int = 0xFF
    stencil_write_mask: int = 0xFF
    stencil_reference: int = 0

@dataclass
class BlendState:
    """Blend configuration."""
    blend_enable: bool = False
    src_color_blend_factor: BlendFactor = BlendFactor.ONE
    dst_color_blend_factor: BlendFactor = BlendFactor.ZERO
    color_blend_op: int = vk.VK_BLEND_OP_ADD
    src_alpha_blend_factor: BlendFactor = BlendFactor.ONE
    dst_alpha_blend_factor: BlendFactor = BlendFactor.ZERO
    alpha_blend_op: int = vk.VK_BLEND_OP_ADD

class RenderState:
    """Manages the complete render state configuration."""
    
    def __init__(self):
        self.viewport = ViewportState()
        self.scissor = ScissorState()
        self.rasterization = RasterizationState()
        self.depth_stencil = DepthStencilState()
        self.blend = BlendState()
        self.dynamic_states: List[int] = []
        
    def set_viewport(self, width: float, height: float) -> None:
        """Set the viewport dimensions."""
        self.viewport.width = width
        self.viewport.height = height
        if vk.VK_DYNAMIC_STATE_VIEWPORT not in self.dynamic_states:
            self.dynamic_states.append(vk.VK_DYNAMIC_STATE_VIEWPORT)

    def set_scissor(self, width: int, height: int) -> None:
        """Set the scissor dimensions."""
        self.scissor.width = width
        self.scissor.height = height
        if vk.VK_DYNAMIC_STATE_SCISSOR not in self.dynamic_states:
            self.dynamic_states.append(vk.VK_DYNAMIC_STATE_SCISSOR)

    def create_pipeline_state(self) -> Dict:
        """Create pipeline state create info structures."""
        viewport_state = vk.VkPipelineViewportStateCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO,
            viewportCount=1,
            pViewports=[self.viewport.to_vulkan()],
            scissorCount=1,
            pScissors=[self.scissor.to_vulkan()]
        )

        rasterization_state = vk.VkPipelineRasterizationStateCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO,
            depthClampEnable=vk.VK_FALSE,
            rasterizerDiscardEnable=vk.VK_FALSE,
            polygonMode=vk.VK_POLYGON_MODE_FILL,
            cullMode=self.rasterization.cull_mode.value,
            frontFace=self.rasterization.front_face.value,
            depthBiasEnable=vk.VK_TRUE if self.rasterization.depth_bias_enable else vk.VK_FALSE,
            depthBiasConstantFactor=self.rasterization.depth_bias_constant,
            depthBiasSlopeFactor=self.rasterization.depth_bias_slope,
            depthBiasClamp=self.rasterization.depth_bias_clamp,
            lineWidth=self.rasterization.line_width
        )

        depth_stencil_state = vk.VkPipelineDepthStencilStateCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO,
            depthTestEnable=vk.VK_TRUE if self.depth_stencil.depth_test else vk.VK_FALSE,
            depthWriteEnable=vk.VK_TRUE if self.depth_stencil.depth_write else vk.VK_FALSE,
            depthCompareOp=self.depth_stencil.depth_compare_op.value,
            depthBoundsTestEnable=vk.VK_FALSE,
            stencilTestEnable=vk.VK_TRUE if self.depth_stencil.stencil_test else vk.VK_FALSE,
            front=vk.VkStencilOpState(
                failOp=vk.VK_STENCIL_OP_KEEP,
                passOp=vk.VK_STENCIL_OP_KEEP,
                depthFailOp=vk.VK_STENCIL_OP_KEEP,
                compareOp=vk.VK_COMPARE_OP_ALWAYS,
                compareMask=self.depth_stencil.stencil_read_mask,
                writeMask=self.depth_stencil.stencil_write_mask,
                reference=self.depth_stencil.stencil_reference
            ),
            back=vk.VkStencilOpState(
                failOp=vk.VK_STENCIL_OP_KEEP,
                passOp=vk.VK_STENCIL_OP_KEEP,
                depthFailOp=vk.VK_STENCIL_OP_KEEP,
                compareOp=vk.VK_COMPARE_OP_ALWAYS,
                compareMask=self.depth_stencil.stencil_read_mask,
                writeMask=self.depth_stencil.stencil_write_mask,
                reference=self.depth_stencil.stencil_reference
            )
        )

        color_blend_attachment = vk.VkPipelineColorBlendAttachmentState(
            blendEnable=vk.VK_TRUE if self.blend.blend_enable else vk.VK_FALSE,
            srcColorBlendFactor=self.blend.src_color_blend_factor.value,
            dstColorBlendFactor=self.blend.dst_color_blend_factor.value,
            colorBlendOp=self.blend.color_blend_op,
            srcAlphaBlendFactor=self.blend.src_alpha_blend_factor.value,
            dstAlphaBlendFactor=self.blend.dst_alpha_blend_factor.value,
            alphaBlendOp=self.blend.alpha_blend_op,
            colorWriteMask=vk.VK_COLOR_COMPONENT_R_BIT |
                          vk.VK_COLOR_COMPONENT_G_BIT |
                          vk.VK_COLOR_COMPONENT_B_BIT |
                          vk.VK_COLOR_COMPONENT_A_BIT
        )

        color_blend_state = vk.VkPipelineColorBlendStateCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO,
            logicOpEnable=vk.VK_FALSE,
            logicOp=vk.VK_LOGIC_OP_COPY,
            attachmentCount=1,
            pAttachments=[color_blend_attachment],
            blendConstants=[0.0, 0.0, 0.0, 0.0]
        )

        dynamic_state = None
        if self.dynamic_states:
            dynamic_state = vk.VkPipelineDynamicStateCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO,
                dynamicStateCount=len(self.dynamic_states),
                pDynamicStates=self.dynamic_states
            )

        return {
            'viewport_state': viewport_state,
            'rasterization_state': rasterization_state,
            'depth_stencil_state': depth_stencil_state,
            'color_blend_state': color_blend_state,
            'dynamic_state': dynamic_state
        }

    def apply_dynamic_state(self, command_buffer: vk.VkCommandBuffer) -> None:
        """Apply dynamic state to the command buffer."""
        if vk.VK_DYNAMIC_STATE_VIEWPORT in self.dynamic_states:
            vk.vkCmdSetViewport(
                command_buffer,
                0, 1,
                [self.viewport.to_vulkan()]
            )

        if vk.VK_DYNAMIC_STATE_SCISSOR in self.dynamic_states:
            vk.vkCmdSetScissor(
                command_buffer,
                0, 1,
                [self.scissor.to_vulkan()]
            )

    @staticmethod
    def create_default() -> 'RenderState':
        """Create a default render state configuration."""
        state = RenderState()
        state.dynamic_states = [
            vk.VK_DYNAMIC_STATE_VIEWPORT,
            vk.VK_DYNAMIC_STATE_SCISSOR
        ]
        return state

    @staticmethod
    def create_alpha_blend() -> 'RenderState':
        """Create a render state configured for alpha blending."""
        state = RenderState()
        state.blend = BlendState(
            blend_enable=True,
            src_color_blend_factor=BlendFactor.SRC_ALPHA,
            dst_color_blend_factor=BlendFactor.ONE_MINUS_SRC_ALPHA,
            src_alpha_blend_factor=BlendFactor.ONE,
            dst_alpha_blend_factor=BlendFactor.ZERO
        )
        state.dynamic_states = [
            vk.VK_DYNAMIC_STATE_VIEWPORT,
            vk.VK_DYNAMIC_STATE_SCISSOR
        ]
        return state

    @staticmethod
    def create_additive_blend() -> 'RenderState':
        """Create a render state configured for additive blending."""
        state = RenderState()
        state.blend = BlendState(
            blend_enable=True,
            src_color_blend_factor=BlendFactor.ONE,
            dst_color_blend_factor=BlendFactor.ONE,
            src_alpha_blend_factor=BlendFactor.ONE,
            dst_alpha_blend_factor=BlendFactor.ONE
        )
        state.dynamic_states = [
            vk.VK_DYNAMIC_STATE_VIEWPORT,
            vk.VK_DYNAMIC_STATE_SCISSOR
        ]
        return state