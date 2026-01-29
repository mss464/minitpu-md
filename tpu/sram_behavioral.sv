`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Behavioral True Dual-Port SRAM for ASIC synthesis
// Replaces Xilinx blk_mem_gen IPs for target-independent RTL
//////////////////////////////////////////////////////////////////////////////////

// Data BRAM: 32-bit x 8192 (matches blk_mem_gen_0)
module sram_8192x32 (
    // Port A
    input  logic        clka,
    input  logic        ena,
    input  logic        wea,
    input  logic [12:0] addra,
    input  logic [31:0] dina,
    output logic [31:0] douta,

    // Port B
    input  logic        clkb,
    input  logic        enb,
    input  logic        web,
    input  logic [12:0] addrb,
    input  logic [31:0] dinb,
    output logic [31:0] doutb
);

    // Memory array
    logic [31:0] mem [0:8191];

    // Port A - Read-first mode
    always_ff @(posedge clka) begin
        if (ena) begin
            douta <= mem[addra];
            if (wea)
                mem[addra] <= dina;
        end
    end

    // Port B - Read-first mode
    always_ff @(posedge clkb) begin
        if (enb) begin
            doutb <= mem[addrb];
            if (web)
                mem[addrb] <= dinb;
        end
    end

endmodule


// Instruction BRAM: 64-bit x 256 (matches blk_mem_gen_1)
module sram_256x64 (
    // Port A
    input  logic        clka,
    input  logic        ena,
    input  logic        wea,
    input  logic [7:0]  addra,
    input  logic [63:0] dina,
    output logic [63:0] douta,

    // Port B
    input  logic        clkb,
    input  logic        enb,
    input  logic        web,
    input  logic [7:0]  addrb,
    input  logic [63:0] dinb,
    output logic [63:0] doutb
);

    // Memory array
    logic [63:0] mem [0:255];

    // Port A - Read-first mode
    always_ff @(posedge clka) begin
        if (ena) begin
            douta <= mem[addra];
            if (wea)
                mem[addra] <= dina;
        end
    end

    // Port B - Read-first mode
    always_ff @(posedge clkb) begin
        if (enb) begin
            doutb <= mem[addrb];
            if (web)
                mem[addrb] <= dinb;
        end
    end

endmodule
