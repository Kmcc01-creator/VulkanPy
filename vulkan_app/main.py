import glfw # Import glfw
from src.vulkan_renderer import VulkanRenderer
from src.window_manager import WindowManager
from src.input_handler import InputHandler

def main():
    window_manager = WindowManager(800, 600, "Vulkan App")
    if not glfw.init():
        raise RuntimeError("Failed to initialize GLFW")

    glfw.window_hint(glfw.CLIENT_API, glfw.NO_API)
    window = glfw.create_window(800, 600, "Vulkan App", None, None)

    if not window:
        glfw.terminate()
        raise RuntimeError("Failed to create GLFW window")

    renderer = VulkanRenderer(window)
    input_handler = InputHandler(window)

    while not glfw.window_should_close(window):
        input_handler.process_input()
        renderer.render()

        glfw.poll_events()       # Example using GLFW

    renderer.cleanup()
    glfw.terminate()             # Example using GLFW

if __name__ == "__main__":
    main()
