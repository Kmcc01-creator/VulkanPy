import glfw
import logging
from src.vulkan_renderer import VulkanRenderer
from src.window_manager import WindowManager
from src.input_handler import InputHandler
from src.config import Config

class Application:
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.window_manager = WindowManager(config.window_width, config.window_height, config.window_title)
        self.window = self.window_manager.create_window()
        self.renderer = VulkanRenderer(self.window, config.vulkan_version)
        self.input_handler = InputHandler(self.window)

    def run(self):
        self.logger.info("Starting application main loop")
        while not self.window_manager.should_close():
            self.input_handler.process_input(self.renderer.camera_component)
            self.renderer.render()
            self.window_manager.poll_events()

        self.cleanup()

    def cleanup(self):
        self.logger.info("Cleaning up application resources")
        self.renderer.cleanup()
        self.window_manager.terminate()
