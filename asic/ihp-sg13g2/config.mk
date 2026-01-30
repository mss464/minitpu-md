# Design configuration for mini-TPU Core targeting IHP SG13G2
# For use with OpenROAD-flow-scripts

export PLATFORM    = ihp-sg13g2
export DESIGN_NAME = tpu_core

# RTL sources - all files from src directory
export VERILOG_FILES = $(sort $(wildcard $(DESIGN_HOME)/src/$(DESIGN_NICKNAME)/*.sv))

# Design home is relative to flow/ directory
export DESIGN_HOME = ./designs

# Timing constraints
export SDC_FILE = $(DESIGN_HOME)/$(PLATFORM)/$(DESIGN_NICKNAME)/constraint.sdc

# Floorplan parameters (conservative for first run)
export CORE_UTILIZATION = 40
export PLACE_DENSITY    = 0.55

# Clock period in ns (50 MHz = 20ns)
export CLOCK_PERIOD = 20.0

# Synthesis settings
export SYNTH_HIERARCHICAL = 0

# Don't use any blackboxed macros for now
export ADDITIONAL_LEFS =
export ADDITIONAL_LIBS =
export ADDITIONAL_GDS  =
