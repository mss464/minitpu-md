# Software (Legacy)

> **⚠️ DEPRECATED**: This directory is being refactored into new top-level modules. Run `make clean` to remove generated artifacts.

## Refactoring Overview (Jan 2026)

We have split the monolithic `software/` directory into specialized top-level packages to support multiple backends (FPGA, ASIC, Simulator).

### 1. File Migration Status

Files have been copied to their new homes. The old copies in this directory are kept temporarily for reference but are **deprecated**.

| Original File | New Location | Purpose |
|---------------|--------------|---------|
| `backend/assembler.py` | `compiler/assembler.py` | Instruction encoder |
| `backend/tpu_txt.py` | `compiler/tpu_txt.py` | Assembly IR generation |
| `frontend/tpu_memory_allocator.py` | `runtime/allocator.py` | Memory layout management |
| `frontend/tpu_frontend.py` | `torch/ops.py` | Frontend operations (legacy ops) |
| `host.py` | `hal/pynq.py` | PYNQ FPGA driver |
| `tpu_deploy/*.bit` | `fpga/bitstream/` | Bitstream files |
| `tpu_deploy/*.hwh` | `fpga/bitstream/` | Hardware handoff files |

### 2. New Components Created

We have introduced new placeholder modules to formalize the architecture:

| Component | File | Description |
|-----------|------|-------------|
| **Compiler** | `compiler/module.py` | `TPUModule` class for packaging AOT binaries (planned) |
| **Runtime** | `runtime/device.py` | Abstract `TPUDevice` interface (HAL boundary) |
| | `runtime/executor.py` | `TPUExecutor` for orchestrating transfers & reuse |
| **HAL** | `hal/simulator.py` | CPU-based behavioral simulator (reference) |
| | `hal/xrt.py` | XRT/OpenCL driver stub for Alveo/Versal |
| | `hal/asic_gpio.py` | GPIO driver stub for ASIC post-silicon |

### 3. Legacy Files (Left Behind)

These files remain in `software/` and have **not** been migrated. They are likely obsolete or specific to the old workflow.

| File | Recommendation |
|------|----------------|
| `frontend/mlp_tpu*.py` | **Refactor**: Port relevant tests to `tests/` using the new `torch` API |
| `backend/deploy_and_run.py` | **Delete**: Replaced by standard runtime flow |
| `tpu_deploy/host.py` | **Delete**: Duplicate of `host.py` |
| `*.txt` | **Ignore**: Generated instruction traces |
| `venv/` | **Keep/Ignore**: Local environment |

## Next Steps for Software Team

1. Verify the new `hal/pynq.py` works on the PYNQ board.
2. Port `frontend/mlp_tpu_test.py` to use `torch/` and `runtime/` APIs instead of the old frontend.
3. Once verified, delete this `software/` directory entirely.
