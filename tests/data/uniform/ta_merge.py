def halves(xs):
    if len(xs) <= 1:
        return xs
    mid = len(xs) // 2
    left, right = halves(xs[:mid]), halves(xs[mid:])
    out = []
    while left and right:
        if left[0] <= right[0]:
            out.append(left.pop(0))
        else:
            out.append(right.pop(0))
    return out + left + right
