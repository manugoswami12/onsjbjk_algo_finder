long seq(int n) { long a = 0, b = 1, t; for (int k = 0; k < n; k++) { t = a + b; a = b; b = t; } return a; }
