def fill(a, i):
    if i >= len(a):
        return a
    a[i + 1] = a[i]
    return fill(a, i + 1)
