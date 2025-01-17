# Vulkan Graphics Application in Python

This project aims to create a basic graphics application using the Vulkan API via Python bindings. It utilizes GLFW for window management and provides a modular structure for the Vulkan rendering engine.

## Project Structure

* **vulkan_app/main.py:** The main entry point of the application. Initializes the window, renderer, and input handler, and runs the main loop.
* **vulkan_app/src/window_manager.py:** Handles window creation and management using GLFW.
* **vulkan_app/src/input_handler.py:**  Processes user input (keyboard, mouse, etc.).
* **vulkan_app/src/vulkan_renderer.py:** Contains the core Vulkan rendering logic. This module will be further modularized to separate different rendering components.
* **vulkan_app/src/vulkan_engine/__init__.py:**  Initializes the Vulkan engine and its sub-modules.
* **vulkan_app/src/vulkan_engine/instance.py:** Creates and manages the Vulkan instance.
* **vulkan_app/src/vulkan_engine/device.py:**  Handles Vulkan device selection and setup.
* **vulkan_app/src/vulkan_engine/swapchain.py:**  Manages the swapchain for presenting rendered images to the window.
* **vulkan_app/src/vulkan_engine/pipeline.py:** Sets up the graphics pipeline, including shaders and render passes.
* **vulkan_app/src/vulkan_engine/buffer.py:**  Handles vertex and index buffer creation and management.
* **vulkan_app/shaders/shader.vert:** The vertex shader code (GLSL).
* **vulkan_app/shaders/shader.frag:** The fragment shader code (GLSL).


## Refactoring Notes

The `vulkan_renderer.py` file will be split into multiple modules within a `vulkan_engine` directory to improve code organization and maintainability.  Each module will handle a specific aspect of Vulkan rendering (instance creation, device management, swapchain, pipeline, etc.).
