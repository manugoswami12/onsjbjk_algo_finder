def djb2(text):
    h = 5381
    for ch in text:
        h = ((h << 5) + h) ^ ord(ch)
    return h
