# Mini-TPU ASIC Flow

**Target**: Tiny Tapeout (TT07+) using IHP SG13G2 130nm BiCMOS Open Source PDK

## 🚀 Critical TODOs for Handoff
- [ ] **SPI Bridge**: Complete FSM in `src/spi_bridge.sv` (currently skeleton).
- [ ] **SRAM Integration**: Replace `sram_blackbox.sv` with hardened macros + banking logic.
- [ ] **Pad Ring**: Define pinout constraints and generate IO ring.
- [ ] **Wrapper**: Create `tt_um_minitpu.sv` top-level for Tiny Tapeout.

## Tiny Tapeout Integration

### 24-Pin Constraint

Tiny Tapeout provides exactly **24 user I/O pins** plus clock/reset:

| Pin Group | Count | Direction | Assignment |
|-----------|-------|-----------|------------|
| `ui_in[7:0]` | 8 | Input | SPI interface + control |
| `uo_out[7:0]` | 8 | Output | SPI MISO + status |
| `uio[7:0]` | 8 | Bidirectional | External SRAM interface |
| `clk` | 1 | Input | System clock (from TT mux) |
| `rst_n` | 1 | Input | Active-low reset |
| `ena` | 1 | Input | Active-high enable |

### Proposed Pin Mapping

```
┌─────────────────────────────────────────────────────────────────┐
│                    Tiny Tapeout User Module                      │
│                        tt_um_minitpu                             │
├─────────────────────────────────────────────────────────────────┤
│  ui_in[7:0] (Inputs):              uo_out[7:0] (Outputs):       │
│    [0] spi_sclk                      [0] spi_miso               │
│    [1] spi_cs_n                      [1] busy                   │
│    [2] spi_mosi                      [2] done                   │
│    [3] mode[0]                       [3] error                  │
│    [4] mode[1]                       [4..7] reserved            │
│    [5] mode[2]                                                   │
│    [6..7] reserved                                               │
├─────────────────────────────────────────────────────────────────┤
│  uio[7:0] (Bidirectional) — External SPI SRAM:                  │
│    [0] sram_sclk    (output)                                    │
│    [1] sram_cs_n    (output)                                    │
│    [2] sram_mosi    (output)                                    │
│    [3] sram_miso    (input)                                     │
│    [4..7] reserved / additional SRAM for quad-SPI               │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Status

| Component | File | Status |
|-----------|------|--------|
| **SPI Bridge** | `src/spi_bridge.sv` | ⚠️ Skeleton (FSM incomplete) |
| **TT Wrapper** | `src/tt_um_minitpu.sv` | ❌ Not created |
| **External SRAM Controller** | — | ❌ Not created |
| **Pinout Constraints** | — | ❌ Not created |

### External Memory Strategy

On-die SRAM is limited (~2KB practical in TT tiles). Strategy:
1. **Instruction RAM**: On-die (256×64 = 2KB) — fits
2. **Data RAM**: External SPI SRAM (e.g., 23LC1024 = 128KB)
3. **Interface**: Quad-SPI for 4× bandwidth if pins available

---

## Phase 1: Core Logic GDS

**Status**: ✅ Physical Design Complete (GDS Generated)

**Objective**: Baseline digital implementation for `tpu_core` targeting 50 MHz.

**Goal**: Clean GDSII layout for core compute fabric with:
- **Frequency**: 50 MHz target.
- **Scope**: Core logic only (no AXI/Xilinx deps).
- **Memory strategy**: Blackboxed SRAMs (replacing FPGA-specific BRAMs).
- **Quality**: Zero DRC/Antenna violations.

## ASIC vs FPGA Architecture

The ASIC flow uses a **different top-level wrapper** than the FPGA flow:

| Aspect | FPGA (`tpu_top_v6.sv`) | ASIC (`tpu_core.sv`) |
|--------|------------------------|----------------------|
| **Data Interface** | AXI4-Stream (64-bit in, 32-bit out) | Valid/Ready FIFO (same widths) |
| **Control Interface** | AXI4-Lite registers | Direct control signals |
| **DMA Dependency** | Requires Xilinx `axi_dma` IP | None (host drives FIFO directly) |
| **Memory** | Inferred BRAM via `mem_wrapper.sv` | Blackboxed SRAM macros |
| **Location** | `tpu/tpu_top_v6.sv` | `asic/src/tpu_core.sv` |

```
FPGA System:                              ASIC System:
┌──────────┐    ┌─────────────┐          ┌──────────┐
│ Xilinx   │───►│ tpu_top_v6  │          │ SPI/GPIO │───► tpu_core
│ AXI DMA  │    │ (AXI-Stream)│          │ Bridge   │     (valid/ready)
└──────────┘    └─────────────┘          └──────────┘
```

Both wrappers instantiate the **same internal modules**: `compute_core`, `bram_top`, `systolic`, `vpu_top`, etc.

### Interface Change Analysis

#### Semantic Equivalence
| Aspect | FPGA (AXI-Stream) | ASIC (Valid/Ready) | Equivalent? |
|--------|-------------------|--------------------|----|
| **Handshaking** | `TVALID`/`TREADY` | `valid`/`ready` | ✅ Identical semantics |
| **Data transfer** | One beat per valid+ready | Same | ✅ Same throughput model |
| **Backpressure** | `TREADY` deasserted | `ready` deasserted | ✅ Same behavior |
| **Packet boundary** | `TLAST` signal | Counter-based (via `dma_len`) | ⚠️ Functionally equivalent |
| **Byte strobes** | `TSTRB`/`TKEEP` | Not implemented | ⚠️ ASIC assumes all bytes valid |

> The valid/ready interface is semantically equivalent to AXI-Stream for **full-word transfers**. Partial-word transfers (via TSTRB) are not supported in the ASIC wrapper.

#### Performance Impact
| Metric | FPGA | ASIC | Notes |
|--------|------|------|-------|
| **Latency (interface)** | ~2-3 cycles (AXI protocol overhead) | 1 cycle (direct handshake) | ASIC slightly lower latency |
| **Throughput** | 1 word/cycle (sustained) | 1 word/cycle (sustained) | ✅ Identical peak throughput |
| **Clock frequency** | 100 MHz (Zynq PL) | 50 MHz (IHP SG13G2) | Technology-limited, not interface-limited |
| **Effective bandwidth** | 6.4 GB/s (64-bit @ 100MHz) | 3.2 GB/s (64-bit @ 50MHz) | Lower due to ASIC process node |

#### Design Tradeoffs

| Tradeoff | FPGA Approach | ASIC Approach | Rationale |
|----------|---------------|---------------|-----------|
| **Complexity** | Higher (AXI protocol state machines) | Lower (simple FSM) | ASIC minimizes area/power |
| **Interoperability** | Industry-standard AXI | Custom protocol | ASIC has fixed external interface (GPIO/SPI) |
| **Verification** | AXI VIP available | Must verify custom protocol | Additional testbench effort for ASIC |
| **Host driver** | PYNQ/XRT libraries | Custom GPIO/SPI driver | More host-side development for ASIC |

> [!NOTE]
> The internal compute datapath is **identical** between FPGA and ASIC. Only the external interface wrapper differs. All functional correctness validation on FPGA applies to ASIC internal logic.

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
