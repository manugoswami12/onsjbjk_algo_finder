def matmul(a, b, n):
    rows = []
    for i in range(n):
        row = []
        for j in range(n):
            s = 0
            for k in range(n):
                s = s + a[i][k] * b[k][j]
            row.append(s)
        rows.append(row)
    return rows
