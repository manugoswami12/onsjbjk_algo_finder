def paths(grid, n):
    t = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i + j < n and i - j >= 0:
                t[i][j] = grid[i][j] + 1
    return t
