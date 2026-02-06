#!/usr/bin/env python3
"""
Comprehensive test program definition.

Defines what kernels to run and memory layout. Run to compile:
    python tests/ultra96-v2/programs/comprehensive.py

Output:
    tests/ultra96-v2/comprehensive.npy
    tests/ultra96-v2/comprehensive.hex
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from compiler.program import Program
from compiler.kernel import kernel, Param
from compiler.kernels.matmul import matmul_4x4, matmul_8x8_tiled


# ============================================================================
# Define VPU test kernels
# ============================================================================

@kernel
def vpu_add_n(A: Param, B: Param, C: Param, n: int = 4):
    from compiler.tpu_txt import add
    for i in range(n):
        add(A + i, B + i, C + i)


@kernel
def vpu_sub_n(A: Param, B: Param, C: Param, n: int = 4):
    from compiler.tpu_txt import sub
    for i in range(n):
        sub(A + i, B + i, C + i)


@kernel
def vpu_mul_n(A: Param, B: Param, C: Param, n: int = 4):
    from compiler.tpu_txt import mul
    for i in range(n):
        mul(A + i, B + i, C + i)


@kernel
def vpu_relu_n(X: Param, Zero: Param, Y: Param, n: int = 4):
    from compiler.tpu_txt import relu
    for i in range(n):
        relu(X + i, Zero, Y + i)


# ============================================================================
# Build program
# ============================================================================

def build_comprehensive_program() -> Program:
    """Build the comprehensive test program."""
    prog = Program()

    # VPU test allocations
    a = prog.alloc("a", 4)
    b = prog.alloc("b", 4)
    zero = prog.alloc("zero", 1)
    add_out = prog.alloc("add_out", 4)
    sub_out = prog.alloc("sub_out", 4)
    mul_out = prog.alloc("mul_out", 4)
    relu_out = prog.alloc("relu_out", 4)

    # 4x4 matmul allocations
    W4 = prog.alloc("W4", 16)
    X4 = prog.alloc("X4", 16)
    Z4 = prog.alloc("Z4", 16)

    # 8x8 tiled matmul allocations (tile-major layout)
    W8 = prog.alloc("W8", 64)
    X8 = prog.alloc("X8", 64)
    Z8 = prog.alloc("Z8", 64)
    temp = prog.alloc("temp", 16)

    # Schedule VPU operations
    prog.call(vpu_add_n, A=a, B=b, C=add_out)
    prog.call(vpu_sub_n, A=a, B=b, C=sub_out)
    prog.call(vpu_mul_n, A=a, B=b, C=mul_out)
    prog.call(vpu_relu_n, X=a, Zero=zero, Y=relu_out)

    # Schedule 4x4 matmul
    prog.call(matmul_4x4, W=W4, X=X4, Z=Z4)

    # Schedule 8x8 tiled matmul
    prog.call(matmul_8x8_tiled, W=W8, X=X8, Z=Z8, temp=temp)

    return prog


def main():
    output_dir = Path(__file__).parent.parent

    prog = build_comprehensive_program()

    # Save compiled program
    npy_path = output_dir / "comprehensive.npy"
    hex_path = output_dir / "comprehensive.hex"

    n_instr = prog.save(npy_path)
    prog.save(hex_path)

    print(f"Compiled {n_instr} instructions")
    print(f"  {npy_path}")
    print(f"  {hex_path}")

    # Save memory map for test verification
    import json
    meta_path = output_dir / "comprehensive_meta.json"
    memory_map = {name: {"addr": addr, "size": size}
                  for name, (addr, size) in prog.get_memory_map().items()}
    with open(meta_path, 'w') as f:
        json.dump(memory_map, f, indent=2)
    print(f"  {meta_path}")


if __name__ == "__main__":
    main()
