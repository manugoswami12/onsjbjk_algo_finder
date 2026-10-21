def dot(a, b):
    s = 0
    for k in range(len(a)):
        s = s + a[k] * b[k]
    return s
