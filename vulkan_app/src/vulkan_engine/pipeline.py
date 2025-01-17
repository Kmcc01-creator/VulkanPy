import vulkan as vk

def create_shader_module(device, shader_code):
    create_info = vk.VkShaderModuleCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
        codeSize=len(shader_code),
        pCode=shader_code,
    )

    try:
        return vk.vkCreateShaderModule(device, create_info, None)
    except vk.VkError as e:
        raise Exception(f"Failed to create shader module: {e}")


from vulkan_engine.descriptors import DescriptorSetLayout
from src.vertex import Vertex

def create_pipeline(device, swapchain_extent, render_pass, resource_manager): # Add resource_manager as parameter
    # ... (Load shader code from shader.vert and shader.frag) ...
    with open("vulkan_app/shaders/shader.vert", "rb") as f:
        vert_shader_code = f.read()
    with open("vulkan_app/shaders/shader.frag", "rb") as f:
        frag_shader_code = f.read()

    vert_shader_module = resource_manager.create_shader_module(vert_shader_code) # Use resource_manager to create shader modules
    frag_shader_module = resource_manager.create_shader_module(frag_shader_code)

    # ... (Shader stage create info) ...
    vert_shader_stage_info = vk.VkPipelineShaderStageCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
        stage=vk.VK_SHADER_STAGE_VERTEX_BIT,
        module=vert_shader_module,
        pName="main",
    )

    frag_shader_stage_info = vk.VkPipelineShaderStageCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
        stage=vk.VK_SHADER_STAGE_FRAGMENT_BIT,
        module=frag_shader_module,
        pName="main",
    )

    shader_stages = [vert_shader_stage_info, frag_shader_stage_info]

    # Create descriptor set layout
    bindings = []
    # MVP matrix uniform buffer
    bindings.append(
        vk.VkDescriptorSetLayoutBinding(
            binding=0,
            descriptorType=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
            descriptorCount=1,
            stageFlags=vk.VK_SHADER_STAGE_VERTEX_BIT,
        )
    )

    descriptor_set_layout_info = vk.VkDescriptorSetLayoutCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
        bindingCount=len(bindings),
        pBindings=bindings,
    )

    descriptor_set_layout = resource_manager.create_descriptor_set_layout(bindings) # Use resource_manager to create descriptor set layout

    # ... (Pipeline layout create info) ...
    push_constant_range = vk.VkPushConstantRange(
        stageFlags=vk.VK_SHADER_STAGE_VERTEX_BIT,
        offset=0,
        size=4 * 4 * 4, # mat4
    )

    pipeline_layout_create_info = vk.VkPipelineLayoutCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        setLayoutCount=1,
        pSetLayouts=[descriptor_set_layout.layout], # Access layout attribute
        pushConstantRangeCount=1,
        pPushConstantRanges=[push_constant_range],

    )
    vertex_input_bindings = Vertex.get_binding_descriptions()
    vertex_input_attributes = Vertex.get_attribute_descriptions()

    pipeline_layout = resource_manager.create_pipeline_layout(pipeline_layout_create_info) # Use resource_manager to create pipeline layout


    # Vertex Input state
    vertex_input_state = vk.VkPipelineVertexInputStateCreateInfo( # Using descriptions from Vertex class
        sType=vk.VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO,
        vertexBindingDescriptionCount=len(vertex_input_bindings),
        pVertexBindingDescriptions=vertex_input_bindings,
        vertexAttributeDescriptionCount=len(vertex_input_attributes),
        pVertexAttributeDescriptions=vertex_input_attributes,
    )

    # Input Assembly state
    input_assembly_state = vk.VkPipelineInputAssemblyStateCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO,
        topology=vk.VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST,
        primitiveRestartEnable=vk.VK_FALSE,
    )

    # Viewport and Scissor state (using dynamic states for now)
    viewport_state = vk.VkPipelineViewportStateCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO,
        viewportCount=1,
        scissorCount=1,
    )

    # Rasterization state
    rasterization_state = vk.VkPipelineRasterizationStateCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO,
        polygonMode=vk.VK_POLYGON_MODE_FILL,
        cullMode=vk.VK_CULL_MODE_BACK_BIT,
        frontFace=vk.VK_FRONT_FACE_COUNTER_CLOCKWISE,
        lineWidth=1.0,
    )

    # Multisampling state
    multisample_state = vk.VkPipelineMultisampleStateCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO,
        rasterizationSamples=vk.VK_SAMPLE_COUNT_1_BIT,
    )

    # Depth/Stencil state (if needed)
    # ...

    # Color blend state
    color_blend_attachment_state = vk.VkPipelineColorBlendAttachmentState(
        colorWriteMask=vk.VK_COLOR_COMPONENT_R_BIT | vk.VK_COLOR_COMPONENT_G_BIT | vk.VK_COLOR_COMPONENT_B_BIT | vk.VK_COLOR_COMPONENT_A_BIT,
        blendEnable=vk.VK_FALSE,  # Disable blending for now
    )

    color_blend_state = vk.VkPipelineColorBlendStateCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO,
        attachmentCount=1,
        pAttachments=[color_blend_attachment_state],
    )

    # Dynamic states (viewport and scissor)
    dynamic_states = [vk.VK_DYNAMIC_STATE_VIEWPORT, vk.VK_DYNAMIC_STATE_SCISSOR]
    dynamic_state = vk.VkPipelineDynamicStateCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO,
        dynamicStateCount=len(dynamic_states),
        pDynamicStates=dynamic_states,
    )


    # ... (Pipeline create info) ...
    pipeline_create_info = vk.VkGraphicsPipelineCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO,
        stageCount=len(shader_stages),
        pStages=shader_stages,
        pVertexInputState=vertex_input_state,
        pInputAssemblyState=input_assembly_state,
        pViewportState=viewport_state,
        pRasterizationState=rasterization_state,
        pMultisampleState=multisample_state,
        pDepthStencilState=None,  # Add depth stencil state if needed
        pColorBlendState=color_blend_state,
        pDynamicState=dynamic_state,
        layout=pipeline_layout,
        renderPass=render_pass,   # Set render pass
        subpass=0,
    )

    vertex_input_bindings = Vertex.get_binding_descriptions()
    vertex_input_attributes = Vertex.get_attribute_descriptions()

    # ... (Create graphics pipeline) ...
    try:
        graphics_pipeline = resource_manager.create_graphics_pipeline(pipeline_create_info) # Use resource_manager to create graphics pipeline
        return graphics_pipeline, pipeline_layout, descriptor_set_layout # Return descriptor_set_layout
    except vk.VkError as e:
        raise Exception(f"Failed to create graphics pipeline: {e}")

    # ... (Destroy shader modules) ...
    vk.vkDestroyShaderModule(device, vert_shader_module, None)
    vk.vkDestroyShaderModule(device, frag_shader_module, None)

    return graphics_pipeline, pipeline_layout, descriptor_set_layout # Returning descriptor set layout object
