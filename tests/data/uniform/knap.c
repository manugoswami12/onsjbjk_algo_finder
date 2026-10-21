int knap(int *w, int *v, int n, int cap, int t[][101]) {
    for (int i = 1; i <= n; i++)
        for (int j = 0; j <= cap; j++) {
            t[i][j] = t[i - 1][j];
            if (w[i - 1] <= j && t[i - 1][j - w[i - 1]] + v[i - 1] > t[i][j])
                t[i][j] = t[i - 1][j - w[i - 1]] + v[i - 1];
        }
    return t[n][cap];
}
