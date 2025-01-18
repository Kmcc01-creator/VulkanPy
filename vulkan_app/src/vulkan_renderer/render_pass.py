import vulkan as vk
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AttachmentDescription:
    format: int
    samples: int = vk.VK_SAMPLE_COUNT_1_BIT
    load_op: int = vk.VK_ATTACHMENT_LOAD_OP_CLEAR
    store_op: int = vk.VK_ATTACHMENT_STORE_OP_STORE
    stencil_load_op: int = vk.VK_ATTACHMENT_LOAD_OP_DONT_CARE
    stencil_store_op: int = vk.VK_ATTACHMENT_STORE_OP_DONT_CARE
    initial_layout: int = vk.VK_IMAGE_LAYOUT_UNDEFINED
    final_layout: int = vk.VK_IMAGE_LAYOUT_PRESENT_SRC_KHR

@dataclass
class SubpassDescription:
    pipeline_bind_point: int = vk.VK_PIPELINE_BIND_POINT_GRAPHICS
    color_attachments: List[int] = None
    depth_attachment: Optional[int] = None
    input_attachments: List[int] = None
    resolve_attachments: List[int] = None

    def __post_init__(self):
        self.color_attachments = self.color_attachments or []
        self.input_attachments = self.input_attachments or []
        self.resolve_attachments = self.resolve_attachments or []

class RenderPass:
    """
    Manages render pass creation and execution.
    """
    def __init__(self, device: vk.VkDevice):
        self.device = device
        self.handle: Optional[vk.VkRenderPass] = None
        self.attachments: List[AttachmentDescription] = []
        self.subpasses: List[SubpassDescription] = []
        self.dependencies: List[vk.VkSubpassDependency] = []
        
    def add_attachment(self, attachment: AttachmentDescription) -> int:
        """Add an attachment to the render pass."""
        self.attachments.append(attachment)
        return len(self.attachments) - 1
        
    def add_subpass(self, subpass: SubpassDescription) -> int:
        """Add a subpass to the render pass."""
        self.subpasses.append(subpass)
        return len(self.subpasses) - 1
        
    def add_dependency(self, src_subpass: int, dst_subpass: int,
                      src_stage: int, dst_stage: int,
                      src_access: int, dst_access: int) -> None:
        """Add a dependency between subpasses."""
        dependency = vk.VkSubpassDependency(
            srcSubpass=src_subpass,
            dstSubpass=dst_subpass,
            srcStageMask=src_stage,
            dstStageMask=dst_stage,
            srcAccessMask=src_access,
            dstAccessMask=dst_access
        )
        self.dependencies.append(dependency)
        
    def create(self) -> None:
        """Create the Vulkan render pass."""
        # Convert AttachmentDescriptions to VkAttachmentDescriptions
        attachment_descriptions = [
            vk.VkAttachmentDescription(
                format=attachment.format,
                samples=attachment.samples,
                loadOp=attachment.load_op,
                storeOp=attachment.store_op,
                stencilLoadOp=attachment.stencil_load_op,
                stencilStoreOp=attachment.stencil_store_op,
                initialLayout=attachment.initial_layout,
                finalLayout=attachment.final_layout
            )
            for attachment in self.attachments
        ]

        # Create subpass descriptions
        subpass_descriptions = []
        for subpass in self.subpasses:
            color_refs = [
                vk.VkAttachmentReference(
                    attachment=attachment_idx,
                    layout=vk.VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL
                )
                for attachment_idx in subpass.color_attachments
            ]
            
            depth_ref = None
            if subpass.depth_attachment is not None:
                depth_ref = vk.VkAttachmentReference(
                    attachment=subpass.depth_attachment,
                    layout=vk.VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL
                )
                
            input_refs = [
                vk.VkAttachmentReference(
                    attachment=attachment_idx,
                    layout=vk.VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL
                )
                for attachment_idx in subpass.input_attachments
            ]
            
            resolve_refs = [
                vk.VkAttachmentReference(
                    attachment=attachment_idx,
                    layout=vk.VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL
                )
                for attachment_idx in subpass.resolve_attachments
            ]
            
            subpass_description = vk.VkSubpassDescription(
                pipelineBindPoint=subpass.pipeline_bind_point,
                colorAttachmentCount=len(color_refs),
                pColorAttachments=color_refs,
                pDepthStencilAttachment=depth_ref,
                inputAttachmentCount=len(input_refs),
                pInputAttachments=input_refs,
                pResolveAttachments=resolve_refs if resolve_refs else None
            )
            subpass_descriptions.append(subpass_description)

        # Create render pass
        create_info = vk.VkRenderPassCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO,
            attachmentCount=len(attachment_descriptions),
            pAttachments=attachment_descriptions,
            subpassCount=len(subpass_descriptions),
            pSubpasses=subpass_descriptions,
            dependencyCount=len(self.dependencies),
            pDependencies=self.dependencies
        )

        try:
            self.handle = vk.vkCreateRenderPass(self.device, create_info, None)
            logger.info("Created render pass successfully")
        except Exception as e:
            logger.error(f"Failed to create render pass: {e}")
            raise
            
    def begin(self, command_buffer: vk.VkCommandBuffer,
              framebuffer: vk.VkFramebuffer,
              render_area: vk.VkRect2D,
              clear_values: List[vk.VkClearValue]) -> None:
        """Begin the render pass."""
        begin_info = vk.VkRenderPassBeginInfo(
            sType=vk.VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO,
            renderPass=self.handle,
            framebuffer=framebuffer,
            renderArea=render_area,
            clearValueCount=len(clear_values),
            pClearValues=clear_values
        )
        
        vk.vkCmdBeginRenderPass(
            command_buffer,
            begin_info,
            vk.VK_SUBPASS_CONTENTS_INLINE
        )
        
    def end(self, command_buffer: vk.VkCommandBuffer) -> None:
        """End the render pass."""
        vk.vkCmdEndRenderPass(command_buffer)
        
    def cleanup(self) -> None:
        """Clean up render pass resources."""
        if self.handle:
            vk.vkDestroyRenderPass(self.device, self.handle, None)
            self.handle = None
            logger.info("Cleaned up render pass")