`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 11/21/2025 10:01:43 AM
// Design Name: 
// Module Name: compute_core
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module compute_core #(
    parameter ADDR_WIDTH = 13,
    parameter DATA_WIDTH = 32,

    // VPU-specific params
    parameter VPU_DATA_W  = 32,
    parameter VPU_ADDR_W  = 13,
    parameter VPU_OP_W    = 4,
    parameter VPU_IADDR_W = 5
)(
    input  logic clk,
    input  logic rst_n,
    input logic [1:0] mode_compute,
    input  logic [ADDR_WIDTH-1:0]    addr_a_compute,
    input  logic [ADDR_WIDTH-1:0]    addr_b_compute,
    input  logic [ADDR_WIDTH-1:0]    addr_out_compute,
    input logic [ADDR_WIDTH-1:0]     addr_const_compute,
    input logic [9:0] opcode_compute,
    input  logic [22:0]              len_compute,
    input logic start_systolic_compute,
    input logic start_vadd_compute,
    input logic start_vpu_compute,
    output logic systolic_done_compute,
    output logic vadd_done_compute,
    output logic vpu_done_compute,

    // VPU SIMD fields
    input logic [2:0] vpu_type_compute,
    input logic [2:0] vreg_dst_compute,
    input logic [2:0] vreg_a_compute,
    input logic [2:0] vreg_b_compute,
    input logic [2:0] vpu_opcode_compute,
    input logic scalar_b_compute,

    // BRAM Port B Interface - 8 Banks
    output logic [ADDR_WIDTH-1:0]    bram_addr_b0, output logic [DATA_WIDTH-1:0]    bram_din_b0, input  logic [DATA_WIDTH-1:0]    bram_dout_b0, output logic                     bram_en_b0, output logic                     bram_we_b0,
    output logic [ADDR_WIDTH-1:0]    bram_addr_b1, output logic [DATA_WIDTH-1:0]    bram_din_b1, input  logic [DATA_WIDTH-1:0]    bram_dout_b1, output logic                     bram_en_b1, output logic                     bram_we_b1,
    output logic [ADDR_WIDTH-1:0]    bram_addr_b2, output logic [DATA_WIDTH-1:0]    bram_din_b2, input  logic [DATA_WIDTH-1:0]    bram_dout_b2, output logic                     bram_en_b2, output logic                     bram_we_b2,
    output logic [ADDR_WIDTH-1:0]    bram_addr_b3, output logic [DATA_WIDTH-1:0]    bram_din_b3, input  logic [DATA_WIDTH-1:0]    bram_dout_b3, output logic                     bram_en_b3, output logic                     bram_we_b3,
    output logic [ADDR_WIDTH-1:0]    bram_addr_b4, output logic [DATA_WIDTH-1:0]    bram_din_b4, input  logic [DATA_WIDTH-1:0]    bram_dout_b4, output logic                     bram_en_b4, output logic                     bram_we_b4,
    output logic [ADDR_WIDTH-1:0]    bram_addr_b5, output logic [DATA_WIDTH-1:0]    bram_din_b5, input  logic [DATA_WIDTH-1:0]    bram_dout_b5, output logic                     bram_en_b5, output logic                     bram_we_b5,
    output logic [ADDR_WIDTH-1:0]    bram_addr_b6, output logic [DATA_WIDTH-1:0]    bram_din_b6, input  logic [DATA_WIDTH-1:0]    bram_dout_b6, output logic                     bram_en_b6, output logic                     bram_we_b6,
    output logic [ADDR_WIDTH-1:0]    bram_addr_b7, output logic [DATA_WIDTH-1:0]    bram_din_b7, input  logic [DATA_WIDTH-1:0]    bram_dout_b7, output logic                     bram_en_b7, output logic                     bram_we_b7
);

    logic [ADDR_WIDTH-1:0]    vadd_addr;
    logic [DATA_WIDTH-1:0]    vadd_din_b;
    logic [DATA_WIDTH-1:0]    vadd_dout_b;
    logic                     vadd_en_b;
    logic                     vadd_we_b;
    
    // Systolic expects banked interface
    logic [ADDR_WIDTH-1:0]    systolic_addr;
    logic [8*DATA_WIDTH-1:0]  systolic_din_b;
    logic [8*DATA_WIDTH-1:0]  systolic_dout_b;
    logic                     systolic_en_b;
    logic                     systolic_we_b;
    
    logic [ADDR_WIDTH-1:0]    vpu_addr;
    logic [8*DATA_WIDTH-1:0]  vpu_din_b;
    logic [8*DATA_WIDTH-1:0]  vpu_dout_b;
    logic                     vpu_en_b;
    logic                     vpu_we_b;
    

    dummy_unit #(
        .ADDR_WIDTH(ADDR_WIDTH),
        .DATA_WIDTH(DATA_WIDTH)
    ) u_dummy_unit (
        .clk(clk),
        .rst_n(rst_n),
        .start(start_vadd_compute),
        .done(vadd_done_compute),

        // BRAM B port (single bank for vadd)
        .bram_addr_b(vadd_addr),
        .bram_din_b (vadd_din_b),
        .bram_dout_b(bram_dout_b0),
        .bram_en_b  (vadd_en_b),
        .bram_we_b  (vadd_we_b),

        .addr_a_vadd(addr_a_compute),
        .addr_b_vadd(addr_b_compute),
        .addr_out_vadd(addr_out_compute),
        .len_vadd(len_compute)
    );

    mxu #(
        .N(4),
        .DATA_WIDTH(DATA_WIDTH),
        .BANKING_FACTOR(8),
        .ADDRESS_WIDTH(ADDR_WIDTH),
        .MEM_LATENCY(3)
    ) u_mxu (
        .clk(clk),
        .rst_n(rst_n),

        .start(start_systolic_compute),
        .done(systolic_done_compute),

        .base_addr_w(addr_a_compute),
        .base_addr_x(addr_b_compute),
        .base_addr_out(addr_out_compute),
        
        // Banked BRAM interface
        .mem_req_addr(systolic_addr),
        .mem_req_data(systolic_din_b),
        .mem_resp_data(systolic_dout_b),
        .mem_read_en (systolic_en_b),
        .mem_write_en(systolic_we_b)
    );



    vpu_simd #(
        .DATA_W(VPU_DATA_W),
        .ADDR_W(VPU_ADDR_W),
        .NUM_LANES(8)
    ) u_vpu_simd (
        .clk(clk),
        .rst_n(rst_n),
        .start(start_vpu_compute),

        // Instruction fields
        .addr_a(addr_a_compute),
        .addr_b(addr_b_compute),
        .addr_out(addr_out_compute),
        .opcode(opcode_compute),
        .addr_const(addr_const_compute),
        .vpu_type(vpu_type_compute),
        .vreg_dst(vreg_dst_compute),
        .vreg_a(vreg_a_compute),
        .vreg_b(vreg_b_compute),
        .vpu_opcode(vpu_opcode_compute),
        .scalar_b(scalar_b_compute),

        // BRAM B port (Banked)
        .bram_addr(vpu_addr),
        .bram_din(vpu_din_b),
        .bram_dout(vpu_dout_b),
        .bram_en(vpu_en_b),
        .bram_we(vpu_we_b),
        .done(vpu_done_compute)
    );
    
    //---------------------------------------------
// BRAM PORT B ARBITRATION (8 BANKS)
//---------------------------------------------
always_comb begin
    // default safe values
    bram_addr_b0 = '0; bram_din_b0  = '0; bram_en_b0   = 1'b0; bram_we_b0   = 1'b0;
    bram_addr_b1 = '0; bram_din_b1  = '0; bram_en_b1   = 1'b0; bram_we_b1   = 1'b0;
    bram_addr_b2 = '0; bram_din_b2  = '0; bram_en_b2   = 1'b0; bram_we_b2   = 1'b0;
    bram_addr_b3 = '0; bram_din_b3  = '0; bram_en_b3   = 1'b0; bram_we_b3   = 1'b0;
    bram_addr_b4 = '0; bram_din_b4  = '0; bram_en_b4   = 1'b0; bram_we_b4   = 1'b0;
    bram_addr_b5 = '0; bram_din_b5  = '0; bram_en_b5   = 1'b0; bram_we_b5   = 1'b0;
    bram_addr_b6 = '0; bram_din_b6  = '0; bram_en_b6   = 1'b0; bram_we_b6   = 1'b0;
    bram_addr_b7 = '0; bram_din_b7  = '0; bram_en_b7   = 1'b0; bram_we_b7   = 1'b0;

    // default passthrough dout to all units
    vadd_dout_b      = bram_dout_b0;
    vpu_dout_b       = {bram_dout_b7, bram_dout_b6, bram_dout_b5, bram_dout_b4, bram_dout_b3, bram_dout_b2, bram_dout_b1, bram_dout_b0};
    systolic_dout_b  = {bram_dout_b7, bram_dout_b6, bram_dout_b5, bram_dout_b4, bram_dout_b3, bram_dout_b2, bram_dout_b1, bram_dout_b0};

    case (mode_compute)
        
        2'b00: begin  // VPU (All 8 banks)
            bram_addr_b0 = vpu_addr; bram_din_b0 = vpu_din_b[0*32 +: 32]; bram_en_b0 = vpu_en_b; bram_we_b0 = vpu_we_b;
            bram_addr_b1 = vpu_addr; bram_din_b1 = vpu_din_b[1*32 +: 32]; bram_en_b1 = vpu_en_b; bram_we_b1 = vpu_we_b;
            bram_addr_b2 = vpu_addr; bram_din_b2 = vpu_din_b[2*32 +: 32]; bram_en_b2 = vpu_en_b; bram_we_b2 = vpu_we_b;
            bram_addr_b3 = vpu_addr; bram_din_b3 = vpu_din_b[3*32 +: 32]; bram_en_b3 = vpu_en_b; bram_we_b3 = vpu_we_b;
            bram_addr_b4 = vpu_addr; bram_din_b4 = vpu_din_b[4*32 +: 32]; bram_en_b4 = vpu_en_b; bram_we_b4 = vpu_we_b;
            bram_addr_b5 = vpu_addr; bram_din_b5 = vpu_din_b[5*32 +: 32]; bram_en_b5 = vpu_en_b; bram_we_b5 = vpu_we_b;
            bram_addr_b6 = vpu_addr; bram_din_b6 = vpu_din_b[6*32 +: 32]; bram_en_b6 = vpu_en_b; bram_we_b6 = vpu_we_b;
            bram_addr_b7 = vpu_addr; bram_din_b7 = vpu_din_b[7*32 +: 32]; bram_en_b7 = vpu_en_b; bram_we_b7 = vpu_we_b;
        end

        2'b01: begin  // Systolic (All 8 banks)
            bram_addr_b0 = systolic_addr; bram_din_b0 = systolic_din_b[0*32 +: 32]; bram_en_b0 = systolic_en_b; bram_we_b0 = systolic_we_b;
            bram_addr_b1 = systolic_addr; bram_din_b1 = systolic_din_b[1*32 +: 32]; bram_en_b1 = systolic_en_b; bram_we_b1 = systolic_we_b;
            bram_addr_b2 = systolic_addr; bram_din_b2 = systolic_din_b[2*32 +: 32]; bram_en_b2 = systolic_en_b; bram_we_b2 = systolic_we_b;
            bram_addr_b3 = systolic_addr; bram_din_b3 = systolic_din_b[3*32 +: 32]; bram_en_b3 = systolic_en_b; bram_we_b3 = systolic_we_b;
            bram_addr_b4 = systolic_addr; bram_din_b4 = systolic_din_b[4*32 +: 32]; bram_en_b4 = systolic_en_b; bram_we_b4 = systolic_we_b;
            bram_addr_b5 = systolic_addr; bram_din_b5 = systolic_din_b[5*32 +: 32]; bram_en_b5 = systolic_en_b; bram_we_b5 = systolic_we_b;
            bram_addr_b6 = systolic_addr; bram_din_b6 = systolic_din_b[6*32 +: 32]; bram_en_b6 = systolic_en_b; bram_we_b6 = systolic_we_b;
            bram_addr_b7 = systolic_addr; bram_din_b7 = systolic_din_b[7*32 +: 32]; bram_en_b7 = systolic_en_b; bram_we_b7 = systolic_we_b;
        end

        2'b10: begin  // Vadd (Bank 0)
            bram_addr_b0 = vadd_addr;
            bram_din_b0  = vadd_din_b;
            bram_en_b0   = vadd_en_b;
            bram_we_b0   = vadd_we_b;
        end

        default: ;
    endcase
end


endmodule
