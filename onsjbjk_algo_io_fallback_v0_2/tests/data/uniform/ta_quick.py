def split_sort(xs):
    if len(xs) <= 1:
        return xs
    pivot = xs[0]
    return split_sort([x for x in xs[1:] if x < pivot]) + [pivot] + split_sort([x for x in xs[1:] if x >= pivot])
