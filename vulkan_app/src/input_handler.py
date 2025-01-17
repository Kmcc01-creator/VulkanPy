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
            glfw.KEY_D: vec3(1.0, 0.0, 0.0),
            glfw.KEY_Q: vec3(0.0, 1.0, 0.0),
            glfw.KEY_E: vec3(0.0, -1.0, 0.0)
        }
        self.mouse_sensitivity = 0.1
        self.last_mouse_pos = None
        logger.info("InputHandler initialized")

    def process_input(self, camera: Any) -> None:
        self.process_keyboard_input(camera)
        self.process_mouse_input(camera)

    def process_keyboard_input(self, camera: Any) -> None:
        camera_speed = 0.01
        movement = vec3(0.0, 0.0, 0.0)
        pressed_keys = [key for key in self.key_mappings if glfw.get_key(self.window, key) == glfw.PRESS]
        for key in pressed_keys:
            movement += self.key_mappings[key]
        if movement.length() > 0:
            movement = movement.normalize() * camera_speed
            camera.position += movement
            logger.debug(f"Camera moved: {movement}")

    def process_mouse_input(self, camera: Any) -> None:
        x_pos, y_pos = glfw.get_cursor_pos(self.window)
        if self.last_mouse_pos is None:
            self.last_mouse_pos = (x_pos, y_pos)
            return

        x_offset = x_pos - self.last_mouse_pos[0]
        y_offset = self.last_mouse_pos[1] - y_pos
        self.last_mouse_pos = (x_pos, y_pos)

        x_offset *= self.mouse_sensitivity
        y_offset *= self.mouse_sensitivity

        camera.yaw += x_offset
        camera.pitch += y_offset

        camera.pitch = max(min(camera.pitch, 89.0), -89.0)

        camera.update_camera_vectors()
        logger.debug(f"Camera rotated: yaw={camera.yaw}, pitch={camera.pitch}")
