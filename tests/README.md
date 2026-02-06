# Mini-TPU Test Suite

Tests are organized by component.

## Structure

```
tests/
├── tensorcore/         # TensorCore RTL testbenches (cocotb) - ACTIVE
├── ultra96-v2/         # ultra96-v2 hardware deployment tests - ACTIVE
├── compiler/           # [TODO] Codegen, IR emission
├── runtime/            # [TODO] Allocator, executor
├── hal/                # [TODO] Driver verification
├── torch/              # [TODO] High-level API tests
└── integration/        # [TODO] End-to-end MLP training/inference tests
```

## Running Tests

### RTL Simulation (TPU)
Requires `cocotb` and a simulator (e.g., `icarus-verilog`).

```bash
make -C tests/tensorcore test
```

### ultra96-v2 Board Tests
Requires Ultra96-v2 board with PYNQ. Uses `tests/Makefile` to deploy and run.

**Quick start with automated skill:**
```bash
agent-skills/ultra96-v2/validate/scripts/build_and_test.sh --board-ip <ip>
```

**Manual workflow:**
```bash
# Build bitstream first (if needed)
make -C tpu bitstream TARGET=ultra96-v2

# Comprehensive test (VPU ops, matmul, tiled matmul)
make -C tests board-comprehensive \
    BIT=tpu/ultra96-v2/output/artifacts/minitpu.bit \
    HWH=tpu/ultra96-v2/output/artifacts/minitpu.hwh \
    BOARD_IP=<your-board-ip>

# MLP forward+backward pass test
make -C tests board-test \
    BIT=tpu/ultra96-v2/output/artifacts/minitpu.bit \
    HWH=tpu/ultra96-v2/output/artifacts/minitpu.hwh \
    PROGRAM=tests/ultra96-v2/test_mlp.py \
    BOARD_IP=<your-board-ip>
```

### Offline Compiler Tests
No hardware required.

```bash
# Test instruction limit enforcement and tiled matmul generation
python tests/ultra96-v2/test_tiled_matmul.py
```

## ultra96-v2 Test Coverage

| Test | Operations | Instructions | Status |
|------|------------|--------------|--------|
| `test_comprehensive.py` | Data integrity, VPU (add/sub/mul/relu), 4x4 matmul, 8x8 tiled matmul | 90 | PASS |
| `test_mlp.py` | Full MLP forward+backward pass | 169 | PASS |
| `test_tiled_matmul.py` | Compiler tiling + instruction limit | N/A (offline) | PASS |

## Important Notes

**Single-batch execution:** The TPU requires all operations to be in a single
instruction batch. Multiple `compute()` calls without reprogramming the ultra96-v2
do not properly reset TPU state. This is by design - load all data, load all
instructions, execute once, read results.

**Instruction limit:** IRAM holds 256 instructions max. The compiler enforces
this limit and raises `CompilationError` if exceeded. Use tiled operations to
keep instruction count manageable.

## TODOs & CI Integration
- [ ] Re-implement software stack tests (compiler, runtime, torch).
- [ ] Integrate TPU tests into CI pipeline (GitHub Actions).
- [ ] Add ultra96-v2 hardware-in-the-loop testing to CI.

## RTL Unit Test Plan (tests/tpu)

Goal: make unit coverage complete, reduce redundancy, and keep targeted regression tests.

Planned work:
1) Coverage gap closure
   - **Mem Wrapper (`mem_wrapper.sv`)**:
     - Verify 1-cycle read latency (`READ_FIRST`).
     - Test dual-port independence (Port A vs Port B).
     - Check parameter propagation (`DATA_WIDTH`, `ADDR_WIDTH`).
   - **SRAM Behavioral (`sram_behavioral.sv`)**:
     - Verify 2-cycle read latency (pipeline behavior).
     - Test specific configurations: `sram_8192x32` (Data) and `sram_256x64` (Instr).
     - Validate write-enable masking if applicable.
   - **Other Missing Units**:
     - `compute_core.sv`, `dummy_unit.sv`.
     - `axi` wrappers (verify bus logic).
   - Add tests for legacy fp_adder/fp_mul (or confirm deprecation and remove).
2) Redundancy cleanup
   - Consolidate size-specific systolic tests (4x4/5x5/16x16) into a
     parameterized test, keeping one directed test and one randomized test.
   - Reduce wrapper test overlap: keep a minimal directed test, one randomized
     stress test, and the sequential-stale-state regression.
3) Decoder/VPU alignment
   - Keep ISA decoder test as primary; trim overlapping checks from older
     decoder test if redundant.
4) Regression set
   - Maintain a small fast target (`make test_unit`) plus focused regressions
     (ISA decoder, sequential systolic, VPU op coverage).
