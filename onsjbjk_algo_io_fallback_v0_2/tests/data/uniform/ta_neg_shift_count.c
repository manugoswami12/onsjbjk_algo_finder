int ones(unsigned n) { int c = 0; while (n) { c = c + (n & 1); n = n >> 1; } return c; }
