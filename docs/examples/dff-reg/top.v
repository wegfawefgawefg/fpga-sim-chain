module top(
  input clk,
  input d,
  output q
);
  dff u1(.d(d), .q(q), .clk(clk));
endmodule
