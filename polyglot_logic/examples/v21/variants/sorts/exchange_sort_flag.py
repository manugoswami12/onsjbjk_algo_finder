def exchange_sort(a):
    swaps = 0
    for k in range(len(a) - 1):
        for j in range(len(a) - 1 - k):
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                swaps = swaps + a[j]
    return swaps
