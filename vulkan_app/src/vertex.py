from dataclasses import dataclass
import vulkan as vk
import numpy as np

@dataclass
class Vertex:
    pos: np.ndarray
    normal: np.ndarray
    color: np.ndarray

    @staticmethod
    def sizeof():
        return 3 * 4 * 3  # vec3 pos + vec3 normal + vec3 color

    @staticmethod
    def get_binding_descriptions():
        return [
            vk.VkVertexInputBindingDescription(
                binding=0,
                stride=Vertex.sizeof(),
                inputRate=vk.VK_VERTEX_INPUT_RATE_VERTEX,
            )
        ]

    @staticmethod
    def get_attribute_descriptions():
        return [
            vk.VkVertexInputAttributeDescription(
                location=0,
                binding=0,
                format=vk.VK_FORMAT_R32G32B32_SFLOAT,
                offset=0,
            ),
            vk.VkVertexInputAttributeDescription(
                location=1,
                binding=0,
                format=vk.VK_FORMAT_R32G32B32_SFLOAT,
                offset=4 * 3,  # Offset of normal after position
            ),
            vk.VkVertexInputAttributeDescription(
                location=2,
                binding=0,
                format=vk.VK_FORMAT_R32G32B32_SFLOAT,
                offset=4 * 6,  # Offset of color after normal
            )
        ]

    @staticmethod
    def as_bytes(vertices):
        buffer = bytearray()
        for vertex in vertices:
            buffer.extend(vertex.pos.astype(np.float32).tobytes())
            buffer.extend(vertex.normal.astype(np.float32).tobytes())
            buffer.extend(vertex.color.astype(np.float32).tobytes())
        return buffer
