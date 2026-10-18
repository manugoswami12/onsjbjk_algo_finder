def drain(xs):
    out = []
    while xs:
        out.append(xs.pop(0))
    return out
