def equals_its_divisors(n):
    total = 0
    for d in range(1, n):
        if n % d == 0:
            total += d
    return total == n
