# Ackermann with the outer tail call written as a loop (the textbook tail-call elimination).
def ackermann(m, n):
    while m != 0:
        if n == 0:
            n = 1
        else:
            n = ackermann(m, n - 1)
        m = m - 1
    return n + 1
