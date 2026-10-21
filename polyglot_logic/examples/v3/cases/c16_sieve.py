def sieve(n):
    mark = [True] * (n + 1)
    p = 2
    while p * p <= n:
        if mark[p]:
            for j in range(p * p, n + 1, p):
                mark[j] = False
        p += 1
    return [i for i in range(2, n + 1) if mark[i]]
