"""
Test tiled matrix multiplication with increasing sizes.

Demonstrates:
1. Small matrices (8x8) work fine
2. Medium matrices (12x12) work
3. Large matrices (16x16+) exceed instruction limit
"""

import sys
import os
import tempfile
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from compiler.tpu_txt import (
    tiled_matmul, load, store, get_instruction_log, clear_instruction_log
)
from compiler.runtime.allocator import MemoryAllocator
from compiler.assembler import assemble_file, CompilationError, IMEM_MAX_SIZE


def generate_tiled_matmul_trace(M, N, K, tile_size=4):
    """Generate instruction trace for MxK @ KxN^T -> MxN matmul."""
    clear_instruction_log()
    mem = MemoryAllocator()

    # Allocate matrices (in tile-major order)
    X_size = M * K
    W_size = N * K
    Z_size = M * N

    X_addr = mem.alloc('X', X_size)
    W_addr = mem.alloc('W', W_size)
    Z_addr = mem.alloc('Z', Z_size)

    # Generate random test data
    np.random.seed(42)
    X_data = np.random.randn(M, K).astype(np.float32)
    W_data = np.random.randn(N, K).astype(np.float32)

    # Convert to tile-major format
    def to_tile_major(mat, tile_size):
        rows, cols = mat.shape
        result = []
        for ti in range(rows // tile_size):
            for tj in range(cols // tile_size):
                tile = mat[ti*tile_size:(ti+1)*tile_size,
                          tj*tile_size:(tj+1)*tile_size]
                result.extend(tile.flatten().tolist())
        return result

    X_tiled = to_tile_major(X_data, tile_size)
    W_tiled = to_tile_major(W_data, tile_size)

    # Load inputs
    load(X_addr, np.array(X_tiled, dtype=np.float32))
    load(W_addr, np.array(W_tiled, dtype=np.float32))

    # Perform tiled matmul
    tiled_matmul(W_addr, X_addr, Z_addr, M, N, K, tile_size=tile_size, allocator=mem)

    # Store output
    store(Z_addr, Z_size, f'Z_{M}x{N}')

    # Compute expected result for verification
    expected = (X_data @ W_data.T).astype(np.float32)

    return get_instruction_log(), expected, mem


def count_instructions(trace):
    """Count actual compute instructions (excluding load/store)."""
    return sum(1 for line in trace
               if not line.startswith('load') and not line.startswith('store'))


def test_matmul_size(M, N, K, tile_size=4, verbose=True):
    """Test a specific matrix size, return (success, num_instructions, error_msg)."""
    if verbose:
        print(f"\n{'='*60}")
        print(f"Testing {M}x{K} @ {K}x{N}^T -> {M}x{N} (tile_size={tile_size})")
        print(f"{'='*60}")

    try:
        trace, expected, mem = generate_tiled_matmul_trace(M, N, K, tile_size)
        num_instrs = count_instructions(trace)

        if verbose:
            print(f"Generated {num_instrs} compute instructions (+1 HALT = {num_instrs + 1} total)")
            print(f"Memory used: {mem.used()} / 8192 words")

        # Try to assemble
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for line in trace:
                f.write(line + '\n')
            trace_path = f.name

        output_path = trace_path.replace('.txt', '_out.txt')

        try:
            assemble_file(trace_path, output_path, matmul_len=tile_size*tile_size)

            # Count actual assembled instructions
            with open(output_path) as f:
                assembled_count = sum(1 for line in f if line.strip())

            if verbose:
                print(f"Assembly successful: {assembled_count} instructions")
                print(f"IMEM usage: {assembled_count}/{IMEM_MAX_SIZE} ({100*assembled_count/IMEM_MAX_SIZE:.1f}%)")

            return True, assembled_count, None

        except CompilationError as e:
            if verbose:
                print(f"Compilation FAILED: {e}")
            return False, num_instrs + 1, str(e)

        finally:
            os.unlink(trace_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
            # Clean up generated host script
            host_path = os.path.dirname(trace_path) + '/test_generated.py'
            if os.path.exists(host_path):
                os.unlink(host_path)

    except Exception as e:
        if verbose:
            print(f"Error: {e}")
        return False, 0, str(e)


def main():
    print("=" * 60)
    print("Tiled MatMul Instruction Count Test")
    print(f"IMEM Limit: {IMEM_MAX_SIZE} instructions")
    print("=" * 60)

    # Test increasingly large square matrices
    test_sizes = [
        (4, 4, 4),      # 1 tile: 1 matmul
        (8, 8, 8),      # 2x2x2 tiles: 8 matmuls + 64 adds
        (12, 12, 12),   # 3x3x3 tiles: 27 matmuls + 288 adds
        (16, 16, 16),   # 4x4x4 tiles: 64 matmuls + 768 adds (should fail)
        (20, 20, 20),   # 5x5x5 tiles: definitely fails
    ]

    results = []

    for M, N, K in test_sizes:
        success, num_instrs, error = test_matmul_size(M, N, K)
        results.append((M, N, K, success, num_instrs, error))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Size':<15} {'Instructions':<15} {'Status':<10} {'IMEM %':<10}")
    print("-" * 60)

    for M, N, K, success, num_instrs, error in results:
        size_str = f"{M}x{N}x{K}"
        status = "PASS" if success else "FAIL"
        pct = f"{100*num_instrs/IMEM_MAX_SIZE:.1f}%" if num_instrs > 0 else "N/A"
        print(f"{size_str:<15} {num_instrs:<15} {status:<10} {pct:<10}")

    print("-" * 60)
    print(f"IMEM Limit: {IMEM_MAX_SIZE} instructions")

    # Find the maximum working size
    max_working = None
    for M, N, K, success, num_instrs, error in results:
        if success:
            max_working = (M, N, K)

    if max_working:
        print(f"Maximum working size: {max_working[0]}x{max_working[1]}x{max_working[2]}")

    # Return exit code based on expected behavior
    # We expect sizes that exceed IMEM_MAX_SIZE to fail
    for M, N, K, success, num_instrs, error in results:
        if num_instrs > IMEM_MAX_SIZE:
            if success:
                print(f"UNEXPECTED: {M}x{N}x{K} ({num_instrs} instrs) should have failed but passed")
                return 1
        else:
            if not success:
                print(f"UNEXPECTED: {M}x{N}x{K} should have passed but failed: {error}")
                return 1

    print("\nAll tests behaved as expected!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
