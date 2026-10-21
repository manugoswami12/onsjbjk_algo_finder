# 0-1 knapsack by dynamic programming over a (items + 1) x (capacity + 1) table.
def knapsack(weights, values, capacity):
    n = len(weights)
    table = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for w in range(capacity + 1):
            table[i][w] = table[i - 1][w]
            if weights[i - 1] <= w:
                table[i][w] = max(table[i][w], table[i - 1][w - weights[i - 1]] + values[i - 1])
    return table[n][capacity]
