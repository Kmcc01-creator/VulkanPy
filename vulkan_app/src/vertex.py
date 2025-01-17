import vulkan as vk

class Vertex:
    def __init__(self, pos, color):
        self.pos = pos
        self.color = color

    def get_binding_descriptions():
        bindings = []
        # Position and color binding description
        bindings.append(
            vk.VkVertexInputBindingDescription(
                binding=0,
                stride=2 * 4 * 3,  # Position (vec3) + Color (vec3) = 6 floats * 4 bytes/float
                inputRate=vk.VK_VERTEX_INPUT_RATE_VERTEX,
            )
        )
        return bindings

    def get_attribute_descriptions():
        attributes = []
        # Position attribute description
        attributes.append(
            vk.VkVertexInputAttributeDescription(
                location=0,
                binding=0,
                format=vk.VK_FORMAT_R32G32B32_SFLOAT,  # vec3
                offset=0,
            )
        )
        # Color attribute description
        attributes.append(
            vk.VkVertexInputAttributeDescription(
                location=1,
                binding=0,
                format=vk.VK_FORMAT_R32G32B32_SFLOAT,  # vec3
                offset=3 * 4,  # Offset after position (3 floats * 4 bytes/float)
            )
        )

        return attributes
