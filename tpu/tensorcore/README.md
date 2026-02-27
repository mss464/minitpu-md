# Mini-TensorCore RTL

This directory contains the **portable, vendor-agnostic** SystemVerilog source code for the TensorCore, the core of our TPU.

## RTL Module Hierarchy

```
                              ┌─────────────────────────────────────────────┐
                              │          FPGA Top (fpga/rtl/)               │
                              │                                             │
                              │   tpu.sv ────────────────────────────┐  │
                              │   ├─ S00_AXI  (AXI-Lite control)         │  │
                              │   ├─ S00_AXIS (AXI-Stream input)         │  │
                              │   ├─ M00_AXIS (AXI-Stream output)        │  │
                              │   │                                      │  │
                              │   │  ┌─ tpu_slave_axi_lite.v             │  │
                              │   │  ├─ tpu_slave_axi_stream.v           │  │
                              │   │  └─ tpu_master_axi_stream.v          │  │
                              └───┼──────────────────────────────────────┼──┘
                                  │                                      │
                                  ▼                                      │
┌─────────────────────────────────────────────────────────────────────────┼──┐
│                         TensorCore (tpu/)                                 │  │
│                                                                         │  │
│   ┌─────────────┐    ┌────────────────────────────────────────────────┐ │  │
│   │   pc.sv     │───►│              compute_core.sv                   │ │  │
│   │ (Program    │    │                                                │ │  │
│   │  Counter)   │    │   ┌────────────────────────────────────────┐   │ │  │
│   └─────────────┘    │   │       mxu.sv                          │   │ │  │
│                      │   │   ┌─────────────────────────────────┐  │   │ │  │
│   ┌─────────────┐    │   │   │        systolic.sv (4×4)        │  │   │ │  │
│   │ decoder.sv  │───►│   │   │  ┌───┐ ┌───┐ ┌───┐ ┌───┐       │  │   │ │  │
│   │ (Instr      │    │   │   │  │PE │→│PE │→│PE │→│PE │→ out  │  │   │ │  │
│   │  Decode)    │    │   │   │  └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘       │  │   │ │  │
│   └─────────────┘    │   │   │    ↓     ↓     ↓     ↓         │  │   │ │  │
│                      │   │   │  ┌───┐ ┌───┐ ┌───┐ ┌───┐       │  │   │ │  │
│   ┌─────────────┐    │   │   │  │PE │→│PE │→│PE │→│PE │→ out  │  │   │ │  │
│   │scratchpad.sv│◄──►│   │   │  └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘       │  │   │ │  │
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
│                      │   │           vpu.sv                       │   │ │  │
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
│                      │   │        dummy_unit.sv                   │   │ │  │
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
| `mxu.sv` | `mxu` | Matrix unit: memory-interfaced systolic wrapper |
| `fp32_add.sv` | `fp32_add` | IEEE-754 single-precision adder |
| `fp32_mul.sv` | `fp32_mul` | IEEE-754 single-precision multiplier |
| `vpu_op.sv` | `vpu_op` | Vector ALU: ADD, SUB, MUL, ReLU, D_ReLU |
| `vpu.sv` | `vpu` | Vector processing unit |
| `compute_core.sv` | `compute_core` | Orchestrates systolic, VPU, and vadd |
| `dummy_unit.sv` | `dummy_unit` | Vector addition unit (placeholder) |
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
| `scratchpad.sv` | `scratchpad` | Data memory (scratchpad) |
| `mem_wrapper.sv` | `mem_wrapper` | Portable dual-port RAM (ifdef FPGA/ASIC) |
| `sram_behavioral.sv` | `sram_*` | Behavioral SRAM models (simulation only) |

### FPGA Interface (Moved to fpga/rtl/)
The following files have been moved to `fpga/rtl/` as they are FPGA-specific:
- `tpu.sv` - Top-level with AXI interfaces
- `tpu_slave_axi_lite.v` - AXI-Lite slave
- `tpu_slave_axi_stream.v` - AXI-Stream slave
- `tpu_master_axi_stream.v` - AXI-Stream master

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
make test_mxu               # Memory-interfaced sequential tests
make test_unit              # All unit tests
```

## Known Issues

### Data Shift Bug in AXI-Stream Slave (fpga/rtl/)

**Status**: Believed fixed as of January 31, 2026 (verify in fpga/rtl).

The `tpu_slave_axi_stream.v` module has a 1-element data shift bug:
- **Root cause**: Pipeline register `S_AXIS_TDATA_PIPELINED` captures data on the same clock edge that `write_pointer_stream` increments, causing a 1-cycle mismatch.
- **Effect**: First element written to address 0 is garbage; subsequent elements shifted by 1.
- **Fix**: Remove pipeline stage or delay write pointer increment.

See main README.md for details.
