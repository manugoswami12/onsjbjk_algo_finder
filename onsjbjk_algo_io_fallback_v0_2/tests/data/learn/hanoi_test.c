#include <stdio.h>
void mv(int n, int a, int b, int c) {
  if (n > 0) { mv(n - 1, a, c, b); printf("%d %d\n", a, b); mv(n - 1, c, b, a); }
}
