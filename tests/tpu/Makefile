#==============================================================================
# Mini-TPU RTL Unit Test Makefile
# Run from: tests/tpu/
# Usage: make test_<module> or make all
#==============================================================================

# Compiler and simulator settings
IVERILOG = iverilog
VVP = vvp
# cocotb 2.0+ path detection
COCOTB_LIBS = $(shell python3 -c "import cocotb; import os; print(os.path.join(os.path.dirname(cocotb.__file__), 'libs'))")

# Directories
TPU_DIR = ../../tpu
SIM_BUILD = sim_build
WAVEFORMS = waveforms
WRAPPERS = wrappers

# Environment variables for cocotb
export COCOTB_REDUCED_LOG_FMT = 1
export LIBPYTHON_LOC = $(shell python3 -c "import find_libpython; print(find_libpython.find_libpython())")
export PYTHONPATH := $(PWD):$(PYTHONPATH)
export PYGPI_PYTHON_BIN = $(shell which python3)

# Iverilog flags
IVFLAGS = -g2012 -Wall

#==============================================================================
# RTL Source Files (grouped by category)
#==============================================================================

# Core arithmetic
SRC_FP32 = $(TPU_DIR)/fp32_add.sv $(TPU_DIR)/fp32_mul.sv
SRC_FIXEDPOINT = $(TPU_DIR)/fixedpoint.sv
SRC_VADD = $(TPU_DIR)/vadd.sv

# Control and memory
SRC_FIFO = $(TPU_DIR)/fifo4.sv
SRC_PC = $(TPU_DIR)/pc.sv
SRC_DECODER = $(TPU_DIR)/decoder.sv
SRC_BRAM = $(TPU_DIR)/bram_top.sv $(TPU_DIR)/sram_behavioral.sv

# Processing elements
SRC_PE = $(TPU_DIR)/pe.sv $(SRC_FP32)
SRC_SYSTOLIC = $(TPU_DIR)/systolic.sv $(SRC_PE)
SRC_SYSTOLIC_WRAPPER = $(TPU_DIR)/systolic_wrapperv2.sv $(SRC_SYSTOLIC)

# VPU
SRC_VPU_OP = $(TPU_DIR)/vpu_op.sv $(SRC_FP32)
SRC_VPU_TOP = $(TPU_DIR)/vpu_top.sv $(SRC_VPU_OP)

# All sources for comprehensive tests
SRC_ALL = $(TPU_DIR)/pe.sv \
          $(TPU_DIR)/systolic.sv \
          $(TPU_DIR)/systolic_wrapperv2.sv \
          $(TPU_DIR)/fixedpoint.sv \
          $(TPU_DIR)/fp32_add.sv \
          $(TPU_DIR)/fp32_mul.sv \
          $(TPU_DIR)/fifo4.sv \
          $(TPU_DIR)/pc.sv \
          $(TPU_DIR)/decoder.sv \
          $(TPU_DIR)/vadd.sv \
          $(TPU_DIR)/vpu_op.sv

#==============================================================================
# Test Targets - Unit Tests for Individual Modules
#==============================================================================

# FIFO unit test
test_fifo4: $(SIM_BUILD)
	@echo "=== Running FIFO4 Unit Test ==="
	$(IVERILOG) -o $(SIM_BUILD)/sim.vvp -s fifo4 -s dump $(IVFLAGS) \
		$(SRC_FIFO) $(WRAPPERS)/dump_fifo4.sv
	COCOTB_TEST_MODULES=test_fifo4 $(VVP) -M $(COCOTB_LIBS) -m libcocotbvpi_icarus $(SIM_BUILD)/sim.vvp
	@! grep -q 'failure' results.xml || (echo "TEST FAILED" && exit 1)
	@mv -f fifo4.vcd $(WAVEFORMS)/ 2>/dev/null || true
	@echo "=== FIFO4 Test Complete ==="

# Decoder unit test
test_decoder: $(SIM_BUILD)
	@echo "=== Running Decoder Unit Test ==="
	$(IVERILOG) -o $(SIM_BUILD)/sim.vvp -s decoder -s dump $(IVFLAGS) \
		$(SRC_DECODER) $(WRAPPERS)/dump_decoder.sv
	COCOTB_TEST_MODULES=test_decoder $(VVP) -M $(COCOTB_LIBS) -m libcocotbvpi_icarus $(SIM_BUILD)/sim.vvp
	@! grep -q 'failure' results.xml || (echo "TEST FAILED" && exit 1)
	@mv -f decoder.vcd $(WAVEFORMS)/ 2>/dev/null || true
	@echo "=== Decoder Test Complete ==="

# ISA Decoder test (tests actual instruction encoding per docs/system.md)
test_isa_decoder: $(SIM_BUILD)
	@echo "=== Running ISA Decoder Test ==="
	$(IVERILOG) -o $(SIM_BUILD)/sim.vvp -s decoder -s dump $(IVFLAGS) \
		$(SRC_DECODER) $(WRAPPERS)/dump_decoder.sv
	COCOTB_TEST_MODULES=test_isa_decoder $(VVP) -M $(COCOTB_LIBS) -m libcocotbvpi_icarus $(SIM_BUILD)/sim.vvp
	@! grep -q 'failure' results.xml || (echo "TEST FAILED" && exit 1)
	@mv -f decoder.vcd $(WAVEFORMS)/ 2>/dev/null || true
	@echo "=== ISA Decoder Test Complete ==="

# Systolic sequential test (tests for stale weight bug)
test_systolic_wrapper: $(SIM_BUILD)
	@echo "=== Running Systolic Sequential Test ==="
	$(IVERILOG) -o $(SIM_BUILD)/sim.vvp -s systolic_wrapper $(IVFLAGS) $(SRC_SYSTOLIC_WRAPPER)
	COCOTB_TEST_MODULES=test_systolic_wrapper $(VVP) -M $(COCOTB_LIBS) -m libcocotbvpi_icarus $(SIM_BUILD)/sim.vvp
	@! grep -q 'failure' results.xml || (echo "TEST FAILED" && exit 1)
	@echo "=== Systolic Sequential Test Complete ==="

# Program Counter unit test
test_pc: $(SIM_BUILD)
	@echo "=== Running PC Unit Test ==="
	$(IVERILOG) -o $(SIM_BUILD)/sim.vvp -s pc -s dump $(IVFLAGS) \
		$(SRC_PC) $(WRAPPERS)/dump_pc.sv
	COCOTB_TEST_MODULES=test_pc $(VVP) -M $(COCOTB_LIBS) -m libcocotbvpi_icarus $(SIM_BUILD)/sim.vvp
	@! grep -q 'failure' results.xml || (echo "TEST FAILED" && exit 1)
	@mv -f pc.vcd $(WAVEFORMS)/ 2>/dev/null || true
	@echo "=== PC Test Complete ==="

# Vector Add unit test
test_vadd: $(SIM_BUILD)
	@echo "=== Running VADD Unit Test ==="
	$(IVERILOG) -o $(SIM_BUILD)/sim.vvp -s vadd -s dump $(IVFLAGS) \
		$(SRC_VADD) $(WRAPPERS)/dump_vadd.sv
	COCOTB_TEST_MODULES=test_vadd $(VVP) -M $(COCOTB_LIBS) -m libcocotbvpi_icarus $(SIM_BUILD)/sim.vvp
	@! grep -q 'failure' results.xml || (echo "TEST FAILED" && exit 1)
	@mv -f vadd.vcd $(WAVEFORMS)/ 2>/dev/null || true
	@echo "=== VADD Test Complete ==="

# FP32 Add unit test
test_fp32_add: $(SIM_BUILD)
	@echo "=== Running FP32 Add Unit Test ==="
	$(IVERILOG) -o $(SIM_BUILD)/sim.vvp -s fp32_add -s dump $(IVFLAGS) \
		$(SRC_FP32) $(WRAPPERS)/dump_fp32_add.sv
	COCOTB_TEST_MODULES=test_fp32_add $(VVP) -M $(COCOTB_LIBS) -m libcocotbvpi_icarus $(SIM_BUILD)/sim.vvp
	@! grep -q 'failure' results.xml || (echo "TEST FAILED" && exit 1)
	@mv -f fp32_add.vcd $(WAVEFORMS)/ 2>/dev/null || true
	@echo "=== FP32 Add Test Complete ==="

# FP32 Mul unit test
test_fp32_mul: $(SIM_BUILD)
	@echo "=== Running FP32 Mul Unit Test ==="
	$(IVERILOG) -o $(SIM_BUILD)/sim.vvp -s fp32_mul -s dump $(IVFLAGS) \
		$(SRC_FP32) $(WRAPPERS)/dump_fp32_mul.sv
	COCOTB_TEST_MODULES=test_fp32_mul $(VVP) -M $(COCOTB_LIBS) -m libcocotbvpi_icarus $(SIM_BUILD)/sim.vvp
	@! grep -q 'failure' results.xml || (echo "TEST FAILED" && exit 1)
	@mv -f fp32_mul.vcd $(WAVEFORMS)/ 2>/dev/null || true
	@echo "=== FP32 Mul Test Complete ==="

# PE (Processing Element) unit test
test_pe: $(SIM_BUILD)
	@echo "=== Running PE Unit Test ==="
	$(IVERILOG) -o $(SIM_BUILD)/sim.vvp -s pe $(IVFLAGS) $(SRC_PE)
	COCOTB_TEST_MODULES=test_pe $(VVP) -M $(COCOTB_LIBS) -m libcocotbvpi_icarus $(SIM_BUILD)/sim.vvp
	@! grep -q 'failure' results.xml || (echo "TEST FAILED" && exit 1)
	@echo "=== PE Test Complete ==="

# VPU operation unit test (requires parameterized_adder/mul wrappers)
test_vpu_op: $(SIM_BUILD)
	@echo "=== Running VPU Op Unit Test ==="
	@echo "Note: vpu_op requires parameterized_adder and parameterized_mul modules"
	$(IVERILOG) -o $(SIM_BUILD)/sim.vvp -s vpu_op -s dump $(IVFLAGS) \
		$(SRC_VPU_OP) $(WRAPPERS)/dump_vpu_op.sv || \
		echo "Warning: vpu_op has dependencies that may need resolution"

test_systolic_array: $(SIM_BUILD)
	@echo "=== Running Random Systolic Test ==="
	$(IVERILOG) -o $(SIM_BUILD)/sim.vvp -s systolic $(IVFLAGS) $(SRC_SYSTOLIC)
	COCOTB_TEST_MODULES=test_systolic_array $(VVP) -M $(COCOTB_LIBS) -m libcocotbvpi_icarus $(SIM_BUILD)/sim.vvp
	@! grep -q 'failure' results.xml || (echo "TEST FAILED" && exit 1)

#==============================================================================
# Aggregate Test Targets
#==============================================================================

# Core unit tests (fast, independent modules)
test_unit: test_fifo4 test_decoder test_pc test_vadd test_fp32_add test_fp32_mul
	@echo ""
	@echo "========================================"
	@echo "All unit tests completed successfully!"
	@echo "========================================"

# PE and systolic tests
test_compute: test_pe test_systolic_array test_systolic_wrapper
	@echo ""
	@echo "========================================"
	@echo "All compute tests completed successfully!"
	@echo "========================================"

# Systolic wrapper tests
test_wrappers: test_systolic_wrapper
	@echo ""
	@echo "========================================"
	@echo "All wrapper tests completed!"
	@echo "========================================"

# Run ALL tests
all: test_unit test_compute
	@echo ""
	@echo "========================================"
	@echo "ALL TESTS PASSED"
	@echo "========================================"

# Comprehensive test
test_all: test_unit test_compute test_wrappers
	@echo ""
	@echo "========================================"
	@echo "COMPREHENSIVE TEST SUITE PASSED"
	@echo "========================================"

#==============================================================================
# Infrastructure
#==============================================================================

# Create build directories
$(SIM_BUILD):
	mkdir -p $(SIM_BUILD)
	mkdir -p $(WAVEFORMS)

# Waveform viewing (usage: make show_fifo4)
show_%: $(WAVEFORMS)/%.vcd
	gtkwave $<

# Linting with Verilator
lint:
	verilator --lint-only -Wall $(SRC_ALL) 2>&1 | head -50

# Linting with Verible (if available)
lint_verible:
	verible-verilog-lint $(TPU_DIR)/*.sv --rules_config verible.rules 2>/dev/null || echo "Verible not found"

# Cleanup
clean:
	rm -rf $(SIM_BUILD) $(WAVEFORMS)/*.vcd results.xml __pycache__ *.vcd

# Deep clean (includes pycache)
distclean: clean
	rm -rf __pycache__ .pytest_cache

# Help
help:
	@echo "Mini-TPU RTL Test Makefile"
	@echo ""
	@echo "Unit Tests (Individual Modules):"
	@echo "  make test_fifo4       - FIFO unit test"
	@echo "  make test_decoder     - Instruction decoder test"
	@echo "  make test_pc          - Program counter test"
	@echo "  make test_vadd        - Vector add test"
	@echo "  make test_fp32_add    - FP32 adder test"
	@echo "  make test_fp32_mul    - FP32 multiplier test"
	@echo "  make test_pe          - Processing element test"
	@echo "  make test_systolic_array     - Systolic array random test (100 cases)"
	@echo "  make test_systolic_wrapper - Systolic wrapper sequential test"
	@echo ""
	@echo "Aggregate Test Targets:"
	@echo "  make test_unit        - All unit tests (fast)"
	@echo "  make test_compute     - PE and systolic tests"
	@echo "  make all              - Unit + compute tests"
	@echo "  make test_all         - Comprehensive test suite"
	@echo ""
	@echo "Utilities:"
	@echo "  make lint             - Lint with Verilator"
	@echo "  make show_<module>    - View waveform (e.g., show_fifo4)"
	@echo "  make clean            - Remove build artifacts"
	@echo "  make help             - Show this help"

.PHONY: all clean distclean lint lint_verible help
.PHONY: test_unit test_compute test_wrappers test_all
.PHONY: test_fifo4 test_decoder test_pc test_vadd test_fp32_add test_fp32_mul
.PHONY: test_pe test_systolic_array test_vpu_op test_isa_decoder test_systolic_wrapper
