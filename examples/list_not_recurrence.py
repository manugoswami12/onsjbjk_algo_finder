def ramp(n):
    out = [0]
    for _ in range(n):
        out.append(out[-1] + 1)
    return out
