---
name: FPGA Test Generation & Deployment
description: Generate test cases from Torch models, build bitstreams, and verify on FPGA hardware.
status: stable
---

# FPGA Test Generation & Deployment

This skill documents the modular Hardware-in-the-Loop (HIL) testing flow for the Mini-TPU. The process follows industry standard verification practices:
1.  **Golden Model**: Run high-level Python simulation (Torch) to generate ground truth data and execution traces.
2.  **Artifact Generation**: Assemble traces into binary instructions and generate host-side test scripts.
3.  **HIL Verification**: Deploy artifacts to the FPGA board and execute against the hardware.

## Quick Start

### 1. Generate Test Artifacts
Run the MLP example to generate the instruction trace, then compile it into deployment artifacts:

```bash
# Ensure project root is in PYTHONPATH
export PYTHONPATH=. 

# 1. Run Golden Model (Generates mlp_instruction_trace.txt)
python3 torch/examples/mlp.py

# 2. Compile Artifacts (Generates tests/fpga/mlp_instructions.txt and tests/fpga/test_generated.py)
python3 compiler/assembler.py mlp_instruction_trace.txt tests/fpga/mlp_instructions.txt

# 3. Stage Artifacts for Deployment
mv tests/fpga/test_generated.py tests/fpga/test_mlp_generated.py
cp tests/fpga/test_mlp_generated.py tests/fpga/test_mlp.py
```

### 2. Run Hardware Test
Deploy the generated artifacts and the current bitstream to the FPGA board:

```bash
agent-skills/fpga/deploy/scripts/board_test.sh
```

## Toolchain Architecture

*   **Golden Model**: `torch/examples/mlp.py`
    *   Simulates TPU logic using `torch.ops`.
    *   Produces `mlp_instruction_trace.txt`.
*   **Assembler**: `compiler/assembler.py`
    *   Parses the trace.
    *   Generates binary instructions (`.txt` hex format).
    *   Generates Python test script (`test_generated.py`) containing the exact random input data/weights used in the simulation run.
*   **Hardware Abstraction Layer (HAL)**: `compiler/hal/pynq_host.py`
    *   Reusable `TpuDriver` class handling register I/O, DMA, and interrupts on the PYNQ board.
*   **Deployment**: `agent-skills/fpga/deploy/scripts/board_test.sh`
    *   Assembles a temporary deployment package.
    *   Includes `compiler/hal`, generated test script, and bitstream.
    *   SCPs to board and executes.

## Build Bitstream (optional)

If you need to regenerate the FPGA bitstream from RTL:

```bash
source /opt/xilinx/Vitis/2023.2/settings64.sh
cd fpga && make bitstream
```
*   Artifacts: `fpga/output/artifacts/minitpu.{bit,hwh}`
*   Deployment: Copy artifacts to `fpga/bitstream/` to use them in tests.
