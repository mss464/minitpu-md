#!/usr/bin/env python3
"""
Comprehensive FPGA test for Mini-TPU.

Compile program first:
    python tests/ultra96-v2/programs/comprehensive.py

Run on board:
    make -C tests board-test \
        BIT=tpu/ultra96-v2/bitstream/minitpu.bit \
        HWH=tpu/ultra96-v2/bitstream/minitpu.hwh \
        PROGRAM=tests/ultra96-v2/test_comprehensive.py
"""

import argparse
import sys
import json
from pathlib import Path
import numpy as np

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


# ============================================================================
# Utilities
# ============================================================================

def to_tile_major(mat, tile_size=4):
    """Convert row-major matrix to tile-major layout."""
    rows, cols = mat.shape
    result = []
    for ti in range(rows // tile_size):
        for tj in range(cols // tile_size):
            tile = mat[ti*tile_size:(ti+1)*tile_size, tj*tile_size:(tj+1)*tile_size]
            result.extend(tile.flatten().tolist())
    return np.array(result, dtype=np.float32)


def from_tile_major(data, rows, cols, tile_size=4):
    """Convert tile-major layout back to row-major matrix."""
    mat = np.zeros((rows, cols), dtype=np.float32)
    idx = 0
    for ti in range(rows // tile_size):
        for tj in range(cols // tile_size):
            tile = data[idx:idx + tile_size*tile_size].reshape(tile_size, tile_size)
            mat[ti*tile_size:(ti+1)*tile_size, tj*tile_size:(tj+1)*tile_size] = tile
            idx += tile_size * tile_size
    return mat


# ============================================================================
# Test functions
# ============================================================================

def test_data_integrity(tpu):
    """Test BRAM read/write integrity."""
    print("\n[Test 1] Data Integrity")
    all_pass = True

    # Sequential values
    seq_data = np.arange(64, dtype=np.float32)
    tpu.write_bram(0, seq_data)
    readback = tpu.read_bram(0, 64)
    if np.allclose(seq_data, readback):
        print("  Sequential values: PASS")
    else:
        print(f"  Sequential values: FAIL (max diff {np.max(np.abs(seq_data - readback))})")
        all_pass = False

    # Random values
    np.random.seed(789)
    rand_data = np.random.randn(128).astype(np.float32)
    tpu.write_bram(100, rand_data)
    readback = tpu.read_bram(100, 128)
    if np.allclose(rand_data, readback):
        print("  Random values: PASS")
    else:
        print(f"  Random values: FAIL (max diff {np.max(np.abs(rand_data - readback))})")
        all_pass = False

    return all_pass


def test_edge_cases_data(tpu):
    """Test BRAM with edge case values."""
    print("\n[Test 2] Edge Case Data Integrity")
    all_pass = True

    # All zeros
    zeros = np.zeros(64, dtype=np.float32)
    tpu.write_bram(0, zeros)
    readback = tpu.read_bram(0, 64)
    if np.allclose(zeros, readback):
        print("  All zeros: PASS")
    else:
        print(f"  All zeros: FAIL (max diff {np.max(np.abs(zeros - readback))})")
        all_pass = False

    # All negative
    negatives = np.full(64, -5.5, dtype=np.float32)
    tpu.write_bram(100, negatives)
    readback = tpu.read_bram(100, 64)
    if np.allclose(negatives, readback):
        print("  All negative: PASS")
    else:
        print(f"  All negative: FAIL (max diff {np.max(np.abs(negatives - readback))})")
        all_pass = False

    # Very large values (but not infinity)
    large = np.full(32, 1e20, dtype=np.float32)
    tpu.write_bram(200, large)
    readback = tpu.read_bram(200, 32)
    if np.allclose(large, readback, rtol=1e-5):
        print("  Very large values: PASS")
    else:
        print(f"  Very large values: FAIL (max diff {np.max(np.abs(large - readback))})")
        all_pass = False

    # Very small values (near zero but not denormal)
    small = np.full(32, 1e-20, dtype=np.float32)
    tpu.write_bram(300, small)
    readback = tpu.read_bram(300, 32)
    if np.allclose(small, readback, rtol=1e-5):
        print("  Very small values: PASS")
    else:
        print(f"  Very small values: FAIL (max diff {np.max(np.abs(small - readback))})")
        all_pass = False

    # Mixed sign pattern
    alternating = np.array([(-1)**i * i for i in range(64)], dtype=np.float32)
    tpu.write_bram(400, alternating)
    readback = tpu.read_bram(400, 64)
    if np.allclose(alternating, readback):
        print("  Alternating signs: PASS")
    else:
        print(f"  Alternating signs: FAIL (max diff {np.max(np.abs(alternating - readback))})")
        all_pass = False

    # Powers of 2 (exactly representable in FP32)
    powers = np.array([2.0**i for i in range(-10, 22)], dtype=np.float32)
    tpu.write_bram(500, powers)
    readback = tpu.read_bram(500, len(powers))
    if np.allclose(powers, readback):
        print("  Powers of 2: PASS")
    else:
        print(f"  Powers of 2: FAIL (max diff {np.max(np.abs(powers - readback))})")
        all_pass = False

    # Boundary addresses (test first and last safe addresses)
    # BRAM is 8192 elements (0-8191), use conservative upper bound
    boundary_data = np.array([123.456, -789.012], dtype=np.float32)
    tpu.write_bram(0, boundary_data[:1])
    tpu.write_bram(8000, boundary_data[1:])  # Safe upper address
    readback_start = tpu.read_bram(0, 1)
    readback_end = tpu.read_bram(8000, 1)
    if np.allclose(boundary_data[0], readback_start) and np.allclose(boundary_data[1], readback_end):
        print("  Memory boundaries: PASS")
    else:
        print(f"  Memory boundaries: FAIL")
        all_pass = False

    return all_pass


def test_compute(tpu, instructions, mem):
    """Test compute operations with pre-compiled program."""
    print("\n[Test 2-4] Compute Operations")
    np.random.seed(42)

    # Test data
    a = np.array([1.5, -2.0, 3.0, -0.5], dtype=np.float32)
    b = np.array([0.5, 1.0, -1.0, 2.0], dtype=np.float32)
    zero = np.array([0.0], dtype=np.float32)
    W4 = np.random.randn(4, 4).astype(np.float32)
    X4 = np.random.randn(4, 4).astype(np.float32)
    X8 = np.random.randn(8, 8).astype(np.float32)
    W8 = np.random.randn(8, 8).astype(np.float32)

    # Load data to BRAM
    tpu.write_bram(mem["a"]["addr"], a)
    tpu.write_bram(mem["b"]["addr"], b)
    tpu.write_bram(mem["zero"]["addr"], zero)
    tpu.write_bram(mem["W4"]["addr"], W4.flatten())
    tpu.write_bram(mem["X4"]["addr"], X4.flatten())
    tpu.write_bram(mem["W8"]["addr"], to_tile_major(W8, 4))
    tpu.write_bram(mem["X8"]["addr"], to_tile_major(X8, 4))
    tpu.write_bram(mem["Z8"]["addr"], np.zeros(64, dtype=np.float32))

    # Execute
    print(f"  Instructions: {len(instructions)}")
    tpu.write_instructions(instructions)
    tpu.compute()

    # Verify results
    results = {}

    # VPU
    results['VPU Add'] = np.allclose(a + b, tpu.read_bram(mem["add_out"]["addr"], 4))
    results['VPU Sub'] = np.allclose(a - b, tpu.read_bram(mem["sub_out"]["addr"], 4))
    results['VPU Mul'] = np.allclose(a * b, tpu.read_bram(mem["mul_out"]["addr"], 4))
    results['VPU ReLU'] = np.allclose(np.maximum(a, 0), tpu.read_bram(mem["relu_out"]["addr"], 4))

    # 4x4 matmul
    actual_Z4 = tpu.read_bram(mem["Z4"]["addr"], 16).reshape(4, 4)
    results['4x4 Matmul'] = np.allclose(X4 @ W4.T, actual_Z4, atol=1e-3)

    # 8x8 tiled matmul
    actual_Z8 = from_tile_major(tpu.read_bram(mem["Z8"]["addr"], 64), 8, 8, 4)
    results['8x8 Tiled Matmul'] = np.allclose(X8 @ W8.T, actual_Z8, atol=1e-2)

    all_pass = True
    for name, passed in results.items():
        print(f"  {name}: {'PASS' if passed else 'FAIL'}")
        if not passed:
            all_pass = False

    return all_pass


def test_edge_cases_numerical(tpu):
    """Test numerical edge cases and precision (safe values only)."""
    print("\n[Test 3] Numerical Edge Cases")
    all_pass = True

    # Test near-zero values (but avoid subnormals)
    near_zero = np.array([1e-10, -1e-10, 1e-20, -1e-20], dtype=np.float32)
    tpu.write_bram(1000, near_zero)
    readback = tpu.read_bram(1000, 4)
    if np.allclose(near_zero, readback, rtol=1e-5):
        print("  Near-zero values: PASS")
    else:
        print(f"  Near-zero values: FAIL")
        all_pass = False

    # Test decimal precision (common floating point issues)
    decimal_test = np.array([0.1, 0.2, 0.3, 0.1+0.2], dtype=np.float32)
    tpu.write_bram(1100, decimal_test)
    readback = tpu.read_bram(1100, 4)
    if np.allclose(decimal_test, readback, rtol=1e-6):
        print("  Decimal precision: PASS")
    else:
        print(f"  Decimal precision: FAIL")
        all_pass = False

    # Test safe large values (avoid overflow)
    large_safe = np.array([1e20, -1e20, 1e10, -1e10], dtype=np.float32)
    tpu.write_bram(1200, large_safe)
    readback = tpu.read_bram(1200, 4)
    if np.allclose(large_safe, readback, rtol=1e-5):
        print("  Large safe values: PASS")
    else:
        print(f"  Large safe values: FAIL")
        all_pass = False

    # Test fraction precision
    fractions = np.array([1.0/3.0, 2.0/3.0, 1.0/7.0, 22.0/7.0], dtype=np.float32)
    tpu.write_bram(1300, fractions)
    readback = tpu.read_bram(1300, 4)
    if np.allclose(fractions, readback, rtol=1e-6):
        print("  Fraction precision: PASS")
    else:
        print(f"  Fraction precision: FAIL")
        all_pass = False

    return all_pass


def test_special_matrices(tpu):
    """Test special matrix cases (requires compute capabilities)."""
    print("\n[Test 4] Special Matrix Cases")
    all_pass = True

    # Note: This test just verifies BRAM handling of special matrices
    # Actual compute tests require pre-compiled programs

    # Zero matrix
    zero_4x4 = np.zeros((4, 4), dtype=np.float32)
    tpu.write_bram(2000, zero_4x4.flatten())
    readback = tpu.read_bram(2000, 16).reshape(4, 4)
    if np.allclose(zero_4x4, readback):
        print("  Zero matrix storage: PASS")
    else:
        print("  Zero matrix storage: FAIL")
        all_pass = False

    # Identity matrix
    identity = np.eye(4, dtype=np.float32)
    tpu.write_bram(2100, identity.flatten())
    readback = tpu.read_bram(2100, 16).reshape(4, 4)
    if np.allclose(identity, readback):
        print("  Identity matrix storage: PASS")
    else:
        print("  Identity matrix storage: FAIL")
        all_pass = False

    # Sparse matrix (mostly zeros)
    sparse = np.zeros((4, 4), dtype=np.float32)
    sparse[0, 0] = 1.0
    sparse[2, 3] = -5.0
    tpu.write_bram(2200, sparse.flatten())
    readback = tpu.read_bram(2200, 16).reshape(4, 4)
    if np.allclose(sparse, readback):
        print("  Sparse matrix storage: PASS")
    else:
        print("  Sparse matrix storage: FAIL")
        all_pass = False

    # Diagonal matrix
    diag = np.diag([1.0, 2.0, 3.0, 4.0]).astype(np.float32)
    tpu.write_bram(2300, diag.flatten())
    readback = tpu.read_bram(2300, 16).reshape(4, 4)
    if np.allclose(diag, readback):
        print("  Diagonal matrix storage: PASS")
    else:
        print("  Diagonal matrix storage: FAIL")
        all_pass = False

    # All negative matrix
    neg_matrix = -np.ones((4, 4), dtype=np.float32)
    tpu.write_bram(2400, neg_matrix.flatten())
    readback = tpu.read_bram(2400, 16).reshape(4, 4)
    if np.allclose(neg_matrix, readback):
        print("  All-negative matrix storage: PASS")
    else:
        print("  All-negative matrix storage: FAIL")
        all_pass = False

    # Large magnitude matrix
    large_matrix = np.full((4, 4), 1e10, dtype=np.float32)
    tpu.write_bram(2500, large_matrix.flatten())
    readback = tpu.read_bram(2500, 16).reshape(4, 4)
    if np.allclose(large_matrix, readback, rtol=1e-5):
        print("  Large magnitude matrix: PASS")
    else:
        print("  Large magnitude matrix: FAIL")
        all_pass = False

    return all_pass


def test_memory_patterns(tpu):
    """Test various memory access patterns."""
    print("\n[Test 5] Memory Access Patterns")
    all_pass = True

    # Scattered writes and reads (BRAM size is 8192 elements, use safe addresses)
    for offset in [0, 100, 500, 1000, 2000, 4000, 6000]:
        data = np.array([float(offset + i) for i in range(10)], dtype=np.float32)
        tpu.write_bram(offset, data)

    # Verify scattered reads
    all_correct = True
    for offset in [0, 100, 500, 1000, 2000, 4000, 6000]:
        expected = np.array([float(offset + i) for i in range(10)], dtype=np.float32)
        readback = tpu.read_bram(offset, 10)
        if not np.allclose(expected, readback):
            all_correct = False
            break

    if all_correct:
        print("  Scattered write/read: PASS")
    else:
        print("  Scattered write/read: FAIL")
        all_pass = False

    # Overlapping writes (last write should win)
    overlap_data_1 = np.ones(20, dtype=np.float32)
    overlap_data_2 = np.full(20, 2.0, dtype=np.float32)
    tpu.write_bram(3000, overlap_data_1)
    tpu.write_bram(3005, overlap_data_2)  # Overlaps last 15 elements

    # Check that overlap region has value 2.0
    readback = tpu.read_bram(3005, 20)
    if np.allclose(readback, overlap_data_2):
        print("  Overlapping writes: PASS")
    else:
        print("  Overlapping writes: FAIL")
        all_pass = False

    # Sequential burst writes
    burst_size = 256
    burst_data = np.arange(burst_size, dtype=np.float32)
    tpu.write_bram(5000, burst_data)
    readback = tpu.read_bram(5000, burst_size)
    if np.allclose(burst_data, readback):
        print("  Large burst (256 elements): PASS")
    else:
        print(f"  Large burst: FAIL (max diff {np.max(np.abs(burst_data - readback))})")
        all_pass = False

    # Single element writes at various offsets (stay within BRAM bounds)
    single_writes = {7000: 42.0, 7100: -99.5, 7200: 0.0, 7300: 1e-5}
    for addr, val in single_writes.items():
        tpu.write_bram(addr, np.array([val], dtype=np.float32))

    all_correct = True
    for addr, expected_val in single_writes.items():
        readback = tpu.read_bram(addr, 1)[0]
        if not np.allclose(readback, expected_val):
            all_correct = False
            break

    if all_correct:
        print("  Single element writes: PASS")
    else:
        print("  Single element writes: FAIL")
        all_pass = False

    return all_pass


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Comprehensive FPGA Test")
    parser.add_argument("bitstream", help="Path to bitstream (.bit)")
    parser.add_argument("program", nargs="?", default=None, help="Compiled program (.npy/.hex)")
    parser.add_argument("--trace", default=None, help="Trace output file (unused)")
    parser.add_argument("--tpu-ip", default=None, help="TPU IP block name (auto-detect if not provided)")
    parser.add_argument("--dma-ip", default=None, help="DMA IP block name (auto-detect if not provided)")
    args = parser.parse_args()

    # Find program files
    test_dir = Path(__file__).parent
    if args.program:
        prog_path = Path(args.program)
    else:
        prog_path = test_dir / "comprehensive.npy"

    meta_path = test_dir / "comprehensive_meta.json"

    if not prog_path.exists():
        print(f"ERROR: Program not found: {prog_path}")
        print("Compile first: python tests/ultra96-v2/programs/comprehensive.py")
        return 1

    # Load program and metadata
    instructions = load_program(prog_path)
    with open(meta_path) as f:
        mem = json.load(f)

    # Run tests
    print(f"Programming FPGA: {args.bitstream}")
    tpu = TpuDriver(args.bitstream, tpu_name=args.tpu_ip, dma_name=args.dma_ip)

    print("\n" + "=" * 60)
    print("COMPREHENSIVE FPGA TEST WITH EDGE CASES")
    print("=" * 60)

    all_pass = True

    # Core functionality tests
    if not test_data_integrity(tpu):
        all_pass = False

    # Edge case tests (BRAM only, no compute)
    if not test_edge_cases_data(tpu):
        all_pass = False
    if not test_edge_cases_numerical(tpu):
        all_pass = False
    if not test_special_matrices(tpu):
        all_pass = False
    if not test_memory_patterns(tpu):
        all_pass = False

    # Compute tests (requires pre-compiled program)
    if not test_compute(tpu, instructions, mem):
        all_pass = False

    print("\n" + "=" * 60)
    print(f"OVERALL: {'PASS' if all_pass else 'FAIL'}")
    print("=" * 60)

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
