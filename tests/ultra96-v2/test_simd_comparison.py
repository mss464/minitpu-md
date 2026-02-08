#!/usr/bin/env python3
"""
SIMD vs Scalar VPU comparison test for Mini-TPU.

Compile program first:
    python tests/ultra96-v2/programs/simd_comparison.py

Run on board:
    make -C tests board-simd-comparison \
        BIT=tpu/ultra96-v2/output/artifacts/minitpu.bit \
        HWH=tpu/ultra96-v2/output/artifacts/minitpu.hwh \
        BOARD_IP=<ip>
"""

import argparse
import sys
import json
from pathlib import Path
import numpy as np
import time

# Runtime is copied to board
from compiler.hal.pynq_host import TpuDriver


def load_program(path):
    """Load compiled program from .npy or .hex file."""
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


def write_test_inputs(tpu, memory_map):
    """Write all test input data to BRAM before execution."""
    # Test 1 & 2 inputs (shared)
    a_data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], dtype=np.float32)
    b_data = np.array([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], dtype=np.float32)
    tpu.write_bram(memory_map["test_input_a"]["addr"], a_data)
    tpu.write_bram(memory_map["test_input_b"]["addr"], b_data)

    # Test 3 input (ReLU)
    relu_data = np.array([1.0, -2.0, 3.0, -4.0, 5.0, -6.0, 7.0, -8.0], dtype=np.float32)
    tpu.write_bram(memory_map["relu_input"]["addr"], relu_data)

    # Test 4 inputs (scalar broadcast)
    scale_data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], dtype=np.float32)
    scale_val = np.array([0.5], dtype=np.float32)
    tpu.write_bram(memory_map["scale_input"]["addr"], scale_data)
    tpu.write_bram(memory_map["scale_value"]["addr"], scale_val)

    # Test 5 inputs (fused MLP)
    mlp_x_data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], dtype=np.float32)
    mlp_w_data = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], dtype=np.float32)
    mlp_bias_data = np.array([-1.0, -2.0, -3.0, -4.0, -5.0, -6.0, -7.0, -8.0], dtype=np.float32)
    tpu.write_bram(memory_map["mlp_x"]["addr"], mlp_x_data)
    tpu.write_bram(memory_map["mlp_w"]["addr"], mlp_w_data)
    tpu.write_bram(memory_map["mlp_bias"]["addr"], mlp_bias_data)


def test_simd_comparison(tpu, memory_map):
    """
    Test SIMD vs Scalar VPU operations.

    Verifies:
        1. Scalar and SIMD produce identical results
        2. SIMD vector operations work correctly
        3. Scalar broadcast works correctly
        4. Fused operations work correctly
    """
    print("\n" + "="*70)
    print("SIMD VPU Comparison Test")
    print("="*70)

    all_pass = True

    # ========================================================================
    # Test 1: Vector Addition (Scalar vs SIMD)
    # ========================================================================
    print("\n[Test 1] Vector Addition: Scalar vs SIMD")

    # Expected results (data was written before compute())
    a_data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], dtype=np.float32)
    b_data = np.array([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], dtype=np.float32)
    expected = a_data + b_data

    # Read results
    scalar_add_addr = memory_map["scalar_add_out"]["addr"]
    simd_add_addr = memory_map["simd_add_out"]["addr"]
    scalar_result = tpu.read_bram(scalar_add_addr, 8)
    simd_result = tpu.read_bram(simd_add_addr, 8)

    # Verify
    scalar_match = np.allclose(scalar_result, expected, rtol=1e-5)
    simd_match = np.allclose(simd_result, expected, rtol=1e-5)
    results_match = np.allclose(scalar_result, simd_result, rtol=1e-6)

    print(f"  Expected: {expected}")
    print(f"  Scalar:   {scalar_result}")
    print(f"  SIMD:     {simd_result}")
    print(f"  Scalar correct: {scalar_match}")
    print(f"  SIMD correct:   {simd_match}")
    print(f"  Results match:  {results_match}")

    if scalar_match and simd_match and results_match:
        print("  ✓ PASS")
    else:
        print("  ✗ FAIL")
        all_pass = False

    # ========================================================================
    # Test 2: Vector Multiplication (Scalar vs SIMD)
    # ========================================================================
    print("\n[Test 2] Vector Multiplication: Scalar vs SIMD")

    expected_mul = a_data * b_data

    # Read results
    scalar_mul_addr = memory_map["scalar_mul_out"]["addr"]
    simd_mul_addr = memory_map["simd_mul_out"]["addr"]
    scalar_result = tpu.read_bram(scalar_mul_addr, 8)
    simd_result = tpu.read_bram(simd_mul_addr, 8)

    # Verify
    scalar_match = np.allclose(scalar_result, expected_mul, rtol=1e-5)
    simd_match = np.allclose(simd_result, expected_mul, rtol=1e-5)
    results_match = np.allclose(scalar_result, simd_result, rtol=1e-6)

    print(f"  Expected: {expected_mul}")
    print(f"  Scalar:   {scalar_result}")
    print(f"  SIMD:     {simd_result}")
    print(f"  Scalar correct: {scalar_match}")
    print(f"  SIMD correct:   {simd_match}")
    print(f"  Results match:  {results_match}")

    if scalar_match and simd_match and results_match:
        print("  ✓ PASS")
    else:
        print("  ✗ FAIL")
        all_pass = False

    # ========================================================================
    # Test 3: SIMD ReLU
    # ========================================================================
    print("\n[Test 3] SIMD ReLU (clamp negative to zero)")

    # Expected results (data was written before compute())
    relu_data = np.array([1.0, -2.0, 3.0, -4.0, 5.0, -6.0, 7.0, -8.0], dtype=np.float32)
    expected_relu = np.maximum(relu_data, 0)

    # Read result
    relu_out_addr = memory_map["relu_out"]["addr"]
    relu_result = tpu.read_bram(relu_out_addr, 8)

    # Verify
    relu_match = np.allclose(relu_result, expected_relu, rtol=1e-5)

    print(f"  Input:    {relu_data}")
    print(f"  Expected: {expected_relu}")
    print(f"  Result:   {relu_result}")
    print(f"  Correct:  {relu_match}")

    if relu_match:
        print("  ✓ PASS")
    else:
        print("  ✗ FAIL")
        all_pass = False

    # ========================================================================
    # Test 4: SIMD Scalar Broadcast
    # ========================================================================
    print("\n[Test 4] SIMD Scalar Broadcast (vector * scalar)")

    # Expected results (data was written before compute())
    scale_data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], dtype=np.float32)
    scale_val = np.array([0.5], dtype=np.float32)
    expected_scale = scale_data * scale_val[0]

    # Read result
    scale_out_addr = memory_map["scale_out"]["addr"]
    scale_result = tpu.read_bram(scale_out_addr, 8)

    # Verify
    scale_match = np.allclose(scale_result, expected_scale, rtol=1e-5)

    print(f"  Vector:   {scale_data}")
    print(f"  Scalar:   {scale_val[0]}")
    print(f"  Expected: {expected_scale}")
    print(f"  Result:   {scale_result}")
    print(f"  Correct:  {scale_match}")

    if scale_match:
        print("  ✓ PASS")
    else:
        print("  ✗ FAIL")
        all_pass = False

    # ========================================================================
    # Test 5: Fused MLP Layer (mul + add + relu)
    # ========================================================================
    print("\n[Test 5] Fused MLP Layer: Y = ReLU(X * W + Bias)")

    # Expected results (data was written before compute())
    mlp_x_data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], dtype=np.float32)
    mlp_w_data = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], dtype=np.float32)
    mlp_bias_data = np.array([-1.0, -2.0, -3.0, -4.0, -5.0, -6.0, -7.0, -8.0], dtype=np.float32)
    expected_mlp = np.maximum(mlp_x_data * mlp_w_data + mlp_bias_data, 0)

    # Read result
    mlp_out_addr = memory_map["mlp_out"]["addr"]
    mlp_result = tpu.read_bram(mlp_out_addr, 8)

    # Verify
    mlp_match = np.allclose(mlp_result, expected_mlp, rtol=1e-5)

    print(f"  X =       {mlp_x_data}")
    print(f"  W =       {mlp_w_data}")
    print(f"  Bias =    {mlp_bias_data}")
    print(f"  Expected: {expected_mlp}")
    print(f"  Result:   {mlp_result}")
    print(f"  Correct:  {mlp_match}")

    if mlp_match:
        print("  ✓ PASS")
    else:
        print("  ✗ FAIL")
        all_pass = False

    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "="*70)
    if all_pass:
        print("ALL TESTS PASSED ✓")
    else:
        print("SOME TESTS FAILED ✗")
    print("="*70)

    return all_pass


def main():
    parser = argparse.ArgumentParser(
        description="SIMD VPU comparison test for Mini-TPU"
    )
    parser.add_argument("bitstream", help="Path to bitstream file (.bit)")
    parser.add_argument("--instructions", "-i", default="simd_comparison.npy",
                        help="Compiled program file (.npy or .hex)")
    parser.add_argument("--metadata", "-m", default="simd_comparison_meta.json",
                        help="Memory map metadata file (.json)")
    parser.add_argument("--tpu-ip", default="tpu_0",
                        help="TPU IP name in overlay (default: tpu_0)")
    parser.add_argument("--dma-ip", default="axi_dma_0",
                        help="DMA IP name in overlay (default: axi_dma_0)")
    args = parser.parse_args()

    # Load compiled program and metadata
    instructions = load_program(args.instructions)
    with open(args.metadata) as f:
        memory_map = json.load(f)

    print(f"\nLoading bitstream: {args.bitstream}")
    print(f"Program: {args.instructions} ({len(instructions)} instructions)")
    print(f"Memory map: {len(memory_map)} allocations")

    # Initialize TPU
    tpu = TpuDriver(args.bitstream, tpu_name=args.tpu_ip, dma_name=args.dma_ip)

    # Load program
    print("\nLoading program...")
    tpu.write_instructions(instructions)

    # Write test inputs to BRAM
    print("Writing test inputs...")
    write_test_inputs(tpu, memory_map)

    # Execute
    print("Executing program...")
    start_time = time.time()
    tpu.compute()
    elapsed = time.time() - start_time
    print(f"Execution time: {elapsed*1000:.2f} ms")

    # Verify results
    success = test_simd_comparison(tpu, memory_map)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
