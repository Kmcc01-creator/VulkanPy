# System Overview

This document provides a high-level overview of the Vulkan rendering system.

## Architecture

The system follows an Entity-Component-System (ECS) architecture.  The core components are:

* **Entities:**  Unique identifiers representing objects in the scene.  They don't hold data themselves but are associated with components.
* **Components:** Data containers holding properties of entities (e.g., Transform, Mesh, Material).
* **Systems:** Logic modules operating on entities possessing specific components (e.g., RenderSystem, CameraSystem).

The `World` class manages entities, components, and systems.  It provides methods for creating entities, adding/retrieving components, and updating systems.

## Rendering Pipeline

The rendering process is managed by the `VulkanRenderer` and `RenderManager`.  The key steps are:

1. **Initialization:**  Creating Vulkan instance, device, swapchain, and other necessary resources.
2. **Resource Loading:** Loading shaders and mesh data.
3. **World Update:** Updating camera and other systems.
4. **Rendering:**
    * Acquiring a swapchain image.
    * Recording command buffers: Binding pipelines, setting viewports, drawing objects.
    * Submitting command buffers for execution.
    * Presenting the rendered image.
5. **Cleanup:** Releasing Vulkan resources.

## Input Handling

Input is processed by the `InputHandler` class, which updates the camera's position and orientation based on user input.

## Configuration

The `Config` class stores application settings, such as window dimensions and Vulkan API version.

