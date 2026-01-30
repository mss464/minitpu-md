---
name: FPGA Deployment
description: Build bitstreams and run FPGA board tests for the Mini-TPU
status: stable
---

# FPGA Deployment

This skill handles the Vivado-based flow for building Mini-TPU bitstreams and running PYNQ board tests.

## Quick Start

Run the local bitstream test (default):
```bash
agent-skills/fpga/deploy/scripts/board_test.sh
```

Override board settings if needed:
```bash
BOARD_IP=132.236.59.64 BOARD_USER=xilinx BOARD_PASS=xilinx \
agent-skills/fpga/deploy/scripts/board_test.sh
```

Optionally run the origin/main reference first:
```bash
RUN_ORIGIN=1 agent-skills/fpga/deploy/scripts/board_test.sh
```

## Build Bitstream (optional)

If `vivado` is not on PATH:
```bash
source /opt/xilinx/Vitis/2023.2/settings64.sh
```

Then build:
```bash
cd fpga && make bitstream
```

Artifacts land in `fpga/output/artifacts/`.

## Board Test Details

- Board defaults come from `fpga/Makefile` (`BOARD_IP`, `BOARD_USER`, `BOARD_PASS`).
- Local test defaults to `fpga/bitstream/minitpu.{bit,hwh}`; override with `LOCAL_BIT`/`LOCAL_HWH`.
- Host/instructions default to `software/tpu_deploy` or `legacy-software/tpu_deploy` when present; override via `HOST_DIR` or `HOST_PY`/`INSTR_FILE`.
- Reference test uses `origin/main:software/tpu_deploy/{CornellTPU.bit,CornellTPU.hwh,host.py,tpu_instructions.txt}` when `RUN_ORIGIN=1`.
