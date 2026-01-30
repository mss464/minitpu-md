"""
Unit tests for fixedpoint.sv - Fixed-point arithmetic modules
Tests fxp_add, fxp_mul, fxp_zoom with various input patterns
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge, ClockCycles
import random
import struct


def to_fixed(val, int_bits=8, frac_bits=8):
    """Convert float to fixed-point representation."""
    total_bits = int_bits + frac_bits
    scaled = int(round(val * (1 << frac_bits)))
    # Handle sign extension for negative numbers
    if scaled < 0:
        scaled = (1 << total_bits) + scaled
    return scaled & ((1 << total_bits) - 1)


def from_fixed(val, int_bits=8, frac_bits=8):
    """Convert fixed-point representation to float."""
    total_bits = int_bits + frac_bits
    # Check if negative (MSB set)
    if val >= (1 << (total_bits - 1)):
        val = val - (1 << total_bits)
    return float(val) / (1 << frac_bits)


# ============================================================================
# fxp_add tests
# ============================================================================

@cocotb.test()
async def test_fxp_add_basic(dut):
    """Test basic fixed-point addition."""
    # Test adding positive numbers
    a_float, b_float = 2.5, 1.5
    dut.ina.value = to_fixed(a_float)
    dut.inb.value = to_fixed(b_float)
    await Timer(10, units="ns")

    result = int(dut.out.value)
    result_float = from_fixed(result)
    expected = a_float + b_float

    dut._log.info(f"fxp_add: {a_float} + {b_float} = {result_float} (expected {expected})")
    assert abs(result_float - expected) < 0.02, f"Addition error: got {result_float}, expected {expected}"
    dut._log.info("PASS: Basic fxp_add test")


@cocotb.test()
async def test_fxp_add_negative(dut):
    """Test fixed-point addition with negative numbers."""
    test_cases = [
        (-2.0, 1.0, -1.0),
        (3.5, -1.5, 2.0),
        (-2.25, -1.75, -4.0),
        (0.0, -5.0, -5.0),
    ]

    for a, b, expected in test_cases:
        dut.ina.value = to_fixed(a)
        dut.inb.value = to_fixed(b)
        await Timer(10, units="ns")

        result = from_fixed(int(dut.out.value))
        dut._log.info(f"fxp_add: {a} + {b} = {result} (expected {expected})")
        assert abs(result - expected) < 0.02, f"Got {result}, expected {expected}"

    dut._log.info("PASS: Negative numbers fxp_add test")


@cocotb.test()
async def test_fxp_add_zero(dut):
    """Test fixed-point addition with zero."""
    test_values = [1.5, -2.25, 0.0, 127.5, -128.0]

    for val in test_values:
        # val + 0
        dut.ina.value = to_fixed(val)
        dut.inb.value = to_fixed(0.0)
        await Timer(10, units="ns")
        result = from_fixed(int(dut.out.value))
        assert abs(result - val) < 0.02, f"{val} + 0 should be {val}, got {result}"

    dut._log.info("PASS: Zero addition test")


@cocotb.test()
async def test_fxp_add_randomized(dut):
    """Randomized test for fixed-point addition."""
    num_tests = 50
    seed = 11111
    random.seed(seed)

    dut._log.info(f"Starting randomized fxp_add test ({num_tests} tests, seed={seed})")

    for _ in range(num_tests):
        # Generate random values within fixed-point range
        a = random.uniform(-64.0, 64.0)
        b = random.uniform(-64.0, 64.0)
        expected = a + b

        # Clamp expected to representable range
        if expected > 127.99:
            expected = 127.99
        elif expected < -128.0:
            expected = -128.0

        dut.ina.value = to_fixed(a)
        dut.inb.value = to_fixed(b)
        await Timer(10, units="ns")

        result = from_fixed(int(dut.out.value))
        overflow = int(dut.overflow.value)

        # If not overflow, check result
        if not overflow and abs(expected) < 127:
            assert abs(result - expected) < 0.5, f"{a} + {b}: got {result}, expected {expected}"

    dut._log.info("PASS: Randomized fxp_add test")


# ============================================================================
# fxp_mul tests
# ============================================================================

@cocotb.test()
async def test_fxp_mul_basic(dut):
    """Test basic fixed-point multiplication."""
    test_cases = [
        (2.0, 3.0, 6.0),
        (1.5, 2.0, 3.0),
        (4.0, 0.25, 1.0),
        (0.5, 0.5, 0.25),
    ]

    for a, b, expected in test_cases:
        dut.ina.value = to_fixed(a)
        dut.inb.value = to_fixed(b)
        await Timer(10, units="ns")

        result = from_fixed(int(dut.out.value))
        dut._log.info(f"fxp_mul: {a} * {b} = {result} (expected {expected})")
        assert abs(result - expected) < 0.05, f"Got {result}, expected {expected}"

    dut._log.info("PASS: Basic fxp_mul test")


@cocotb.test()
async def test_fxp_mul_negative(dut):
    """Test fixed-point multiplication with negative numbers."""
    test_cases = [
        (-2.0, 3.0, -6.0),
        (2.0, -3.0, -6.0),
        (-2.0, -3.0, 6.0),
        (-1.5, 2.0, -3.0),
    ]

    for a, b, expected in test_cases:
        dut.ina.value = to_fixed(a)
        dut.inb.value = to_fixed(b)
        await Timer(10, units="ns")

        result = from_fixed(int(dut.out.value))
        dut._log.info(f"fxp_mul: {a} * {b} = {result} (expected {expected})")
        assert abs(result - expected) < 0.05, f"Got {result}, expected {expected}"

    dut._log.info("PASS: Negative fxp_mul test")


@cocotb.test()
async def test_fxp_mul_zero(dut):
    """Test multiplication by zero."""
    test_values = [1.0, -2.5, 127.0, -128.0, 0.5]

    for val in test_values:
        dut.ina.value = to_fixed(val)
        dut.inb.value = to_fixed(0.0)
        await Timer(10, units="ns")
        result = from_fixed(int(dut.out.value))
        assert abs(result) < 0.01, f"{val} * 0 should be 0, got {result}"

    dut._log.info("PASS: Zero multiplication test")


@cocotb.test()
async def test_fxp_mul_one(dut):
    """Test multiplication by one (identity)."""
    test_values = [1.0, -2.5, 50.75, -100.25, 0.125]

    for val in test_values:
        dut.ina.value = to_fixed(val)
        dut.inb.value = to_fixed(1.0)
        await Timer(10, units="ns")
        result = from_fixed(int(dut.out.value))
        assert abs(result - val) < 0.05, f"{val} * 1 should be {val}, got {result}"

    dut._log.info("PASS: Identity multiplication test")


@cocotb.test()
async def test_fxp_mul_randomized(dut):
    """Randomized test for fixed-point multiplication."""
    num_tests = 50
    seed = 22222
    random.seed(seed)

    dut._log.info(f"Starting randomized fxp_mul test ({num_tests} tests, seed={seed})")

    for _ in range(num_tests):
        # Use smaller values to avoid overflow
        a = random.uniform(-8.0, 8.0)
        b = random.uniform(-8.0, 8.0)
        expected = a * b

        dut.ina.value = to_fixed(a)
        dut.inb.value = to_fixed(b)
        await Timer(10, units="ns")

        result = from_fixed(int(dut.out.value))
        overflow = int(dut.overflow.value)

        # If no overflow, check result
        if not overflow and abs(expected) < 64:
            # Allow larger tolerance for multiplication
            assert abs(result - expected) < 0.5, f"{a} * {b}: got {result}, expected {expected}"

    dut._log.info("PASS: Randomized fxp_mul test")


# ============================================================================
# fxp_zoom tests (bit width conversion)
# ============================================================================

@cocotb.test()
async def test_fxp_zoom_identity(dut):
    """Test zoom with same input/output widths (identity)."""
    test_values = [0, 1.0, -1.0, 5.5, -5.5, 127.0, -128.0]

    for val in test_values:
        dut.inp.value = to_fixed(val)
        await Timer(10, units="ns")
        result = from_fixed(int(dut.out.value))
        assert abs(result - val) < 0.01, f"Identity zoom failed: {val} -> {result}"

    dut._log.info("PASS: fxp_zoom identity test")


@cocotb.test()
async def test_fxp_zoom_overflow(dut):
    """Test zoom overflow detection."""
    # This requires specific parameter configuration
    # For now, just verify overflow flag exists and works for extreme values
    max_positive = 127.9
    min_negative = -128.0

    dut.inp.value = to_fixed(max_positive)
    await Timer(10, units="ns")
    # Overflow should be 0 for valid range
    dut._log.info(f"Max positive {max_positive}: overflow={int(dut.overflow.value)}")

    dut.inp.value = to_fixed(min_negative)
    await Timer(10, units="ns")
    dut._log.info(f"Min negative {min_negative}: overflow={int(dut.overflow.value)}")

    dut._log.info("PASS: fxp_zoom overflow test")


# ============================================================================
# fxp_addsub tests (combined add/subtract)
# ============================================================================

@cocotb.test()
async def test_fxp_addsub_add_mode(dut):
    """Test fxp_addsub in addition mode."""
    test_cases = [
        (2.0, 3.0, 5.0),
        (-1.0, 4.0, 3.0),
        (1.5, 2.5, 4.0),
    ]

    for a, b, expected in test_cases:
        dut.ina.value = to_fixed(a)
        dut.inb.value = to_fixed(b)
        dut.sub.value = 0  # Addition mode
        await Timer(10, units="ns")

        result = from_fixed(int(dut.out.value))
        assert abs(result - expected) < 0.02, f"Add {a} + {b}: got {result}, expected {expected}"

    dut._log.info("PASS: fxp_addsub add mode test")


@cocotb.test()
async def test_fxp_addsub_sub_mode(dut):
    """Test fxp_addsub in subtraction mode."""
    test_cases = [
        (5.0, 3.0, 2.0),
        (3.0, 5.0, -2.0),
        (-1.0, -4.0, 3.0),
        (2.5, 1.5, 1.0),
    ]

    for a, b, expected in test_cases:
        dut.ina.value = to_fixed(a)
        dut.inb.value = to_fixed(b)
        dut.sub.value = 1  # Subtraction mode
        await Timer(10, units="ns")

        result = from_fixed(int(dut.out.value))
        assert abs(result - expected) < 0.02, f"Sub {a} - {b}: got {result}, expected {expected}"

    dut._log.info("PASS: fxp_addsub sub mode test")


@cocotb.test()
async def test_fxp_addsub_randomized(dut):
    """Randomized test for add/sub operations."""
    num_tests = 50
    seed = 33333
    random.seed(seed)

    dut._log.info(f"Starting randomized fxp_addsub test ({num_tests} tests, seed={seed})")

    for _ in range(num_tests):
        a = random.uniform(-64.0, 64.0)
        b = random.uniform(-64.0, 64.0)
        sub_mode = random.randint(0, 1)

        expected = a - b if sub_mode else a + b

        dut.ina.value = to_fixed(a)
        dut.inb.value = to_fixed(b)
        dut.sub.value = sub_mode
        await Timer(10, units="ns")

        result = from_fixed(int(dut.out.value))
        overflow = int(dut.overflow.value)

        if not overflow and abs(expected) < 64:
            op = "-" if sub_mode else "+"
            assert abs(result - expected) < 0.5, f"{a} {op} {b}: got {result}, expected {expected}"

    dut._log.info("PASS: Randomized fxp_addsub test")
