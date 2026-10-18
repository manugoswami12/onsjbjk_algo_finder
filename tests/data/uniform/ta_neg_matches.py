def agree(a, b):
    count = 0
    for x, y in zip(a, b):
        if x == y:
            count += 1
    return count
