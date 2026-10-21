def rotate_once(xs):
    for k in range(len(xs) - 1):
        xs[k], xs[k + 1] = xs[k + 1], xs[k]
    return xs
