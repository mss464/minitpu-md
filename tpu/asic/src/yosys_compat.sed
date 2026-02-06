# Convert SystemVerilog to Yosys-compatible Verilog

# Remove function definition (lines 32-35)
/function automatic int idx/,/endfunction/d

# Replace idx(r,c) calls with (r*N + c)
s/idx(\([^,]*\), *\([^)]*\))/(\1*N + \2)/g

# Parameter int -> parameter
s/parameter int\b/parameter/g

# localparam int -> localparam integer
s/localparam int\b/localparam integer/g

# for (int -> for (integer
s/for (int\b/for (integer/g

# int flat_index -> integer flat_index
s/\bint flat_index\b/integer flat_index/g

# int ph -> integer ph
s/\bint ph\b/integer ph/g

# bit all_done -> reg all_done
s/\bbit all_done\b/reg all_done/g
