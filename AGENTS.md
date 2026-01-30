# AGENTS.md - Mini-TPU Project Guidelines

## Project Overview

This repository contains a mini TPU (Tensor Processing Unit) implementation with RTL design, FPGA deployment, ASIC synthesis, software stack, and tests.

## Directory Structure & Scope Boundaries

> [!CAUTION]
> **File Scope Rule**: Each conversation must confine modifications to its relevant subfolder. DO NOT touch files outside your designated scope unless explicitly instructed.

### Directory Responsibilities

| Directory | Purpose | Scope |
|-----------|---------|-------|
| `tpu/` | Core RTL design (SystemVerilog modules) | Modify only when working on RTL/design |
| `fpga/` | FPGA synthesis, packaging, bitstream generation | Modify only during FPGA deployment tasks |
| `asic/` | ASIC synthesis flow (Yosys, OpenROAD, PDK configs) | Modify only during ASIC/tapeout tasks |
| `tests/` | Testbenches and verification | Modify only when writing/updating tests |
| `software/` | Host software, compiler, instruction generation | Modify only for software/toolchain work |
| `docs/` | Documentation files | Modify only when updating documentation |

## Available Skills

This project uses the `agent-skills/` directory to define specialized workflows.

- **ASIC**: `agent-skills/asic/synthesize/`
- **FPGA**: `agent-skills/fpga/deploy/`
- **TPU RTL**: `agent-skills/tpu/design/`
- **Testing**: `agent-skills/tests/validate/`
- **Software**: `agent-skills/software/develop/`

---

## Task-Specific Guidelines

### ASIC Synthesis (`./asic/`)

When working on synthesis, PnR, or tapeout:
- Confine all new scripts, configs, and outputs to `./asic/`
- Reference RTL from `../tpu/` but do not modify it
- If RTL changes are needed, explicitly flag this to the user

### FPGA Deployment (`./fpga/`)

When working on FPGA builds:
- Keep Vivado scripts, IP packaging, and outputs in `./fpga/`
- Reference RTL from `../tpu/` but do not modify it
- Artifacts go in `./fpga/output/`

### RTL Development (`./tpu/`)

When modifying the core TPU design:
- All SystemVerilog modules live here
- Coordinate with `./tests/` for verification
- Do not modify `./fpga/` or `./asic/` scripts without explicit request

### Testing (`./tests/`)

When writing or running tests:
- Testbenches and test scripts go in `./tests/tpu-unit/`
- May reference RTL from `../tpu/` read-only
- Do not modify production RTL during test development

### Software (`./software/`)

When working on the software stack:
- Compiler, host interface, and deployment code live here
- Do not modify RTL or FPGA/ASIC flows

---

## General Rules

1. **Read-Only References**: When referencing files from another directory, treat them as read-only unless the user explicitly requests cross-boundary modifications.

2. **Explicit Flagging**: If a task genuinely requires modifying files outside scope, flag this to the user before proceeding.

3. **Artifact Placement**: Build outputs, generated files, and logs should stay within the relevant subfolder (e.g., `./asic/build/`, `./fpga/output/`).

4. **Documentation**: If significant changes are made, update the relevant `README.md` or docs in `./docs/`.