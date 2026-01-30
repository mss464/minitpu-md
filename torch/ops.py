"""
Core TPU Atomic Operations Library.
This module acts as a facade, exporting low-level TPU instructions and memory allocator.
"""

from compiler.tpu_txt import load, store, matmul, add, sub, mul, relu, relu_derivative, get_instruction_log
from compiler.runtime.allocator import allocator as mem

__all__ = [
    "load",
    "store",
    "matmul",
    "add",
    "sub",
    "mul",
    "relu",
    "relu_derivative",
    "get_instruction_log",
    "mem"
]