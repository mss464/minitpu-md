
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
LOADS = [(0, 1, [0.0]), (217, 1, [0.0]), (250, 1, [0.0625]), (251, 1, [0.125]), (252, 1, [0.25]), (17, 16, [0.5349372625350952, -0.42807283997535706, 0.6224414706230164, 0.412855863571167, -0.1609402596950531, 0.45991650223731995, -0.008394825272262096, -1.0810587406158447, -0.4092785120010376, 0.33538737893104553, 0.7745689749717712, 1.246403455734253, 0.06053096055984497, -0.4809349775314331, 2.8815693855285645, 0.3675261437892914]), (1, 16, [-2.011988639831543, -1.096235752105713, 0.28206828236579895, 1.3023632764816284, -2.6207454204559326, 0.5203536748886108, -0.7461836934089661, -1.4004322290420532, -0.3369337022304535, -0.4005471169948578, -0.5305342674255371, -0.8704047203063965, -1.2647355794906616, -0.6878875494003296, -1.266802430152893, -1.1686781644821167]), (65, 4, [-0.23962494730949402, 0.5054038166999817, -0.19779425859451294, 1.5840543508529663]), (101, 16, [0.9468435049057007, -0.400322824716568, 0.29833781719207764, 0.03668760135769844, -1.5196205377578735, -0.7553608417510986, 0.008393446914851665, 0.15188133716583252, -0.2558029294013977, 1.2145031690597534, -0.7655883431434631, 1.3448312282562256, 0.7687711119651794, -0.3062424957752228, -0.2469402551651001, 0.8169132471084595])]
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
