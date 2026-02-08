# Timing constraints for mini-TensorCore
# Target: IHP SG13G2, 50 MHz (20ns period)

# Primary clock
create_clock -name clk -period 20.0 [get_ports {clk}]

# Clock uncertainty (conservative for 130nm)
set_clock_uncertainty 0.5 [get_clocks clk]

# Input delays (assume 10% of period)
set_input_delay -clock clk 2.0 [all_inputs]

# Output delays
set_output_delay -clock clk 2.0 [all_outputs]

# False paths for reset (async reset)
set_false_path -from [get_ports {rst_n}]
