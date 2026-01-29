################################################################################
# Cornell TPU - Vivado Build Makefile
#
# Automates IP packaging and bitstream generation for the TPU accelerator.
#
# Usage:
#   make all          - Build everything (package IP + generate bitstream)
#   make package_ip   - Package TPU RTL into reusable IP
#   make bitstream    - Build block design and generate bitstream
#   make clean        - Remove all generated files
################################################################################

#===============================================================================
# Configuration - Override these via command line or environment
#===============================================================================

# FPGA part number
PART ?= xczu3eg-sbva484-1-i

# IP settings
IP_NAME ?= cornell_tpu
IP_VERSION ?= 1.0
IP_VENDOR ?= cornell.edu
IP_LIBRARY ?= user

# Directory settings
RTL_DIR ?= ../tpu
IP_REPO_DIR ?= ip_repo
OUTPUT_DIR ?= output
PROJ_NAME ?= tpu_system
BD_NAME ?= minitpu

# Vivado settings
VIVADO ?= vivado
VIVADO_OPTS ?= -mode batch -nojournal

# Script locations (Tcl scripts are in the same directory as Makefile)
PACKAGE_SCRIPT ?= package_tpu_ip.tcl
BUILD_SCRIPT ?= build_bd_bitstream.tcl

#===============================================================================
# Derived paths
#===============================================================================

IP_OUT_DIR := $(IP_REPO_DIR)/$(IP_NAME)_$(IP_VERSION)
COMPONENT_XML := $(IP_OUT_DIR)/component.xml
ARTIFACTS_DIR := $(OUTPUT_DIR)/artifacts
BITSTREAM := $(ARTIFACTS_DIR)/$(BD_NAME)_wrapper.bit
HWH := $(ARTIFACTS_DIR)/$(BD_NAME).hwh

#===============================================================================
# Deployment Configuration
#===============================================================================

BOARD_IP ?= 132.236.59.64
BOARD_USER ?= xilinx
BOARD_PASS ?= xilinx
DEPLOY_DIR ?= ~/tpu_deploy
HOST_SCRIPT ?= ../software/host.py
INSTR_FILE ?= ../software/tpu_deploy/tpu_instructions.txt

#===============================================================================
# Main targets
#===============================================================================

.PHONY: all package_ip bitstream clean clean_ip clean_output help deploy run

# Default target: build everything
all: bitstream

# Show help
help:
	@echo "Cornell TPU - Vivado Build System"
	@echo ""
	@echo "Usage: make [target] [VARIABLE=value ...]"
	@echo ""
	@echo "Targets:"
	@echo "  all          Build everything (package IP + generate bitstream)"
	@echo "  package_ip   Package TPU RTL into reusable IP core"
	@echo "  bitstream    Build block design and generate bitstream"
	@echo "  clean        Remove all generated files"
	@echo "  clean_ip     Remove only IP repository"
	@echo "  clean_output Remove only output directory"
	@echo "  help         Show this help message"
	@echo ""
	@echo "Configuration variables:"
	@echo "  PART         FPGA part number (default: $(PART))"
	@echo "  IP_NAME      IP core name (default: $(IP_NAME))"
	@echo "  IP_VERSION   IP version (default: $(IP_VERSION))"
	@echo "  RTL_DIR      RTL source directory (default: $(RTL_DIR))"
	@echo "  IP_REPO_DIR  IP repository output (default: $(IP_REPO_DIR))"
	@echo "  OUTPUT_DIR   Build output directory (default: $(OUTPUT_DIR))"
	@echo "  PROJ_NAME    Project name (default: $(PROJ_NAME))"
	@echo "  VIVADO       Vivado executable (default: $(VIVADO))"
	@echo ""
	@echo "Examples:"
	@echo "  make all PART=xczu9eg-ffvb1156-2-e"
	@echo "  make package_ip IP_NAME=my_tpu"
	@echo "  make bitstream OUTPUT_DIR=build"

#===============================================================================
# IP Packaging
#===============================================================================

# Package TPU IP
package_ip: $(COMPONENT_XML)

$(COMPONENT_XML): $(wildcard $(RTL_DIR)/*.v) $(wildcard $(RTL_DIR)/*.sv)
	@echo "=========================================="
	@echo "Packaging TPU IP: $(IP_NAME) v$(IP_VERSION)"
	@echo "=========================================="
	@mkdir -p $(IP_REPO_DIR)
	$(VIVADO) $(VIVADO_OPTS) -source $(PACKAGE_SCRIPT) -tclargs \
		-ip_name $(IP_NAME) \
		-ip_version $(IP_VERSION) \
		-ip_vendor $(IP_VENDOR) \
		-ip_library $(IP_LIBRARY) \
		-part $(PART) \
		-rtl_dir $(RTL_DIR) \
		-repo_out $(IP_REPO_DIR)
	@echo ""
	@echo "IP packaged successfully: $(IP_OUT_DIR)"
	@echo ""

#===============================================================================
# Bitstream Generation
#===============================================================================

# Build block design and generate bitstream
bitstream: $(BITSTREAM)

$(BITSTREAM): $(COMPONENT_XML)
	@echo "=========================================="
	@echo "Building Block Design and Bitstream"
	@echo "=========================================="
	@mkdir -p $(OUTPUT_DIR)
	$(VIVADO) $(VIVADO_OPTS) -source $(BUILD_SCRIPT) -tclargs \
		-proj_name $(PROJ_NAME) \
		-part $(PART) \
		-ip_repo_path $(IP_REPO_DIR) \
		-out_dir $(OUTPUT_DIR) \
		-bd_name $(BD_NAME)
	@echo ""
	@echo "Build complete!"
	@echo "Artifacts: $(ARTIFACTS_DIR)"
	@ls -la $(ARTIFACTS_DIR)/
	@echo ""

#===============================================================================
# Clean targets
#===============================================================================

clean: clean_ip clean_output
	@echo "Cleaned all generated files"
	-rm -rf pkg_*_proj
	-rm -rf .Xil
	-rm -rf *.log *.jou

clean_ip:
	@echo "Cleaning IP repository..."
	-rm -rf $(IP_REPO_DIR)

clean_output:
	@echo "Cleaning output directory..."
	-rm -rf $(OUTPUT_DIR)

#===============================================================================
# Utility targets
#===============================================================================

.PHONY: info gui

# Print configuration info
info:
	@echo "Cornell TPU Build Configuration"
	@echo "================================"
	@echo "PART:        $(PART)"
	@echo "IP_NAME:     $(IP_NAME)"
	@echo "IP_VERSION:  $(IP_VERSION)"
	@echo "RTL_DIR:     $(RTL_DIR)"
	@echo "IP_REPO_DIR: $(IP_REPO_DIR)"
	@echo "OUTPUT_DIR:  $(OUTPUT_DIR)"
	@echo "PROJ_NAME:   $(PROJ_NAME)"
	@echo "VIVADO:      $(VIVADO)"
	@echo ""
	@echo "RTL files:"
	@ls -1 $(RTL_DIR)/*.v $(RTL_DIR)/*.sv 2>/dev/null | head -10
	@echo "..."

# Open project in Vivado GUI (after build)
gui:
	@if [ -f "$(OUTPUT_DIR)/$(PROJ_NAME)/$(PROJ_NAME).xpr" ]; then \
		$(VIVADO) $(OUTPUT_DIR)/$(PROJ_NAME)/$(PROJ_NAME).xpr & \
	else \
		echo "Project not found. Run 'make bitstream' first."; \
	fi

#===============================================================================
# Deployment & Execution
#===============================================================================

# Copy artifacts to PYNQ board
deploy:
	@echo "=========================================="
	@echo "Deploying to $(BOARD_USER)@$(BOARD_IP):$(DEPLOY_DIR)"
	@echo "=========================================="
	@ssh $(BOARD_USER)@$(BOARD_IP) "mkdir -p $(DEPLOY_DIR)"
	@scp $(BITSTREAM) $(HWH) $(HOST_SCRIPT) $(INSTR_FILE) $(BOARD_USER)@$(BOARD_IP):$(DEPLOY_DIR)/
	@echo "Deployment complete."
	@echo ""

# Run benchmark on PYNQ board (automates sudo password)
run: deploy
	@echo "=========================================="
	@echo "Running benchmark on PYNQ..."
	@echo "=========================================="
	@echo "Executing: sudo python3 host.py $(notdir $(BITSTREAM)) tpu_instructions.txt"
	@ssh -t $(BOARD_USER)@$(BOARD_IP) "cd $(DEPLOY_DIR) && echo $(BOARD_PASS) | sudo -S python3 host.py $(notdir $(BITSTREAM)) tpu_instructions.txt"

