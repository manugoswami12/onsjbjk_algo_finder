void change(int n, const int *coins, int k, int *counts) {
    for (int i = 0; i < k; i++) {
        counts[i] = 0;
        while (n >= coins[i]) {
            n -= coins[i];
            counts[i]++;
        }
    }
}
