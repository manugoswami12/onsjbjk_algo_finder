def valid(number):
    total = 0
    for i, ch in enumerate(reversed(number)):
        d = int(ch)
        if i % 2 == 1:
            d = d * 2
            if d > 9:
                d = d - 9
        total += d
    return total % 10 == 0
