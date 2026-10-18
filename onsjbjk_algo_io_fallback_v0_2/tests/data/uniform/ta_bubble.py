def sort_passes(xs):
    done = False
    while not done:
        done = True
        for k in range(len(xs) - 1):
            if xs[k] > xs[k + 1]:
                xs[k], xs[k + 1] = xs[k + 1], xs[k]
                done = False
    return xs
