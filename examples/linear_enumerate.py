def where(seq, target):
    for k, item in enumerate(seq):
        if item == target:
            return k
    return -1
