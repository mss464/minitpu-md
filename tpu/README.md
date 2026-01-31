# Mini-TPU Core RTL

This directory contains the **portable, vendor-agnostic** SystemVerilog source code for the Mini-TPU compute engine.

## RTL Module Hierarchy

```
                              ┌─────────────────────────────────────────────┐
                              │          FPGA Top (fpga/rtl/)               │
                              │                                             │
                              │   tpu_top_v6.sv ─────────────────────────┐  │
                              │   ├─ S00_AXI  (AXI-Lite control)         │  │
                              │   ├─ S00_AXIS (AXI-Stream input)         │  │
                              │   ├─ M00_AXIS (AXI-Stream output)        │  │
                              │   │                                      │  │
                              │   │  ┌─ tpu_top_v4_slave_lite_*.v        │  │
                              │   │  ├─ tpu_top_v4_slave_stream_*.v      │  │
                              │   │  └─ tpu_top_v4_master_stream_*.v     │  │
                              └───┼──────────────────────────────────────┼──┘
                                  │                                      │
                                  ▼                                      │
┌─────────────────────────────────────────────────────────────────────────┼──┐
│                         TPU Core (tpu/)                                 │  │
│                                                                         │  │
│   ┌─────────────┐    ┌────────────────────────────────────────────────┐ │  │
│   │   pc.sv     │───►│              compute_core.sv                   │ │  │
│   │ (Program    │    │                                                │ │  │
│   │  Counter)   │    │   ┌────────────────────────────────────────┐   │ │  │
│   └─────────────┘    │   │       systolic_wrapperv2.sv            │   │ │  │
│                      │   │   ┌─────────────────────────────────┐  │   │ │  │
│   ┌─────────────┐    │   │   │        systolic.sv (4×4)        │  │   │ │  │
│   │ decoder.sv  │───►│   │   │  ┌───┐ ┌───┐ ┌───┐ ┌───┐       │  │   │ │  │
│   │ (Instr      │    │   │   │  │PE │→│PE │→│PE │→│PE │→ out  │  │   │ │  │
│   │  Decode)    │    │   │   │  └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘       │  │   │ │  │
│   └─────────────┘    │   │   │    ↓     ↓     ↓     ↓         │  │   │ │  │
│                      │   │   │  ┌───┐ ┌───┐ ┌───┐ ┌───┐       │  │   │ │  │
│   ┌─────────────┐    │   │   │  │PE │→│PE │→│PE │→│PE │→ out  │  │   │ │  │
│   │ bram_top.sv │◄──►│   │   │  └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘       │  │   │ │  │
│   │ (Data Mem)  │    │   │   │    ↓     ↓     ↓     ↓         │  │   │ │  │
│   │             │    │   │   │  ┌───┐ ┌───┐ ┌───┐ ┌───┐       │  │   │ │  │
│   └─────────────┘    │   │   │  │PE │→│PE │→│PE │→│PE │→ out  │  │   │ │  │
│                      │   │   │  └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘       │  │   │ │  │
│                      │   │   │    ↓     ↓     ↓     ↓         │  │   │ │  │
│                      │   │   │  ┌───┐ ┌───┐ ┌───┐ ┌───┐       │  │   │ │  │
│                      │   │   │  │PE │→│PE │→│PE │→│PE │→ out  │  │   │ │  │
│                      │   │   │  └───┘ └───┘ └───┘ └───┘       │  │   │ │  │
│                      │   │   └─────────────────────────────────┘  │   │ │  │
│                      │   └────────────────────────────────────────┘   │ │  │
│                      │                                                │ │  │
│                      │   ┌────────────────────────────────────────┐   │ │  │
│                      │   │           vpu_top.sv                   │   │ │  │
│                      │   │   ┌─────────────────────────────────┐  │   │ │  │
│                      │   │   │          vpu_op.sv              │  │   │ │  │
│                      │   │   │  ┌─────────┐  ┌─────────┐       │  │   │ │  │
│                      │   │   │  │fp32_add │  │fp32_mul │       │  │   │ │  │
│                      │   │   │  └─────────┘  └─────────┘       │  │   │ │  │
│                      │   │   │  + ReLU, D_ReLU                 │  │   │ │  │
│                      │   │   └─────────────────────────────────┘  │   │ │  │
│                      │   └────────────────────────────────────────┘   │ │  │
│                      │                                                │ │  │
│                      │   ┌────────────────────────────────────────┐   │ │  │
│                      │   │        compute_top.sv                  │   │ │  │
│                      │   │   ┌─────────────────────────────────┐  │   │ │  │
│                      │   │   │          vadd.sv                │  │   │ │  │
│                      │   │   │     (Simple vector add)         │  │   │ │  │
│                      │   │   └─────────────────────────────────┘  │   │ │  │
│                      │   └────────────────────────────────────────┘   │ │  │
│                      └────────────────────────────────────────────────┘ │  │
│                                                                         │  │
│   ┌────────────────────────────────────────────────────────────────────┘│  │
│   │  PE internals (pe.sv):                                              │  │
│   │  ┌─────────────────────────────────────────────────────────────┐    │  │
│   │  │  input W ──►┌──────────┐                                    │    │  │
│   │  │             │ fp32_mul │──►┌──────────┐                     │    │  │
│   │  │  input X ──►└──────────┘   │ fp32_add │──► Accumulator ──►Y │    │  │
│   │  │             accum_in ─────►└──────────┘                     │    │  │
│   │  └─────────────────────────────────────────────────────────────┘    │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

## File Inventory

### Core Compute (Portable)
| File | Module | Description |
|------|--------|-------------|
| `pe.sv` | `pe` | Processing Element: FP32 MAC unit |
| `systolic.sv` | `systolic` | 4×4 weight-stationary systolic array |
| `systolic_wrapperv2.sv` | `systolic_wrapper` | Memory-interfaced wrapper with FSM |
| `fp32_add.sv` | `fp32_add` | IEEE-754 single-precision adder |
| `fp32_mul.sv` | `fp32_mul` | IEEE-754 single-precision multiplier |
| `vpu_op.sv` | `vpu_op` | Vector ALU: ADD, SUB, MUL, ReLU, D_ReLU |
| `vpu_top.sv` | `vpu_top` | VPU top-level wrapper |
| `compute_core.sv` | `compute_core` | Orchestrates systolic, VPU, and vadd |
| `compute_top.sv` | `compute_top` | Vector addition unit wrapper |
| `vadd.sv` | `vadd` | Simple 32-bit adder |

### Control (Portable)
| File | Module | Description |
|------|--------|-------------|
| `decoder.sv` | `decoder` | 64-bit instruction decoder |
| `pc.sv` | `pc` | 8-bit program counter |
| `fifo4.sv` | `fifo4` | 8-entry FIFO (used in AXI master) |

### Memory (Portable)
| File | Module | Description |
|------|--------|-------------|
| `bram_top.sv` | `bram_top` | Data memory wrapper |
| `mem_wrapper.sv` | `mem_wrapper` | Portable dual-port RAM (ifdef FPGA/ASIC) |
| `sram_behavioral.sv` | `sram_*` | Behavioral SRAM models (simulation only) |

### FPGA Interface (Moved to fpga/rtl/)
The following files have been moved to `fpga/rtl/` as they are FPGA-specific:
- `tpu_top_v6.sv` - Top-level with AXI interfaces
- `tpu_top_v4_slave_lite_v1_0_S00_AXI.v` - AXI-Lite slave
- `tpu_top_v4_slave_stream_V1_0_S00_AXIS.v` - AXI-Stream slave
- `tpu_top_v4_master_stream_V1_0_M00_AXIS.v` - AXI-Stream master

## Data Flow

```
                    ┌──────────────────────────────────────────────────┐
   Input (64-bit)   │                  COMPUTE PATH                     │   Output (32-bit)
   ────────────────►│                                                   │────────────────►
                    │  ┌─────────┐   ┌─────────────┐   ┌─────────────┐ │
   Instructions     │  │ BRAM    │──►│  Systolic   │──►│   Output    │ │
   ────────────────►│  │ (Data/  │   │   Array     │   │   Buffer    │ │
                    │  │ Weight) │   │   (4×4)     │   │             │ │
                    │  └─────────┘   └─────────────┘   └─────────────┘ │
                    │       │                              ▲           │
                    │       ▼                              │           │
                    │  ┌─────────────────────────────────┐ │           │
                    │  │            VPU                  │─┘           │
                    │  │  (ReLU, Element-wise ops)       │             │
                    │  └─────────────────────────────────┘             │
                    └──────────────────────────────────────────────────┘
```

## Simulation

Run tests from `tests/tpu/`:
```bash
cd tests/tpu
make test_systolic_array    # 100 random 4×4 matmuls
make test_systolic_wrapper  # Memory-interfaced sequential tests
make test_unit              # All unit tests
```

## Known Issues

### Data Shift Bug in AXI-Stream Slave (fpga/rtl/)

**Status**: Believed fixed as of January 31, 2026 (verify in fpga/rtl).

The `tpu_top_v4_slave_stream_V1_0_S00_AXIS.v` module has a 1-element data shift bug:
- **Root cause**: Pipeline register `S_AXIS_TDATA_PIPELINED` captures data on the same clock edge that `write_pointer_stream` increments, causing a 1-cycle mismatch.
- **Effect**: First element written to address 0 is garbage; subsequent elements shifted by 1.
- **Fix**: Remove pipeline stage or delay write pointer increment.

See main README.md for details.
