import vulkan as vk

class ResourceManager:
    def __init__(self, renderer):
        self.renderer = renderer
        self.device = renderer.device
        self.resources = []

    def add_resource(self, resource, resource_type, cleanup_function):
        self.resources.append((resource, resource_type, cleanup_function))

    def cleanup(self):
        for resource, resource_type, cleanup_function in reversed(self.resources):
            cleanup_function(self.device, resource, None)
