"""
TPU Program abstraction for composing kernels into deployable binaries.

A Program combines:
- Memory allocation (via MemoryAllocator)
- Kernel scheduling (sequence of compiled kernels with bindings)
- Binary generation (instructions as .npy or .hex)

Example:
    from compiler.program import Program
    from compiler.kernels import matmul_4x4

    prog = Program()
    W = prog.alloc("W", 16)
    X = prog.alloc("X", 16)
    Z = prog.alloc("Z", 16)
    prog.call(matmul_4x4, W=W, X=X, Z=Z)
    prog.save("program.npy")
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Union
from pathlib import Path
import numpy as np

from compiler.kernel import CompiledKernel, KernelFunction
from compiler.runtime.allocator import MemoryAllocator
from compiler.assembler import encode_halt


@dataclass
class KernelCall:
    """A scheduled kernel call with resolved bindings."""
    kernel: CompiledKernel
    bindings: Dict[str, int]


class Program:
    """
    Composes kernels into a deployable TPU program.

    Manages memory allocation and kernel scheduling.
    """

    def __init__(self, allocator: MemoryAllocator = None):
        self.allocator = allocator or MemoryAllocator()
        self.calls: List[KernelCall] = []
        self._compiled_cache: Dict[str, CompiledKernel] = {}

    def alloc(self, name: str, words: int) -> int:
        """Allocate memory and return address."""
        return self.allocator.alloc(name, words)

    def addr(self, name: str) -> int:
        """Get address of previously allocated memory."""
        return self.allocator.get(name)

    def free(self, name: str):
        """Free previously allocated memory."""
        self.allocator.free(name)

    def call(self, kernel: Union[KernelFunction, CompiledKernel], **bindings: int):
        """
        Schedule a kernel call with address bindings.

        Args:
            kernel: KernelFunction (will be compiled) or CompiledKernel
            **bindings: Parameter name -> address mappings
        """
        if isinstance(kernel, KernelFunction):
            # Cache compiled kernels by function name
            name = kernel._fn.__name__
            if name not in self._compiled_cache:
                self._compiled_cache[name] = kernel.compile()
            compiled = self._compiled_cache[name]
        else:
            compiled = kernel

        self.calls.append(KernelCall(kernel=compiled, bindings=bindings))

    def compile(self) -> np.ndarray:
        """
        Compile all scheduled kernels to instruction array.

        Returns:
            np.ndarray of uint64 instructions (with HALT appended)
        """
        all_instructions = []

        for call in self.calls:
            resolved = call.kernel.resolve(call.bindings)
            all_instructions.append(resolved)

        if all_instructions:
            combined = np.concatenate(all_instructions)
        else:
            combined = np.array([], dtype=np.uint64)

        # Append HALT
        halt = np.array([encode_halt()], dtype=np.uint64)
        return np.concatenate([combined, halt])

    def save(self, path: Union[str, Path], format: str = None):
        """
        Save compiled program to file.

        Args:
            path: Output file path
            format: 'npy', 'hex', or None (auto-detect from extension)
        """
        path = Path(path)
        instructions = self.compile()

        if format is None:
            format = path.suffix.lstrip('.')

        if format == 'npy':
            np.save(path, instructions)
        elif format in ('hex', 'txt'):
            with open(path, 'w') as f:
                for instr in instructions:
                    f.write(f"{instr:016X}\n")
        else:
            raise ValueError(f"Unknown format: {format}")

        return len(instructions)

    def get_memory_map(self) -> Dict[str, tuple]:
        """Get current memory allocations as {name: (addr, size)}."""
        return dict(self.allocator.memory_map)

    def reset(self):
        """Reset program state (clear allocations and calls)."""
        self.allocator.reset()
        self.calls.clear()
        self._compiled_cache.clear()


def load_program(path: Union[str, Path]) -> np.ndarray:
    """
    Load compiled program from file.

    Args:
        path: Path to .npy or .hex file

    Returns:
        np.ndarray of uint64 instructions
    """
    path = Path(path)

    if path.suffix == '.npy':
        return np.load(path)
    else:
        instructions = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    instructions.append(int(line, 16))
        return np.array(instructions, dtype=np.uint64)
