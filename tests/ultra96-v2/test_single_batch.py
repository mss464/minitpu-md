"""
Test all operations in a single instruction batch (like MLP test does).
"""
import argparse
import sys
import numpy as np

try:
    from compiler.hal.pynq_host import TpuDriver
except ImportError as e:
    print(f"Warning: Could not import TpuDriver: {e}")
    TpuDriver = None


def encode_vpu(addr_a, addr_b, addr_out, opcode, addr_const=0):
    """Encode VPU instruction."""
    return ((0 << 62) | (addr_a << 49) | (addr_b << 36) |
            (addr_out << 23) | (addr_const << 10) | opcode)


def encode_matmul(addr_w, addr_x, addr_z, length=16):
    """Encode matmul instruction."""
    return (1 << 62) | (addr_w << 49) | (addr_x << 36) | (addr_z << 23) | length


def to_tile_major(mat, tile_size=4):
    """Convert row-major to tile-major."""
    rows, cols = mat.shape
    result = []
    for ti in range(rows // tile_size):
        for tj in range(cols // tile_size):
            tile = mat[ti*tile_size:(ti+1)*tile_size, tj*tile_size:(tj+1)*tile_size]
            result.extend(tile.flatten().tolist())
    return np.array(result, dtype=np.float32)


def from_tile_major(data, rows, cols, tile_size=4):
    """Convert tile-major to row-major."""
    mat = np.zeros((rows, cols), dtype=np.float32)
    idx = 0
    for ti in range(rows // tile_size):
        for tj in range(cols // tile_size):
            tile = data[idx:idx + tile_size*tile_size].reshape(tile_size, tile_size)
            mat[ti*tile_size:(ti+1)*tile_size, tj*tile_size:(tj+1)*tile_size] = tile
            idx += tile_size * tile_size
    return mat


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bitstream", type=str)
    parser.add_argument("instr_file", type=str, nargs="?", default=None)
    parser.add_argument("--trace", type=str, default=None)
    args = parser.parse_args()

    if TpuDriver is None:
        print("ERROR: TpuDriver not available")
        return 1

    print(f"Programming FPGA with {args.bitstream}")
    tpu = TpuDriver(args.bitstream)

    print("\n=== Single Batch Test ===")
    print("All operations in one instruction batch, one compute() call\n")

    np.random.seed(42)

    # Memory layout
    # VPU test: 0-19
    a_addr = 0      # 4 values
    b_addr = 4      # 4 values
    add_out = 8     # 4 values
    sub_out = 12    # 4 values
    mul_out = 16    # 4 values

    # Matmul test: 100-200
    W_addr = 100    # 16 values (4x4)
    X_addr = 116    # 16 values (4x4)
    Z_addr = 132    # 16 values (4x4)

    # Tiled 8x8 matmul test: 200-500
    X8_addr = 200   # 64 values
    W8_addr = 264   # 64 values
    Z8_addr = 328   # 64 values
    temp_addr = 392 # 16 values

    # Generate test data
    a = np.array([1.5, -2.0, 3.0, -0.5], dtype=np.float32)
    b = np.array([0.5, 1.0, -1.0, 2.0], dtype=np.float32)

    W4 = np.random.randn(4, 4).astype(np.float32)
    X4 = np.random.randn(4, 4).astype(np.float32)

    X8 = np.random.randn(8, 8).astype(np.float32)
    W8 = np.random.randn(8, 8).astype(np.float32)

    # Load all data to BRAM
    print("Loading data to BRAM...")
    tpu.write_bram(a_addr, a)
    tpu.write_bram(b_addr, b)
    tpu.write_bram(W_addr, W4.flatten())
    tpu.write_bram(X_addr, X4.flatten())
    tpu.write_bram(X8_addr, to_tile_major(X8, 4))
    tpu.write_bram(W8_addr, to_tile_major(W8, 4))
    tpu.write_bram(Z8_addr, np.zeros(64, dtype=np.float32))

    # Generate ALL instructions in one batch
    print("Generating instructions...")
    instructions = []

    # VPU operations (4 each)
    for i in range(4):
        instructions.append(encode_vpu(a_addr + i, b_addr + i, add_out + i, 0))  # add
        instructions.append(encode_vpu(a_addr + i, b_addr + i, sub_out + i, 1))  # sub
        instructions.append(encode_vpu(a_addr + i, b_addr + i, mul_out + i, 3))  # mul

    # 4x4 matmul
    instructions.append(encode_matmul(W_addr, X_addr, Z_addr, 16))

    # 8x8 tiled matmul (2x2x2 tiles)
    t2 = 16
    for i in range(2):
        for j in range(2):
            Z_tile = Z8_addr + (i * 2 + j) * t2
            for k in range(2):
                X_tile = X8_addr + (i * 2 + k) * t2
                W_tile = W8_addr + (j * 2 + k) * t2

                if k == 0:
                    instructions.append(encode_matmul(W_tile, X_tile, Z_tile, t2))
                else:
                    instructions.append(encode_matmul(W_tile, X_tile, temp_addr, t2))
                    for elem in range(t2):
                        instructions.append(encode_vpu(Z_tile + elem, temp_addr + elem, Z_tile + elem, 0))

    # Halt
    instructions.append(3 << 62)

    print(f"Total instructions: {len(instructions)}")

    # Execute
    print("Executing...")
    tpu.write_instructions(np.array(instructions, dtype=np.uint64))
    tpu.compute()

    # Read and verify results
    print("\n=== Results ===\n")

    # VPU results
    actual_add = tpu.read_bram(add_out, 4)
    actual_sub = tpu.read_bram(sub_out, 4)
    actual_mul = tpu.read_bram(mul_out, 4)

    expected_add = a + b
    expected_sub = a - b
    expected_mul = a * b

    print("VPU Add:")
    print(f"  Expected: {expected_add}")
    print(f"  Actual:   {actual_add}")
    print(f"  PASS: {np.allclose(expected_add, actual_add)}")

    print("\nVPU Sub:")
    print(f"  Expected: {expected_sub}")
    print(f"  Actual:   {actual_sub}")
    print(f"  PASS: {np.allclose(expected_sub, actual_sub)}")

    print("\nVPU Mul:")
    print(f"  Expected: {expected_mul}")
    print(f"  Actual:   {actual_mul}")
    print(f"  PASS: {np.allclose(expected_mul, actual_mul)}")

    # 4x4 matmul result
    actual_Z4 = tpu.read_bram(Z_addr, 16).reshape(4, 4)
    expected_Z4 = X4 @ W4.T

    print("\n4x4 Matmul:")
    print(f"  PASS: {np.allclose(expected_Z4, actual_Z4, atol=1e-3)}")
    if not np.allclose(expected_Z4, actual_Z4, atol=1e-3):
        print(f"  Max diff: {np.max(np.abs(expected_Z4 - actual_Z4))}")

    # 8x8 tiled matmul result
    actual_Z8_tiled = tpu.read_bram(Z8_addr, 64)
    actual_Z8 = from_tile_major(actual_Z8_tiled, 8, 8, 4)
    expected_Z8 = X8 @ W8.T

    print("\n8x8 Tiled Matmul:")
    print(f"  PASS: {np.allclose(expected_Z8, actual_Z8, atol=1e-2)}")
    if not np.allclose(expected_Z8, actual_Z8, atol=1e-2):
        diff = np.abs(expected_Z8 - actual_Z8)
        print(f"  Max diff: {np.max(diff)} at {np.unravel_index(np.argmax(diff), diff.shape)}")

    # Summary
    all_pass = (
        np.allclose(expected_add, actual_add) and
        np.allclose(expected_sub, actual_sub) and
        np.allclose(expected_mul, actual_mul) and
        np.allclose(expected_Z4, actual_Z4, atol=1e-3) and
        np.allclose(expected_Z8, actual_Z8, atol=1e-2)
    )

    print("\n" + "=" * 40)
    print(f"OVERALL: {'PASS' if all_pass else 'FAIL'}")
    print("=" * 40)

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
