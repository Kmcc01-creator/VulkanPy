import vulkan as vk

def create_shader_module(device, code):
    create_info = vk.VkShaderModuleCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
        codeSize=len(code),
        pCode=code
    )
    try:
        module = vk.vkCreateShaderModule(device, create_info, None)
        return module
    except vk.VkError as e:
        print(f"Failed to create shader module: {str(e)}")
        raise
