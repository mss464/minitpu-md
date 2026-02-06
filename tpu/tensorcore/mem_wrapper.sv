`timescale 1ns / 1ps
////////////////////////////////////////////////////////////////////////////////
// Module: mem_wrapper
// Description: Portable True Dual-Port RAM wrapper with 1-cycle read latency.
// Behavior: read-first, matches Xilinx blk_mem_gen with:
//   - Register_PortA_Output_of_Memory_Primitives = false  
//   - Register_PortB_Output_of_Memory_Primitives = false
//   - Operating_Mode_A = READ_FIRST
//   - Operating_Mode_B = READ_FIRST
//
// Latency: 1 cycle from address assertion to valid data output
//   Cycle 0: Address presented, ena=1
//   Cycle 1: Data appears on output (douta/doutb)
////////////////////////////////////////////////////////////////////////////////

module mem_wrapper #(
    parameter DATA_WIDTH = 32,
    parameter ADDR_WIDTH = 13, // 8192 depth by default
    parameter DEPTH      = 1 << ADDR_WIDTH,
    parameter RAM_STYLE  = "block" // "block", "distributed", "ultra"
)(
    // Port A
    input  logic                    clka,
    input  logic                    ena,
    input  logic                    wea,
    input  logic [ADDR_WIDTH-1:0]   addra,
    input  logic [DATA_WIDTH-1:0]   dina,
    output logic [DATA_WIDTH-1:0]   douta,

    // Port B
    input  logic                    clkb,
    input  logic                    enb,
    input  logic                    web,
    input  logic [ADDR_WIDTH-1:0]   addrb,
    input  logic [DATA_WIDTH-1:0]   dinb,
    output logic [DATA_WIDTH-1:0]   doutb
);

`ifdef TARGET_FPGA
    // FPGA inference with explicit ram_style
    (* ram_style = RAM_STYLE *)
    logic [DATA_WIDTH-1:0] mem [0:DEPTH-1];
`else
    // Generic behavioral RAM (ASIC/sim)
    logic [DATA_WIDTH-1:0] mem [0:DEPTH-1];
`endif

    // Port A: 1-cycle read latency, READ_FIRST mode
    logic [DATA_WIDTH-1:0] data_a_reg;

    always_ff @(posedge clka) begin
        if (ena) begin
            // READ_FIRST: read happens before write
            data_a_reg <= mem[addra];
            if (wea)
                mem[addra] <= dina;
        end
    end

    assign douta = data_a_reg;

    // Port B: 1-cycle read latency, READ_FIRST mode
    logic [DATA_WIDTH-1:0] data_b_reg;

    always_ff @(posedge clkb) begin
        if (enb) begin
            // READ_FIRST: read happens before write
            data_b_reg <= mem[addrb];
            if (web)
                mem[addrb] <= dinb;
        end
    end

    assign doutb = data_b_reg;

endmodule
