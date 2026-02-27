# Runtime

Execution orchestration, memory allocation, and scheduling.

## Contents

| File | Description |
|------|-------------|
| `allocator.py` | Memory region allocator for TPU BRAM |
| `executor.py` | [PLANNED] TPUExecutor for running compiled modules |
| `device.py` | [PLANNED] TPUDevice abstract interface (HAL boundary) |

## Architecture

```
TPUExecutor
    ├── allocator (memory layout)
    ├── TPUDevice (HAL interface)
    └── TPUModule (compiled instructions)
```

The runtime is backend-agnostic; it delegates hardware interaction to HAL implementations.
