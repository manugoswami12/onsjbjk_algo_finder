void wrong_exchange(int *a, int n) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n - i - 1; j++) {
            if (a[j] > a[j + 1]) {
                int t = a[j];
                a[j] = a[j + 2];
                a[j + 2] = t;
            }
        }
    }
}
