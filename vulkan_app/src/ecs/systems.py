import vulkan as vk

class RenderSystem:
    def __init__(self, renderer):
        self.renderer = renderer

    def update(self, world):
        from src.vertex import Vertex
        import numpy as np

        self.vertices = [
            Vertex(np.array([-0.5, -0.5, 0.0]), np.array([1.0, 0.0, 0.0])),
            Vertex(np.array([0.5, -0.5, 0.0]), np.array([0.0, 1.0, 0.0])),
            Vertex(np.array([0.0, 0.5, 0.0]), np.array([0.0, 0.0, 1.0])),
        ]
        self.vertex_count = len(self.vertices)
        buffer_size = Vertex.sizeof() * self.vertex_count

        # Create staging buffer
        staging_buffer, staging_buffer_memory = self.renderer.create_buffer(buffer_size, vk.VK_BUFFER_USAGE_TRANSFER_SRC_BIT, vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)

        # Copy vertex data to staging buffer
        data_ptr = vk.vkMapMemory(self.renderer.device, staging_buffer_memory, 0, buffer_size, 0)
        vk.ffi.memmove(data_ptr, Vertex.as_bytes(self.vertices), buffer_size)
        vk.vkUnmapMemory(self.renderer.device, staging_buffer_memory)

        # Create vertex buffer on device
        self.vertex_buffer, self.vertex_buffer_memory = self.renderer.create_buffer(buffer_size, vk.VK_BUFFER_USAGE_TRANSFER_DST_BIT | vk.VK_BUFFER_USAGE_VERTEX_BUFFER_BIT, vk.VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT)

        # Copy data from staging buffer to vertex buffer
        self.renderer.copy_buffer(staging_buffer, self.vertex_buffer, buffer_size)

        # Destroy staging buffer
        vk.vkDestroyBuffer(self.renderer.device, staging_buffer, None)
        vk.vkFreeMemory(self.renderer.device, staging_buffer_memory, None)

    def render(self, command_buffer, world):
        vk.vkCmdBindVertexBuffers(command_buffer, 0, 1, [self.vertex_buffer], [0])
        vk.vkCmdDraw(command_buffer, self.vertex_count, 1, 0, 0)
