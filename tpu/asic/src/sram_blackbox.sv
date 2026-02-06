`timescale 1ns / 1ps
/////////////////////////////////////////////////////////////////////////////////
// SRAM Blackbox Wrappers for ASIC Synthesis
// These are synthesized as empty modules and replaced with hardened macros in PnR
/////////////////////////////////////////////////////////////////////////////////

// Data SRAM: 8192 x 32-bit (true dual-port)
(* blackbox *)
module sram_8192x32 (
    input  logic        clka,
    input  logic        ena,
    input  logic        wea,
    input  logic [12:0] addra,
    input  logic [31:0] dina,
    output logic [31:0] douta,
    
    input  logic        clkb,
    input  logic        enb,
    input  logic        web,
    input  logic [12:0] addrb,
    input  logic [31:0] dinb,
    output logic [31:0] doutb
);
    // Blackbox - no implementation
    // In real ASIC flow, this would map to SRAM macros
    // For IHP SG13G2: Use banked 2048x64 macros
endmodule

// Instruction SRAM: 256 x 64-bit (true dual-port)
(* blackbox *)
module sram_256x64 (
    input  logic        clka,
    input  logic        ena,
    input  logic        wea,
    input  logic [7:0]  addra,
    input  logic [63:0] dina,
    output logic [63:0] douta,
    
    input  logic        clkb,
    input  logic        enb,
    input  logic        web,
    input  logic [7:0]  addrb,
    input  logic [63:0] dinb,
    output logic [63:0] doutb
);
    // Blackbox - no implementation
    // For IHP SG13G2: Use 256x64 macro directly
endmodule
