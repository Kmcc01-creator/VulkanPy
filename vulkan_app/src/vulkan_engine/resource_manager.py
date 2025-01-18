import vulkan as vk
from src.vertex import Vertex
from src.vulkan_engine.vulkan_resources import VulkanBuffer, VulkanImage, VulkanCommandPool
from src.vulkan_engine.memory_allocator import MemoryAllocator
import logging
import ctypes
import glm
from src.ecs.components import Mesh, Material
from src.vulkan_engine.uniform_buffer_objects import UniformBufferObject, LightUBO

logger = logging.getLogger(__name__)

class ResourceManager:
    def __init__(self, renderer):
        self.renderer = renderer
        self.device = renderer.device
        self.physical_device = renderer.physical_device
        self.resources = {}
        self.descriptor_set_layouts = {}

    def create_instance(self): # New method to create Vulkan instance
        from vulkan_engine.instance import create_instance as create_vk_instance
        instance, enabled_layers = create_vk_instance()
        self.add_resource(instance, "instance") # Add instance to managed resources
        return instance, enabled_layers

    def create_pipeline_layout(self, create_info):
        pipeline_layout = vk.vkCreatePipelineLayout(self.device, create_info, None)
        self.add_resource(pipeline_layout, "pipeline_layout")
        return pipeline_layout

    def create_graphics_pipeline(self, create_info):
        try:
            graphics_pipelines = vk.vkCreateGraphicsPipelines(self.device, None, 1, [create_info], None)
            graphics_pipeline = graphics_pipelines[0]
            self.add_resource(graphics_pipeline, "graphics_pipeline")
            return graphics_pipeline
        except vk.VkError as e:
            logger.error(f"Failed to create graphics pipeline: {e}")
            raise

    def create_compute_pipeline(self, create_info):
        try:
            compute_pipelines = vk.vkCreateComputePipelines(self.device, None, 1, [create_info], None)
            compute_pipeline = compute_pipelines[0]
            self.add_resource(compute_pipeline, "compute_pipeline")
            return compute_pipeline
        except vk.VkError as e:
            logger.error(f"Failed to create compute pipeline: {e}")
            raise

    def create_descriptor_set_layout(self, bindings):
        layout_info = vk.VkDescriptorSetLayoutCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
            bindingCount=len(bindings),
            pBindings=bindings,
        )
        try:
            layout = vk.vkCreateDescriptorSetLayout(self.device, layout_info, None)
            self.add_resource(layout, "descriptor_set_layout")
            return layout
        except vk.VkError as e:
            logger.error(f"Failed to create descriptor set layout: {e}")
            raise

    def create_shader_module(self, create_info):
        try:
            module = vk.vkCreateShaderModule(self.device, create_info, None)
            self.add_resource(module, "shader_module")
            return module
        except vk.VkError as e:
            logger.error(f"Failed to create shader module: {e}")
            raise

    def destroy_shader_module(self, shader_module):
        vk.vkDestroyShaderModule(self.device, shader_module, None)
        self.remove_resource(shader_module, "shader_module")

    def __enter__(self): # No changes here
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup()

    def add_resource(self, resource, resource_type):
        if resource_type not in self.resources:
            self.resources[resource_type] = []
        self.resources[resource_type].append(resource)

    def cleanup(self):
        for resource_type, resources in self.resources.items():
            for resource in reversed(resources):
                try:
                    resource.destroy()
                except Exception as e:
                    logger.error(f"Failed to clean up {resource_type}: {e}")
        self.resources.clear()
        self.resource_cache.clear()

    def create_buffer(self, size, usage, memory_properties):
        cache_key = (size, usage, memory_properties)
        if cache_key in self.resource_cache:
            return self.resource_cache[cache_key]

        try:
            buffer = VulkanBuffer(self.device, size, usage, memory_properties, self.memory_allocator)
            self.add_resource(buffer, "buffer")
            self.resource_cache[cache_key] = buffer
            return buffer
        except vk.VkError as e:
            logger.error(f"Failed to create buffer: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during buffer creation: {e}")
            raise

    def create_sync_objects(self, num_images):
        image_available_semaphores = []
        render_finished_semaphores = []
        in_flight_fences = []

        semaphore_create_info = vk.VkSemaphoreCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO
        )
        fence_create_info = vk.VkFenceCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_FENCE_CREATE_INFO,
            flags=vk.VK_FENCE_CREATE_SIGNALED_BIT,
        )

        for _ in range(num_images):
            try:
                image_available_semaphore = vk.vkCreateSemaphore(self.device, semaphore_create_info, None)
                render_finished_semaphore = vk.vkCreateSemaphore(self.device, semaphore_create_info, None)
                in_flight_fence = vk.vkCreateFence(self.device, fence_create_info, None)

                self.add_resource(image_available_semaphore, "semaphore")
                self.add_resource(render_finished_semaphore, "semaphore")
                self.add_resource(in_flight_fence, "fence")

                image_available_semaphores.append(image_available_semaphore)
                render_finished_semaphores.append(render_finished_semaphore)
                in_flight_fences.append(in_flight_fence)

            except vk.VkError as e:
                raise Exception(f"Failed to create synchronization objects: {e}")

        return image_available_semaphores, render_finished_semaphores, in_flight_fences

    def create_image(self, width, height, format, usage, memory_properties):
        cache_key = (width, height, format, usage, memory_properties)
        if cache_key in self.resource_cache:
            return self.resource_cache[cache_key]

        try:
            image = VulkanImage(self.device, width, height, format, usage, memory_properties, self.memory_allocator)
            self.add_resource(image, "image")
            self.resource_cache[cache_key] = image
            return image
        except vk.VkError as e:
            logger.error(f"Failed to create image: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during image creation: {e}")
            raise

    def create_vertex_buffer(self, vertices):
        buffer_size = Vertex.sizeof() * len(vertices)

        staging_buffer = self.create_buffer(
            buffer_size, 
            vk.VK_BUFFER_USAGE_TRANSFER_SRC_BIT, 
            vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT
        )

        staging_buffer.map_memory()
        staging_buffer.copy_to_memory(Vertex.as_bytes(vertices))
        staging_buffer.unmap_memory()

        vertex_buffer = self.create_buffer(
            buffer_size, 
            vk.VK_BUFFER_USAGE_TRANSFER_DST_BIT | vk.VK_BUFFER_USAGE_VERTEX_BUFFER_BIT, 
            vk.VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT
        )

        self.copy_buffer(staging_buffer, vertex_buffer, buffer_size)

        # Staging buffer will be automatically cleaned up when no longer needed
        return vertex_buffer

    def create_mesh(self, mesh_renderer):
        mesh_renderer.generate_mesh()
        vertices = mesh_renderer.get_vertex_data()
        indices = mesh_renderer.get_index_data()

        vertex_buffer = self.create_vertex_buffer(vertices)
        index_buffer, index_buffer_memory, index_count = self.create_index_buffer(indices) # Create index buffer

        return vertex_buffer, index_buffer, index_count # Return index buffer and count

    def copy_buffer(self, src_buffer, dst_buffer, size):
        with self.begin_single_time_commands() as command_buffer:
            copy_region = vk.VkBufferCopy(srcOffset=0, dstOffset=0, size=size)
            vk.vkCmdCopyBuffer(command_buffer, src_buffer.buffer, dst_buffer.buffer, 1, [copy_region])

    def begin_single_time_commands(self):
        command_pool = VulkanCommandPool(self.device, self.renderer.graphics_queue_family_index)
        self.add_resource(command_pool, "command_pool")
        return command_pool.begin_single_time_commands()

    def end_single_time_commands(self, command_buffer):
        submit_info = vk.VkSubmitInfo(
            sType=vk.VK_STRUCTURE_TYPE_SUBMIT_INFO,
            commandBufferCount=1,
            pCommandBuffers=[command_buffer],
        )

        vk.vkQueueSubmit(self.renderer.graphics_queue, 1, [submit_info], vk.VK_NULL_HANDLE)
        vk.vkQueueWaitIdle(self.renderer.graphics_queue)


    def create_index_buffer(self, indices):
        buffer_size = indices.nbytes

        staging_buffer = self.create_buffer(
            buffer_size,
            vk.VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
            vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
        )
        staging_buffer.map_memory()
        staging_buffer.copy_to_memory(indices)
        staging_buffer.unmap_memory()

        index_buffer = self.create_buffer(
            buffer_size,
            vk.VK_BUFFER_USAGE_TRANSFER_DST_BIT | vk.VK_BUFFER_USAGE_INDEX_BUFFER_BIT,
            vk.VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,
        )

        self.copy_buffer(staging_buffer.buffer, index_buffer.buffer, buffer_size)
        return index_buffer, staging_buffer.memory, len(indices)

    def create_descriptor_pool(self, swapchain_image_count, descriptor_set_layout):
        pool_sizes = [
            vk.VkDescriptorPoolSize(
                type=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
                descriptorCount=swapchain_image_count * 2,  # 2 for camera and light
            )
        ]

        pool_create_info = vk.VkDescriptorPoolCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
            maxSets=swapchain_image_count,
            poolSizeCount=len(pool_sizes),
            pPoolSizes=pool_sizes,
        )

        try:
            descriptor_pool = vk.vkCreateDescriptorPool(self.device, pool_create_info, None)
            self.add_resource(descriptor_pool, "descriptor_pool")
            return descriptor_pool
        except vk.VkError as e:
            logger.error(f"Failed to create descriptor pool: {e}")
            raise

    def create_descriptor_sets(self, descriptor_pool, descriptor_set_layout, uniform_buffers, light_uniform_buffers):
        layouts = [descriptor_set_layout.layout] * len(uniform_buffers)
        alloc_info = vk.VkDescriptorSetAllocateInfo(
            sType=vk.VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
            descriptorPool=descriptor_pool,
            descriptorSetCount=len(uniform_buffers),
            pSetLayouts=layouts,
        )
        try:
            descriptor_sets = vk.vkAllocateDescriptorSets(self.device, alloc_info)

            for i, (uniform_buffer, light_uniform_buffer) in enumerate(zip(uniform_buffers, light_uniform_buffers)):
                camera_buffer_info = vk.VkDescriptorBufferInfo(
                    buffer=uniform_buffer.buffer,
                    offset=0,
                    range=uniform_buffer.size,
                )
                light_buffer_info = vk.VkDescriptorBufferInfo(
                    buffer=light_uniform_buffer.buffer,
                    offset=0,
                    range=light_uniform_buffer.size,
                )

                write_descriptor_sets = [
                    vk.VkWriteDescriptorSet(
                        sType=vk.VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
                        dstSet=descriptor_sets[i],
                        dstBinding=0,
                        dstArrayElement=0,
                        descriptorCount=1,
                        descriptorType=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
                        pBufferInfo=[camera_buffer_info],
                    ),
                    vk.VkWriteDescriptorSet(
                        sType=vk.VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
                        dstSet=descriptor_sets[i],
                        dstBinding=1,
                        dstArrayElement=0,
                        descriptorCount=1,
                        descriptorType=vk.VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
                        pBufferInfo=[light_buffer_info],
                    ),
                ]

                vk.vkUpdateDescriptorSets(self.device, len(write_descriptor_sets), write_descriptor_sets, 0, None)

            return descriptor_sets
        except vk.VkError as e:
            logger.error(f"Failed to create descriptor sets: {e}")
            raise

    def create_uniform_buffers(self, num_buffers):
        camera_uniform_buffers = []
        light_uniform_buffers = []
        material_uniform_buffers = []
        try:
            for _ in range(num_buffers):
                camera_buffer = self.create_buffer(
                    ctypes.sizeof(UniformBufferObject),
                    vk.VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT,
                    vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT
                )
                camera_uniform_buffers.append(camera_buffer)

                light_buffer = self.create_buffer(
                    ctypes.sizeof(LightUBO),
                    vk.VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT,
                    vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT
                )
                light_uniform_buffers.append(light_buffer)

                material_buffer = self.create_buffer(
                    4 * 4 + 4 * 3,  # vec3 albedo + float metallic + float roughness + float ao
                    vk.VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT,
                    vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT
                )
                material_uniform_buffers.append(material_buffer)

            return camera_uniform_buffers, light_uniform_buffers, material_uniform_buffers
        except Exception as e:
            logger.error(f"Failed to create uniform buffers: {e}")
            raise

    def update_uniform_buffers(self, current_image, camera_component, light, world, camera_uniform_buffers, light_uniform_buffers, material_uniform_buffers):
        try:
            camera_ubo = UniformBufferObject()
            camera_ubo.model = glm.mat4()
            camera_ubo.view = camera_component.get_view_matrix()
            camera_ubo.proj = camera_component.get_projection_matrix()

            camera_data = self.map_memory(camera_uniform_buffers[current_image].memory)
            ctypes.memmove(camera_data, ctypes.addressof(camera_ubo), ctypes.sizeof(camera_ubo))
            self.unmap_memory(camera_uniform_buffers[current_image].memory)

            light_ubo = LightUBO()
            light_ubo.lightPos = light.position
            light_ubo.viewPos = camera_component.position
            light_ubo.lightColor = light.color

            light_data = self.map_memory(light_uniform_buffers[current_image].memory)
            ctypes.memmove(light_data, ctypes.addressof(light_ubo), ctypes.sizeof(light_ubo))
            self.unmap_memory(light_uniform_buffers[current_image].memory)

            for entity, (mesh, material) in world.get_components(Mesh, Material):
                material_data = self.map_memory(material_uniform_buffers[current_image].memory)
                material_buffer = material.to_uniform_buffer()
                ctypes.memmove(material_data, material_buffer.ctypes.data, material_buffer.nbytes)
                self.unmap_memory(material_uniform_buffers[current_image].memory)
        except Exception as e:
            logger.error(f"Failed to update uniform buffers: {e}")
            raise
