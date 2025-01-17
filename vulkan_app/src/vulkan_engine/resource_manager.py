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
            if resource is not None:  # Check if resource is not None
                cleanup_function(self.device, resource, None)

    def destroy_swapchain(self, swapchain):
        vk.vkDestroySwapchainKHR(self.device, swapchain, None)
        self.resources.remove((swapchain, "swapchain", self.destroy_swapchain)) # Remove from resources list

    def destroy_framebuffer(self, framebuffer):
        vk.vkDestroyFramebuffer(self.device, framebuffer, None)

    def destroy_pipeline(self, pipeline):
        vk.vkDestroyPipeline(self.device, pipeline, None)

    def destroy_pipeline_layout(self, pipeline_layout):
        vk.vkDestroyPipelineLayout(self.device, pipeline_layout, None)

    def destroy_render_pass(self, render_pass):
        vk.vkDestroyRenderPass(self.device, render_pass, None)

    def destroy_image_view(self, image_view):
        vk.vkDestroyImageView(self.device, image_view, None)

    def destroy_buffer(self, buffer):
        vk.vkDestroyBuffer(self.device, buffer, None)

    def free_memory(self, memory):
        vk.vkFreeMemory(self.device, memory, None)

    def destroy_descriptor_pool(self, descriptor_pool):
        vk.vkDestroyDescriptorPool(self.device, descriptor_pool, None)

    def destroy_descriptor_set_layout(self, descriptor_set_layout):
        vk.vkDestroyDescriptorSetLayout(self.device, descriptor_set_layout, None)

    def destroy_semaphore(self, semaphore):
        vk.vkDestroySemaphore(self.device, semaphore, None)

    def destroy_fence(self, fence):
        vk.vkDestroyFence(self.device, fence, None)

    def destroy_command_pool(self, command_pool):
        vk.vkDestroyCommandPool(self.device, command_pool, None)
