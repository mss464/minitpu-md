`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// tensorcore.sv - ASIC top-level wrapper for Phase 1 tapeout
// 
// Stripped version of tpu without AXI interfaces.
// Exposes direct control signals for standalone testing.
//
// Target: IHP SG13G2 130nm
// Clock: 50 MHz (20ns period)
//////////////////////////////////////////////////////////////////////////////////

module tensorcore (
    input  logic        clk,
    input  logic        rst_n,

    // Control interface (directly exposed, no AXI)
    input  logic [2:0]  tpu_mode,       // Operation mode
    input  logic [12:0] base_addr,      // Base address for BRAM ops
    input  logic [31:0] dma_len,        // Transfer length
    
    // Status outputs
    output logic        busy,
    output logic        done,
    
    // Data input FIFO interface (replaces AXI-Stream slave)
    input  logic        din_valid,
    output logic        din_ready,
    input  logic [63:0] din_data,       // 64-bit data input
    
    // Data output FIFO interface (replaces AXI-Stream master)
    output logic        dout_valid,
    input  logic        dout_ready,
    output logic [31:0] dout_data,      // 32-bit data output
    
    // Instruction input interface
    input  logic        instr_valid,
    input  logic [63:0] instr_data,
    input  logic [7:0]  instr_addr
);

    // Internal wires
    wire [7:0]  pc;
    wire [63:0] instr;
    wire [12:0] addr_a, addr_b, addr_out, addr_const;
    wire [9:0]  opcode;
    wire [22:0] len;
    wire [1:0]  mode;
    
    logic start_systolic, start_vpu, start_vadd;
    wire  systolic_done, vpu_done, vadd_done;
    
    // BRAM interface wires
    wire [12:0] comp_addr_b;
    wire [31:0] comp_din_b, comp_dout_b;
    wire        comp_en_b, comp_we_b;
    
    // DMA state machine simplified
    reg [3:0] state;
    localparam IDLE         = 4'd0;
    localparam EXEC_WRITE   = 4'd1;
    localparam EXEC_READ    = 4'd2;  
    localparam EXEC_COMPUTE = 4'd3;
    localparam WAIT_COMPUTE = 4'd4;
    localparam FETCH_1      = 4'd5;
    localparam FETCH_2      = 4'd6;
    localparam FETCH_3      = 4'd7;
    localparam WAIT_DONE    = 4'd8;
    
    // Simplified status
    assign busy = (state != IDLE);
    assign done = (state == WAIT_DONE) && (tpu_mode == 3'd0);
    
    // FIFO handshake (simplified)
    assign din_ready  = (state == EXEC_WRITE);
    assign dout_valid = (state == EXEC_READ);
    
    // Write/read pointers
    reg [15:0] write_pointer, read_pointer;
    
    // FSM
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            write_pointer <= 0;
            read_pointer <= 0;
            start_systolic <= 0;
            start_vpu <= 0;
            start_vadd <= 0;
        end else begin
            start_systolic <= 0;
            start_vpu <= 0;
            start_vadd <= 0;
            
            case (state)
                IDLE: begin
                    if (tpu_mode == 3'd1 || tpu_mode == 3'd4) begin
                        write_pointer <= 0;
                        state <= EXEC_WRITE;
                    end else if (tpu_mode == 3'd2) begin
                        read_pointer <= 0;
                        state <= EXEC_READ;
                    end else if (tpu_mode == 3'd3) begin
                        state <= EXEC_COMPUTE;
                    end
                end
                
                EXEC_WRITE: begin
                    if (din_valid && din_ready) begin
                        write_pointer <= write_pointer + 1;
                        if (write_pointer >= dma_len[15:0] - 1)
                            state <= WAIT_DONE;
                    end
                end
                
                EXEC_READ: begin
                    if (dout_valid && dout_ready) begin
                        read_pointer <= read_pointer + 1;
                        if (read_pointer >= dma_len[15:0] - 1)
                            state <= WAIT_DONE;
                    end
                end
                
                EXEC_COMPUTE: begin
                    if (mode == 2'd3) begin // Done instruction
                        state <= WAIT_DONE;
                    end else begin
                        case (mode)
                            2'd0: start_vpu      <= 1;
                            2'd1: start_systolic <= 1;
                            2'd2: start_vadd     <= 1;
                        endcase
                        state <= WAIT_COMPUTE;
                    end
                end
                
                WAIT_COMPUTE: begin
                    if (systolic_done || vpu_done || vadd_done)
                        state <= FETCH_1;
                end
                
                FETCH_1: state <= FETCH_2;
                FETCH_2: state <= FETCH_3;
                FETCH_3: state <= EXEC_COMPUTE;
                
                WAIT_DONE: begin
                    if (tpu_mode == 3'd0)
                        state <= IDLE;
                end
            endcase
        end
    end
    
    // Instantiate BRAM (behavioral for Phase 1)
    scratchpad #(
        .ADDR_WIDTH(13),
        .DATA_WIDTH(32)
    ) u_scratchpad (
        .clk(clk),
        .rst_n(rst_n),
        .base_addr(base_addr),
        
        .dma_wr_en(din_valid && din_ready),
        .dma_wr_data(din_data[31:0]),
        .dma_write_pointer(write_pointer),
        
        .dma_rd_en(dout_valid && dout_ready),
        .dma_rd_data(dout_data),
        .dma_read_pointer(read_pointer),
        
        .dma_comp_addr_b(comp_addr_b),
        .dma_comp_din_b(comp_din_b),
        .dma_comp_dout_b(comp_dout_b),
        .dma_comp_en_b(comp_en_b),
        .dma_comp_we_b(comp_we_b)
    );
    
    // Instantiate compute core
    compute_core #(
        .ADDR_WIDTH(13),
        .DATA_WIDTH(32),
        .VPU_DATA_W(32),
        .VPU_ADDR_W(13),
        .VPU_OP_W(10),
        .VPU_IADDR_W(5)
    ) u_compute_core (
        .clk(clk),
        .rst_n(rst_n),
        
        .mode_compute(mode),
        
        .addr_a_compute(addr_a),
        .addr_b_compute(addr_b),
        .addr_out_compute(addr_out),
        .addr_const_compute(addr_const),
        .opcode_compute(opcode),
        .len_compute(len),
        
        .start_systolic_compute(start_systolic),
        .start_vadd_compute(start_vadd),
        .start_vpu_compute(start_vpu),
        
        .systolic_done_compute(systolic_done),
        .vadd_done_compute(vadd_done),
        .vpu_done_compute(vpu_done),
        
        .bram_addr_b(comp_addr_b),
        .bram_din_b(comp_din_b),
        .bram_dout_b(comp_dout_b),
        .bram_en_b(comp_en_b),
        .bram_we_b(comp_we_b)
    );
    
    // Program counter
    wire pc_enable = (systolic_done || vadd_done || vpu_done);
    
    pc #(
        .PC_WIDTH(8)
    ) u_pc (
        .clk(clk),
        .rst_n(rst_n),
        .PC_enable(pc_enable),
        .PC_load(1'b0),
        .PC_load_val(8'b0),
        .PC(pc)
    );
    
    // Instruction decoder
    decoder dec (
        .instr_decode(instr),
        .len_decode(len),
        .opcode_decode(opcode),
        .addr_const_decode(addr_const),
        .addr_a_decode(addr_a),
        .addr_b_decode(addr_b),
        .addr_out_decode(addr_out),
        .mode_decode(mode)
    );
    
    // Instruction BRAM (behavioral)
    sram_256x64 I_bram (
        .clka(clk),
        .ena(1'b1),
        .wea(instr_valid),
        .addra(instr_addr),
        .dina(instr_data),
        .douta(),
        
        .clkb(clk),
        .enb(1'b1),
        .web(1'b0),
        .addrb(pc),
        .dinb(64'b0),
        .doutb(instr)
    );

endmodule
