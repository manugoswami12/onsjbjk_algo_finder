#include <stdlib.h>

static int cmp(const void *a, const void *b) { return *(const int *)a - *(const int *)b; }

void sort_ints(int *a, int n) {
    qsort(a, n, sizeof(int), cmp);
}
