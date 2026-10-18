def cheapest(cost):
    n = len(cost)
    best = [[0] * n for _ in range(n)]
    for i in range(n - 1):
        for j in range(n):
            if best[i][j] > cost[i][j] + 1:
                best[i][j] = cost[i][j] + 1
    return best
