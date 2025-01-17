from dataclasses import dataclass
import numpy as np

@dataclass
class Transform:
    position: np.ndarray
    rotation: np.ndarray
    scale: np.ndarray

@dataclass
class Mesh:
    vertices: np.ndarray
    indices: np.ndarray

@dataclass
class Material:
    color: np.ndarray # For now, just a simple color
