def shift(text, k):
    return "".join(chr((ord(c) - 65 + k) % 26 + 65) for c in text)
