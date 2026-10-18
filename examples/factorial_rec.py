def g(n):
    if n <= 1:
        return 1
    return n * g(n - 1)
