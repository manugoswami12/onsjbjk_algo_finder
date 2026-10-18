def lucas(n):
    a, b = 2, 1
    for _ in range(n):
        a, b = b, a + b
    return a
