import glfw # Import glfw
from src.vulkan_renderer import VulkanRenderer
from src.window_manager import WindowManager
from src.input_handler import InputHandler

def main():
    window_manager = WindowManager(800, 600, "Vulkan App")
    window = window_manager.create_window()
    renderer = VulkanRenderer(window)
    input_handler = InputHandler(window)

    while not glfw.window_should_close(window):  # Example using GLFW
        input_handler.process_input()
        renderer.render()

        glfw.swap_buffers(window) # Example using GLFW
        glfw.poll_events()       # Example using GLFW

    glfw.terminate()             # Example using GLFW

if __name__ == "__main__":
    main()
