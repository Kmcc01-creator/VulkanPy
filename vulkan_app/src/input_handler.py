import glfw
import logging
from pyglm import vec3
from typing import Dict, Any

logger = logging.getLogger(__name__)

class InputHandler:
    def __init__(self, window: Any) -> None:
        self.window = window
        self.key_mappings: Dict[int, vec3] = {
            glfw.KEY_W: vec3(0.0, 0.0, 1.0),
            glfw.KEY_S: vec3(0.0, 0.0, -1.0),
            glfw.KEY_A: vec3(-1.0, 0.0, 0.0),
            glfw.KEY_D: vec3(1.0, 0.0, 0.0)
        }
        logger.info("InputHandler initialized")

    def process_input(self, camera: Any) -> None:
        camera_speed = 0.01
        pressed_keys = [key for key, direction in self.key_mappings.items() if glfw.get_key(self.window, key) == glfw.PRESS]
        for key in pressed_keys:
            direction = self.key_mappings[key]
            camera.position += direction * camera_speed
            logger.debug(f"Camera moved: {direction * camera_speed}")
