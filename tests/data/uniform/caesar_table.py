import string


def caesar(text, k):
    a = string.ascii_lowercase
    return text.translate(str.maketrans(a, a[k:] + a[:k]))
