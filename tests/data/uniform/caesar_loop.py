def caesar(codes, key):
    out = []
    for c in codes:
        out.append(chr((ord(c) - 65 + key) % 26 + 65))
    return out
