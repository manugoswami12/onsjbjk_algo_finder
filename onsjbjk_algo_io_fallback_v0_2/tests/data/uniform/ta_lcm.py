def common(a, b):
    while b:
        a, b = b, a % b
    return a

def multiple(a, b):
    return a * b // common(a, b)
