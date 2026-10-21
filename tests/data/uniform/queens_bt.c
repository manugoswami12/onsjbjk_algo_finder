int solve(int n, int row, int *col, int *d1, int *d2) {
    if (row == n) return 1;
    int count = 0;
    for (int c = 0; c < n; c++)
        if (!col[c] && !d1[row + c] && !d2[row - c + n - 1]) {
            col[c] = d1[row + c] = d2[row - c + n - 1] = 1;
            count += solve(n, row + 1, col, d1, d2);
            col[c] = d1[row + c] = d2[row - c + n - 1] = 0;
        }
    return count;
}
