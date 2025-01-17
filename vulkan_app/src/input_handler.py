class InputHandler:
    def __init__(self, window):
        self.window = window
        # ... Input setup ...

    def process_input(self):
        from pyglm import vec3

        camera_speed = 0.01 # Adjust camera speed as needed
        if glfw.get_key(self.window, glfw.KEY_W) == glfw.PRESS:
            camera.position += vec3(0.0, 0.0, camera_speed)
        if glfw.get_key(self.window, glfw.KEY_S) == glfw.PRESS:
            camera.position -= vec3(0.0, 0.0, camera_speed)
        if glfw.get_key(self.window, glfw.KEY_A) == glfw.PRESS:
            camera.position -= vec3(camera_speed, 0.0, 0.0)
        if glfw.get_key(self.window, glfw.KEY_D) == glfw.PRESS:
            camera.position += vec3(camera_speed, 0.0, 0.0)
