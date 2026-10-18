def terms(n):
    out = [0, 1]
    for _ in range(n - 1):
        out.append(out[-1] + out[-2])
    return out
