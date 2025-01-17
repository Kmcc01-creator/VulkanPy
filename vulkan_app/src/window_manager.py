import glfw
import logging

class WindowManager:
    def __init__(self, width: int, height: int, title: str):
        self.width = width
        self.height = height
        self.title = title
        self.window = None
        self.logger = logging.getLogger(__name__)

    def create_window(self):
        if not glfw.init():
            self.logger.error("Failed to initialize GLFW")
            raise RuntimeError("Failed to initialize GLFW")

        glfw.window_hint(glfw.CLIENT_API, glfw.NO_API)
        self.window = glfw.create_window(self.width, self.height, self.title, None, None)

        if not self.window:
            glfw.terminate()
            self.logger.error("Failed to create GLFW window")
            raise RuntimeError("Failed to create GLFW window")

        return self.window

    def should_close(self):
        return glfw.window_should_close(self.window)

    def poll_events(self):
        glfw.poll_events()

    def terminate(self):
        glfw.terminate()
