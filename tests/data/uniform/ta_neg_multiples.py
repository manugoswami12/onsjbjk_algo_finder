def total(n):
    s = 0
    for k in range(n):
        if k % 3 == 0 or k % 5 == 0:
            s += k
    return s
