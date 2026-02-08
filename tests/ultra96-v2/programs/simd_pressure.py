#!/usr/bin/env python3
"""
SIMD VPU pressure/performance test program.

Generates TWO programs (scalar baseline and SIMD) that compute identical
workloads, allowing wall-clock timing comparison on the board.

IMPORTANT: Instruction BRAM (blk_mem_gen_1) holds only 256 entries.
All programs MUST fit within 255 instructions + 1 HALT = 256 total.

Run to compile:
    PYTHONPATH=. python3 tests/ultra96-v2/programs/simd_pressure.py

Output:
    tests/ultra96-v2/pressure_scalar.npy
    tests/ultra96-v2/pressure_simd.npy
    tests/ultra96-v2/pressure_meta.json
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from compiler.program import Program
from compiler.kernel import kernel, Param

IRAM_DEPTH = 256  # Hardware limit (8-bit PC)


# ============================================================================
# Scalar kernels (one element per instruction)
# ============================================================================

@kernel
def scalar_add_32(A: Param, B: Param, C: Param):
    """32-element add using scalar VPU: 32 instructions."""
    from compiler.tpu_txt import add
    for i in range(32):
        add(A + i, B + i, C + i)


@kernel
def scalar_mul_32(A: Param, B: Param, C: Param):
    """32-element mul using scalar VPU: 32 instructions."""
    from compiler.tpu_txt import mul
    for i in range(32):
        mul(A + i, B + i, C + i)


@kernel
def scalar_mlp_32(X: Param, W: Param, Bias: Param, Zero: Param, Y: Param):
    """32-element fused MLP: Y = ReLU(X*W + Bias). 96 instructions."""
    from compiler.tpu_txt import mul, add, relu
    for i in range(32):
        mul(X + i, W + i, Y + i)       # Y[i] = X[i] * W[i]
    for i in range(32):
        add(Y + i, Bias + i, Y + i)    # Y[i] = Y[i] + Bias[i]
    for i in range(32):
        relu(Y + i, Zero, Y + i)       # Y[i] = ReLU(Y[i])


@kernel
def scalar_add_64(A: Param, B: Param, C: Param):
    """64-element add using scalar VPU: 64 instructions."""
    from compiler.tpu_txt import add
    for i in range(64):
        add(A + i, B + i, C + i)


# ============================================================================
# SIMD kernels (8 elements per instruction)
# ============================================================================

@kernel
def simd_add_32(A: Param, B: Param, C: Param):
    """32-element add using SIMD VPU: 16 instructions."""
    from compiler.tpu_txt import vload, vadd, vstore
    for chunk in range(4):
        off = chunk * 8
        vload(0, A + off)
        vload(1, B + off)
        vadd(2, 0, 1)
        vstore(2, C + off)


@kernel
def simd_mul_32(A: Param, B: Param, C: Param):
    """32-element mul using SIMD VPU: 16 instructions."""
    from compiler.tpu_txt import vload, vmul, vstore
    for chunk in range(4):
        off = chunk * 8
        vload(0, A + off)
        vload(1, B + off)
        vmul(2, 0, 1)
        vstore(2, C + off)


@kernel
def simd_mlp_32(X: Param, W: Param, Bias: Param, Y: Param):
    """32-element fused MLP: Y = ReLU(X*W + Bias). 28 instructions."""
    from compiler.tpu_txt import vload, vmul, vadd, vrelu, vstore
    for chunk in range(4):
        off = chunk * 8
        vload(0, X + off)
        vload(1, W + off)
        vload(2, Bias + off)
        vmul(3, 0, 1)       # V3 = X * W
        vadd(4, 3, 2)       # V4 = V3 + Bias
        vrelu(5, 4)         # V5 = ReLU(V4)
        vstore(5, Y + off)


@kernel
def simd_add_64(A: Param, B: Param, C: Param):
    """64-element add using SIMD VPU: 32 instructions."""
    from compiler.tpu_txt import vload, vadd, vstore
    for chunk in range(8):
        off = chunk * 8
        vload(0, A + off)
        vload(1, B + off)
        vadd(2, 0, 1)
        vstore(2, C + off)


# ============================================================================
# Build programs
# ============================================================================

def alloc_shared(prog):
    """Allocate shared memory layout. Both programs must call this identically."""
    layout = {}
    layout["vec_a_32"] = prog.alloc("vec_a_32", 32)
    layout["vec_b_32"] = prog.alloc("vec_b_32", 32)
    layout["add_out_32"] = prog.alloc("add_out_32", 32)
    layout["mul_out_32"] = prog.alloc("mul_out_32", 32)
    layout["mlp_x"] = prog.alloc("mlp_x", 32)
    layout["mlp_w"] = prog.alloc("mlp_w", 32)
    layout["mlp_bias"] = prog.alloc("mlp_bias", 32)
    layout["mlp_out"] = prog.alloc("mlp_out", 32)
    layout["zero"] = prog.alloc("zero", 1)
    layout["vec_a_64"] = prog.alloc("vec_a_64", 64)
    layout["vec_b_64"] = prog.alloc("vec_b_64", 64)
    layout["add_out_64"] = prog.alloc("add_out_64", 64)
    return layout


def build_scalar_program() -> Program:
    prog = Program()
    l = alloc_shared(prog)

    prog.call(scalar_add_32, A=l["vec_a_32"], B=l["vec_b_32"], C=l["add_out_32"])
    prog.call(scalar_mul_32, A=l["vec_a_32"], B=l["vec_b_32"], C=l["mul_out_32"])
    prog.call(scalar_mlp_32, X=l["mlp_x"], W=l["mlp_w"], Bias=l["mlp_bias"],
              Zero=l["zero"], Y=l["mlp_out"])
    prog.call(scalar_add_64, A=l["vec_a_64"], B=l["vec_b_64"], C=l["add_out_64"])

    return prog


def build_simd_program() -> Program:
    prog = Program()
    l = alloc_shared(prog)

    prog.call(simd_add_32, A=l["vec_a_32"], B=l["vec_b_32"], C=l["add_out_32"])
    prog.call(simd_mul_32, A=l["vec_a_32"], B=l["vec_b_32"], C=l["mul_out_32"])
    prog.call(simd_mlp_32, X=l["mlp_x"], W=l["mlp_w"], Bias=l["mlp_bias"],
              Y=l["mlp_out"])
    prog.call(simd_add_64, A=l["vec_a_64"], B=l["vec_b_64"], C=l["add_out_64"])

    return prog


def main():
    output_dir = Path(__file__).parent.parent

    # Build and save scalar program
    scalar_prog = build_scalar_program()
    scalar_npy = output_dir / "pressure_scalar.npy"
    n_scalar = scalar_prog.save(scalar_npy)
    print(f"Scalar program: {n_scalar} instructions -> {scalar_npy}")

    # Build and save SIMD program
    simd_prog = build_simd_program()
    simd_npy = output_dir / "pressure_simd.npy"
    n_simd = simd_prog.save(simd_npy)
    print(f"SIMD program:   {n_simd} instructions -> {simd_npy}")

    # Validate against IRAM depth
    if n_scalar > IRAM_DEPTH:
        print(f"\nERROR: Scalar program ({n_scalar}) exceeds IRAM depth ({IRAM_DEPTH})!")
        return 1
    if n_simd > IRAM_DEPTH:
        print(f"\nERROR: SIMD program ({n_simd}) exceeds IRAM depth ({IRAM_DEPTH})!")
        return 1

    # Save memory map (same for both programs)
    import json
    meta_path = output_dir / "pressure_meta.json"
    memory_map = {name: {"addr": addr, "size": size}
                  for name, (addr, size) in simd_prog.get_memory_map().items()}
    with open(meta_path, 'w') as f:
        json.dump(memory_map, f, indent=2)
    print(f"Memory map:     {meta_path}")

    print(f"\nInstruction count comparison:")
    print(f"  Scalar: {n_scalar} instructions (IRAM limit: {IRAM_DEPTH})")
    print(f"  SIMD:   {n_simd} instructions")
    print(f"  Ratio:  {n_scalar/n_simd:.2f}x fewer instructions with SIMD")

    print(f"\nBreakdown:")
    print(f"  32-elem add:  scalar=32, simd=16  (2.0x)")
    print(f"  32-elem mul:  scalar=32, simd=16  (2.0x)")
    print(f"  32-elem MLP:  scalar=96, simd=28  (3.4x)")
    print(f"  64-elem add:  scalar=64, simd=32  (2.0x)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
