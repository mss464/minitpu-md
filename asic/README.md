# Mini-TPU ASIC Flow (IHP SG13G2)

**Status**: ✅ Physical Design Complete (Phase 1 GDS Generated)

## Project Context
**Objective**: Establish a baseline digital implementation flow for the `mini-tpu` design targeting the IHP SG13G2 130nm BiCMOS Open Source PDK.

**Phase 1 Goal**: Achieve a clean GDSII layout for the core compute fabric (`tpu_core`) with:
- **Frequency**: 50 MHz target.
- **Scope**: Core logic only (no AXI/Xilinx deps).
- **Memory strategy**: Blackboxed SRAMs (replacing FPGA-specific BRAMs).
- **Quality**: Zero DRC/Antenna violations.

## Phase 1 Progress Report (Jan 28, 2026)

Successfully established a complete RTL-to-GDS flow using OpenROAD-flow-scripts (ORFS). All design stages from synthesis to GDS generation have passed.

### Key Metrics
| Metric | Value | Notes |
|:---|:---|:---|
| **Technology** | IHP SG13G2 (130nm) | Open-source PDK |
| **Clock Frequency** | 50 MHz (20ns) | Met Setup/Hold |
| **Die Area** | 2.43 mm² | 40% Target Utilization |
| **Std Cell Utilization** | ~27% | Final placement density |
| **Total Cells** | ~9,300 | Excluding fill cells |
| **Routing** | Clean | 1M+ vias, 0 violations |
| **SRAM** | Blackboxed | 8192x32 (Data) + 256x64 (Instr) |

## SRAM Macro Banking
- Current: Behavioral SRAM (8192x32)
- Future: Bank 4× IHP 2048x64 macros with address decode logic

## AXI Interface Strategy
- Options: Keep AXI-Stream, simplify to valid/ready, WISBane
- Decision deferred to Phase 2

## Test Infrastructure
- Scan chain insertion (DFT)
- JTAG boundary scan
- BIST for SRAMs

## IO Pad Ring
- IHP IO cell integration
- Padring generation
- ESD protection

## Status Log (2026-01-28)
- **Tiny Tapeout Adaptation**: Started implementation of SPI-based I/O bridge (`spi_bridge.sv`) to fit 24-pin constraint.
- **Memory Strategy**: Decision made to use External SPI SRAM (e.g., 23LC1024) for data storage, bypassing on-die size limits.
- **Next Steps**: Complete SPI Bridge FSM, implement External Memory Controller, and wrap in `tt_um_tpu`.

### Flow Stages & Results
1.  **Synthesis (Yosys)**: ✅ Completed in 8m 26s.
    *   **Fix**: Created ASIC-compatible versions of 7 core files to resolve SystemVerilog compatibility and latch inference issues.
    *   **Strategy**: Switched to "Blackbox" approach for SRAMs (`sram_8192x32`, `sram_256x64`) to bypass impractical synthesis times for behavioral memory.

2.  **Floorplan**: ✅ Completed in 56s.
    *   Utilization set to 40% (conservative).
    *   No macros placed (blackboxes will be handled later).

3.  **Placement**: ✅ Completed in 1m 46s.
    *   Utilization dropped to 26% after optimization.
    *   HPWL: ~4.25m um.

4.  **CTS (Clock Tree Synthesis)**: ✅ Completed in 1m 30s.
    *   Inserted 4,305 hold buffers.
    *   Timing met with 50MHz constraints.

5.  **Routing**: ✅ Completed in 37m 41s.
    *   **DRC Clean**: 0 net violations, 0 pin violations.
    *   **Antenna**: 0 violations.
    *   Layer usage: Metal1-Metal4 primarily used.

6.  **GDS Generation**: ✅ Completed in 12s.
    *   Final layout generated in `results/ihp-sg13g2/tpu_core/base/6_final.gds`.

### ASIC-Specific Modifications
To enable the flow, the following files were modified/created in `asic/src/`:
*   `tpu_core.sv`: Top-level wrapper stripping AXI/Xilinx IPs.
*   `bram_top.sv`: Fixed non-constant initialization.
*   `pe.sv`: Separated async reset from synchronous enable logic.
*   `fp32_add.sv` / `fp_adder.sv`: Replaced complex `for` loops with priority encoders to prevent latch inference.
*   `systolic_wrapper.sv`: Removed unsupported `function automatic`.
*   `sram_blackbox.sv`: New file defining blackbox modules for memories.

### Reproducing the Flow
Pre-requisite: Docker installed.

```bash
# 1. From project root, run the flow in Docker
docker run --rm -v $(pwd):/design -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -c "
    # Setup directories
    mkdir -p designs/src/tpu_core designs/ihp-sg13g2/tpu_core

    # Copy RTL (Base + ASIC fixes)
    cp /design/tpu/*.sv designs/src/tpu_core/
    cp /design/asic/src/*.sv designs/src/tpu_core/
    
    # Copy Config
    cp /design/asic/ihp-sg13g2/config.mk designs/ihp-sg13g2/tpu_core/
    cp /design/asic/ihp-sg13g2/constraint.sdc designs/ihp-sg13g2/tpu_core/

    # Run complete flow
    source ../env.sh
    make finish DESIGN_CONFIG=designs/ihp-sg13g2/tpu_core/config.mk
"
```

## Next Steps (Phase 2)
1.  **SRAM Macro Integration**: 
    *   Replace `sram_blackbox.sv` with hardened SRAM macros.
    *   Option A: Use IHP loaded macros (if available).
    *   Option B: Generate using OpenRAM.
2.  **IO Pad Ring**:
    *   Design a pad ring for the chip.
    *   Connect core signals to pads.
3.  **Timing Analysis**:
    *   Perform detailed STA with extracted parasitics.
    *   Close timing at higher frequencies if possible (>50MHz).
4.  **Verification**:
    *   Run GLs (Gate Level Simulation) to verify functionality of the synthesized netlist.
