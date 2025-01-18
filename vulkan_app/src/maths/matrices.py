import numpy as np
from src.maths.vectors import Vector3

class Matrix4:
    def __init__(self, matrix: np.ndarray = None):
        if matrix is not None and matrix.shape == (4, 4):
            self.m = matrix.copy()
        else:
            self.m = np.identity(4, dtype=np.float32)

    def __mul__(self, other):
        if isinstance(other, Matrix4):
            return Matrix4(np.dot(self.m, other.m))
        elif isinstance(other, Vector3):
            v = np.array([other.x, other.y, other.z, 1.0])
            result = np.dot(self.m, v)
            return Vector3(result[0], result[1], result[2])
        return NotImplemented

    @staticmethod
    def perspective(fov_radians: float, aspect_ratio: float, near_clip: float, far_clip: float):
        tan_half_fov = np.tan(fov_radians / 2.0)
        m = np.zeros((4, 4), dtype=np.float32)
        m[0, 0] = 1.0 / (aspect_ratio * tan_half_fov)
        m[1, 1] = 1.0 / tan_half_fov
        m[2, 2] = -(far_clip + near_clip) / (far_clip - near_clip)
        m[2, 3] = -1.0
        m[3, 2] = -(2.0 * far_clip * near_clip) / (far_clip - near_clip)
        return Matrix4(m)

    @staticmethod
    def look_at(eye: Vector3, target: Vector3, up: Vector3):
        forward = (target - eye).normalize()
        right = up.cross(forward).normalize()
        new_up = forward.cross(right)

        m = np.identity(4, dtype=np.float32)
        m[0, :3] = right.x, right.y, right.z
        m[1, :3] = new_up.x, new_up.y, new_up.z
        m[2, :3] = -forward.x, -forward.y, -forward.z
        m[3, :3] = -eye.dot(right), -eye.dot(new_up), eye.dot(forward)
        return Matrix4(m)

    @staticmethod
    def translate(vector: Vector3):
        m = np.identity(4, dtype=np.float32)
        m[0, 3] = vector.x
        m[1, 3] = vector.y
        m[2, 3] = vector.z
        return Matrix4(m)

    @staticmethod
    def scale(vector: Vector3):
        m = np.identity(4, dtype=np.float32)
        m[0, 0] = vector.x
        m[1, 1] = vector.y
        m[2, 2] = vector.z
        return Matrix4(m)

    # Add methods for rotation matrices (around X, Y, Z axes)
