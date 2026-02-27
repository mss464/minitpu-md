# Mini-TPU tests Makefile
# Keep this lightweight; this workflow is under refactor.

# Quick Start
# -----------
# Comprehensive test (kernel API):
#   make -C tests board-comprehensive BIT=path/to/minitpu.bit HWH=path/to/minitpu.hwh
#
# If auto-detect fails, specify IP names:
#   make -C tests board-comprehensive BIT=... HWH=... TPU_IP=tpu_top_0 DMA_IP=axi_dma_0
#
# MLP test (legacy):
#   make -C tests board-mlp BIT=... HWH=...

# Reference flow (manual)
# ----------------------------------------
# # Ensure project root is in PYTHONPATH
# export PYTHONPATH=.
#
# # 1. Generate Instruction Trace via Compiler CLI
# python3 compiler/cli.py torch/examples/mlp.py -o tests/ultra96-v2/mlp_instruction_trace.txt
#
# # 2. Compile Artifacts (Generates tests/ultra96-v2/mlp_instructions.txt and tests/ultra96-v2/test_generated.py)
# python3 compiler/assembler.py tests/ultra96-v2/mlp_instruction_trace.txt tests/ultra96-v2/mlp_instructions.txt
#
# # 3. Stage Artifacts for Deployment
# mv tests/ultra96-v2/test_generated.py tests/ultra96-v2/test_mlp_generated.py
# cp tests/ultra96-v2/test_mlp_generated.py tests/ultra96-v2/test_mlp.py

ROOT := $(abspath $(CURDIR)/..)
SHELL := /usr/bin/env bash
PYTHONPATH ?= $(ROOT)
BOARD_TEST_SH ?= $(ROOT)/agent-skills/ultra96-v2/deploy/scripts/board_test.sh

INSTR_TRACE ?= $(ROOT)/tests/ultra96-v2/mlp_instruction_trace.txt
INSTR_TXT ?= $(ROOT)/tests/ultra96-v2/mlp_instructions.txt
GEN_TEST ?= $(ROOT)/tests/ultra96-v2/test_generated.py
GEN_TEST_NAMED ?= $(ROOT)/tests/ultra96-v2/test_mlp_generated.py
TEST_MLP ?= $(ROOT)/tests/ultra96-v2/test_mlp.py
TRACE_FILE ?= $(ROOT)/tests/ultra96-v2/mlp_instruction_trace.txt

# Board deployment inputs (fill in paths for your bitstream)
BIT ?= path/to/xx.bit
HWH ?= path/to/xx.hwh
PROGRAM ?= $(TEST_MLP)
INSTR_FILE ?= $(INSTR_TXT)
BOARD_USER ?= xilinx
BOARD_IP ?= 132.236.59.64
BOARD_PASS ?= xilinx
DEPLOY_DIR ?= ~/tpu_deploy
ORIGIN_REF ?= origin/main
RUN_ORIGIN ?= 0
# Optional: additional files to copy (e.g., .npy, .json)
EXTRA_FILES ?=
# Optional: IP block names (auto-detect if not specified)
TPU_IP ?=
DMA_IP ?=

.PHONY: gen-mlp stage-mlp board-test board-mlp board-comprehensive show-runtime board-data-integrity

# Generate instruction trace + compile artifacts
# Usage: make -C tests gen-mlp
#   (Outputs: $(INSTR_TRACE), $(INSTR_TXT), $(GEN_TEST))
gen-mlp:
	PYTHONPATH=$(PYTHONPATH) \
	python3 $(ROOT)/compiler/cli.py $(ROOT)/torch/examples/mlp.py -o $(INSTR_TRACE)
	PYTHONPATH=$(PYTHONPATH) \
	python3 $(ROOT)/compiler/assembler.py $(INSTR_TRACE) $(INSTR_TXT)

# Stage generated test for deployment
# Usage: make -C tests stage-mlp
stage-mlp: $(GEN_TEST)
	mv $(GEN_TEST) $(GEN_TEST_NAMED)
	cp $(GEN_TEST_NAMED) $(TEST_MLP)

# Run board test (script is maintained in agent-skills)
# Usage: make -C tests board-test BIT=/path/xx.bit HWH=/path/xx.hwh PROGRAM=$(TEST_MLP)
board-test:
	@set -euo pipefail; \
	require() { command -v "$$1" >/dev/null 2>&1 || { echo "Missing required tool: $$1" >&2; exit 1; }; }; \
	require git; require ssh; require scp; require sshpass; \
	REPO_ROOT="$$(git rev-parse --show-toplevel)"; \
	cd "$$REPO_ROOT"; \
	LOCAL_BIT="$(BIT)"; \
	LOCAL_HWH="$(HWH)"; \
	PROGRAM_PATH="$(PROGRAM)"; \
	INSTR_PATH="$(INSTR_FILE)"; \
	TRACE_PATH="$(TRACE_FILE)"; \
	if [[ ! -f "$$LOCAL_BIT" || ! -f "$$LOCAL_HWH" ]]; then \
		echo "Missing local bitstream files: $$LOCAL_BIT or $$LOCAL_HWH" >&2; \
		exit 1; \
	fi; \
	if [[ ! -f "$$PROGRAM_PATH" ]]; then \
		echo "Missing test program: $$PROGRAM_PATH" >&2; \
		exit 1; \
	fi; \
	SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"; \
	if [[ "$(RUN_ORIGIN)" == "1" ]]; then \
		TMP_DIR="$$(mktemp -d /tmp/tpu_deploy_origin_main.XXXXXX)"; \
		trap 'rm -rf "$$TMP_DIR"' EXIT; \
		git show "$(ORIGIN_REF):software/tpu_deploy/CornellTPU.bit" > "$$TMP_DIR/CornellTPU.bit"; \
		git show "$(ORIGIN_REF):software/tpu_deploy/CornellTPU.hwh" > "$$TMP_DIR/CornellTPU.hwh"; \
		git show "$(ORIGIN_REF):software/tpu_deploy/host.py" > "$$TMP_DIR/host.py"; \
		git show "$(ORIGIN_REF):software/tpu_deploy/tpu_instructions.txt" > "$$TMP_DIR/tpu_instructions.txt"; \
		sshpass -p "$(BOARD_PASS)" ssh $$SSH_OPTS "$(BOARD_USER)@$(BOARD_IP)" "mkdir -p $(DEPLOY_DIR)"; \
		sshpass -p "$(BOARD_PASS)" scp $$SSH_OPTS \
			"$$TMP_DIR/CornellTPU.bit" \
			"$$TMP_DIR/CornellTPU.hwh" \
			"$$TMP_DIR/host.py" \
			"$$TMP_DIR/tpu_instructions.txt" \
			"$(BOARD_USER)@$(BOARD_IP):$(DEPLOY_DIR)/"; \
		echo "== Running origin/main reference =="; \
		sshpass -p "$(BOARD_PASS)" ssh -t $$SSH_OPTS "$(BOARD_USER)@$(BOARD_IP)" \
			"cd $(DEPLOY_DIR) && echo $(BOARD_PASS) | sudo -S python3 host.py CornellTPU.bit tpu_instructions.txt"; \
	fi; \
	DEPLOY_TMP="$$(mktemp -d /tmp/tpu_deploy_local.XXXXXX)"; \
	trap 'rm -rf "$$DEPLOY_TMP"' EXIT; \
	mkdir -p "$$DEPLOY_TMP/compiler/hal"; \
	cp compiler/hal/pynq_host.py "$$DEPLOY_TMP/compiler/hal/"; \
	touch "$$DEPLOY_TMP/compiler/__init__.py"; \
	touch "$$DEPLOY_TMP/compiler/hal/__init__.py"; \
	PROGRAM_NAME="$$(basename "$$PROGRAM_PATH")"; \
	PROGRAM_DIR="$$(dirname "$$PROGRAM_PATH")"; \
	cp "$$PROGRAM_PATH" "$$DEPLOY_TMP/$$PROGRAM_NAME"; \
	cp "$$LOCAL_BIT" "$$DEPLOY_TMP/minitpu.bit"; \
	cp "$$LOCAL_HWH" "$$DEPLOY_TMP/minitpu.hwh"; \
	if [[ -f "$$INSTR_PATH" ]]; then cp "$$INSTR_PATH" "$$DEPLOY_TMP/tpu_instructions.txt"; fi; \
	if [[ -f "$$TRACE_PATH" ]]; then cp "$$TRACE_PATH" "$$DEPLOY_TMP/tpu_trace.txt"; fi; \
	for extra_file in $(EXTRA_FILES); do \
		if [[ -f "$$extra_file" ]]; then \
			cp "$$extra_file" "$$DEPLOY_TMP/$$(basename "$$extra_file")"; \
		fi; \
	done; \
	sshpass -p "$(BOARD_PASS)" ssh $$SSH_OPTS "$(BOARD_USER)@$(BOARD_IP)" \
		"echo $(BOARD_PASS) | sudo -S rm -rf $(DEPLOY_DIR) && mkdir -p $(DEPLOY_DIR)"; \
	sshpass -p "$(BOARD_PASS)" scp -r $$SSH_OPTS "$$DEPLOY_TMP"/* "$(BOARD_USER)@$(BOARD_IP):$(DEPLOY_DIR)/"; \
	echo "== Running local bitstream ($$(basename "$$LOCAL_BIT")) =="; \
	PROG_ARGS="minitpu.bit"; \
	if [[ -f "$$INSTR_PATH" ]]; then PROG_ARGS="$$PROG_ARGS tpu_instructions.txt"; fi; \
	if [[ -f "$$TRACE_PATH" ]]; then PROG_ARGS="$$PROG_ARGS --trace tpu_trace.txt"; fi; \
	if [[ -n "$(TPU_IP)" ]]; then PROG_ARGS="$$PROG_ARGS --tpu-ip $(TPU_IP)"; fi; \
	if [[ -n "$(DMA_IP)" ]]; then PROG_ARGS="$$PROG_ARGS --dma-ip $(DMA_IP)"; fi; \
	sshpass -p "$(BOARD_PASS)" ssh -t $$SSH_OPTS "$(BOARD_USER)@$(BOARD_IP)" \
	"cd $(DEPLOY_DIR) && echo $(BOARD_PASS) | sudo -S python3 $$PROGRAM_NAME $$PROG_ARGS"

# One-shot: generate MLP instructions + stage test + run board test
# Usage: make -C tests board-mlp BIT=/path/xx.bit HWH=/path/xx.hwh
board-mlp: gen-mlp stage-mlp
	@$(MAKE) --no-print-directory board-test \
		BIT="$(BIT)" HWH="$(HWH)" PROGRAM="$(TEST_MLP)" INSTR_FILE="$(INSTR_TXT)"

# Compile and run comprehensive test
# Usage: make -C tests board-comprehensive BIT=/path/xx.bit HWH=/path/xx.hwh
# Optional: TPU_IP=tpu_top_0 DMA_IP=axi_dma_0 (auto-detect if not specified)
.PHONY: board-comprehensive
board-comprehensive:
	@echo "Compiling comprehensive test program..."
	@python3 $(ROOT)/tests/ultra96-v2/programs/comprehensive.py
	@$(MAKE) --no-print-directory board-test \
		BIT="$(BIT)" \
		HWH="$(HWH)" \
		PROGRAM="$(ROOT)/tests/ultra96-v2/test_comprehensive.py" \
		INSTR_FILE="" \
		TRACE_FILE="" \
		EXTRA_FILES="$(ROOT)/tests/ultra96-v2/comprehensive.npy $(ROOT)/tests/ultra96-v2/comprehensive_meta.json" \
		TPU_IP="$(TPU_IP)" \
		DMA_IP="$(DMA_IP)"

# Compile and run SIMD comparison test
# Usage: make -C tests board-simd-comparison BIT=/path/xx.bit HWH=/path/xx.hwh
.PHONY: board-simd-comparison
board-simd-comparison:
	@echo "Compiling SIMD comparison test program..."
	@python3 $(ROOT)/tests/ultra96-v2/programs/simd_comparison.py
	@$(MAKE) --no-print-directory board-test \
		BIT="$(BIT)" \
		HWH="$(HWH)" \
		PROGRAM="$(ROOT)/tests/ultra96-v2/test_simd_comparison.py" \
		INSTR_FILE="" \
		TRACE_FILE="" \
		EXTRA_FILES="$(ROOT)/tests/ultra96-v2/simd_comparison.npy $(ROOT)/tests/ultra96-v2/simd_comparison_meta.json" \
		TPU_IP="$(TPU_IP)" \
		DMA_IP="$(DMA_IP)"

# Run basic data integrity test (no compute, just BRAM read/write)
# Usage: make -C tests board-data-integrity BIT=/path/xx.bit HWH=/path/xx.hwh
# Compile and run SIMD edge case tests (18 corner cases)
# Usage: make -C tests board-simd-edge-cases BIT=/path/xx.bit HWH=/path/xx.hwh
.PHONY: board-simd-edge-cases
board-simd-edge-cases:
	@echo "Compiling SIMD edge case test program..."
	@PYTHONPATH=$(ROOT) python3 $(ROOT)/tests/ultra96-v2/programs/simd_edge_cases.py
	@$(MAKE) --no-print-directory board-test \
		BIT="$(BIT)" \
		HWH="$(HWH)" \
		PROGRAM="$(ROOT)/tests/ultra96-v2/test_simd_edge_cases.py" \
		INSTR_FILE="" \
		TRACE_FILE="" \
		EXTRA_FILES="$(ROOT)/tests/ultra96-v2/simd_edge_cases.npy $(ROOT)/tests/ultra96-v2/simd_edge_cases_meta.json" \
		TPU_IP="$(TPU_IP)" \
		DMA_IP="$(DMA_IP)"

# Compile and run SIMD pressure/performance test (scalar vs SIMD timing)
# Usage: make -C tests board-simd-pressure BIT=/path/xx.bit HWH=/path/xx.hwh
.PHONY: board-simd-pressure
board-simd-pressure:
	@echo "Compiling SIMD pressure test programs..."
	@PYTHONPATH=$(ROOT) python3 $(ROOT)/tests/ultra96-v2/programs/simd_pressure.py
	@$(MAKE) --no-print-directory board-test \
		BIT="$(BIT)" \
		HWH="$(HWH)" \
		PROGRAM="$(ROOT)/tests/ultra96-v2/test_simd_pressure.py" \
		INSTR_FILE="" \
		TRACE_FILE="" \
		EXTRA_FILES="$(ROOT)/tests/ultra96-v2/pressure_scalar.npy $(ROOT)/tests/ultra96-v2/pressure_simd.npy $(ROOT)/tests/ultra96-v2/pressure_meta.json" \
		TPU_IP="$(TPU_IP)" \
		DMA_IP="$(DMA_IP)"

# Diagnostic debug test: progressive isolation of pressure test zero-output issue
# Usage: make -C tests board-pressure-debug BIT=/path/xx.bit HWH=/path/xx.hwh
.PHONY: board-pressure-debug
board-pressure-debug:
	@echo "Deploying pressure debug test..."
	@$(MAKE) --no-print-directory board-test \
		BIT="$(BIT)" \
		HWH="$(HWH)" \
		PROGRAM="$(ROOT)/tests/ultra96-v2/test_pressure_debug.py" \
		INSTR_FILE="" \
		TRACE_FILE="" \
		EXTRA_FILES="$(ROOT)/tests/ultra96-v2/pressure_debug_mini.npy $(ROOT)/tests/ultra96-v2/pressure_simd.npy $(ROOT)/tests/ultra96-v2/pressure_scalar.npy $(ROOT)/tests/ultra96-v2/simd_edge_cases.hex $(ROOT)/tests/ultra96-v2/pressure_meta.json" \
		TPU_IP="$(TPU_IP)" \
		DMA_IP="$(DMA_IP)"

.PHONY: board-data-integrity
board-data-integrity:
	@$(MAKE) --no-print-directory board-test \
		BIT="$(BIT)" \
		HWH="$(HWH)" \
		PROGRAM="$(ROOT)/tests/ultra96-v2/test_data_integrity.py" \
		INSTR_FILE="" \
		TRACE_FILE="" \
		TPU_IP="$(TPU_IP)" \
		DMA_IP="$(DMA_IP)"

# Show what runtime files get deployed
.PHONY: show-runtime
show-runtime:
	@echo "Runtime files deployed to board:"
	@echo "  compiler/__init__.py (package marker)"
	@echo "  compiler/hal/__init__.py (package marker)"
	@echo "  compiler/hal/pynq_host.py (TpuDriver)"
	@echo ""
	@echo "Dependencies:"
	@echo "  - Python stdlib: time, json, pathlib, argparse"
	@echo "  - numpy (installed on PYNQ)"
	@echo "  - pynq (installed on PYNQ)"
	@echo ""
	@echo "NOT deployed (compilation-only):"
	@echo "  - compiler/kernel.py"
	@echo "  - compiler/program.py"
	@echo "  - compiler/kernels/"
	@echo "  - compiler/assembler.py"
	@echo "  - compiler/runtime/allocator.py"
