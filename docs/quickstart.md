# CornellTPU Current Architecture Quickstart

**Last Updated:** 2026-01-30

## 1. Setup Environment
```bash
# From project root (mini-tpu)
python3 -m venv venv
source venv/bin/activate  # or ./venv/Scripts/Activate.ps1 on Windows
pip install numpy torch
export PYTHONPATH=.       # Required for imports
```

## 2. Generate Instruction Trace
Run the model definition code through the compiler CLI.
```bash
python3 compiler/cli.py torch/examples/mlp.py -o tests/fpga/mlp_instruction_trace.txt
```
*   **Input:** `torch/examples/mlp.py` (Model definition with `build()` entry point)
*   **Output:** `tests/fpga/mlp_instruction_trace.txt`

## 3. Assemble Instructions
Convert the trace into machine code (hex).
```bash
python3 compiler/assembler.py tests/fpga/mlp_instruction_trace.txt tests/fpga/mlp_instructions.txt
```
*   **Output:** `tests/fpga/mlp_instructions.txt`
*   **Output:** `tests/fpga/test_generated.py` (Auto-generated host script, useful for debug)

## 4. Run on FPGA Board
Use the automated deployment script to package artifacts and run the test on the PYNQ board.

**Prerequisites:**
- PYNQ board accessible via SSH
- `sshpass` installed (`sudo apt install sshpass`)

**Run:**
```bash
./agent-skills/fpga/deploy/scripts/board_test.sh
```

**What this does:**
1.  Packages `compiler/` library, `tests/fpga/test_mlp.py` (Reference Host Script), and `minitpu.bit`.
2.  Deploys to board (`~/tpu_deploy`).
3.  Executes `test_mlp.py` on the board using the generated instructions.

### Notes
- **Golden Bitstream**: The current `minitpu.bit` generated from source has a known data shift bug. The script may default to `origin/main` bitstream references if available, or run the local one.
- **Modifying Code**:
    - **Frontend**: Edit `torch/examples/mlp.py`
    - **Compiler**: Edit `compiler/tpu_txt.py` or `compiler/assembler.py`
    - **RTL**: Edit `tpu/*.sv`
