
import argparse
import sys
import time
import os
import ast
import re
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

_TRACE_LOAD_RE = re.compile(r"^load (\d+), (\d+), (\[.*\])$")
_TRACE_STORE_RE = re.compile(r"^store (\d+), (\d+), (.+)$")


def _default_trace_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    trace_path = os.path.join(script_dir, "mlp_instruction_trace.txt")
    return trace_path if os.path.exists(trace_path) else None


def _infer_tile_size():
    for _, length, _ in LOADS:
        if length > 1:
            m = int(np.sqrt(length))
            if m * m == length:
                return m
    return 4


def _load_trace_ops(trace_path):
    ops = []
    with open(trace_path, "r") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("load "):
                match = _TRACE_LOAD_RE.match(line)
                if not match:
                    raise ValueError(f"Unrecognized load format: {line}")
                addr = int(match.group(1))
                length = int(match.group(2))
                values = ast.literal_eval(match.group(3))
                ops.append(("load", addr, length, values))
                continue
            if line.startswith("store "):
                match = _TRACE_STORE_RE.match(line)
                if not match:
                    raise ValueError(f"Unrecognized store format: {line}")
                addr = int(match.group(1))
                length = int(match.group(2))
                label = match.group(3).strip()
                ops.append(("store", addr, length, label))
                continue
            parts = [p.strip() for p in line.split()]
            op = parts[0]
            if op in {"add", "sub", "mul", "relu", "relu_derivative", "matmul"}:
                addr_parts = [int(p.strip()) for p in " ".join(parts[1:]).split(",")]
                ops.append((op, *addr_parts))
                continue
            raise ValueError(f"Unsupported op in trace: {line}")
    return ops


def _init_mem_from_loads(size):
    mem = np.zeros(size, dtype=np.float32)
    for addr, length, values in LOADS:
        mem[addr:addr + length] = np.array(values, dtype=np.float32)
    return mem


def _mem_size_hint(trace_ops, tile_size):
    max_addr = 0
    for op in trace_ops:
        name = op[0]
        if name == "load":
            _, addr, length, _ = op
            max_addr = max(max_addr, addr + length)
        elif name == "store":
            _, addr, length, _ = op
            max_addr = max(max_addr, addr + length)
        elif name == "matmul":
            _, a, b, c = op
            max_addr = max(max_addr, a + tile_size * tile_size,
                           b + tile_size * tile_size,
                           c + tile_size * tile_size)
        else:
            _, a, b, c = op
            max_addr = max(max_addr, a + 1, b + 1, c + 1)
    for addr, length, _ in STORES:
        max_addr = max(max_addr, addr + length)
    return max_addr + 1


def _run_trace(trace_ops, tile_size):
    mem = _init_mem_from_loads(_mem_size_hint(trace_ops, tile_size))
    for op in trace_ops:
        name = op[0]
        if name == "load":
            _, addr, length, values = op
            mem[addr:addr + length] = np.array(values, dtype=np.float32)
        elif name == "matmul":
            _, a, b, c = op
            # Hardware systolic array computes: C = B @ A^T
            # where matmul(a, b, c) means A at addr a, B at addr b, result at addr c
            A = mem[a:a + tile_size * tile_size].reshape(tile_size, tile_size)
            B = mem[b:b + tile_size * tile_size].reshape(tile_size, tile_size)
            C = (B @ A.T).astype(np.float32)
            mem[c:c + tile_size * tile_size] = C.reshape(-1)
        elif name == "add":
            _, a, b, c = op
            mem[c] = np.float32(mem[a] + mem[b])
        elif name == "sub":
            _, a, b, c = op
            mem[c] = np.float32(mem[a] - mem[b])
        elif name == "mul":
            _, a, b, c = op
            mem[c] = np.float32(mem[a] * mem[b])
        elif name == "relu":
            _, a, _, c = op
            mem[c] = np.float32(mem[a] if mem[a] > 0 else 0.0)
        elif name == "relu_derivative":
            _, a, _, c = op
            mem[c] = np.float32(1.0 if mem[a] > 0 else 0.0)
        elif name == "store":
            continue
        else:
            raise ValueError(f"Unsupported op in trace: {op}")
    expected = {}
    for addr, length, label in STORES:
        expected[label] = mem[addr:addr + length].copy()
    return expected


def _compare_results(expected, actual, atol=1e-3, rtol=1e-4):
    all_ok = True
    for label, exp in expected.items():
        got = actual.get(label)
        if got is None:
            print(f"  MISSING: {label}")
            all_ok = False
            continue
        if not np.allclose(got, exp, atol=atol, rtol=rtol):
            diff = np.abs(got - exp)
            max_idx = int(np.argmax(diff))
            print(f"  FAIL: {label} max diff {diff[max_idx]} at index {max_idx}")
            print(f"    Expected: {exp[:8]}...")
            print(f"    Got:      {got[:8]}...")
            all_ok = False
        else:
            print(f"  PASS: {label}")
    return all_ok


def main():
    parser = argparse.ArgumentParser(description="Generated TPU Test Script")
    parser.add_argument("bitstream", type=str, help="Path to TPU bitstream (.bit)")
    parser.add_argument("instr_file", type=str, nargs="+", help="Path(s) to instruction file(s)")
    parser.add_argument("--trace", type=str, nargs="*", default=None, help="Optional trace file(s) for CPU reference")
    parser.add_argument("--no_ref", action="store_true", help="Skip CPU numpy reference comparison")
    args = parser.parse_args()

    if not os.path.exists(args.bitstream):
        raise FileNotFoundError(f"Cannot find {args.bitstream}")
    for instr in args.instr_file:
        if not os.path.exists(instr):
            raise FileNotFoundError(f"Cannot find {instr}")

    if TpuDriver is None:
        print("ERROR: TpuDriver is not available in this environment.")
        sys.exit(1)

    trace_paths = args.trace
    if trace_paths is None or len(trace_paths) == 0:
        default_trace = _default_trace_path()
        trace_paths = [default_trace] if default_trace else []
    if trace_paths and len(trace_paths) not in {1, len(args.instr_file)}:
        raise ValueError("Provide either one trace file or one per instruction file.")

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

    tile_size = _infer_tile_size()
    all_ok = True

    for idx, instr_path in enumerate(args.instr_file):
        trace_path = None
        if trace_paths:
            trace_path = trace_paths[0] if len(trace_paths) == 1 else trace_paths[idx]
        expected = None
        if trace_path and not args.no_ref:
            trace_ops = _load_trace_ops(trace_path)
            expected = _run_trace(trace_ops, tile_size)

        # Load data to BRAM
        print(f"Loading data for program {idx + 1}...")
        t0 = time.perf_counter()
        for addr, length, values in LOADS:
            tpu.write_bram(addr, np.array(values, dtype=np.float32))
        bench["load_time"] += time.perf_counter() - t0
        print("loading data complete")

        # Load instructions
        print(f"Loading instructions from {instr_path}...")
        instrs = []
        with open(instr_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    instrs.append(int(line, 16))
        instrs_np = np.array(instrs, dtype=np.uint64)

        t0 = time.perf_counter()
        tpu.write_instructions(instrs_np)
        bench["write_iram_time"] += time.perf_counter() - t0
        print("writing instructions complete")

        # Execute compute
        print("Executing compute...")
        t0 = time.perf_counter()
        tpu.compute()
        bench["compute_time"] += time.perf_counter() - t0
        print("compute complete")

        # Read back results
        print("Reading results...")
        t0 = time.perf_counter()
        results = {}
        for addr, length, label in STORES:
            result = tpu.read_bram(addr, length)
            results[label] = result
            print(f"{label} = {result}")
        bench["store_time"] += time.perf_counter() - t0
        print("storing complete")

        if expected is not None:
            print("Comparing against CPU numpy reference...")
            if not _compare_results(expected, results):
                all_ok = False
        elif not args.no_ref:
            print("WARNING: No trace provided, skipping CPU reference comparison.")

    bench["total_time"] = time.perf_counter() - overall_start

    print("===== BENCHMARK RESULTS =====")
    for key, val in bench.items():
        print(f"{key}: {val*1000:.3f} ms")

    if not all_ok:
        sys.exit(1)

if __name__ == "__main__":
    main()
