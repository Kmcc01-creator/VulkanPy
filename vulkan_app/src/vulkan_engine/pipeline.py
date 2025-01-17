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


def create_pipeline(device, swapchain_extent, render_pass): # Added render_pass
    # ... (Load shader code from shader.vert and shader.frag) ...
    with open("vulkan_app/shaders/shader.vert", "rb") as f:
        vert_shader_code = f.read()
    with open("vulkan_app/shaders/shader.frag", "rb") as f:
        frag_shader_code = f.read()


    vert_shader_module = create_shader_module(device, vert_shader_code)
    frag_shader_module = create_shader_module(device, frag_shader_code)

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

    # ... (Pipeline layout create info) ...
    pipeline_layout_create_info = vk.VkPipelineLayoutCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
    )

    pipeline_layout = vk.vkCreatePipelineLayout(device, pipeline_layout_create_info, None)


    # ... (Pipeline create info) ...
    pipeline_create_info = vk.VkGraphicsPipelineCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO,
        stageCount=len(shader_stages),
        pStages=shader_stages,
        pVertexInputState=None,  # Add vertex input state
        pInputAssemblyState=None,  # Add input assembly state
        pViewportState=None,      # Add viewport state
        pRasterizationState=None,  # Add rasterization state
        pMultisampleState=None,   # Add multisample state
        pDepthStencilState=None,  # Add depth stencil state
        pColorBlendState=None,    # Add color blend state
        pDynamicState=None,      # Add dynamic state
        layout=pipeline_layout,
        renderPass=render_pass,   # Set render pass
        subpass=0,
    )

    # ... (Create graphics pipeline) ...
    try:
        graphics_pipeline = vk.vkCreateGraphicsPipelines(device, None, 1, [pipeline_create_info], None)[0]
        return graphics_pipeline
    except vk.VkError as e:
        raise Exception(f"Failed to create graphics pipeline: {e}")

    # ... (Destroy shader modules) ...
    vk.vkDestroyShaderModule(device, vert_shader_module, None)
    vk.vkDestroyShaderModule(device, frag_shader_module, None)
