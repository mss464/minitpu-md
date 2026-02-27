import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
import numpy as np
import struct

N = 4
BASE_ADDR_W = 0x000
BASE_ADDR_X = 0x100
BASE_ADDR_OUT = 0x200
TIMEOUT_CYCLES = 2000

def float_to_fp32_bits(val: float) -> int:
    return struct.unpack(">I", struct.pack(">f", float(val)))[0]

def fp32_bits_to_float(bits: int) -> float:
    bits = bits & 0xFFFFFFFF
    return struct.unpack(">f", struct.pack(">I", bits))[0]

async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.start.value = 0
    dut.base_addr_w.value = BASE_ADDR_W
    dut.base_addr_x.value = BASE_ADDR_X
    dut.base_addr_out.value = BASE_ADDR_OUT
    dut.mem_resp_data.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

async def memory_driver(dut, mem):
    """Memory model - simulates 8 BANKING_FACTOR banks (256-bit)."""
    last_addr = 0
    while True:
        await RisingEdge(dut.clk)
        try:
            rd_en = int(dut.mem_read_en.value)
            addr = int(dut.mem_req_addr.value)
            wr_en = int(dut.mem_write_en.value)
            wr_data_raw = int(dut.mem_req_data.value)
        except ValueError:
            rd_en, addr, wr_en, wr_data_raw = 0, 0, 0, 0

        if rd_en: last_addr = addr
        if wr_en:
            for b in range(8):
                mem[addr + b] = (wr_data_raw >> (b * 32)) & 0xFFFFFFFF

        resp_val = 0
        for b in range(8):
            resp_val |= (mem.get(last_addr + b, 0) & 0xFFFFFFFF) << (b * 32)
        dut.mem_resp_data.value = resp_val

def load_matrices(mem, w_base, x_base, w_mat, x_mat):
    w_flat = w_mat.flatten()
    x_flat = x_mat.flatten()
    for i, val in enumerate(w_flat):
        mem[w_base + i] = float_to_fp32_bits(val)
    for i, val in enumerate(x_flat):
        mem[x_base + i] = float_to_fp32_bits(val)

async def run_matmul(dut, mem, w_mat, x_mat, w_base=BASE_ADDR_W, x_base=BASE_ADDR_X, out_base=BASE_ADDR_OUT):
    load_matrices(mem, w_base, x_base, w_mat, x_mat)
    dut.base_addr_w.value = w_base
    dut.base_addr_x.value = x_base
    dut.base_addr_out.value = out_base
    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0
    for _ in range(TIMEOUT_CYCLES):
        await RisingEdge(dut.clk)
        if int(dut.done.value): break
    else: raise cocotb.result.TestFailure("Timeout")
    await RisingEdge(dut.clk)
    
    out = np.zeros((N, N), dtype=float)
    for i in range(N):
        for j in range(N):
            idx = i * N + j
            try: raw = int(dut.OUT_DEBUG[idx].out_elem.value)
            except AttributeError: raw = int(dut.out_matrix[idx].value)
            out[i, j] = fp32_bits_to_float(raw)
    return out

@cocotb.test()
async def test_identity_and_permutation(dut):
    """Test Identity and Permutation matrices."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    mem = {}
    cocotb.start_soon(memory_driver(dut, mem))
    await reset_dut(dut)

    # Identity
    w = np.eye(N)
    x = np.arange(1, N*N+1).reshape(N, N).astype(float)
    out = await run_matmul(dut, mem, w, x)
    assert np.allclose(out, x @ w.T, atol=1e-3), "Identity mismatch"

    # Permutation
    w_perm = np.zeros((N, N))
    w_perm[0, 1] = 1; w_perm[1, 0] = 1; w_perm[2, 3] = 1; w_perm[3, 2] = 1
    out_perm = await run_matmul(dut, mem, w_perm, x)
    assert np.allclose(out_perm, x @ w_perm.T, atol=1e-3), "Permutation mismatch"

@cocotb.test()
async def test_sparse_matrices(dut):
    """Test highly sparse matrices."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    mem = {}
    cocotb.start_soon(memory_driver(dut, mem))
    await reset_dut(dut)

    rng = np.random.default_rng(123)
    w = rng.uniform(-1, 1, (N, N))
    w[w < 0.8] = 0 # 80% sparse
    x = rng.uniform(-1, 1, (N, N))
    x[x < 0.5] = 0 # 50% sparse
    
    out = await run_matmul(dut, mem, w, x)
    assert np.allclose(out, x @ w.T, atol=1e-3), "Sparse mismatch"

@cocotb.test()
async def test_tiled_8x8_matmul(dut):
    """Simulate an 8x8 matmul using 4x4 tiles."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    mem = {}
    cocotb.start_soon(memory_driver(dut, mem))
    await reset_dut(dut)

    rng = np.random.default_rng(456)
    W_large = rng.uniform(-1, 1, (8, 8)).astype(float)
    X_large = rng.uniform(-1, 1, (8, 8)).astype(float)
    Y_expected = X_large @ W_large.T

    Y_actual = np.zeros((8, 8))

    # C_ij = sum_k (X_ik * W_jk^T)
    # We do this in 4x4 tiles
    for i_tile in range(2):
        for j_tile in range(2):
            tile_acc = np.zeros((4, 4))
            for k_tile in range(2):
                x_sub = X_large[i_tile*4:(i_tile+1)*4, k_tile*4:(k_tile+1)*4]
                w_sub = W_large[j_tile*4:(j_tile+1)*4, k_tile*4:(k_tile+1)*4]
                
                # We need to accumulate. Since our MXU is simple weight-stationary,
                # we'll do the summation in Python and just verify each 4x4 hop.
                out_tile = await run_matmul(dut, mem, w_sub, x_sub)
                tile_acc += out_tile
            
            Y_actual[i_tile*4:(i_tile+1)*4, j_tile*4:(j_tile+1)*4] = tile_acc

    assert np.allclose(Y_actual, Y_expected, atol=1e-2), "Tiled 8x8 mismatch"
