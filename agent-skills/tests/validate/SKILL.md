---
name: Validation & Testing
description: Running testbenches and verification suites
status: draft
---

# Validation & Testing

> [!NOTE]
> **STATUS: DRAFT / PLACEHOLDER**
> This skill is currently a scaffold. Specific command lines for cocoTB vs Pytest vs Verilator need to be documented.

This skill guides running the verification suite.

## Workflows

1.  **TPU Unit Tests**
    Run pytest-based simulation:
    ```bash
    pytest tests/tpu-unit/
    ```

2.  **Verification Strategy**
    - Unit tests for individual modules (`pe.sv`, `fifo.sv`)
    - Integration tests for full `systolic` array
