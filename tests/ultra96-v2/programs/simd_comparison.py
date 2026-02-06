#!/usr/bin/env python3
"""
SIMD vs Scalar VPU comparison test program.

This program demonstrates the performance benefits of SIMD vector operations
compared to traditional scalar VPU operations.

Run to compile:
    python tests/ultra96-v2/programs/simd_comparison.py

Output:
    tests/ultra96-v2/simd_comparison.npy
    tests/ultra96-v2/simd_comparison.hex
    tests/ultra96-v2/simd_comparison_meta.json
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from compiler.program import Program
from compiler.kernel import kernel, Param
from compiler.kernels.vpu import vector_add, vector_mul
from compiler.kernels.vpu_simd import (
    vector_add_simd,
    vector_mul_simd,
    vector_relu_simd,
    vector_scale_simd,
    fused_mlp_layer_simd,
)


# ============================================================================
# Scalar baseline kernels (for comparison)
# ============================================================================

@kernel
def vector_add_scalar_8(A: Param, B: Param, C: Param):
    """8-element add using scalar VPU (baseline)."""
    from compiler.tpu_txt import add
    for i in range(8):
        add(A + i, B + i, C + i)


@kernel
def vector_mul_scalar_8(A: Param, B: Param, C: Param):
    """8-element mul using scalar VPU (baseline)."""
    from compiler.tpu_txt import mul
    for i in range(8):
        mul(A + i, B + i, C + i)


# ============================================================================
# Build comparison program
# ============================================================================

def build_simd_comparison_program() -> Program:
    """
    Build SIMD vs Scalar comparison test program.

    Memory Layout:
        - test_input_a: 8 elements for input A
        - test_input_b: 8 elements for input B
        - scalar_add_out: 8 elements (scalar VPU result)
        - simd_add_out: 8 elements (SIMD VPU result)
        - scalar_mul_out: 8 elements (scalar VPU result)
        - simd_mul_out: 8 elements (SIMD VPU result)
        - relu_input: 8 elements (mixed pos/neg values)
        - relu_out: 8 elements (SIMD ReLU result)
        - scale_input: 8 elements
        - scale_value: 1 element (scalar for broadcast)
        - scale_out: 8 elements (SIMD scale result)
        - mlp_x, mlp_w, mlp_bias, mlp_out: 8 elements each

    Test Cases:
        1. Addition: Compare scalar vs SIMD add (8 elements)
        2. Multiplication: Compare scalar vs SIMD mul (8 elements)
        3. ReLU: SIMD-only test (8 elements)
        4. Scalar broadcast: SIMD-only test (8 elements * scalar)
        5. Fused MLP layer: SIMD-only test (mul + add + relu)
    """
    prog = Program()

    # ========================================================================
    # Allocations
    # ========================================================================

    # Test Case 1: Vector Addition (Scalar vs SIMD)
    test_input_a = prog.alloc("test_input_a", 8)
    test_input_b = prog.alloc("test_input_b", 8)
    scalar_add_out = prog.alloc("scalar_add_out", 8)
    simd_add_out = prog.alloc("simd_add_out", 8)

    # Test Case 2: Vector Multiplication (Scalar vs SIMD)
    scalar_mul_out = prog.alloc("scalar_mul_out", 8)
    simd_mul_out = prog.alloc("simd_mul_out", 8)

    # Test Case 3: ReLU (SIMD only)
    relu_input = prog.alloc("relu_input", 8)
    relu_out = prog.alloc("relu_out", 8)

    # Test Case 4: Scalar Broadcast (SIMD only)
    scale_input = prog.alloc("scale_input", 8)
    scale_value = prog.alloc("scale_value", 1)
    scale_out = prog.alloc("scale_out", 8)

    # Test Case 5: Fused MLP Layer (SIMD only)
    mlp_x = prog.alloc("mlp_x", 8)
    mlp_w = prog.alloc("mlp_w", 8)
    mlp_bias = prog.alloc("mlp_bias", 8)
    mlp_out = prog.alloc("mlp_out", 8)

    # ========================================================================
    # Kernel Calls
    # ========================================================================

    # Test 1: Addition comparison
    prog.call(vector_add_scalar_8, A=test_input_a, B=test_input_b, C=scalar_add_out)
    prog.call(vector_add_simd, A=test_input_a, B=test_input_b, C=simd_add_out)

    # Test 2: Multiplication comparison
    prog.call(vector_mul_scalar_8, A=test_input_a, B=test_input_b, C=scalar_mul_out)
    prog.call(vector_mul_simd, A=test_input_a, B=test_input_b, C=simd_mul_out)

    # Test 3: ReLU (SIMD only)
    prog.call(vector_relu_simd, X=relu_input, Y=relu_out)

    # Test 4: Scalar broadcast (SIMD only)
    prog.call(vector_scale_simd, X=scale_input, Scale=scale_value, Y=scale_out)

    # Test 5: Fused MLP layer (SIMD only)
    prog.call(fused_mlp_layer_simd, X=mlp_x, W=mlp_w, Bias=mlp_bias, Y=mlp_out)

    return prog


def main():
    output_dir = Path(__file__).parent.parent

    prog = build_simd_comparison_program()

    # Save compiled program
    npy_path = output_dir / "simd_comparison.npy"
    hex_path = output_dir / "simd_comparison.hex"

    n_instr = prog.save(npy_path)
    prog.save(hex_path)

    print(f"Compiled {n_instr} instructions")
    print(f"  {npy_path}")
    print(f"  {hex_path}")

    # Save memory map for test verification
    import json
    meta_path = output_dir / "simd_comparison_meta.json"
    memory_map = {name: {"addr": addr, "size": size}
                  for name, (addr, size) in prog.get_memory_map().items()}
    with open(meta_path, 'w') as f:
        json.dump(memory_map, f, indent=2)
    print(f"  {meta_path}")

    # Print expected speedup
    print("\n" + "="*60)
    print("Expected Performance (instruction count)")
    print("="*60)
    print("Test 1: 8-element Addition")
    print("  Scalar VPU:  8 instructions")
    print("  SIMD VPU:    4 instructions (2 vload, 1 vadd, 1 vstore)")
    print("  Speedup:     2x (instruction count)")
    print()
    print("Test 2: 8-element Multiplication")
    print("  Scalar VPU:  8 instructions")
    print("  SIMD VPU:    4 instructions (2 vload, 1 vmul, 1 vstore)")
    print("  Speedup:     2x (instruction count)")
    print()
    print("Test 3: 8-element ReLU")
    print("  SIMD VPU:    3 instructions (1 vload, 1 vrelu, 1 vstore)")
    print()
    print("Test 4: 8-element Scalar Broadcast")
    print("  SIMD VPU:    4 instructions (2 vload, 1 vmul.s, 1 vstore)")
    print()
    print("Test 5: Fused MLP Layer (mul + add + relu)")
    print("  Scalar VPU:  24 instructions")
    print("  SIMD VPU:    6 instructions (3 vload, 1 vmul, 1 vadd, 1 vrelu, 1 vstore)")
    print("  Speedup:     4x (instruction count)")
    print("="*60)


if __name__ == "__main__":
    main()
