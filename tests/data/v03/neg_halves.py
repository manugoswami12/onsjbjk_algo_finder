def halves(xs):
    if len(xs) < 2:
        return xs
    h = len(xs) // 2
    left = halves(xs[:h])
    right = halves(xs[h:])
    return left + right
