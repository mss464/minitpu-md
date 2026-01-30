---
artifact: agent_notes
scope: fpga
format: markdown
compatibility:
  - claude-code
  - antigravity
---

# Agent Artifacts Log

Notes intended for future FPGA bring-up/debug sessions.

## 2026-01-29
- Vivado env: if `vivado` is not on PATH, run `source /opt/xilinx/Vitis/2023.2/settings64.sh`.
- Legacy BRAM (blk_mem_gen) behavior (user-reported): write-first, 2-cycle read latency, pipelined sequential reads.
