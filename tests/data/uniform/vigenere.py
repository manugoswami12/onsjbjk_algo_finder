def vigenere(text, key):
    out = []
    for i in range(len(text)):
        out.append(chr((ord(text[i]) + ord(key[i % len(key)]) - 130) % 26 + 65))
    return out
