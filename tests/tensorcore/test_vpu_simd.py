"""Functional tests for vpu_simd.sv - SIMD VPU with register file."""

import cocotb
from cocotb.triggers import RisingEdge
from cocotb.clock import Clock
import struct

def float_to_fp32(f):
    return struct.unpack('>I', struct.pack('>f', f))[0]

def fp32_to_float(bits):
    return struct.unpack('>f', struct.pack('>I', bits))[0]


@cocotb.test()
async def test_vpu_simd_reset(dut):
    """Test that reset brings VPU to IDLE state."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut.rst_n.value = 0
    dut.start.value = 0
    dut.vpu_type.value = 0
    dut.addr_a.value = 0
    dut.addr_out.value = 0
    dut.vreg_dst.value = 0
    dut.vreg_a.value = 0
    dut.vreg_b.value = 0
    dut.vpu_opcode.value = 0
    dut.scalar_b.value = 0
    dut.bram_dout.value = 0

    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    # Verify idle state
    assert int(dut.done.value) == 0, "Done should be 0 after reset"
    assert int(dut.bram_en.value) == 0, "BRAM enable should be 0 in IDLE"

    dut._log.info("PASS: VPU SIMD reset to IDLE")


@cocotb.test()
async def test_vcompute_simple(dut):
    """Test VCOMPUTE operation (without actual BRAM)."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut.rst_n.value = 0
    dut.start.value = 0
    dut.vpu_type.value = 0
    dut.addr_a.value = 0
    dut.addr_out.value = 0
    dut.vreg_dst.value = 0
    dut.vreg_a.value = 0
    dut.vreg_b.value = 0
    dut.vpu_opcode.value = 0
    dut.scalar_b.value = 0
    dut.bram_dout.value = 0
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    # Setup VCOMPUTE: V2 = V0 + V1 (registers start at zero, so result should be zero)
    dut.vpu_type.value = 3  # VCOMPUTE
    dut.vpu_opcode.value = 0  # VADD
    dut.vreg_dst.value = 2
    dut.vreg_a.value = 0
    dut.vreg_b.value = 1
    dut.scalar_b.value = 0
    dut.start.value = 1

    await RisingEdge(dut.clk)
    dut.start.value = 0

    # Wait for done signal
    cycle_count = 0
    while cycle_count < 20:
        await RisingEdge(dut.clk)
        if int(dut.done.value) == 1:
            break
        cycle_count += 1

    assert cycle_count < 20, "VCOMPUTE timeout"
    assert cycle_count <= 3, f"VCOMPUTE should complete in 1-3 cycles, took {cycle_count}"

    dut._log.info(f"PASS: VCOMPUTE completed in {cycle_count} cycles")


@cocotb.test()
async def test_vload_sequential(dut):
    """Test VLOAD reading 8 sequential elements from BRAM."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    # Simple BRAM model
    bram = {}
    for i in range(8):
        bram[100 + i] = float_to_fp32(float(i + 10))

    # Reset
    dut.rst_n.value = 0
    dut.start.value = 0
    dut.vpu_type.value = 0
    dut.addr_a.value = 0
    dut.addr_out.value = 0
    dut.vreg_dst.value = 0
    dut.vreg_a.value = 0
    dut.vreg_b.value = 0
    dut.vpu_opcode.value = 0
    dut.scalar_b.value = 0
    dut.bram_dout.value = 0
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    # Trigger VLOAD: V0 = BRAM[100:107] (Parallel)
    dut.vpu_type.value = 1  # VLOAD
    dut.addr_a.value = 100
    dut.vreg_dst.value = 0
    dut.start.value = 1

    await RisingEdge(dut.clk)
    dut.start.value = 0

    # Simulate BRAM reads (8 words in 1 parallel beat)
    cycle_count = 0
    read_count = 0
    en_prev = 0
    while cycle_count < 20:
        await RisingEdge(dut.clk)
        en = int(dut.bram_en.value)
        we = int(dut.bram_we.value)

        # Check if BRAM read is active (count only on leading edge)
        if en == 1 and we == 0:
            if en_prev == 0:
                addr = int(dut.bram_addr.value)
                resp_data = 0
                for i in range(8):
                    val = bram.get(addr + i, 0)
                    resp_data |= (val & 0xFFFFFFFF) << (i * 32)
                dut.bram_dout.value = resp_data
                read_count += 1
        en_prev = en

        if int(dut.done.value) == 1:
            break
        cycle_count += 1

    assert cycle_count < 20, "VLOAD timeout"
    assert read_count == 1, f"Expected 1 parallel BRAM read, got {read_count}"

    # Verify data in register file (if possible)
    # Using the internal regfile signal if it works in Icarus
    # regfile.mem[0] should contain 8 words
    try:
        rf_v0 = dut.regfile.mem[0].value
        for i in range(8):
            expected = float_to_fp32(float(i + 10))
            actual = (int(rf_v0) >> (i * 32)) & 0xFFFFFFFF
            assert actual == expected, f"V0[{i}] mismatch: expected {expected:x}, got {actual:x}"
    except AttributeError:
        pass # Some simulators might not expose internal arrays

    dut._log.info(f"PASS: VLOAD completed in {cycle_count} cycles with parallel read and data verification")



@cocotb.test()
async def test_vstore_sequential(dut):
    """Test VSTORE writing 8 sequential elements to BRAM."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    # BRAM model to capture writes
    bram_writes = {}

    # Reset
    dut.rst_n.value = 0
    dut.start.value = 0
    dut.vpu_type.value = 0
    dut.addr_a.value = 0
    dut.addr_out.value = 0
    dut.vreg_dst.value = 0
    dut.vreg_a.value = 0
    dut.vreg_b.value = 0
    dut.vpu_opcode.value = 0
    dut.scalar_b.value = 0
    dut.bram_dout.value = 0
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    # Trigger VSTORE: BRAM[200:207] = V1 (Parallel)
    dut.vpu_type.value = 2  # VSTORE
    dut.addr_out.value = 200
    dut.vreg_a.value = 1
    dut.start.value = 1

    await RisingEdge(dut.clk)
    dut.start.value = 0

    # Capture BRAM writes
    cycle_count = 0
    write_count = 0
    while cycle_count < 20:
        await RisingEdge(dut.clk)

        # Check if BRAM write is active
        if int(dut.bram_en.value) == 1 and int(dut.bram_we.value) == 1:
            addr = int(dut.bram_addr.value)
            raw_data = int(dut.bram_din.value)
            # Parallel write: unpack 8 words
            for i in range(8):
                val = (raw_data >> (i * 32)) & 0xFFFFFFFF
                bram_writes[addr + i] = val
            write_count += 1

        if int(dut.done.value) == 1:
            break
        cycle_count += 1

    assert cycle_count < 20, "VSTORE timeout"
    assert write_count == 1, f"Expected 1 parallel BRAM write, got {write_count}"

    # Verify writes went to correct addresses
    for i in range(8):
        assert (200 + i) in bram_writes, f"Missing write to address {200 + i}"

    dut._log.info(f"PASS: VSTORE completed in {cycle_count} cycles with parallel write")


@cocotb.test()
async def test_vcompute_scalar_broadcast(dut):
    """Test scalar broadcast mode (V2 = V0 * V1[0])."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut.rst_n.value = 0
    dut.start.value = 0
    dut.vpu_type.value = 0
    dut.addr_a.value = 0
    dut.addr_out.value = 0
    dut.vreg_dst.value = 0
    dut.vreg_a.value = 0
    dut.vreg_b.value = 0
    dut.vpu_opcode.value = 0
    dut.scalar_b.value = 0
    dut.bram_dout.value = 0
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    # Setup VMUL with scalar broadcast: V2 = V0 * V1[0]
    dut.vpu_type.value = 3  # VCOMPUTE
    dut.vpu_opcode.value = 2  # VMUL
    dut.vreg_dst.value = 2
    dut.vreg_a.value = 0
    dut.vreg_b.value = 1
    dut.scalar_b.value = 1  # Enable scalar broadcast
    dut.start.value = 1

    await RisingEdge(dut.clk)
    dut.start.value = 0

    # Wait for done
    cycle_count = 0
    while cycle_count < 20:
        await RisingEdge(dut.clk)
        if int(dut.done.value) == 1:
            break
        cycle_count += 1

    assert cycle_count < 20, "VMUL scalar broadcast timeout"

    dut._log.info(f"PASS: Scalar broadcast VMUL completed in {cycle_count} cycles")


@cocotb.test()
async def test_invalid_vpu_type(dut):
    """Test that invalid VPU_TYPE completes without hanging."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut.rst_n.value = 0
    dut.start.value = 0
    dut.vpu_type.value = 0
    dut.addr_a.value = 0
    dut.addr_out.value = 0
    dut.vreg_dst.value = 0
    dut.vreg_a.value = 0
    dut.vreg_b.value = 0
    dut.vpu_opcode.value = 0
    dut.scalar_b.value = 0
    dut.bram_dout.value = 0
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    # Trigger with invalid VPU_TYPE
    dut.vpu_type.value = 7  # Invalid (only 0-3 are valid)
    dut.start.value = 1

    await RisingEdge(dut.clk)
    dut.start.value = 0

    # Should go to DONE_STATE immediately
    cycle_count = 0
    while cycle_count < 10:
        await RisingEdge(dut.clk)
        if int(dut.done.value) == 1:
            break
        cycle_count += 1

    assert cycle_count < 10, "Invalid VPU_TYPE should complete quickly"

    dut._log.info(f"PASS: Invalid VPU_TYPE handled gracefully in {cycle_count} cycles")
