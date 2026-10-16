def rotate(a):
    last = a[-1]
    j = len(a) - 1
    while j > 0:
        a[j] = a[j - 1]
        j -= 1
    a[0] = last
    return a
