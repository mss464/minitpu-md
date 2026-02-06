#!/usr/bin/env python3
"""
SIMD VPU corner/edge case test harness.

Compile program first:
    PYTHONPATH=. python3 tests/ultra96-v2/programs/simd_edge_cases.py

Run on board:
    make -C tests board-simd-edge-cases \
        BIT=tpu/ultra96-v2/output/artifacts/minitpu.bit \
        HWH=tpu/ultra96-v2/output/artifacts/minitpu.hwh
"""

import argparse
import sys
import json
from pathlib import Path
import numpy as np
import time

from compiler.hal.pynq_host import TpuDriver


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


def write_test_inputs(tpu, mm):
    """Write all input data to BRAM."""
    # zeros: [0, 0, ..., 0]
    tpu.write_bram(mm["zeros"]["addr"],
                   np.zeros(8, dtype=np.float32))

    # ones: [1, 1, ..., 1]
    tpu.write_bram(mm["ones"]["addr"],
                   np.ones(8, dtype=np.float32))

    # neg_ones: [-1, -1, ..., -1]
    tpu.write_bram(mm["neg_ones"]["addr"],
                   np.full(8, -1.0, dtype=np.float32))

    # input_a: [1, 2, 3, 4, 5, 6, 7, 8]
    tpu.write_bram(mm["input_a"]["addr"],
                   np.arange(1, 9, dtype=np.float32))

    # neg_a: [-1, -2, ..., -8]
    tpu.write_bram(mm["neg_a"]["addr"],
                   -np.arange(1, 9, dtype=np.float32))

    # input_b: [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    tpu.write_bram(mm["input_b"]["addr"],
                   np.arange(0.5, 4.5, 0.5, dtype=np.float32))

    # all_neg: [-10, -20, ..., -80]
    tpu.write_bram(mm["all_neg"]["addr"],
                   np.array([-10, -20, -30, -40, -50, -60, -70, -80],
                            dtype=np.float32))

    # all_pos: [10, 20, ..., 80]
    tpu.write_bram(mm["all_pos"]["addr"],
                   np.array([10, 20, 30, 40, 50, 60, 70, 80],
                            dtype=np.float32))

    # large_a / large_b: large but not infinite after addition
    tpu.write_bram(mm["large_a"]["addr"],
                   np.array([1e30, 2e30, 3e30, 4e30, 5e30, 6e30, 7e30, 8e30],
                            dtype=np.float32))
    tpu.write_bram(mm["large_b"]["addr"],
                   np.array([1e30, 1e30, 1e30, 1e30, 1e30, 1e30, 1e30, 1e30],
                            dtype=np.float32))

    # small_a / small_b: very small
    tpu.write_bram(mm["small_a"]["addr"],
                   np.array([1e-20, 2e-20, 3e-20, 4e-20,
                             5e-20, 6e-20, 7e-20, 8e-20], dtype=np.float32))
    tpu.write_bram(mm["small_b"]["addr"],
                   np.array([1e-20, 1e-20, 1e-20, 1e-20,
                             1e-20, 1e-20, 1e-20, 1e-20], dtype=np.float32))

    # scalar_val: [100.0]  (broadcast for VADD scalar)
    tpu.write_bram(mm["scalar_val"]["addr"],
                   np.array([100.0], dtype=np.float32))

    # reg_d0..reg_d7: simple patterns for all-registers test
    for i in range(8):
        name = f"reg_d{i}"
        data = np.full(8, float(i + 1), dtype=np.float32)  # d0=1,d1=2,...,d7=8
        tpu.write_bram(mm[name]["addr"], data)


def run_tests(tpu, mm):
    """Read results and verify all 18 edge-case tests."""
    print("\n" + "=" * 70)
    print("SIMD VPU Edge Case Tests (18 tests)")
    print("=" * 70)

    all_pass = True
    n_pass = 0
    n_total = 18

    def check(test_num, name, out_key, expected, rtol=1e-5, atol=1e-7):
        nonlocal all_pass, n_pass
        result = tpu.read_bram(mm[out_key]["addr"], 8)
        ok = np.allclose(result, expected, rtol=rtol, atol=atol)
        status = "PASS" if ok else "FAIL"
        print(f"\n[Test {test_num:2d}] {name}")
        print(f"  Expected: {expected}")
        print(f"  Got:      {result}")
        print(f"  {status}")
        if ok:
            n_pass += 1
        else:
            all_pass = False
            # Print element-wise diff
            diff = np.abs(result - expected)
            print(f"  Max diff: {diff.max():.6e}")

    # Recompute expected values from the same inputs written above
    zeros = np.zeros(8, dtype=np.float32)
    ones = np.ones(8, dtype=np.float32)
    neg_ones = np.full(8, -1.0, dtype=np.float32)
    input_a = np.arange(1, 9, dtype=np.float32)
    neg_a = -input_a
    input_b = np.arange(0.5, 4.5, 0.5, dtype=np.float32)
    all_neg = np.array([-10, -20, -30, -40, -50, -60, -70, -80], dtype=np.float32)
    all_pos = np.array([10, 20, 30, 40, 50, 60, 70, 80], dtype=np.float32)
    large_a = np.array([1e30, 2e30, 3e30, 4e30, 5e30, 6e30, 7e30, 8e30], dtype=np.float32)
    large_b = np.array([1e30, 1e30, 1e30, 1e30, 1e30, 1e30, 1e30, 1e30], dtype=np.float32)
    small_a = np.array([1e-20, 2e-20, 3e-20, 4e-20, 5e-20, 6e-20, 7e-20, 8e-20], dtype=np.float32)
    small_b = np.array([1e-20, 1e-20, 1e-20, 1e-20, 1e-20, 1e-20, 1e-20, 1e-20], dtype=np.float32)

    # Test 1: add zeros => 0+0=0
    check(1, "VADD zeros + zeros = zeros",
          "out_add_zeros", zeros + zeros)

    # Test 2: mul zeros => 0*0=0
    check(2, "VMUL zeros * zeros = zeros",
          "out_mul_zeros", zeros * zeros)

    # Test 3: add negatives => neg+neg = 2*neg
    check(3, "VADD negatives + negatives",
          "out_add_neg", all_neg + all_neg)

    # Test 4: cancellation => a + (-a) = 0
    check(4, "VADD cancellation: A + (-A) = 0",
          "out_cancel", input_a + neg_a, atol=1e-6)

    # Test 5: mul identity => a * 1 = a
    check(5, "VMUL identity: A * 1.0 = A",
          "out_mul_identity", input_a * ones)

    # Test 6: add identity => a + 0 = a
    check(6, "VADD identity: A + 0.0 = A",
          "out_add_identity", input_a + zeros)

    # Test 7: self_add => V0 = V0 + V0 = 2*A
    check(7, "VADD self: V0 = V0 + V0 (= 2*A)",
          "out_self_add", input_a + input_a)

    # Test 8: sub basic => A - B
    check(8, "VSUB basic: A - B",
          "out_sub", input_a - input_b)

    # Test 9: sub self => V0 - V0 = 0
    check(9, "VSUB self: V0 - V0 = 0",
          "out_sub_self", zeros, atol=1e-6)

    # Test 10: relu positive => identity
    check(10, "VRELU all-positive (identity)",
          "out_relu_pos", np.maximum(all_pos, 0))

    # Test 11: relu negative => all zeros
    check(11, "VRELU all-negative (all zeros)",
          "out_relu_neg", np.maximum(all_neg, 0))

    # Test 12: relu zeros => zeros
    check(12, "VRELU zeros (remain zero)",
          "out_relu_zero", np.maximum(zeros, 0))

    # Test 13: chain => (A+B)*A
    check(13, "Chain: (A+B)*A",
          "out_chain", (input_a + input_b) * input_a)

    # Test 14: all regs => D0+D1+D2+...+D7, where Di = fill(i+1)
    # So each element = 1+2+3+4+5+6+7+8 = 36
    expected_all_regs = np.full(8, 36.0, dtype=np.float32)
    check(14, "All 8 regs: V0+V1+...+V7 (= 36.0 each)",
          "out_all_regs", expected_all_regs)

    # Test 15: large values => large_a + large_b
    check(15, "VADD large values (near overflow)",
          "out_large", large_a + large_b, rtol=1e-4)

    # Test 16: small values => small_a * small_b (may underflow to 0)
    expected_small = small_a * small_b
    check(16, "VMUL small values (near underflow)",
          "out_small", expected_small, atol=1e-35)

    # Test 17: scalar add broadcast => A[i] + 100.0
    check(17, "VADD scalar broadcast: A[i] + 100.0",
          "out_scalar_add", input_a + 100.0)

    # Test 18: mul neg one => A * (-1) = -A
    check(18, "VMUL by -1.0 (negate)",
          "out_mul_negone", input_a * neg_ones)

    # Summary
    print("\n" + "=" * 70)
    print(f"Results: {n_pass}/{n_total} passed")
    if all_pass:
        print("ALL EDGE CASE TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 70)

    return all_pass


def main():
    parser = argparse.ArgumentParser(
        description="SIMD VPU edge case test for Mini-TPU"
    )
    parser.add_argument("bitstream", help="Path to bitstream file (.bit)")
    parser.add_argument("--instructions", "-i", default="simd_edge_cases.npy",
                        help="Compiled program file (.npy or .hex)")
    parser.add_argument("--metadata", "-m", default="simd_edge_cases_meta.json",
                        help="Memory map metadata file (.json)")
    parser.add_argument("--tpu-ip", default="tpu_0",
                        help="TPU IP name in overlay")
    parser.add_argument("--dma-ip", default="axi_dma_0",
                        help="DMA IP name in overlay")
    args = parser.parse_args()

    instructions = load_program(args.instructions)
    with open(args.metadata) as f:
        memory_map = json.load(f)

    print(f"\nLoading bitstream: {args.bitstream}")
    print(f"Program: {args.instructions} ({len(instructions)} instructions)")
    print(f"Memory map: {len(memory_map)} allocations")

    tpu = TpuDriver(args.bitstream, tpu_name=args.tpu_ip, dma_name=args.dma_ip)

    print("\nLoading program...")
    tpu.write_instructions(instructions)

    print("Writing test inputs...")
    write_test_inputs(tpu, memory_map)

    print("Executing program...")
    start_time = time.time()
    tpu.compute()
    elapsed = time.time() - start_time
    print(f"Execution time: {elapsed*1000:.2f} ms")

    success = run_tests(tpu, memory_map)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
