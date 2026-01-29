---
name: FPGA Deployment
description: Bitstream generation and IP packaging for Xilinx FPGAs
status: draft
---

# FPGA Deployment

> [!NOTE]
> **STATUS: DRAFT / PLACEHOLDER**
> This skill is currently a scaffold. Using the Makefile is correct, but the exact TCL parameters need validation.

This skill handles the Vivado-based flow for deploying the TPU to FPGA hardware.

## Workflow

1.  **Bitstream Generation**
    Run the complete build flow:
    ```bash
    cd fpga && make all
    ```

2.  **IP Packaging**
    If updating the IP core:
    ```bash
    vivado -mode batch -source package_tpu_ip.tcl
    ```

## Do's and Don'ts
- **DO** use the `2023.2` Vivado version as configured in the Makefile.
- **DO** check timing reports in `output/` after build.
