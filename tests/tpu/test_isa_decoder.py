"""
Tests for decoder.sv aligned with ISA documentation (docs/system.md)

ISA Format:
- MODE [63:62]: 0=VPU, 1=Systolic, 2=Vadd, 3=Halt
- ADDR_A [61:49]: Base address of input A
- ADDR_B [48:36]: Base address of input B  
- ADDR_OUT [35:23]: Base address of output
- For VPU: ADDR_CONST [22:10], OPCODE [9:0]
- For Systolic: LEN [22:0]

VPU Opcodes: ADD=0, SUB=1, RELU=2, MUL=3, RELU_DERIVATIVE=4
"""

import cocotb
from cocotb.triggers import Timer
import random


# ISA Mode values from docs/system.md
MODE_VPU = 0
MODE_SYSTOLIC = 1
MODE_VADD = 2
MODE_HALT = 3

# VPU Opcodes from docs/system.md
VPU_ADD = 0
VPU_SUB = 1
VPU_RELU = 2
VPU_MUL = 3
VPU_RELU_DERIV = 4


def encode_vpu_instruction(addr_a, addr_b, addr_out, addr_const, opcode):
    """Encode a VPU instruction per ISA spec."""
    instr = 0
    instr |= (MODE_VPU & 0x3) << 62         # MODE [63:62]
    instr |= (addr_a & 0x1FFF) << 49        # ADDR_A [61:49]
    instr |= (addr_b & 0x1FFF) << 36        # ADDR_B [48:36]
    instr |= (addr_out & 0x1FFF) << 23      # ADDR_OUT [35:23]
    instr |= (addr_const & 0x1FFF) << 10    # ADDR_CONST [22:10]
    instr |= (opcode & 0x3FF)               # OPCODE [9:0]
    return instr


def encode_systolic_instruction(addr_a, addr_b, addr_out, length):
    """Encode a Systolic instruction per ISA spec."""
    instr = 0
    instr |= (MODE_SYSTOLIC & 0x3) << 62    # MODE [63:62]
    instr |= (addr_a & 0x1FFF) << 49        # ADDR_A [61:49]
    instr |= (addr_b & 0x1FFF) << 36        # ADDR_B [48:36]
    instr |= (addr_out & 0x1FFF) << 23      # ADDR_OUT [35:23]
    instr |= (length & 0x7FFFFF)            # LEN [22:0]
    return instr


def encode_halt_instruction():
    """Encode a HALT instruction."""
    return (MODE_HALT & 0x3) << 62


@cocotb.test()
async def test_vpu_add_instruction(dut):
    """Test VPU ADD instruction decoding."""
    instr = encode_vpu_instruction(
        addr_a=0x100, addr_b=0x200, addr_out=0x300,
        addr_const=0x0, opcode=VPU_ADD
    )
    dut.instr_decode.value = instr
    await Timer(1, units="ns")
    
    assert int(dut.mode_decode.value) == MODE_VPU, "Mode should be VPU (0)"
    assert int(dut.addr_a_decode.value) == 0x100, "ADDR_A mismatch"
    assert int(dut.addr_b_decode.value) == 0x200, "ADDR_B mismatch"
    assert int(dut.addr_out_decode.value) == 0x300, "ADDR_OUT mismatch"
    assert int(dut.opcode_decode.value) == VPU_ADD, "Opcode should be ADD (0)"
    dut._log.info("PASS: VPU ADD instruction")


@cocotb.test()
async def test_vpu_sub_instruction(dut):
    """Test VPU SUB instruction decoding."""
    instr = encode_vpu_instruction(
        addr_a=0x400, addr_b=0x500, addr_out=0x600,
        addr_const=0x0, opcode=VPU_SUB
    )
    dut.instr_decode.value = instr
    await Timer(1, units="ns")
    
    assert int(dut.mode_decode.value) == MODE_VPU
    assert int(dut.opcode_decode.value) == VPU_SUB, "Opcode should be SUB (1)"
    dut._log.info("PASS: VPU SUB instruction")


@cocotb.test()
async def test_vpu_relu_instruction(dut):
    """Test VPU RELU instruction decoding."""
    # RELU uses addr_const for Zero_addr per quickstart.md
    instr = encode_vpu_instruction(
        addr_a=0x100, addr_b=0x0, addr_out=0x200,
        addr_const=0x50, opcode=VPU_RELU
    )
    dut.instr_decode.value = instr
    await Timer(1, units="ns")
    
    assert int(dut.mode_decode.value) == MODE_VPU
    assert int(dut.opcode_decode.value) == VPU_RELU, "Opcode should be RELU (2)"
    assert int(dut.addr_const_decode.value) == 0x50, "ADDR_CONST (Zero_addr) mismatch"
    dut._log.info("PASS: VPU RELU instruction")


@cocotb.test()
async def test_vpu_mul_instruction(dut):
    """Test VPU MUL instruction decoding."""
    instr = encode_vpu_instruction(
        addr_a=0x100, addr_b=0x200, addr_out=0x300,
        addr_const=0x0, opcode=VPU_MUL
    )
    dut.instr_decode.value = instr
    await Timer(1, units="ns")
    
    assert int(dut.mode_decode.value) == MODE_VPU
    assert int(dut.opcode_decode.value) == VPU_MUL, "Opcode should be MUL (3)"
    dut._log.info("PASS: VPU MUL instruction")


@cocotb.test()
async def test_vpu_relu_derivative_instruction(dut):
    """Test VPU RELU_DERIVATIVE instruction decoding."""
    instr = encode_vpu_instruction(
        addr_a=0x100, addr_b=0x0, addr_out=0x200,
        addr_const=0x50, opcode=VPU_RELU_DERIV
    )
    dut.instr_decode.value = instr
    await Timer(1, units="ns")
    
    assert int(dut.mode_decode.value) == MODE_VPU
    assert int(dut.opcode_decode.value) == VPU_RELU_DERIV, "Opcode should be RELU_DERIV (4)"
    dut._log.info("PASS: VPU RELU_DERIVATIVE instruction")


@cocotb.test()
async def test_systolic_instruction(dut):
    """Test Systolic (matmul) instruction decoding."""
    instr = encode_systolic_instruction(
        addr_a=0x000,   # Weight matrix base
        addr_b=0x100,   # Input matrix base
        addr_out=0x200, # Output matrix base
        length=16       # 4x4 = 16 elements (not used currently but encoded)
    )
    dut.instr_decode.value = instr
    await Timer(1, units="ns")
    
    assert int(dut.mode_decode.value) == MODE_SYSTOLIC, "Mode should be Systolic (1)"
    assert int(dut.addr_a_decode.value) == 0x000, "ADDR_A (weights) mismatch"
    assert int(dut.addr_b_decode.value) == 0x100, "ADDR_B (inputs) mismatch"
    assert int(dut.addr_out_decode.value) == 0x200, "ADDR_OUT mismatch"
    dut._log.info("PASS: Systolic instruction")


@cocotb.test()
async def test_halt_instruction(dut):
    """Test HALT instruction decoding (required to end all instruction sets)."""
    instr = encode_halt_instruction()
    dut.instr_decode.value = instr
    await Timer(1, units="ns")
    
    assert int(dut.mode_decode.value) == MODE_HALT, "Mode should be HALT (3)"
    dut._log.info("PASS: HALT instruction")


@cocotb.test()
async def test_vadd_instruction(dut):
    """Test VADD instruction (test compute unit)."""
    instr = (MODE_VADD & 0x3) << 62
    instr |= (0x100 & 0x1FFF) << 49  # ADDR_A
    instr |= (0x200 & 0x1FFF) << 36  # ADDR_B
    instr |= (0x300 & 0x1FFF) << 23  # ADDR_OUT
    
    dut.instr_decode.value = instr
    await Timer(1, units="ns")
    
    assert int(dut.mode_decode.value) == MODE_VADD, "Mode should be VADD (2)"
    dut._log.info("PASS: VADD instruction")


@cocotb.test()
async def test_instruction_sequence(dut):
    """Test a typical instruction sequence: load -> matmul -> store (simulated via decode)."""
    # Instruction 1: Systolic matmul
    instr1 = encode_systolic_instruction(0x000, 0x010, 0x020, 16)
    dut.instr_decode.value = instr1
    await Timer(1, units="ns")
    assert int(dut.mode_decode.value) == MODE_SYSTOLIC
    
    # Instruction 2: VPU RELU on result
    instr2 = encode_vpu_instruction(0x020, 0x0, 0x030, 0x0, VPU_RELU)
    dut.instr_decode.value = instr2
    await Timer(1, units="ns")
    assert int(dut.mode_decode.value) == MODE_VPU
    assert int(dut.opcode_decode.value) == VPU_RELU
    
    # Instruction 3: VPU ADD bias
    instr3 = encode_vpu_instruction(0x030, 0x040, 0x050, 0x0, VPU_ADD)
    dut.instr_decode.value = instr3
    await Timer(1, units="ns")
    assert int(dut.mode_decode.value) == MODE_VPU
    assert int(dut.opcode_decode.value) == VPU_ADD
    
    # Instruction 4: HALT
    instr4 = encode_halt_instruction()
    dut.instr_decode.value = instr4
    await Timer(1, units="ns")
    assert int(dut.mode_decode.value) == MODE_HALT
    
    dut._log.info("PASS: Instruction sequence test")


@cocotb.test()
async def test_full_address_range(dut):
    """Test maximum address values (13-bit addresses = 8192 words for BRAM)."""
    max_addr = 0x1FFF  # 13-bit max
    
    instr = encode_systolic_instruction(max_addr, max_addr, max_addr, 0)
    dut.instr_decode.value = instr
    await Timer(1, units="ns")
    
    assert int(dut.addr_a_decode.value) == max_addr, "Max ADDR_A failed"
    assert int(dut.addr_b_decode.value) == max_addr, "Max ADDR_B failed"
    assert int(dut.addr_out_decode.value) == max_addr, "Max ADDR_OUT failed"
    dut._log.info("PASS: Full address range test")
