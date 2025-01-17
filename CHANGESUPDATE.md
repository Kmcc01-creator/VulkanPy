# Refactoring: Vulkan Renderer

The `VulkanRenderer` class is currently overburdened with responsibilities.  This refactoring aims to decompose it into smaller, more manageable classes, improving code organization and maintainability.

## Proposed Changes

1. **Introduce a `VulkanEngine` class:** This class will encapsulate the core Vulkan setup and management, including instance creation, device selection, and resource management.  It will also handle swapchain creation and recreation.

2. **Create a `RenderManager` class:** This class will manage the rendering process, including command buffer recording, synchronization, and pipeline management.  It will interact with the `VulkanEngine` to acquire swapchain images and submit command buffers.

3. **Refactor `VulkanRenderer`:** The `VulkanRenderer` class will primarily serve as an interface between the application and the rendering engine.  It will delegate Vulkan setup and rendering tasks to the `VulkanEngine` and `RenderManager` classes.

## Benefits

* **Improved Code Organization:**  Clear separation of concerns will make the code easier to understand and maintain.
* **Increased Reusability:**  The `VulkanEngine` and `RenderManager` classes can be reused in other Vulkan projects.
* **Simplified Testing:**  Smaller, more focused classes are easier to test thoroughly.

## Implementation Details

The `VulkanEngine` class will be responsible for:

* Creating and managing the Vulkan instance.
* Selecting a suitable physical device and creating a logical device.
* Creating and managing the swapchain.
* Managing Vulkan resources (buffers, images, etc.).

The `RenderManager` class will be responsible for:

* Creating and managing command pools and command buffers.
* Recording command buffers for rendering.
* Managing synchronization primitives (semaphores, fences).
* Managing the graphics pipeline.

The `VulkanRenderer` class will:

* Initialize the `VulkanEngine` and `RenderManager`.
* Handle window resizing and swapchain recreation.
* Delegate rendering tasks to the `RenderManager`.
