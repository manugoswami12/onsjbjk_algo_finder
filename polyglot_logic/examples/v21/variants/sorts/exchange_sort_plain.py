def exchange_sort(a):
    for k in range(len(a) - 1):
        for j in range(len(a) - 1 - k):
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
    return a
