import vulkan as vk
import os

class ShaderManager:
    def __init__(self, device):
        self.device = device
        self.shaders = {}

    def load_shader(self, name, vertex_path, fragment_path):
        with open(vertex_path, 'rb') as f:
            vertex_shader_code = f.read()
        with open(fragment_path, 'rb') as f:
            fragment_shader_code = f.read()

        vertex_shader_module = self.create_shader_module(vertex_shader_code)
        fragment_shader_module = self.create_shader_module(fragment_shader_code)

        self.shaders[name] = {
            'vertex': vertex_shader_module,
            'fragment': fragment_shader_module
        }

    def create_shader_module(self, code):
        create_info = vk.VkShaderModuleCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
            codeSize=len(code),
            pCode=code
        )
        return vk.vkCreateShaderModule(self.device, create_info, None)

    def get_shader(self, name):
        return self.shaders.get(name)

    def cleanup(self):
        for shader in self.shaders.values():
            vk.vkDestroyShaderModule(self.device, shader['vertex'], None)
            vk.vkDestroyShaderModule(self.device, shader['fragment'], None)
