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
