# Mini-TPU Test Suite

Tests are organized by component, mirroring the top-level directory structure.

## Structure

```
tests/
├── compiler/           # Codegen, IR emission, module packaging
├── runtime/            # Allocator, executor, device interface
├── hal/                # Driver verification
│   ├── sim/            # Software simulator tests (Golden Reference)
│   ├── pynq/           # Hardware tests (require PYNQ board)
│   └── mock/           # Mock drivers for runtime logical testing
├── torch/              # High-level API tests (Tensor, nn.Linear)
├── integration/        # End-to-end MLP training/inference tests
├── tpu/                # RTL testbenches (cocotb/verilator) - EXISTING
└── e2e/                # System-level E2E tests
```

## Running Tests

```bash
# Run all software tests
python -m pytest tests/

# Run specific component
python -m pytest tests/compiler/

# Run hardware tests (requires connected board)
python -m pytest tests/hal/pynq/ --board-ip 192.168.2.99
```

## RTL Unit Test Plan (tests/tpu)

Goal: make unit coverage complete, reduce redundancy, and keep targeted regression tests.

Planned work:
1) Coverage gap closure
   - Add/extend unit tests for: compute_core, compute_top, vpu_top, mem_wrapper,
     sys_interface, bram_top, sram_behavioral, and the AXI top wrappers.
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
