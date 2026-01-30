---
name: IHP ASIC Synthesis
description: Synthesis and tapeout flow using Yosys and OpenROAD with the IHP PDK
status: draft
---

# IHP PDK Full Design Tapeout

> [!NOTE]
> **STATUS: DRAFT / PLACEHOLDER**
> This skill is currently a scaffold. The specific commands and scripts need to be verified against the project's actual execution flow.

This skill guides you through synthesizing the `tpu_top_v6.sv` design using the IHP PDK.

## Workflow

1.  **Environment Setup**
    Ensure OpenROAD-flow-scripts (ORFS) is available.
    Working directory: `asic/`

2.  **Synthesis**
    Run Yosys synthesis to generate a gate-level netlist.
    ```bash
    yosys -c synth.tcl
    ```

3.  **Place and Route (PnR)**
    Use OpenROAD for floorplanning, placement, CTS, and routing.

## Do's and Don'ts
- **DO** keep all synthesis configs in `./asic/`.
- **DON'T** modify RTL in `../tpu/` without explicit user request.
