def bits_of(n):
    out = ""
    while n > 0:
        out = str(n % 2) + out
        n = n // 2
    return out or "0"
