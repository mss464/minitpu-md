# Ultra96-v2 Board Support

Board-specific sources and Tcl scripts for the Ultra96-v2 Vivado flow.

## Contents

```
ultra96-v2/
├── rtl/                    # FPGA-specific RTL (AXI interfaces)
├── package_tpu_ip.tcl      # IP packaging script
├── build_bd_bitstream.tcl  # Block design & bitstream script
├── ip_repo/                # Generated IP (gitignored)
└── output/                 # Build artifacts (gitignored)
```

## How to Build

**Quick Start:**
```bash
# From tpu/ directory
source /opt/xilinx/Vitis/2023.2/settings64.sh  # Source Vivado environment
make bitstream TARGET=ultra96-v2                # Build everything
```

**Individual Steps:**
```bash
# Package TPU IP (includes tensorcore RTL)
make tpu-ip TARGET=ultra96-v2

# Build bitstream from packaged IP
make bitstream TARGET=ultra96-v2

# Clean build artifacts
make clean TARGET=ultra96-v2
```

See the top-level TPU flow guide: `tpu/README.md` for more details.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Zynq UltraScale+ MPSoC                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Processing System                      │   │
│  │                                                           │   │
│  │   M_AXI_HPM0_FPD ─────┐          ┌───── S_AXI_HP0_FPD    │   │
│  │                        │          │                       │   │
│  │   PL_CLK0 ────────────┼──────────┼───────                 │   │
│  │   PL_RESETN0 ─────────┼──────────┼───────                 │   │
│  └──────────────────────┼──────────┼────────────────────────┘   │
└─────────────────────────┼──────────┼────────────────────────────┘
                          │          │
                          ▼          ▲
              ┌───────────────────────────────┐
              │       AXI Interconnect        │
              │        (Control Path)         │
              └───────┬─────────────┬─────────┘
                      │             │
            ┌─────────▼───┐   ┌─────▼─────────┐
            │  AXI DMA    │   │  Cornell TPU  │
            │ (Control)   │   │   (S00_AXI)   │
            └─────────────┘   └───────────────┘
                  │                   ▲
    ┌─────────────┴───────────────────┴──────────┐
    │              AXI SmartConnect               │
    │              (Memory Access)                │
    └────────────────────┬────────────────────────┘
                         │ (to PS HP0)

              ┌──────────────────────────────┐
              │          Data Flow           │
              │                              │
              │  DMA MM2S ─────► TPU S00_AXIS│
              │  (64-bit)       (Input)      │
              │                              │
              │  TPU M00_AXIS ──► DMA S2MM   │
              │  (Output)        (32-bit)    │
              └──────────────────────────────┘
```

## IP Interfaces

The packaged TPU IP exposes:

| Interface | Type | Width | Description |
|-----------|------|-------|-------------|
| S00_AXI | AXI4-Lite Slave | 32-bit data, 6-bit addr | Control registers |
| S00_AXIS | AXI-Stream Slave | 64-bit | Input data stream |
| M00_AXIS | AXI-Stream Master | 32-bit | Output data stream |

The `rtl/tpu_slave_axi_stream.v` module has a 1-element data shift bug during burst transfers:

**Root Cause** (lines 195-211):
```verilog
S_AXIS_TDATA_PIPELINED <= S_AXIS_TDATA;      // Captures current data
case (tpu_mode_stream)
    3'd4: data_iram <= S_AXIS_TDATA_PIPELINED;  // Uses OLD pipelined value
    3'd1: data_bram <= S_AXIS_TDATA_PIPELINED;  // Uses OLD pipelined value
endcase
```

The pipeline register captures data on the same clock edge that `write_pointer_stream` increments, causing data to be written to the wrong address (off by 1).

**Fix Options**:
1. Remove pipeline register: `data_iram <= S_AXIS_TDATA;`
2. Delay write pointer increment by 1 cycle

## Troubleshooting

### "Black box" errors for blk_mem_gen_1
The packaging script creates the BRAM IP dynamically. If you see errors:
1. Ensure Vivado has network access or the IP catalog is cached
2. Check BRAM IP version matches your Vivado version

### IP not found in repository
Run `make clean` and rebuild. Ensure the `ip_repo` path is correct.

### Timing violations
The default 100MHz clock is conservative. Check `timing_summary.txt` for details.

## Clean

```bash
make clean      # Remove all generated files
make clean_ip   # Remove only IP repo
```

## License

Cornell University © 2024
