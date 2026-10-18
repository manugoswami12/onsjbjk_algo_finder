def scramble(text, key):
    return "".join(chr(ord(c) ^ key) for c in text)
