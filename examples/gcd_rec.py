def common(a, b):
    if b == 0:
        return a
    return common(b, a % b)
