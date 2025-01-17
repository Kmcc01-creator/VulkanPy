import numpy as np
from src.vertex import Vertex

def load_obj(filepath):
    vertices = []
    indices = []

    # Placeholder for actual .obj loading logic
    # Replace with your .obj loading code here

    # Example data (replace with loaded data)
    vertices = [
        Vertex(np.array([-0.5, -0.5, 0.0]), np.array([1.0, 0.0, 0.0])),
        Vertex(np.array([0.5, -0.5, 0.0]), np.array([0.0, 1.0, 0.0])),
        Vertex(np.array([0.0, 0.5, 0.0]), np.array([0.0, 0.0, 1.0])),
    ]
    indices = []

    return np.array(vertices, dtype=Vertex), np.array(indices, dtype=np.uint32)
