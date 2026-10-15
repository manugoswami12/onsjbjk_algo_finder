def shaker_sort(a):
    for k in range(len(a) - 1, 0, -1):
        for j in range(k):
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
        for j in range(k, 0, -1):
            if a[j - 1] > a[j]:
                a[j - 1], a[j] = a[j], a[j - 1]
    return a
