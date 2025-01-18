import vulkan as vk
from src.ecs.components import Mesh

class RenderSystem:
    def __init__(self, renderer):
        self.renderer = renderer
        self.required_components = (Mesh,)  # Declare required components

    def render(self, command_buffer, world):
        for entity in world.entities:
            if all(world.get_component(entity, component) for component in self.required_components):
                mesh = world.get_component(entity, Mesh)
                vk.vkCmdBindVertexBuffers(command_buffer, 0, 1, [mesh.vertex_buffer], [0]) # Assuming mesh.vertex_buffer exists
                vk.vkCmdDrawIndexed(command_buffer, mesh.index_count, 1, 0, 0, 0) # Use indexed drawing

from src.ecs.components import Camera # Import Camera component
from src.ecs.components import Transform

class CameraSystem:
    def __init__(self, renderer):
        self.renderer = renderer
        self.required_components = (Camera, Transform) # Declare required components

    def update(self, world):
        from pyglm import lookAt, perspective
        for entity in world.entities:
            if all(world.get_component(entity, component) for component in self.required_components):
                camera = world.get_component(entity, Camera)
                transform = world.get_component(entity, Transform)
                view_matrix = lookAt(transform.position, transform.position + camera.target, camera.up)
                projection_matrix = perspective(camera.fov, camera.aspect, camera.near, camera.far)
                # Assuming your uniform buffer expects projection * view
                self.renderer.uniform_buffers[self.renderer.current_frame].update(projection_matrix * view_matrix) # Update uniform buffer
