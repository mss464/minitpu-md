# Mini-TPU Test Suite

Tests are organized by component.

## Structure

```
tests/
├── tpu/                # RTL testbenches (cocotb) - ACTIVE
├── fpga/               # FPGA hardware deployment scripts - ACTIVE
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
# Run all TPU unit tests
cd tests/tpu
make test
```

### FPGA Deployment
Requires PYNQ board and `pynq` library.

```bash
# Run MLP on FPGA
python tests/fpga/test_mlp.py
```

## TODOs & CI Integration
- [ ] Re-implement software stack tests (compiler, runtime, torch).
- [ ] Integrate TPU tests into CI pipeline (GitHub Actions).
- [ ] Add FPGA hardware-in-the-loop testing to CI.

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
     - `compute_core.sv`, `compute_top.sv`.
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
