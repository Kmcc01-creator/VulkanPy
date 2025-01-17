import vulkan as vk
import logging
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
    def __init__(self, window):
        self.window = window
        logger.info("Initializing VulkanRenderer")
        try:
            self.vulkan_engine = VulkanEngine(window)
            self.shader_manager = ShaderManager(self.vulkan_engine.device)
            self.render_manager = RenderManager(self.vulkan_engine, self.shader_manager)
            self.current_frame = 0

            glfw.set_framebuffer_size_callback(window, self.framebuffer_resize_callback)

            self.init_world()
            self.load_shaders()
            logger.info("VulkanRenderer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize VulkanRenderer: {str(e)}")
            raise

    def load_shaders(self):
        self.shader_manager.load_shader('default', 'shaders/default.vert', 'shaders/default.frag')
        self.shader_manager.load_shader('pbr', 'shaders/pbr.vert', 'shaders/pbr.frag')

    def init_world(self):
        self.world = World()
        self.render_system = RenderSystem(self)
        self.camera_system = CameraSystem(self)
        self.world.add_system(self.camera_system)
        self.world.add_system(self.render_system)

        # Camera
        camera_entity = self.world.create_entity()
        self.camera_component = Camera()
        self.world.add_component(camera_entity, self.camera_component)
        self.world.add_component(camera_entity, Transform(position=np.array([0.0, 0.0, -5.0]), rotation=np.array([0.0, 0.0, 0.0]), scale=np.array([1.0, 1.0, 1.0])))

        # Light
        light_entity = self.world.create_entity()
        self.world.add_component(light_entity, Light(position=np.array([5.0, 5.0, 5.0]), color=np.array([1.0, 1.0, 1.0]), intensity=1.0))
        self.world.add_component(light_entity, Transform(position=np.array([5.0, 5.0, 5.0]), rotation=np.array([0.0, 0.0, 0.0]), scale=np.array([1.0, 1.0, 1.0])))

        # Objects
        self.create_mesh_entity(MeshType.SPHERE, np.array([0.0, 0.0, 0.0]))
        self.create_mesh_entity(MeshType.CUBE, np.array([2.0, 0.0, 0.0]))
        self.create_mesh_entity(MeshType.CYLINDER, np.array([-2.0, 0.0, 0.0]))

        # Custom mesh
        def custom_function(u, v):
            return np.sin(u) * np.cos(v)
        
        custom_mesh = MeshRenderer.from_function(custom_function, (-np.pi, np.pi), (-np.pi, np.pi), 32)
        self.create_mesh_entity(MeshType.CUSTOM, np.array([0.0, 2.0, 0.0]), custom_mesh)

    def create_mesh_entity(self, mesh_type, position, custom_mesh=None):
        entity = self.world.create_entity()
        mesh_renderer = custom_mesh if custom_mesh else MeshRenderer(mesh_type)
        mesh = Mesh(mesh_renderer=mesh_renderer)
        mesh.create_buffers(self.vulkan_engine.resource_manager)
        self.world.add_component(entity, mesh)
        self.world.add_component(entity, Material(albedo=np.array([0.7, 0.7, 0.7]), metallic=0.5, roughness=0.5, ao=1.0))
        self.world.add_component(entity, Transform(position=position, rotation=np.array([0.0, 0.0, 0.0]), scale=np.array([1.0, 1.0, 1.0])))
        self.world.add_component(entity, Shader(vertex_shader='pbr', fragment_shader='pbr'))

    def render(self):
        self.render_manager.render(self.world)

    def framebuffer_resize_callback(self, window, width, height):
        self.vulkan_engine.recreate_swapchain()

    def cleanup(self):
        self.vulkan_engine.cleanup()

    def record_command_buffer(self, command_buffer, image_index):
        begin_info = vk.VkCommandBufferBeginInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
        )

        try:
            vk.vkBeginCommandBuffer(command_buffer, begin_info)
        except vk.VkError as e:
            raise Exception(f"Failed to begin recording command buffer: {e}")

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

        self.render_system.render(command_buffer, self.world) # Delegate rendering to RenderSystem
        vk.vkCmdEndRenderPass(command_buffer)

        try:
            vk.vkEndCommandBuffer(command_buffer)
        except vk.VkError as e:
            raise Exception(f"Failed to end recording command buffer: {e}")

        pool_sizes = []
        pool_sizes.append(vk.VkDescriptorPoolSize(type=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, descriptorCount=1))

        pool_create_info = vk.VkDescriptorPoolCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
            maxSets=1,
            poolSizeCount=len(pool_sizes),
            pPoolSizes=pool_sizes
        )

        self.descriptor_pool = vk.vkCreateDescriptorPool(self.device, pool_create_info, None)



        allocate_info = vk.VkCommandBufferAllocateInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
            level=vk.VK_COMMAND_BUFFER_LEVEL_PRIMARY,
            commandPool=self.command_pool,
            commandBufferCount=1,
        )
        command_buffer = vk.vkAllocateCommandBuffers(self.device, allocate_info)[0]

        begin_info = vk.VkCommandBufferBeginInfo(
            sType=vk.VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
            flags=vk.VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT,
        )
    # Removed copy_buffer method


        vk.vkEndCommandBuffer(command_buffer)

        submit_info = vk.VkSubmitInfo(
            sType=vk.VK_STRUCTURE_TYPE_SUBMIT_INFO,
            commandBufferCount=1,
            pCommandBuffers=[command_buffer],
        )
        vk.vkQueueSubmit(self.graphics_queue, 1, [submit_info], vk.VK_NULL_HANDLE)
        vk.vkQueueWaitIdle(self.graphics_queue)

        vk.vkFreeCommandBuffers(self.device, self.command_pool, 1, [command_buffer])

        for fence in self.in_flight_fences:
            vk.vkWaitForFences(self.device, 1, [fence], vk.VK_TRUE, 1000000000) # Wait for fence before destroying it
            vk.vkDestroyFence(self.device, fence, None)

        for semaphore in self.image_available_semaphores:
            vk.vkDestroySemaphore(self.device, semaphore, None)

        for semaphore in self.render_finished_semaphores:
            vk.vkDestroySemaphore(self.device, semaphore, None)


    def cleanup(self):
        self.vulkan_engine.cleanup()
