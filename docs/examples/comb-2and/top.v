module top(
  input a,
  input b,
  output y
);
  wire n1;
  and u1(n1, a, b);
  not u2(y, n1);
endmodule
