import vulkan as vk
import logging
from vulkan_engine.descriptors import DescriptorSetLayout
from src.vertex import Vertex

logger = logging.getLogger(__name__)

class Pipeline:
    def __init__(self, resource_manager):
        self.resource_manager = resource_manager
        self.device = resource_manager.device

    def create_shader_module(self, shader_code):
        create_info = vk.VkShaderModuleCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
            codeSize=len(shader_code),
            pCode=shader_code,
        )

        try:
            return self.resource_manager.create_shader_module(create_info)
        except vk.VkError as e:
            logger.error(f"Failed to create shader module: {e}")
            raise

    def create_graphics_pipeline(self, swapchain_extent, render_pass):
        try:
            with open("vulkan_app/shaders/vert.spv", "rb") as f:
                vert_shader_code = f.read()
            with open("vulkan_app/shaders/frag.spv", "rb") as f:
                frag_shader_code = f.read()
        except IOError as e:
            logger.error(f"Failed to read shader files: {e}")
            raise

        vert_shader_module = self.create_shader_module(vert_shader_code)
        frag_shader_module = self.create_shader_module(frag_shader_code)

        shader_stages = [
            vk.VkPipelineShaderStageCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
                stage=vk.VK_SHADER_STAGE_VERTEX_BIT,
                module=vert_shader_module,
                pName="main",
            ),
            vk.VkPipelineShaderStageCreateInfo(
                sType=vk.VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
                stage=vk.VK_SHADER_STAGE_FRAGMENT_BIT,
                module=frag_shader_module,
                pName="main",
            ),
        ]

        bindings = [
            vk.VkDescriptorSetLayoutBinding(
                binding=0,
                descriptorType=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
                descriptorCount=1,
                stageFlags=vk.VK_SHADER_STAGE_VERTEX_BIT,
            ),
            vk.VkDescriptorSetLayoutBinding(
                binding=1,
                descriptorType=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
                descriptorCount=1,
                stageFlags=vk.VK_SHADER_STAGE_FRAGMENT_BIT,
            ),
        ]

        descriptor_set_layout = self.resource_manager.create_descriptor_set_layout(bindings)

        push_constant_range = vk.VkPushConstantRange(
            stageFlags=vk.VK_SHADER_STAGE_VERTEX_BIT,
            offset=0,
            size=4 * 4 * 4,  # mat4
        )

        pipeline_layout_create_info = vk.VkPipelineLayoutCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
            setLayoutCount=1,
            pSetLayouts=[descriptor_set_layout],
            pushConstantRangeCount=1,
            pPushConstantRanges=[push_constant_range],
        )

        pipeline_layout = self.resource_manager.create_pipeline_layout(pipeline_layout_create_info)

        vertex_input_bindings = Vertex.get_binding_descriptions()
        vertex_input_attributes = Vertex.get_attribute_descriptions()

        vertex_input_state = vk.VkPipelineVertexInputStateCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO,
            vertexBindingDescriptionCount=len(vertex_input_bindings),
            pVertexBindingDescriptions=vertex_input_bindings,
            vertexAttributeDescriptionCount=len(vertex_input_attributes),
            pVertexAttributeDescriptions=vertex_input_attributes,
        )

        input_assembly_state = vk.VkPipelineInputAssemblyStateCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO,
            topology=vk.VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST,
            primitiveRestartEnable=vk.VK_FALSE,
        )

        viewport_state = vk.VkPipelineViewportStateCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO,
            viewportCount=1,
            scissorCount=1,
        )

        rasterization_state = vk.VkPipelineRasterizationStateCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO,
            depthClampEnable=vk.VK_FALSE,
            rasterizerDiscardEnable=vk.VK_FALSE,
            polygonMode=vk.VK_POLYGON_MODE_FILL,
            cullMode=vk.VK_CULL_MODE_BACK_BIT,
            frontFace=vk.VK_FRONT_FACE_COUNTER_CLOCKWISE,
            depthBiasEnable=vk.VK_FALSE,
            lineWidth=1.0,
        )

        multisample_state = vk.VkPipelineMultisampleStateCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO,
            rasterizationSamples=vk.VK_SAMPLE_COUNT_1_BIT,
            sampleShadingEnable=vk.VK_FALSE,
        )

        color_blend_attachment_state = vk.VkPipelineColorBlendAttachmentState(
            blendEnable=vk.VK_FALSE,
            colorWriteMask=vk.VK_COLOR_COMPONENT_R_BIT | vk.VK_COLOR_COMPONENT_G_BIT | vk.VK_COLOR_COMPONENT_B_BIT | vk.VK_COLOR_COMPONENT_A_BIT,
        )

        color_blend_state = vk.VkPipelineColorBlendStateCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO,
            logicOpEnable=vk.VK_FALSE,
            attachmentCount=1,
            pAttachments=[color_blend_attachment_state],
        )

        dynamic_states = [vk.VK_DYNAMIC_STATE_VIEWPORT, vk.VK_DYNAMIC_STATE_SCISSOR]
        dynamic_state = vk.VkPipelineDynamicStateCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO,
            dynamicStateCount=len(dynamic_states),
            pDynamicStates=dynamic_states,
        )

        pipeline_create_info = vk.VkGraphicsPipelineCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO,
            stageCount=len(shader_stages),
            pStages=shader_stages,
            pVertexInputState=vertex_input_state,
            pInputAssemblyState=input_assembly_state,
            pViewportState=viewport_state,
            pRasterizationState=rasterization_state,
            pMultisampleState=multisample_state,
            pColorBlendState=color_blend_state,
            pDynamicState=dynamic_state,
            layout=pipeline_layout,
            renderPass=render_pass,
            subpass=0,
        )

        try:
            graphics_pipeline = self.resource_manager.create_graphics_pipeline(pipeline_create_info)
            logger.info("Graphics pipeline created successfully")
            return graphics_pipeline, pipeline_layout, descriptor_set_layout
        except vk.VkError as e:
            logger.error(f"Failed to create graphics pipeline: {e}")
            raise
        finally:
            self.resource_manager.destroy_shader_module(vert_shader_module)
            self.resource_manager.destroy_shader_module(frag_shader_module)

    def create_compute_pipeline(self, shader_path, descriptor_set_layout):
        try:
            with open(shader_path, "rb") as f:
                compute_shader_code = f.read()
        except IOError as e:
            logger.error(f"Failed to read compute shader file: {e}")
            raise

        compute_shader_module = self.create_shader_module(compute_shader_code)

        shader_stage = vk.VkPipelineShaderStageCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
            stage=vk.VK_SHADER_STAGE_COMPUTE_BIT,
            module=compute_shader_module,
            pName="main",
        )

        pipeline_layout_create_info = vk.VkPipelineLayoutCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
            setLayoutCount=1,
            pSetLayouts=[descriptor_set_layout],
        )

        pipeline_layout = self.resource_manager.create_pipeline_layout(pipeline_layout_create_info)

        pipeline_create_info = vk.VkComputePipelineCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO,
            stage=shader_stage,
            layout=pipeline_layout,
        )

        try:
            compute_pipeline = self.resource_manager.create_compute_pipeline(pipeline_create_info)
            logger.info("Compute pipeline created successfully")
            return compute_pipeline, pipeline_layout
        except vk.VkError as e:
            logger.error(f"Failed to create compute pipeline: {e}")
            raise
        finally:
            self.resource_manager.destroy_shader_module(compute_shader_module)
