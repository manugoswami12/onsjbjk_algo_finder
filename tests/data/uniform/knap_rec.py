def best(items, i, cap):
    if i == len(items):
        return 0
    w, v = items[i]
    skip = best(items, i + 1, cap)
    if w <= cap:
        return max(skip, v + best(items, i + 1, cap - w))
    return skip
