def ways(coins, amount):
    table = [0] * (amount + 1)
    table[0] = 1
    for c in coins:
        for j in range(c, amount + 1):
            table[j] += table[j - c]
    return table[amount]
