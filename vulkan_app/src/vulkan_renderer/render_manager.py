import vulkan as vk

class RenderManager:
    def __init__(self, vulkan_engine):
        self.vulkan_engine = vulkan_engine
        self.device = vulkan_engine.device

    def init_rendering(self, renderer):
        self.create_command_pool()
        self.create_command_buffers(renderer.swapchain.framebuffers)
        self.create_sync_objects(len(renderer.swapchain.swapchain_images))

    def create_command_pool(self):
        from vulkan_engine.command_buffer import create_command_pool as create_vk_command_pool
        self.command_pool = create_vk_command_pool(self.device, self.vulkan_engine.graphics_queue_family_index)
        self.vulkan_engine.resource_manager.add_resource(self.command_pool, "command_pool", self.vulkan_engine.resource_manager.destroy_command_pool)

    def create_command_buffers(self, framebuffers):
        from vulkan_engine.command_buffer import create_command_buffers as create_vk_command_buffers
        self.command_buffers = create_vk_command_buffers(self.device, self.command_pool, len(framebuffers))

    def create_sync_objects(self, swapchain_image_count):
        from vulkan_engine.synchronization import create_sync_objects as create_vk_sync_objects
        self.image_available_semaphores, self.render_finished_semaphores, self.in_flight_fences = create_vk_sync_objects(self.device, swapchain_image_count, self.vulkan_engine.resource_manager)

