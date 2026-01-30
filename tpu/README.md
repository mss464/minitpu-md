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

The core RTL (`tpu_top_v6.sv`) implements AXI interfaces in **hand-coded Verilog** — no vendor IP dependencies.

| Interface | Type | Width | Implementation |
|-----------|------|-------|----------------|
| **S00_AXI** | AXI4-Lite Slave | 32-bit data | `tpu_top_v4_slave_lite_v1_0_S00_AXI.v` |
| **S00_AXIS** | AXI4-Stream Slave | 64-bit data | `tpu_top_v4_slave_stream_V1_0_S00_AXIS.v` |
| **M00_AXIS** | AXI4-Stream Master | 32-bit data | `tpu_top_v4_master_stream_V1_0_M00_AXIS.v` |

> [!IMPORTANT]
> **What's NOT in this directory:** The **DMA controller** that drives the AXI-Stream interfaces is a **Xilinx IP** (`axi_dma:7.1`) instantiated in `fpga/build_bd_bitstream.tcl`. For ASIC, `asic/tpu_core.sv` replaces these with simple valid/ready FIFO interfaces.

### Portability Note
- ✅ All `.sv`/`.v` files in `tpu/` are vendor-agnostic
- ❌ A working system also requires a DMA controller (Xilinx IP or custom)

## Simulation

To run tests, see `tests/` directory.

## Status Log (2026-01-28)
- **Architecture Update**: Replaced `blk_mem_gen` hard IP with `mem_wrapper` for portable BRAM inference.
- **Portability**: Codebase now supports generic FPGA targets (U280/V80/Zynq) and behavioral simulation for ASIC without modifying RTL.
- **Refactoring**: `tpu_top_v6` and `bram_top` validated to check for IP dependencies.

## Status Log (2026-01-29)
- **BRAM vs Inferred RAM**: `bram_top.sv` changed from `blk_mem_gen_0` (origin/main) to `mem_wrapper` with `RAM_STYLE("block")`; instruction RAM in `tpu_top_v6.sv` changed from `blk_mem_gen_1` to `mem_wrapper` with `RAM_STYLE("block")`. Legacy `blk_mem_gen` behavior (user-reported): **write-first**, **2-cycle read latency**, **pipelined sequential reads** (now modeled in `mem_wrapper.sv`).
- **Instruction Fetch**: `tpu_top_v6.sv` retains origin/main fetch sequencing (no added pre-fetch on compute entry); timing is expected to match legacy BRAM via `mem_wrapper` latency.
