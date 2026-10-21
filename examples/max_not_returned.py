def size(values):
    best = values[0]
    for v in values:
        if v > best:
            best = v
    return len(values)
