# Matrix product with three nested loops: c[i][j] = sum over k of a[i][k] * b[k][j].
def matmul(a, b):
    n, m, p = len(a), len(b), len(b[0])
    c = [[0] * p for _ in range(n)]
    for i in range(n):
        for j in range(p):
            for k in range(m):
                c[i][j] += a[i][k] * b[k][j]
    return c
