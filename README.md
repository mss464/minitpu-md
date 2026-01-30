# Mini-TPU

A compact ML stack built by Cornell students, taking a bottom-up approach from a Tensor Processing Unit implementation featuring a systolic array architecture, supporting FPGA prototyping and ASIC tapeout workflows.

## Progress Tracking
- [x] **Refactoring**: Unified `hal` and `runtime` under `compiler/`. Removed legacy code.
- [/] **FPGA Flow**: Bitstream generation functional.
    - [x] Board deployment scripts (`board_test.sh`).
    - [ ] **Fix**: Data shift bug in `slave_stream` RTL (Patch planned).
- [/] **ASIC Flow**: Phase 1 (Core GDS) complete. Phase 2 (Integration/Tapeout) pending.

## Project Structure
```text
mini-tpu/
├── agent-skills/       # Agentic workflows (fpga, asic, deploy)
├── asic/               # ASIC Synthesis (OpenLane/TinyTapeout)
├── compiler/           # Compiler & Runtime
│   ├── hal/            # Hardware Abstraction Layer (PYNQ, Sim)
│   └── runtime/        # Execution Runtime & Allocators
├── docs/               # Documentation
├── fpga/               # FPGA Synthesis (Vivado)
├── tests/              # Verification
│   └── fpga/           # FPGA board tests
├── torch/              # PyTorch Frontend
└── tpu/                # Core RTL (SystemVerilog)
```

## Architecture Overview

The design follows a **two-tier architecture** separating portable compute logic from platform-specific system integration:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        System Integration Layer                          │
│  (Platform-specific: fpga/ or asic/)                                     │
│                                                                          │
│   FPGA (fpga/):                      ASIC (asic/):                       │
│   ├─ Xilinx AXI DMA IP               ├─ tpu_core.sv (valid/ready I/O)    │
│   ├─ Zynq PS (hard processor)        ├─ SPI bridge (Tiny Tapeout)        │
│   └─ Block design integration        └─ Blackboxed SRAMs                 │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         TPU Core Layer (tpu/)                            │
│  (Portable: vendor-agnostic SystemVerilog)                               │
│                                                                          │
│   ├─ tpu_top_v6.sv      # Top wrapper with AXI interfaces (hand-coded)  │
│   ├─ compute_core.sv    # Systolic + VPU control                        │
│   ├─ systolic.sv        # 8x8 weight-stationary array                   │
│   ├─ mem_wrapper.sv     # Portable BRAM (ifdef FPGA/ASIC)               │
│   └─ ...                                                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### What's Portable (tpu/)
- All compute RTL (systolic array, VPU, decoder, PC)
- AXI-Lite and AXI-Stream **interface logic** (hand-coded Verilog, no vendor IP)
- Memory abstraction via `mem_wrapper.sv` with `TARGET_FPGA`/`TARGET_ASIC` ifdefs

### What's Platform-Specific
| Component | FPGA (Xilinx) | ASIC |
|-----------|---------------|------|
| **DMA Engine** | Xilinx `axi_dma` IP | Not used (direct FIFO interface) |
| **Host Interface** | Zynq PS via AXI | GPIO/SPI bridge |
| **Memory** | Inferred BRAM/URAM | Blackboxed SRAM macros |
| **Top Wrapper** | `tpu_top_v6.sv` | `tpu_core.sv` |

> [!IMPORTANT]
> The `tpu/` directory contains AXI interface *implementations* in RTL, but the **DMA controller** that drives them is a Xilinx IP instantiated in `fpga/`. For ASIC, `asic/tpu_core.sv` replaces AXI-Stream with simple valid/ready handshaking.

## Pending Decisions

Architectural decisions deferred for future consideration:

| Decision | Current Choice | Alternatives | Notes |
|----------|---------------|--------------|-------|
| **Compilation Mode** | AOT (Ahead-of-Time) | JIT (Just-in-Time) | JIT would enable dynamic graph compilation like XLA. Useful if supporting frameworks that generate graphs at runtime (e.g., PyTorch eager mode). |
| **FPGA Runtime API** | OpenCL-compatible | XRT Native | OpenCL adds overhead but ensures portability across Xilinx/Intel FPGAs. XRT native gives lower latency and better Versal AI Engine support. |
| **Multi-Device** | Single device | Multi-device orchestration | IREE-style instance/session model would enable running across multiple FPGAs or distributed ASIC test setups. Adds complexity. |
| **ASIC Test Interface** | GPIO (8-in/8-out/8-bidir) | JTAG, SPI, UART | GPIO chosen for simplicity; may revisit if bring-up reveals bandwidth limitations. |
| **Compiler IR** | Direct-to-assembly | MLIR dialect | MLIR would enable optimization passes (fusion, tiling) but adds toolchain complexity. Current approach is simpler. |
| **Memory Layout** | Baked into module | Separate metadata | Embedding addresses in compiled module is simpler; separate metadata allows runtime relocation. |
| **Error Handling** | Timeout-based | Hardware interrupts | GPIO-based ASIC lacks interrupt support; timeout polling is the fallback. |
| **HAL Testing** | Simulator as golden reference | Mock interfaces | Using simulator output as ground truth for all HAL implementations. |

## Software Stack

The software follows a 4-layer architecture:

```
torch/     → User API (tensors, nn layers)
compiler/  → IR, encoding, TPUModule packaging  
runtime/   → TPUExecutor, memory allocation
hal/       → Device drivers (Simulator, PYNQ, XRT)
```

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Simulator accuracy** | numpy float32 | Functional verification, not bit-accurate IEEE 754 |
| **Matmul dimensions** | Fixed 4×4 in HW | Variable sizes via software tiling |
| **Serialization** | Binary TPUModule | No code generation; generic deployment scripts |


## Quick Start

See [docs/quickstart.md](docs/quickstart.md) for setup instructions.

## Documentation

| Document | Description |
|----------|-------------|
| [System Overview](docs/system.md) | Top-level architecture |
| [Systolic Array](docs/systolic.md) | Compute core design |
| [Memory](docs/memory.md) | Memory subsystem |

## AI Agent Setup

This repo includes configuration for AI coding assistants:

- **`AGENTS.md`** — Primary agent instructions (scope rules, directory boundaries)
- **`CLAUDE.md`** — Symlink to `AGENTS.md` for tool compatibility (gitignored)
- **`agent-skills/<subfolder>/SKILL.md`** — Specialized skills mirroring the project structure

The `agent-skills/` directory contains standard-compliant skill definitions for each domain (e.g., `agent-skills/asic/SKILL.md`).

## License

[Add license information]
