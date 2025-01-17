import numpy as np
from enum import Enum
from dataclasses import dataclass
from typing import List, Callable

class MeshType(Enum):
    SPHERE = 1
    CUBE = 2
    CYLINDER = 3
    CUSTOM = 4

@dataclass
class Vertex:
    position: np.ndarray
    normal: np.ndarray
    uv: np.ndarray

class MeshRenderer:
    def __init__(self, mesh_type: MeshType, resolution: int = 32):
        self.mesh_type = mesh_type
        self.resolution = resolution
        self.vertices: List[Vertex] = []
        self.indices: List[int] = []

    def generate_mesh(self):
        if self.mesh_type == MeshType.SPHERE:
            self._generate_sphere()
        elif self.mesh_type == MeshType.CUBE:
            self._generate_cube()
        elif self.mesh_type == MeshType.CYLINDER:
            self._generate_cylinder()
        else:
            raise ValueError("Unsupported mesh type")

    def _generate_sphere(self):
        for i in range(self.resolution + 1):
            theta = i * np.pi / self.resolution
            for j in range(self.resolution + 1):
                phi = j * 2 * np.pi / self.resolution
                x = np.sin(theta) * np.cos(phi)
                y = np.cos(theta)
                z = np.sin(theta) * np.sin(phi)
                position = np.array([x, y, z])
                normal = position / np.linalg.norm(position)
                uv = np.array([j / self.resolution, i / self.resolution])
                self.vertices.append(Vertex(position, normal, uv))

        for i in range(self.resolution):
            for j in range(self.resolution):
                first = i * (self.resolution + 1) + j
                second = first + self.resolution + 1
                self.indices.extend([first, second, first + 1])
                self.indices.extend([second, second + 1, first + 1])

    def _generate_cube(self):
        vertices = [
            (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
            (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)
        ]
        normals = [
            (0, 0, -1), (0, 0, 1), (0, -1, 0),
            (0, 1, 0), (-1, 0, 0), (1, 0, 0)
        ]
        faces = [
            (0, 1, 2, 3), (5, 4, 7, 6), (4, 0, 3, 7),
            (1, 5, 6, 2), (4, 5, 1, 0), (3, 2, 6, 7)
        ]

        for face, normal in zip(faces, normals):
            for vertex_idx in face:
                position = np.array(vertices[vertex_idx])
                uv = (position[:2] + 1) / 2
                self.vertices.append(Vertex(position, np.array(normal), uv))

            base = len(self.vertices) - 4
            self.indices.extend([base, base + 1, base + 2, base, base + 2, base + 3])

    def _generate_cylinder(self):
        for i in range(self.resolution + 1):
            theta = i * 2 * np.pi / self.resolution
            x = np.cos(theta)
            z = np.sin(theta)
            for y in [-1, 1]:
                position = np.array([x, y, z])
                normal = np.array([x, 0, z])
                uv = np.array([i / self.resolution, (y + 1) / 2])
                self.vertices.append(Vertex(position, normal, uv))

        for i in range(self.resolution):
            base = i * 2
            self.indices.extend([base, base + 1, base + 2])
            self.indices.extend([base + 1, base + 3, base + 2])

        # Add top and bottom caps
        for y in [-1, 1]:
            center = len(self.vertices)
            self.vertices.append(Vertex(np.array([0, y, 0]), np.array([0, y, 0]), np.array([0.5, 0.5])))
            for i in range(self.resolution):
                theta = i * 2 * np.pi / self.resolution
                x = np.cos(theta)
                z = np.sin(theta)
                position = np.array([x, y, z])
                normal = np.array([0, y, 0])
                uv = np.array([(x + 1) / 2, (z + 1) / 2])
                self.vertices.append(Vertex(position, normal, uv))
                if i > 0:
                    if y > 0:
                        self.indices.extend([center, center + i, center + i + 1])
                    else:
                        self.indices.extend([center, center + i + 1, center + i])

    @classmethod
    def from_function(cls, func: Callable[[float, float], float], u_range: tuple, v_range: tuple, resolution: int):
        mesh = cls(MeshType.CUSTOM, resolution)
        u_min, u_max = u_range
        v_min, v_max = v_range

        for i in range(resolution + 1):
            for j in range(resolution + 1):
                u = u_min + (u_max - u_min) * i / resolution
                v = v_min + (v_max - v_min) * j / resolution
                x, y = u, v
                z = func(u, v)
                position = np.array([x, y, z])

                # Compute normal using central differences
                eps = 1e-5
                dx = (func(u + eps, v) - func(u - eps, v)) / (2 * eps)
                dy = (func(u, v + eps) - func(u, v - eps)) / (2 * eps)
                normal = np.array([-dx, -dy, 1])
                normal /= np.linalg.norm(normal)

                uv = np.array([i / resolution, j / resolution])
                mesh.vertices.append(Vertex(position, normal, uv))

        for i in range(resolution):
            for j in range(resolution):
                first = i * (resolution + 1) + j
                second = first + resolution + 1
                mesh.indices.extend([first, second, first + 1])
                mesh.indices.extend([second, second + 1, first + 1])

        return mesh

    def get_vertex_data(self):
        return np.array([np.concatenate((v.position, v.normal, v.uv)) for v in self.vertices], dtype=np.float32)

    def get_index_data(self):
        return np.array(self.indices, dtype=np.uint32)
