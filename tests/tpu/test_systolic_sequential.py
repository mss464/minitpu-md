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
    """Convert Python float to 32-bit IEEE-754 single-precision bit pattern."""
    return struct.unpack(">I", struct.pack(">f", float(val)))[0]


def fp32_bits_to_float(bits: int) -> float:
    """Convert 32-bit IEEE-754 bit pattern to Python float."""
    bits = bits & 0xFFFFFFFF
    return struct.unpack(">f", struct.pack(">I", bits))[0]


async def reset_dut(dut):
    """Assert active-low reset and return to a clean idle state."""
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
    """Simple memory model that responds to read requests."""
    while True:
        await RisingEdge(dut.clk)
        try:
            addr = int(dut.mem_req_addr.value)
        except ValueError:
            addr = 0
        dut.mem_resp_data.value = mem.get(addr, 0)


def load_matrices(mem, w_base, x_base, w_mat, x_mat):
    """Load flattened matrices into the memory map."""
    w_flat = w_mat.flatten()
    x_flat = x_mat.flatten()
    for i, val in enumerate(w_flat):
        mem[w_base + i] = float_to_fp32_bits(val)
    for i, val in enumerate(x_flat):
        mem[x_base + i] = float_to_fp32_bits(val)


async def run_matmul(dut, mem, w_mat, x_mat):
    """Run one matmul through the wrapper and return output matrix."""
    load_matrices(mem, BASE_ADDR_W, BASE_ADDR_X, w_mat, x_mat)

    dut.base_addr_w.value = BASE_ADDR_W
    dut.base_addr_x.value = BASE_ADDR_X
    dut.base_addr_out.value = BASE_ADDR_OUT

    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0

    for _ in range(TIMEOUT_CYCLES):
        await RisingEdge(dut.clk)
        if int(dut.done.value):
            break
    else:
        raise cocotb.result.TestFailure("Timeout waiting for done")

    await RisingEdge(dut.clk)

    out = np.zeros((N, N), dtype=float)
    for i in range(N):
        for j in range(N):
            out[i, j] = fp32_bits_to_float(int(dut.out_matrix[i * N + j].value))
    return out


@cocotb.test()
async def test_sequential_matmul_no_reset(dut):
    """Two matmuls back-to-back without reset should not leak state."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    mem = {}
    cocotb.start_soon(memory_driver(dut, mem))

    await reset_dut(dut)

    rng = np.random.default_rng(42)

    w1 = rng.uniform(-2.0, 2.0, size=(N, N)).astype(float)
    x1 = rng.uniform(-2.0, 2.0, size=(N, N)).astype(float)
    out1 = await run_matmul(dut, mem, w1, x1)
    exp1 = x1 @ w1.T
    assert np.allclose(out1, exp1, rtol=1e-3, atol=1e-3), "Run 1 mismatch"

    w2 = rng.uniform(-2.0, 2.0, size=(N, N)).astype(float)
    x2 = rng.uniform(-2.0, 2.0, size=(N, N)).astype(float)
    out2 = await run_matmul(dut, mem, w2, x2)
    exp2 = x2 @ w2.T
    assert np.allclose(out2, exp2, rtol=1e-3, atol=1e-3), "Run 2 mismatch"


@cocotb.test()
async def test_alternating_weight_patterns(dut):
    """Zero weights after a nonzero run should produce zero output."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    mem = {}
    cocotb.start_soon(memory_driver(dut, mem))

    await reset_dut(dut)

    rng = np.random.default_rng(7)
    w1 = rng.uniform(-1.5, 1.5, size=(N, N)).astype(float)
    x1 = rng.uniform(-1.5, 1.5, size=(N, N)).astype(float)
    out1 = await run_matmul(dut, mem, w1, x1)
    exp1 = x1 @ w1.T
    assert np.allclose(out1, exp1, rtol=1e-3, atol=1e-3), "Baseline mismatch"

    w2 = np.zeros((N, N), dtype=float)
    x2 = rng.uniform(-1.5, 1.5, size=(N, N)).astype(float)
    out2 = await run_matmul(dut, mem, w2, x2)
    exp2 = np.zeros((N, N), dtype=float)
    assert np.allclose(out2, exp2, rtol=1e-5, atol=1e-5), "Zero-weight run mismatch"


@cocotb.test()
async def test_multiple_sequential_random(dut):
    """Stress test multiple sequential matmuls without reset."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    mem = {}
    cocotb.start_soon(memory_driver(dut, mem))

    await reset_dut(dut)

    rng = np.random.default_rng(1234)
    for _ in range(10):
        w = rng.uniform(-2.0, 2.0, size=(N, N)).astype(float)
        x = rng.uniform(-2.0, 2.0, size=(N, N)).astype(float)
        out = await run_matmul(dut, mem, w, x)
        exp = x @ w.T
        assert np.allclose(out, exp, rtol=1e-3, atol=1e-3), "Sequential run mismatch"
