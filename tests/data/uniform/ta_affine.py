ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
def enc(text, a, b):
    out = ""
    for ch in text:
        i = ALPHA.find(ch)
        out += ALPHA[(a * i + b) % len(ALPHA)]
    return out
