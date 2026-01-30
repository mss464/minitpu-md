#!/usr/bin/env bash
set -euo pipefail

# Board Test Script for Mini-TPU
#
# This script assembles a temporary deployment folder and runs tests on the FPGA board.
# It uses the refactored structure:
#   - hal/pynq_host.py: Reusable TPU interface
#   - tests/fpga/: Test entry points
#   - fpga/bitstream/: Bitstream artifacts
#
# Usage:
#   ./board_test.sh                    # Run local test
#   RUN_ORIGIN=1 ./board_test.sh       # Compare with origin/main reference

BOARD_USER="${BOARD_USER:-xilinx}"
BOARD_IP="${BOARD_IP:-132.236.59.64}"
BOARD_PASS="${BOARD_PASS:-xilinx}"
DEPLOY_DIR="${DEPLOY_DIR:-~/tpu_deploy}"
ORIGIN_REF="${ORIGIN_REF:-origin/main}"
RUN_ORIGIN="${RUN_ORIGIN:-0}"

# Local artifacts
LOCAL_BIT="${LOCAL_BIT:-fpga/bitstream/minitpu.bit}"
LOCAL_HWH="${LOCAL_HWH:-fpga/bitstream/minitpu.hwh}"
INSTR_FILE="${INSTR_FILE:-tests/fpga/mlp_instructions.txt}"

SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

require() {
    command -v "$1" >/dev/null 2>&1 || { echo "Missing required tool: $1" >&2; exit 1; }
}

require git
require ssh
require scp
require sshpass

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# Verify local files exist
if [[ ! -f "$LOCAL_BIT" || ! -f "$LOCAL_HWH" ]]; then
    echo "Missing local bitstream files: $LOCAL_BIT or $LOCAL_HWH" >&2
    exit 1
fi

# Run origin/main reference test first if requested
if [[ "$RUN_ORIGIN" == "1" ]]; then
    TMP_DIR="$(mktemp -d /tmp/tpu_deploy_origin_main.XXXXXX)"
    trap 'rm -rf "$TMP_DIR"' EXIT

    git show "$ORIGIN_REF:software/tpu_deploy/CornellTPU.bit" > "$TMP_DIR/CornellTPU.bit"
    git show "$ORIGIN_REF:software/tpu_deploy/CornellTPU.hwh" > "$TMP_DIR/CornellTPU.hwh"
    git show "$ORIGIN_REF:software/tpu_deploy/host.py" > "$TMP_DIR/host.py"
    git show "$ORIGIN_REF:software/tpu_deploy/tpu_instructions.txt" > "$TMP_DIR/tpu_instructions.txt"

    sshpass -p "$BOARD_PASS" ssh $SSH_OPTS "${BOARD_USER}@${BOARD_IP}" "mkdir -p ${DEPLOY_DIR}"

    sshpass -p "$BOARD_PASS" scp $SSH_OPTS \
        "$TMP_DIR/CornellTPU.bit" \
        "$TMP_DIR/CornellTPU.hwh" \
        "$TMP_DIR/host.py" \
        "$TMP_DIR/tpu_instructions.txt" \
        "${BOARD_USER}@${BOARD_IP}:${DEPLOY_DIR}/"

    echo "== Running origin/main reference =="
    sshpass -p "$BOARD_PASS" ssh -t $SSH_OPTS "${BOARD_USER}@${BOARD_IP}" \
        "cd ${DEPLOY_DIR} && echo ${BOARD_PASS} | sudo -S python3 host.py CornellTPU.bit tpu_instructions.txt"
fi

# Create temporary deployment folder
DEPLOY_TMP="$(mktemp -d /tmp/tpu_deploy_local.XXXXXX)"
trap 'rm -rf "$DEPLOY_TMP"' EXIT

# Assemble deployment: HAL module + test script + artifacts
mkdir -p "$DEPLOY_TMP/hal"
cp hal/pynq_host.py "$DEPLOY_TMP/hal/"
touch "$DEPLOY_TMP/hal/__init__.py"
cp tests/fpga/test_mlp.py "$DEPLOY_TMP/"
cp "$LOCAL_BIT" "$DEPLOY_TMP/minitpu.bit"
cp "$LOCAL_HWH" "$DEPLOY_TMP/minitpu.hwh"
cp "$INSTR_FILE" "$DEPLOY_TMP/tpu_instructions.txt"

# Deploy to board
sshpass -p "$BOARD_PASS" ssh $SSH_OPTS "${BOARD_USER}@${BOARD_IP}" "echo ${BOARD_PASS} | sudo -S rm -rf ${DEPLOY_DIR} && mkdir -p ${DEPLOY_DIR}"
sshpass -p "$BOARD_PASS" scp -r $SSH_OPTS "$DEPLOY_TMP"/* "${BOARD_USER}@${BOARD_IP}:${DEPLOY_DIR}/"

echo "== Running local bitstream ($(basename "$LOCAL_BIT")) =="
sshpass -p "$BOARD_PASS" ssh -t $SSH_OPTS "${BOARD_USER}@${BOARD_IP}" \
    "cd ${DEPLOY_DIR} && echo ${BOARD_PASS} | sudo -S python3 test_mlp.py minitpu.bit tpu_instructions.txt"
