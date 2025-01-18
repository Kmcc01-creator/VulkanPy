import numpy as np

class Quaternion:
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0, w: float = 1.0):
        self.x = x
        self.y = y
        self.z = z
        self.w = w

    def __mul__(self, other):
        x1, y1, z1, w1 = self.x, self.y, self.z, self.w
        x2, y2, z2, w2 = other.x, other.y, other.z, other.w
        return Quaternion(
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        )

    def magnitude(self):
        return np.sqrt(self.x**2 + self.y**2 + self.z**2 + self.w**2)

    def normalize(self):
        mag = self.magnitude()
        if mag > 0:
            self.x /= mag
            self.y /= mag
            self.z /= mag
            self.w /= mag
        return self

    def conjugate(self):
        return Quaternion(-self.x, -self.y, -self.z, self.w)

    def to_rotation_matrix(self):
        q = self.normalize()
        x, y, z, w = q.x, q.y, q.z, q.w
        m = np.zeros((4, 4), dtype=np.float32)
        m[0, 0] = 1 - 2 * (y**2 + z**2)
        m[0, 1] = 2 * (x * y - w * z)
        m[0, 2] = 2 * (x * z + w * y)
        m[1, 0] = 2 * (x * y + w * z)
        m[1, 1] = 1 - 2 * (x**2 + z**2)
        m[1, 2] = 2 * (y * z - w * x)
        m[2, 0] = 2 * (x * z - w * y)
        m[2, 1] = 2 * (y * z + w * x)
        m[2, 2] = 1 - 2 * (x**2 + y**2)
        m[3, 3] = 1
        return Matrix4(m)

    @staticmethod
    def from_axis_angle(axis: Vector3, angle_radians: float):
        axis_normalized = axis.normalize()
        half_angle = angle_radians / 2.0
        sin_half_angle = np.sin(half_angle)
        cos_half_angle = np.cos(half_angle)
        return Quaternion(
            axis_normalized.x * sin_half_angle,
            axis_normalized.y * sin_half_angle,
            axis_normalized.z * sin_half_angle,
            cos_half_angle,
        )

