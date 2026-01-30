"""
PYNQ Host Interface for Mini-TPU

This module provides a reusable hardware abstraction layer for interacting
with the Mini-TPU on PYNQ-based FPGA boards.
"""

import time
import numpy as np

try:
    from pynq import Overlay, allocate
except ImportError:
    # Allow import on non-PYNQ systems for development
    Overlay = None
    allocate = None


# TPU Register addresses (AXI-Lite)
REG_ADDR = {
    "tpu_mode":     0x00,
    "instr_ready":  0x04,
    "stream_ready": 0x08,
    "addr_ram":     0x0C,
    "length":       0x18,
}

# TPU operation modes
class TpuMode:
    IDLE       = 0
    WRITE_BRAM = 1
    READ_BRAM  = 2
    COMPUTE    = 3
    WRITE_IRAM = 4


class TpuDriver:
    """Driver class for Mini-TPU hardware interface."""
    
    def __init__(self, bitstream_path: str):
        """
        Initialize TPU driver with the specified bitstream.
        
        Args:
            bitstream_path: Path to .bit file (expects .hwh in same directory)
        """
        if Overlay is None:
            raise RuntimeError("pynq library not available - must run on PYNQ board")
        
        self.overlay = Overlay(bitstream_path)
        self.overlay.download()
        
        self.dma = self.overlay.axi_dma_0
        self.ctrl = self.overlay.tpu_top_v6_0
        self.mmio = self.ctrl.mmio
    
    def wait_for_flag(self, name: str, expected: int = 1, poll_delay: float = 0.001):
        """Wait for a TPU status flag to reach expected value."""
        offset = REG_ADDR[name]
        while self.mmio.read(offset) != expected:
            time.sleep(poll_delay)
    
    def write_bram(self, addr: int, values: np.ndarray):
        """
        Write data to TPU BRAM.
        
        Args:
            addr: Base address in BRAM
            values: numpy array of float32 values to write
        """
        values = np.asarray(values, dtype=np.float32).reshape(-1)
        in_buf = allocate(shape=values.shape, dtype=np.int64)
        value_bits = values.view(np.uint32)
        
        self.wait_for_flag("instr_ready", 1)
        self.mmio.write(REG_ADDR["addr_ram"], addr)
        self.mmio.write(REG_ADDR["length"], values.size)
        self.mmio.write(REG_ADDR["tpu_mode"], TpuMode.WRITE_BRAM)
        
        self.wait_for_flag("stream_ready", 1)
        in_buf[:] = value_bits.astype(np.uint64)
        self.dma.sendchannel.transfer(in_buf)
        self.dma.sendchannel.wait()
        self.wait_for_flag("instr_ready", 1)
        
        in_buf.freebuffer()
        self.mmio.write(REG_ADDR["tpu_mode"], TpuMode.IDLE)
    
    def read_bram(self, addr: int, length: int) -> np.ndarray:
        """
        Read data from TPU BRAM.
        
        Args:
            addr: Base address in BRAM
            length: Number of float32 values to read
            
        Returns:
            numpy array of float32 values
        """
        out_buf = allocate(shape=(length,), dtype=np.float32)
        
        self.wait_for_flag("instr_ready", 1)
        self.mmio.write(REG_ADDR["addr_ram"], addr)
        self.mmio.write(REG_ADDR["length"], length)
        self.mmio.write(REG_ADDR["tpu_mode"], TpuMode.READ_BRAM)
        
        self.dma.recvchannel.transfer(out_buf)
        self.dma.recvchannel.wait()
        
        self.wait_for_flag("instr_ready", 1)
        self.mmio.write(REG_ADDR["tpu_mode"], TpuMode.IDLE)
        
        arr = np.copy(out_buf)
        out_buf.freebuffer()
        return arr
    
    def write_instructions(self, instructions: np.ndarray, base_addr: int = 0):
        """
        Write instruction memory (IRAM).
        
        Args:
            instructions: numpy array of uint64 instruction words
            base_addr: Base address for instruction memory
        """
        instructions = np.asarray(instructions, dtype=np.uint64)
        instr_buf = allocate(shape=instructions.shape, dtype=np.uint64)
        
        self.wait_for_flag("instr_ready", 1)
        self.mmio.write(REG_ADDR["addr_ram"], base_addr)
        self.mmio.write(REG_ADDR["length"], len(instructions))
        self.mmio.write(REG_ADDR["tpu_mode"], TpuMode.WRITE_IRAM)
        
        self.wait_for_flag("stream_ready", 1)
        instr_buf[:] = instructions
        self.dma.sendchannel.transfer(instr_buf)
        self.dma.sendchannel.wait()
        self.wait_for_flag("instr_ready", 1)
        
        self.mmio.write(REG_ADDR["tpu_mode"], TpuMode.IDLE)
        instr_buf.freebuffer()
    
    def compute(self):
        """Execute the loaded instruction program."""
        self.wait_for_flag("instr_ready", 1)
        self.mmio.write(REG_ADDR["tpu_mode"], TpuMode.COMPUTE)
        self.wait_for_flag("instr_ready", 1)
        self.mmio.write(REG_ADDR["tpu_mode"], TpuMode.IDLE)


def load_instructions(filepath: str) -> np.ndarray:
    """
    Load instruction file (hex format, one instruction per line).
    
    Args:
        filepath: Path to instruction file
        
    Returns:
        numpy array of uint64 instructions
    """
    instructions = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line:
                instructions.append(int(line, 16))
    return np.array(instructions, dtype=np.uint64)
