# src/vulkan_engine/command_system/command_types.py
from enum import Enum, auto
import vulkan as vk
from dataclasses import dataclass
from typing import Dict, Optional

class CommandType(Enum):
    GRAPHICS = auto()
    COMPUTE = auto()
    TRANSFER = auto()

    def to_queue_flag_bits(self) -> int:
        return {
            CommandType.GRAPHICS: vk.VK_QUEUE_GRAPHICS_BIT,
            CommandType.COMPUTE: vk.VK_QUEUE_COMPUTE_BIT,
            CommandType.TRANSFER: vk.VK_QUEUE_TRANSFER_BIT,
        }[self]

class CommandLevel(Enum):
    PRIMARY = auto()
    SECONDARY = auto()

    def to_vk_level(self) -> int:
        return {
            CommandLevel.PRIMARY: vk.VK_COMMAND_BUFFER_LEVEL_PRIMARY,
            CommandLevel.SECONDARY: vk.VK_COMMAND_BUFFER_LEVEL_SECONDARY,
        }[self]

@dataclass
class CommandPoolCreateInfo:
    queue_family_index: int
    command_type: CommandType
    transient: bool = False
    resetable: bool = True

    def to_vk_flags(self) -> int:
        flags = 0
        if self.transient:
            flags |= vk.VK_COMMAND_POOL_CREATE_TRANSIENT_BIT
        if self.resetable:
            flags |= vk.VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT
        return flags
