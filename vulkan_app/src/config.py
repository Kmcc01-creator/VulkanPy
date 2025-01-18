import yaml
import os
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
        
        # Override with environment variables if set
        data['window_width'] = int(os.environ.get('VULKAN_APP_WIDTH', data['window_width']))
        data['window_height'] = int(os.environ.get('VULKAN_APP_HEIGHT', data['window_height']))
        data['window_title'] = os.environ.get('VULKAN_APP_TITLE', data['window_title'])
        
        vulkan_version = os.environ.get('VULKAN_APP_VERSION')
        if vulkan_version:
            data['vulkan_version'] = tuple(map(int, vulkan_version.split('.')))

        return cls(**data)
