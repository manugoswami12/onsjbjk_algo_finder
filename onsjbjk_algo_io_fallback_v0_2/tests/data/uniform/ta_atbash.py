def mirror_letters(text):
    out = ""
    for ch in text:
        out += chr(155 - ord(ch)) if ch.isupper() else ch
    return out
