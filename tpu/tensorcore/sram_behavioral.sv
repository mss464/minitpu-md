`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Behavioral True Dual-Port SRAM (portable simulation model)
// Matches write-first, 2-cycle read latency behavior.
//////////////////////////////////////////////////////////////////////////////////

// Data BRAM: 32-bit x 8192 (matches legacy blk_mem_gen_0)
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

    logic [31:0] mem [0:8191];

    // Port A pipeline
    logic [12:0] addra_d;
    logic        ena_d, ena_d2;
    logic [31:0] data_a_d, data_a_q;

    always_ff @(posedge clka) begin
        if (ena) begin
            if (wea)
                mem[addra] <= dina;
            addra_d <= addra;
            ena_d   <= 1'b1;
        end else begin
            ena_d   <= 1'b0;
        end

        if (ena_d) begin
            data_a_d <= mem[addra_d];
            ena_d2   <= 1'b1;
        end else begin
            ena_d2   <= 1'b0;
        end

        if (ena_d2)
            data_a_q <= data_a_d;
    end

    assign douta = data_a_q;

    // Port B pipeline
    logic [12:0] addrb_d;
    logic        enb_d, enb_d2;
    logic [31:0] data_b_d, data_b_q;

    always_ff @(posedge clkb) begin
        if (enb) begin
            if (web)
                mem[addrb] <= dinb;
            addrb_d <= addrb;
            enb_d   <= 1'b1;
        end else begin
            enb_d   <= 1'b0;
        end

        if (enb_d) begin
            data_b_d <= mem[addrb_d];
            enb_d2   <= 1'b1;
        end else begin
            enb_d2   <= 1'b0;
        end

        if (enb_d2)
            data_b_q <= data_b_d;
    end

    assign doutb = data_b_q;

endmodule


// Instruction BRAM: 64-bit x 256 (matches legacy blk_mem_gen_1)
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

    logic [63:0] mem [0:255];

    // Port A pipeline
    logic [7:0]  addra_d;
    logic        ena_d, ena_d2;
    logic [63:0] data_a_d, data_a_q;

    always_ff @(posedge clka) begin
        if (ena) begin
            if (wea)
                mem[addra] <= dina;
            addra_d <= addra;
            ena_d   <= 1'b1;
        end else begin
            ena_d   <= 1'b0;
        end

        if (ena_d) begin
            data_a_d <= mem[addra_d];
            ena_d2   <= 1'b1;
        end else begin
            ena_d2   <= 1'b0;
        end

        if (ena_d2)
            data_a_q <= data_a_d;
    end

    assign douta = data_a_q;

    // Port B pipeline
    logic [7:0]  addrb_d;
    logic        enb_d, enb_d2;
    logic [63:0] data_b_d, data_b_q;

    always_ff @(posedge clkb) begin
        if (enb) begin
            if (web)
                mem[addrb] <= dinb;
            addrb_d <= addrb;
            enb_d   <= 1'b1;
        end else begin
            enb_d   <= 1'b0;
        end

        if (enb_d) begin
            data_b_d <= mem[addrb_d];
            enb_d2   <= 1'b1;
        end else begin
            enb_d2   <= 1'b0;
        end

        if (enb_d2)
            data_b_q <= data_b_d;
    end

    assign doutb = data_b_q;

endmodule
