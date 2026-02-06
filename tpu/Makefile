################################################################################
# TPU FPGA Build Orchestrator (no nested make)
#
# Usage:
#   make all TARGET=ultra96-v2
#   make tensorcore-ip
#   make tpu-ip TARGET=ultra96-v2
#   make bitstream TARGET=ultra96-v2
################################################################################

TARGET ?= ultra96-v2
TARGETS := ultra96-v2 alveo-u280 alveo-v80
SUPPORTED_TARGETS := ultra96-v2

TENSORCORE_DIR := tensorcore
ULTRA96_DIR := ultra96-v2
ULTRA96_FPGA_RTL_DIR := $(ULTRA96_DIR)/rtl
ULTRA96_IP_REPO_DIR := $(ULTRA96_DIR)/ip_repo
ULTRA96_OUTPUT_DIR := $(ULTRA96_DIR)/output
ULTRA96_PACKAGE_SCRIPT := $(ULTRA96_DIR)/package_tpu_ip.tcl
ULTRA96_BUILD_SCRIPT := $(ULTRA96_DIR)/build_bd_bitstream.tcl

# Common FPGA settings (override as needed)
PART ?= xczu3eg-sbva484-1-i
IP_NAME ?= cornell_tpu
IP_VERSION ?= 1.0
IP_VENDOR ?= cornell.edu
IP_LIBRARY ?= user
PROJ_NAME ?= tpu_system
BD_NAME ?= minitpu

# Vivado settings
VIVADO_SETTINGS ?= /opt/xilinx/Vitis/2023.2/settings64.sh
VIVADO ?= vivado
VIVADO_OPTS ?= -mode batch -nojournal
VIVADO_ENV_HINT ?= "source $(VIVADO_SETTINGS)"
VIVADO_CHECK = command -v $(VIVADO) >/dev/null 2>&1 || \
	{ echo "Vivado not found on PATH. Run: $(VIVADO_ENV_HINT)"; exit 2; }
# VIVADO_RUN: Use with additional arguments, e.g., $(call VIVADO_RUN,-source script.tcl)
define VIVADO_RUN
	bash -c "source $(VIVADO_SETTINGS) && vivado $(VIVADO_OPTS) $(1)"
endef

# TensorCore IP packaging
TENSORCORE_IP_REPO ?= $(TENSORCORE_DIR)/ip_repo
TENSORCORE_IP_XML := $(TENSORCORE_IP_REPO)/tensorcore_1.0/component.xml

ULTRA96_IP_OUT_DIR := $(ULTRA96_IP_REPO_DIR)/$(IP_NAME)_$(IP_VERSION)
ULTRA96_COMPONENT_XML := $(ULTRA96_IP_OUT_DIR)/component.xml
ULTRA96_ARTIFACTS_DIR := $(ULTRA96_OUTPUT_DIR)/artifacts
ULTRA96_BITSTREAM := $(ULTRA96_ARTIFACTS_DIR)/$(BD_NAME).bit
ULTRA96_HWH := $(ULTRA96_ARTIFACTS_DIR)/$(BD_NAME).hwh

ifeq ($(TARGET),ultra96-v2)
ULTRA96_IP_DEPS := _ultra96_package_ip
ULTRA96_BIT_DEPS := _ultra96_bitstream
else
ULTRA96_IP_DEPS :=
ULTRA96_BIT_DEPS :=
endif

.PHONY: all help list-targets tensorcore-ip tpu-ip bitstream clean \
	clean-tensorcore clean-target

all: bitstream

help:
	@echo "TPU FPGA Build Orchestrator (no nested make)"
	@echo ""
	@echo "Targets:"
	@echo "  tensorcore-ip  Package TensorCore IP (tpu/TensorCore)"
	@echo "  tpu-ip         Package TPU IP for TARGET"
	@echo "  bitstream      Build TPU bitstream for TARGET"
	@echo "  clean          Clean TensorCore + TARGET outputs"
	@echo "  list-targets   Show supported targets"
	@echo ""
	@echo "Targets available: $(TARGETS)"
	@echo "Supported today:   $(SUPPORTED_TARGETS)"
	@echo ""
	@echo "Examples:"
	@echo "  make tensorcore-ip"
	@echo "  make tpu-ip TARGET=ultra96-v2"
	@echo "  make bitstream TARGET=ultra96-v2"
	@echo ""
	@echo "Notes:"
	@echo "  - For Vivado: source /opt/xilinx/Vitis/2023.2/settings64.sh"

list-targets:
	@echo "Targets: $(TARGETS)"
	@echo "Supported today: $(SUPPORTED_TARGETS)"

# -----------------------------------------------------------------------------
# TensorCore IP
# -----------------------------------------------------------------------------

tensorcore-ip: $(TENSORCORE_IP_XML)

$(TENSORCORE_IP_XML): $(TENSORCORE_DIR)/*.sv $(TENSORCORE_DIR)/package_ip.tcl
	@echo "Packaging TensorCore IP..."
	$(call VIVADO_RUN,-source $(TENSORCORE_DIR)/package_ip.tcl -tclargs \
		-part $(PART) -out $(TENSORCORE_IP_REPO) -ip_name tensorcore -ip_version 1.0)

clean-tensorcore:
	rm -rf $(TENSORCORE_IP_REPO) $(TENSORCORE_DIR)/pkg_*_tmp $(TENSORCORE_DIR)/.Xil \
		$(TENSORCORE_DIR)/*.log $(TENSORCORE_DIR)/*.jou

# -----------------------------------------------------------------------------
# TPU IP + Bitstream
# -----------------------------------------------------------------------------

tpu-ip: tensorcore-ip $(ULTRA96_IP_DEPS)
	@if [ "$(TARGET)" != "ultra96-v2" ]; then \
		echo "TARGET=$(TARGET) is not supported yet."; \
		exit 2; \
	fi

bitstream: tpu-ip $(ULTRA96_BIT_DEPS)
	@if [ "$(TARGET)" != "ultra96-v2" ]; then \
		echo "TARGET=$(TARGET) is not supported yet."; \
		exit 2; \
	fi

_ultra96_package_ip: $(ULTRA96_COMPONENT_XML)

$(ULTRA96_COMPONENT_XML): $(TENSORCORE_DIR)/*.sv $(ULTRA96_FPGA_RTL_DIR)/*.v $(ULTRA96_FPGA_RTL_DIR)/*.sv
	@echo "=========================================="
	@echo "Packaging TPU IP: $(IP_NAME) v$(IP_VERSION)"
	@echo "=========================================="
	@mkdir -p $(ULTRA96_IP_REPO_DIR)
	$(call VIVADO_RUN,-source $(ULTRA96_PACKAGE_SCRIPT) -tclargs \
		-ip_name $(IP_NAME) \
		-ip_version $(IP_VERSION) \
		-ip_vendor $(IP_VENDOR) \
		-ip_library $(IP_LIBRARY) \
		-part $(PART) \
		-rtl_dir $(TENSORCORE_DIR) \
		-rtl_dir $(ULTRA96_FPGA_RTL_DIR) \
		-repo_out $(ULTRA96_IP_REPO_DIR))
	@echo ""
	@echo "IP packaged successfully: $(ULTRA96_IP_OUT_DIR)"
	@echo ""

_ultra96_bitstream: $(ULTRA96_BITSTREAM)

$(ULTRA96_BITSTREAM): $(ULTRA96_COMPONENT_XML)
	@echo "=========================================="
	@echo "Building Block Design and Bitstream"
	@echo "=========================================="
	@mkdir -p $(ULTRA96_OUTPUT_DIR)
	$(call VIVADO_RUN,-source $(ULTRA96_BUILD_SCRIPT) -tclargs \
		-proj_name $(PROJ_NAME) \
		-part $(PART) \
		-ip_repo_path $(ULTRA96_IP_REPO_DIR) \
		-out_dir $(ULTRA96_OUTPUT_DIR) \
		-bd_name $(BD_NAME))
	@echo ""
	@echo "Build complete!"
	@echo "Artifacts: $(ULTRA96_ARTIFACTS_DIR)"
	@ls -la $(ULTRA96_ARTIFACTS_DIR)/
	@echo ""

clean: clean-tensorcore
	@if [ "$(TARGET)" = "ultra96-v2" ]; then \
		rm -rf $(ULTRA96_IP_REPO_DIR) $(ULTRA96_OUTPUT_DIR) $(ULTRA96_DIR)/.Xil \
			$(ULTRA96_DIR)/*.log $(ULTRA96_DIR)/*.jou $(ULTRA96_DIR)/pkg_*_proj; \
	else \
		echo "TARGET=$(TARGET) is not supported yet."; \
	fi
