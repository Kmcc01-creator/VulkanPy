# Vulkan Graphics Application in Python

This project aims to create a basic graphics application using the Vulkan API via Python bindings. It utilizes GLFW for window management and an Entity Component System (ECS) for scene management.

## Project Structure

* **vulkan_app/main.py:** The main entry point of the application. Initializes GLFW, the window, renderer, and input handler, and runs the main loop.
* **vulkan_app/src/window_manager.py:** Handles window creation and management using GLFW.
* **vulkan_app/src/input_handler.py:** Processes user input (keyboard, mouse, etc.).  Currently placeholder, needs implementation.
* **vulkan_app/src/vulkan_renderer.py:** Contains the core Vulkan rendering logic, utilizing the ECS.
* **vulkan_app/src/vulkan_engine/__init__.py:** Initializes the Vulkan engine and its sub-modules.
* **vulkan_app/src/vulkan_engine/instance.py:** Creates and manages the Vulkan instance.
* **vulkan_app/src/vulkan_engine/device.py:** Handles Vulkan device selection and setup.
* **vulkan_app/src/vulkan_engine/swapchain.py:** Manages the swapchain for presenting rendered images to the window.  Handles swapchain recreation.
* **vulkan_app/src/vulkan_engine/pipeline.py:** Sets up the graphics pipeline, including shaders, render passes, and descriptor set layouts.
* **vulkan_app/src/vulkan_engine/buffer.py:** Handles vertex and uniform buffer creation and management.
* **vulkan_app/src/vulkan_engine/descriptors.py:** Manages descriptor sets and descriptor pools.
* **vulkan_app/src/vulkan_engine/synchronization.py:** Creates and manages Vulkan synchronization objects (semaphores, fences).
* **vulkan_app/src/vulkan_engine/command_buffer.py:**  Handles command pool and command buffer creation and recording.
* **vulkan_app/src/ecs/world.py:** Implements the ECS world.
* **vulkan_app/src/ecs/components.py:** Defines ECS components (Transform, Mesh, Material).
* **vulkan_app/src/ecs/systems.py:** Defines ECS systems (RenderSystem).
* **vulkan_app/src/vertex.py:** Defines the vertex data structure.
* **vulkan_app/shaders/shader.vert:** The vertex shader code (GLSL).
* **vulkan_app/shaders/shader.frag:** The fragment shader code (GLSL).

## Goals and Future Improvements

### Engine Improvements

* **Robust Resource Management:** Implement a more robust resource management system using RAII principles or a dedicated resource manager to prevent memory leaks and ensure efficient resource usage.
* **Enhanced Swapchain Recreation:** Improve swapchain recreation to handle edge cases like window minimization and device loss more effectively.
* **Input Handling:** Implement a comprehensive input handling system for camera control, object manipulation, and UI interaction.
* **Shader Management:** Develop a more flexible shader management system, including hot reloading and compilation error handling.

### Functionality Goals

* **Model Loading:** Implement support for loading 3D models from external files (e.g., .obj, .gltf).
* **Texturing:** Add texture loading and mapping capabilities.
* **Lighting:** Implement basic lighting models (e.g., Phong, Blinn-Phong) with support for different light types (directional, point, spot).
* **Material System:** Develop a material system to define the appearance of objects, including properties like color, reflectivity, and textures.
* **GUI:** Integrate a GUI library (e.g., Dear ImGui) for user interface elements.
