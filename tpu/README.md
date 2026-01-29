# Mini-TPU Core RTL

This directory contains the SystemVerilog source code for the Mini-TPU core compute engine.

## Directory Structure

- `tpu_top_v6.sv`: Top-level wrapper (original, optimized for FPGA AXI).
- `bram_top.sv`: Memory subsystem wrapper.
- `mem_wrapper.sv`: **[NEW]** Portable memory wrapper for cross-platform support.
- `compute_core.sv`: Main control logic for Systolic, Vector, and Scalar units.
- `systolic.sv`: 8x8 Systolic Array implementation (`ws` = Weight Stationary).
- `pe.sv`: Processing Element with MAC units.

## Memory Architecture

The design uses a unified memory abstraction (`mem_wrapper.sv`) to support both FPGA and ASIC flows without code changes.

### FPGA Target (Xilinx UltraScale+/Versal)
Define `TARGET_FPGA` during synthesis.
- Infers True Dual-Port **BRAM** or **URAM** using `(* ram_style *)`.
- No Xilinx IP (`blk_mem_gen`) dependency.
- Portability across Alveo U280, Versal V80, VCK5000, and Zynq.

### ASIC Target (Tiny Tapeout / IHP SG13G2)
Define `TARGET_ASIC` during synthesis.
- Uses behavioral SRAM models for simulation.
- Maps to `sram_blackbox` or external SPI controller in the ASIC top-level wrapper.
- Requires external memory (SPI/QSPI) for large data backing.

## Interfaces

The core exposes a stream-like interface for data ingestion and a control interface for instruction dispatch.

| Interface | Type | Description |
|-----------|------|-------------|
| **Control** | Register | Memory mapped registers for start/stop/status |
| **Stream In** | AXIS-like | Data loading into Scratchpad |
| **Stream Out** | AXIS-like | Results readback to Host |

## Simulation

To run tests, see `tests/` directory.

## Status Log (2026-01-28)
- **Architecture Update**: Replaced `blk_mem_gen` hard IP with `mem_wrapper` for portable BRAM inference.
- **Portability**: Codebase now supports generic FPGA targets (U280/V80/Zynq) and behavioral simulation for ASIC without modifying RTL.
- **Refactoring**: `tpu_top_v6` and `bram_top` validated to check for IP dependencies.
