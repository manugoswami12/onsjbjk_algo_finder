#include <stdio.h>
void move(int n, int from, int to, int via) {
    if (n > 0) {
        move(n - 1, from, via, to);
        printf("%d -> %d\n", from, to);
        move(n - 1, via, to, from);
    }
}
