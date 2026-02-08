#!/usr/bin/env python3
"""
Diagnostic test to find why pressure test outputs all zeros.

Tests progressively more complex scenarios to isolate the issue.
No compiler dependency - all programs loaded from pre-compiled .npy/.hex files.
"""

import argparse
import sys
from pathlib import Path
import numpy as np
import time

from compiler.hal.pynq_host import TpuDriver

DMA_CHUNK = 8


def write_bram_chunked(tpu, addr, values):
    values = np.asarray(values, dtype=np.float32).ravel()
    for i in range(0, len(values), DMA_CHUNK):
        tpu.write_bram(addr + i, values[i:i + DMA_CHUNK])


def read_bram_chunked(tpu, addr, length):
    result = np.empty(length, dtype=np.float32)
    for i in range(0, length, DMA_CHUNK):
        n = min(DMA_CHUNK, length - i)
        result[i:i + n] = tpu.read_bram(addr + i, n)
    return result


def load_program(path):
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


def main():
    parser = argparse.ArgumentParser(description="Pressure test debugger")
    parser.add_argument("bitstream", help="Path to bitstream file (.bit)")
    parser.add_argument("--tpu-ip", default="tpu_0")
    parser.add_argument("--dma-ip", default="axi_dma_0")
    args = parser.parse_args()

    tpu = TpuDriver(args.bitstream, tpu_name=args.tpu_ip, dma_name=args.dma_ip)

    all_pass = True

    # =========================================================================
    # TEST 1: Minimal SIMD program (5 instructions) with direct write_bram
    #   Same pattern as working edge case tests
    # =========================================================================
    print("\n" + "=" * 70)
    print("TEST 1: Minimal 5-instr SIMD program (edge-case style)")
    print("=" * 70)

    # Pre-compiled: vload v0 @0, vload v1 @8, vadd v2=v0+v1, vstore v2 @16, halt
    mini_prog = load_program("pressure_debug_mini.npy")

    print(f"  Program: {len(mini_prog)} instructions")
    for i, instr in enumerate(mini_prog):
        print(f"    [{i}] {instr:#018x}")

    # Write program
    tpu.write_instructions(mini_prog)

    # Write inputs (8-element, like edge cases)
    a = np.array([1, 2, 3, 4, 5, 6, 7, 8], dtype=np.float32)
    b = np.array([10, 20, 30, 40, 50, 60, 70, 80], dtype=np.float32)
    expected = a + b

    tpu.write_bram(0, a)
    tpu.write_bram(8, b)
    tpu.write_bram(16, np.zeros(8, dtype=np.float32))  # Clear output

    # Verify inputs persisted
    readback_a = tpu.read_bram(0, 8)
    readback_b = tpu.read_bram(8, 8)
    print(f"  Input A readback: {readback_a}")
    print(f"  Input B readback: {readback_b}")

    # Compute
    tpu.compute()

    result = tpu.read_bram(16, 8)
    ok = np.allclose(result, expected, rtol=1e-5)
    print(f"  Expected: {expected}")
    print(f"  Got:      {result}")
    print(f"  Result: {'PASS' if ok else 'FAIL'}")
    if not ok:
        all_pass = False

    # =========================================================================
    # TEST 2: Minimal SIMD program but with chunked writes (larger arrays)
    # =========================================================================
    print("\n" + "=" * 70)
    print("TEST 2: Same 5-instr program + chunked writes")
    print("=" * 70)

    # Re-load program (to be safe)
    tpu.write_instructions(mini_prog)

    np.random.seed(42)
    a32 = np.random.uniform(0, 10, 32).astype(np.float32)
    b32 = np.random.uniform(0, 10, 32).astype(np.float32)

    # Program addresses: VLOAD from 0 and 8, VSTORE to 16
    write_bram_chunked(tpu, 0, a32[:8])
    write_bram_chunked(tpu, 8, b32[:8])
    write_bram_chunked(tpu, 16, np.zeros(8, dtype=np.float32))

    # Verify inputs
    readback = read_bram_chunked(tpu, 0, 8)
    print(f"  Input A[0:7] readback: {readback[:4]}...")
    ok_input = np.allclose(readback, a32[:8], rtol=1e-5)
    print(f"  Input persisted: {'YES' if ok_input else 'NO'}")

    tpu.compute()
    result = read_bram_chunked(tpu, 16, 8)
    expected2 = a32[:8] + b32[:8]
    ok = np.allclose(result, expected2, rtol=1e-5)
    print(f"  Expected: {expected2[:4]}...")
    print(f"  Got:      {result[:4]}...")
    print(f"  Result: {'PASS' if ok else 'FAIL'}")
    if not ok:
        all_pass = False

    # =========================================================================
    # TEST 3: Load SIMD pressure program (93 instr), test first chunk only
    # =========================================================================
    print("\n" + "=" * 70)
    print("TEST 3: SIMD pressure program (93 instr), verify first chunk")
    print("=" * 70)

    simd_prog = load_program("pressure_simd.npy")
    print(f"  Loading SIMD program: {len(simd_prog)} instructions")
    print(f"  First 4 instrs:")
    for i in range(min(4, len(simd_prog))):
        print(f"    [{i}] {simd_prog[i]:#018x}")

    tpu.write_instructions(simd_prog)

    # Write inputs at pressure test addresses
    # vec_a_32: addr=0, size=32
    # vec_b_32: addr=32, size=32
    # add_out_32: addr=64, size=32
    np.random.seed(42)
    vec_a_32 = np.random.uniform(0, 10, 32).astype(np.float32)
    vec_b_32 = np.random.uniform(0, 10, 32).astype(np.float32)

    write_bram_chunked(tpu, 0, vec_a_32)
    write_bram_chunked(tpu, 32, vec_b_32)
    write_bram_chunked(tpu, 64, np.zeros(32, dtype=np.float32))

    # Also need to write other inputs the program expects
    mlp_x = np.random.uniform(-5, 5, 32).astype(np.float32)
    write_bram_chunked(tpu, 128, mlp_x)
    mlp_w = np.random.uniform(-1, 1, 32).astype(np.float32)
    write_bram_chunked(tpu, 160, mlp_w)
    mlp_bias = np.random.uniform(-2, 2, 32).astype(np.float32)
    write_bram_chunked(tpu, 192, mlp_bias)

    vec_a_64 = np.random.uniform(0, 10, 64).astype(np.float32)
    write_bram_chunked(tpu, 257, vec_a_64)
    vec_b_64 = np.random.uniform(0, 10, 64).astype(np.float32)
    write_bram_chunked(tpu, 321, vec_b_64)

    # Zero all outputs
    write_bram_chunked(tpu, 64, np.zeros(32, dtype=np.float32))   # add_out_32
    write_bram_chunked(tpu, 96, np.zeros(32, dtype=np.float32))   # mul_out_32
    write_bram_chunked(tpu, 224, np.zeros(32, dtype=np.float32))  # mlp_out
    write_bram_chunked(tpu, 385, np.zeros(64, dtype=np.float32))  # add_out_64

    # Verify inputs survive all those writes
    readback = read_bram_chunked(tpu, 0, 8)
    print(f"  vec_a_32[0:7] after all writes: {readback[:4]}...")
    ok_input = np.allclose(readback, vec_a_32[:8], rtol=1e-5)
    print(f"  Input persisted: {'YES' if ok_input else 'NO'}")

    # Compute
    print("  Running compute...")
    start = time.time()
    tpu.compute()
    elapsed = time.time() - start
    print(f"  Compute time: {elapsed*1000:.3f} ms")

    # Check inputs survived compute
    readback_post = read_bram_chunked(tpu, 0, 8)
    print(f"  vec_a_32[0:7] AFTER compute: {readback_post[:4]}...")
    ok_survive = np.allclose(readback_post, vec_a_32[:8], rtol=1e-5)
    print(f"  Inputs survived compute: {'YES' if ok_survive else 'NO'}")

    # Check outputs
    add32_result = read_bram_chunked(tpu, 64, 32)
    add32_expected = vec_a_32 + vec_b_32
    ok = np.allclose(add32_result, add32_expected, rtol=1e-5)
    print(f"  add_out_32 expected[0:4]: {add32_expected[:4]}")
    print(f"  add_out_32 got[0:4]:      {add32_result[:4]}")
    all_zero = np.all(add32_result == 0)
    print(f"  add_out_32 all zeros: {all_zero}")
    print(f"  add_out_32 result: {'PASS' if ok else 'FAIL'}")
    if not ok:
        all_pass = False

    mul32_result = read_bram_chunked(tpu, 96, 32)
    mul32_expected = vec_a_32 * vec_b_32
    ok = np.allclose(mul32_result, mul32_expected, rtol=1e-5)
    print(f"  mul_out_32 expected[0:4]: {mul32_expected[:4]}")
    print(f"  mul_out_32 got[0:4]:      {mul32_result[:4]}")
    print(f"  mul_out_32 result: {'PASS' if ok else 'FAIL'}")
    if not ok:
        all_pass = False

    # =========================================================================
    # TEST 4: Load SCALAR pressure program (225 instr), test first 8
    # =========================================================================
    print("\n" + "=" * 70)
    print("TEST 4: Scalar pressure program (225 instr), verify first chunk")
    print("=" * 70)

    scalar_prog = load_program("pressure_scalar.npy")
    print(f"  Loading scalar program: {len(scalar_prog)} instructions")
    print(f"  First 4 instrs:")
    for i in range(min(4, len(scalar_prog))):
        print(f"    [{i}] {scalar_prog[i]:#018x}")

    tpu.write_instructions(scalar_prog)

    # Re-write all inputs (same seed)
    np.random.seed(42)
    vec_a_32 = np.random.uniform(0, 10, 32).astype(np.float32)
    vec_b_32 = np.random.uniform(0, 10, 32).astype(np.float32)
    mlp_x = np.random.uniform(-5, 5, 32).astype(np.float32)
    mlp_w = np.random.uniform(-1, 1, 32).astype(np.float32)
    mlp_bias = np.random.uniform(-2, 2, 32).astype(np.float32)
    tpu.write_bram(256, np.array([0.0], dtype=np.float32))  # zero

    vec_a_64 = np.random.uniform(0, 10, 64).astype(np.float32)
    vec_b_64 = np.random.uniform(0, 10, 64).astype(np.float32)

    write_bram_chunked(tpu, 0, vec_a_32)
    write_bram_chunked(tpu, 32, vec_b_32)
    write_bram_chunked(tpu, 128, mlp_x)
    write_bram_chunked(tpu, 160, mlp_w)
    write_bram_chunked(tpu, 192, mlp_bias)
    write_bram_chunked(tpu, 257, vec_a_64)
    write_bram_chunked(tpu, 321, vec_b_64)

    # Zero outputs
    write_bram_chunked(tpu, 64, np.zeros(32, dtype=np.float32))
    write_bram_chunked(tpu, 96, np.zeros(32, dtype=np.float32))
    write_bram_chunked(tpu, 224, np.zeros(32, dtype=np.float32))
    write_bram_chunked(tpu, 385, np.zeros(64, dtype=np.float32))

    # Compute
    print("  Running compute...")
    start = time.time()
    tpu.compute()
    elapsed = time.time() - start
    print(f"  Compute time: {elapsed*1000:.3f} ms")

    # Check add_out_32 first 8 elements
    add32_result = read_bram_chunked(tpu, 64, 8)
    add32_expected = vec_a_32[:8] + vec_b_32[:8]
    ok = np.allclose(add32_result, add32_expected, rtol=1e-5)
    print(f"  Scalar add[0:7] expected: {add32_expected[:4]}...")
    print(f"  Scalar add[0:7] got:      {add32_result[:4]}...")
    all_zero = np.all(add32_result == 0)
    print(f"  Scalar add all zeros: {all_zero}")
    print(f"  Result: {'PASS' if ok else 'FAIL'}")
    if not ok:
        all_pass = False
        # Also check if inputs survived
        readback = read_bram_chunked(tpu, 0, 8)
        print(f"  vec_a_32[0:7] after compute: {readback[:4]}...")

    # =========================================================================
    # TEST 5: Edge case program (working reference) - just to compare
    # =========================================================================
    print("\n" + "=" * 70)
    print("TEST 5: Edge case program (known working, 81 instr)")
    print("=" * 70)

    edge_prog = load_program("simd_edge_cases.hex")
    print(f"  Loading edge case program: {len(edge_prog)} instructions")

    tpu.write_instructions(edge_prog)

    # Write simple test inputs at edge case addresses
    tpu.write_bram(0, np.zeros(8, dtype=np.float32))     # zeros
    tpu.write_bram(8, np.ones(8, dtype=np.float32))       # ones
    tpu.write_bram(24, np.arange(1, 9, dtype=np.float32)) # input_a
    tpu.write_bram(16, np.full(8, -1.0, dtype=np.float32)) # neg_ones
    tpu.write_bram(32, -np.arange(1, 9, dtype=np.float32)) # neg_a
    tpu.write_bram(40, np.arange(0.5, 4.5, 0.5, dtype=np.float32))  # input_b
    tpu.write_bram(48, np.array([-10,-20,-30,-40,-50,-60,-70,-80], dtype=np.float32))
    tpu.write_bram(56, np.array([10,20,30,40,50,60,70,80], dtype=np.float32))
    tpu.write_bram(64, np.array([1e30,2e30,3e30,4e30,5e30,6e30,7e30,8e30], dtype=np.float32))
    tpu.write_bram(72, np.full(8, 1e30, dtype=np.float32))
    tpu.write_bram(80, np.array([1e-20,2e-20,3e-20,4e-20,5e-20,6e-20,7e-20,8e-20], dtype=np.float32))
    tpu.write_bram(88, np.full(8, 1e-20, dtype=np.float32))
    tpu.write_bram(96, np.array([100.0], dtype=np.float32))
    for i in range(8):
        tpu.write_bram(97 + i * 8, np.full(8, float(i + 1), dtype=np.float32))

    tpu.compute()

    # Check test 1: add zeros+zeros = zeros (out_add_zeros at 161)
    result = tpu.read_bram(161, 8)
    expected_z = np.zeros(8, dtype=np.float32)
    ok1 = np.allclose(result, expected_z, rtol=1e-5)
    print(f"  Test 1 (add zeros): {result[:4]} -> {'PASS' if ok1 else 'FAIL'}")

    # Check test 5: mul identity (out_mul_identity at 193)
    result = tpu.read_bram(193, 8)
    expected_m = np.arange(1, 9, dtype=np.float32)
    ok5 = np.allclose(result, expected_m, rtol=1e-5)
    print(f"  Test 5 (mul identity): {result[:4]} -> {'PASS' if ok5 else 'FAIL'}")

    # Check test 13: chain (A+B)*A (out_chain at 257)
    input_a = np.arange(1, 9, dtype=np.float32)
    input_b = np.arange(0.5, 4.5, 0.5, dtype=np.float32)
    result = tpu.read_bram(257, 8)
    expected_c = (input_a + input_b) * input_a
    ok13 = np.allclose(result, expected_c, rtol=1e-5)
    print(f"  Test 13 (chain): expected {expected_c[:4]}, got {result[:4]} -> {'PASS' if ok13 else 'FAIL'}")

    if not (ok1 and ok5 and ok13):
        all_pass = False

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    if all_pass:
        print("ALL DIAGNOSTIC TESTS PASSED")
    else:
        print("SOME DIAGNOSTIC TESTS FAILED")
    print("=" * 70)

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
