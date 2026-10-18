int digit_total(int n, int base) { int s = 0; while (n > 0) { s = s + n % base; n = n / base; } return s; }
