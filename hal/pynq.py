
import argparse
import os
import time
import numpy as np
from pynq import Overlay, allocate

REG_ADDR = {
    "tpu_mode":        0x00,
    "instr_ready":  0x04,
    "stream_ready": 0x08,
    "addr_ram":       0x0C,
    "length":       0x18,
}

WRITE_BRAM = 1
READ_BRAM  = 2
COMPUTE    = 3
WRITE_IRAM = 4

def wait_for_flag(mmio, name, expected=1, poll_delay=0.001):
    offset = REG_ADDR[name]
    while mmio.read(offset) != expected:
        time.sleep(poll_delay)

# --- Auto-injected ---
LOADS = [(0, 253, [0.0, 0.8280847072601318, -1.850175380706787, -1.0441585779190063, 1.1127811670303345, -0.8332078456878662, -1.436883568763733, 2.042782783508301, -0.3516356348991394, 1.4032084941864014, 0.6471076011657715, -0.2705962657928467, 1.7811048030853271, -0.6257866621017456, 0.8331131339073181, -1.3747423887252808, -0.2148800641298294, -0.04154361039400101, 0.057802312076091766, 0.6344006657600403, 0.231752410531044, -0.7692555785179138, 0.5270997881889343, 1.142364501953125, -0.6342173218727112, 0.08543499559164047, 1.5855762958526611, -1.189626932144165, -1.217897891998291, -0.7606958746910095, -0.0959782749414444, 0.43485406041145325, 1.029808759689331, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -0.42975351214408875, -0.6227213144302368, -1.7321325540542603, -0.09314381331205368, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -0.8831514716148376, -0.8105963468551636, 0.18598048388957977, 1.1302368640899658, -0.09444493055343628, 1.7072230577468872, -0.27756357192993164, 2.0517308712005615, 1.8680415153503418, 0.25381696224212646, 0.5450514554977417, -1.435294270515442, -1.5792121887207031, -0.19108685851097107, -1.455509066581726, 0.792579174041748, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0625, 0.125, 0.25])]
STORES = [(1, 16, 'X'), (17, 16, 'W'), (33, 16, 'Z'), (65, 4, 'b'), (49, 16, 'W.T'), (69, 16, 'Y'), (85, 16, 'A'), (185, 16, 'diff'), (201, 16, 'sqaured'), (117, 16, 'dA'), (133, 16, 'dZ'), (149, 16, 'dW'), (165, 4, 'db'), (169, 16, 'dX'), (233, 1, 'loss')]

def write_bram(mmio, dma, addr, values):
    in_buf = allocate(shape=values.shape, dtype=np.int64)
    value_bits = values.view(np.uint32)
    wait_for_flag(mmio, "instr_ready", 1)
    mmio.write(REG_ADDR["addr_ram"], addr)
    mmio.write(REG_ADDR["length"], values.size)
    mmio.write(REG_ADDR["tpu_mode"], WRITE_BRAM)

    wait_for_flag(mmio, "stream_ready", 1)
    in_buf[:] = value_bits.astype(np.uint64)
    dma.sendchannel.transfer(in_buf)
    dma.sendchannel.wait()
    wait_for_flag(mmio, "instr_ready", 1)
    in_buf.freebuffer()
    mmio.write(REG_ADDR["tpu_mode"], 0)

def read_bram(mmio, dma, addr, length):

    out_buf = allocate(shape=(length,), dtype=np.float32)
    # wait_for_flag(mmio, "stream_ready", 1)
    wait_for_flag(mmio, "instr_ready", 1)
    mmio.write(REG_ADDR["addr_ram"], addr)
    mmio.write(REG_ADDR["length"], length)
    mmio.write(REG_ADDR["tpu_mode"], READ_BRAM)

    dma.recvchannel.transfer(out_buf)
    dma.recvchannel.wait()

    wait_for_flag(mmio, "instr_ready", 1)
    mmio.write(REG_ADDR["tpu_mode"], 0)

    arr = np.copy(out_buf)
    out_buf.freebuffer()
    return arr

def main():
    parser = argparse.ArgumentParser(description="PYNQ host program to test TPU (write, compute, read)")
    parser.add_argument("bitstream", type=str, help="Path to TPU bitstream (.bit)")
    parser.add_argument("instr_file")
    args = parser.parse_args()

    bit_path = args.bitstream
    instructions = args.instr_file

    if not os.path.exists(bit_path):
        raise FileNotFoundError(f"Cannot find {bit_path}")
    hwh_path = os.path.splitext(bit_path)[0] + ".hwh"
    if not os.path.exists(hwh_path):
        raise FileNotFoundError(f"Missing .hwh for overlay: {hwh_path}")

    print(f"Programming FPGA with {bit_path}")
    ol = Overlay(args.bitstream)
    ol.download()

    dma = ol.axi_dma_0
    ctrl = ol.tpu_top_v6_0
    mmio = ctrl.mmio

    base = 0x0000

    bench = {
        "load_time": 0.0,
        "write_iram_time": 0.0,
        "compute_time": 0.0,
        "store_time": 0.0,
        "total_time": 0.0
    }

    overall_start = time.perf_counter()

    t0 = time.perf_counter()
    for (addr, length, value) in LOADS:
        write_bram(mmio, dma, addr, np.array(value, dtype=np.float32).reshape(-1))
    bench["load_time"] = time.perf_counter() - t0
    print("loading data complete")

    instrs = []
    with open(instructions) as f:
        for line in f:
            instrs.append(int(line, 16))
    instrs_np = np.array(instrs, dtype=np.uint64)

    instr_buf = allocate(shape=instrs_np.shape, dtype=np.uint64)
    
    t0 = time.perf_counter()
    
    wait_for_flag(mmio, "instr_ready", 1)
    mmio.write(REG_ADDR["addr_ram"], base)
    mmio.write(REG_ADDR["length"], len(instrs_np))
    mmio.write(REG_ADDR["tpu_mode"], WRITE_IRAM)
    wait_for_flag(mmio, "stream_ready", 1)
    instr_buf[:] = instrs_np
    dma.sendchannel.transfer(instr_buf)
    dma.sendchannel.wait()
    wait_for_flag(mmio, "instr_ready", 1)

    bench["write_iram_time"] = time.perf_counter() - t0
    print("writing instructions complete")

    mmio.write(REG_ADDR["tpu_mode"], 0)
    instr_buf.freebuffer()


    t0 = time.perf_counter()

    wait_for_flag(mmio, "instr_ready", 1)
    mmio.write(REG_ADDR["tpu_mode"], COMPUTE)
    wait_for_flag(mmio, "instr_ready", 1)

    bench["compute_time"] = time.perf_counter() - t0
    print("compute complete")

    mmio.write(REG_ADDR["tpu_mode"], 0)

    
    # Compute overall read window
    min_addr = min(addr for (addr, _, _) in STORES)
    max_addr = max(addr + (length) for (addr, length, _) in STORES)
    total_len = max_addr - min_addr

    # Single DMA read
    t0 = time.perf_counter()
    merged = read_bram(mmio, dma, min_addr, total_len + 1) # idk why but the +1 fixes the bus error bug somehow
    bench["store_time"] = time.perf_counter() - t0

    for (addr, length, label) in STORES:
        start = addr - min_addr
        end = start + length
        out = merged[start:end]
        print(f"{label} = {out}")

    print("storing complete")
    bench["total_time"] = time.perf_counter() - overall_start
    print("===== BENCHMARK RESULTS =====")
    for key, val in bench.items():
        print(f"{key}: {val*1000:.3f} ms")

if __name__ == "__main__":
    main()

