import yaml
from dataclasses import dataclass

@dataclass
class Config:
    window_width: int
    window_height: int
    window_title: str
    vulkan_version: tuple

    @classmethod
    def load_from_file(cls, filename):
        with open(filename, 'r') as file:
            data = yaml.safe_load(file)
        return cls(**data)
