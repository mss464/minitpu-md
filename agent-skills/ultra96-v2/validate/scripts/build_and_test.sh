#!/usr/bin/env bash
# Ultra96-v2 Build and Test Script
# Configurable paths and settings for bitstream build and board testing

set -euo pipefail

# ============================================================================
# Configuration (can be overridden via CLI args or environment variables)
# ============================================================================

# Paths (relative to repo root)
REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || echo ".")}"
TPU_DIR="${TPU_DIR:-${REPO_ROOT}/tpu}"
TESTS_DIR="${TESTS_DIR:-${REPO_ROOT}/tests}"
TARGET="${TARGET:-ultra96-v2}"
OUTPUT_DIR="${OUTPUT_DIR:-${TPU_DIR}/${TARGET}/output/artifacts}"

# Build settings
VIVADO_SETTINGS="${VIVADO_SETTINGS:-/opt/xilinx/Vitis/2023.2/settings64.sh}"
PART="${PART:-xczu3eg-sbva484-1-i}"

# Board settings
BOARD_IP="${BOARD_IP:-}"
BOARD_USER="${BOARD_USER:-xilinx}"
BOARD_PASS="${BOARD_PASS:-xilinx}"

# Test settings
TEST_PROGRAM="${TEST_PROGRAM:-test_comprehensive.py}"

# Flags
SKIP_BUILD="${SKIP_BUILD:-0}"
SKIP_TEST="${SKIP_TEST:-0}"
CLEAN="${CLEAN:-0}"

# ============================================================================
# Helper Functions
# ============================================================================

usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Build TPU bitstream and run tests on Ultra96-v2 board.

OPTIONS:
    -h, --help              Show this help message
    -i, --board-ip IP       Board IP address (required for testing)
    -u, --board-user USER   Board username (default: xilinx)
    -p, --board-pass PASS   Board password (default: xilinx)

    --skip-build            Skip bitstream build, use existing
    --skip-test             Skip board testing, only build
    --clean                 Clean before building

    --tpu-dir DIR           TPU directory (default: \$REPO_ROOT/tpu)
    --tests-dir DIR         Tests directory (default: \$REPO_ROOT/tests)
    --target TARGET         FPGA target (default: ultra96-v2)
    --vivado-settings PATH  Vivado settings64.sh path

EXAMPLES:
    # Build and test
    $0 --board-ip 192.168.1.10

    # Build only
    $0 --skip-test

    # Test existing bitstream
    $0 --skip-build --board-ip 192.168.1.10

    # Clean build
    $0 --clean --board-ip 192.168.1.10

ENVIRONMENT VARIABLES:
    BOARD_IP, BOARD_USER, BOARD_PASS
    VIVADO_SETTINGS, TPU_DIR, TESTS_DIR, TARGET

EOF
    exit 0
}

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    echo "[ERROR] $*" >&2
    exit 1
}

check_prereqs() {
    log "Checking prerequisites..."

    command -v make >/dev/null 2>&1 || error "make not found"
    command -v git >/dev/null 2>&1 || error "git not found"

    if [[ ! -f "$VIVADO_SETTINGS" ]]; then
        error "Vivado settings not found: $VIVADO_SETTINGS"
    fi

    if [[ ! -d "$TPU_DIR" ]]; then
        error "TPU directory not found: $TPU_DIR"
    fi

    if [[ "$SKIP_TEST" == "0" ]] && [[ -z "$BOARD_IP" ]]; then
        error "Board IP required for testing. Use --board-ip or --skip-test"
    fi
}

build_bitstream() {
    log "Building bitstream for $TARGET..."

    cd "$TPU_DIR"

    if [[ "$CLEAN" == "1" ]]; then
        log "Cleaning previous build..."
        make clean TARGET="$TARGET"
    fi

    log "Starting build (this takes ~10-15 minutes)..."
    if ! make bitstream TARGET="$TARGET" PART="$PART" VIVADO_SETTINGS="$VIVADO_SETTINGS"; then
        error "Bitstream build failed"
    fi

    # Verify outputs
    if [[ ! -f "$OUTPUT_DIR/minitpu.bit" ]]; then
        error "Bitstream not generated: $OUTPUT_DIR/minitpu.bit"
    fi
    if [[ ! -f "$OUTPUT_DIR/minitpu.hwh" ]]; then
        error "Hardware handoff not generated: $OUTPUT_DIR/minitpu.hwh"
    fi

    log "Build complete!"
    log "  Bitstream: $OUTPUT_DIR/minitpu.bit ($(du -h "$OUTPUT_DIR/minitpu.bit" | cut -f1))"
    log "  HWH:       $OUTPUT_DIR/minitpu.hwh ($(du -h "$OUTPUT_DIR/minitpu.hwh" | cut -f1))"

    # Show utilization summary
    if [[ -f "$OUTPUT_DIR/utilization_report.txt" ]]; then
        log "Resource Utilization:"
        grep -A 8 "^| CLB LUTs" "$OUTPUT_DIR/utilization_report.txt" | grep -v "^+" | grep -v "^*" || true
    fi

    # Show timing summary
    if [[ -f "$OUTPUT_DIR/timing_summary.txt" ]]; then
        log "Timing Summary:"
        grep -A 3 "WNS(ns)" "$OUTPUT_DIR/timing_summary.txt" | tail -2 || true
    fi
}

run_tests() {
    log "Running comprehensive test on board $BOARD_IP..."

    cd "$REPO_ROOT"

    BIT_PATH="$OUTPUT_DIR/minitpu.bit"
    HWH_PATH="$OUTPUT_DIR/minitpu.hwh"

    if [[ ! -f "$BIT_PATH" ]]; then
        error "Bitstream not found: $BIT_PATH"
    fi

    log "Compiling test program..."
    python3 "$TESTS_DIR/ultra96-v2/programs/comprehensive.py"

    log "Deploying and running test..."
    if ! make -C "$TESTS_DIR" board-comprehensive \
        BIT="$BIT_PATH" \
        HWH="$HWH_PATH" \
        BOARD_IP="$BOARD_IP" \
        BOARD_USER="$BOARD_USER" \
        BOARD_PASS="$BOARD_PASS"; then
        error "Test failed"
    fi

    log "All tests passed!"
}

# ============================================================================
# Parse Arguments
# ============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -i|--board-ip)
            BOARD_IP="$2"
            shift 2
            ;;
        -u|--board-user)
            BOARD_USER="$2"
            shift 2
            ;;
        -p|--board-pass)
            BOARD_PASS="$2"
            shift 2
            ;;
        --skip-build)
            SKIP_BUILD=1
            shift
            ;;
        --skip-test)
            SKIP_TEST=1
            shift
            ;;
        --clean)
            CLEAN=1
            shift
            ;;
        --tpu-dir)
            TPU_DIR="$2"
            shift 2
            ;;
        --tests-dir)
            TESTS_DIR="$2"
            shift 2
            ;;
        --target)
            TARGET="$2"
            shift 2
            ;;
        --vivado-settings)
            VIVADO_SETTINGS="$2"
            shift 2
            ;;
        *)
            error "Unknown option: $1. Use --help for usage."
            ;;
    esac
done

# ============================================================================
# Main Workflow
# ============================================================================

log "Ultra96-v2 Build and Test"
log "=========================="
log "Repository: $REPO_ROOT"
log "Target:     $TARGET"
log "Output:     $OUTPUT_DIR"

check_prereqs

if [[ "$SKIP_BUILD" == "0" ]]; then
    build_bitstream
else
    log "Skipping build (using existing bitstream)"
fi

if [[ "$SKIP_TEST" == "0" ]]; then
    run_tests
else
    log "Skipping tests"
fi

log ""
log "=========================="
log "Workflow Complete!"
log "=========================="

if [[ "$SKIP_BUILD" == "0" ]]; then
    log "Bitstream: $OUTPUT_DIR/minitpu.bit"
fi

if [[ "$SKIP_TEST" == "0" ]]; then
    log "All tests passed on board $BOARD_IP"
fi
