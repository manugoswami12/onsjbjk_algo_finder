def prod_upto(n):
    if n < 2:
        return 1
    return n * prod_upto(n - 1)
