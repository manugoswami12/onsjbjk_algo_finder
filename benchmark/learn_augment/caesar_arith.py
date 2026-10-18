# Caesar cipher by character arithmetic: shift each letter within its alphabet.
def caesar(text, key):
    out = ''
    for c in text:
        if 'A' <= c <= 'Z':
            out += chr((ord(c) - ord('A') + key) % 26 + ord('A'))
        elif 'a' <= c <= 'z':
            out += chr((ord(c) - ord('a') + key) % 26 + ord('a'))
        else:
            out += c
    return out
