#!/bin/bash
# Setup script to integrate mini-TPU design with OpenROAD-flow-scripts

set -e

ORFS_DIR="${ORFS_DIR:-$HOME/OpenROAD-flow-scripts}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TPU_RTL_DIR="$(dirname "$PROJECT_ROOT")/tpu"

echo "=== Mini-TPU ORFS Integration Setup ==="
echo "ORFS_DIR: $ORFS_DIR"
echo "PROJECT_ROOT: $PROJECT_ROOT"
echo "TPU_RTL_DIR: $TPU_RTL_DIR"

# Check ORFS exists
if [ ! -d "$ORFS_DIR" ]; then
    echo "ERROR: ORFS not found at $ORFS_DIR"
    echo "Clone it first: git clone --recursive https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts $ORFS_DIR"
    exit 1
fi

# Create design directories in ORFS
DESIGN_SRC="$ORFS_DIR/flow/designs/src/tpu_core"
DESIGN_CFG="$ORFS_DIR/flow/designs/ihp-sg13g2/tpu_core"

echo "Creating design directories..."
mkdir -p "$DESIGN_SRC"
mkdir -p "$DESIGN_CFG"

# Copy RTL sources (core files only, no AXI wrappers)
echo "Copying RTL sources..."
CORE_FILES=(
    bram_top.sv
    compute_core.sv
    compute_top.sv
    decoder.sv
    fifo4.sv
    fixedpoint.sv
    fp32_add.sv
    fp32_mul.sv
    fp_adder.sv
    fp_mul.sv
    pc.sv
    pe.sv
    sram_behavioral.sv
    systolic.sv
    systolic_wrapperv2.sv
    vadd.sv
    vpu_op.sv
    vpu_top.sv
)

for f in "${CORE_FILES[@]}"; do
    if [ -f "$TPU_RTL_DIR/$f" ]; then
        cp "$TPU_RTL_DIR/$f" "$DESIGN_SRC/"
        echo "  Copied: $f"
    else
        echo "  WARNING: $f not found"
    fi
done

# Copy ASIC core wrapper
cp "$PROJECT_ROOT/src/tpu_core.sv" "$DESIGN_SRC/"
echo "  Copied: tpu_core.sv (ASIC wrapper)"

# Copy config files
cp "$PROJECT_ROOT/ihp-sg13g2/config.mk" "$DESIGN_CFG/"
cp "$PROJECT_ROOT/ihp-sg13g2/constraint.sdc" "$DESIGN_CFG/"
echo "Copied config.mk and constraint.sdc"

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "  cd $ORFS_DIR/flow"
echo "  source ../env.sh"
echo "  make synth DESIGN_CONFIG=./designs/ihp-sg13g2/tpu_core/config.mk"
