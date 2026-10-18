def count_steps(n):
    count = 0
    for p in range(2, n + 1):
        for j in range(p * p, n + 1, p):
            count += 1
    return count
