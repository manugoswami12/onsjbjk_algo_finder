def every_other(n):
    if n < 2:
        return 1
    return n * every_other(n - 2)
