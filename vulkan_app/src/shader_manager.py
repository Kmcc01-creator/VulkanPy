import vulkan as vk
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ShaderManager:
    def __init__(self, resource_manager):
        self.resource_manager = resource_manager
        self.device = resource_manager.device # Access device through resource manager
        self.shaders: Dict[str, Dict[str, vk.VkShaderModule]] = {}

    def load_shader(self, name: str, vertex_path: str, fragment_path: str) -> None:
        try:
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
            logger.info(f"Shader '{name}' loaded successfully")
        except IOError as e:
            logger.error(f"Failed to load shader '{name}': {str(e)}")
            raise
        except vk.VkError as e:
            logger.error(f"Failed to create shader module for '{name}': {str(e)}")
            raise

    def create_shader_module(self, code: bytes) -> vk.VkShaderModule:
        create_info = vk.VkShaderModuleCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
            codeSize=len(code),
            pCode=code
        )
        try:
            module = self.resource_manager.create_shader_module(code) # Use resource manager
            return module
        except vk.VkError as e:
            logger.error(f"Failed to create shader module: {str(e)}")
            raise

    def get_shader(self, name: str) -> Dict[str, vk.VkShaderModule]:
        shader = self.shaders.get(name)
        if shader is None:
            logger.warning(f"Shader '{name}' not found")
        return shader

    def cleanup(self) -> None:
        logger.info("Cleaning up ShaderManager resources")
        # Shader modules are now destroyed by the resource manager
        self.shaders.clear()
