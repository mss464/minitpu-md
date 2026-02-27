"""
TPU Module - Packaged compiled instructions for AOT execution.

[PLANNED] This module will provide:
- TPUModule class for serializing compiled instruction streams
- Memory layout metadata for input/output buffers
- Version compatibility checking
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np


@dataclass
class MemoryRegion:
    """A named region in TPU memory."""
    addr: int
    size: int
    name: str


@dataclass  
class MemoryLayout:
    """Static memory layout computed at compile time."""
    regions: Dict[str, MemoryRegion]
    input_addrs: Dict[str, int]
    output_addrs: Dict[str, Tuple[int, int]]  # (addr, length)


@dataclass
class TPUModule:
    """
    A compiled TPU program ready for execution.
    
    Contains:
    - Encoded instruction stream (bytes)
    - Memory layout for inputs/outputs
    - Optional debug metadata
    """
    instructions: bytes
    memory_layout: MemoryLayout
    metadata: Dict[str, any] = None
    
    def save(self, path: str) -> None:
        """Serialize module to disk."""
        raise NotImplementedError("TPUModule.save() not yet implemented")
    
    @classmethod
    def load(cls, path: str) -> "TPUModule":
        """Load module from disk."""
        raise NotImplementedError("TPUModule.load() not yet implemented")
