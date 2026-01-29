# Mini-TPU

A compact ML stack built by Cornell students, taking a bottom-up approach from a Tensor Processing Unit implementation featuring a systolic array architecture, supporting FPGA prototyping and ASIC tapeout workflows.

## Project Structure
```text
mini-tpu/
├── agent-skills/       # AI Agent Skills
├── asic/               # ASIC Synthesis (RTL to netlist to GDS)
├── compiler/           # Compiler
├── docs/               # Documentation
├── fpga/               # FPGA Synthesis (RTL to bitstream)
├── hal/                # Hardware Abstraction Layer (ASIC and FPGA)
├── legacy-software/    # Legacy Software (FIXME: remove after reviewing)
├── runtime/            # Runtime
├── tests/              # Tests
├── torch/              # PyTorch-like APIs
└── tpu/                # Core RTL
```

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
