
import argparse
import sys
import time
import os
import numpy as np

# Add compiler path if needed, assuming running from tests/fpga or similar
# sys.path.append(...)

try:
    from compiler.hal.pynq_host import TpuDriver
except ImportError as e:
    # Fallback for development/simulation
    print(f"Warning: Could not import TpuDriver: {e}")
    TpuDriver = None

# --- Auto-injected ---
LOADS = [(0, 1, [0.0]), (217, 1, [0.0]), (250, 1, [0.0625]), (251, 1, [0.125]), (252, 1, [0.25]), (17, 16, [2.3904972076416016, -1.27916419506073, -0.7935495376586914, -1.126505970954895, -0.5536972284317017, 1.3254542350769043, 0.7638459205627441, 0.09806855767965317, 0.313088983297348, 0.09190140664577484, -0.6949337720870972, -0.4246157109737396, 0.8132268190383911, 1.1902947425842285, 1.9697345495224, -0.4550611972808838]), (1, 16, [-1.2559642791748047, -0.22694578766822815, -3.102372646331787, 0.27252712845802307, -1.060408115386963, 0.009136246517300606, 0.9773455262184143, 0.3552972376346588, 1.5038087368011475, 0.24579574167728424, 0.028538299724459648, -0.1170438826084137, 0.5765029191970825, -0.5675789713859558, 0.24701951444149017, -1.1251425743103027]), (65, 4, [-0.48279064893722534, -0.7484656572341919, -1.170640468597412, 0.6757204532623291]), (101, 16, [-0.5492802858352661, -1.412819743156433, 1.2102267742156982, 0.13260453939437866, 0.3134997487068176, 1.1749695539474487, -1.2793750762939453, -0.09583567082881927, -1.8437986373901367, 0.5381866693496704, 0.5986366868019104, -1.2080944776535034, 2.750549793243408, -0.3633793294429779, 0.17723040282726288, 0.6219509840011597])]
STORES = [(1, 16, 'X'), (17, 16, 'W'), (33, 16, 'Z'), (65, 4, 'b'), (49, 16, 'W.T'), (69, 16, 'Y'), (85, 16, 'A'), (185, 16, 'diff'), (201, 16, 'sqaured'), (117, 16, 'dA'), (133, 16, 'dZ'), (149, 16, 'dW'), (165, 4, 'db'), (169, 16, 'dX'), (233, 1, 'loss')]

def main():
    parser = argparse.ArgumentParser(description="Generated TPU Test Script")
    parser.add_argument("bitstream", type=str, help="Path to TPU bitstream (.bit)")
    parser.add_argument("instr_file", type=str, help="Path to instruction file")
    args = parser.parse_args()

    if not os.path.exists(args.bitstream):
        raise FileNotFoundError(f"Cannot find {args.bitstream}")
    if not os.path.exists(args.instr_file):
        raise FileNotFoundError(f"Cannot find {args.instr_file}")

    print(f"Programming FPGA with {args.bitstream}")
    tpu = TpuDriver(args.bitstream)

    bench = {
        "load_time": 0.0,
        "write_iram_time": 0.0,
        "compute_time": 0.0,
        "store_time": 0.0,
        "total_time": 0.0
    }

    overall_start = time.perf_counter()

    # Load data to BRAM
    print("Loading data...")
    t0 = time.perf_counter()
    for addr, length, values in LOADS:
        # values is a list
        tpu.write_bram(addr, np.array(values, dtype=np.float32))
    bench["load_time"] = time.perf_counter() - t0
    print("loading data complete")

    # Load instructions
    print("Loading instructions...")
    instrs = []
    with open(args.instr_file) as f:
        for line in f:
            line = line.strip()
            if line:
                instrs.append(int(line, 16))
    instrs_np = np.array(instrs, dtype=np.uint64)

    t0 = time.perf_counter()
    tpu.write_instructions(instrs_np)
    bench["write_iram_time"] = time.perf_counter() - t0
    print("writing instructions complete")

    # Execute compute
    print("Executing compute...")
    t0 = time.perf_counter()
    tpu.compute()
    bench["compute_time"] = time.perf_counter() - t0
    print("compute complete")

    # Read back results
    print("Reading results...")
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
