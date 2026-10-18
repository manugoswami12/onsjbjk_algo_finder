def comb(xs):
    gap = len(xs)
    swapped = True
    while gap > 1 or swapped:
        gap = max(1, int(gap / 1.3))
        swapped = False
        for i in range(len(xs) - gap):
            if xs[i] > xs[i + gap]:
                xs[i], xs[i + gap] = xs[i + gap], xs[i]
                swapped = True
    return xs
