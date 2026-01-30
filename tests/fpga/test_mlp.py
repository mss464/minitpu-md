#!/usr/bin/env python3
"""
MLP Forward/Backward Pass Test for Mini-TPU

This test runs a complete MLP computation on the TPU hardware and
prints the results for verification.

Usage:
    python test_mlp.py <bitstream.bit> <instructions.txt>
"""

import argparse
import sys
import time
import os

# Add hal/ to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from hal.pynq_host import TpuDriver, load_instructions
import numpy as np


# Test data: memory loads (address, length, values)
# These are the input values for the MLP test
LOADS = [
    (0, 1, [0.0]),
    (217, 1, [0.0]),
    (250, 1, [0.0625]),
    (251, 1, [0.125]),
    (252, 1, [0.25]),
    (17, 16, [-0.6157273054122925, -0.8532673120498657, 0.846603512763977, 
              0.24555155634880066, -0.027109621092677116, 0.13724546134471893,
              -1.372422218322754, -0.7323502898216248, 0.011781510896980762,
              1.5158519744873047, 0.2315135896205902, 0.5745108723640442,
              1.082961082458496, -2.2413995265960693, 0.5595777034759521,
              -1.0570253133773804]),
    (1, 16, [1.082766056060791, 1.27499520778656, -0.5501754283905029,
             1.0163384675979614, 0.07839599996805191, -0.034628044813871384,
             0.7430522441864014, -1.9831030368804932, -0.5077247619628906,
             -1.6506532430648804, -0.30850839614868164, 0.7162443399429321,
             -1.2786157131195068, -0.189548060297966, -1.02693510055542,
             0.899297833442688]),
    (65, 4, [2.6693835258483887, -0.7779089212417603, -0.6129744052886963,
             -1.1968188285827637]),
    (101, 16, [1.2220115661621094, -1.1984094381332397, -1.861122488975525,
               0.3849925100803375, 0.7721431851387024, -0.5748991966247559,
               -1.0003670454025269, 1.2401621341705322, 0.9175151586532593,
               -0.2041284441947937, 0.3352528512477875, -1.1656676530838013,
               -1.0598396062850952, 1.288211703300476, 0.1472133994102478,
               -1.7400456666946411]),
]

# Expected outputs to read back (address, length, label)
STORES = [
    (1, 16, 'X'),
    (17, 16, 'W'),
    (33, 16, 'Z'),
    (65, 4, 'b'),
    (49, 16, 'W.T'),
    (69, 16, 'Y'),
    (85, 16, 'A'),
    (185, 16, 'diff'),
    (201, 16, 'sqaured'),
    (117, 16, 'dA'),
    (133, 16, 'dZ'),
    (234, 16, 'relu_deriv'),
    (149, 16, 'dW'),
    (165, 4, 'db'),
    (169, 16, 'dX'),
    (233, 1, 'loss'),
]


def main():
    parser = argparse.ArgumentParser(description="MLP test for Mini-TPU")
    parser.add_argument("bitstream", type=str, help="Path to TPU bitstream (.bit)")
    parser.add_argument("instructions", type=str, help="Path to instruction file")
    args = parser.parse_args()
    
    # Verify files exist
    if not os.path.exists(args.bitstream):
        raise FileNotFoundError(f"Bitstream not found: {args.bitstream}")
    hwh_path = os.path.splitext(args.bitstream)[0] + ".hwh"
    if not os.path.exists(hwh_path):
        raise FileNotFoundError(f"Hardware handoff not found: {hwh_path}")
    if not os.path.exists(args.instructions):
        raise FileNotFoundError(f"Instructions not found: {args.instructions}")
    
    # Initialize TPU
    print(f"Programming FPGA with {args.bitstream}")
    tpu = TpuDriver(args.bitstream)
    
    # Benchmark timing
    bench = {
        "load_time": 0.0,
        "write_iram_time": 0.0,
        "compute_time": 0.0,
        "store_time": 0.0,
        "total_time": 0.0,
    }
    
    overall_start = time.perf_counter()
    
    # Load data to BRAM
    t0 = time.perf_counter()
    for addr, length, values in LOADS:
        tpu.write_bram(addr, np.array(values, dtype=np.float32))
    bench["load_time"] = time.perf_counter() - t0
    print("loading data complete")
    
    # Load instructions
    t0 = time.perf_counter()
    instructions = load_instructions(args.instructions)
    tpu.write_instructions(instructions)
    bench["write_iram_time"] = time.perf_counter() - t0
    print("writing instructions complete")
    
    # Execute compute
    t0 = time.perf_counter()
    tpu.compute()
    bench["compute_time"] = time.perf_counter() - t0
    print("compute complete")
    
    # Read back results
    t0 = time.perf_counter()
    for addr, length, label in STORES:
        result = tpu.read_bram(addr, length)
        print(f"{label} = {result}")
    bench["store_time"] = time.perf_counter() - t0
    print("storing complete")
    
    bench["total_time"] = time.perf_counter() - overall_start
    
    print("===== BENCHMARK RESULTS =====")
    for key, val in bench.items():
        print(f"{key}: {val*1000:.3f} ms")


if __name__ == "__main__":
    main()
