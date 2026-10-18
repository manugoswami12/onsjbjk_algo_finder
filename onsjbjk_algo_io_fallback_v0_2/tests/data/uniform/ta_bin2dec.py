def value_of(bits):
    total = 0
    for ch in bits:
        total = total * 2 + int(ch)
    return total
