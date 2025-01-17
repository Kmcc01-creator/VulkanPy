import vulkan as vk
import logging
from typing import Any
from vulkan_engine.vulkan_engine import VulkanEngine
from vulkan_renderer.render_manager import RenderManager
from src.ecs.world import World
from src.ecs.systems import RenderSystem, CameraSystem
from src.ecs.components import Transform, Mesh, Material, Camera, Light, Shader
from src.shader_manager import ShaderManager
from src.mesh_renderer import MeshRenderer, MeshType
import numpy as np
import glfw
import glm
import ctypes

logger = logging.getLogger(__name__)

class UniformBufferObject(ctypes.Structure):
    _fields_ = [
        ("model", glm.mat4),
        ("view", glm.mat4),
        ("proj", glm.mat4),
    ]

class LightUBO(ctypes.Structure):
    _fields_ = [
        ("lightPos", glm.vec3),
        ("viewPos", glm.vec3),
        ("lightColor", glm.vec3),
    ]

class VulkanRenderer:
    def __init__(self, window: Any) -> None:
        self.window = window
        logger.info("Initializing VulkanRenderer")
        try:
            self.vulkan_engine = VulkanEngine(window)
            self.shader_manager = ShaderManager(self.vulkan_engine.device)
            self.render_manager = RenderManager(self.vulkan_engine, self.shader_manager)
            self.world: World = World()

            glfw.set_framebuffer_size_callback(window, self.framebuffer_resize_callback)

            self.init_world()
            self.load_shaders()
            self.create_uniform_buffers()
            self.create_descriptor_sets()
            logger.info("VulkanRenderer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize VulkanRenderer: {str(e)}")
            self.cleanup()
            raise

    def create_uniform_buffers(self):
        buffer_size = ctypes.sizeof(UniformBufferObject)
        self.uniform_buffers = []
        for _ in range(len(self.vulkan_engine.swapchain.swapchain_images)):
            buffer, memory = self.vulkan_engine.resource_manager.create_buffer(
                buffer_size,
                vk.VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT,
                vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT
            )
            self.uniform_buffers.append((buffer, memory))

        light_buffer_size = ctypes.sizeof(LightUBO)
        self.light_uniform_buffer, self.light_uniform_buffer_memory = self.vulkan_engine.resource_manager.create_buffer(
            light_buffer_size,
            vk.VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT,
            vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT
        )

    def create_descriptor_sets(self):
        # Update this method to include the new light uniform buffer
        # You'll need to modify the descriptor set layout and allocation to include the new buffer
        pass

    def update_uniform_buffer(self, current_image):
        ubo = UniformBufferObject()
        ubo.model = glm.mat4()
        ubo.view = self.camera.get_view_matrix()
        ubo.proj = self.camera.get_projection_matrix()

        data = self.vulkan_engine.resource_manager.map_memory(self.uniform_buffers[current_image][1])
        ctypes.memmove(data, ctypes.addressof(ubo), ctypes.sizeof(ubo))
        self.vulkan_engine.resource_manager.unmap_memory(self.uniform_buffers[current_image][1])

        light_ubo = LightUBO()
        light_ubo.lightPos = self.light.position
        light_ubo.viewPos = self.camera.position
        light_ubo.lightColor = self.light.color

        light_data = self.vulkan_engine.resource_manager.map_memory(self.light_uniform_buffer_memory)
        ctypes.memmove(light_data, ctypes.addressof(light_ubo), ctypes.sizeof(light_ubo))
        self.vulkan_engine.resource_manager.unmap_memory(self.light_uniform_buffer_memory)

    def load_shaders(self) -> None:
        try:
            self.shader_manager.load_shader('default', 'shaders/default.vert', 'shaders/default.frag')
            self.shader_manager.load_shader('pbr', 'shaders/pbr.vert', 'shaders/pbr.frag')
        except Exception as e:
            logger.error(f"Failed to load shaders: {str(e)}")
            raise

    def init_world(self) -> None:
        try:
            self.render_system = RenderSystem(self)
            self.camera_system = CameraSystem(self)
            self.world.add_system(self.camera_system)
            self.world.add_system(self.render_system)

            self.create_camera()
            self.create_light()
            self.create_objects()
            self.create_custom_mesh()
            
            logger.info("World initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize world: {e}")
            raise

    def create_camera(self) -> None:
        camera_entity = self.world.create_entity()
        self.camera_component = Camera()
        self.world.add_component(camera_entity, self.camera_component)
        self.world.add_component(camera_entity, Transform(position=np.array([0.0, 0.0, -5.0]), rotation=np.array([0.0, 0.0, 0.0]), scale=np.array([1.0, 1.0, 1.0])))

    def create_light(self) -> None:
        light_entity = self.world.create_entity()
        self.world.add_component(light_entity, Light(position=np.array([5.0, 5.0, 5.0]), color=np.array([1.0, 1.0, 1.0]), intensity=1.0))
        self.world.add_component(light_entity, Transform(position=np.array([5.0, 5.0, 5.0]), rotation=np.array([0.0, 0.0, 0.0]), scale=np.array([1.0, 1.0, 1.0])))

    def create_objects(self) -> None:
        self.create_mesh_entity(MeshType.SPHERE, np.array([0.0, 0.0, 0.0]))
        self.create_mesh_entity(MeshType.CUBE, np.array([2.0, 0.0, 0.0]))
        self.create_mesh_entity(MeshType.CYLINDER, np.array([-2.0, 0.0, 0.0]))

    def create_custom_mesh(self) -> None:
        def custom_function(u: float, v: float) -> float:
            return np.sin(u) * np.cos(v)
        
        custom_mesh = MeshRenderer.from_function(custom_function, (-np.pi, np.pi), (-np.pi, np.pi), 32)
        self.create_mesh_entity(MeshType.CUSTOM, np.array([0.0, 2.0, 0.0]), custom_mesh)

    def create_mesh_entity(self, mesh_type: MeshType, position: np.ndarray, custom_mesh: MeshRenderer = None) -> None:
        entity = self.world.create_entity()
        mesh_renderer = custom_mesh if custom_mesh else MeshRenderer(mesh_type)
        mesh = Mesh(mesh_renderer=mesh_renderer)
        mesh.create_buffers(self.vulkan_engine.resource_manager)
        self.world.add_component(entity, mesh)
        self.world.add_component(entity, Material(albedo=np.array([0.7, 0.7, 0.7]), metallic=0.5, roughness=0.5, ao=1.0))
        self.world.add_component(entity, Transform(position=position, rotation=np.array([0.0, 0.0, 0.0]), scale=np.array([1.0, 1.0, 1.0])))
        self.world.add_component(entity, Shader(vertex_shader='pbr', fragment_shader='pbr'))

    def render(self) -> None:
        try:
            self.render_manager.render(self.world)
        except vk.VkError as e:
            logger.error(f"Vulkan error during rendering: {str(e)}")
            self.vulkan_engine.recreate_swapchain()
        except Exception as e:
            logger.error(f"Unexpected error during rendering: {str(e)}")
            raise

    def framebuffer_resize_callback(self, window: Any, width: int, height: int) -> None:
        self.vulkan_engine.recreate_swapchain()

    def cleanup(self) -> None:
        logger.info("Cleaning up VulkanRenderer")
        if hasattr(self, 'shader_manager'):
            self.shader_manager.cleanup()
        if hasattr(self, 'render_manager'):
            self.render_manager.cleanup()
        if hasattr(self, 'vulkan_engine'):
            self.vulkan_engine.cleanup()
