def qsort(xs):
    low, same, high = [], [], []
    if len(xs) <= 1:
        return xs
    p = xs[len(xs) // 2]
    for x in xs:
        if x < p:
            low.append(x)
        elif x > p:
            high.append(x)
        else:
            same.append(x)
    low = qsort(low)
    high = qsort(high)
    return low + same + high
