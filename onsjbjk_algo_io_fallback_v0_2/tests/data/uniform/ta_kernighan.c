int ones(unsigned n) { int c = 0; while (n) { n = n & (n - 1); c = c + 1; } return c; }
