
import argparse
import sys
import time
import os
import numpy as np

# Add compiler path if needed, assuming running from tests/fpga or similar
# sys.path.append(...)

try:
    from compiler.hal.pynq_host import TpuDriver
except ImportError:
    # Try local import if hal is in current dir (for board deployment)
    try:
        from hal.pynq_host import TpuDriver
    except ImportError:
        # Fallback for development/simulation
        print("Warning: Could not import TpuDriver")
        TpuDriver = None

# --- Auto-injected ---
LOADS = [(0, 1, [0.0]), (217, 1, [0.0]), (250, 1, [0.0625]), (251, 1, [0.125]), (252, 1, [0.25]), (17, 16, [0.18049031496047974, 1.3456237316131592, -0.46319180727005005, 0.6111230254173279, 0.28908658027648926, -0.843321681022644, 0.1237388327717781, -1.1752479076385498, -1.1311488151550293, 0.25327998399734497, 1.3884514570236206, 0.35802191495895386, 0.26027023792266846, -0.8294625878334045, -0.47780659794807434, -0.5578939318656921]), (1, 16, [0.9746877551078796, 0.3009909689426422, -0.5175281167030334, -0.0497504360973835, 0.623905599117279, -1.6761279106140137, -0.1666465550661087, 1.1768361330032349, -1.8123018741607666, 1.238332986831665, -0.2016395628452301, 0.285489022731781, -1.1836705207824707, 0.6421962380409241, 1.3403878211975098, -0.8354191780090332]), (65, 4, [1.580275297164917, 2.1845762729644775, 1.15296471118927, 1.564477801322937]), (101, 16, [0.7616337537765503, -1.400343894958496, 0.13606107234954834, -0.1788070648908615, 2.73236083984375, 0.051361776888370514, -0.28106337785720825, -0.21290409564971924, 0.2810458540916443, -0.5300220847129822, -1.6555426120758057, -0.2496841847896576, 0.2329879105091095, -0.6109113097190857, -0.757436990737915, 1.635733962059021])]
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
