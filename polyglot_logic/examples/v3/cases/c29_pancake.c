void flip(int *a, int m) {
    for (int i = 0; i < m; i++, m--) { int t = a[i]; a[i] = a[m]; a[m] = t; }
}
void pancake(int *a, int n) {
    for (int size = n; size > 1; size--) {
        int mx = 0;
        for (int i = 1; i < size; i++)
            if (a[i] > a[mx]) mx = i;
        flip(a, mx);
        flip(a, size - 1);
    }
}
