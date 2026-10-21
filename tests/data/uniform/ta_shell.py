def gapped(xs):
    gap = len(xs) // 2
    while gap > 0:
        for i in range(gap, len(xs)):
            item = xs[i]
            j = i
            while j >= gap and xs[j - gap] > item:
                xs[j] = xs[j - gap]
                j -= gap
            xs[j] = item
        gap //= 2
    return xs
