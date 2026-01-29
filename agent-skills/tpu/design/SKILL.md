---
name: TPU RTL Design
description: Core SystemVerilog development for the Mini-TPU
status: draft
---

# TPU RTL Design

> [!NOTE]
> **STATUS: DRAFT / PLACEHOLDER**
> This skill is currently a scaffold. Detailed coding standards and module interface specifications should be added here.

This skill covers modifying the core TPU architecture.

## Key Modules
- `systolic.sv`: The 16x16 systolic array core
- `pe.sv`: Processing Element with MAC units
- `tpu_top_v6.sv`: Top-level wrapper with AXI interfaces

## Development Rules
1.  **Modularity**: Keep arithmetic logic (`fp_mul.sv`, `fp_adder.sv`) separate from control logic.
2.  **Verification**: Always run `tests/` after modifying RTL.
3.  **Scope**: Do not edit `asic/` or `fpga/` files here; those are downstream consumers.
