def table(n):
    flags = [True] * (n + 1)
    flags[0] = flags[1] = False
    for p in range(2, n + 1):
        if flags[p]:
            for j in range(p * p, n + 1, p):
                flags[j] = False
    return [i for i in range(n + 1) if flags[i]]
