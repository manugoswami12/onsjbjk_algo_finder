def garden(xs):
    pos = 0
    while pos < len(xs):
        if pos == 0 or xs[pos - 1] <= xs[pos]:
            pos += 1
        else:
            xs[pos - 1], xs[pos] = xs[pos], xs[pos - 1]
            pos -= 1
    return xs
