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
            self.descriptor_sets = self.vulkan_engine.resource_manager.create_descriptor_sets(
                self.vulkan_engine.resource_manager.descriptor_pool,
                self.vulkan_engine.descriptor_set_layout,
                self.camera_uniform_buffers, self.light_uniform_buffers
            )
            logger.info("VulkanRenderer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize VulkanRenderer: {str(e)}")
            self.cleanup()
            raise


    def create_uniform_buffers(self):
        camera_buffer_size = ctypes.sizeof(UniformBufferObject)
        light_buffer_size = ctypes.sizeof(LightUBO)
        material_buffer_size = 4 * 4 + 4 * 3  # vec3 albedo + float metallic + float roughness + float ao
        self.camera_uniform_buffers = []
        self.light_uniform_buffers = []
        self.material_uniform_buffers = []
        for _ in range(len(self.vulkan_engine.swapchain.swapchain_images)):
            camera_buffer, camera_memory = self.vulkan_engine.resource_manager.create_buffer(
                camera_buffer_size,
                vk.VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT,
                vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT
            )
            self.camera_uniform_buffers.append((camera_buffer, camera_memory))

            light_buffer, light_memory = self.vulkan_engine.resource_manager.create_buffer(
                light_buffer_size,
                vk.VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT,
                vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT
            )
            self.light_uniform_buffers.append((light_buffer, light_memory))

            material_buffer, material_memory = self.vulkan_engine.resource_manager.create_buffer(
                material_buffer_size,
                vk.VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT,
                vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT
            )
            self.material_uniform_buffers.append((material_buffer, material_memory))

    def create_descriptor_sets(self):
        descriptor_sets_layout = self.vulkan_engine.descriptor_set_layout
        descriptor_pool = self.vulkan_engine.swapchain.descriptor_pool
        
        layouts = [descriptor_sets_layout.layout] * len(self.camera_uniform_buffers)
        alloc_info = vk.VkDescriptorSetAllocateInfo(
            sType=vk.VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
            descriptorPool=descriptor_pool,
            descriptorSetCount=len(self.camera_uniform_buffers),
            pSetLayouts=layouts,
        )
        self.descriptor_sets = vk.vkAllocateDescriptorSets(self.vulkan_engine.device, alloc_info)

        for i, (camera_buffer, light_buffer) in enumerate(zip(self.camera_uniform_buffers, self.light_uniform_buffers)):
            camera_buffer_info = vk.VkDescriptorBufferInfo(
                buffer=camera_buffer[0],
                offset=0,
                range=ctypes.sizeof(UniformBufferObject),
            )
            light_buffer_info = vk.VkDescriptorBufferInfo(
                buffer=light_buffer[0],
                offset=0,
                range=ctypes.sizeof(LightUBO),
            )

            write_descriptor_sets = [
                vk.VkWriteDescriptorSet(
                    sType=vk.VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
                    dstSet=self.descriptor_sets[i],
                    dstBinding=0,
                    dstArrayElement=0,
                    descriptorCount=1,
                    descriptorType=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
                    pBufferInfo=[camera_buffer_info],
                ),
                vk.VkWriteDescriptorSet(
                    sType=vk.VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
                    dstSet=self.descriptor_sets[i],
                    dstBinding=1,
                    dstArrayElement=0,
                    descriptorCount=1,
                    descriptorType=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
                    pBufferInfo=[light_buffer_info],
                )
            ]

            vk.vkUpdateDescriptorSets(self.vulkan_engine.device, len(write_descriptor_sets), write_descriptor_sets, 0, None)

    def update_uniform_buffer(self, current_image):
        camera_ubo = UniformBufferObject()
        camera_ubo.model = glm.mat4()
        camera_ubo.view = self.camera_component.get_view_matrix()
        camera_ubo.proj = self.camera_component.get_projection_matrix()

        camera_data = self.vulkan_engine.resource_manager.map_memory(self.camera_uniform_buffers[current_image][1])
        ctypes.memmove(camera_data, ctypes.addressof(camera_ubo), ctypes.sizeof(camera_ubo))
        self.vulkan_engine.resource_manager.unmap_memory(self.camera_uniform_buffers[current_image][1])

        light_ubo = LightUBO()
        light_ubo.lightPos = self.light.position
        light_ubo.viewPos = self.camera_component.position
        light_ubo.lightColor = self.light.color

        light_data = self.vulkan_engine.resource_manager.map_memory(self.light_uniform_buffers[current_image][1])
        ctypes.memmove(light_data, ctypes.addressof(light_ubo), ctypes.sizeof(light_ubo))
        self.vulkan_engine.resource_manager.unmap_memory(self.light_uniform_buffers[current_image][1])

        # Update material uniform buffer
        for entity, (mesh, material) in self.world.get_components(Mesh, Material):
            material_data = self.vulkan_engine.resource_manager.map_memory(self.material_uniform_buffers[current_image][1])
            material_buffer = material.to_uniform_buffer()
            ctypes.memmove(material_data, material_buffer.ctypes.data, material_buffer.nbytes)
            self.vulkan_engine.resource_manager.unmap_memory(self.material_uniform_buffers[current_image][1])

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
