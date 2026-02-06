# Ultra96-v2 Validation Skill

Build and test TPU bitstream on Ultra96-v2 FPGA board.

## Quick Start

### One-Command Build and Test
```bash
agent-skills/ultra96-v2/validate/scripts/build_and_test.sh \
  --board-ip <ip-address> \
  [--board-user xilinx] \
  [--board-pass xilinx]
```

### Manual Workflow

**1. Build Bitstream**
```bash
cd tpu
make bitstream TARGET=ultra96-v2
```

**Outputs:**
- `ultra96-v2/output/artifacts/minitpu.bit` - FPGA bitstream
- `ultra96-v2/output/artifacts/minitpu.hwh` - Hardware handoff for PYNQ

**Build Time:** ~10-15 minutes

**2. Run Comprehensive Test**
```bash
make -C tests board-comprehensive \
  BIT=tpu/ultra96-v2/output/artifacts/minitpu.bit \
  HWH=tpu/ultra96-v2/output/artifacts/minitpu.hwh \
  BOARD_IP=<your-board-ip> \
  BOARD_USER=xilinx \
  BOARD_PASS=xilinx
```

**Test Coverage:**
- Data integrity (BRAM read/write)
- VPU operations (add, sub, mul, relu)
- 4×4 matrix multiplication
- 8×8 tiled matrix multiplication

## Build Details

### Prerequisites
- Vivado 2023.2 (automatically sourced by Makefile)
- Ultra96-v2 board with PYNQ image
- SSH access to board

### Resource Utilization (Typical)
- **LUTs:** ~24% (16,684 / 70,560)
- **Registers:** ~8% (11,523 / 141,120)
- **DSPs:** 34 / 360
- **BRAM:** 12 tiles / 216
- **Clock:** 50 MHz with positive slack

### Build Stages
1. **TensorCore IP** - Package portable RTL from `tpu/tensorcore/`
2. **TPU IP** - Wrap with AXI interfaces from `tpu/ultra96-v2/rtl/`
3. **Block Design** - Create Zynq PS + AXI DMA + TPU system
4. **Synthesis** - Parallel synthesis of all IP blocks
5. **Implementation** - Place and route
6. **Bitstream** - Generate final `.bit` and `.hwh`

## Troubleshooting

### Build Issues

**"Vivado not found"**
- Makefile auto-sources `/opt/xilinx/Vitis/2023.2/settings64.sh`
- Override with: `make bitstream VIVADO_SETTINGS=/path/to/settings64.sh`

**Timing violations**
- Check `ultra96-v2/output/artifacts/timing_summary.txt`
- WNS should be positive (typically +3-4 ns)

**IP packaging errors**
- Clean and rebuild: `make clean TARGET=ultra96-v2 && make bitstream TARGET=ultra96-v2`

### Test Issues

**"Board not reachable"**
- Verify board IP: `ping <board-ip>`
- Check SSH: `ssh xilinx@<board-ip>`

**"Module not found: pynq"**
- Ensure PYNQ image is installed on board
- Standard PYNQ 3.0+ has all required dependencies

**Test failures**
- Check bitstream matches test expectations
- Verify no data shift bug (should be fixed in current RTL)
- Review test output for specific failure

## Configuration

### Environment Variables
```bash
# Override Vivado settings path
export VIVADO_SETTINGS=/opt/xilinx/Vivado/2023.2/settings64.sh

# Override board connection
export BOARD_IP=192.168.1.10
export BOARD_USER=xilinx
export BOARD_PASS=xilinx
```

### Makefile Variables
All make targets support variable overrides:
```bash
make bitstream TARGET=ultra96-v2 PART=xczu3eg-sbva484-1-i
make board-comprehensive BIT=<path> HWH=<path> BOARD_IP=<ip>
```

## Related Files

### Hardware
- `tpu/tensorcore/*.sv` - Portable TensorCore RTL
- `tpu/ultra96-v2/rtl/*.v` - AXI interface wrappers
- `tpu/ultra96-v2/package_tpu_ip.tcl` - IP packaging script
- `tpu/ultra96-v2/build_bd_bitstream.tcl` - Bitstream build script

### Tests
- `tests/ultra96-v2/test_comprehensive.py` - Test harness
- `tests/ultra96-v2/programs/comprehensive.py` - Test program compiler
- `tests/Makefile` - Board deployment automation

### Documentation
- `tpu/README.md` - TPU build overview
- `tpu/tensorcore/README.md` - TensorCore RTL documentation
- `tpu/ultra96-v2/README.md` - Board-specific details
- `tests/ultra96-v2/README.md` - Test workflow details

## License

Cornell University © 2024
