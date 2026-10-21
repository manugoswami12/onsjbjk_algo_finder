int min3(int a, int b, int c) { int m = a < b ? a : b; return m < c ? m : c; }
int lev(const char *a, int la, const char *b, int lb, int d[][64]) {
    for (int i = 0; i <= la; i++) d[i][0] = i;
    for (int j = 0; j <= lb; j++) d[0][j] = j;
    for (int i = 1; i <= la; i++)
        for (int j = 1; j <= lb; j++)
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] != b[j - 1]));
    return d[la][lb];
}
