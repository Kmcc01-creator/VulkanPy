import vulkan as vk
import logging
from typing import Any, List, Tuple
from vulkan_engine.vulkan_engine import VulkanEngine
from vulkan_renderer.render_manager import RenderManager
from src.ecs.world import World
from src.ecs.systems import RenderSystem, CameraSystem
from src.ecs.components import Transform, Mesh, Material, Camera, Light, Shader
from src.shader_manager import ShaderManager
from src.mesh_renderer import MeshRenderer, MeshType
import numpy as np
import glfw

logger = logging.getLogger(__name__)

class VulkanRenderer:
    def __init__(self, window: Any) -> None:
        self.window = window
        logger.info("Initializing VulkanRenderer")
        try:
            self.vulkan_engine = VulkanEngine(window)
            self.shader_manager = ShaderManager(self.vulkan_engine.device)
            self.render_manager = RenderManager(self.vulkan_engine, self.shader_manager)
            self.current_frame = 0
            self.world: World

            glfw.set_framebuffer_size_callback(window, self.framebuffer_resize_callback)

            self.init_world()
            self.load_shaders()
            logger.info("VulkanRenderer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize VulkanRenderer: {str(e)}")
            raise

    def load_shaders(self) -> None:
        try:
            self.shader_manager.load_shader('default', 'shaders/default.vert', 'shaders/default.frag')
            self.shader_manager.load_shader('pbr', 'shaders/pbr.vert', 'shaders/pbr.frag')
        except Exception as e:
            logger.error(f"Failed to load shaders: {str(e)}")
            raise

    def init_world(self) -> None:
        try:
            self.world = World()
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
        self.render_manager.render(self.world)

    def framebuffer_resize_callback(self, window: Any, width: int, height: int) -> None:
        self.vulkan_engine.recreate_swapchain()

    def cleanup(self) -> None:
        self.vulkan_engine.cleanup()

    def record_command_buffer(self, command_buffer: vk.VkCommandBuffer, image_index: int) -> None:
        begin_info = vk.VkCommandBufferBeginInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
        )

        try:
            vk.vkBeginCommandBuffer(command_buffer, begin_info)
        except vk.VkError as e:
            logger.error(f"Failed to begin recording command buffer: {e}")
            raise

        render_pass_begin_info = vk.VkRenderPassBeginInfo(
            sType=vk.VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO,
            renderPass=self.render_pass,
            framebuffer=self.framebuffers[image_index],
            renderArea=vk.VkRect2D(
                offset=vk.VkOffset2D(x=0, y=0),
                extent=self.swapchain_extent,
            ),
            clearValueCount=1,
            pClearValues=[vk.VkClearValue(color=vk.VkClearColorValue(float32=[0.0, 0.0, 0.0, 1.0]))],
        )

        vk.vkCmdBeginRenderPass(command_buffer, render_pass_begin_info, vk.VK_SUBPASS_CONTENTS_INLINE)
        vk.vkCmdBindPipeline(command_buffer, vk.VK_PIPELINE_BIND_POINT_GRAPHICS, self.pipeline)
        vk.vkCmdBindDescriptorSets(command_buffer, vk.VK_PIPELINE_BIND_POINT_GRAPHICS, self.pipeline_layout, 0, 1, self.descriptor_sets, 0, None)

        viewport = vk.VkViewport(
            x=0.0,
            y=0.0,
            width=float(self.swapchain_extent.width),
            height=float(self.swapchain_extent.height),
            minDepth=0.0,
            maxDepth=1.0,
        )
        vk.vkCmdSetViewport(command_buffer, 0, 1, [viewport])

        scissor = vk.VkRect2D(
            offset=vk.VkOffset2D(x=0, y=0),
            extent=self.swapchain_extent,
        )
        vk.vkCmdSetScissor(command_buffer, 0, 1, [scissor])

        self.render_system.render(command_buffer, self.world)
        vk.vkCmdEndRenderPass(command_buffer)

        try:
            vk.vkEndCommandBuffer(command_buffer)
        except vk.VkError as e:
            logger.error(f"Failed to end recording command buffer: {e}")
            raise

    def cleanup(self) -> None:
        logger.info("Cleaning up VulkanRenderer")
        self.shader_manager.cleanup()
        self.render_manager.cleanup()
        self.vulkan_engine.cleanup()
