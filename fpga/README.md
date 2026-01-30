# Cornell TPU Vivado Build Scripts

Automated Vivado batch-mode flow for packaging the TPU RTL into a custom IP and building a complete system with Zynq UltraScale+ MPSoC.

## Overview

```
┌─────────────────┐     package_tpu_ip.tcl     ┌─────────────────┐     build_bd_bitstream.tcl     ┌─────────────────┐
│   RTL Sources   │ ─────────────────────────► │   TPU IP Core   │ ─────────────────────────────► │    Bitstream    │
│   (../tpu/*.sv) │                            │ (ip_repo/)      │                                │ (output/)       │
└─────────────────┘                            └─────────────────┘                                └─────────────────┘
```

| Stage | Input | Output | Description |
|-------|-------|--------|-------------|
| **1. Package IP** | `../tpu/*.sv` (RTL sources) | `ip_repo/cornell_tpu_1.0/` | Packages TPU RTL into reusable Vivado IP with AXI interfaces |
| **2. Build System** | IP repo + Zynq presets | `output/artifacts/minitpu.bit` | Creates block design with PS, DMA, TPU; runs synthesis/implementation |

## Xilinx IP Dependencies

> [!CAUTION]
> This FPGA system integration requires **Xilinx-specific IP** that is NOT portable to other vendors or ASIC:

| IP | VLNV | Purpose | Portable Alternative |
|----|------|---------|----------------------|
| **AXI DMA** | `xilinx.com:ip:axi_dma:7.1` | Memory-to-Stream / Stream-to-Memory transfers | Custom DMA or direct memory interface |
| **Zynq PS** | `xilinx.com:ip:zynq_ultra_ps_e` | Hard processor subsystem | External MCU or soft-core |
| **AXI SmartConnect** | `xilinx.com:ip:smartconnect` | AXI interconnect | AXI crossbar (open-source available) |

The **TPU core RTL** (`tpu/*.sv`) is vendor-agnostic. Only this system-level integration layer (`fpga/`) requires Xilinx tools and IP. For ASIC, see `asic/` which uses `tpu_core.sv` with simple valid/ready interfaces instead.

### Key Steps

1. **IP Packaging**: Wraps RTL with AXI-Lite (control) + AXI-Stream (data) interfaces, generates embedded BRAMs
2. **Block Design**: Instantiates Zynq PS, AXI DMA, AXI interconnects, and TPU IP
3. **Synthesis**: Compiles all HDL to device primitives
4. **Implementation**: Places and routes the design
5. **Bitstream**: Generates `.bit` and `.hwh` for PYNQ deployment

## Board Support

| Board | Status | Notes |
|-------|--------|-------|
| **PYNQ-ZU** (Zynq UltraScale+) | ✅ Supported | Current target; uses embedded PS for DMA and control |
| **Alveo U280** | ❌ Not supported | Requires Vitis platform shell, PCIe-based host interface |
| **Versal VCK5000** | ❌ Not supported | Requires Vitis platform, different PS (CIPS), NoC integration |
| **Versal V80** | ❌ Not supported | Requires Vitis platform, AIE-ML integration |

> [!NOTE]
> The current flow uses a Zynq-specific block design with `zynq_ultra_ps_e` and AXI DMA connected to PS DDR.
> Supporting Alveo/Versal boards would require:
> 1. Vitis platform (.xsa) instead of standalone Vivado project
> 2. XRT kernel packaging (replacing AXI-Stream with AXI4 memory-mapped or HBM interfaces)
> 3. Host-side driver rewrite (PYNQ → XRT runtime)

## Prerequisites

- **Vivado 2023.1+** (tested with 2023.2)
- Zynq UltraScale+ device support installed
- Valid Vivado license

## Quick Start

```bash
# Build everything (package IP + generate bitstream)
make all

# Or run steps individually:
make package_ip    # Step 1: Package TPU IP
make bitstream     # Step 2: Build BD and generate bitstream
```

## Manual Usage

### Script 1: Package TPU IP

```bash
vivado -mode batch -source scripts/package_tpu_ip.tcl -tclargs \
    -ip_name cornell_tpu \
    -part xczu3eg-sbva484-1-i \
    -rtl_dir tpu \
    -repo_out ip_repo
```

**Arguments:**
| Argument | Default | Description |
|----------|---------|-------------|
| `-ip_name` | `cornell_tpu` | Name for the packaged IP |
| `-part` | `xczu3eg-sbva484-1-i` | Target FPGA part |
| `-rtl_dir` | (required) | Directory containing RTL sources |
| `-repo_out` | (required) | Output directory for IP repository |
| `-ip_version` | `1.0` | IP version number |
| `-ip_vendor` | `cornell.edu` | IP vendor string |

**Output:**
- `ip_repo/cornell_tpu_1.0/component.xml` - IP definition
- Prints VLNV at completion

### Script 2: Build Block Design & Bitstream

```bash
vivado -mode batch -source scripts/build_bd_bitstream.tcl -tclargs \
    -proj_name tpu_system \
    -part xczu3eg-sbva484-1-i \
    -ip_repo_path ip_repo \
    -out_dir output
```

**Arguments:**
| Argument | Default | Description |
|----------|---------|-------------|
| `-proj_name` | `tpu_system` | Vivado project name |
| `-part` | `xczu3eg-sbva484-1-i` | Target FPGA part |
| `-ip_repo_path` | (required) | Path to IP repository from step 1 |
| `-out_dir` | (required) | Output directory for project and artifacts |
| `-bd_name` | `tpu_bd` | Block design name |

**Output:**
- `output/artifacts/tpu_bd_wrapper.bit` - Bitstream
- `output/artifacts/tpu_bd.hwh` - Hardware handoff (for Vitis)
- `output/artifacts/utilization_report.txt`
- `output/artifacts/timing_summary.txt`
- `output/artifacts/power_report.txt`

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
