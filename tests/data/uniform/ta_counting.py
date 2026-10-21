def tally_sort(xs, top):
    tally = [0] * (top + 1)
    for x in xs:
        tally[x] += 1
    out = []
    for k in range(top + 1):
        for _ in range(tally[k]):
            out.append(k)
    return out
