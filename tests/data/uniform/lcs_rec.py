def lcs(xs, ys):
    if not xs or not ys:
        return []
    if xs[0] == ys[0]:
        return [xs[0]] + lcs(xs[1:], ys[1:])
    a, b = lcs(xs[1:], ys), lcs(xs, ys[1:])
    return a if len(a) > len(b) else b
