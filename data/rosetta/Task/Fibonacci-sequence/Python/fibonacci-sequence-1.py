from math import *

def analytic_fibonacci(n):
  assert isinstance(n,int), "n must be an integer."
  assert n<=71 , "n must be <=71 due to floating point precision limitations."
  sqrt_5 = sqrt(5);
  p = (1 + sqrt_5) / 2;
  q = 1/p;
  return int( (p**n + q**n) / sqrt_5 + 0.5 )

for i in range(1,31):
  print analytic_fibonacci(i),
