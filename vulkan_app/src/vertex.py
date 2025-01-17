import vulkan as vk
import numpy as np

class Vertex:
    def __init__(self, pos: np.ndarray, color: np.ndarray):
        self.pos = pos
        self.color = color

    @staticmethod
    def sizeof():
        return 2 * 4 * 3 # vec3 pos + vec3 color

    @staticmethod
    def get_binding_descriptions():
        bindings = []
        bindings.append(
            vk.VkVertexInputBindingDescription(
                binding=0,
                stride=Vertex.sizeof(),
                inputRate=vk.VK_VERTEX_INPUT_RATE_VERTEX,
            )
        )
        return bindings

    @staticmethod
    def get_attribute_descriptions():
        attributes = []
        attributes.append(
            vk.VkVertexInputAttributeDescription(
                location=0,
                binding=0,
                format=vk.VK_FORMAT_R32G32B32_SFLOAT,
                offset=0,
            )
        )
        attributes.append(
            vk.VkVertexInputAttributeDescription(
                location=1,
                binding=0,
                format=vk.VK_FORMAT_R32G32B32_SFLOAT,
                offset=4 * 3, # Offset of color after position
            )
        )
        return attributes

    @staticmethod
    def as_bytes(vertices):
        buffer = bytearray()
        for vertex in vertices:
            buffer.extend(vertex.pos.astype(np.float32).tobytes())
            buffer.extend(vertex.color.astype(np.float32).tobytes())
        return buffer
