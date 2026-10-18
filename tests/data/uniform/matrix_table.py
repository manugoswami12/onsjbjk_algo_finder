def matmul(a, b, n):
    c = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                c[i][j] = c[i][j] + a[i][k] * b[k][j]
    return c
