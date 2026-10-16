def counting_sort(a, k):
    count = [0] * (k + 1)
    for x in a:
        count[x] += 1
    out = []
    for v in range(k + 1):
        for _ in range(count[v]):
            out.append(v)
    return out
