def m91(n):
    if n > 100:
        return n - 10
    return m91(m91(n + 11))
