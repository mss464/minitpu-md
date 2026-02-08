"""
Debug test for VPU operations.
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

    print("\n=== VPU Debug Test ===\n")

    # Test 1: Simple scalar add
    print("Test 1: Simple scalar add (1.5 + 0.5 = 2.0)")
    a_val = np.array([1.5], dtype=np.float32)
    b_val = np.array([0.5], dtype=np.float32)

    # Addresses
    a_addr = 0
    b_addr = 1
    out_addr = 2

    # Write data
    tpu.write_bram(a_addr, a_val)
    tpu.write_bram(b_addr, b_val)

    # Verify write
    read_a = tpu.read_bram(a_addr, 1)
    read_b = tpu.read_bram(b_addr, 1)
    print(f"  Written: a={a_val[0]}, b={b_val[0]}")
    print(f"  Readback: a={read_a[0]}, b={read_b[0]}")

    # Generate instruction: add a, b, out
    instr = encode_vpu(a_addr, b_addr, out_addr, 0)
    halt = 3 << 62
    print(f"  Instruction: {instr:016X}")

    # Execute
    tpu.write_instructions(np.array([instr, halt], dtype=np.uint64))
    tpu.compute()

    # Read result
    result = tpu.read_bram(out_addr, 1)
    expected = a_val[0] + b_val[0]
    print(f"  Expected: {expected}")
    print(f"  Actual: {result[0]}")
    print(f"  Match: {np.isclose(expected, result[0])}")

    # Test 2: Use different addresses
    print("\nTest 2: Different addresses (10.0 + 5.0 = 15.0)")
    a_addr2 = 100
    b_addr2 = 101
    out_addr2 = 102

    a_val2 = np.array([10.0], dtype=np.float32)
    b_val2 = np.array([5.0], dtype=np.float32)

    tpu.write_bram(a_addr2, a_val2)
    tpu.write_bram(b_addr2, b_val2)

    instr2 = encode_vpu(a_addr2, b_addr2, out_addr2, 0)
    print(f"  Instruction: {instr2:016X}")

    tpu.write_instructions(np.array([instr2, halt], dtype=np.uint64))
    tpu.compute()

    result2 = tpu.read_bram(out_addr2, 1)
    expected2 = a_val2[0] + b_val2[0]
    print(f"  Expected: {expected2}")
    print(f"  Actual: {result2[0]}")
    print(f"  Match: {np.isclose(expected2, result2[0])}")

    # Test 3: Multiple adds in sequence
    print("\nTest 3: Multiple sequential adds")
    a_vals = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    b_vals = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)

    base_a = 200
    base_b = 204
    base_out = 208

    for i in range(4):
        tpu.write_bram(base_a + i, a_vals[i:i+1])
        tpu.write_bram(base_b + i, b_vals[i:i+1])

    instructions = []
    for i in range(4):
        instructions.append(encode_vpu(base_a + i, base_b + i, base_out + i, 0))
    instructions.append(halt)

    tpu.write_instructions(np.array(instructions, dtype=np.uint64))
    tpu.compute()

    results = tpu.read_bram(base_out, 4)
    expected_vals = a_vals + b_vals

    print(f"  Expected: {expected_vals}")
    print(f"  Actual: {results}")
    print(f"  All match: {np.allclose(expected_vals, results)}")

    # Test 4: Compare with matmul (which works)
    print("\nTest 4: Matmul comparison (known working)")
    W = np.array([[1.0, 0.0, 0.0, 0.0],
                  [0.0, 1.0, 0.0, 0.0],
                  [0.0, 0.0, 1.0, 0.0],
                  [0.0, 0.0, 0.0, 1.0]], dtype=np.float32)  # identity
    X = np.array([[1.0, 2.0, 3.0, 4.0],
                  [5.0, 6.0, 7.0, 8.0],
                  [9.0, 10.0, 11.0, 12.0],
                  [13.0, 14.0, 15.0, 16.0]], dtype=np.float32)

    W_addr = 300
    X_addr = 316
    Z_addr = 332

    tpu.write_bram(W_addr, W.flatten())
    tpu.write_bram(X_addr, X.flatten())

    matmul_instr = (1 << 62) | (W_addr << 49) | (X_addr << 36) | (Z_addr << 23) | 16
    tpu.write_instructions(np.array([matmul_instr, halt], dtype=np.uint64))
    tpu.compute()

    Z_result = tpu.read_bram(Z_addr, 16).reshape(4, 4)
    Z_expected = X @ W.T
    print(f"  Expected (X @ I^T = X):\n{Z_expected}")
    print(f"  Actual:\n{Z_result}")
    print(f"  Match: {np.allclose(Z_expected, Z_result)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
