def dedup(s):
    out = [s[0]]
    for x in s[1:]:
        if x != out[-1]:
            out.append(x)
    return out
