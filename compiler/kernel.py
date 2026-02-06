"""
Kernel Abstraction for Mini-TPU

CUDA-like kernel definition and launch syntax. Kernels are defined as decorated
Python functions, compiled to symbolic instructions, and launched with bound addresses.

Example:
    @kernel
    def matmul4x4(W: Param, X: Param, Z: Param):
        from compiler.tpu_txt import matmul
        matmul(W, X, Z)

    compiled = matmul4x4.compile()
    launcher.launch(compiled, W=0, X=16, Z=32)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional, Union
import numpy as np
import inspect
import functools

from compiler.assembler import (
    encode_vpu, encode_systolic, encode_halt,
    encode_vload, encode_vstore, encode_vcompute,
    OPCODES_VPU, OPCODES_VCOMPUTE, ADDR_MAX
)


class Param:
    """
    Symbolic address placeholder that supports arithmetic.

    During kernel compilation, Param objects track symbolic addresses
    that are resolved to concrete addresses at launch time.
    """

    def __init__(self, name: str, offset: int = 0):
        self.name = name
        self.offset = offset

    def __add__(self, other: int) -> Param:
        if not isinstance(other, int):
            raise TypeError(f"Param arithmetic requires int, got {type(other)}")
        return Param(self.name, self.offset + other)

    def __radd__(self, other: int) -> Param:
        return self.__add__(other)

    def __sub__(self, other: int) -> Param:
        if not isinstance(other, int):
            raise TypeError(f"Param arithmetic requires int, got {type(other)}")
        return Param(self.name, self.offset - other)

    def __repr__(self) -> str:
        if self.offset == 0:
            return f"Param({self.name!r})"
        elif self.offset > 0:
            return f"Param({self.name!r}) + {self.offset}"
        else:
            return f"Param({self.name!r}) - {-self.offset}"

    def resolve(self, bindings: Dict[str, int]) -> int:
        """Resolve to concrete address using bindings."""
        if self.name not in bindings:
            raise ValueError(f"Parameter '{self.name}' not bound")
        addr = bindings[self.name] + self.offset
        if not (0 <= addr <= ADDR_MAX):
            raise ValueError(f"Resolved address {addr} out of range (0..{ADDR_MAX})")
        return addr


@dataclass
class SymbolicInstruction:
    """A symbolic instruction that may contain Param references."""
    op: str
    operands: tuple  # Mix of Param and int values

    def resolve(self, bindings: Dict[str, int]) -> int:
        """Resolve to uint64 instruction word."""
        resolved = []
        for operand in self.operands:
            if isinstance(operand, Param):
                resolved.append(operand.resolve(bindings))
            else:
                resolved.append(operand)

        # Encode based on operation type
        if self.op == "matmul":
            addr_w, addr_x, addr_z, length = resolved
            return encode_systolic(addr_w, addr_x, addr_z, length)
        elif self.op == "vload":
            vreg, addr = resolved
            return encode_vload(vreg, addr)
        elif self.op == "vstore":
            vreg, addr = resolved
            return encode_vstore(vreg, addr)
        elif self.op == "vrelu":
            # vrelu: (vreg_dst, vreg_src) -> use as (vreg_dst, vreg_src, 0, False)
            vreg_dst, vreg_src = resolved
            return encode_vcompute(self.op, vreg_dst, vreg_src, 0, False)
        elif self.op in ("vmax", "vmin"):
            # vmax/vmin: (vreg_dst, vreg_a, vreg_b)
            vreg_dst, vreg_a, vreg_b = resolved
            return encode_vcompute(self.op, vreg_dst, vreg_a, vreg_b, False)
        elif self.op in OPCODES_VCOMPUTE:
            # vadd, vmul, vsub: (vreg_dst, vreg_a, vreg_b, scalar)
            vreg_dst, vreg_a, vreg_b, scalar = resolved
            return encode_vcompute(self.op, vreg_dst, vreg_a, vreg_b, scalar)
        elif self.op in OPCODES_VPU:
            addr_a, addr_b, addr_out = resolved[:3]
            addr_const = resolved[3] if len(resolved) > 3 else 0
            return encode_vpu(self.op, addr_a, addr_b, addr_out, addr_const)
        else:
            raise ValueError(f"Unknown operation: {self.op}")


@dataclass
class CompiledKernel:
    """
    A compiled kernel with symbolic instructions.

    Attributes:
        name: Kernel function name
        params: List of parameter names in order
        instructions: List of SymbolicInstruction objects
    """
    name: str
    params: List[str]
    instructions: List[SymbolicInstruction] = field(default_factory=list)

    def resolve(self, bindings: Dict[str, int]) -> np.ndarray:
        """
        Resolve all symbolic instructions to concrete uint64 values.

        Args:
            bindings: Dict mapping param names to concrete addresses

        Returns:
            np.ndarray of uint64 instruction words
        """
        # Validate all params are bound
        missing = set(self.params) - set(bindings.keys())
        if missing:
            raise ValueError(f"Missing bindings for: {missing}")

        resolved = [instr.resolve(bindings) for instr in self.instructions]
        return np.array(resolved, dtype=np.uint64)


class InstructionCapture:
    """
    Context manager that captures tpu_txt function calls as symbolic instructions.

    Temporarily patches tpu_txt functions to capture operations instead of
    logging to the global instruction_log.
    """

    def __init__(self):
        self.captured: List[SymbolicInstruction] = []
        self._original_functions: Dict[str, Callable] = {}

    def __enter__(self):
        import compiler.tpu_txt as tpu_txt

        # Operations to capture
        ops_to_patch = [
            'matmul', 'add', 'sub', 'mul', 'relu', 'relu_derivative',
            'vload', 'vstore', 'vadd', 'vsub', 'vmul', 'vrelu', 'vmax', 'vmin'
        ]

        for op_name in ops_to_patch:
            if hasattr(tpu_txt, op_name):
                self._original_functions[op_name] = getattr(tpu_txt, op_name)
                setattr(tpu_txt, op_name, self._make_capture_fn(op_name))

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import compiler.tpu_txt as tpu_txt

        # Restore original functions
        for op_name, original_fn in self._original_functions.items():
            setattr(tpu_txt, op_name, original_fn)

        return False

    def _make_capture_fn(self, op_name: str) -> Callable:
        """Create a function that captures calls as symbolic instructions."""
        def capture_fn(*args, **kwargs):
            # Handle operation-specific argument patterns
            if op_name == 'matmul':
                # matmul(W, X, Z, m=4) -> (W, X, Z, m*m)
                W, X, Z = args[:3]
                m = kwargs.get('m', 4) if len(args) < 4 else args[3]
                length = m * m
                operands = (W, X, Z, length)
            elif op_name in ('vload', 'vstore'):
                # vload(vreg, addr) or vstore(vreg, addr)
                operands = args[:2]
            elif op_name in ('vadd', 'vsub', 'vmul'):
                # vadd(dst, a, b, scalar=False)
                vreg_dst, vreg_a, vreg_b = args[:3]
                scalar = kwargs.get('scalar', False) if len(args) < 4 else args[3]
                operands = (vreg_dst, vreg_a, vreg_b, scalar)
            elif op_name == 'vrelu':
                # vrelu(dst, src)
                operands = args[:2]
            elif op_name in ('vmax', 'vmin'):
                # vmax/vmin(dst, a, b)
                operands = args[:3]
            elif op_name in ('relu', 'relu_derivative'):
                # relu(X, Zero_addr, Y) -> vpu op
                operands = args
            else:
                # VPU ops: add(X, Y, Z), sub(X, Y, Z), mul(X, Y, Z)
                operands = args

            self.captured.append(SymbolicInstruction(op_name, operands))

        return capture_fn


class KernelCompiler:
    """Compiles @kernel decorated functions by tracing with symbolic params."""

    def compile(self, kernel_def: Callable) -> CompiledKernel:
        """
        Compile a kernel function to symbolic instructions.

        Args:
            kernel_def: The kernel function decorated with @kernel

        Returns:
            CompiledKernel with symbolic instructions
        """
        # Get parameter names from function signature
        sig = inspect.signature(kernel_def)
        param_names = []
        for name, param in sig.parameters.items():
            # Skip parameters with default values that aren't Params
            if param.annotation == Param or param.default is inspect.Parameter.empty:
                param_names.append(name)

        # Create symbolic Param objects for each parameter
        symbolic_params = {name: Param(name) for name in param_names}

        # Capture instructions by calling the kernel with symbolic params
        with InstructionCapture() as capture:
            kernel_def(**symbolic_params)

        return CompiledKernel(
            name=kernel_def.__name__,
            params=param_names,
            instructions=capture.captured
        )


class KernelLauncher:
    """
    Manages kernel loading and execution on TPU hardware.

    For simplicity, each launch() writes the full instruction image to IMEM.
    Future optimization: cache and reuse previously loaded kernels.
    """

    def __init__(self, driver):
        """
        Initialize launcher with TPU driver.

        Args:
            driver: TpuDriver instance for hardware communication
        """
        self.driver = driver

    def launch(self, compiled: CompiledKernel, **bindings: int) -> None:
        """
        Execute a compiled kernel with bound addresses.

        Args:
            compiled: CompiledKernel to execute
            **bindings: Keyword args mapping param names to addresses

        Example:
            launcher.launch(matmul_kernel, W=0, X=16, Z=32)
        """
        # Resolve symbolic instructions to concrete uint64 values
        instructions = compiled.resolve(bindings)

        # Append HALT instruction
        halt_instr = np.array([encode_halt()], dtype=np.uint64)
        instructions = np.concatenate([instructions, halt_instr])

        # Load and execute
        self.driver.write_instructions(instructions)
        self.driver.compute()

    def launch_batch(self, kernels: List[tuple]) -> int:
        """
        Execute multiple kernels in a single batch with one HALT.

        This is required when the TPU design needs all instructions submitted
        together before execution (e.g., no mid-execution instruction loading).

        Args:
            kernels: List of (CompiledKernel, bindings_dict) tuples

        Returns:
            Total number of instructions executed (excluding HALT)

        Example:
            launcher.launch_batch([
                (vpu_kernel, {'A': 0, 'B': 4, 'C': 8}),
                (matmul_kernel, {'W': 100, 'X': 116, 'Z': 132}),
            ])
        """
        all_instructions = []

        for compiled, bindings in kernels:
            resolved = compiled.resolve(bindings)
            all_instructions.append(resolved)

        # Combine all instructions
        if all_instructions:
            combined = np.concatenate(all_instructions)
        else:
            combined = np.array([], dtype=np.uint64)

        # Append single HALT at end
        halt_instr = np.array([encode_halt()], dtype=np.uint64)
        combined = np.concatenate([combined, halt_instr])

        # Load and execute
        self.driver.write_instructions(combined)
        self.driver.compute()

        return len(combined) - 1  # Exclude HALT from count


class KernelFunction:
    """
    Wrapper for kernel functions that provides the compile() method.

    Created by the @kernel decorator.
    """

    def __init__(self, fn: Callable):
        self._fn = fn
        self._compiler = KernelCompiler()
        functools.update_wrapper(self, fn)

    def __call__(self, *args, **kwargs):
        """Direct call passes through to the wrapped function."""
        return self._fn(*args, **kwargs)

    def compile(self) -> CompiledKernel:
        """Compile this kernel to symbolic instructions."""
        return self._compiler.compile(self._fn)


def kernel(fn: Callable) -> KernelFunction:
    """
    Decorator to define a TPU kernel.

    Usage:
        @kernel
        def my_kernel(W: Param, X: Param, Z: Param):
            from compiler.tpu_txt import matmul
            matmul(W, X, Z)

        compiled = my_kernel.compile()
        launcher.launch(compiled, W=0, X=16, Z=32)
    """
    return KernelFunction(fn)


# Convenience exports
__all__ = [
    'Param',
    'CompiledKernel',
    'SymbolicInstruction',
    'KernelCompiler',
    'KernelLauncher',
    'KernelFunction',
    'kernel',
]
