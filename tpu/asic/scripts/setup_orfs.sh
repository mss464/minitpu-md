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
DESIGN_SRC="$ORFS_DIR/flow/designs/src/tensorcore"
DESIGN_CFG="$ORFS_DIR/flow/designs/ihp-sg13g2/tensorcore"

echo "Creating design directories..."
mkdir -p "$DESIGN_SRC"
mkdir -p "$DESIGN_CFG"

# Copy RTL sources (core files only, no AXI wrappers)
echo "Copying RTL sources..."
CORE_FILES=(
    scratchpad.sv
    compute_core.sv
    dummy_unit.sv
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
    mxu.sv
    vadd.sv
    vpu_op.sv
    vpu.sv
)

for f in "${CORE_FILES[@]}"; do
    if [ -f "$TPU_RTL_DIR/$f" ]; then
        cp "$TPU_RTL_DIR/$f" "$DESIGN_SRC/"
        echo "  Copied: $f"
    else
        echo "  WARNING: $f not found"
    fi
done

# Copy ASIC-specific files (overrides and wrappers)
echo "Copying ASIC-specific files..."
for f in "$PROJECT_ROOT/src/"*.sv; do
    if [ -f "$f" ]; then
        cp "$f" "$DESIGN_SRC/"
        echo "  Copied: $(basename $f) (ASIC override)"
    fi
done

# Copy config files
cp "$PROJECT_ROOT/ihp-sg13g2/config.mk" "$DESIGN_CFG/"
cp "$PROJECT_ROOT/ihp-sg13g2/constraint.sdc" "$DESIGN_CFG/"
echo "Copied config.mk and constraint.sdc"

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "  cd $ORFS_DIR/flow"
echo "  source ../env.sh"
echo "  make synth DESIGN_CONFIG=./designs/ihp-sg13g2/tensorcore/config.mk"
