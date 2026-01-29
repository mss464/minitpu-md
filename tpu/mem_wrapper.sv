`timescale 1ns / 1ps
////////////////////////////////////////////////////////////////////////////////
// Module: mem_wrapper
// Description: Platform-agnostic True Dual-Port RAM wrapper
//
// supported Targets:
//   - TARGET_FPGA: Infers Xilinx BRAM/URAM (Synchronous read)
//   - TARGET_ASIC: Instantiates behavioral model (or PDK macros in future)
//
// Note: Port A is typically used for DMA/External access
//       Port B is typically used for Compute/Internal access
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
    // -------------------------------------------------------------------------
    // FPGA Implementation: Inferred BRAM/URAM
    // -------------------------------------------------------------------------
    
    // Explicitly define ram_style for Vivado synthesis (block, ultra, distributed)
    (* ram_style = RAM_STYLE *) 
    logic [DATA_WIDTH-1:0] mem [0:DEPTH-1];

    // Port A
    always_ff @(posedge clka) begin
        if (ena) begin
            if (wea)
                mem[addra] <= dina;
            douta <= mem[addra]; // Read-during-write: New data (Write First) or Old (Read First)?
                                 // Standard inference usually defaults to Read-First or No-Change depending on coding.
                                 // Ideally, valid data is read.
        end
    end

    // Port B
    always_ff @(posedge clkb) begin
        if (enb) begin
            if (web)
                mem[addrb] <= dinb;
            doutb <= mem[addrb];
        end
    end

`else
    // -------------------------------------------------------------------------
    // ASIC / Simulation Implementation
    // -------------------------------------------------------------------------
    // Ideally map to SRAM macros here. For now, use behavioral model that
    // approximates standard SRAM macro behavior (Read-First).
    
    logic [DATA_WIDTH-1:0] mem [0:DEPTH-1];

    // Port A
    always_ff @(posedge clka) begin
        if (ena) begin
            douta <= mem[addra];
            if (wea)
                mem[addra] <= dina;
        end
    end

    // Port B
    always_ff @(posedge clkb) begin
        if (enb) begin
            doutb <= mem[addrb];
            if (web)
                mem[addrb] <= dinb;
        end
    end

`endif

endmodule
