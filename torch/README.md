# Mini-TPU PyTorch Frontend

This directory contains the Python frontend for the Mini-TPU, mimicking a PyTorch-like API.

## Structure

- **`ops.py`**: The core library exposing atomic TPU operations (`matmul`, `add`, `relu`, etc.) and memory management. Use this module to build your kernels.
- **`examples/`**: Contains user programs and kernels demonstrating how to use the TPU.
  - `examples/mlp.py`: A complete MLP training step implementation.

## Usage

To compile a program (generate instruction trace):

```bash
# Run the example from the project root
python -m torch.examples.mlp
```

This will generate `mlp_instruction_trace.txt`.

## Development Notes

### Software Emulation Functions
> **Suggestion**: The current example (`mlp.py`) includes software emulation functions (`weight_mul`, `bias_add`, etc.) mixed with the kernel definition. In the future, consider refactoring these into a dedicated `torch/emulation.py` or `torch/reference.py` module to separate the "golden model" logic from the hardware generation logic.
