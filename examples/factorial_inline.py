def h(n):
    return 1 if n in {0, 1} else n * h(n - 1)
