`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module Name: vpu_simd
// Description: SIMD Vector Processing Unit with register file
//              - 8-lane SIMD execution (8 parallel vpu_op ALU instances)
//              - Vector register file (V0-V7)
//              - Supports VLOAD, VSTORE, VCOMPUTE operations
//              - Scalar broadcast support for vector-scalar operations
//////////////////////////////////////////////////////////////////////////////////

module vpu_simd #(
    parameter int DATA_W = 32,
    parameter int ADDR_W = 13,
    parameter int NUM_LANES = 8
)(
    input logic clk,
    input logic rst_n,

    // Instruction fields from decoder
    input logic [12:0] addr_a,
    input logic [12:0] addr_b,
    input logic [12:0] addr_out,
    input logic [9:0] opcode,           // For scalar VPU
    input logic [12:0] addr_const,      // For scalar VPU
    input logic [2:0] vpu_type,
    input logic [2:0] vreg_dst,
    input logic [2:0] vreg_a,
    input logic [2:0] vreg_b,
    input logic [2:0] vpu_opcode,
    input logic scalar_b,
    input logic start,

    // BRAM interface (Banked for 8-lane parallel access)
    output logic [ADDR_W-1:0] bram_addr,
    output logic [NUM_LANES*DATA_W-1:0] bram_din,
    input  logic [NUM_LANES*DATA_W-1:0] bram_dout,
    output logic bram_en,
    output logic bram_we,

    output logic done
);

    // Scalar vs SIMD routing
    logic start_scalar, start_simd;
    logic done_scalar, done_simd;
    logic [ADDR_W-1:0] bram_addr_scalar, bram_addr_simd;
    logic [DATA_W-1:0] bram_din_scalar;
    logic [NUM_LANES*DATA_W-1:0] bram_din_simd;
    logic bram_en_scalar, bram_en_simd;
    logic bram_we_scalar, bram_we_simd;

    // Route start signal based on VPU_TYPE
    assign start_scalar = start && (vpu_type == 3'b000);  // VPU_TYPE=0 (SCALAR)
    assign start_simd = start && (vpu_type != 3'b000);     // VPU_TYPE=1/2/3 (SIMD)

    // Route output signals based on which module is active
    assign bram_addr = (vpu_type == 3'b000) ? bram_addr_scalar : bram_addr_simd;
    // For scalar writes, we only write to the first 32 bits of the banked bus
    assign bram_din = (vpu_type == 3'b000) ? {{(NUM_LANES-1)*DATA_W{1'b0}}, bram_din_scalar} : bram_din_simd;
    assign bram_en = (vpu_type == 3'b000) ? bram_en_scalar : bram_en_simd;
    assign bram_we = (vpu_type == 3'b000) ? bram_we_scalar : bram_we_simd;
    assign done = (vpu_type == 3'b000) ? done_scalar : done_simd;

    // Instantiate legacy VPU for scalar operations (vpu_type == 0)
    vpu #(
        .DATA_W(DATA_W),
        .ADDR_W(ADDR_W),
        .OP_W(10),
        .INST_ADDR(5),
        .M(4)
    ) u_vpu_scalar (
        .clk(clk),
        .rst_n(rst_n),
        .start(start_scalar),
        .inst_addr_a(addr_a),
        .inst_addr_b(addr_b),
        .inst_addr_c(addr_out),
        .inst_addr_const(addr_const),
        .opcode(opcode),
        .bram_addr(bram_addr_scalar),
        .bram_din(bram_din_scalar),
        .bram_dout(bram_dout[DATA_W-1:0]), // Scalar only sees first bank
        .bram_en(bram_en_scalar),
        .bram_we(bram_we_scalar),
        .done(done_scalar)
    );

    // FSM states
    typedef enum logic [3:0] {
        IDLE,
        VLOAD_REQ,
        VLOAD_WAIT,
        VLOAD_CAPTURE,
        VSTORE_REQ,
        VCOMPUTE_READ,
        VCOMPUTE_EXEC,
        DONE_STATE
    } state_t;

    state_t state;

    // Vector register file
    logic [2:0] rf_rd_addr_a, rf_rd_addr_b, rf_wr_addr;
    logic [NUM_LANES-1:0][DATA_W-1:0] rf_rd_data_a, rf_rd_data_b, rf_wr_data;
    logic rf_wr_en;

    vec_regfile #(
        .NUM_REGS(8),
        .ELEM_WIDTH(DATA_W),
        .NUM_ELEMS(NUM_LANES)
    ) regfile (
        .clk(clk),
        .rst_n(rst_n),
        .rd_addr_a(rf_rd_addr_a),
        .rd_data_a(rf_rd_data_a),
        .rd_addr_b(rf_rd_addr_b),
        .rd_data_b(rf_rd_data_b),
        .wr_en(rf_wr_en),
        .wr_addr(rf_wr_addr),
        .wr_data(rf_wr_data)
    );

    // 8 parallel ALU instances
    logic [NUM_LANES-1:0][DATA_W-1:0] alu_result;

    generate
        for (genvar i = 0; i < NUM_LANES; i++) begin : alu_lanes
            logic [DATA_W-1:0] operand_b_lane;

            // Scalar broadcast: use element 0 for all lanes
            assign operand_b_lane = scalar_b ? rf_rd_data_b[0] : rf_rd_data_b[i];

            vpu_op #(
                .DATA_W(DATA_W),
                .OP_W(3)
            ) alu (
                .start(1'b1),
                .operand0(rf_rd_data_a[i]),
                .operand1(operand_b_lane),
                .opcode(vpu_opcode),
                .result_out(alu_result[i])
            );
        end
    endgenerate

    // Saved instruction fields for multi-cycle operations
    logic [12:0] saved_addr_a;
    logic [12:0] saved_addr_out;
    logic [2:0] saved_vreg_dst, saved_vreg_a;

    // FSM
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            bram_en_simd <= 1'b0;
            bram_we_simd <= 1'b0;
            bram_addr_simd <= '0;
            bram_din_simd <= '0;
            rf_wr_en <= 1'b0;
            rf_wr_addr <= '0;
            rf_wr_data <= '0;
            rf_rd_addr_a <= '0;
            rf_rd_addr_b <= '0;
            done_simd <= 1'b0;
            saved_addr_a <= '0;
            saved_addr_out <= '0;
            saved_vreg_dst <= '0;
            saved_vreg_a <= '0;
        end else begin
            // Defaults
            done_simd <= 1'b0;
            bram_we_simd <= 1'b0;
            bram_en_simd <= 1'b0;
            rf_wr_en <= 1'b0;

            case (state)
                IDLE: begin
                    if (start_simd) begin
                        // Save instruction fields
                        saved_addr_a <= addr_a;
                        saved_addr_out <= addr_out;
                        saved_vreg_dst <= vreg_dst;
                        saved_vreg_a <= vreg_a;

                        case (vpu_type)
                            3'b001: begin  // VLOAD
                                state <= VLOAD_REQ;
                            end
                            3'b010: begin  // VSTORE
                                rf_rd_addr_a <= vreg_a;
                                state <= VSTORE_REQ;
                            end
                            3'b011: begin // VCOMPUTE
                                rf_rd_addr_a <= vreg_a;
                                rf_rd_addr_b <= vreg_b;
                                state <= VCOMPUTE_READ;
                            end
                            default: state <= DONE_STATE;
                        endcase
                    end
                end

                // VLOAD: Read all 8 elements in parallel (1 cycle req + latency)
                VLOAD_REQ: begin
                    bram_en_simd <= 1'b1;
                    bram_we_simd <= 1'b0;
                    bram_addr_simd <= saved_addr_a;
                    state <= VLOAD_WAIT;
                end

                VLOAD_WAIT: begin
                    bram_en_simd <= 1'b1;
                    // Wait for BRAM latency (we could use a counter, but let's assume fixed timing for now)
                    state <= VLOAD_CAPTURE;
                end

                VLOAD_CAPTURE: begin
                    rf_wr_en <= 1'b1;
                    rf_wr_addr <= saved_vreg_dst;
                    rf_wr_data <= bram_dout; // 8 words in parallel
                    state <= DONE_STATE;
                end

                // VSTORE: Write all 8 elements in parallel (1 cycle)
                VSTORE_REQ: begin
                    bram_en_simd <= 1'b1;
                    bram_we_simd <= 1'b1;
                    bram_addr_simd <= saved_addr_out;
                    bram_din_simd <= rf_rd_data_a; // 8 words in parallel
                    state <= DONE_STATE;
                end

                // VCOMPUTE: Wait one cycle for register read
                VCOMPUTE_READ: begin
                    state <= VCOMPUTE_EXEC;
                end

                // VCOMPUTE: Parallel execution (1 cycle)
                VCOMPUTE_EXEC: begin
                    rf_wr_en <= 1'b1;
                    rf_wr_addr <= saved_vreg_dst;
                    rf_wr_data <= alu_result;
                    state <= DONE_STATE;
                end

                DONE_STATE: begin
                    done_simd <= 1'b1;
                    bram_en_simd <= 1'b0;
                    state <= IDLE;
                end
                default: begin
                    state <= IDLE;
                end
            endcase
        end
    end

endmodule
