`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// scratchpad.sv - Dual-port scratchpad memory
//
// Portable across FPGA and ASIC targets:
//   - Define TARGET_FPGA for Xilinx BRAM IP (blk_mem_gen_0)
//   - Default (no define) uses behavioral SRAM blackbox for ASIC
//////////////////////////////////////////////////////////////////////////////////

module scratchpad #(
    parameter ADDR_WIDTH = 13,
    parameter DATA_WIDTH = 32
)(
    input  logic                     clk,
    input  logic                     rst_n,

    // Control interface
    input  logic [ADDR_WIDTH-1:0]    base_addr,

    // Write interface (from Slave Stream)
    input  logic dma_wr_en,
    input  logic [DATA_WIDTH-1:0] dma_wr_data,
    input logic [15:0] dma_write_pointer,

    // Read interface (to Master Stream)
    input  logic dma_rd_en,
    output logic [DATA_WIDTH-1:0] dma_rd_data,
    input logic [15:0] dma_read_pointer,

    // Compute-side BRAM port (Port B)
    input  logic [ADDR_WIDTH-1:0]    dma_comp_addr_b,
    input  logic [DATA_WIDTH-1:0]    dma_comp_din_b,
    output logic [DATA_WIDTH-1:0]    dma_comp_dout_b,
    input  logic                     dma_comp_en_b,
    input  logic                     dma_comp_we_b
);

    // Internal signals
    logic [ADDR_WIDTH-1:0] dma_addr;

    // Address logic - combinational to avoid extra cycle of latency
    assign dma_addr = base_addr + (dma_wr_en ? dma_write_pointer : (dma_rd_en ? dma_read_pointer : '0));

    //-----------------------------------------------
    // BRAM instantiation (true dual-port)
    //-----------------------------------------------
`ifdef TARGET_FPGA
    // Xilinx Block RAM IP
    blk_mem_gen_0 u_bram (
`else
    // ASIC: Behavioral SRAM blackbox
    sram_8192x32 u_bram (
`endif
        // Port A - DMA side (FSM-controlled)
        .clka(clk),
        .ena(1'b1),
        .wea(dma_wr_en),
        .addra(dma_addr),
        .dina(dma_wr_data),
        .douta(dma_rd_data),

        // Port B - Compute side
        .clkb(clk),
        .enb(1'b1),
        .web(dma_comp_we_b),
        .addrb(dma_comp_addr_b),
        .dinb(dma_comp_din_b),
        .doutb(dma_comp_dout_b)
    );

endmodule
