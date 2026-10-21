def h(c):
    c.sort()
    n = len(c)
    for i in range(n):
        if i >= c[n - 1 - i]:
            return i
    return n
