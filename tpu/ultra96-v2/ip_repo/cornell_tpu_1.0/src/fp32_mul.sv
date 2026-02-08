module fp32_mul#(
  parameter FORMAT = "FP32",
  parameter INT_BITS = 16,
  parameter FRAC_BITS = 16,
  parameter WIDTH = 32
)(
  input [31:0] a, b,
  output reg [31:0] result
);

reg [23:0] a_m, b_m, z_m;
integer a_e, b_e, z_e_i;
integer shift;
reg a_s, b_s, z_s;
reg [49:0] product;
reg guard_bit, round_bit, sticky;

always @(*) begin
    // defaults to avoid latches
    result = '0;
    a_m = '0;
    b_m = '0;
    z_m = '0;
    a_e = 0;
    b_e = 0;
    z_e_i = 0;
    shift = 0;
    a_s = 1'b0;
    b_s = 1'b0;
    z_s = 1'b0;
    product = '0;
    guard_bit = 1'b0;
    round_bit = 1'b0;
    sticky = 1'b0;

    a_m = {1'b0, a[22:0]};
    b_m = {1'b0, b[22:0]};
    a_e = int'(a[30:23]) - 127;
    b_e = int'(b[30:23]) - 127;
    a_s = a[31];
    b_s = b[31];
    
    if ((a_e == 128 && a_m != 0) || (b_e == 128 && b_m != 0)) begin // NAN
        result = {1'b1, 8'hFF, 1'b1, 22'h0};
    end
    else if (a_e == 128) begin // INF A
        if (($signed(b_e) == -127) && (b_m == 0)) begin // NAN IF B = 0
            result = {1'b1, 8'hFF, 1'b1, 22'h0};
        end else begin
            result = {a_s ^ b_s, 8'hFF, 23'h0};
        end
    end
    else if (b_e == 128) begin // INF B
        if (($signed(a_e) == -127) && (a_m == 0)) begin // NAN IF A = 0
            result = {1'b1, 8'hFF, 1'b1, 22'h0};
        end else begin
            result = {a_s ^ b_s, 8'hFF, 23'h0};
        end
    end
    else if (($signed(a_e) == -127) && (a_m == 0)) begin // 0 if A = 0
        result = {a_s ^ b_s, 8'h0, 23'h0};
    end
    else if (($signed(b_e) == -127) && (b_m == 0)) begin // 0 if B = 0
        result = {a_s ^ b_s, 8'h0, 23'h0};
    end
    else begin
        if ($signed(a_e) == -127) begin 
            a_e = -126;
        end else begin
            a_m[23] = 1'b1;
        end
        
        if ($signed(b_e) == -127) begin 
            b_e = -126;
        end else begin
            b_m[23] = 1'b1;
        end
        
        if (~a_m[23]) begin
            a_m = a_m << 1;
            a_e = a_e - 1;
        end
        if (~b_m[23]) begin 
            b_m = b_m << 1;
            b_e = b_e - 1;
        end
        
        z_s = a_s ^ b_s;
        z_e_i = a_e + b_e + 1;
        product = a_m * b_m * 4;
        
        z_m = product[49:26];
        guard_bit = product[25];
        round_bit = product[24];
        sticky = (product[23:0] != 0);
        
        // handle underflow into subnormals
        if (z_e_i < -126) begin
            shift = -126 - z_e_i;
            if (shift >= 25) begin
                z_m = 0;
            end else begin
                z_m = z_m >> shift;
            end
            z_e_i = -126;
        end
        else if (z_m[23] == 0) begin
            z_e_i = z_e_i - 1;
            z_m = z_m << 1;
            z_m[0] = guard_bit;
            guard_bit = round_bit;
            round_bit = 1'b0;
        end
        // round
        else if (guard_bit && (round_bit | sticky | z_m[0])) begin
            z_m = z_m + 1;
            if (z_m == 24'hffffff) begin
                z_e_i = z_e_i + 1;
            end
        end
        
        result[22:0] = z_m[22:0];
        result[30:23] = z_e_i[7:0] + 127;
        result[31] = z_s;
        
        if (z_e_i == -126 && z_m[23] == 0) begin
            result[30:23] = 8'h0;
        end
        
        // overflow
        if (z_e_i > 127) begin 
            result[22:0] = 23'h0;
            result[30:23] = 8'hFF;
            result[31] = z_s;
        end
        // underflow to zero
        if (z_e_i < -149 || z_m == 0) begin
            result = {z_s, 8'h00, 23'h0};
        end
    end
end

endmodule
