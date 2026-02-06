# Implementation Plan - Memory & I/O Adaptation

## Goal Description
Adapt the `mini-tpu` memory subsystem and I/O interfaces to target **Tiny Tapeout** (ASIC) constraints while maintaining high-performance compatibility for **AMD FPGAs**. 
- **ASIC Constraints**: 24 GPIO pins, limited on-die memory (~1KB), 50MHz.
- **FPGA Goals**: Maximize bandwidth using BRAM/URAM, high frequency.

## User Review Required
> [!IMPORTANT]
> **External Memory Dependency**: For Tiny Tapeout, the design will strictly require an external SPI/QSPI SRAM (e.g., 23LC1024 or APS6404L) for meaningful workloads, as on-die memory is insufficient (1KB vs 262KB required).

> [!WARNING]
> **Performance Impact**: Serializing the parallel I/O interface to SPI will significantly reduce data ingest/egress speed on the ASIC target compared to the FPGA version.

> [!NOTE]
> **FPGA Compatibility**: The FPGA flow will remain functionally unchanged. The new `mem_wrapper` will resolve to standard inferred BRAMs (using `(* ram_style = "block" *)`) when `TARGET_FPGA` is defined. This allows the **exact same RTL** to target all 4 disparate FPGA models (Alveo U280, Versal V80, VCK5000, Zynq US+) without regenerating `blk_mem_gen` IP cores for each architecture.

## Proposed Changes

### Memory Subsystem (`tpu/src/mem_wrapper.sv`)
Create a new `mem_wrapper` module to replace the family-dependent `blk_mem_gen` IP.

#### [NEW] [mem_wrapper.sv](file:///home/sk3463/main/projects/mini-tpu/tpu/mem_wrapper.sv)
- **Parameters**: `DATA_WIDTH`, `ADDR_WIDTH`, `DEPTH`, `RAM_STYLE`.
- **Ports**: Dual-port interface (or pseudo-dual for IHP macros).
- **Implementation Details**:
  - `TARGET_FPGA`: Infers BRAM/URAM using `(* ram_style *)` attributes.
  - `TARGET_ASIC`: Instantiates `RM_IHPSG13` macros or behavioral models for external memory controller integration.
  - Handles read-during-write behavior differences.

### I/O Interface (`asic/src/spi_bridge.sv`)
Implement a serialization layer for the 24-pin limit.

#### [NEW] [spi_bridge.sv](file:///home/sk3463/main/projects/mini-tpu/asic/src/spi_bridge.sv)
- **Role**: Slave SPI interface to receive commands/data from host (RP2040).
- **Protocol**: 
  - 8-bit Opcode (Write Config, Write Instr, Write Data, Read Data, Run).
  - Address/Length fields.
  - Data streaming.

### External Memory Controller (`asic/src/ext_mem_ctrl.sv`)
#### [NEW] [ext_mem_ctrl.sv](file:///home/sk3463/main/projects/mini-tpu/asic/src/ext_mem_ctrl.sv)
- **Role**: Master SPI/QSPI interface to talk to external SRAM/PSRAM.
- **Features**: 
  - Arbitrates between DMA (loading data) and TensorCore (compute access).
  - Cache/Prefetch lines? (Future optimization).

### Top Level Integration (`asic/src/tt_um_tpu.sv`)
#### [NEW] [tt_um_tpu.sv](file:///home/sk3463/main/projects/mini-tpu/asic/src/tt_um_tpu.sv)
- **Tiny Tapeout Standard Wrapper**: Matches `tt_um_` template.
- **Pinout**:
  - `ui_in`: SPI Slave (MOSI, SCLK, CS, etc.) + Reset/Clk.
  - `uo_out`: SPI Slave MISO + Status irqs.
  - `uio`: External Memory Bus (SPI/QSPI to RAM chip).

## Verification Plan

### Automated Tests
1. **Module Level**:
   - `test_mem_wrapper`: Verify inference in Vivado and behavioral correctness for ASIC.
   - `test_spi_bridge`: Verify protocol decoding and throughput.
2. **System Level**:
   - `test_tt_tpu`: Full testbench driving the `tt_um_tpu` top level with SPI signals, simulating external memory latency.

### Manual Verification
- **Synthesis check**: Verify 0 latches and correct BRAM inference in Vivado.
- **OpenLANE check**: Run through Tiny Tapeout flow to check area/utilization (approximate).
