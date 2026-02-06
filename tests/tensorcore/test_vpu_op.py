"""Unit tests for vpu_op.sv - VPU ALU operations (ADD, SUB, RELU, MUL)"""

import cocotb
from cocotb.triggers import Timer
import struct
import random

# Opcodes from vpu_op.sv
ADD = 0
SUB = 1
RELU = 2
MUL = 3
D_RELU = 4


def float_to_fp32(f):
    """Convert Python float to IEEE 754 32-bit representation."""
    return struct.unpack('>I', struct.pack('>f', f))[0]


def fp32_to_float(bits):
    """Convert IEEE 754 32-bit representation to Python float."""
    return struct.unpack('>f', struct.pack('>I', bits))[0]


def fp32_approx_equal(a, b, rel_tol=1e-5, abs_tol=1e-6):
    """Check if two FP32 values are approximately equal."""
    fa = fp32_to_float(a)
    fb = fp32_to_float(b)
    if fa == fb:
        return True
    return abs(fa - fb) <= max(rel_tol * max(abs(fa), abs(fb)), abs_tol)


@cocotb.test()
async def test_vpu_add_basic(dut):
    """Test VPU ADD operation."""
    test_cases = [(1.0, 2.0, 3.0), (0.5, 0.5, 1.0), (-1.0, 1.0, 0.0), (10.0, -5.0, 5.0)]
    dut.opcode.value = ADD
    dut.start.value = 1
    for a, b, expected in test_cases:
        dut.operand0.value = float_to_fp32(a)
        dut.operand1.value = float_to_fp32(b)
        await Timer(10, units="ns")
        result = fp32_to_float(int(dut.result_out.value))
        assert abs(result - expected) < 0.001, f"ADD {a}+{b}={result}, expected {expected}"
    dut._log.info("PASS: VPU ADD test")


@cocotb.test()
async def test_vpu_sub_basic(dut):
    """Test VPU SUB operation."""
    test_cases = [(3.0, 1.0, 2.0), (1.0, 3.0, -2.0), (5.0, 5.0, 0.0)]
    dut.opcode.value = SUB
    dut.start.value = 1
    for a, b, expected in test_cases:
        dut.operand0.value = float_to_fp32(a)
        dut.operand1.value = float_to_fp32(b)
        await Timer(10, units="ns")
        result = fp32_to_float(int(dut.result_out.value))
        assert abs(result - expected) < 0.001, f"SUB {a}-{b}={result}, expected {expected}"
    dut._log.info("PASS: VPU SUB test")


@cocotb.test()
async def test_vpu_relu(dut):
    """Test VPU RELU operation."""
    dut.opcode.value = RELU
    dut.start.value = 1
    # Positive values pass through
    for val in [1.0, 2.5, 100.0, 0.001]:
        dut.operand0.value = float_to_fp32(val)
        await Timer(10, units="ns")
        result = fp32_to_float(int(dut.result_out.value))
        assert abs(result - val) < 0.001, f"RELU({val})={result}, expected {val}"
    # Negative values become 0
    for val in [-1.0, -2.5, -100.0]:
        dut.operand0.value = float_to_fp32(val)
        await Timer(10, units="ns")
        result = fp32_to_float(int(dut.result_out.value))
        assert result == 0.0, f"RELU({val})={result}, expected 0.0"
    dut._log.info("PASS: VPU RELU test")


@cocotb.test()
async def test_vpu_mul_basic(dut):
    """Test VPU MUL operation."""
    test_cases = [(2.0, 3.0, 6.0), (0.5, 4.0, 2.0), (-2.0, 3.0, -6.0), (-2.0, -3.0, 6.0)]
    dut.opcode.value = MUL
    dut.start.value = 1
    for a, b, expected in test_cases:
        dut.operand0.value = float_to_fp32(a)
        dut.operand1.value = float_to_fp32(b)
        await Timer(10, units="ns")
        result = fp32_to_float(int(dut.result_out.value))
        assert abs(result - expected) < 0.01, f"MUL {a}*{b}={result}, expected {expected}"
    dut._log.info("PASS: VPU MUL test")


@cocotb.test()
async def test_vpu_relu_derivative(dut):
    """Test VPU RELU_DERIVATIVE operation (opcode 4 per docs/system.md)."""
    dut.opcode.value = D_RELU
    dut.start.value = 1
    # For positive inputs, derivative = 1.0
    for val in [1.0, 2.5, 100.0, 0.001]:
        dut.operand0.value = float_to_fp32(val)
        await Timer(10, units="ns")
        result = fp32_to_float(int(dut.result_out.value))
        assert abs(result - 1.0) < 0.001, f"RELU_DERIV({val})={result}, expected 1.0"
    # For negative inputs, derivative = 0.0
    for val in [-1.0, -2.5, -100.0]:
        dut.operand0.value = float_to_fp32(val)
        await Timer(10, units="ns")
        result = fp32_to_float(int(dut.result_out.value))
        assert result == 0.0, f"RELU_DERIV({val})={result}, expected 0.0"
    # Edge case: zero
    dut.operand0.value = float_to_fp32(0.0)
    await Timer(10, units="ns")
    dut._log.info("PASS: VPU RELU_DERIVATIVE test")


@cocotb.test()
async def test_vpu_randomized(dut):
    """Randomized test for VPU operations (all opcodes per docs/system.md)."""
    random.seed(77777)
    dut.start.value = 1
    for _ in range(50):
        a = random.uniform(-10.0, 10.0)
        b = random.uniform(-10.0, 10.0)
        op = random.choice([ADD, SUB, RELU, MUL, D_RELU])
        dut.operand0.value = float_to_fp32(a)
        dut.operand1.value = float_to_fp32(b)
        dut.opcode.value = op
        await Timer(10, units="ns")
        result = fp32_to_float(int(dut.result_out.value))
        if op == ADD:
            expected = a + b
        elif op == SUB:
            expected = a - b
        elif op == RELU:
            expected = max(0.0, a)
        elif op == MUL:
            expected = a * b
        elif op == D_RELU:
            expected = 1.0 if a > 0 else 0.0
        assert abs(result - expected) < 0.1, f"Op {op}: got {result}, expected {expected}"
    dut._log.info("PASS: VPU randomized test")
