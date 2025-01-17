# Refactoring: Vulkan Renderer

The `VulkanRenderer` class is currently overburdened with responsibilities. This refactoring aims to decompose it into smaller, more manageable classes, improving code organization and maintainability.  Additionally, it addresses redundant code in resource management and swapchain recreation.

## Proposed Changes

1. **Introduce a `VulkanEngine` class:** This class will encapsulate the core Vulkan setup and management, including instance creation, device selection, and resource management.

2. **Create a `RenderManager` class:** This class will manage the rendering process, including command buffer recording, synchronization, and pipeline management. It will interact with the `VulkanEngine` to acquire swapchain images and submit command buffers.

3. **Refactor `VulkanRenderer`:** The `VulkanRenderer` class will serve as an interface between the application and the rendering engine, delegating tasks to the `VulkanEngine` and `RenderManager`.

4. **Consolidate Resource Management:** Move resource cleanup and management entirely into `ResourceManager` and `VulkanEngine`. Remove redundant cleanup logic from `VulkanRenderer` and `Swapchain`.

5. **Streamline Swapchain Recreation:**  Swapchain recreation logic will be handled entirely within the `Swapchain` class.  The `VulkanRenderer` will simply call the `recreate_swapchain` method of the `Swapchain` object.

6. **Remove Redundant Code:** Eliminate the duplicated `choose_surface_format` function by placing it solely within the `Swapchain` class.

## Benefits

* **Improved Code Organization:** Clear separation of concerns will make the code easier to understand and maintain.
* **Increased Reusability:** The `VulkanEngine` and `RenderManager` classes can be reused in other Vulkan projects.
* **Simplified Testing:** Smaller, more focused classes are easier to test thoroughly.
* **Reduced Code Duplication:** Eliminating redundant code improves maintainability and reduces the risk of inconsistencies.
* **More Efficient Resource Management:** Centralized resource management prevents memory leaks and improves resource usage.

## Implementation Details

The `VulkanEngine` class will be responsible for:

* Creating and managing the Vulkan instance.
* Selecting a suitable physical device and creating a logical device.
* Creating and managing the swapchain via the `Swapchain` object.
* Managing Vulkan resources (buffers, images, etc.) via the `ResourceManager` object.

The `RenderManager` class will be responsible for:

* Creating and managing command pools and command buffers.
* Recording command buffers for rendering.
* Managing synchronization primitives (semaphores, fences).
* Interacting with the `Swapchain` object for image acquisition and presentation.

The `VulkanRenderer` class will:

* Initialize the `VulkanEngine` and `RenderManager`.
* Handle window resizing by calling the `Swapchain` object's `recreate_swapchain` method.
* Delegate rendering tasks to the `RenderManager`.
