import vulkan as vk
import logging
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from .vulkan_resources import VulkanResource

logger = logging.getLogger(__name__)

@dataclass
class PipelineConfigInfo:
    viewport: vk.VkViewport
    scissor: vk.VkRect2D
    dynamic_states: List[int]
    vertex_binding_descriptions: List[vk.VkVertexInputBindingDescription]
    vertex_attribute_descriptions: List[vk.VkVertexInputAttributeDescription]
    topology: int = vk.VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST
    enable_depth_test: bool = True
    enable_depth_write: bool = True
    depth_compare_op: int = vk.VK_COMPARE_OP_LESS
    cull_mode: int = vk.VK_CULL_MODE_BACK_BIT
    front_face: int = vk.VK_FRONT_FACE_COUNTER_CLOCKWISE
    line_width: float = 1.0

class Pipeline(VulkanResource):
    def __init__(self, device: vk.VkDevice, cache_dir: str = "shader_cache/"):
        super().__init__(device)
        self.cache_dir = cache_dir
        self.layout: Optional[vk.VkPipelineLayout] = None
        self.validation_enabled = True  # Set based on engine configuration
        
    def create_graphics_pipeline(
        self,
        vert_shader_path: str,
        frag_shader_path: str,
        render_pass: vk.VkRenderPass,
        config: PipelineConfigInfo,
        descriptor_set_layouts: List[vk.VkDescriptorSetLayout] = None
    ) -> None:
        """Create a graphics pipeline with the specified configuration."""
        try:
            # Create shader modules
            vert_shader_module = self._create_shader_module(vert_shader_path)
            frag_shader_module = self._create_shader_module(frag_shader_path)

            shader_stages = self._create_shader_stages(vert_shader_module, frag_shader_module)
            vertex_input_info = self._create_vertex_input_info(config)
            input_assembly_info = self._create_input_assembly_info(config)
            viewport_info = self._create_viewport_info(config)
            rasterization_info = self._create_rasterization_info(config)
            multisample_info = self._create_multisample_info()
            depth_stencil_info = self._create_depth_stencil_info(config)
            color_blend_info = self._create_color_blend_info()
            dynamic_state_info = self._create_dynamic_state_info(config)

            # Create pipeline layout
            self.layout = self._create_pipeline_layout(descriptor_set_layouts)

            # Create the graphics pipeline
            pipeline_info = vk.VkGraphicsPipelineCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO,
                stageCount=len(shader_stages),
                pStages=shader_stages,
                pVertexInputState=vertex_input_info,
                pInputAssemblyState=input_assembly_info,
                pViewportState=viewport_info,
                pRasterizationState=rasterization_info,
                pMultisampleState=multisample_info,
                pDepthStencilState=depth_stencil_info,
                pColorBlendState=color_blend_info,
                pDynamicState=dynamic_state_info,
                layout=self.layout,
                renderPass=render_pass,
                subpass=0
            )

            self.handle = vk.vkCreateGraphicsPipelines(
                self.device, vk.VK_NULL_HANDLE, 1, [pipeline_info], None
            )[0]
            
            logger.info("Graphics pipeline created successfully")

            # Cleanup shader modules
            vk.vkDestroyShaderModule(self.device, vert_shader_module, None)
            vk.vkDestroyShaderModule(self.device, frag_shader_module, None)

        except Exception as e:
            logger.error(f"Failed to create graphics pipeline: {e}")
            self.cleanup()
            raise

    def create_compute_pipeline(
        self,
        compute_shader_path: str,
        descriptor_set_layouts: List[vk.VkDescriptorSetLayout] = None
    ) -> None:
        """Create a compute pipeline."""
        try:
            compute_shader_module = self._create_shader_module(compute_shader_path)
            
            shader_stage = vk.VkPipelineShaderStageCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
                stage=vk.VK_SHADER_STAGE_COMPUTE_BIT,
                module=compute_shader_module,
                pName="main"
            )

            self.layout = self._create_pipeline_layout(descriptor_set_layouts)

            create_info = vk.VkComputePipelineCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO,
                stage=shader_stage,
                layout=self.layout
            )

            self.handle = vk.vkCreateComputePipelines(
                self.device, vk.VK_NULL_HANDLE, 1, [create_info], None
            )[0]
            
            logger.info("Compute pipeline created successfully")

            vk.vkDestroyShaderModule(self.device, compute_shader_module, None)

        except Exception as e:
            logger.error(f"Failed to create compute pipeline: {e}")
            self.cleanup()
            raise

    def _create_shader_module(self, shader_path: str) -> vk.VkShaderModule:
        """Create a shader module from a SPIR-V file."""
        try:
            with open(shader_path, 'rb') as f:
                code = f.read()

            create_info = vk.VkShaderModuleCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
                codeSize=len(code),
                pCode=code
            )

            if self.validation_enabled:
                logger.debug(f"Creating shader module from {shader_path}")

            return vk.vkCreateShaderModule(self.device, create_info, None)

        except Exception as e:
            logger.error(f"Failed to create shader module from {shader_path}: {e}")
            raise

    def _create_pipeline_layout(
        self,
        descriptor_set_layouts: List[vk.VkDescriptorSetLayout] = None
    ) -> vk.VkPipelineLayout:
        """Create a pipeline layout."""
        if descriptor_set_layouts is None:
            descriptor_set_layouts = []

        push_constant_range = vk.VkPushConstantRange(
            stageFlags=vk.VK_SHADER_STAGE_VERTEX_BIT,
            offset=0,
            size=64  # Adjust size based on your push constant needs
        )

        create_info = vk.VkPipelineLayoutCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
            setLayoutCount=len(descriptor_set_layouts),
            pSetLayouts=descriptor_set_layouts,
            pushConstantRangeCount=1,
            pPushConstantRanges=[push_constant_range]
        )

        return vk.vkCreatePipelineLayout(self.device, create_info, None)

    def cleanup(self) -> None:
        """Clean up pipeline resources."""
        if self.handle:
            vk.vkDestroyPipeline(self.device, self.handle, None)
            self.handle = None
            
        if self.layout:
            vk.vkDestroyPipelineLayout(self.device, self.layout, None)
            self.layout = None

    def _create_shader_stages(
        self,
        vert_shader_module: vk.VkShaderModule,
        frag_shader_module: vk.VkShaderModule
    ) -> List[vk.VkPipelineShaderStageCreateInfo]:
        """Create shader stage create infos."""
        return [
            vk.VkPipelineShaderStageCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
                stage=vk.VK_SHADER_STAGE_VERTEX_BIT,
                module=vert_shader_module,
                pName="main"
            ),
            vk.VkPipelineShaderStageCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
                stage=vk.VK_SHADER_STAGE_FRAGMENT_BIT,
                module=frag_shader_module,
                pName="main"
            )
        ]

    def _create_vertex_input_info(self, config: PipelineConfigInfo) -> vk.VkPipelineVertexInputStateCreateInfo:
        """Create vertex input state create info."""
        return vk.VkPipelineVertexInputStateCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO,
            vertexBindingDescriptionCount=len(config.vertex_binding_descriptions),
            pVertexBindingDescriptions=config.vertex_binding_descriptions,
            vertexAttributeDescriptionCount=len(config.vertex_attribute_descriptions),
            pVertexAttributeDescriptions=config.vertex_attribute_descriptions
        )

    # ... Additional helper methods for creating pipeline state info structures ...