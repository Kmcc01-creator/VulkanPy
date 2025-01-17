import vulkan as vk
from src.ecs.components import Mesh

class RenderSystem:
    def __init__(self, renderer):
        self.renderer = renderer


    def render(self, command_buffer, world):
        for entity in world.entities:
            mesh = world.get_component(entity, Mesh)
            if mesh:
                vk.vkCmdBindVertexBuffers(command_buffer, 0, 1, [mesh.vertex_buffer], [0]) # Assuming mesh.vertex_buffer exists
                vk.vkCmdDraw(command_buffer, mesh.vertex_count, 1, 0, 0) # Assuming mesh.vertex_count exists

class CameraSystem:
    def __init__(self, renderer):
        self.renderer = renderer

    def update(self, world):
        from pyglm import lookAt
        for entity in world.entities:
            camera = world.get_component(entity, Camera)
            if camera:
                view_matrix = lookAt(camera.position, camera.target, camera.up)
                # TODO: Update uniform buffer with view matrix
