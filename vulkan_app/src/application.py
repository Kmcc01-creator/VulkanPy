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
        self.window_manager = None
        self.window = None
        self.renderer = None
        self.input_handler = None
        self.initialize()

    def initialize(self):
        try:
            self.window_manager = WindowManager(self.config.window_width, self.config.window_height, self.config.window_title)
            self.window = self.window_manager.create_window()
            self.renderer = VulkanRenderer(self.window, self.config.vulkan_version)
            self.input_handler = InputHandler(self.window)
            self.logger.info("Application initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize application: {e}")
            raise

    def run(self):
        self.logger.info("Starting application main loop")
        try:
            while not self.window_manager.should_close():
                self.input_handler.process_input(self.renderer.camera_component)
                self.renderer.render()
                self.window_manager.poll_events()
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        self.logger.info("Cleaning up application resources")
        if self.renderer:
            self.renderer.cleanup()
        if self.window_manager:
            self.window_manager.terminate()
