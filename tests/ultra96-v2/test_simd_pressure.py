#!/usr/bin/env python3
"""
SIMD VPU pressure/performance test harness.

Runs BOTH scalar and SIMD programs on identical data, compares wall-clock
execution time, and verifies correctness of both outputs.

IMPORTANT: Instruction BRAM holds only 256 entries. Programs are sized
to fit within this limit (scalar=225, SIMD=93).

Compile programs first:
    PYTHONPATH=. python3 tests/ultra96-v2/programs/simd_pressure.py

Run on board:
    make -C tests board-simd-pressure \
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

# DMA transfers > 8 elements can be unreliable on the Ultra96-v2 fabric.
# Chunk all BRAM reads/writes into 8-element batches.
DMA_CHUNK = 8


def write_bram_chunked(tpu, addr, values):
    """Write float32 array to BRAM in DMA_CHUNK-element chunks."""
    values = np.asarray(values, dtype=np.float32).ravel()
    for i in range(0, len(values), DMA_CHUNK):
        tpu.write_bram(addr + i, values[i:i + DMA_CHUNK])


def read_bram_chunked(tpu, addr, length):
    """Read float32 array from BRAM in DMA_CHUNK-element chunks."""
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


def write_test_inputs(tpu, mm):
    """Write all input data to BRAM. Same layout for both programs."""
    np.random.seed(42)

    vec_a_32 = np.random.uniform(0, 10, 32).astype(np.float32)
    write_bram_chunked(tpu, mm["vec_a_32"]["addr"], vec_a_32)

    vec_b_32 = np.random.uniform(0, 10, 32).astype(np.float32)
    write_bram_chunked(tpu, mm["vec_b_32"]["addr"], vec_b_32)

    mlp_x = np.random.uniform(-5, 5, 32).astype(np.float32)
    write_bram_chunked(tpu, mm["mlp_x"]["addr"], mlp_x)

    mlp_w = np.random.uniform(-1, 1, 32).astype(np.float32)
    write_bram_chunked(tpu, mm["mlp_w"]["addr"], mlp_w)

    mlp_bias = np.random.uniform(-2, 2, 32).astype(np.float32)
    write_bram_chunked(tpu, mm["mlp_bias"]["addr"], mlp_bias)

    tpu.write_bram(mm["zero"]["addr"], np.array([0.0], dtype=np.float32))

    vec_a_64 = np.random.uniform(0, 10, 64).astype(np.float32)
    write_bram_chunked(tpu, mm["vec_a_64"]["addr"], vec_a_64)

    vec_b_64 = np.random.uniform(0, 10, 64).astype(np.float32)
    write_bram_chunked(tpu, mm["vec_b_64"]["addr"], vec_b_64)

    return {
        "vec_a_32": vec_a_32,
        "vec_b_32": vec_b_32,
        "mlp_x": mlp_x,
        "mlp_w": mlp_w,
        "mlp_bias": mlp_bias,
        "vec_a_64": vec_a_64,
        "vec_b_64": vec_b_64,
    }


def clear_outputs(tpu, mm):
    """Zero out all output regions so stale data doesn't cause false passes."""
    for key in ["add_out_32", "mul_out_32", "mlp_out", "add_out_64"]:
        size = mm[key]["size"]
        write_bram_chunked(tpu, mm[key]["addr"],
                           np.zeros(size, dtype=np.float32))


def data_integrity_check(tpu, mm):
    """Quick round-trip check: write known data, read back, compare."""
    print("\n--- Data Integrity Pre-Check ---")
    all_ok = True

    for name, size in [("vec_a_32", 32), ("vec_a_64", 64)]:
        addr = mm[name]["addr"]
        pattern = np.arange(1, size + 1, dtype=np.float32)
        write_bram_chunked(tpu, addr, pattern)
        readback = read_bram_chunked(tpu, addr, size)
        ok = np.array_equal(pattern, readback)
        status = "OK" if ok else "FAIL"
        print(f"  {name} ({size} elems) write/read: {status}")
        if not ok:
            diff_idx = np.where(pattern != readback)[0]
            print(f"    Mismatches at indices: {diff_idx[:10]}...")
            all_ok = False

    if all_ok:
        print("  Data integrity: PASS")
    else:
        print("  Data integrity: FAIL (DMA issue with large transfers)")
    return all_ok


def verify_outputs(tpu, mm, inputs, label):
    """Read and verify all output buffers. Returns (pass_count, total)."""
    n_pass = 0
    n_total = 4

    def check_one(test_name, out_key, expected):
        nonlocal n_pass
        size = mm[out_key]["size"]
        result = read_bram_chunked(tpu, mm[out_key]["addr"], size)
        ok = np.allclose(result, expected, rtol=1e-5)
        status = "PASS" if ok else "FAIL"
        print(f"  [{label}] {test_name}: {status}")
        if not ok:
            diff = np.abs(result - expected)
            idx = diff.argmax()
            print(f"    Max diff: {diff.max():.6e}, at index {idx}")
            print(f"    Expected[{idx}]={expected[idx]:.6f}, Got[{idx}]={result[idx]:.6f}")
        else:
            n_pass += 1

    check_one("32-elem ADD", "add_out_32",
              inputs["vec_a_32"] + inputs["vec_b_32"])

    check_one("32-elem MUL", "mul_out_32",
              inputs["vec_a_32"] * inputs["vec_b_32"])

    check_one("32-elem MLP", "mlp_out",
              np.maximum(inputs["mlp_x"] * inputs["mlp_w"] + inputs["mlp_bias"], 0))

    check_one("64-elem ADD", "add_out_64",
              inputs["vec_a_64"] + inputs["vec_b_64"])

    return n_pass, n_total


def run_pressure_test(tpu, mm, scalar_prog, simd_prog, n_runs=5):
    """Run both programs multiple times, collect timing data."""
    print("\n" + "=" * 70)
    print("SIMD VPU Pressure / Performance Test")
    print("=" * 70)

    n_scalar_instr = len(scalar_prog)
    n_simd_instr = len(simd_prog)

    print(f"\nProgram sizes:")
    print(f"  Scalar: {n_scalar_instr} instructions")
    print(f"  SIMD:   {n_simd_instr} instructions")
    print(f"  Ratio:  {n_scalar_instr / n_simd_instr:.2f}x fewer with SIMD")

    all_pass = True

    # --- Scalar run ---
    print(f"\n--- Scalar Program ({n_runs} runs) ---")
    tpu.write_instructions(scalar_prog)

    scalar_times = []
    for run in range(n_runs):
        clear_outputs(tpu, mm)
        write_test_inputs(tpu, mm)
        start = time.time()
        tpu.compute()
        elapsed = time.time() - start
        scalar_times.append(elapsed)
        print(f"  Run {run+1}: {elapsed*1000:.3f} ms")

    # Verify scalar outputs (fresh write + compute)
    print(f"\n  Scalar correctness check:")
    clear_outputs(tpu, mm)
    inputs_data = write_test_inputs(tpu, mm)
    tpu.compute()
    s_pass, s_total = verify_outputs(tpu, mm, inputs_data, "Scalar")
    if s_pass < s_total:
        all_pass = False

    # --- SIMD run ---
    print(f"\n--- SIMD Program ({n_runs} runs) ---")
    tpu.write_instructions(simd_prog)

    simd_times = []
    for run in range(n_runs):
        clear_outputs(tpu, mm)
        write_test_inputs(tpu, mm)
        start = time.time()
        tpu.compute()
        elapsed = time.time() - start
        simd_times.append(elapsed)
        print(f"  Run {run+1}: {elapsed*1000:.3f} ms")

    # Verify SIMD outputs (fresh write + compute)
    print(f"\n  SIMD correctness check:")
    clear_outputs(tpu, mm)
    inputs_data = write_test_inputs(tpu, mm)
    tpu.compute()
    v_pass, v_total = verify_outputs(tpu, mm, inputs_data, "SIMD")
    if v_pass < v_total:
        all_pass = False

    # --- Performance summary ---
    scalar_avg = np.mean(scalar_times) * 1000
    scalar_min = np.min(scalar_times) * 1000
    simd_avg = np.mean(simd_times) * 1000
    simd_min = np.min(simd_times) * 1000

    print("\n" + "=" * 70)
    print("Performance Summary")
    print("=" * 70)
    print(f"{'Metric':<25} {'Scalar':>12} {'SIMD':>12} {'Speedup':>10}")
    print("-" * 60)
    print(f"{'Instructions':<25} {n_scalar_instr:>12} {n_simd_instr:>12} {n_scalar_instr/n_simd_instr:>9.2f}x")
    print(f"{'Avg time (ms)':<25} {scalar_avg:>12.3f} {simd_avg:>12.3f} {scalar_avg/simd_avg:>9.2f}x")
    print(f"{'Best time (ms)':<25} {scalar_min:>12.3f} {simd_min:>12.3f} {scalar_min/simd_min:>9.2f}x")

    print(f"\nPer-workload instruction counts:")
    print(f"  {'Workload':<20} {'Scalar':>8} {'SIMD':>8} {'Speedup':>10}")
    print(f"  {'-'*48}")
    print(f"  {'32-elem ADD':<20} {'32':>8} {'16':>8} {'2.0x':>10}")
    print(f"  {'32-elem MUL':<20} {'32':>8} {'16':>8} {'2.0x':>10}")
    print(f"  {'32-elem MLP':<20} {'96':>8} {'28':>8} {'3.4x':>10}")
    print(f"  {'64-elem ADD':<20} {'64':>8} {'32':>8} {'2.0x':>10}")

    print(f"\nCorrectness: Scalar {s_pass}/{s_total}, SIMD {v_pass}/{v_total}")

    print("\n" + "=" * 70)
    if all_pass:
        print("ALL TESTS PASSED - SIMD produces correct results with fewer instructions")
    else:
        print("SOME TESTS FAILED")
    print("=" * 70)

    return all_pass


def main():
    parser = argparse.ArgumentParser(
        description="SIMD VPU pressure/performance test for Mini-TPU"
    )
    parser.add_argument("bitstream", help="Path to bitstream file (.bit)")
    parser.add_argument("--scalar-program", default="pressure_scalar.npy",
                        help="Compiled scalar program (.npy)")
    parser.add_argument("--simd-program", default="pressure_simd.npy",
                        help="Compiled SIMD program (.npy)")
    parser.add_argument("--metadata", "-m", default="pressure_meta.json",
                        help="Memory map metadata (.json)")
    parser.add_argument("--runs", "-n", type=int, default=5,
                        help="Number of timing runs per program (default: 5)")
    parser.add_argument("--tpu-ip", default="tpu_0",
                        help="TPU IP name in overlay")
    parser.add_argument("--dma-ip", default="axi_dma_0",
                        help="DMA IP name in overlay")
    args = parser.parse_args()

    scalar_prog = load_program(args.scalar_program)
    simd_prog = load_program(args.simd_program)
    with open(args.metadata) as f:
        memory_map = json.load(f)

    print(f"\nLoading bitstream: {args.bitstream}")
    print(f"Scalar program: {args.scalar_program} ({len(scalar_prog)} instructions)")
    print(f"SIMD program:   {args.simd_program} ({len(simd_prog)} instructions)")
    print(f"Memory map:     {len(memory_map)} allocations")

    # Validate program sizes against IRAM depth
    IRAM_DEPTH = 256
    if len(scalar_prog) > IRAM_DEPTH:
        print(f"\nERROR: Scalar program ({len(scalar_prog)}) exceeds IRAM depth ({IRAM_DEPTH})!")
        return 1
    if len(simd_prog) > IRAM_DEPTH:
        print(f"\nERROR: SIMD program ({len(simd_prog)}) exceeds IRAM depth ({IRAM_DEPTH})!")
        return 1

    tpu = TpuDriver(args.bitstream, tpu_name=args.tpu_ip, dma_name=args.dma_ip)

    # Data integrity sanity check before performance test
    data_integrity_check(tpu, memory_map)

    success = run_pressure_test(tpu, memory_map, scalar_prog, simd_prog,
                                n_runs=args.runs)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
