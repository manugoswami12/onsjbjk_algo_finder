def pell(n):
    if n < 2:
        return n
    return 2 * pell(n - 1) + pell(n - 2)
